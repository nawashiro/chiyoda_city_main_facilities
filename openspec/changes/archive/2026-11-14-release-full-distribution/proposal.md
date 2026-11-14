# Proposal

## Why

GitHub Release はPages配布物の一部(JSON-LD単体)しか凍結しておらず、v3.0.0のリリースノートはOSM・Wikidataを含むと記載したのに資産には無い、という不整合が起きました。また配布は「dry-run実行→人がartifactを確認→人がReleaseを作成・公開」という二段階の手作業で、手動運搬が余計な資産(zip)の混入を生んでいます。

Releaseを「その版のPages配布物一式の凍結」として再定義し、Actionsを起動したらタグ作成からリリース公開・全資産添付まで自動で完了させます。版号は日付(`YYYY.MM.DD`)を使い、版の判断だけを人に残します。

## What Changes

- **BREAKING** Release配布物を `places-<tag>.jsonld` に加え、同じコミットでビルドしたOSMミラー(`osm-<tag>.json`)とWikidataミラー(`wikidata-<tag>.json`)を添付します。landing page `index.html` は版非依存のため含めません。
- **BREAKING** リリースworkflowを1本に統合します。`workflow_dispatch` 1回の起動で、main最新検査→テスト→ビルド→日付タグ作成→Release公開→全資産添付まで行います。既存の `release: published` トリガーとdry-run用の `tag` 入力を廃止します。
- 版号の採番を自動化します。実行日のUTC日付 `YYYY.MM.DD` をタグとし、タグが既に存在する場合は失敗して終了します(タグ移動・上書きはしません)。
- リリースノートをworkflowが生成します。資産一覧と、各資産のライセンス(ODbL・CC0)を本文に含めます。
- リリース手順の文書(`docs/how-to/release-dataset.md`)を新フローに書き換え、READMEの配布の記述を更新します。
- 既存の published Release(v3.0.0を含む)は編集しません。重複資産やリリースノートの文言は履歴として残ります。

## Capabilities

### New Capabilities

(なし)

### Modified Capabilities

- `dataset-publication`: Immutable release snapshot 要求を「GitHub Releaseごとに、そのコミットでPagesに公開した配布物と同等のJSON-LD・OSMミラー・Wikidataミラーを版固定で公開する」に書き換えます。Actions起動から公開までの自動化、日付版号、タグ存在時の失敗、リリースノートのライセンス明記を要求に含めます。

## Impact

- `.github/workflows/release-jsonld.yml` を新workflowに置き換えます(内容: write)。
- `scripts/prepare_release_jsonld.py` を3資産を準備するスクリプトに置き換えます。
- `tests/test_release_workflow.py` を新workflow・新スクリプトに合わせて書き換えます。
- `docs/how-to/release-dataset.md`、`README.md`、`docs/reference/data-contracts.md` の配布の記述を更新します。
- 既存タグ(v1.0.0〜v3.0.0)とそのRelease資産は変更しません。
