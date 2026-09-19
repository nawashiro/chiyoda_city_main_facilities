# CLI

作業者はリポジトリ root で `./fac` を実行します。

## 検証

```sh
./fac jsonld-validate data/places.jsonld
```

成功時、コマンドは出力しません。

## 検索入力を確認する

```sh
./fac in ls .
./fac in get . SEARCH_ID
```

`ls` は全検索入力の名称と ID を出力します。

## 検索入力を追加する

```sh
./fac in add . NAME --lon LONGITUDE --lat LATITUDE
./fac in add . NAME --qid QID
```

`in add` は経度と緯度の組、または Wikidata QID を受け取ります。

## 検索入力を編集する

```sh
./fac in set . SEARCH_ID --name NAME
./fac in set . SEARCH_ID --lon LONGITUDE --lat LATITUDE
./fac in set . SEARCH_ID --qid QID
```

`in set` は名称、経度と緯度の組、または Wikidata QID を変更します。

入力が不正な場合、コマンドは `ERROR: <理由>` を出力し、終了コード 1 で停止します。
