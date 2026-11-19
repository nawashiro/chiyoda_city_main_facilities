# Design

## Context

語彙文書`data/category-names.jsonld`は22コードを持ち、各termの名前はGIF v2.4の項目名の写しです。公開recordは`gif-poi`の4桁コードだけを運び、名前は辞書を引いた利用者だけが見ます。辞書の検証は構造だけで、名前と原典の一致は検査していません。背景は`proposal.md`を参照してください。

## Goals / Non-Goals

**Goals:**

- 辞書の名前を、GIFの分類を指す表示名として人が決められるようにする
- 1402の表示名を、託児所を含む分類だと読める語に変える
- コードによる結合と既存の判断記録を変えない

**Non-Goals:**

- 語彙のコードの追加・削除
- 辞書への説明文や出典の追加
- 名前とGIF項目名の一致を機械的に検査する仕組み
- 消費側の表示ロジックの変更

## Decisions

### The label is a display name anchored to the GIF class

termの名前はGIFの項目名の写しではなく、コードが指す分類を説明する表示名にします。GIFの分類名は分類の代表形に引きずられ、1402のように解説より狭く読める場合があります。表示名を人の裁量に置けば、収録施設の実態を辞書で伝えられます。範囲はGIFの解説が定め、表示名はその範囲を変えません。コードは変わらないため、辞書と原典の対応は採用版の表で辿れます。

代替案は3つ検討しました。ラベルをGIFのままにする案は誤解が残ります。説明文を辞書に足す案は、辞書が名前だけを持つという契約と、termが名前だけを持つ構造を崩します。表示名を別フィールドで持つ案は、同じtermに2つの名前ができて管理が二重になります。

### 1402 is displayed as 保育所・託児所

GIFの解説は1402に保育園・保育所・託児所を含めています。保育所は保育園の通称も受けるため、保育所と託児所の2語で範囲を表せます。保育所だけでは託児所が落ち、この施設が1402に該当する理由が表示名から読めません。保育所等は範囲が読み取れません。

### Names stay editorial, not generated

表示名は語彙文書の編集で決め、翻訳規則やJevでは生成しません。規則はコードを決めるもので、名前はコードと独立した辞書の内容です。表示名の変更はPRのレビューで確認します。

### Provenance stays at the dataset level

辞書にGIFへの参照を入れない契約は維持します。表示名が原典の項目名と異なることは、`docs/reference/sources-and-licenses.md`の加工内容に記します。CC0なので翻案は自由で、帰属の追加は要りません。

### The site copy follows the build

`site/category-names.jsonld`は`build_repository`が`data/category-names.jsonld`のバイト列を複製します。手で編集せず、ビルドで追随させます。Releaseの`category-names-<版>.jsonld`も同じ経路です。

## Risks / Trade-offs

- [表示名が原典から離れ、辞書とGIFの突合が手作業になる] → コードは変えず、採用版の表をdocsで固定して対応を辿れるようにする
- [表示名の裁量が広がり、分類の意味が変わる] → 表示名が分類の範囲を変えないことをspecで規定し、変更をPRでレビューする
- [利用者が表示名の変化に気づかない] → `gif-poi`コードは不変で、名前は辞書の更新として届く。recordの変更はない

## Migration Plan

1. `data/category-names.jsonld`の1402の表示名を変える
2. `docs/reference/sources-and-licenses.md`の出典と加工内容を合わせる
3. `python3 -m src.facility_data build .`で`site/category-names.jsonld`を追随させる
4. テストとリポジトリ検証を通す

ロールバックは表示名と文書を戻して再ビルドするだけで済みます。判断記録と公開recordは変わりません。
