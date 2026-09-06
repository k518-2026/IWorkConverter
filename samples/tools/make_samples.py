# -*- coding: utf-8 -*-
"""
iWork Converter 動作確認用サンプルファイル生成スクリプト。

生成物:
  sample.pages / sample.numbers / sample.key            … iWork 2013 以降形式（Index/*.iwa）
  sample-iwork09.pages / .numbers / .key                … iWork '09 形式（index.xml）

.iwa は「Apple 独自フレーミングの Snappy で圧縮した protobuf 列」なので、
ここでは Snappy を「リテラルのみ」で符号化している（Snappy として正当な最小構成）。
"""
import io, os, zipfile, struct, datetime

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# ---------------- protobuf 書き出し ----------------
def varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)

def f_var(num, val):   return varint((num << 3) | 0) + varint(val)
def f_bytes(num, data):
    if isinstance(data, str): data = data.encode("utf-8")
    return varint((num << 3) | 2) + varint(len(data)) + data

def msg(*parts): return b"".join(parts)
def ref(num, obj_id): return f_bytes(num, f_var(1, obj_id))   # TSP.Reference 相当 {1: id}

# ---------------- Snappy（リテラルのみ） ----------------
def snappy_raw(data):
    out = bytearray(varint(len(data)))
    i = 0
    while i < len(data):
        chunk = data[i:i + 60]
        out.append(((len(chunk) - 1) << 2) | 0x00)   # リテラルタグ
        out += chunk
        i += 60
    return bytes(out)

def iwa_frame(payload):
    block = snappy_raw(payload)
    return b"\x00" + len(block).to_bytes(3, "little") + block

# ---------------- .iwa 組み立て ----------------
def archive(obj_id, type_id, body):
    info = msg(f_var(1, obj_id), f_bytes(2, msg(f_var(1, type_id), f_var(3, len(body)))))
    return varint(len(info)) + info + body

def iwa(objects):
    return iwa_frame(b"".join(archive(i, t, b) for i, t, b in objects))

# ---------------- テキストストレージ ----------------
def text_storage(text, para_styles):
    """TSWP.StorageArchive 相当 {1: stylesheet, 2: kind, 3: text, 4: 段落スタイル表}"""
    parts = [ref(1, 1), f_var(2, 1), f_bytes(3, text)]
    for char_index, style_id in para_styles:
        parts.append(f_bytes(4, msg(f_var(1, char_index), ref(2, style_id))))
    return msg(*parts)

def style(name):
    return msg(f_bytes(1, name), f_var(2, 0))

def para_style_table(paragraphs):
    """段落ごとの (開始文字位置, スタイル ID) を作る"""
    table, pos = [], 0
    for text, style_id in paragraphs:
        table.append((pos, style_id))
        pos += len(text) + 1
    return "\n".join(t for t, _ in paragraphs), table

# ================= Pages =================
def build_pages():
    ST_TITLE, ST_H1, ST_BODY, ST_CAPTION = 101, 102, 103, 104
    paragraphs = [
        ("iWork Converter 動作確認用サンプル", ST_TITLE),
        ("はじめに", ST_H1),
        ("このファイルは Pages → docx 変換の動作を確認するためのサンプルです。"
         "見出し・本文・箇条書き・番号付きリストが正しく変換されるかを確認できます。", ST_BODY),
        ("箇条書きの確認", ST_H1),
        ("•\t項目 A：段落スタイルから箇条書きを判定します", ST_BODY),
        ("•\t項目 B：先頭の記号とタブは取り除かれます", ST_BODY),
        ("•\t項目 C：Word の List Paragraph スタイルになります", ST_BODY),
        ("番号付きリストの確認", ST_H1),
        ("1.\t最初の手順", ST_BODY),
        ("2.\t次の手順", ST_BODY),
        ("3.\t最後の手順", ST_BODY),
        ("まとめ", ST_H1),
        ("段落が 13 個、見出しが 4 個、タイトルが 1 個あります。", ST_BODY),
        ("図 1　サンプル文書の構成", ST_CAPTION),
    ]
    text, table = para_style_table(paragraphs)
    box_text = "これはテキストボックス内の文字です。\nオプションを有効にすると文末に追記されます。"

    objects = [
        (1,   10000, msg(f_var(1, 1))),                       # Document
        (ST_TITLE,   2003, style("Title")),
        (ST_H1,      2003, style("Heading 1")),
        (ST_BODY,    2003, style("Body")),
        (ST_CAPTION, 2003, style("Caption")),
        (200, 2001, text_storage(text, table)),               # 本文
        (201, 2001, text_storage(box_text, [(0, ST_BODY)])),  # テキストボックス
    ]
    return {"Index/Document.iwa": iwa(objects)}

