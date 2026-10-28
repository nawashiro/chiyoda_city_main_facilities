# Spec Delta

## Purpose

登録済み施設についてOSMの月次更新と確定済みデータの公開を継続し、自動で確定できない関連付けだけを人へ通知する。人の判断を再利用し、判断待ちや取得失敗によって古い回答を誤反映することを防ぐ。

## ADDED Requirements

### Requirement: Monthly maintenance of registered facilities

システム SHALL GitHub Actionsで毎月OSMを取得し、登録済み施設を更新する。システム SHALL 同じ処理を手動で再実行できる。システム MUST 取得結果だけを理由に施設を追加・削除せず、既存UUIDと明示的な公開除外指定を維持する。

#### Scenario: Scheduled update runs

- **WHEN** 月次の実行時刻になる
- **THEN** システムは登録済み施設のOSM更新を人の起動操作なしに開始する

#### Scenario: Source contains an unregistered facility

- **WHEN** 取得したOSMに未登録施設が含まれる
- **THEN** システムはその施設を公開対象に追加しない

### Requirement: Deterministic association precedes Jev

システム SHALL 現在の取得条件で得た結果に型を含む既存OSM IDがあれば既存参照を継続する。名称・座標・タグ・QIDや入力ハッシュの変化だけでは再審査しない。これで確定できなければ一意なQID一致を適用し、残る候補をJevで判定する。システム MUST 名称と近接座標だけで一致を自動確定しない。

#### Scenario: Previous typed object remains valid

- **WHEN** 前回の`way/123`が今回の取得結果にも存在するが、名称・座標・QIDが変わっている
- **THEN** システムはJevを呼び出さず参照を継続する

#### Scenario: Object number exists with another type

- **WHEN** 前回の`way/123`がなく、`node/123`だけが存在する
- **THEN** システムはそれを既存参照の継続として扱わない

#### Scenario: QID uniquely identifies a candidate

- **WHEN** 既存参照で確定できず、検索対象のQIDと一致する候補が一つある
- **THEN** システムはその候補をQID一致で確定する

#### Scenario: Nearby name match remains

- **WHEN** 一意なQID一致がなく、名称の似た候補が50m以内に一つある
- **THEN** システムは名称と距離で確定せずJevへ判定を求める

### Requirement: Durable evidence-bound human decisions

システム SHALL 人が選んだOSM IDを正本へ保存し、以後は既存参照として維持する。システム MUST 入力ハッシュだけで採用済みの接続を失効させない。人の「該当なし」と未解決のJev結果は同じ根拠では再利用し、根拠が変われば再評価する。取得日時や候補順だけの変化は根拠の変更とみなさない。

#### Scenario: Rejected candidates recur next month

- **WHEN** 人が「該当なし」と確定した施設と候補の判断根拠が翌月も同じである
- **THEN** システムは不採用を維持し、同じ確認Issueを新規作成しない

#### Scenario: Candidate evidence changes

- **WHEN** 人の「該当なし」の判断後に候補の名称、座標、QIDなど判断に使う情報が変わる
- **THEN** システムは古い判断をそのまま適用せず、現在の根拠で再評価する

### Requirement: Unresolved facilities do not block resolved updates

システム SHALL 検証済みの確定分を、他施設の人手判断を待たず正本へ反映する。未確定施設は直前の公開状態を保ち、判断待ちであることを確認Issueに示す。システム MUST 一つのOSM typed object IDを複数施設へ同時に割り当てない。

#### Scenario: Only one facility needs review

- **WHEN** 一施設だけが未確定で、他施設の更新は確定している
- **THEN** システムは確定分を反映し、未確定施設の公開状態を変えず確認Issueを用意する

#### Scenario: Associations conflict

- **WHEN** 複数施設の判定が同じOSM typed object IDを選ぶ
- **THEN** システムは競合する新しい割り当てを自動適用せず、競合を確認Issueに示す

### Requirement: Empty evidence and explicit rejection are distinct

システム SHALL 候補がない状態と、提示した候補を不採用と確定した状態を区別する。未関連付け施設で候補がない場合はOSM参照を作らない。候補なし、Jevが閾値以上で「該当なし」を選んだ場合、人が「該当なし」を確定した場合、システム MUST 対象のOSM参照とその照合から得たWikidata参照を解除し、施設UUIDと有効な座標を保持する。

#### Scenario: No candidate exists for an unlinked facility

- **WHEN** 未関連付け施設について取得が成功し候補が一つもない
- **THEN** システムは候補なしを記録し、選択候補のないAI確認通知を作らない

#### Scenario: Existing object disappears

- **WHEN** 既存参照が今回の取得物になく、代替候補がない、またはJevが閾値以上で「該当なし」と判定した
- **THEN** システムはOSMと照合由来のWikidata参照だけを解除し、UUIDと座標を維持する

#### Scenario: Human confirms rejection

- **WHEN** 人が既存関連付けのある施設で「該当なし」を確定する
- **THEN** システムは対象の関連参照を解除し、施設と座標は残す

### Requirement: Operational failures do not become identity reviews

システム MUST 取得失敗、取得物の検証失敗、Jevの認証・通信失敗、不正なAPI応答を候補の不採用や低信頼度と扱わない。システム SHALL 実行を失敗として報告し、その実行の未検証結果を正本へ反映・公開しない。

#### Scenario: Jev cannot be reached

- **WHEN** Jevの呼び出しが通信エラーで終了する
- **THEN** システムは運用上の失敗を報告し、施設判断用Issueを作らず、その実行のデータ変更を公開しない

### Requirement: WAM is a documentary reference

システム MUST 通常更新・手動再実行・候補判定でWAMを取得、読み込み、照合しない。WAMは参考資料と必要な出典・利用条件の文書に残す。移行は既存施設UUID、検索対象および利用可能な座標を保持し、公開データからWAM識別子を除く。

#### Scenario: OSM maintenance runs after migration

- **WHEN** 移行後に月次更新または手動再実行が動く
- **THEN** システムはWAMの接続先、保存ファイル、設定を必要とせずOSM更新を行う

### Requirement: One notification for unmatched targets

システム SHALL 候補なしまたは確定した「該当なし」の検索対象を一つの通常Issueへまとめて通知する。既存接続の有無で通知を分けず、通知に確定操作を要求しない。システム MUST 同じ内容で閉じた通知を再提示しない。

#### Scenario: Several targets have no match

- **WHEN** 既存接続を失った対象と新しい検索対象の両方に接続先がない
- **THEN** システムは一つのIssueに列挙し、検索入力の除去またはOSMへの収録の判断を人に委ねる

### Requirement: Commit decisions before presenting Issues

システム SHALL 取得・判定結果を検証してGitへ保存した後にIssueを提示する。保存済み判断だけで提示を再実行できる。システム MUST push失敗時にIssueを提示せず、取得・Jev判定からの自動再試行を行わない。

#### Scenario: Push fails

- **WHEN** 判定結果のpushが失敗する
- **THEN** 実行は失敗し、Issue提示と公開には進まない

#### Scenario: Presentation is retried

- **WHEN** 保存済み判断のIssue提示を再実行する
- **THEN** 取得とJevを呼ばず判断記録も変更せずに提示する
