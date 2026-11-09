# osm-maintenance 変更（delta）

## MODIFIED Requirements

### Requirement: Durable evidence-bound human decisions

システム SHALL 人が選んだOSM IDを正本へ保存し、以後は既存参照として維持する。システム MUST 入力ハッシュだけで採用済みの接続を失効させない。人の「該当なし」と未解決のJev結果は同じ根拠では再利用し、根拠が変われば再評価する。取得日時や候補順だけの変化は根拠の変更とみなさない。

人が実地調査で確定した接続先 SHALL 専用CLIの`assoc`サブコマンドで記録・正本へ適用できる。システム SHALL OSM APIから指定された要素の実データを取得し、確認Issueと同じ`IDENTITY_TAGS`に基づく根拠を一つの候補として作る。システム MUST 取得できない要素を候補にせず、正本を変更しない。編集者と実行時刻 SHALL 人の判断として`human`へ記録する。

#### Scenario: Field-survey OSM ID is recorded as a human decision

- **WHEN** 保守者が`./fac assoc <query_id> --osm-id node/123 --editor <editor>`を実行する
- **THEN** システムはOSM APIから`node/123`の名称・座標・タグを取得し、候補一つの根拠を作って`method: human`の判断を判断記録へ保存し、`places.jsonld`の当該施設へ参照と座標を適用する

#### Scenario: Rejected candidates recur next month

- **WHEN** 人が「該当なし」と確定した施設と候補の判断根拠が翌月も同じである
- **THEN** システムは不採用を維持し、同じ確認Issueを新規作成しない

#### Scenario: Candidate evidence changes

- **WHEN** 人の「該当なし」の判断後に候補の名称、座標、QIDなど判断に使う情報が変わる
- **THEN** システムは古い判断をそのまま適用せず、現在の根拠で再評価する

#### Scenario: Element does not exist in OSM

- **WHEN** 指定されたOSM要素がOSM APIに存在しない
- **THEN** システムは判断記録と正本を変更せず失敗を報告する

#### Scenario: None choice is recorded

- **WHEN** 保守者が`--choice none`を指定する
- **THEN** システムは人による「該当なし」を判断記録へ保存し、当該施設のOSM参照を解除してUUIDと座標を残す

#### Scenario: Duplicate OSM allocation is rejected

- **WHEN** 指定した要素が別の施設に既に割り当てられている
- **THEN** システムは正本を変更せず失敗を報告する
