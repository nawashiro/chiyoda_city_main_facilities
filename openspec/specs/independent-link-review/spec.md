# independent-link-review Specification

## Purpose

自動関連付けの三者判断が単一モデルの反復にならないよう、独立した接続先とモデルを検証します。投票ログを公開データから除外し、人手確認は候補に結び付いたYAMLとPRで行います。

## Requirements

### Requirement: Decision history stays outside public data

システム MUST Jevの回答、確率、信頼度、人の選択、判断根拠、Issue URLを公開Place JSON-LDへ保存しない。判断の記録は公開配布物の外で保持する。

#### Scenario: A link decision is published

- **WHEN** 照合結果を公開データへ反映する
- **THEN** JSON-LDには判断の記録を含めない

### Requirement: Single Jev judgment with an uncertainty threshold

システム SHALL 決定規則で確定できない候補について、Jev一つに候補IDまたは「該当なし」を選ばせる。システム SHALL 回答の信頼度が定めた閾値以上で、重複割り当ての制約に抵触しない場合に自動確定する。閾値未満の場合は人の確認を求める。システム MUST 同じ施設について観点別の三者投票や別モデルへのフォールバックを行わない。

#### Scenario: Jev confidently chooses a candidate

- **WHEN** Jevが有効な候補を閾値以上の信頼度で選び、適用制約も満たす
- **THEN** システムはその関連付けを自動確定し、確認Issueを新規作成しない

#### Scenario: Jev is uncertain

- **WHEN** 有効なJevの回答が閾値未満の信頼度である
- **THEN** システムは候補を自動確定せず、確認Issueを用意する

### Requirement: Actionable review notification

システム SHALL 自動確定できない施設ごとに、対象名、現在の参照、候補名、OSM typed ID、距離、地図・OSMへのリンク、判断が必要な理由、Jevの選択と信頼度をIssueに示す。Jevを呼んでいない場合はその旨を示す。選択肢には各候補と「該当なし」、別途「判断を確定する」を含める。

#### Scenario: Uncertain candidates are presented

- **WHEN** Jevが二つの候補について確信を持てない
- **THEN** Issueは対象と候補を比較できる情報、低信頼度という理由、および判断に使うチェックボックスを表示する

### Requirement: Exactly one confirmed Issue choice

システム SHALL 書き込み権限のある利用者によるIssue本文の編集を受け付け、候補または「該当なし」が一つだけ選択され、確定欄がチェックされた場合に適用する。システム MUST 未選択、複数選択、保存済み候補にない選択を適用しない。形式が不正な確定には修正方法を通知する。チェック途中やコメントだけでは適用しない。

#### Scenario: Human confirms one candidate

- **WHEN** 利用者が候補を一つ選び、確定欄をチェックする
- **THEN** システムは施設ID、選択候補、編集権限、現在の割り当てを確認した上で、その施設の判断だけを適用する

#### Scenario: Multiple candidates are confirmed

- **WHEN** 利用者が候補を二つ選んで確定する
- **THEN** システムは反映せず、一つだけ選ぶようIssueで知らせる

### Requirement: Review remains bound to current evidence

システム SHALL 施設ID、保存済み候補、Issueを対応付け、現在のIssue本文の回答を確認する。説明文・信頼度・本文全体・根拠ハッシュの一致を回答の必須条件にしない。未解決Issueは同じ施設で再利用し、根拠が変われば提示時に選択・確定欄をリセットする。同じ根拠では途中の選択を保持し、閉じたIssueを再提示しない。システム MUST 回答処理で取得・Jev判定・未解決Issueの再提示を行わず、適用済み回答を重複適用せず、正本のGit保存と公開が成功した後にIssueを完了する。

#### Scenario: A previous month is answered late

- **WHEN** Issueの説明文や信頼度が編集され、保存済み候補から一つ選んで確定される
- **THEN** システムは本文全体やハッシュの一致を求めず、有効な選択を反映する

#### Scenario: Review outlives Actions artifacts

- **WHEN** 確認IssueがActions artifactの保存期限より長く未解決のまま残る
- **THEN** システムは保持した判断根拠から回答を検証でき、期限切れartifactを必須としない

#### Scenario: Publication fails after applying a decision

- **WHEN** 判断を正本へ反映した後に公開処理が失敗する
- **THEN** システムはIssueを完了せず、再実行で同じ判断を重複適用せずに公開を再試行できる