# ================= Numbers =================
def cell_text(key):
    return bytes([5, 3, 0, 0]) + struct.pack("<I", key) + b"\x00" * 4

def dec128(coeff, exp, negative=False):
    hi = ((exp + 6176) & 0x3FFF) << 49
    hi |= (coeff >> 64) & 0x1FFFFFFFFFFFF
    if negative: hi |= 1 << 63
    return struct.pack("<Q", coeff & 0xFFFFFFFFFFFFFFFF) + struct.pack("<Q", hi)

def cell_number(coeff, exp, negative=False):
    return bytes([5, 1, 0, 0]) + dec128(coeff, exp, negative)

def cell_date(dt):
    seconds = int((dt - datetime.datetime(2001, 1, 1)).total_seconds())
    return bytes([5, 5, 0, 0]) + dec128(seconds, 0)

def build_numbers():
    strings, keys = {}, {}
    def sid(s):
        if s not in keys:
            k = len(keys) + 1
            keys[s] = k
            strings[k] = s
        return keys[s]

    rows = [
        [("t", "商品"), ("t", "数量"), ("t", "単価"), ("t", "納品日")],
        [("t", "りんご"),   ("n", (120, 0)),  ("n", (1980, -1)), ("d", datetime.datetime(2026, 4, 6))],
        [("t", "みかん"),   ("n", (85, 0)),   ("n", (1250, -1)), ("d", datetime.datetime(2026, 4, 13))],
        [("t", "ぶどう"),   ("n", (43, 0)),   ("n", (5400, -1)), ("d", datetime.datetime(2026, 4, 20))],
        [("t", "もも"),     ("n", (67, 0)),   ("n", (3800, -1)), ("d", datetime.datetime(2026, 4, 27))],
        [("t", "合計"),     ("n", (315, 0)),  ("n", (12430, -1)), ("t", "―")],
    ]

    row_infos = []
    for r, row in enumerate(rows):
        storage, offsets = bytearray(), []
        for kind, val in row:
            offsets.append(len(storage))
            if kind == "t":   storage += cell_text(sid(val))
            elif kind == "n": storage += cell_number(val[0], val[1])
            else:             storage += cell_date(val)
        off_bytes = b"".join(struct.pack("<h", o) for o in offsets)
        row_infos.append(f_bytes(5, msg(f_var(1, r), f_bytes(3, bytes(storage)), f_bytes(4, off_bytes))))

    STR_ID, TILE_ID = 300, 310
    string_table = msg(f_var(1, 1), f_var(2, len(strings) + 1),
                       *[f_bytes(3, msg(f_var(1, k), f_var(2, 1), f_bytes(3, v)))
                         for k, v in sorted(strings.items())])
    tile = msg(f_var(1, len(rows)), *row_infos)

    data_store = msg(
        f_bytes(1, msg(f_bytes(1, msg(f_var(1, 0), ref(2, TILE_ID))))),   # タイル一覧
        f_bytes(4, msg(f_var(1, 0), ref(2, STR_ID))),                     # 文字列テーブル
    )
    table_model = msg(f_var(1, 1), f_bytes(2, "売上サンプル"), f_bytes(3, data_store))

    objects = [
        (1,       10000, msg(f_var(1, 1))),
        (STR_ID,  6005,  string_table),
        (TILE_ID, 6002,  tile),
        (320,     6001,  table_model),
    ]
    return {"Index/Document.iwa": iwa(objects)}

