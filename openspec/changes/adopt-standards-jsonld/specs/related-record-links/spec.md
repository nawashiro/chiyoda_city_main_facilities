# Spec Delta

## Purpose

自動照合した外部レコードを同一性として断定せず、再利用者がたどれる関連情報として公開します。

## ADDED Requirements

### Requirement: Conservative related-record links
システム SHALL 自動照合したOSM、Wikidata、WAMの関連先を`rdfs:seeAlso`で出力します。
自動出力 MUST `schema:sameAs`、SKOS match関係、Place単位の`prov:wasDerivedFrom`を含みません。

#### Scenario: Automated OSM association is exported
- **WHEN** 施設とOSM recordの照合結果を公開します
- **THEN** 出力は`rdfs:seeAlso`だけで関連先を表現します

### Requirement: WAM service distinction
システム MUST WAMのサービスrecordをPlaceの同一実体として扱いません。
WAM由来の住所とサービス種別を公開する場合、施設とサービスの区別を維持します。

#### Scenario: Multiple WAM services relate to one facility
- **WHEN** 一施設に複数のWAMサービスrecordがあります
- **THEN** 出力は施設recordを複製せず関連情報として扱います
