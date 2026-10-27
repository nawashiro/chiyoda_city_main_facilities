# OpenStreetMapの更新

通常は毎月1日03:17 UTC（日本時間12:17）にActionsの`Update OpenStreetMap data`が動きます。GitHubの定期実行は遅れる場合があります。[scheduleの制約](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

## 初期設定

リポジトリのSettings → Secrets and variables → Actionsに、TypeSafeのキーを`TYPESAFE_API_KEY`というsecretで登録します。値をコミットやIssueへ記載しないでください。

workflowは`contents: write`、`issues: write`、`pages: write`、`id-token: write`を要求します。mainの保護設定がActionsの直接pushを拒む場合は、設定と運用方針を管理者が確認してください。検証や保護を迂回する経路は設けていません。Pagesの公開元は`GitHub Actions`を指定します。

## 再実行と結果の確認

1. Actions → **Update OpenStreetMap data** → **Run workflow**で`main`を選びます。
2. `process`で取得・照合・検証と、必要なデータコミットが成功したことを確認します。
3. `publish`の対象SHAとPagesの公開結果を確認します。Pages公開URLの`places.jsonld`が配布物です。
4. 確認Issueがあれば[Issueでの確認・修正](review-osm-candidates.md)を行います。

APIや取得の障害ではIssue回答を求めず実行を失敗させます。Actionsのログで原因を直し、再実行してください。公開だけ失敗した場合は失敗したjobを再実行できます。mainが進んで対象SHAが古くなった場合はworkflow全体を再実行します。

## 照合条件

同じ根拠への人の確定、既存の型付きOSM ID、一意なQID、Jevの順に判定します。既存IDは今回の取得物に名称があり、前回座標から50m以内で、検索QIDとの矛盾がない場合に継続します。名称と近接座標だけでは確定しません。

JevはTypeSafe System Oneの`choice`を`jev-1.14.0`で一施設につき一回呼びます。`confidence >= 0.90`で自動確定しますが、既存参照の変更・解除と施設間の候補競合は人の確認へ回します。信頼度は正答率ではありません。[Choice](https://docs.typesafe.ai/primitives/choice)、[信頼度の定義](https://docs.typesafe.ai/confidence)

候補も既存参照もない施設は`no_candidates`として記録します。「該当なし」と明示的に不採用にした判断とは区別します。既存参照が消えた場合は確認Issueを作ります。

## Jevの使用量と費用

使用モデル、信頼度、候補ごとの確率、使用量は`data/osm-decisions.json`の各施設の`jev`へ保存します。評価コマンドと期待値の扱いは[検証](../reference/verification.md#jevの実測評価)を参照してください。

2026-10-27時点の公開料金は入力100万トークン当たり0.042米ドル、出力無料です。評価結果の`input_tokens × 0.042 / 1,000,000`がその料金での試算です。請求額はTypeSafe側の使用状況と照合し、価格変更時は単価も確認してください。[モデルと料金](https://docs.typesafe.ai/models)
