# public-jsonld-dataset Specification

## Purpose

施設データを標準語彙のJSON-LDで公開し、既存UUIDを維持した施設識別子と緯度・経度を提供します。運用履歴を公開施設データから除外し、再利用者が施設と関連情報を取得できるようにします。

## Requirements

### Requirement: JSON-LD Place record
システム SHALL 各公開施設をJSON-LD recordとして出力します。
各record MUST 既存UUIDから作る`urn:uuid:`の`@id`を持ちます。
各record MUST `schema:Place`を型として持ちます。

#### Scenario: Existing facility is exported
- **WHEN** 有効な既存施設を公開します
- **THEN** UUIDを維持したJSON-LD Place recordを出力します

### Requirement: Standard spatial representation
システム SHALL Point座標をschema.orgで出力します。
record MUST `schema:geo`、`schema:GeoCoordinates`、`schema:latitude`、`schema:longitude`を使います。
record MUST GeoSPARQLのgeometry literalを含みません。

#### Scenario: Point geometry is exported
- **WHEN** 施設にPoint geometryがあります
- **THEN** 出力は追加のJSON parseなしで取得できる緯度と経度を含みます

### Requirement: Public record excludes operational history
公開Place record MUST 監査イベント、参照の履歴状態、更新時刻、LLM投票ログを含みません。

#### Scenario: Public record is inspected
- **WHEN** 利用者がJSON-LD Place recordを取得します
- **THEN** 運用履歴と投票ログを取得できません

### Requirement: Public record excludes derived and upstream-detail fields
公開Place record MUST 町名、電話番号、OSMタグ、独自`categoryIds`、rights文字列を含みません。
システム MUST town polygonから町名を導出しません。

#### Scenario: Public record is generated
- **WHEN** システムが公開Place recordを生成します
- **THEN** recordは町名、電話番号、OSMタグ、独自`categoryIds`、rights文字列を含みません

### Requirement: Explicit publication exclusion
システム SHALL 検索入力の`publish: false`を公開除外指定として扱います。
システム MUST この指定を持つ施設候補のPlace recordを公開JSON-LD distributionへ出力しません。

#### Scenario: Excluded facility is processed
- **WHEN** `publish: false`の検索入力から公開distributionを生成します
- **THEN** distributionはその施設のPlace recordを含みません

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
