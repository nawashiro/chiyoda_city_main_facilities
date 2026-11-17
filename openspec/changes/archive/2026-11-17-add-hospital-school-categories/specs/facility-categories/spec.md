# Spec Delta

## ADDED Requirements

### Requirement: Category maintenance follows the OSM update

システム SHALL 月次更新および手動再実行の完了時に、語彙`data/category-names.jsonld`と規則`data/category-rules.json`が存在する場合、未決定および関連付けが変わった施設のカテゴリを再評価します。カテゴリ再評価の対象 MUST OSM関連付けのある施設に限ります。システム MUST 関連付け済みでカテゴリを確定できない施設をカテゴリ確認Issueに提示します。語彙または規則がない場合、システム MUST カテゴリ処理を省略し、OSM更新を継続します。

#### Scenario: Monthly update decides a category

- **WHEN** 月次更新で未分類施設のOSM関連付けが確定する
- **THEN** システムは規則またはJevでカテゴリ判断を記録し、公開recordにgif-poi識別子を適用します

#### Scenario: Unassociated facility is not auto-classified

- **WHEN** 施設にOSM関連付けがない
- **THEN** システムは規則とJevでカテゴリを決めず、未分類のまま保ちます

#### Scenario: Unresolved category is presented

- **WHEN** カテゴリを確定できない施設が残る
- **THEN** システムはその施設をカテゴリ確認Issueに示し、未分類のまま保ちます

#### Scenario: Vocabulary or rules are absent

- **WHEN** 語彙または規則が存在しない
- **THEN** システムはカテゴリ処理を省略し、OSM更新を成功させます

#### Scenario: Category maintenance fails

- **WHEN** カテゴリ判断が認証・通信エラーで失敗する
- **THEN** システムは更新全体を失敗として報告し、未検証の判断を公開しません
