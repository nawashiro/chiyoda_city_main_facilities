# CLI

作業者は `python3 -m src.fac_cli` を実行します。リポジトリ root は既定で `.` です。

## 検証

```sh
python3 -m src.fac_cli jsonld-validate data/places.jsonld
```

成功時、コマンドは出力しません。

## 施設を確認する

```sh
python3 -m src.fac_cli ls .
python3 -m src.fac_cli get . PLACE_ID
```

`ls` はカテゴリ、名称、OSM 状態、存続状態で絞り込めます。

## 施設を編集する

```sh
python3 -m src.fac_cli set . PLACE_ID --cat CATEGORY --at 2026-09-18T00:00:00+00:00
python3 -m src.fac_cli ref . PLACE_ID osm node/123 --at 2026-09-18T00:00:00+00:00
```

`ref` の `none` は OSM 参照を解除します。

## 検索入力を編集する

```sh
python3 -m src.fac_cli in ls .
python3 -m src.fac_cli in get . SEARCH_ID
python3 -m src.fac_cli in add . --name NAME --lon LONGITUDE --lat LATITUDE
```

`in add` と `in set` は、経度と緯度の組、または QID を受け取ります。

入力が不正な場合、コマンドは標準エラーへ `ERROR: <理由>` を出力し、終了コード 1 で停止します。
