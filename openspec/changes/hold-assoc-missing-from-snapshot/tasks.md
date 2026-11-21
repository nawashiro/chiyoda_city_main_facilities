# Tasks

## 1. 保持スナップショットの照合

- [x] 1.1 `assoc --osm-id`から保持スナップショットを読めるようにし、`imports/openstreetmap/raw.json`と`retrieval.json`の組を`verified_snapshot`で検証して要素IDの集合を得る。取得物が無い場合とハッシュが一致しない場合を区別して扱えることを、`tests/test_assoc.py`の追加テストで確認する

## 2. assoc の記録分岐

- [x] 2.1 収録済みの要素では、従来どおり`method: human`の確定判断を保存して参照と座標を適用することを、既存の`tests/test_assoc.py`が通ることで確認する
- [x] 2.2 保持スナップショットに未収録の要素を指定したとき、`WARNING`を表示して`status: hold`、`previous`に指定要素、自動の理由、`human`を持つ保留を保存し、`places.jsonld`へ参照と座標を付けないことを、追加テストで確認する
- [x] 2.3 2.2の自動保留がカテゴリ判断を取り消すことを、`data/categories.json`を用意した追加テストで確認する
- [x] 2.4 取得物が無い、または`verified_snapshot`が失敗するとき、照合しなかった`WARNING`を表示して指定要素を確定判断として記録することを、追加テストで確認する
- [x] 2.5 自動保留のあとに、収録済みの取得物と`assoc --osm-id`で保留が人の確定判断に置き換わり参照が適用されることを、追加テストで確認する
- [x] 2.6 `docs/reference/cli.md`の`assoc`節に、記録前照合・自動保留・`WARNING`の意味・ミラー更新後の再実行による解除を追記し、記載したコマンドがそのまま動くことを確認する

## 3. レビュー手順の文書

- [x] 3.1 `docs/how-to/review-osm-candidates.md`の保留の節に、保持スナップショット未収録の要素が自動で保留になることと、ミラー更新後に`./fac assoc --osm-id`で解除する手順を追記し、記載どおりに動くことを確認する

## 4. 統合検証

- [x] 4.1 `python3 -m unittest discover -s tests`、`python3 -m src.facility_data validate .`、`./fac jsonld-validate data/places.jsonld`を通し、既存の公開データが変わらないことを確認する
- [x] 4.2 保持スナップショットのある作業ツリーで未収録の要素を`./fac assoc --osm-id`へ渡し、`WARNING`、保留エントリ、`./fac category review`の表示を確認する。スナップショットが無い作業ツリーでは、照合しなかった`WARNING`と確定判断の記録だけを確認する

## Workflow follow-up

- レビュー後に変更をアーカイブする
- アーカイブ後の`openspec/specs/osm-maintenance/spec.md`と、次の`assoc`実行の挙動を確認する
