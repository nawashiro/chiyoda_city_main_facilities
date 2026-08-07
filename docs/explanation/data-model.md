# データモデル

## 3つの層

このrepositoryは、検索入力、Place正本、公開GeoJSONを分けます。

検索入力はOSM同定のための入力です。
`data/registry.json`は唯一のPlace正本です。
`dist/public/places.geojson`は正本から生成する公開用の派生物です。

検索入力のUUIDv7は、対応するPlaceへ引き継ぎます。
正本の`name`は検索入力語と一致します。

## 代表点

代表点は次の優先順位で採用します。

1. WAM
2. OSM (OpenStreetMap)
3. 検索入力座標

PlaceはPointだけを保持します。
公開GeoJSONはPolygon、relation member、過去OSM IDを含めません。

## 公開範囲

`visibility.status`が`public`のPlaceだけを公開GeoJSONへ出力します。
`private`は正本と監査を保持しますが、公開Featureを出力しません。

公開Featureは画像、OSM属性、WAM属性をソース別名前空間で保持します。

## 保守範囲

このDBは網羅性より、単独保守と誤案内の回避を優先します。
外部ソースから消えたことだけを理由に、Placeを削除しません。

WAMは計画相談支援、地域移行、地域定着、障害児相談支援だけを対象にします。
OSMの曖昧候補は、訪問者、利用者、現地スタッフの3視点で判断します。
2票以上が一致した候補またはrejectを自動処理します。

詳細な契約は[保守仕様](../reference/data-maintenance-spec.md)を参照してください。
