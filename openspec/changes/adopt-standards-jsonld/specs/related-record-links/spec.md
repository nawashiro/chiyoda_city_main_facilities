# Spec Delta

## Purpose

自動照合した外部recordを同一性として断定せず、出典付き識別子とソース入力に存在する明示的な`dereferenceable URI`を、再利用者がたどれる関連情報として公開します。

## ADDED Requirements

### Requirement: Conservative related-record links
システム SHALL 自動照合したOSM、Wikidata、WAMの外部識別子を`schema:identifier`で出力します。
各`schema:identifier` MUST `schema:PropertyValue`として表現し、`propertyID`に`sourceId`、`value`に`recordId`を設定します。
システム SHALL ソース入力に明示された`dereferenceable URI`だけを`rdfs:seeAlso`で出力します。
システム MUST `recordId`から`rdfs:seeAlso`のURIを合成しません。
自動出力 MUST `schema:sameAs`、SKOS match関係、Place単位の`prov:wasDerivedFrom`を含みません。

#### Scenario: Automated OSM association is exported
- **WHEN** 施設とOSM recordの照合結果を公開し、ソース入力に`recordId`だけがあります
- **THEN** 出力は`schema:identifier`を`schema:PropertyValue`として表現し、`propertyID`に`sourceId`、`value`に`recordId`を設定して、`rdfs:seeAlso`を出力しません

#### Scenario: Explicit source URI is exported
- **WHEN** ソース入力に明示された`dereferenceable URI`を含む施設と外部recordの照合結果を公開します
- **THEN** 出力はそのURIだけを`rdfs:seeAlso`で表現し、`recordId`からURIを合成しません

### Requirement: WAM service distinction
システム MUST WAMのサービスrecordをPlaceの同一実体として扱いません。
システム MUST WAMの外部識別子を`schema:identifier`の`schema:PropertyValue`で表現し、`propertyID`に`sourceId`、`value`に`recordId`を設定します。
システム MUST WAMの`recordId`からIRIを合成しません。
システム MUST WAM由来の住所、サービス種別、電話番号を公開Placeへ出力しません。

#### Scenario: Multiple WAM services relate to one facility
- **WHEN** 一施設に複数のWAMサービスrecordがあります
- **THEN** 出力は施設recordを複製せず、各recordを`schema:identifier`の`schema:PropertyValue`で表現し、WAM IRIを`rdfs:seeAlso`へ合成しません
