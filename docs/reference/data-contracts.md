# データ契約

## 公開JSON-LD

`data/places.jsonld`を施設の正本とします。施設は一意な`urn:uuid:`のUUIDv7で識別し、`schema:Place`と、有効な経度・緯度を持つ`schema:GeoCoordinates`を設定します。

OSMとWikidataの公式HTTPS URIを`rdfs:seeAlso`へ設定します。OSM IDは`node/123`、`way/123`、`relation/123`を区別します。同じOSM IDを複数の施設へ割り当てません。

関連付けを置換すると古いOSM・Wikidata参照を取り除き、新しい候補の参照と座標へ更新します。候補なし、Jevの高信頼度の「該当なし」、人の「該当なし」では関連参照を取り除き、UUIDと座標を維持します。判断待ちの施設は前回の公開内容を保ちます。

Pagesは`site/places.jsonld`と両ミラーを配布します。Releaseは同じコミットのビルドから`places-<tag>.jsonld`、`osm-<tag>.json`、`wikidata-<tag>.json`を配布します。検索入力の`publish: false`に該当する施設を配布物から除きます。除外がなければ正本のバイト列をそのまま複製します。公開物に判断記録、取得物、履歴を含めません。

`site/index.html`には`schema:Dataset`、名称、説明、公開URL、JSON-LDの`DataDownload`と出典表示を埋め込みます。

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

