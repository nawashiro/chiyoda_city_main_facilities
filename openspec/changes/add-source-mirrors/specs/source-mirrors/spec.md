# Spec Delta

## Purpose

OSM と Wikidata の Raw ミラーを月次パイプラインで更新し、常に最新1版を Pages 配信します。third-party 元データの抽出物・取得物を配布物として公開し、該当 ID の持つ値をすべて提供します。

## ADDED Requirements

### Requirement: OSM mirror distribution
システム SHALL 月次 OSM 更新パイプラインの抽出物に基づき、OSM ミラー配布物を生成します。
配布物 MUST 抽出された各 OSM 要素の `type`、`id`、座標値（node は `lon`/`lat`、way/relation は中心 `center`）と、該当要素が持つすべてのタグを含みます。
配布物 MUST `site/mirrors/osm.json` として Pages 配信され、常に最新1版を保持します。

#### Scenario: Monthly pipeline refreshes the mirror
- **WHEN** 月次 `update-osm` パイプラインが新しい PBF から抽出を行う
- **THEN** 更新内容が `site/mirrors/osm.json` に反映され、Pages に配信される

#### Scenario: Element tags are complete
- **WHEN** 配布物の要素が参照される
- **THEN** その要素が OpenStreetMap 上で持つすべてのタグを含む

### Requirement: Wikidata mirror distribution
システム SHALL 同定された Wikidata QID それぞれについて、entity JSON が持つ値をすべて（全 statements）取得し、Wikidata ミラー配布物として保持します。
Wikidata API への取得 MUST 50 QID 以下のリクエストに分割して行い、単一の大規模バルク取得に依存しません。
システム MUST Wikidata 取得のメタ（取得日時・エンドポイント・応答 SHA256）を OSM の retrieval メタと同種の記録として残します。

#### Scenario: Wikidata mirror is retrieved with paging
- **WHEN** 月次パイプラインが Wikidata entity を取得する
- **THEN** entity は全 statements を含み、取得は複数リクエストに分割される

### Requirement: Separate license files per source
システム SHALL OSM 由来の配布物と Wikidata 由来の配布物を、別ファイルとして分けて保持します。
システム MUST ODbL（OSM）と CC0（Wikidata）をそれぞれ配布物側で区別して明示します。

#### Scenario: Mirror files are inspected
- **WHEN** ミラー配布物のファイル群を確認する
- **THEN** OSM ミラーと Wikidata ミラーが別ファイルであり、混合配布物としての単一 CC0 表示になっていない

### Requirement: Retrieval failure does not block publication
システム SHALL Wikidata ミラーの更新失敗時に OSM 関係の月次更新と Pages 公開を継続します。
Wikidata 取得は付加的であり、その失敗が process job を失敗させてはなりません（MUST NOT）。

#### Scenario: Wikidata endpoint unreachable
- **WHEN** 月次パイプラインが走ったが Wikidata API が応答しない
- **THEN** OSM 側の更新と Pages 公開は完了する
