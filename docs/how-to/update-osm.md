# OpenStreetMap を更新する

OpenStreetMap の更新は GitHub Actions だけで実行します。ローカルでの取得、入力JSONの確認、取得日時の指定は不要です。

## 1. 更新workflowを開始する

GitHub の **Actions** から **Update OpenStreetMap data** を選び、**Run workflow** を実行します。workflow は取得、正規化、候補解決、canonical JSON-LDの更新、検証を順に実行します。

raw snapshot と取得metadataは内部来歴として保存されます。workflow はSHA-256をcandidate reportへ結び付け、後続の適用時にも照合します。reviewerがraw payloadを開いたり内容を確認したりする必要はありません。

## 2. 候補をreviewする

人手判断が必要な候補があれば、workflow は下書きPull Requestを作成します。`reports/osm-review-needed.yaml`だけを編集してcommitし、そのPull Requestをmergeしてください。merge後のworkflowが、commit済みYAMLと生成時artifactを照合し、適用用Pull Requestを作成します。

自動解決できた場合も、workflow は更新用Pull Requestを作成します。候補YAML（ある場合）とPull Requestの差分だけをreview対象とします。

## 3. 更新を反映する

適用用Pull Requestまたは自動解決の更新Pull Requestで、検証済みのcanonical JSON-LD差分をreviewしてmergeします。失敗したrunはActionsのログを確認し、workflowを再実行してください。
