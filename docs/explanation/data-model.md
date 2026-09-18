edit only `data/places.jsonld`; do not edit `site/places.jsonld`, imports, snapshots, or generated distribution files.

# データモデル

`data/places.jsonld`は、公開Placeを記録するJSON-LD 1.1の正本です。編集対象はこのファイルだけです。
属性の完全な一覧と値の形式は、[属性リファレンス](../reference/attributes.md)を参照してください。

## 安全な編集入口

次の4段階で1件を編集します。

1. **既存の`@id`を特定します。** 対象のUUIDを完全一致で検索します。

   ```bash
   grep -n -F '"@id": "urn:uuid:<既存のUUID>"' data/places.jsonld
   ```

   検索結果が0件または複数件なら停止します。
2. **意図した値だけを変更します。** 対象recordの既存の`@id`を保持し、他のrecordと構造を変更しません。
3. **差分を確認します。** 次のコマンドで、変更対象と内容を確認します。

   ```bash
   git diff --name-only
   git diff -- data/places.jsonld
   git diff --check
   ```

   `data/places.jsonld`以外のファイル、対象外のrecord、または意図しない差分があれば停止します。
4. **検証を実行します。** 次のコマンドが失敗したら、公開せずに原因を直して再実行します。

   ```bash
   python3 -m src.fac_cli jsonld-validate data/places.jsonld
   python3 -m src.facility_data validate .
   ```

## JSON-LDの詳細

### 標準名前空間

`@context`はJSON-LD 1.1を指定し、次の標準名前空間を使います。通常は`schema`と`geo`を宣言し、`rdfs:seeAlso`を収録する場合だけ`rdfs`を追加します。

| 接頭辞 | 名前空間 | 用途 |
|---|---|---|
| `schema` | `https://schema.org/` | Placeと識別子 |
| `geo` | `http://www.opengis.net/ont/geosparql#` | 地理フィーチャーとPoint |
| `rdfs` | `http://www.w3.org/2000/01/rdf-schema#` | 明示された関連URI |

各recordの`@type`は、`schema:Place`と`geo:Feature`を含みます。`@id`は既存の`urn:uuid:<UUID>`を保持し、生成、短縮、置換しません。

### Place、位置、外部識別子

最小構造は次のとおりです。

```json
{
  "@id": "urn:uuid:<既存のUUID>",
  "@type": ["schema:Place", "geo:Feature"],
  "geo:hasGeometry": {
    "geo:asGeoJSON": {
      "@type": "geo:geoJSONLiteral",
      "@value": "{\"type\":\"Point\",\"coordinates\":[139.75,35.69]}"
    }
  },
  "schema:identifier": [
    {
      "@type": "schema:PropertyValue",
      "schema:propertyID": "openstreetmap",
      "schema:value": "node/123456"
    }
  ]
}
```

`coordinates`は必ず`[経度, 緯度]`の順で、2つの数値を持ちます。`schema:identifier`は`schema:PropertyValue`の配列です。`schema:propertyID`にソース名を、`schema:value`にソース側のrecord IDをそのまま設定します。IDからURIや別の識別子を推測しません。

### `rdfs:seeAlso`

`rdfs:seeAlso`は、入力に明示された解決可能なURIがある場合だけ収録します。record ID、ソース名、関連情報からURIを推測または生成しません。明示されたURIがなければ、この属性を省略します。

### 収録しない情報

公開recordには、識別子、型、Point、外部識別子、明示された関連URIだけを収録します。次の情報を追加しません。

- `audit`、`history`、`timestamps`、`votes`、`voteLog`などの運用情報
- `phone`、`images`、`rights`などの個人情報または補助情報
- `categoryIds`などのプロジェクト固有の分類

## 検証と公開を分ける

`jsonld-validate`は、JSON-LDの構文、識別子、型、Point、外部識別子を検証します。検証コマンドはファイルを確認するだけで、PagesやReleaseを公開・更新しません。検証処理の実装は[`src/facility_data.py`](../../src/facility_data.py)で確認できます。

レビューとmergeが完了した後、GitHub Pagesは[current JSON-LD](https://nawashiro.github.io/chiyoda_city_main_facilities/places.jsonld)を配布します。`site/places.jsonld`は配布用出力です。[Release workflow](../../.github/workflows/release-jsonld.yml)は、別の公開段階で版固定ファイルを作成し、[GitHub Releases](https://github.com/nawashiro/chiyoda_city_main_facilities/releases)へ添付します。
