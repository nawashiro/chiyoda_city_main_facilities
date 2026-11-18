# Spec Delta

## MODIFIED Requirements

### Requirement: Publication image enrichment
公開distributionはシステム SHALL 各公開Place recordに、公開時に導出した`schema:image`を含めます。`schema:image` MUST `schema:ImageObject`の型で、`schema:contentUrl`にCommonsの直接URL、`schema:license`にライセンス、`schema:creator`に作者名を持ちます。`LicenseUrl`があるとき`schema:license` MUST そのURLであり、無いとき MUST ライセンス名の文字列です。

#### Scenario: Facility with an upstream image is published

- **WHEN** 公開対象の施設にWikidata P18、OSMの`File:`タグ、またはOSMの`Category:`タグに対応する画像があり、Commonsのメタデータが得られる
- **THEN** 公開recordは`schema:ImageObject`に直接URL、ライセンス、作者名を含む

#### Scenario: Commons metadata is absent

- **WHEN** 取得済みのCommonsメタデータに該当ファイルがなく、取得も失敗している
- **THEN** システムは`schema:image`を持たない公開recordを生成し、公開を続ける

#### Scenario: Canonical record is inspected

- **WHEN** 正本`data/places.jsonld`のrecordを点検する
- **THEN** recordは`schema:image`を含まない

### Requirement: Deterministic single image selection
システム SHALL 画像の選択を、取得物だけで決まるように行います。Wikidata P18を優先し、無いときはOSMの`wikimedia_commons`タグのうち`File:`で始まるものを使います。`Category:`タグのときは、`imports/commons/raw.json`に記録されたカテゴリ名からファイル名への対応を使います。一つのrecord MUST 画像を高々一つにします。

#### Scenario: Both P18 and OSM tag exist

- **WHEN** 施設のWikidata entityにP18があり、OSM要素にも`File:`タグがある
- **THEN** 選択はP18で確定し、OSMタグは使わない

#### Scenario: Both P18 and a category tag exist

- **WHEN** 施設のWikidata entityにP18があり、OSM要素にも`Category:`タグがある
- **THEN** 選択はP18で確定し、カテゴリの代表画像は使わない

#### Scenario: Multiple P18 claims exist

- **WHEN** Wikidata entityに複数のP18がある
- **THEN** システムは先頭のP18を画像にする

#### Scenario: Only a category tag exists

- **WHEN** OSMタグが`Category:`のみで、P18がなく、対応するファイルのメタデータが得られる
- **THEN** システムはそのファイルを`schema:image`に使う

#### Scenario: Category image metadata is insufficient

- **WHEN** OSMタグが`Category:`のみで、P18がなく、対応するファイルがない、またはメタデータが不完全
- **THEN** システムはその施設に`schema:image`を付けない
