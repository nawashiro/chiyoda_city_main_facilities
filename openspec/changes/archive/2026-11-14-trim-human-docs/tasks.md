# Tasks

## 1. 削除対象文書の除去

- [x] 1.1 `docs/explanation/data-flow.md`、`docs/reference/verification.md`、`docs/tutorials/first-data-change.md`を削除し、`docs/`に残るファイルが5つ（`reference/cli.md`、`reference/data-contracts.md`、`reference/sources-and-licenses.md`、`how-to/publish-release-jsonld.md`、`how-to/review-osm-candidates.md`）と`how-to/update-osm.md`で6つになることを`find docs -name "*.md"`で確認する
- [x] 1.2 削除後、リポジトリ全体で`verification.md`・`data-flow.md`・`first-data-change`への言及が`openspec/changes/archive/`配下だけになることをgrepで確認する

## 2. update-osm.mdとcli.mdの整理

- [x] 2.1 `docs/how-to/update-osm.md`から「照合条件」「Jevの使用量と費用」「保存済み判断の提示」を削除し、残るのが「初期設定」「再実行と結果の確認」だけであることを確認する。節の削除で`verification.md`へのリンクが消えることをgrepで確認する
- [x] 2.2 `docs/reference/cli.md`に`python3 -m src.osm_maintenance present .`の節を追加し（`GITHUB_REPOSITORY`と`GH_TOKEN`が必要、取得・Jev判定・判断記録の書き換えをしない、手動クローズ済みIssueは再提示しない）、記載どおりに`python3 -m src.osm_maintenance present --help`が実行できることを確認する
- [x] 2.3 `docs/how-to/update-osm.md`から削除した節への参照が文書内に残っていないことをgrepで確認する

## 3. data-contracts.mdとpublish-release-jsonld.mdの整理

- [x] 3.1 `docs/reference/data-contracts.md`から「判断記録」を削除し、公開JSON-LDと検索入力の契約が残ることを確認する
- [x] 3.2 `docs/how-to/publish-release-jsonld.md`の「1. 正本を検証する」を削除し、節番号を振り直す。workflowの動作説明を手順に必要な確認事項まで削る。rollbackの節の`verification.md`参照を、PRで`validate.yml`が検証する旨の記述に置き換える

## 4. READMEの更新

- [x] 4.1 作業表から「データを初めて編集する」「変更を検証する」の行を除き、検証が`validate.yml`のPR・push実行で行われることをREADMEに一文で明示する
- [x] 4.2 文書案内の段落から`data-flow.md`へのリンクを除き、残すリンク（データ契約、出典とライセンス）が実在するファイルを指すことを確認する

## 5. 全体の確認

- [x] 5.1 `docs/`内の全Markdownの相対リンクを抽出し、実在するファイル・見出しを指していることを確認する
- [x] 5.2 `git status --short`で変更がdocs/とREADME.mdだけであることを確認する
