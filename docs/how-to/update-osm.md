# OpenStreetMap を更新する

OpenStreetMap の更新は GitHub Actions だけで実行します。ローカルでの取得、入力 JSON の確認、取得日時の指定は不要です。

## 1. 更新 workflow を開始する

GitHub の **Actions** から **Update OpenStreetMap data** を選び、**Run workflow** を実行します。workflow は取得、正規化、候補解決、canonical JSON-LD の更新、検証を順に実行します。

raw snapshot と取得 metadata は内部来歴として保存されます。workflow は SHA-256 を candidate report へ結び付け、後続の適用時にも照合します。reviewer が raw payload を開いたり内容を確認したりする必要はありません。

## 2. 候補を review する

人手判断が必要な候補があれば、workflow は下書き Pull Request を作成します。`reports/osm-review-needed.yaml` だけを編集して commit し、その Pull Request を merge してください。merge 後の workflow が、commit 済み YAML と生成時 artifact を照合し、適用用 Pull Request を作成します。

自動解決できた場合も、workflow は更新用 Pull Request を作成します。候補 YAML（ある場合）と Pull Request の差分だけを review 対象とします。

## 3. 更新を反映する

適用用 Pull Request または自動解決の更新 Pull Request で、検証済みの canonical JSON-LD 差分を review して merge します。失敗した run は Actions のログを確認し、workflow を再実行してください。
