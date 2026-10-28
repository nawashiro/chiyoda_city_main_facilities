# Proposal

## Why

リポジトリはデータファイル8個に対してトップレベルに多数のディレクトリを持ち、参照されないファイルと空のディレクトリが混雑の原因になっている。取得ミラー`raw.json`(約1.6万行)がGitに追跡され、リポジトリ全体の8割をデータスナップショットが占める。このままだと、どこに何があるのかの把握とレビューが不要に難しくなる。

## What Changes

- **BREAKING** `imports/openstreetmap/raw.json` をGit追跡から外す。取得から判定までの同一実行内の作業ファイルであり、`retrieval.json`が`rawSha256`と取得元を記録するため、コミットによる永続保存は不要。
- `selection.json` の書き出しを削除する。`retrieve_osm.py`が書くだけで読み手が存在しない。
- 参照のない`schema/search-input.schema.json`を削除する。検証は`facility_data.py`がコード内で完結する。
- 空の`reports/`ディレクトリとそのgitignore設定を削除する。
- `config/sources.json`を`data/sources.json`へ移動し、コミット対象データを`data/`に集約する。
- `.hermes/`を`.agents/`へ改名する。ベンダー名を含まない標準的なエージェント用ディレクトリ名とし、Git管理は継続する。
- データフロー文書の取得物保存の記述を、実際の保存対象(取得元・ハッシュ)に合わせて更新する。

## Capabilities

### New Capabilities

(なし)

### Modified Capabilities

(なし)

## Impact

- `.github/workflows/update-osm.yml`の`git add imports/openstreetmap/`は、raw.jsonがgitignoreされるだけで動作を変えない。
- `src/retrieve_osm.py`(selection.json書き出しの削除)、`.gitignore`、`docs/explanation/data-flow.md`、`docs/reference/data-contracts.md`。
- `tests/test_licensing_metadata.py`の`config/sources.json`参照を`data/sources.json`へ更新。
- 公開データ`site/places.jsonld`とReleasesの内容は変わらない。
