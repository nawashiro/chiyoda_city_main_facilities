# データ契約

## 公開JSON-LD

`data/places.jsonld`を施設の正本とします。施設は一意な`urn:uuid:`のUUIDv7で識別し、`schema:Place`と、有効な経度・緯度を持つ`schema:GeoCoordinates`を設定します。正本は施設だけを含み、カテゴリ参照と画像を含みません。

`python3 -m src.facility_data build .`は、正本、カテゴリ語彙`data/category-vocabulary.jsonld`、形状`data/dataset-shape.jsonld`、判断記録`data/categories.json`から`site/dataset.jsonld`を合成します。公開文書の`@graph`はPlace、`schema:DefinedTermSet`、`schema:DefinedTerm`、`sh:NodeShape`を含みます。Pagesは`site/dataset.jsonld`と両ミラーを配布します。Releaseは同じコミットのビルドから`dataset-<tag>.jsonld`、`osm-<tag>.json`、`wikidata-<tag>.json`を配布します。検索入力の`publish: false`に該当する施設は配布物から除きます。

カテゴリは`schema:keywords`で参照します。各カテゴリtermは`urn:uuid:`の`@id`、人間用の`schema:name`、`schema:identifier`の`gif-poi`コードを持ちます。Placeは判断のあるカテゴリtermを`schema:keywords`に並べます。複数カテゴリを許します。Placeは`gif-poi`の`schema:identifier`を持ちません。

公開文書はSHACLの`sh:NodeShape`を含み、`schema:geo`の必須、`schema:image`の単一、`schema:contentUrl`と`schema:license`の必須、`schema:creator`の任意と、`schema:creator`を出すときの`schema:name`必須を表します。カテゴリtermの形状はUUID、名前、`gif-poi`識別子を必須にします。

OSMとWikidataの公式HTTPS URIを`rdfs:seeAlso`へ設定します。OSM IDは`node/123`、`way/123`、`relation/123`を区別します。同じOSM IDを複数の施設へ割り当てません。

関連付けを置換すると古いOSM・Wikidata参照を取り除き、新しい候補の参照と座標へ更新します。候補なし、Jevの高信頼度の「該当なし」、人の「該当なし」では関連参照を取り除き、UUIDと座標を維持します。判断待ちの施設は前回の公開内容を保ちます。

建物と内部施設は別の`Place`として公開します。建物は建物のOSM要素（way・relation）に、内部施設は施設のOSM要素にそれぞれ関連付け、包含関係（`schema:containsPlace`など）は出力しません。カテゴリはそれぞれの実体に合わせます。同じ住所に建物と施設のrecordが並ぶことがあります。

`site/index.html`には`schema:Dataset`、名称、説明、公開URL、JSON-LDの`DataDownload`と出典表示を埋め込みます。

### カテゴリ参照の移行

以前の公開recordは`schema:identifier`の`gif-poi`でカテゴリコードを持っていました。現在はPlaceが`schema:keywords`で`schema:DefinedTerm`を参照し、コードはtermの`schema:identifier`にあります。利用者は次の順で読みます。

1. Placeの`schema:keywords`を読む。
2. 各`@id`のtermを`@graph`から探す。
3. termの`schema:identifier`から`gif-poi`コードを、`schema:name`から表示名を読む。

## カテゴリ判断

`data/categories.json`は施設UUIDごとのカテゴリ判断を保存します。エントリは`category`（4桁のGIF-POIコード）、`method`（`rule`、`jev`、`human`）、`osmId`を持ちます。公開recordへの反映はビルドが行い、`category assign`と`category clear`は判断記録だけを更新します。

カテゴリ語彙`data/category-vocabulary.jsonld`は非公開のソースです。一つの`schema:DefinedTermSet`と`schema:DefinedTerm`を持ち、termの`@id`はUUIDv5です。ソースは公開distributionとして配布しません。

## 検索入力

`inputs/facilities.json`の`queries`を人が編集します。配列順は照合結果へ影響しません。

| 項目 | 契約 |
| --- | --- |
| `id` | 施設のUUIDv7。同じファイル内で一意。正本にある施設は同じUUIDを使う |
| `name` | 空でない施設名 |
| `coordinates` | `[経度, 緯度]`。有効範囲の数値 |
| `qid` | Wikidataの`Q`と正の整数からなるID |
| `publish` | 任意の真偽値。`false`は公開除外。検索対象は維持する |

`coordinates`か`qid`の少なくとも一方が必要です。両方を指定できます。検索例は次のとおりです。

```json
{
  "queries": [{
    "id": "019c0000-0000-7000-8000-000000000001",
    "name": "千代田相談支援センター",
    "coordinates": [139.75, 35.69]
  }]
}
```


## 判断記録

`data/osm-decisions.json`は施設ごとのOSM関連付けの判断を保存します。エントリは`status`を持ち、`decided`、`no_candidates`、`needs_review`、`hold`のいずれかです。

`status: hold`は実地調査を待つ保留です。`reason`、`previous`（解除したOSM ID。なければ`null`）、`human`（`editor`と`editedAt`）を必要とし、専用CLIの`./fac assoc --hold`だけが記録します。保留中はOSM参照とWikidata参照を公開せず、カテゴリ判断も取り消します。解除は`./fac assoc --osm-id`または`./fac assoc --choice none`で行います。
