# Spec Delta

## ADDED Requirements

### Requirement: Association hold suspends category decisions

システム SHALL 関連付けを保留した施設のカテゴリ判断を取り消し、保留中は規則・Jevによるカテゴリ判断とカテゴリ確認Issueへの提示を行いません。システム MUST 保留の解除後に、確定した関連付けを根拠にカテゴリを再評価できるようにします。

#### Scenario: Hold withdraws the category decision

- **WHEN** 保守者が施設のOSM関連付けを保留として記録します
- **THEN** その施設のカテゴリ判断は取り消され、公開recordからgif-poi識別子が外れます

#### Scenario: Held facility is not presented

- **WHEN** カテゴリのない保留中の施設が残ります
- **THEN** システムはその施設をカテゴリ確認Issueに示しません

#### Scenario: Category is re-evaluated after the hold is lifted

- **WHEN** 保留を解除して関連付けを確定します
- **THEN** その施設は未決定施設としてカテゴリ再評価の対象に戻ります
