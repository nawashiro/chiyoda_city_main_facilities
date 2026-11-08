# Design

## Context

- 月次 `update-osm.yml` → `src/osm_maintenance.py refresh` → `src/retrieve_osm.py`（Tokyo PBF から `src/osm_mirror.py` で抽出）→ `imports/openstreetmap/raw.json`（919要素、`out center` 形式）が既にある。配信はしていない。
- Wikidata は取得パイプラインが存在しない。QID は OSM 要素の `wikidata` / `operator:wikidata` タグにのみ現れ、現行ミラーには90個ある。
- landing page は `site/index.html` の `hasPart` に source Dataset（repository CC0 / OSM ODbL / Wikidata CC0 / WAM）を既に宣言済み。ミラー配布物（`DataDownload`）の記述はない。

## Goals / Non-Goals

**Goals:**
- `site/mirrors/osm.json` と `site/mirrors/wikidata.json` を月次パイプラインで最新化し Pages で配信する。
- landing page から両ミラーを発見可能にする（`DataDownload` + 個別ライセンス）。

**Non-Goals:**
- GitHub Release への snapshot 添付（別 change）。
- way/relation の geometry 保持（`out center` のまま）。
- Wikidata 以外の source の新規取得。

## Decisions

- **配布物の内容は `imports/openstreetmap/raw.json` と同型のまま**。ミラーに新形式を作らず、抽出物をそのまま配信する。変換層を置かない（KISS）。
- **QID の正本は OSM ミラーのタグ**。追加の QID 一覧を持たず、raw 抽出に現れる `wikidata` / `operator:wikidata` タグを収集して `wbgetentities`（`ids=` 50 件/リクエスト）をループする。90 QID → 2 リクエスト。
- **Wikidata ミラーは entities API 応答の entity 部分をそのまま保存**。全 statements が要望の「値すべて」であり、SPARQL やスリム化した形式を作らない。
- **Wikidata 取得の失敗は warning で継続**。`wikidata.json` が作れない月は当該ファイルだけ旧版のまま有効とし、OSM 更新・Pages 公開・decisions close までの連鎖を止めない。
- **取得メタは `imports/wikidata/retrieval.json`**（OSM と同種のフィールド）+ `raw.json`。ファイル名は既存 OSM に揃える。
- **landing page の `hasPart` に `DataDownload` を OSM/Wikidata 各1件追加**。ライセンスは既存 `hasPart` の source Dataset と個別参照で区別し、混合 CC0 表示を作らない。

## Risks / Trade-offs

- [Wikidata entity のリビジョンが応答毎に動く] → ミラーは「取得日時点の snapshot」と割り切り、`retrievedAt` で示す。
- [`wbgetentities` の props 未指定は一部プロパティ（`sitelinks`/URL 等）を返さない] → `props=` を明示して全要素を取得する方針を選ぶ。
- [ミラーが Pages に月次で追加されるためリポジトリの push サイズが増える] → 千代田区スコープ（数百 KB 程度）であり許容。
