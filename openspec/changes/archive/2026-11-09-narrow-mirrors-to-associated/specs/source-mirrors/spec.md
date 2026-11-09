# source-mirrors Specification (Delta)

## Purpose

公開ミラーは places.jsonld に紐付けられたデータのみを Pages 配信し、調査用の広域抽出は非公開の imports に留める。

## MODIFIED Requirements

### Requirement: OSM mirror distribution
システム SHALL 月次 OSM 更新パイプラインの抽出物のうち、places.jsonld に OSM 紐付けが記録されている要素のみに基づき、OSM ミラー配布物を生成します。検索入力座標の近傍抽出や wikidata タグ一致で得られた未紐付け要素を、配布物に含めてはなりません（MUST NOT）。調査用の広域抽出物は `imports/openstreetmap/raw.json` として保持され、Pages 配信の対象ではありません。配布物 MUST 抽出された各 OSM 要素の `type`、`id`、座標値（node は `lon`/`lat`、way/relation は中心 `center`）と、該当要素が持つすべてのタグを含みます。配布物 MUST `site/mirrors/osm.json` として Pages 配信され、常に最新1版を保持します。

#### Scenario: Monthly pipeline refreshes the mirror
- **WHEN** 月次 `update-osm` パイプラインが新しい PBF から抽出を行う
- **THEN** 紐付け済み OSM 要素の更新内容が `site/mirrors/osm.json` に反映され、Pages に配信される

#### Scenario: Element tags are complete
- **WHEN** 配布物の要素が参照される
- **THEN** その要素が OpenStreetMap 上で持つすべてのタグを含む

#### Scenario: Unassociated elements are excluded
- **WHEN** 紐付けが存在しない OSM 要素（.restaurant など近傍抽出に由来するもの）が抽出物に含まれる
- **THEN** その要素は `site/mirrors/osm.json` に現れず、`imports/` 側に留まる

#### Scenario: New association appears in the next refresh
- **WHEN** OSM 紐付けが places.jsonld に新たに追加される
- **THEN** 次回の月次更新でその要素が `site/mirrors/osm.json` に現れる

### Requirement: Wikidata mirror distribution
システム SHALL places.jsonld が参照する Wikidata QID それぞれについて、entity JSON が持つ値をすべて（全 statements）取得し、Wikidata ミラー配布物として保持します。OSM タグの出典により一時的に発見された、紐付けのない QID を配布物に含めてはなりません（MUST NOT）。そのような QID の取得物は `imports/wikidata/raw.json` 側に留まります。Wikidata API への取得 MUST 50 QID 以下のリクエストに分割して行い、単一の大規模バルク取得に依存しません。システム MUST Wikidata 取得のメタ（取得日時・エンドポイント・応答 SHA256）を OSM の retrieval メタと同種の記録として残します。

#### Scenario: Wikidata mirror is retrieved with paging
- **WHEN** 月次パイプラインが Wikidata entity を取得する
- **THEN** entity は全 statements を含み、取得は複数リクエストに分割される

#### Scenario: Unassociated QIDs are excluded
- **WHEN** OSM タグから発見された、places.jsonld が参照しない QID が取得される
- **THEN** その entity は `site/mirrors/wikidata.json` に現れず、imports 側のみに保持される
