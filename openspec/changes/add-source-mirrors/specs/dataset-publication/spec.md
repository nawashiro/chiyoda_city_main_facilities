# Spec Delta

## ADDED Requirements

### Requirement: Source mirror distributions on the landing page
landing page MUST OSM ミラー配布物と Wikidata ミラー配布物を、それぞれ個別の `DataDownload` として表現します。
各 `DataDownload` MUST `contentUrl` と `encodingFormat` を含みます。
landing page MUST OSM 配布物に ODbL を、Wikidata 配布物に CC0 を、配布物単位で対応づけて明示します。

#### Scenario: A visitor selects a mirror distribution
- **WHEN** 利用者が landing page を開く
- **THEN** OSM ミラーと Wikidata ミラーの取得 URL と、それぞれのライセンスを確認できる

#### Scenario: Licenses stay separated
- **WHEN** landing page の Dataset metadata を検査する
- **THEN** ミラー各配布物が、dataset 全体を CC0 と表示する記述を持たず、個別のライセンスを参照する
