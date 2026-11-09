# Tasks

- [x] 1. `src/facility_data.py` に紐付け QID 収集を追加（places.jsonld から `Q\d+` 参照を抽出する正本判定）
- [x] 2. `src/retrieve_osm.py`（またはそのパイプライン呼び出し側）に site/mirrors 書き出し時の絞り込みを追加: `collect_osm_ids()` の紐付け要素のみを `site/mirrors/osm.json` へ（実装は `build_repository()` のコピー段階で絞る）
- [x] 3. `src/wikidata_retrieval.py` に同じ絞り込みを追加:places が参照する QID の entities のみを `site/mirrors/wikidata.json` へ（imports 側 raw は広域のまま）
- [x] 4. `.github/workflows/update-osm.yml` の site/mirrors 書き出しステップを新絞り込み経路に合わせる（ミラー生成は publish build 内 `facility_data build` なので、 monthly commit の `git add` に `site/mirrors/` を追加）
- [x] 5. 現データで絞り込みを実行し、`site/mirrors/osm.json` が紐付け要素のみ、`site/mirrors/wikidata.json` が参照 44 QID のみになることを確認（OSM は紐付け 89件 のうち新規紐付け2件が今月の抽出差し替え待ちで未抽出、次回月次で反映）
- [x] 6. `imports/` 側 raw が変わらず残ることを確認（調査プール維持）
- [x] 7. Tests: 絞り込み関数のテスト追加（未紐付け除外・紐付け追加後の反映）と既存テストの通過を確認
- [x] 8. jsonld-validate・Pages 公開ワークフロー（validate.yml / publish-pages.yml）の通過を確認

