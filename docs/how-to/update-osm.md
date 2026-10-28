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

## 照合条件

既存の型付きOSM IDが取得結果にあれば、その接続を維持します。名称・座標・タグ・QIDや入力ハッシュの変化だけでは再審査しません。名前のない要素を除く取得条件は維持します。

既存IDがなければ、一意なQID、Jevの順に照合します。未接続の検索対象も同じ経路を使います。名称と近接座標だけでは確定しません。

JevはTypeSafe System Oneの`choice`を`jev-1.14.0`で呼びます。`confidence >= 0.90`で候補採用または「該当なし」を自動確定します。施設間の候補競合は人の確認へ回します。信頼度は正答率ではありません。[Choice](https://docs.typesafe.ai/primitives/choice)、[信頼度の定義](https://docs.typesafe.ai/confidence)

候補なしではJevを呼びません。候補なし、Jevの高信頼度の「該当なし」、人の「該当なし」はOSMと照合由来のWikidata参照を解除し、施設UUIDと座標を残します。接続先がない対象は一つの通常Issueへまとめて通知します。実在を確認し、検索入力の除去またはOSMへの収録を検討してください。

人が選んだ接続先は以後の既存参照として維持します。人の「該当なし」と未解決のJev結果は同じ照合根拠で再利用し、根拠が変わったときだけ再判定します。

## 保存済み判断の提示

Gitへの保存後にIssue提示だけが失敗した場合は、保存済み判断を使って再提示できます。

```bash
python3 -m src.osm_maintenance present .
```

実行には`GITHUB_REPOSITORY`と`GH_TOKEN`が必要です。取得やJev判定、判断記録の書き換えは行いません。同じ内容で手動クローズしたIssueは再提示しません。push失敗時は取得から自動でやり直さず停止するため、原因を確認してください。

## Jevの使用量と費用

使用モデル、信頼度、候補ごとの確率、使用量は`data/osm-decisions.json`の各施設の`jev`へ保存します。評価コマンドと期待値の扱いは[検証](../reference/verification.md#jevの実測評価)を参照してください。

2026-10-27時点の公開料金は入力100万トークン当たり0.042米ドル、出力無料です。評価結果の`input_tokens × 0.042 / 1,000,000`がその料金での試算です。請求額はTypeSafe側の使用状況と照合し、価格変更時は単価も確認してください。[モデルと料金](https://docs.typesafe.ai/models)
