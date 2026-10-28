# データ契約

## 公開JSON-LD

`data/places.jsonld`を施設の正本とします。施設は一意な`urn:uuid:`のUUIDv7で識別し、`schema:Place`と、有効な経度・緯度を持つ`schema:GeoCoordinates`を設定します。

OSMとWikidataの公式HTTPS URIを`rdfs:seeAlso`へ設定します。OSM IDは`node/123`、`way/123`、`relation/123`を区別します。同じOSM IDを複数の施設へ割り当てません。

関連付けを置換すると古いOSM・Wikidata参照を取り除き、新しい候補の参照と座標へ更新します。候補なし、Jevの高信頼度の「該当なし」、人の「該当なし」では関連参照を取り除き、UUIDと座標を維持します。判断待ちの施設は前回の公開内容を保ちます。

Pagesは`site/places.jsonld`、Releaseは`places-<tag>.jsonld`を配布します。検索入力の`publish: false`に該当する施設を配布物から除きます。除外がなければ正本のバイト列をそのまま複製します。公開物に判断記録、取得物、履歴を含めません。

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

## 判断記録

`data/osm-decisions.json`は`version: 1`、`facilities`を持ちます。`facilities`は施設UUIDをキーにした生成記録です。人の回答はIssue本文で受け付け、記録を直接編集して回答しません。

| 項目 | 内容 |
| --- | --- |
| `evidence`、`evidenceHash` | 対象の名称・検索座標・QID、候補の型付きID・名称・座標・QID・識別用タグとSHA-256 |
| `status` | `decided`、`needs_review`、`no_candidates` |
| `method`、`choice` | `human`、`source_record`、`qid`、`jev`などの方法と、型付きIDまたは`none` |
| `jev` | モデル、選択、信頼度、確率、入力・出力トークン数 |
| `human` | 確定した選択、編集者、編集日時、Issue URL |
| `issue` | 人の回答を受け付けた確認Issueの番号 |
| `current`、`reason` | 判定時の既存参照と確認理由 |

根拠の候補は型付きID順に正規化します。取得日時や候補の配列順はハッシュへ含めません。識別用タグは`IDENTITY_TAGS`の許可リストに限定し、Jevに渡す内容と保存内容を一致させます。採用済みの接続は取得結果に残る間維持し、ハッシュの一致に依存しません。人の「該当なし」と未解決のJev結果は同じ根拠で再利用します。

`no_candidates`は取得が成功して候補がなかった状態です。人またはJevの`none`とは記録上区別しますが、どちらも参照を解除して一括通知の対象にします。APIの障害をこの状態へ変換しません。
