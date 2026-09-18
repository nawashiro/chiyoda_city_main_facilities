# OpenStreetMap を更新する

この手順は、OpenStreetMap の取得結果を正規化する作業者向けです。

## 1. 問い合わせを作る

```sh
python3 -m src.update_osm query . > /tmp/osm-query.txt
```

作業者は、生成した問い合わせを OpenStreetMap の取得先へ送信します。作業者は、応答 JSON を追跡可能な場所へ保存します。

## 2. 出力を退避する

```sh
cp imports/openstreetmap/normalized.json /tmp/osm-normalized.json.before
cp imports/openstreetmap/retrieval.json /tmp/osm-retrieval.json.before
```

## 3. 正規化する

生データは `version` 文字列と `elements` 配列を持つ必要があります。

```sh
python3 -m src.update_osm normalize . --raw RAW_JSON --at ACTUAL_RETRIEVED_AT
```

作業者は、実際の取得日時をタイムゾーン付き ISO 8601 形式で指定します。処理は正規化済み記録と取得記録を上書きします。

## 4. 結果を確認する

```sh
python3 -m src.facility_data validate .
git diff -- imports/openstreetmap
```

作業者は、重複 QID、raw 形式エラー、必須引数エラーを解消してから再実行します。これらのエラー時、処理は出力を更新しません。

処理を中断した場合、作業者は次を実行して退避版を復元します。

```sh
cp /tmp/osm-normalized.json.before imports/openstreetmap/normalized.json
cp /tmp/osm-retrieval.json.before imports/openstreetmap/retrieval.json
```

作業者は、復元後に `python3 -m src.facility_data validate .` を実行します。
