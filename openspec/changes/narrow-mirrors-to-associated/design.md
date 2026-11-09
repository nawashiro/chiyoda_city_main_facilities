# Design

## Context

月次パイプライン（`src/retrieve_osm.py` → OSM 抽出 → `src/wikidata_retrieval.py` → QID 取得）は、調査プールを意図した広域抽出（検索入力座標 ±50m・OSM タグ wikidata 全採集）をそのまま `site/mirrors/` にコピーしている（現状: OSM 919 要素中紐付け 89、Wikidata 94 QID 中紐付け 44）。配布先 `site/mirrors/` は Pages 公開物であり、調査プールは非公開に留めるべき。

## Goals / Non-Goals

- Goals: 公開ミラーを紐付け分のみに限定。調査プール（imports）は現状維持。
- Non-Goals: 抽出ルール（±50m・wikidata タグ採集）自体の変更。調査プールの遡及削除。新たな調査ワークフローの追加。

## Decisions

1. **選別は imports の raw に対して行い、配信側でフィルタする。** `site/mirrors/` への書き出し時に、紐付け ID/QID 集合で raw を絞る。`retrieve_osm.py` の抽出側（PBF パース）は変更しない。
   - 根拠: 調査プールは既存抽出のままなので、過去ワークフロー（`resolve_osm_candidates.py` の候補探索）が壊れない。抽出側で絞ると調査データが失われる。
   - 代替: 抽出時に紐付け ID のみに絞る — 調査プールが失われ却下。
2. **紐付け集合の読み取りは既存 `src/facility_data.py` の `collect_osm_ids()` を使う。** places 紐付けの正確な単一実装であり、重複したパーサを書かない（KISS）。Wikidata 側の参照 QID は places.jsonld 全文から `Q\d+` を抽出する既存手段（fac CLI 側と同じ正本データに対する判定）を `facility_data.py` に集約する。
3. **選別関数は新設モジュールに置かず、ミラー書き出しを担う薄い1関数にまとめる。** OSM と Wikidata で「紐付け集合で raw の elements/entities を絞る」という同一の形をとるため、処理は各リトリーバルモジュールに置くか共有ヘルパ1つとする。新ファイルを増やさない。

## Risks / Trade-offs

- 紐付けが工件にブロックされた要素（例: way の center 欠損）はミラーから自然に欠け、紐付け情報を失わない — 選別は places 側が正本。
- 未紐付け QID の取り扱い: `imports/wikidata/raw.json` は月次 update ジョブ内で生成済み。 survey 用途が実装側で参照を続けるため、削除は行わない。
- 未紐付け QID 中に将来紐付け予定の施設候補（神田明神等）を含むが、ミラー公開責任として調査の段階で吟味するものであり、公開ミラーには含めない。
