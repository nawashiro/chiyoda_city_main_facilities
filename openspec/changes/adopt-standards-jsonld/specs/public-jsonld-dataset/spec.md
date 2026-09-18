# Spec Delta

## Purpose

施設を標準語彙のJSON-LDで公開し、内部履歴を出さずに他者が再利用できる正本を提供します。

## ADDED Requirements

### Requirement: JSON-LD Place record
システム SHALL 各公開施設をJSON-LD recordとして出力します。
各record MUST 既存UUIDから作る`urn:uuid:`の`@id`を持ちます。
各record MUST `schema:Place`と`geo:Feature`を型として持ちます。

#### Scenario: Existing facility is exported
- **WHEN** 有効な既存施設を公開します
- **THEN** UUIDを維持したJSON-LD Place recordを出力します

### Requirement: Standard spatial representation
システム SHALL Point geometryをGeoSPARQLで出力します。
geometry MUST `geo:hasGeometry`、`geo:asGeoJSON`、`geo:geoJSONLiteral`を使います。

#### Scenario: Point geometry is exported
- **WHEN** 施設にPoint geometryがあります
- **THEN** 出力は標準GeoSPARQL geometryを含みます

### Requirement: Public record excludes operational history
公開Place record MUST 監査イベント、参照の履歴状態、更新時刻、LLM投票ログを含みません。

#### Scenario: Public record is inspected
- **WHEN** 利用者がJSON-LD Place recordを取得します
- **THEN** 運用履歴と投票ログを取得できません

### Requirement: Non-public Place protection
システム MUST 非公開Placeを公開JSON-LD distributionへ出力しません。

#### Scenario: Non-public facility is processed
- **WHEN** 非公開状態の施設を公開distributionへ生成します
- **THEN** distributionはその施設のPlace recordを含みません
