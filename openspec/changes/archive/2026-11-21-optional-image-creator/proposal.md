# Proposal

## Why

公開JSON-LDの`schema:image`に、Commonsのプレースホルダ`Unknown author`が実在の作者名として、しかも二重に連結されたまま出ています（`Unknown authorUnknown author`）。原因はCommons APIの作者欄に含まれる非表示要素の文字列を作者名として取り出していることと、作者が不明なときにプレースホルダを`schema:Person`として公開していることです。画像自体は残し、作者が分からない画像は`schema:creator`を持たない形で公開します。

## What Changes

- Commonsの作者抽出で、非表示要素（`display:none`、`hidden`）の文字列を無視します。`Unknown author`など`{{unknown}}`由来のプレースホルダは作者なしとして扱います。
- 公開時の画像生成を、`schema:contentUrl`と`schema:license`だけで成立させ、作者が分かるときだけ`schema:creator`を付けます。
- `facility_data`の画像検証と`fac jsonld-validate`で、`schema:creator`を任意にします。あるときは`schema:Person`と非空の名前を要求します。
- `imports/commons/raw.json`を再取得し、該当ファイルの`artist`を`null`にします。
- 再取得したメタデータで公開画像は55枚になり、4件の画像が`creator`を持ちません。CC BYの作者不明画像も`creator`なしで公開されます。

## Capabilities

### New Capabilities

なし。

### Modified Capabilities

- `public-jsonld-dataset`: `Publication image enrichment`の`creator`要件を、作者が分かるときだけ持つ形に変えます。
- `source-mirrors`: `Commons license metadata extraction`の作者抽出に、非表示要素とプレースホルダの扱いを加えます。

## Impact

- コード: `src/commons_retrieval.py`、`src/facility_data.py`、`tests/test_commons_retrieval.py`、`tests/test_published_images.py`
- データ: `imports/commons/raw.json`（1ファイルの`artist`）、`site/places.jsonld`（ビルドで再生成）
- 仕様: `openspec/specs/public-jsonld-dataset`、`openspec/specs/source-mirrors`
- 公開物: 画像付きrecordが55になり、`creator`を持たない画像が4件になる
- 既知のリスク: 作者不明のCC BY画像を`creator`なしで公開するため、再利用者が作者表示を満たせない場合がある
