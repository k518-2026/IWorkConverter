# -*- coding: utf-8 -*-
"""生成したサンプルを、C# 側リーダーと同じ手順で読み直して検証する。"""
import zipfile, struct, sys, datetime

# --- varint / protobuf（ProtoMessage.cs と同じ挙動） ---
def read_varint(d, p, end):
    v = 0; shift = 0
    while p < end:
        b = d[p]; p += 1
        v |= (b & 0x7F) << shift
        if not (b & 0x80): return v, p
        shift += 7
        if shift > 63: return None, p
    return None, p

def parse(d, off=0, length=None):
    end = len(d) if length is None else off + length
    fields = {}
    p = off
    while p < end:
        key, p = read_varint(d, p, end)
        if key is None: break
        num, wire = key >> 3, key & 7
        if num <= 0: break
        if wire == 0:
            v, p = read_varint(d, p, end)
            if v is None: break
            fields.setdefault(num, []).append(("v", v))
        elif wire == 1:
            if p + 8 > end: break
            fields.setdefault(num, []).append(("v", struct.unpack_from("<Q", d, p)[0])); p += 8
        elif wire == 2:
            ln, p = read_varint(d, p, end)
            if ln is None or p + ln > end: break
            fields.setdefault(num, []).append(("b", d[p:p+ln])); p += ln
        elif wire == 5:
            if p + 4 > end: break
            fields.setdefault(num, []).append(("v", struct.unpack_from("<I", d, p)[0])); p += 4
        else: break
    return fields

def txt(b):
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        return None
    for c in s:
        if c == "\uFFFD" or (ord(c) < 0x20 and c not in "\n\r\t\v\f") or ord(c) == 0x7F:
            return None
    return s

# --- Snappy（AppleSnappy.cs と同じ） ---
def snappy_block(src, off, length):
    p, end = off, off + length
    n, p = read_varint(src, p, end)
    dst = bytearray()
    while p < end and len(dst) < n:
        tag = src[p]; p += 1
        kind = tag & 3
        if kind == 0:
            ln = tag >> 2
            if ln >= 60:
                extra = ln - 59
                ln = int.from_bytes(src[p:p+extra], "little"); p += extra
            ln += 1
            dst += src[p:p+ln]; p += ln
        else:
            if kind == 1:
                cl = 4 + ((tag >> 2) & 7); co = ((tag >> 5) & 7) << 8 | src[p]; p += 1
            elif kind == 2:
                cl = (tag >> 2) + 1; co = int.from_bytes(src[p:p+2], "little"); p += 2
            else:
                cl = (tag >> 2) + 1; co = int.from_bytes(src[p:p+4], "little"); p += 4
            for _ in range(cl): dst.append(dst[-co])
    return bytes(dst)

def snappy(data):
    out = bytearray(); p = 0
    while p + 4 <= len(data):
        t = data[p]; ln = int.from_bytes(data[p+1:p+4], "little"); p += 4
        out += snappy_block(data, p, ln) if t == 0 else data[p:p+ln]
        p += ln
    return bytes(out)

def load(path):
    objs = []
    with zipfile.ZipFile(path) as z:
        names = sorted(n for n in z.namelist() if n.endswith(".iwa"))
        names.sort(key=lambda n: (0 if "Document" in n else 5, n))
        for name in names:
            plain = snappy(z.read(name))
            p = 0
            while p < len(plain):
                ln, q = read_varint(plain, p, len(plain))
                if not ln: break
                info = parse(plain, q, ln); q += ln
                oid = info.get(1, [("v", 0)])[0][1]
                for _, mi in info.get(2, []):
                    m = parse(mi)
                    tp = m.get(1, [("v", 0)])[0][1]
                    bl = m.get(3, [("v", 0)])[0][1]
                    objs.append((oid, tp, parse(plain, q, bl), name.split("/")[-1]))
                    q += bl
                p = q
    return objs

def storages(objs):
    out = []
    for oid, tp, m, comp in objs:
        f3 = m.get(3)
        if not f3 or (4 not in m and 5 not in m): continue
        if any(k != "b" or txt(v) is None for k, v in f3): continue
        text = "".join(txt(v) for _, v in f3)
        if text: out.append((oid, comp, text))
    return out

def dec128(buf, off):
    lo, hi = struct.unpack_from("<QQ", buf, off)
    if (hi >> 61) & 3 == 3: return None
    exp = ((hi >> 49) & 0x3FFF) - 6176
    coeff = ((hi & 0x1FFFFFFFFFFFF) << 64) | lo
    if exp < -30 or exp > 30 or coeff > 10**20: return None
    d = float(coeff) * (10.0 ** exp)
    return -d if hi >> 63 else d

print("=" * 68)
print("■ sample.pages")
objs = load("sample.pages")
sts = sorted(storages(objs), key=lambda s: -len(s[2]))
print("  オブジェクト数:", len(objs), "/ テキストストレージ:", len(sts))
body = sts[0][2]
print("  本文段落数:", len(body.split("\n")))
for line in body.split("\n")[:4]: print("   ", line[:48])
print("  テキストボックス:", repr(sts[1][2][:24]))

print("=" * 68)
print("■ sample.key")
objs = load("sample.key")
by_comp = {}
for oid, comp, t in storages(objs): by_comp.setdefault(comp, []).append(t)
for comp in sorted(by_comp):
    ts = by_comp[comp]
    print("  %-16s タイトル=%s / 箇条書き %d 行" % (comp, ts[0][:22], len(ts[1].split("\n"))))

print("=" * 68)
print("■ sample.numbers")
objs = load("sample.numbers")
strings, tile = {}, None
for oid, tp, m, comp in objs:
    if tp == 6005:
        for _, e in m.get(3, []):
            em = parse(e)
            strings[em[1][0][1]] = txt(em[3][0][1])
    if tp == 6002: tile = m
print("  文字列テーブル:", len(strings), "件")
rows = []
for _, r in tile.get(5, []):
    rm = parse(r)
    idx = rm[1][0][1]; storage = rm[3][0][1]; offs = rm[4][0][1]
    offsets = [struct.unpack_from("<h", offs, i)[0] for i in range(0, len(offs), 2)]
    cells = []
    for c, start in enumerate(offsets):
        end = offsets[c+1] if c + 1 < len(offsets) else len(storage)
        ctype = storage[start+1]
        val = None
        if ctype == 3:
            val = strings.get(struct.unpack_from("<I", storage, start+4)[0])
        else:
            n = dec128(storage, start+4)
            if ctype == 5 and n is not None:
                val = (datetime.datetime(2001,1,1) + datetime.timedelta(seconds=n)).strftime("%Y-%m-%d")
            else:
                val = n
        cells.append(val)
    rows.append((idx, cells))
for idx, cells in sorted(rows):
    print("  行%d: %s" % (idx, cells))
print("=" * 68)
