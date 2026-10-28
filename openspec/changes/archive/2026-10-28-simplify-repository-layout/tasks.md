# Tasks

## 1. 取得ミラーの整理

- [x] 1.1 `src/retrieve_osm.py` から `selection.json` の書き出しを削除する
- [x] 1.2 `.gitignore` に `imports/openstreetmap/raw.json` を追加し、`git rm --cached` で追跡を外す
- [x] 1.3 `.gitignore` から `reports/` 関連の行を整理する

## 2. 死んだファイルとディレクトリの除去

- [x] 2.1 `schema/` を削除する
- [x] 2.2 `reports/` ディレクトリを削除する

## 3. データ配置の集約

- [x] 3.1 `config/sources.json` を `data/sources.json` へ移動し、`config/` を除去する
- [x] 3.2 `tests/test_licensing_metadata.py` の参照を `data/sources.json` へ更新する

## 4. エージェント用ディレクトリの改名

- [x] 4.1 `.hermes/` を `.agents/` へ改名する

## 5. 文書と検証

- [x] 5.1 `docs/explanation/data-flow.md` と `docs/reference/data-contracts.md` の保存対象の記述を更新する
- [x] 5.2 `python3 -m unittest discover -s tests` が通ることを確認する
- [x] 5.3 `openspec validate --change simplify-repository-layout` が通ることを確認する
