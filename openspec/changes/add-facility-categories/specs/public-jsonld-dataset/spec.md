# Spec Delta

## MODIFIED Requirements

### Requirement: Public record excludes derived and upstream-detail fields
公開Place record MUST 町名、電話番号、OSMタグ、rights文字列を含みません。
システム MUST town polygonから町名を導出しません。
recordの分類は `schema:identifier` の `schema:PropertyValue`（`propertyID`が`gif-poi`）だけであり、日本語ラベル、判断のmethod、翻訳規則の根拠を含みません。

#### Scenario: Public record is generated

- **WHEN** システムが公開Place recordを生成します
- **THEN** recordは町名、電話番号、OSMタグ、rights文字列を含まず、分類はgif-poi識別子だけを持ちます

#### Scenario: Labels stay in the name dictionary

- **WHEN** 利用者が公開recordのgif-poi識別子を点検します
- **THEN** 日本語ラベルはrecordに含まれず、名前辞書が持ちます

## ADDED Requirements

### Requirement: Place record category identifiers
公開Place recordは、保存済みカテゴリ判断の数だけ `schema:identifier` の `schema:PropertyValue`（`propertyID`が`gif-poi`、`value`が4桁POIコード） MUST 持ちます。判断のないrecord MUST gif-poi識別子を持ちません。公開Place record MUST 分類を `schema:additionalType` に持ちません（MUST NOT）。

#### Scenario: Categorized facility is exported

- **WHEN** カテゴリ判断のある施設を公開します
- **THEN** recordの`schema:identifier`に判断の数だけgif-poiの`PropertyValue`が並びます

#### Scenario: Uncategorized facility is exported

- **WHEN** カテゴリ判断のない施設を公開します
- **THEN** recordはgif-poi識別子を持ちません

#### Scenario: Additional type is inspected

- **WHEN** 公開Place recordを点検します
- **THEN** 分類の`schema:additionalType`は含まれません
