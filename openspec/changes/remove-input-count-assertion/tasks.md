# Tasks

## 1. テストの修正

- [ ] 1.1 件数のassert（`self.assertEqual(106, len(queries))`と一意ID数の行）を削除し、`queries`を`declared`の構築に使う。`python3 -m unittest tests.test_osm_maintenance`が通ることを確認する
- [ ] 1.2 テスト名を`test_published_places_are_declared_and_unique`に変更する。同じテストが通り、名前で件数固定を連想させないことを確認する

## 2. 検証

- [ ] 2.1 `python3 -m unittest discover -s tests`を実行し、全テストが通ることを確認する

## Workflow follow-up

- テスト修正のコミット後に変更をアーカイブする