# ================= Keynote =================
def build_keynote():
    slides = [
        ("iWork Converter サンプル",
         ["Keynote → pptx の変換確認用", "スライドは 3 枚あります", "作成: サンプル生成スクリプト"]),
        ("読み取れるもの",
         ["スライドのタイトル", "本文の箇条書き", "スライドの並び順（参照リストから推定）"]),
        ("読み取れないもの",
         ["フォント・配色・背景", "画像・図形・グラフ", "アニメーションと画面切り替え"]),
    ]
    files = {}
    slide_ids = []
    for i, (title, bullets) in enumerate(slides):
        base = 10 * (i + 1)
        slide_ids.append(base)
        objects = [
            (base,     3,    msg(f_var(1, 1))),                              # SlideArchive
            (base + 1, 2001, text_storage(title, [(0, 900)])),               # タイトル
            (base + 2, 2001, text_storage("\n".join(bullets), [(0, 901)])),  # 本文
        ]
        files["Index/Slide-%d.iwa" % (i + 1)] = iwa(objects)

    doc = msg(*[ref(1, sid) for sid in slide_ids])
    files["Index/Document.iwa"] = iwa([
        (1, 1, doc),
        (900, 2003, style("Title")),
        (901, 2003, style("Body")),
    ])
    return files

# ================= iWork '09（index.xml） =================
NS = 'xmlns:sl="http://developer.apple.com/namespaces/sl" xmlns:sf="http://developer.apple.com/namespaces/sf" xmlns:key="http://developer.apple.com/namespaces/keynote2"'

PAGES09 = f"""<?xml version="1.0" encoding="UTF-8"?>
<sl:document {NS}>
  <sf:text-storage>
    <sf:text-body>
      <sf:p sf:style="title-style">iWork '09 形式のサンプル</sf:p>
      <sf:p sf:style="heading-1-style">概要</sf:p>
      <sf:p sf:style="body-style">index.xml を持つ旧形式の読み取り経路を確認するためのファイルです。</sf:p>
      <sf:p sf:style="heading-1-style">確認したいこと</sf:p>
      <sf:p sf:style="bullet-style">段落が順番どおりに取り出せること</sf:p>
      <sf:p sf:style="bullet-style">スタイル名から見出しが判定されること</sf:p>
      <sf:p sf:style="body-style">最後の段落です。</sf:p>
    </sf:text-body>
  </sf:text-storage>
</sl:document>
"""

NUMBERS09 = f"""<?xml version="1.0" encoding="UTF-8"?>
<sl:document {NS}>
  <sf:workspace>
    <sf:tabular-model sf:name="旧形式の表">
      <sf:grid sf:numrows="4" sf:numcols="3">
        <sf:r><sf:t>都市</sf:t><sf:t>人口（万人）</sf:t><sf:t>備考</sf:t></sf:r>
        <sf:r><sf:t>札幌</sf:t><sf:n sf:v="196"/><sf:t>北海道</sf:t></sf:r>
        <sf:r><sf:t>仙台</sf:t><sf:n sf:v="109"/><sf:t>宮城県</sf:t></sf:r>
        <sf:r><sf:t>那覇</sf:t><sf:n sf:v="31.7"/><sf:t>沖縄県</sf:t></sf:r>
      </sf:grid>
    </sf:tabular-model>
  </sf:workspace>
</sl:document>
"""

KEYNOTE09 = f"""<?xml version="1.0" encoding="UTF-8"?>
<key:presentation {NS}>
  <key:slide-list>
    <key:slide><sf:text><sf:p>旧形式のサンプル</sf:p><sf:p>1 枚目の項目</sf:p><sf:p>2 つめの項目</sf:p></sf:text></key:slide>
    <key:slide><sf:text><sf:p>2 枚目のスライド</sf:p><sf:p>並び順が保たれるか確認</sf:p></sf:text></key:slide>
  </key:slide-list>
</key:presentation>
"""

# ---------------- 書き出し ----------------
def write_zip(path, files):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    print("生成:", os.path.basename(path), "(%d bytes)" % os.path.getsize(path))

def main():
    write_zip(os.path.join(OUT, "sample.pages"),   build_pages())
    write_zip(os.path.join(OUT, "sample.numbers"), build_numbers())
    write_zip(os.path.join(OUT, "sample.key"),     build_keynote())
    write_zip(os.path.join(OUT, "sample-iwork09.pages"),   {"index.xml": PAGES09.encode("utf-8")})
    write_zip(os.path.join(OUT, "sample-iwork09.numbers"), {"index.xml": NUMBERS09.encode("utf-8")})
    write_zip(os.path.join(OUT, "sample-iwork09.key"),     {"index.xml": KEYNOTE09.encode("utf-8")})

if __name__ == "__main__":
    main()
