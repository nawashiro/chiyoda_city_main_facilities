# Spec Delta

## Purpose

公開Placeへ、バリアフリー観点で作られた第三者案内ページ（言葉の道案内、東京バリアフリーマップ）へのリンクを `schema:subjectOf` に公開します。対応付けは実施者（bot）が判断し、正しさは人の訂正ループで担保します。リンク掲載のみで、ソースの本文データは取り込みません。

## ADDED Requirements

### Requirement: Verified webpage link association

システム SHALL 検証済みの案内ページURLを、対象Placeの `schema:subjectOf` に `schema:WebPage`（`schema:url`、`schema:name`、`schema:provider` を含む）として記録する。対応付けの実施者はbotであり、人が施設単位でないページや誤対応を指摘した場合、システム SHALL その訂正を解除と再入力で反映する。実行時の自動照合 MUST 行わない。リンク先の許容ドメイン SHALL `walkingnavi.com` と `lwd.tokyo` に限定する。

#### Scenario: Link is recorded for a facility

- **WHEN** 施行者が施設の案内ページURLを対応付けとして記録する
- **THEN** 対象Placeにソース名を `schema:provider` に持つ `schema:WebPage` が `schema:subjectOf` に記録される

#### Scenario: Disallowed domain is rejected

- **WHEN** 許容ドメイン外のURLを対応付けしようとする
- **THEN** システムはその入力を拒否し、データを変更しない

### Requirement: Published export carries webpage links

システム SHALL `subjectOf` を持つPlaceを公開JSON-LDへ `schema:subjectOf` として出力する。対応付けの解除 SHALL 対象Placeから該当する `schema:WebPage` を除去する。システム MUST `rdfs:seeAlso` の要件（公式OSM/Wikidata URIのみ）を変更しない。

#### Scenario: Linked facility is published

- **WHEN** `subjectOf` を持つPlaceの公開JSON-LDを生成する
- **THEN** 出力は該当する `schema:WebPage` を `schema:subjectOf` に含む

#### Scenario: Link removal clears without side effects

- **WHEN** 訂正のために対応付けを解除する
- **THEN** 該当する `schema:WebPage` が除去され、施設UUIDと `rdfs:seeAlso` は維持される

#### Scenario: Human correction is applied

- **WHEN** 人が対応付けの誤りを指摘する
- **THEN** 該当リンクが解除され、訂正後のURLが再記録され、検証が通る
