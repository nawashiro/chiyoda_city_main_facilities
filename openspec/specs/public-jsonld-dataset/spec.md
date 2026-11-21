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
公開Place record MUST 町名、電話番号、OSMタグ、rights文字列を含みません。
システム MUST town polygonから町名を導出しません。
recordの分類は`schema:keywords`が参照するカテゴリtermだけであり、日本語ラベル、判断のmethod、翻訳規則の根拠をrecordに含みません。

#### Scenario: Public record is generated

- **WHEN** システムが公開Place recordを生成します
- **THEN** recordは町名、電話番号、OSMタグ、rights文字列を含まず、分類はカテゴリtermへの`schema:keywords`だけを持ちます

#### Scenario: Labels stay in the name dictionary

- **WHEN** 利用者が公開recordの`schema:keywords`を点検します
- **THEN** 日本語ラベルはrecordに含まれず、参照先のカテゴリtermが持ちます

### Requirement: Self-contained dataset graph
公開JSON-LD文書は、地物のPlace record、カテゴリ語彙、record形状を一つの`@graph`に含め MUST 、カテゴリ語彙とrecord形状を別文書に公開しません（MUST NOT）。Place recordは`schema:Place`を型に持つノードだけです。カテゴリtermと形状はPlace recordではありません。

#### Scenario: Public document is fetched
- **WHEN** 利用者が公開JSON-LD文書を取得します
- **THEN** 利用者は同じ`@graph`からPlace record、カテゴリterm、record形状を取得できます

#### Scenario: Non-place node is inspected
- **WHEN** 利用者が`@graph`のカテゴリtermまたは形状ノードを点検します
- **THEN** そのノードはPlace recordとして扱われません

### Requirement: Category terms in the dataset graph
公開`@graph` MUST `schema:DefinedTermSet`を一つと、その語彙に採用したカテゴリごとの`schema:DefinedTerm`を含みます。各term MUST `urn:uuid:`の`@id`、人間用の`schema:name`、GIF-POIコードを表す`schema:identifier`の`schema:PropertyValue`（`propertyID`が`gif-poi`）を持ちます。term MUST HTTP URIのterm URLを持ちません（MUST NOT）。

#### Scenario: Category term is inspected
- **WHEN** 利用者が公開`@graph`のカテゴリtermを点検します
- **THEN** termはUUID、日本語の名前、GIF-POIコードを持ちます

#### Scenario: Category vocabulary has one set
- **WHEN** 利用者が公開`@graph`の`DefinedTermSet`を数えます
- **THEN** 一つだけ存在し、その`schema:hasDefinedTerm`から全termを辿れます

### Requirement: Place record category references
公開Place record MUST 保存済みカテゴリ判断の数だけ`schema:keywords`の値を持ち、各値 MUST `urn:uuid:`のカテゴリtermを参照します。判断のないrecord MUST `schema:keywords`を持ちません。Place record MUST `gif-poi`の`schema:identifier`を持ちません（MUST NOT）。

#### Scenario: Categorized facility is exported
- **WHEN** カテゴリ判断のある施設を公開します
- **THEN** recordの`schema:keywords`が判断の数だけカテゴリtermを参照します

#### Scenario: Uncategorized facility is exported
- **WHEN** カテゴリ判断のない施設を公開します
- **THEN** recordは`schema:keywords`を持ちません

#### Scenario: Place identifier is inspected
- **WHEN** 公開Place recordを点検します
- **THEN** recordは`gif-poi`の`schema:identifier`を持ちません

### Requirement: Explicit publication exclusion
システム SHALL 検索入力の`publish: false`を公開除外指定として扱います。
システム MUST この指定を持つ施設候補のPlace recordを公開JSON-LD distributionへ出力しません。

#### Scenario: Excluded facility is processed
- **WHEN** `publish: false`の検索入力から公開distributionを生成します
- **THEN** distributionはその施設のPlace recordを含みません

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

### Requirement: Machine-readable record shape
公開`@graph` MUST `schema:Place`を対象とするSHACLの`sh:NodeShape`を含みます。形状 MUST `schema:geo`、`schema:image`、`schema:keywords`、`rdfs:seeAlso`の必須・任意と値の型を表現します。`schema:image`の作者は任意であり、作者を出すときだけ`schema:name`を必須にします。

#### Scenario: Image creator optionality is read
- **WHEN** 利用者が形状の`schema:image`の`sh:property`を点検します
- **THEN** `schema:creator`は必須ではなく、`schema:creator`があるとき`schema:name`が必須であることが分かります

#### Scenario: Missing required property is detected
- **WHEN** 形状に適合しないPlace recordを検証します
- **THEN** 形状は必須プロパティの欠落または型の不一致を報告します

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
