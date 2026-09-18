# Placeを直接保守する

このハウツーは、`data/places.jsonld`の1件を直接編集し、検証してGitレビューへ出す手順です。
`@graph`の各recordをPlaceとして扱います。

## 1. 作業branchを準備する

既存checkoutでは、作業前に状態を確認します。

```bash
git status --short
git switch -c data/<作業内容>
```

変更前の検証を実行します。

```bash
python3 -m src.fac_cli jsonld-validate data/places.jsonld
python3 -m src.facility_data validate .
python3 -m unittest discover -s tests -v
```

検証に失敗した場合、データを編集しません。

## 2. 対象Placeを探す

`data/places.jsonld`をUTF-8のテキストとして開きます。
`@graph`から、対象の`@id`と一致するrecordを探します。

```text
urn:uuid:<UUID>
```

`@id`のUUIDを生成、短縮、置換しません。
対象外のrecordの順序と内容を変更しません。

## 3. 標準プロパティを編集する

`@type`には`schema:Place`と`geo:Feature`を残します。
Point geometryは、次のGeoSPARQL構造を保ちます。

```json
"geo:hasGeometry": {
  "geo:asGeoJSON": {
    "@type": "geo:geoJSONLiteral",
    "@value": "{\"type\":\"Point\",\"coordinates\":[139.75,35.69]}"
  }
}
```

`@value`はJSON文字列です。
`coordinates`は`[経度,緯度]`の順序で指定します。
`@type`と`@value`を通常のJSONオブジェクトへ置き換えません。

外部識別子は`schema:identifier`の配列へ追加または修正します。
各要素は`schema:PropertyValue`として、文字列の`schema:propertyID`と`schema:value`を持たせます。

```json
"schema:identifier": [
  {
    "@type": "schema:PropertyValue",
    "schema:propertyID": "openstreetmap",
    "schema:value": "node/123456"
  }
]
```

確認できない識別子を追加しません。
識別子からURLや別のIDを推測して作りません。

## 4. 意図しない変更を防ぐ

値を1つ変更するとき、JSON全体を整形し直しません。
キーの順序、インデント、改行、エスケープ、末尾改行を維持します。
変更対象のPlaceの`@id`と、変更対象外のバイトを維持します。

運用履歴、監査記録、更新時刻、投票記録をPlaceへ追加しません。
非公開フィールドや作業者向けの補助情報をPlaceへ追加しません。

## 5. 変更後に検証する

```bash
python3 -m src.fac_cli jsonld-validate data/places.jsonld
python3 -m src.facility_data validate .
python3 -m unittest discover -s tests -v
git diff --check
```

`jsonld-validate`はJSON-LDの構造、ID、Point geometry、識別子を確認します。
repository validationは関連する入力とPlaceの整合性を確認します。
テストが失敗した場合、失敗原因を直してから差分を再確認します。

## 6. Gitでレビューする

```bash
git diff -- data/places.jsonld
git diff --check
```

差分が対象Placeの意図した変更だけを含むことを確認します。
レビューでは、UUID、標準プロパティ、GeoSPARQL literal、`schema:PropertyValue`の値を確認します。
検証成功後にcommitとPull Requestを作成します。

## 7. 公開を確認する

Pull Requestの検証が成功してから変更をmergeします。
GitHub Pagesはcurrent JSON-LDを公開します。

- Dataset: <https://nawashiro.github.io/chiyoda_city_main_facilities/>
- current JSON-LD: <https://nawashiro.github.io/chiyoda_city_main_facilities/places.jsonld>

公開版を固定して配布するとき、GitHub Releaseを作成します。
Release workflowは検証済み`data/places.jsonld`から版固定snapshotを作成します。
