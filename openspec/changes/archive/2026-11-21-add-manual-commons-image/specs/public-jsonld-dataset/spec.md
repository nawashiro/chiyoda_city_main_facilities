# Spec Delta

## MODIFIED Requirements

### Requirement: Publication image enrichment
公開distributionはシステム SHALL 各公開Place recordに、公開時に導出した`schema:image`を含めます。`schema:image` MUST `schema:ImageObject`の型で、`schema:contentUrl`にCommonsの直接URL、`schema:license`にライセンスを持ちます。作者が分かるとき`schema:creator` MUST `schema:Person`の型と作者名を持ちます。作者が不明なとき`schema:creator`を含んではなりません（MUST NOT）。`LicenseUrl`があるとき`schema:license` MUST そのURLであり、無いとき MUST ライセンス名の文字列です。

#### Scenario: Facility with an upstream image is published

- **WHEN** 公開対象の施設に手動参照、Wikidata P18、OSMの`File:`タグ、またはOSMの`Category:`タグに対応する画像があり、Commonsのメタデータが得られる
- **THEN** 公開recordは`schema:ImageObject`に直接URL、ライセンス、作者名を含む

#### Scenario: Facility with an unknown author is published

- **WHEN** 公開対象の施設の画像について、Commonsが作者を示さない、または作者欄がプレースホルダのみである
- **THEN** 公開recordは`schema:image`に直接URLとライセンスを含み、`schema:creator`を持たない

#### Scenario: Commons metadata is absent

- **WHEN** 取得済みのCommonsメタデータに該当ファイルがなく、取得も失敗している
- **THEN** システムは`schema:image`を持たない公開recordを生成し、公開を続ける

#### Scenario: Canonical record is inspected

- **WHEN** 正本`data/places.jsonld`のrecordを点検する
- **THEN** recordの`schema:image`はCommonsファイルページを指す`@id`だけを持ち、直接URL、ライセンス、作者を含まない

### Requirement: Deterministic single image selection
システム SHALL 画像の選択を、正本の手動参照と取得物だけで決まるように行います。正本に対象施設のCommonsファイルページ参照があるとき MUST そのファイルを使います。無いときはWikidata P18を優先し、無いときはOSMの`wikimedia_commons`タグのうち`File:`で始まるものを使います。`Category:`タグのときは、`imports/commons/raw.json`に記録されたカテゴリ名からファイル名への対応を使います。手動参照のファイルメタデータが得られないとき MUST 他の候補へフォールバックせず、その施設に`schema:image`を付けません。一つのrecord MUST 画像を高々一つにします。

#### Scenario: Manual reference wins over P18 and OSM tags

- **WHEN** 正本に対象施設のCommonsファイルページ参照があり、Wikidata P18とOSMの`File:`タグが別のファイルを指す
- **THEN** 選択は手動参照のファイルで確定し、P18とOSMタグは使わない

#### Scenario: Manual reference metadata is missing

- **WHEN** 正本に対象施設のCommonsファイルページ参照があるが、取得済みのCommonsメタデータにそのファイルがない、またはライセンスが不完全である
- **THEN** システムはP18、OSMの`File:`タグ、`Category:`タグへフォールバックせず、その施設に`schema:image`を付けず、ビルドで警告を報告する

#### Scenario: Manual reference is cleared

- **WHEN** 正本から手動参照が外れる
- **THEN** 次のビルドはP18、OSMの`File:`タグ、`Category:`タグによる自動選択を使う

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

## ADDED Requirements

### Requirement: Canonical Commons image reference
正本`data/places.jsonld`のPlace record MAY `schema:image`にCommonsファイルページのIRI参照を一つだけ持ちます。参照 MUST `{"@id": "https://commons.wikimedia.org/wiki/File:..."}`の形で、直接URL、ライセンス、作者、その他のフィールドを含みません（MUST NOT）。システム MUST この参照を公開recordの`schema:ImageObject`へ解決します。メタデータが得られないとき、公開recordは`schema:image`を持ちません。

#### Scenario: Derived image object is rejected in the canonical record

- **WHEN** 正本の`schema:image`が`schema:contentUrl`、`schema:license`、または`schema:creator`を持つ
- **THEN** 正本の検証はそのrecordを拒否する

#### Scenario: Non-Commons reference is rejected

- **WHEN** 正本の`schema:image`の`@id`がCommonsファイルページ以外を指す、または`Category:`を指す
- **THEN** 正本の検証はそのrecordを拒否する

#### Scenario: Manual reference survives an association change

- **WHEN** 施設のOSM関連付けが置換される
- **THEN** 施設のUUIDと`schema:image`の手動参照は維持される

#### Scenario: Manual reference is removed

- **WHEN** 手動参照を外す操作の後
- **THEN** 正本のrecordは`schema:image`を持たず、次のビルドは自動選択を使う
