# Spec Delta

## ADDED Requirements

### Requirement: Commons license metadata extraction
システム SHALL 月次パイプラインで、紐付け済み要素から集めたCommonsのファイル名それぞれについて、Commons APIから直接URL、ライセンス、作者を取得し、`imports/commons/raw.json`に保持します。ファイル名の収集 SHALL Wikidata P18とOSMの`File:`タグに由来し、紐付け集合の要素に限定します。抽出物 MUST Pages配信の対象にしません。システム MUST 取得メタ（取得日時・エンドポイント・応答SHA256）を既存のretrievalメタと同種の記録として残します。

#### Scenario: Monthly pipeline refreshes the metadata

- **WHEN** 月次`update-osm`パイプラインが走る
- **THEN** 紐付け済み要素に由来するファイルのメタデータが`imports/commons/raw.json`に保存される

#### Scenario: Unassociated files are excluded

- **WHEN** 紐付けが存在しない要素が参照するファイル名が集められる
- **THEN** そのファイルは`imports/commons/raw.json`の対象にならない

#### Scenario: Extraction stays outside the published mirrors

- **WHEN** `site/mirrors/`の配布物が点検される
- **THEN** Commonsのメタデータ抽出物は配布物の外の`imports/commons/`に留まる

## MODIFIED Requirements

### Requirement: Retrieval failure does not block publication
システム SHALL Wikidata ミラーと Commons メタデータの更新失敗時に OSM 関係の月次更新と Pages 公開を継続します。
Wikidata 取得と Commons 取得は付加的であり、その失敗が process job を失敗させてはなりません（MUST NOT）。

#### Scenario: Wikidata endpoint unreachable
- **WHEN** 月次パイプラインが走ったが Wikidata API が応答しない
- **THEN** OSM 側の更新と Pages 公開は完了する

#### Scenario: Commons endpoint unreachable
- **WHEN** 月次パイプラインが走ったが Commons API が応答しない
- **THEN** OSM 側の更新と Pages 公開は完了する
