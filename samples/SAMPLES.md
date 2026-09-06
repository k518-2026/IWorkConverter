# 動作確認用サンプルファイル

`sample.pages` / `sample.numbers` / `sample.key` をアプリのウィンドウにドラッグ＆ドロップして
「変換を開始」を押すと、同じフォルダに `.docx` / `.xlsx` / `.pptx` が出力されます。

| ファイル | 形式 | 通る経路 |
|---|---|---|
| `sample.pages` | iWork 2013 以降（Index/*.iwa） | Snappy 展開 → protobuf 解析 → `PagesExtractor` |
| `sample.numbers` | 同上 | 同上 → `NumbersExtractor`（タイル＋文字列テーブル） |
| `sample.key` | 同上 | 同上 → `KeynoteExtractor`（スライド順の推定を含む） |
| `sample-iwork09.pages` | iWork '09（index.xml） | `LegacyXmlExtractor.ExtractPages` |
| `sample-iwork09.numbers` | 同上 | `LegacyXmlExtractor.ExtractNumbers` |
| `sample-iwork09.key` | 同上 | `LegacyXmlExtractor.ExtractKeynote` |

---

## 期待される変換結果

### sample.pages → sample.docx

- 段落 **14 個**、うちタイトル 1・見出し 1 が 4・キャプション 1
- 1 行目「iWork Converter 動作確認用サンプル」が **Title スタイル**
- 「箇条書きの確認」以下の 3 行が **箇条書き**（先頭の `•` とタブが取れて Word の行頭記号になる）
- 「1.」「2.」「3.」の 3 行が **番号付きリスト**
- 「テキストボックスの文字も取り込む」を ON にすると、末尾に
  「［テキストボックス・図形内のテキスト］」という見出しと 2 行が追加される
  （OFF なら追加されない ← このオプションの確認用）

### sample.numbers → sample.xlsx

シート名 **「売上サンプル」**、6 行 × 4 列。

| 商品 | 数量 | 単価 | 納品日 |
|---|---|---|---|
| りんご | 120 | 198 | 2026-04-06 |
| みかん | 85 | 125 | 2026-04-13 |
| ぶどう | 43 | 540 | 2026-04-20 |
| もも | 67 | 380 | 2026-04-27 |
| 合計 | 315 | 1243 | ― |

確認ポイント:

- **数値が数値として**（文字列ではなく）入っているか — セルを選んで合計が出るか
- **納品日が日付書式**で表示されるか（`decimal128` → 2001-01-01 起点の秒数 → 日付の経路）
- 1 行目が太字になるか（「1 行目を見出しとして太字にする」ON のとき）

### sample.key → sample.pptx

スライド 3 枚。**この順番で並ぶこと**が確認ポイントです（順序は書類内の参照リストから推定するため）。

1. 「iWork Converter サンプル」 — 箇条書き 3 行
2. 「読み取れるもの」 — 箇条書き 3 行
3. 「読み取れないもの」 — 箇条書き 3 行

### iWork '09 版

- `sample-iwork09.pages` … 段落 7 個。ログに「iWork '09 形式（index.xml）として読み込みました。」と出る
- `sample-iwork09.numbers` … 表「旧形式の表」4 行 × 3 列（人口の 31.7 が小数のまま入るか）
- `sample-iwork09.key` … スライド 2 枚

---

## サンプルの作り方・作り直し方

`tools/make_samples.py`（Python 3、標準ライブラリのみ）が生成スクリプトです。

```
python3 tools/make_samples.py     # サンプルを生成
python3 tools/verify_samples.py   # C# 側と同じ手順で読み直して内容を表示
```

`make_samples.py` には、`.iwa` を書き出すために必要な最小限の実装
（リテラルのみの Snappy 符号化・protobuf の書き出し・decimal128 の符号化）が入っています。
表の中身や段落を書き換えて別のパターンを試したいときは、`build_pages()` /
`build_numbers()` / `build_keynote()` の中の配列を編集してください。

---

## 重要な注意

これらのサンプルは **Apple の iWork で作成したものではなく、本アプリのリーダーが想定している
構造どおりにスクリプトで組み立てたもの**です。

そのため、

- ✅ Snappy 展開・protobuf 解析・タイル復号・OOXML 書き出しといった **各段の実装が壊れていないか**の確認には使えます
- ❌ **Apple の実ファイルと構造が一致しているかの検証にはなりません**（内部スキーマが非公開のため、
  想定そのものが間違っている可能性は、このサンプルでは検出できません）

実際の精度を確かめるには、Pages / Numbers / Keynote で保存した本物のファイルで試すのが確実です。
結果がおかしい場合は、そのファイルの特徴（表の数、日付や数式の有無、スライド枚数など）を
教えていただければ、`Extract/` のヒューリスティックを調整します。
