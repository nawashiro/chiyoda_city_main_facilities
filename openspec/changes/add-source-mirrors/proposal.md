# Proposal

## Why

施設データの裏付けとなっている OSM と Wikidata の元データが外部に任せきりで、このリポジトリが持っている抽出物（`imports/openstreetmap/raw.json`、919要素）は配信されていない。千代田区の施設規模なら十分ホストできるので、調査の再現性のため Raw ミラーを自前配信する。issue #68。

## What Changes

- 月次 `update-osm` パイプラインが、OSM ミラー抽出物（既存 `imports/openstreetmap/raw.json` と同じ内容・`out center` 形式）を `site/mirrors/osm.json` として配信する。
- 同パイプラインが、参照されている Wikidata QID の entity JSON（全 statements）を `wbgetentities` で取得（50 QID/リクエストでページング）し、`site/mirrors/wikidata.json` として配信する。取得メタと SHA256 を `imports/wikidata/` に記録する。
- ODbL（OSM 由来）と CC0（Wikidata 由来・リポジトリ独自)を別ファイルに分離し、landing page（`site/index.html`）の `hasPart` に各ミラーの `DataDownload` とライセンスを明示する。
- GitHub Release による版固定 snapshot は本 change の対象外とする（別 change）。

## Capabilities

### New Capabilities

- `source-mirrors`: OSM・Wikidata の Raw ミラーの取得・更新・配信。 月次パイプラインに統合され、常に最新1版のみを Pages 配信する。

### Modified Capabilities

- `dataset-publication`: landing page が source ミラー配布物を `DataDownload` として表現し、ODbL と CC0 を区別して明示する要件を追加。

## Impact

- `src/retrieve_osm.py` / `src/osm_maintenance.py`: 配信への組み込み
- 新規 `src/` 内の Wikidata 取得モジュール
- `site/index.html`: `hasPart` への `DataDownload` 追加
- `.github/workflows/update-osm.yml`: artifacts の追加
- 依存追加なし（Wikidata API は標準 HTTP GET）
