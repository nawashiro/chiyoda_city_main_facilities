# Proposal

## Why

現在の独自レジストリは、施設属性、監査履歴、外部参照の履歴、更新処理を密結合します。
この構成は小規模な公開データの保守負担を増やし、ウェブ上での再利用を妨げます。

施設データを標準語彙のJSON-LDへ移します。
Gitを変更履歴とし、関連先には同一性を断定しないリンクを使います。

## What Changes

- **BREAKING** 公開Placeの正本を独自`registry.json`からJSON-LDへ移します。
- **BREAKING** Placeに保存する監査配列、外部参照のcurrent/superseded履歴、更新時刻を廃止します。
- 既存UUIDを`urn:uuid:`のPlace IDとして維持します。
- 検索入力で`publish: false`を明示した施設候補を公開配布物へ出力しません。
- Placeを`schema:Place`で表現します。
- Point座標を`schema:GeoCoordinates`の`latitude`と`longitude`で表現します。
- OSMとWikidataの自動関連先を、公式のresource URIによる`rdfs:seeAlso`で表現します。
- WAMの自動関連先を`schema:PropertyValue`の識別子で表現します。
- `schema:sameAs`、SKOSのmatch関係、Place単位の`prov:wasDerivedFrom`を自動では出力しません。
- 独自`categoryIds`を公開正本から削除します。
- WAMの公開Placeへの反映は`schema:PropertyValue`の外部識別子だけに限定します。
- 営業時間の変換と公開は今回の対象から除外します。
- 町名、電話番号、OSMタグの公開と導出は今回の対象から除外します。
- 画像とrights文字列を公開Placeから除外します。
- 三者LLM照合では、正規化済み`(base_url, model)`が全員で重複しないことを必須にします。
- 投票ログを公開Placeデータへ保存しません。
- GitHub PagesにDataset landing pageを置き、`schema:Dataset`と`DataDownload`で最新配布物を公開します。
- GitHub Releaseに版固定JSON-LD snapshotを公開します。
- 人手OSM reviewはcommit済みreview YAMLとPRだけで実施します。
- Issue本文の候補checkboxと互換parserを廃止します。
- GeoJSONの公開、互換生成、manifest entryを即時終了します。
- town polygonの取得、pinned data、町名の導出経路を削除します。
- canonical JSON-LDを直接編集し、最小のvalidate CLIだけを残します。
- リポジトリ固有の資産をCC0で公開し、OSM、Wikidata、WAMの由来と利用条件を別々に明示します。
- 旧保守規約を削除し、このOpenSpec changeの成果物を移行の正本にします。
- Zenodo DOI、W3ID、独自ドメインは今回の実装対象から除外します。

## Capabilities

### New Capabilities

- `public-jsonld-dataset`: 標準語彙で施設とDatasetを公開し、安定した配布物を提供します。
- `related-record-links`: 自動照合した外部レコードを、同一性を断定せずにPlaceへ関連付けます。
- `independent-link-review`: 異なるLLM接続先とモデルによる照合判断を検証します。
- `dataset-publication`: GitHub PagesとGitHub Releaseでデータセットを発見・取得可能にします。

### Modified Capabilities

- なし。既存OpenSpec capabilityはありません。

## Impact

- `data/registry.json`、公開GeoJSON、入力スナップショット、生成処理を移行します。
- `src/facility_data.py`、`src/fac_cli.py`、OSM/WAM更新処理、照合処理を簡素化します。
- GitHub Actions、テスト、公開成果物、利用者向け文書を更新します。
- 既存の利用者は、独自GeoJSON属性と内部履歴に依存しないよう移行が必要です。
