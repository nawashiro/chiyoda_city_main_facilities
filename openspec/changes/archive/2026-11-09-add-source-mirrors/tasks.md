# Tasks

## 1. Wikidata 取得モジュール

- [x] 1.1 `src/wikidata_retrieval.py` を作る: OSM ミラー抽出物から `wikidata` / `operator:wikidata` タグの QID を収集し、`wbgetentities`（ids= 50件/リクエスト、props=info,labels,aliases,descriptions,claims,sitelinks）を分割取得して entity 部分を `imports/wikidata/raw.json` に、メタを `imports/wikidata/retrieval.json`（sourceId, retrievedAt, endpoint, rawSha256, qidCount, pages）に書く
- [x] 1.2 QID が空のときはファイルを空の entity セットとして書き、API を呼ばない
- [x] 1.3 取得失敗時に例外を握らず、失敗を報告して OSM 更新の継続を妨げない設計をテストで確認する

## 2. 月次パイプラインへの組み込みと配信

- [x] 2.1 `site/mirrors/` を作り、`imports/openstreetmap/raw.json` をそのまま `site/mirrors/osm.json` としてコピーする処理をパイプラインに追加する
- [x] 2.2 Wikidata 取得を月次 refresh に組み込み、成功時 `site/mirrors/wikidata.json` を更新する。取得が失敗しても process job を失敗させない（warning 出力）
- [x] 2.3 `.github/workflows/update-osm.yml` の `git add` に `imports/wikidata/` を追加する（`site/mirrors/` は Pages デプロイ時の build で生成）

## 3. landing page

- [x] 3.1 `site/index.html` の `hasPart` に OSM ミラー・Wikidata ミラーの `DataDownload`（contentUrl, encodingFormat）を追加し、配布物単位で ODbL / CC0 を参照する

## 4. 検証

- [x] 4.1 `python3 -m unittest discover -s tests` と `./fac jsonld-validate site/places.jsonld` を通す
- [x] 4.2 リポジトリ内で `python3 -m src.wikidata_retrieval` を実行して raw.json / retrieval.json の生成を確認する（初回実データ）
- [x] 4.3 index.html の JSON-LD がパースでき、`DataDownload` 2件とライセンス区別を確認する

## Workflow follow-up

- 実施後: main に commit・push（origin のみ）
- issue #68 に進捗をコメントで残す
