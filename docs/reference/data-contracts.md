# データ契約

## 正本と公開物

作業者は `data/places.jsonld` を唯一の正本として扱います。

`site/places.jsonld` は正本の公開コピーです。作業者は両ファイルをバイト単位で一致させます。

`site/index.html` は JSON-LD データセットを埋め込みます。埋め込みは `schema:Dataset`、データセット名、説明、公開 URL、`DataDownload` を含めます。

`DataDownload` は `places.jsonld` と `application/ld+json` を示します。GitHub Release は同じ正本の版固定 `places-<tag>.jsonld` を添付します。

公開経路は JSON-LD だけです。`registry.json`、GeoJSON、manifest は正本、公開コピー、Release snapshot に存在しません。

## 施設 record

作業者は UUIDv7 の一意な施設 ID を使います。

作業者は `schema:geo` に `schema:GeoCoordinates` を設定します。作業者は `schema:latitude` と `schema:longitude` に有効な座標を設定します。

作業者は OSM と Wikidata の公式 HTTPS URI を `rdfs:seeAlso` へ設定します。

作業者は WAM record ID を `schema:identifier` の `schema:PropertyValue` へ設定します。作業者は WAM record ID から URI を合成しません。

公開物は公開施設だけを含めます。公開物は registry、監査履歴、current/superseded 参照履歴を含めません。

## 座標と照合

更新処理は座標を WAM、OSM、検索入力の順に採用します。

OSM は QID、名称と 50m 以内の座標、または既存参照で照合します。
