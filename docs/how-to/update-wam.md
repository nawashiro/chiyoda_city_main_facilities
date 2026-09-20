# WAM NET を更新する

WAM NET の更新は GitHub Actions だけで実行します。ローカルでの取得、入力 JSON の確認、取得日時の指定は不要です。

## 1. 更新 workflow を開始する

GitHub の **Actions** から **Update WAM data** を選び、対象 release を `YYYYMM` で入力して **Run workflow** を実行します。workflow は公式 release を取得し、正規化、canonical JSON-LD への反映、repository validation、unit test、再生成検証を実行します。

raw snapshot と取得 metadata は内部来歴として保存されます。SHA-256 は workflow が検証するため、reviewer が raw payload を開いたり内容を確認したりする必要はありません。

## 2. Pull Request を review する

成功した workflow は更新用 Pull Request を作成します。canonical JSON-LD と Pull Request の差分を review して merge してください。raw snapshot は人手 review の前提ではありません。

workflow が失敗した場合は Actions のログを確認し、必要に応じて release を見直して workflow を再実行してください。
