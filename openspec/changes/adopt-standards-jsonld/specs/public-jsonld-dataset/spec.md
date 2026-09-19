# Spec Delta

## Purpose

施設を標準語彙のJSON-LDで公開し、内部履歴を出さずに他者が再利用できる正本を提供します。

## ADDED Requirements

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
公開Place record MUST 町名、電話番号、OSMタグ、独自`categoryIds`、画像、rights文字列を含みません。
システム MUST town polygonから町名を導出しません。

#### Scenario: Public record is generated
- **WHEN** システムが公開Place recordを生成します
- **THEN** recordは町名、電話番号、OSMタグ、独自`categoryIds`、画像、rights文字列を含みません

### Requirement: Explicit publication exclusion
システム SHALL 検索入力の`publish: false`を公開除外指定として扱います。
システム MUST この指定を持つ施設候補のPlace recordを公開JSON-LD distributionへ出力しません。

#### Scenario: Excluded facility is processed
- **WHEN** `publish: false`の検索入力から公開distributionを生成します
- **THEN** distributionはその施設のPlace recordを含みません
