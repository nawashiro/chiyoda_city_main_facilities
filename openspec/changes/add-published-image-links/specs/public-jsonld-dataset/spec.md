# Spec Delta

## ADDED Requirements

### Requirement: Publication image enrichment
公開distributionはシステム SHALL 各公開Place recordに、公開時に導出した`schema:image`を含めます。`schema:image` MUST `schema:ImageObject`の型で、`schema:contentUrl`にCommonsの直接URL、`schema:license`にライセンス、`schema:creator`に作者名を持ちます。`LicenseUrl`があるとき`schema:license` MUST そのURLであり、無いとき MUST ライセンス名の文字列です。

#### Scenario: Facility with an upstream image is published

- **WHEN** 公開対象の施設にWikidata P18またはOSMの`File:`タグがあり、Commonsのメタデータが得られる
- **THEN** 公開recordは`schema:ImageObject`に直接URL、ライセンス、作者名を含む

#### Scenario: Commons metadata is absent

- **WHEN** 取得済みのCommonsメタデータに該当ファイルがなく、取得も失敗している
- **THEN** システムは`schema:image`を持たない公開recordを生成し、公開を続ける

#### Scenario: Canonical record is inspected

- **WHEN** 正本`data/places.jsonld`のrecordを点検する
- **THEN** recordは`schema:image`を含まない

### Requirement: Deterministic single image selection
システム SHALL 画像の選択を、取得物だけで決まるように行います。Wikidata P18を優先し、無いときはOSMの`wikimedia_commons`タグのうち`File:`で始まるものを使います。`Category:`タグはシステム MUST 画像の対象にしません。一つのrecord MUST 画像を高々一つにします。

#### Scenario: Both P18 and OSM tag exist

- **WHEN** 施設のWikidata entityにP18があり、OSM要素にも`File:`タグがある
- **THEN** 選択はP18で確定し、OSMタグは使わない

#### Scenario: Multiple P18 claims exist

- **WHEN** Wikidata entityに複数のP18がある
- **THEN** システムは先頭のP18を画像にする

#### Scenario: Only a category tag exists

- **WHEN** OSMタグが`Category:`のみで、P18がない
- **THEN** システムはその施設に`schema:image`を付けない

## MODIFIED Requirements

### Requirement: Public record excludes derived and upstream-detail fields
公開Place record MUST 町名、電話番号、OSMタグ、独自`categoryIds`、rights文字列を含みません。
システム MUST town polygonから町名を導出しません。

#### Scenario: Public record is generated
- **WHEN** システムが公開Place recordを生成します
- **THEN** recordは町名、電話番号、OSMタグ、独自`categoryIds`、rights文字列を含みません
