# related-record-links Specification

## Purpose
自動照合した外部recordを同一性として断定せず、OSMとWikidataの公式resource URI、およびWAMの出典付き識別子を、再利用者がたどれる関連情報として公開します。

## Requirements

### Requirement: Conservative related-record links
システム SHALL 自動照合したOSM typed object IDとWikidata QIDを、公式resource URIによる`rdfs:seeAlso`で出力します。
システム SHALL WAMの外部識別子を`schema:identifier`で出力します。
WAMの`schema:identifier` MUST `schema:PropertyValue`として表現し、`propertyID`に`wam`、`value`にWAM record IDを設定します。
システム MUST WAM record IDから`rdfs:seeAlso`のURIを合成しません。
自動出力 MUST `schema:sameAs`、SKOS match関係、Place単位の`prov:wasDerivedFrom`を含みません。

#### Scenario: Automated OSM association is exported
- **WHEN** 施設とOSM recordの照合結果を公開します
- **THEN** 出力はそのtyped object IDに対応する公式OSM resource URIを`rdfs:seeAlso`で表現します

#### Scenario: Wikidata association is exported
- **WHEN** OSM照合済みrecordが直接のWikidata QIDを含みます
- **THEN** 出力はQIDに対応する公式Wikidata resource URIを`rdfs:seeAlso`で表現します

### Requirement: WAM service distinction
システム MUST WAMのサービスrecordをPlaceの同一実体として扱いません。
システム MUST WAMの外部識別子を`schema:identifier`の`schema:PropertyValue`で表現し、`propertyID`に`wam`、`value`に`recordId`を設定します。
システム MUST WAMの`recordId`からIRIを合成しません。
システム MUST WAM由来の住所、サービス種別、電話番号を公開Placeへ出力しません。

#### Scenario: Multiple WAM services relate to one facility
- **WHEN** 一施設に複数のWAMサービスrecordがあります
- **THEN** 出力は施設recordを複製せず、各recordを`schema:identifier`の`schema:PropertyValue`で表現し、WAM IRIを`rdfs:seeAlso`へ合成しません
