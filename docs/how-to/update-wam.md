# WAM NET を更新する

WAM NET の更新は GitHub Actions だけで実行します。ローカルでの取得、入力JSONの確認、取得日時の指定は不要です。

## 1. 更新workflowを開始する

GitHub の **Actions** から **Update WAM data** を選び、対象releaseを `YYYYMM` で入力して **Run workflow** を実行します。workflow は公式releaseを取得し、正規化、canonical JSON-LDへの反映、repository validation、unit test、再生成検証を実行します。

raw snapshot と取得metadataは内部来歴として保存されます。SHA-256はworkflowが検証するため、reviewerがraw payloadを開いたり内容を確認したりする必要はありません。

## 2. Pull Requestをreviewする

成功したworkflowは更新用Pull Requestを作成します。canonical JSON-LDとPull Requestの差分をreviewしてmergeしてください。raw snapshotは人手reviewの前提ではありません。

workflowが失敗した場合はActionsのログを確認し、必要に応じてreleaseを見直してworkflowを再実行してください。
