# 千代田区主要施設データベース

千代田区で「生活する・助けてもらう・楽しむ」ために訪れる主要施設を、小規模に保守するデータベースです。

## 公開データ

公開物はPointだけを収録したGeoJSONです。

```text
https://cdn.jsdelivr.net/gh/nawashiro/chiyoda_city_main_facilities@<version>/dist/public/places.geojson
```

本番利用では`latest`ではなくリリースまたはコミットを指定してください。`dist/public/manifest.json`のSHA-256で取得物を確認できます。

公開GeoJSONには名称、分類、製品タグ、代表点、派生町名だけを含めます。OSM ID履歴、監査記録、OSM・町名ポリゴンは含めません。

## データ構成

- `inputs/osm-search/`: OSM同定用の検索入力。正本ではありません
- `data/registry.json`: 唯一のPlace正本
- `schema/`: 検索入力、正本、公開GeoJSONの契約
- `dist/public/places.geojson`: 正本から生成する公開用派生物
- `reports/`: 一時移行や更新結果の短いレポート
- `img/`: 正本から参照する画像

検索入力は次のいずれかです。

```text
UUIDv7 + name + coordinates
UUIDv7 + name + qid
```

同じUUIDを正本Placeへ引き継ぎます。正本の`name`は検索入力語だけです。座標はWAM、OSM、検索入力座標の順で採用します。

## 検証と生成

外部パッケージは不要です。Python 3.13で実行します。

```bash
python3 -m unittest discover -s tests -v
python3 -m src.facility_data validate .
python3 -m src.facility_data build .
```

公開ファイルを直接編集してはいけません。検索入力または`data/registry.json`を更新し、検証後に再生成します。

## 運用方針

- UUID重複を許容しない
- 50m以内だけをOSM候補にし、自動的に距離を広げない
- 曖昧な低リスク同定は3票すべて有効かつ2票以上一致した場合だけ採用する
- 削除、統合、恒久的な非公開化を合議だけで自動確定しない
- 監査記録は`at`、`method`、`action`、`target`だけにする
- 外部ソース取得はソースごとに月1回以下にする

詳しい設計は[`doc/data_maintenance_spec.md`](doc/data_maintenance_spec.md)を参照してください。

## ライセンスと出典

ソースごとのライセンスと公開時の帰属は[`SOURCES_AND_LICENSES.md`](SOURCES_AND_LICENSES.md)および[`config/sources.json`](config/sources.json)に記録しています。
