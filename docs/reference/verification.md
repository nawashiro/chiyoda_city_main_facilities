# 検証

作業者は、変更後に次の手順をリポジトリ root で実行します。

## 全体検証

```sh
python3 -m unittest discover -s tests -v
python3 -m src.facility_data validate .
python3 -m src.fac_cli jsonld-validate data/places.jsonld
cmp data/places.jsonld site/places.jsonld
git diff --check
```

## 正本の不変性

作業者は、既存の `data/places.jsonld` を `build` が上書きしないことを確認します。

```sh
cp data/places.jsonld /tmp/places.jsonld.before
python3 -m src.facility_data build .
python3 -m src.fac_cli jsonld-validate data/places.jsonld
cmp /tmp/places.jsonld.before data/places.jsonld
```

`cmp` が失敗した場合、作業者は処理を止めて差分の原因を確認します。作業者は、意図しない正本の変更をコミットしません。

公開物だけを確認する場合、作業者は次を実行します。

```sh
python3 -m unittest tests/test_dataset_publication.py
```
