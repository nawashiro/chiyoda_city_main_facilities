# WAM NET を更新する

この手順は、WAM NET の取得済み JSON を正規化する作業者向けです。

## 1. 出力を退避する

```sh
cp imports/wam/normalized.json /tmp/wam-normalized.json.before
cp imports/wam/retrieval.json /tmp/wam-retrieval.json.before
```

この処理は二つのファイルを順次上書きします。作業者は、実行中断に備えて両方を退避します。

## 2. 生データを確認する

作業者は、生データに空でない `version` と `rows` 配列があることを確認します。

作業者は、実際の取得日時をタイムゾーン付き ISO 8601 形式で記録します。

## 3. 正規化する

```sh
python3 src/update_wam.py RAW_JSON . --at ACTUAL_RETRIEVED_AT
```

処理は `imports/wam/normalized.json` を生成します。処理は `imports/wam/retrieval.json` の取得日時と生データ版も更新します。

## 4. 結果を確認する

```sh
python3 -m src.facility_data validate .
git diff -- imports/wam
```

処理が失敗または中断した場合、作業者は次を実行して退避版を復元します。

```sh
cp /tmp/wam-normalized.json.before imports/wam/normalized.json
cp /tmp/wam-retrieval.json.before imports/wam/retrieval.json
python3 -m src.facility_data validate .
git diff -- imports/wam
```

作業者は、入力、生データ版、取得日時を確認してから再実行します。
