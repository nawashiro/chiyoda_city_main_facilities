# Tasks

## 1. リリース資産の準備スクリプト

- [x] 1.1 `scripts/prepare_release.py` を作成する。`--site-dir` と `--output-dir` と `--version` を受け、`site/places.jsonld` を `validate_published_document` で検証して `release/places-<version>.jsonld` に、`site/mirrors/osm.json` と `site/mirrors/wikidata.json` を `release/osm-<version>.json` と `release/wikidata-<version>.json` に複製する。検証失敗で非ゼロ終了することを `python3 scripts/prepare_release.py --version 2026.11.14` の実行と出力3点のバイト一致で確認する
- [x] 1.2 `scripts/prepare_release_jsonld.py` を削除し、参照が残っていないことを `grep -r prepare_release_jsonld src scripts tests docs README.md .github` が空で確認する

## 2. リリースworkflow

- [x] 2.1 `.github/workflows/release.yml` を作成する。トリガーは `workflow_dispatch` のみ。permissionsは `contents: write`。手順: checkout → Python 3.13 → 「checkoutコミット == origin/main HEAD」検査 → `unittest` → `facility_data build` → タグ `YYYY.MM.DD`(UTC)の存在確認と失敗 → `prepare_release.py` → リリースノート本文を変数で定義 → softprops/action-gh-release で `tag_name`・`body`・`files: release/*` によりタグ作成とRelease公開と添付。ymlの構文を `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/release.yml'))"` で確認する
- [x] 2.2 `.github/workflows/release-jsonld.yml` を削除する

## 3. テスト

- [x] 3.1 `tests/test_release_workflow.py` を書き換える。workflowが `workflow_dispatch` トリガーのみを持ち `release:` イベントとdry-run入力を含まないこと、main最新検査・タグ存在確認・release upload action・3資産の添付(`release/*` または個別パス)・リリースノート変数があることを検査する。スクリプトのテストは3資産の生成とバイト一致、失敗時の非ゼロ終了を検査する。`python3 -m unittest tests.test_release_workflow -v` が通ることで確認する
- [x] 3.2 全テスト `python3 -m unittest discover -s tests` が通ることで確認する

## 4. 文書

- [x] 4.1 `docs/how-to/release-dataset.md` を新フローに書き換える。Actionsのrelease workflowを起動する手順、日付タグの採番、タグ衝突時の対処、資産3点とノートの確認、既存published Releaseを編集しない規律を含める。タイトルと手順の整合を確認する
- [x] 4.2 `README.md` の配布の記述と手順表、`docs/reference/data-contracts.md` のRelease資産の記述を新資産構成に更新する。記述が実ファイルと一致することを確認する

## 5. 統合確認

- [x] 5.1 変更全体を `git diff` で点検し、旧ファイル(`release-jsonld.yml`、`prepare_release_jsonld.py`)の削除と新資産構成の整合を確認する
