# Spec Delta

## ADDED Requirements

### Requirement: Association hold defers field survey

システム SHALL 実地調査を待つ施設のOSM関連付けを、理由・編集者・実行時刻つきの保留として`data/osm-decisions.json`に保存します。保留 MUST 専用CLIの`assoc --hold`で記録し、対象施設のOSM参照と照合由来のWikidata参照を解除して、施設UUIDと有効な座標を残します。システム MUST 保留中の施設を関連付けの再評価、Jev、確認Issueの対象にしません。保留 MUST 名称・タグ・候補の変化で失効せず、`assoc --osm-id`または`assoc --choice none`による人の確定でのみ解除します。

#### Scenario: Hold is recorded

- **WHEN** 保守者が`./fac assoc <query_id> --hold --reason <理由> --editor <editor>`を実行します
- **THEN** 判断記録に保留のエントリが理由・編集者・実行時刻つきで保存され、対象施設のOSM参照とWikidata参照が解除され、UUIDと座標が残ります

#### Scenario: Held facility is skipped by updates

- **WHEN** 月次更新または手動再実行が保留中の施設を含めて走ります
- **THEN** システムはその施設の関連付けを再評価せず、確認Issueにも提示しません

#### Scenario: Evidence changes do not lift the hold

- **WHEN** 保留中に候補、タグ、名称、取得結果が変わります
- **THEN** システムは保留を維持し、判断記録を変更しません

#### Scenario: Survey-confirmed association ends the hold

- **WHEN** 実地調査で接続先を確定した保守者が`./fac assoc <query_id> --osm-id <id> --editor <editor>`を実行します
- **THEN** 保留は人の判断に置き換わり、確定したOSM参照と座標が施設へ適用されます

#### Scenario: Human rejection ends the hold

- **WHEN** 保守者が保留中の施設に`./fac assoc <query_id> --choice none --editor <editor>`を実行します
- **THEN** 保留は人の「該当なし」の判断に置き換わり、施設は関連付けのない状態のまま公開されます

#### Scenario: Held facility is published without related references

- **WHEN** 保留中の施設を公開します
- **THEN** recordはUUIDと座標を持ち、OSM参照とWikidata参照を持ちません
