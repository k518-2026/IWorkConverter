# iWork Converter

実行ファイルのダウンロード.
https://github.com/k518-2026/IWorkConverter/releases

## 注意！
- 書式まで含めて完全に移行したい場合は、iWork 側の「書き出し」機能で Office 形式にするのが
確実です。本アプリは **Mac が手元にない環境で中身を取り出す** ことを目的としています。

Pages / Numbers / Keynote の書類を Windows 上で Office 形式に変換するデスクトップアプリです。
| 入力 | 出力 |
|---|---|
| `.pages` | `.docx` |
| `.numbers` | `.xlsx` |
| `.key` | `.pptx` |

- **WPF（C#）／ .NET 8**
- **NuGet パッケージ・外部 DLL は一切なし**（OOXML は `System.IO.Compression` で直接書き出し。
  UI も WPF 標準コントロールのカスタムテンプレートだけで組んでいます）
- Visual Studio 2022 で `IWorkConverter.sln` を開いて **F5** で実行できます

## 画面

- 左：ファイル一覧（種別バッジ・状態ピル・行ごとの削除）／空のときは点線のドロップゾーン
- 右：出力先と変換オプション（トグルスイッチ）
- 下：進捗バーと「変換を開始」。ログは折りたたみ式

スタイルは `src/IWorkConverter.App/Themes/Theme.xaml` にまとまっています。
配色を変えたいときは先頭のカラーパレット（`Brush.Accent` など）を差し替えてください。

---

## 使い方

1. `IWorkConverter.sln` を Visual Studio 2022（.NET 8 デスクトップ開発ワークロード）で開く
2. **スタートアッププロジェクトが `IWorkConverter.App` になっていることを確認**して F5

   `IWorkConverter.Core` はクラスライブラリなので、そちらが選ばれていると
   「クラス ライブラリの出力タイプを持つプロジェクトを直接起動することはできません」
   というエラーになります。その場合はソリューションエクスプローラーで
   `IWorkConverter.App` を右クリック →「スタートアップ プロジェクトに設定」を選んでください
   （プロジェクト名が太字になれば設定済みです）。
3. ウィンドウにファイルまたはフォルダをドラッグ＆ドロップ（複数一括可）
4. 必要なら出力先フォルダを指定して「変換を開始」

出力先が空欄のときは、元ファイルと同じ場所に保存します。

### オプション

| 項目 | 効果 |
|---|---|
| 見出しを推定する | Pages のスタイル名から見出し・タイトルを判定して Word のスタイルに割り当てる |
| テキストボックスの文字も取り込む | 本文以外の図形内テキストを文書末尾に追記する |
| 空のスライドを除外 | 本文が取れなかった Keynote のスライドを出力しない |
| 1 行目を見出しとして太字にする | Numbers の各表の 1 行目を太字にする |
| 同名ファイルを上書きする | オフのときは `名前 (2).docx` のように連番を付ける |

---

## プロジェクト構成

```
IWorkConverter.sln
└─ src/
   ├─ IWorkConverter.Core/          変換エンジン（UI 非依存・net8.0）
   │   ├─ Iwa/                      Snappy 展開・protobuf 解析・.iwa 読み込み
   │   ├─ Package/                  .pages/.numbers/.key（ZIP／フォルダ）の展開
   │   ├─ Extract/                  Pages / Numbers / Keynote の内容抽出
   │   ├─ Legacy/                   iWork '09（index.xml）形式の抽出
   │   ├─ Model/                    中間モデル（DocModel / BookModel / DeckModel）
   │   ├─ Ooxml/                    docx / xlsx / pptx の書き出し
   │   └─ ConversionService.cs      入口
   └─ IWorkConverter.App/           WPF の UI（net8.0-windows）
```

変換は **入力形式 → 中間モデル → OOXML** の 3 段階です。新しい入力形式や出力形式を足す場合は、
`Extract/` か `Ooxml/` に 1 クラス追加するだけで済みます。

---

## 内部でやっていること

iWork 2013 以降の書類は、次のような構造になっています。

```
書類.pages（ZIP）
└─ Index/
   ├─ Document.iwa
   ├─ DocumentStylesheet.iwa
   └─ …
```

`.iwa` は **Apple 独自フレーミングの Snappy** で圧縮された **protobuf** の列です。本アプリでは

1. `AppleSnappy` … `[0x00][長さ 3 バイト][Snappy ブロック]` のフレームを展開
2. `ProtoMessage` … `.proto` 定義なしで protobuf を汎用パース
3. `IwaArchive` … オブジェクト ID・型 ID・本体メッセージに分解
4. `Extract/*` … 構造の形から「本文」「表」「スライド」を特定

という順で読み解いています。

---

## 精度についての注意（重要）

**iWork の内部スキーマは Apple が公開していません。** 本アプリはファイル構造から内容を推定して
復元しているため、次の点は原理的に完全ではありません。

- **文字・段落・表の値・スライドの本文は高い確度で復元できます。**
- **書式（フォント、色、行間、図形、画像、グラフ、アニメーション）は引き継ぎません。**
- Numbers のセル格納バッファはレイアウトが非公開のため、
  文字列テーブルのキー照合と decimal128 / double の妥当性チェックによる **推定復元** です。
  数式は値としてではなく、計算済みの値または空として出力されます。
- Keynote のスライド順は、書類内の参照リストから推定します。取得できない場合は
  コンポーネント名の番号順になります。
- パスワード保護された書類は復号できません。
- iWork '09 以前の `index.xml` 形式は別ルートで処理します（こちらは仕様が公開されており安定します）。

書式まで含めて完全に移行したい場合は、iWork 側の「書き出し」機能で Office 形式にするのが
確実です。本アプリは **Mac が手元にない環境で中身を取り出す** ことを目的としています。

---

## 動作要件

- Windows 10 / 11
- .NET 8 デスクトップランタイム（Visual Studio でビルドする場合は SDK）
