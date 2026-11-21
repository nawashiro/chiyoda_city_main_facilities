# Spec Delta

## ADDED Requirements

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

### Requirement: Machine-readable record shape
公開`@graph` MUST `schema:Place`を対象とするSHACLの`sh:NodeShape`を含みます。形状 MUST `schema:geo`、`schema:image`、`schema:keywords`、`rdfs:seeAlso`の必須・任意と値の型を表現します。`schema:image`の作者は任意であり、作者を出すときだけ`schema:name`を必須にします。

#### Scenario: Image creator optionality is read
- **WHEN** 利用者が形状の`schema:image`の`sh:property`を点検します
- **THEN** `schema:creator`は必須ではなく、`schema:creator`があるとき`schema:name`が必須であることが分かります

#### Scenario: Missing required property is detected
- **WHEN** 形状に適合しないPlace recordを検証します
- **THEN** 形状は必須プロパティの欠落または型の不一致を報告します

## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Place record category identifiers
**Reason**: カテゴリは地物の属性として`schema:keywords`で参照し、GIF-POIコードはカテゴリtermの識別子に置く。place-levelの`gif-poi`識別子は同じ事実の重複になる。
**Migration**: 利用者は`schema:keywords`の参照先`schema:DefinedTerm`の`schema:identifier`からGIF-POIコードを取得する。Place recordの`gif-poi`識別子は削除される。
