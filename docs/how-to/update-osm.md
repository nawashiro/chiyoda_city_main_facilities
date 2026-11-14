# OpenStreetMapの更新

通常は毎月1日03:17 UTC（日本時間12:17）にActionsの`Update OpenStreetMap data`が動きます。GitHubの定期実行は遅れる場合があります。[scheduleの制約](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

## 初期設定

リポジトリのSettings → Secrets and variables → Actionsに、TypeSafeのキーを`TYPESAFE_API_KEY`というsecretで登録します。値をコミットやIssueへ記載しないでください。

workflowは`contents: write`、`issues: write`、`pages: write`、`id-token: write`を要求します。mainの保護設定がActionsの直接pushを拒む場合は、設定と運用方針を管理者が確認してください。検証や保護を迂回する経路は設けていません。Pagesの公開元は`GitHub Actions`を指定します。

## 再実行と結果の確認

1. Actions → **Update OpenStreetMap data** → **Run workflow**で`main`を選びます。
2. `process`で取得・照合・検証、必要なデータコミットとpush、その後のIssue提示が成功したことを確認します。
3. `publish`の対象SHAとPagesの公開結果を確認します。Pages公開URLの`places.jsonld`が配布物です。
4. 確認Issueがあれば[Issueでの確認・修正](review-osm-candidates.md)を行います。

APIや取得の障害ではIssue回答を求めず実行を失敗させます。Actionsのログで原因を直し、再実行してください。公開だけ失敗した場合は失敗したjobを再実行できます。mainが進んで対象SHAが古くなった場合はworkflow全体を再実行します。


