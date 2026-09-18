# `data/places.jsonld` 属性リファレンス

## 初めて読む人へ

`data/places.jsonld` は、公開する施設（Place）の正本です。[JSON-LD 1.1](https://www.w3.org/TR/json-ld11/) の `@context` が語彙を宣言し、`@graph` が施設レコードを配列で持ちます。

各 `@graph[]` は1施設です。最初に必須構造を確認し、その後で外部識別子と任意の関連URIを確認してください。

### 最小のレコード形

次の例は、必須構造だけを示します。`<UUID>` は説明用の置換文字列です。

```json
{
  "@context": {
    "@version": 1.1,
    "geo": "http://www.opengis.net/ont/geosparql#",
    "schema": "https://schema.org/"
  },
  "@graph": [
    {
      "@id": "urn:uuid:<UUID>",
      "@type": ["schema:Place", "geo:Feature"],
      "geo:hasGeometry": {
        "geo:asGeoJSON": {
          "@type": "geo:geoJSONLiteral",
          "@value": "{\"type\":\"Point\",\"coordinates\":[139.7535624,35.6941626]}"
        }
      }
    }
  ]
}
```

`schema:identifier` と `rdfs:seeAlso` は任意です。現行の正本は、外部識別子がない場合も `schema:identifier` に空配列 `[]` を記録します。

## 必須・任意の一覧

### 文書

| 状態 | JSONパス | 型 | 値・制約 |
|---|---|---|---|
| 必須 | `@context` | オブジェクト | JSON-LD 1.1 の語彙を宣言します。 |
| 必須 | `@context.@version` | 数値 | `1.1` を指定します。 |
| 必須 | `@context.geo` | 文字列 | `http://www.opengis.net/ont/geosparql#` を指定します。 |
| 必須 | `@context.schema` | 文字列 | `https://schema.org/` を指定します。 |
| 任意 | `@context.rdfs` | 文字列 | `rdfs:seeAlso` を使う場合だけ `http://www.w3.org/2000/01/rdf-schema#` を指定します。 |
| 必須 | `@graph` | 配列 | Placeレコードを並べます。 |
| 必須 | `@graph[]` | オブジェクト | 1施設のレコードです。 |

### Placeレコード

| 状態 | JSONパス | 型 | 値・制約 |
|---|---|---|---|
| 必須 | `@graph[].@id` | 文字列 | 一意な `urn:uuid:<UUID>` です。 |
| 必須 | `@graph[].@type` | 配列 | `schema:Place` と `geo:Feature` を含みます。 |
| 必須 | `@graph[].geo:hasGeometry` | オブジェクト | Pointの位置情報を持ちます。 |
| 任意 | `@graph[].schema:identifier` | 配列 | 外部識別子の `schema:PropertyValue` を並べます。 |
| 任意 | `@graph[].rdfs:seeAlso` | URI文字列 | 入力に明示された解決可能URIがある場合だけ指定します。 |

`@graph[].@type` の `schema:Place` は [Place](https://schema.org/Place) を、`geo:Feature` は GeoSPARQL の [Feature](http://www.opengis.net/ont/geosparql#Feature) を表します。

## `@context` と名前空間

現行の必須コンテキストは次のとおりです。

```json
{
  "@version": 1.1,
  "geo": "http://www.opengis.net/ont/geosparql#",
  "schema": "https://schema.org/"
}
```

`rdfs:seeAlso` を使うレコードだけ、`rdfs` を次の名前空間へ割り当てます。

```json
"rdfs": "http://www.w3.org/2000/01/rdf-schema#"
```

RDF Schema の `seeAlso` は [rdfs:seeAlso](http://www.w3.org/2000/01/rdf-schema#seeAlso) で定義されます。現行の `data/places.jsonld` は `rdfs:seeAlso` を収録しません。

## Placeの識別子と型

`@graph[].@id` はレコードを一意に識別します。既存の `@id` は値をそのまま保持し、短縮、再生成、置換をしません。

新しいレコードのIDには、一意な `urn:uuid:<UUID>` を指定します。既存レコードと重複するIDを指定しません。確認できない識別子やURIを推測して作りません。

`@id` はドメイン名に依存しないURNです。Webで解決できるURLとして扱いません。

## Pointの位置情報

`@graph[].geo:hasGeometry` は、次のGeoSPARQL構造を必ず持ちます。

| 状態 | JSONパス | 型 | 値・制約 |
|---|---|---|---|
| 必須 | `@graph[].geo:hasGeometry` | オブジェクト | `geo:asGeoJSON` を持ちます。 |
| 必須 | `@graph[].geo:hasGeometry.geo:asGeoJSON` | オブジェクト | GeoJSONリテラルを持ちます。 |
| 必須 | `@graph[].geo:hasGeometry.geo:asGeoJSON.@type` | 文字列 | `geo:geoJSONLiteral` ([語彙](http://www.opengis.net/ont/geosparql#geoJSONLiteral)) を指定します。 |
| 必須 | `@graph[].geo:hasGeometry.geo:asGeoJSON.@value` | 文字列 | Pointを表す1つのJSON文字列です。 |

`geo:geoJSONLiteral.@value` は、入れ子のオブジェクトではなく、1つのJSON文字列です。文字列をJSONとして読むと、次のオブジェクトになります。

```json
{"type":"Point","coordinates":[経度, 緯度]}
```

`coordinates` は必ず `[経度, 緯度]` の順で、2つの数値を持ちます。`Point` 以外のジオメトリ型を収録しません。

現行データの実例は次のとおりです。

```json
"geo:hasGeometry": {
  "geo:asGeoJSON": {
    "@type": "geo:geoJSONLiteral",
    "@value": "{\"type\":\"Point\",\"coordinates\":[139.7535624,35.6941626]}"
  }
}
```

## 外部識別子

`@graph[].schema:identifier` は任意です。属性を置く場合、値は `schema:PropertyValue` の配列です。外部識別子がない現行レコードは `[]` を使います。

| 状態 | JSONパス | 型 | 値・制約 |
|---|---|---|---|
| 必須（要素ごと） | `@graph[].schema:identifier[].@type` | 文字列 | `schema:PropertyValue` を指定します。 |
| 必須（要素ごと） | `@graph[].schema:identifier[].schema:propertyID` | 文字列 | 識別子を発行したソースの識別子です。 |
| 必須（要素ごと） | `@graph[].schema:identifier[].schema:value` | 文字列 | ソース側のレコード識別子です。 |

`schema:propertyID` と `schema:value` は、入力が示す値をそのまま設定します。たとえば `openstreetmap` の `node/1420770185` や `wam` のレコードIDを指定します。識別子から新しいID、URI、IRIを推測または合成しません。

現行データの実例は次のとおりです。`schema:PropertyValue` は [PropertyValue](https://schema.org/PropertyValue)、`schema:propertyID` は [propertyID](https://schema.org/propertyID)、`schema:value` は [value](https://schema.org/value) に対応します。

```json
"schema:identifier": [
  {
    "@type": "schema:PropertyValue",
    "schema:propertyID": "openstreetmap",
    "schema:value": "node/1420770185"
  }
]
```

複数の外部識別子がある場合は、1つのPlaceレコード内に要素を追加します。外部サービスのレコードを施設レコードとして複製しません。

## `rdfs:seeAlso` の扱い

`@graph[].rdfs:seeAlso` は任意属性です。入力に明示された解決可能URIがある場合だけ、そのURIを設定します。URIが明示されていないレコードでは、この属性を省略します。

外部レコードのID、ソース名、関連リンクだけから `rdfs:seeAlso` を生成しません。`schema:value` からURIを組み立てません。`schema:sameAs`、SKOSのmatch関係、Place単位の `prov:wasDerivedFrom` も自動出力しません。

## 公開しない項目

公開Placeは、識別子、型、Point、外部識別子、必要に応じた関連URIだけを持ちます。次のJSONパスは収録しません。

- `@graph[].audit`、`@graph[].history`、`@graph[].timestamps`、`@graph[].votes`
- `@graph[].town`、`@graph[].phone`、`@graph[].images`、`@graph[].rights`
- `@graph[].categoryIds`

これらは監査、履歴、時刻、投票、派生した町名、電話番号、画像、権利表記、独自分類の項目です。公開Placeへ別名の独自属性として追加しません。

## 公開URL

- GitHub Pages: <https://nawashiro.github.io/chiyoda_city_main_facilities/>（Datasetの案内ページ）
- current JSON-LD: <https://nawashiro.github.io/chiyoda_city_main_facilities/places.jsonld>（現在の `data/places.jsonld`）
- GitHub Releases: <https://github.com/nawashiro/chiyoda_city_main_facilities/releases>（版固定スナップショットの一覧）
- Release snapshot: `https://github.com/nawashiro/chiyoda_city_main_facilities/releases/download/<tag>/places-<tag>.jsonld`

GitHub Pagesは現在のデータを配布します。GitHub Releaseは `places-<tag>.jsonld` として版固定データを添付します。
