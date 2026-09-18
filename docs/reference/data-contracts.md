# データ契約

## 正本と公開物

作業者は `data/places.jsonld` を正本として扱います。

`site/places.jsonld` は正本の公開コピーです。両ファイルはバイト単位で一致させます。

`site/index.html` は JSON-LD データセットを埋め込みます。埋め込みは `schema:Dataset`、データセット名、説明、公開 URL、`DataDownload` を含めます。

`DataDownload` は `places.jsonld` と `application/ld+json` を示します。

## 施設の不変条件

作業者は、UUIDv7 の一意な施設 ID を使います。

作業者は、有効な経緯度順の Point を設定します。

作業者は、検索名と施設名を整合させます。

作業者は、施設ごとに current の OSM 参照を一件まで設定します。

作業者は、同じ OSM 記録を複数の施設へ割り当てません。

作業者は、WAM と OSM の由来、取得物のハッシュ、監査記録を保持します。

公開物は公開施設だけを含めます。

## 座標と照合

更新処理は座標を WAM、OSM、検索入力の順に採用します。

OSM は QID、名称と 50m 以内の座標、または既存参照で照合します。
