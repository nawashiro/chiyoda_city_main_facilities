# Tasks

## 1. 選択判定の切り出し

- [x] 1.1 検索座標から50m超（0.001度）広げた`query_region`と、3つの選択規則を評価する`selection_predicate`を`src/osm_mirror.py`に追加する。`(kind, identifier) in selected_ids`、`query_region`内の50m照合、`CHIYODA_BBOX`内の`wikidata`一致の順に評価し、`tests/test_osm_retrieval.py`に50mの内外・両矩形の内外・typed ID・wikidata一致の境界テストを追加して、`python3 -m unittest tests.test_osm_retrieval`が通ることを確認する
- [x] 1.2 座標を1件も持たない入力で`selection_predicate`がtyped IDとWikidata一致だけを評価することをテストで確認する（`query_region`を作らない分岐の確認）

## 2. ハンドラの判定順の変更

- [x] 2.1 nodeハンドラで`selectable`を先に評価し、選択が確定したときだけ`dict(node.tags)`を作る。`python3 -m unittest tests.test_osm_retrieval`と既存の抽出テストが通ることを確認する
- [x] 2.2 wayハンドラで中心を出した後に`selectable`を評価し、選択が確定したときだけ`dict(way.tags)`を作る。way中心の50m境界と矩形外のwayが候補にならないことをテストで確認する
- [x] 2.3 relationハンドラを`selectable`を使う形に揃え、`dict(relation.tags)`の作成順は変えない。`python3 -m unittest tests.test_osm_retrieval`が通ることを確認する

## 3. 実データでの同一性と短縮の確認

- [x] 3.1 変更前の`extract_elements`を退避し、`imports/openstreetmap/retrieval.json`の`pbfUrl`が指すPBFを新旧両方のコードに同じ入力で通して、要素の並びと各要素の`tags`が一致することを確認する
- [x] 3.2 同じ実行で抽出時間を計測し、変更前（手元実測353秒）が3分の1程度（120秒前後）に短縮することを確認する
- [x] 3.3 `python3 -m unittest discover -s tests`と`python3 -m src.facility_data validate .`が通ることを確認する

## Workflow follow-up

- mainへ反映後、Actionsの`Update OpenStreetMap data`を手動実行し、抽出ログの所要時間と生成された`imports/openstreetmap/raw.json`の差分を確認する。
- 変更をアーカイブする。
