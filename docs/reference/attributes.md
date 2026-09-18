# `data/places.jsonld` 属性リファレンス

この文書は、公開正本 `data/places.jsonld` だけを説明します。
このファイルは、JSON-LD 1.1 で施設の識別子、位置、外部識別子を表します。

## 公開URL

| 配布物 | URL | 内容 |
|---|---|---|
| GitHub Pages | `https://nawashiro.github.io/chiyoda_city_main_facilities/` | Dataset の案内ページ |
| current JSON-LD | `https://nawashiro.github.io/chiyoda_city_main_facilities/places.jsonld` | 現在の `data/places.jsonld` |
| GitHub Releases | `https://github.com/nawashiro/chiyoda_city_main_facilities/releases` | 版固定スナップショットの一覧 |
| Release snapshot | `https://github.com/nawashiro/chiyoda_city_main_facilities/releases/download/<tag>/places-<tag>.jsonld` | 指定したタグの JSON-LD |

GitHub Pages は現在のデータを配布します。
GitHub Release は `places-<tag>.jsonld` として版固定データを添付します。

## 文書の構造

ファイルのトップレベルは、次の2属性を持ちます。

| 属性 | 型 | 説明 |
|---|---|---|
| `@context` | オブジェクト | JSON-LD 1.1 の語彙と処理規則を宣言します。 |
| `@graph` | 配列 | `schema:Place` のレコードを並べます。 |

### `@context`

現行の `@context` は次の内容です。

```json
{
  "@version": 1.1,
  "geo": "http://www.opengis.net/ont/geosparql#",
  "schema": "https://schema.org/"
}
```

| 項目 | 値 | 説明 |
|---|---|---|
| `@version` | `1.1` | JSON-LD 1.1 を指定します。仕様は [JSON-LD 1.1](https://www.w3.org/TR/json-ld11/) です。 |
| `schema` | `https://schema.org/` | Schema.org 語彙を指定します。 |
| `geo` | `http://www.opengis.net/ont/geosparql#` | OGC GeoSPARQL 語彙を指定します。 |

`rdfs:seeAlso` を収録するレコードは、`rdfs` に `http://www.w3.org/2000/01/rdf-schema#` を割り当てます。
RDF Schema の `seeAlso` は、[rdfs:seeAlso](http://www.w3.org/2000/01/rdf-schema#seeAlso) で定義されます。

## Place レコード

`@graph` の各レコードは、次の属性を持ちます。

| 属性 | 型 | 値または形式 | 説明 |
|---|---|---|---|
| `@id` | 文字列 | `urn:uuid:<UUID>` | 施設の永続識別子です。 |
| `@type` | 配列 | `schema:Place`、`geo:Feature` | 施設と地理フィーチャーの標準型を指定します。 |
| `geo:hasGeometry` | オブジェクト | `geo:asGeoJSON` を含む | 施設の位置を指定します。 |
| `schema:identifier` | 配列 | `schema:PropertyValue` の配列 | 外部データの識別子を指定します。該当する識別子がない場合は空配列です。 |
| `rdfs:seeAlso` | URI文字列 | 明示された解決可能URI | 入力が明示的に与えた関連URIがある場合だけ指定します。 |

`@type` は、Schema.org の [Place](https://schema.org/Place) と GeoSPARQL の [Feature](http://www.opengis.net/ont/geosparql#Feature) を必ず含みます。

`@id` は、ドメイン名に依存しない `urn:uuid` 識別子です。
この識別子を、Webで解決できるURLとして扱いません。

### 位置情報

`geo:hasGeometry` の値はオブジェクトです。
このオブジェクトは `geo:asGeoJSON` を持ちます。

`geo:asGeoJSON` は、次の2属性を持ちます。

| 属性 | 値 | 説明 |
|---|---|---|
| `@type` | `geo:geoJSONLiteral` | GeoJSON リテラル型を指定します。語彙は [geoJSONLiteral](http://www.opengis.net/ont/geosparql#geoJSONLiteral) です。 |
| `@value` | JSON文字列 | GeoJSON の `Point` を文字列で指定します。 |

`@value` の文字列は、次の形式です。

```json
{"type":"Point","coordinates":[経度,緯度]}
```

`coordinates` は、経度、緯度の順に2つの数値を持ちます。
`Point` 以外のジオメトリ型を収録しません。

### 外部識別子

`schema:identifier` の各要素は、次の [PropertyValue](https://schema.org/PropertyValue) オブジェクトです。

| 属性 | 値または形式 | 説明 |
|---|---|---|
| `@type` | `schema:PropertyValue` | 識別子の値を構造化する標準型です。 |
| `schema:propertyID` | 文字列 | 識別子を発行したソースの識別子です。Schema.org の [propertyID](https://schema.org/propertyID) に対応します。 |
| `schema:value` | 文字列 | ソース内のレコード識別子です。Schema.org の [value](https://schema.org/value) に対応します。 |

`schema:propertyID` に `openstreetmap` や `wam` を設定します。
`schema:value` に、ソースが示すレコード識別子をそのまま設定します。
識別子から新しいURIを推測または合成しません。

### `rdfs:seeAlso`

`rdfs:seeAlso` は任意属性です。
入力に解決可能なURIが明示されている場合だけ、そのURIを設定します。

外部レコードのID、ソース名、関連リンクだけから `rdfs:seeAlso` を生成しません。
明示されたURIがないレコードは、この属性を省略します。
現行の `data/places.jsonld` は `rdfs:seeAlso` を収録しません。

## 意図的に収録しない属性

次の属性は、`data/places.jsonld` の仕様に含めません。

| 属性 | 除外理由 |
|---|---|
| `audit` | 操作の監査記録を公開しません。 |
| `history` | 参照や更新の履歴をPlaceへ含めません。 |
| `timestamps` | 取得、確認、変更の時刻をPlaceへ含めません。 |
| `votes` | 自動照合や人手評価の投票を公開しません。 |
| `town` | 位置から導出する町名を公開しません。 |
| `phone` | 電話番号を公開しません。 |
| `images` | 画像を公開しません。 |
| `rights` | 画像に関する権利表記を公開しません。 |
| `categoryIds` | プロジェクト固有の分類IDを公開しません。 |

除外属性を、別名の独自属性へ置き換えません。
