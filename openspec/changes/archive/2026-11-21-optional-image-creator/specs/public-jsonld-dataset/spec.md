# Spec Delta

## MODIFIED Requirements

### Requirement: Publication image enrichment
公開distributionはシステム SHALL 各公開Place recordに、公開時に導出した`schema:image`を含めます。`schema:image` MUST `schema:ImageObject`の型で、`schema:contentUrl`にCommonsの直接URL、`schema:license`にライセンスを持ちます。作者が分かるとき`schema:creator` MUST `schema:Person`の型と作者名を持ちます。作者が不明なとき`schema:creator`を含んではなりません（MUST NOT）。`LicenseUrl`があるとき`schema:license` MUST そのURLであり、無いとき MUST ライセンス名の文字列です。

#### Scenario: Facility with an upstream image is published

- **WHEN** 公開対象の施設にWikidata P18、OSMの`File:`タグ、またはOSMの`Category:`タグに対応する画像があり、Commonsのメタデータが得られる
- **THEN** 公開recordは`schema:ImageObject`に直接URL、ライセンス、作者名を含む

#### Scenario: Facility with an unknown author is published

- **WHEN** 公開対象の施設の画像について、Commonsが作者を示さない、または作者欄がプレースホルダのみである
- **THEN** 公開recordは`schema:image`に直接URLとライセンスを含み、`schema:creator`を持たない

#### Scenario: Commons metadata is absent

- **WHEN** 取得済みのCommonsメタデータに該当ファイルがなく、取得も失敗している
- **THEN** システムは`schema:image`を持たない公開recordを生成し、公開を続ける

#### Scenario: Canonical record is inspected

- **WHEN** 正本`data/places.jsonld`のrecordを点検する
- **THEN** recordは`schema:image`を含まない
