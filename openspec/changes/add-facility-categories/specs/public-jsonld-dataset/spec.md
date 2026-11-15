# Spec Delta

## MODIFIED Requirements

### Requirement: Public record excludes derived and upstream-detail fields
公開Place record MUST 町名、電話番号、OSMタグ、rights文字列を含みません。
システム MUST town polygonから町名を導出しません。
recordの分類 MUST `schema:additionalType`に語彙文書のterm URLを設定するだけであり、POIコードの値、日本語ラベル、判断のmethod、翻訳規則の根拠を含みません。

#### Scenario: Public record is generated

- **WHEN** システムが公開Place recordを生成します
- **THEN** recordは町名、電話番号、OSMタグ、rights文字列を含まず、分類はadditionalTypeのterm URLだけを持ちます

#### Scenario: Category values stay in the vocabulary document

- **WHEN** 利用者が公開recordのadditionalTypeを点検します
- **THEN** 値は語彙文書のterm URLのみであり、コードやラベルの複製を含みません

## ADDED Requirements

### Requirement: Place record category references
公開Place recordは、保存済みカテゴリ判断の数だけ `schema:additionalType` MUST 語彙文書のterm URLを持ちます。判断のないrecord MUST `schema:additionalType`を持ちません。term URLのfragment MUST GIF POIコードの4桁コードそのものです。

#### Scenario: Categorized facility is exported

- **WHEN** カテゴリ判断のある施設を公開します
- **THEN** recordの`schema:additionalType`に判断の数だけ語彙文書のterm URLが並びます

#### Scenario: Uncategorized facility is exported

- **WHEN** カテゴリ判断のない施設を公開します
- **THEN** recordは`schema:additionalType`を持ちません
