# データソースとライセンス

このリポジトリは、由来と利用条件の異なる複数のデータを含みます。正本の編集値と、公開GeoJSONへソース別名前空間で直接含める外部レコードでは適用条件が異なります。再配布時は`sourceAttributions`と本書を確認してください。

機械可読なソース台帳は [`config/sources.json`](config/sources.json) です。

## プロジェクトのデータベース

READMEで従来から宣言しているとおり、データベースは Open Data Commons Open Database License 1.0 の条件で提供します。全文は [`LICENSE`](LICENSE) を参照してください。

- License: Open Data Commons Open Database License 1.0
- URL: https://opendatacommons.org/licenses/odbl/1-0/

正本と互換GeoJSON全体を単一の包括ライセンスだけで説明しません。個別の画像、説明、町名、OSMタグ、Wikidataレコード、WAMレコード等には、下記に示す各ソースの条件が適用されます。

## OpenStreetMap

- 出典: © OpenStreetMap contributors
- URL: https://www.openstreetmap.org/copyright
- License: Open Data Commons Open Database License 1.0

## Wikidata

- URL: https://www.wikidata.org/wiki/Wikidata:Licensing
- License: Creative Commons CC0 1.0 Universal
- 用途: 以前のOSM同定で同じ地物を指すと確認できたItem IDを、名前と組み合わせた次回のOSM検索入力として利用
- 注意: Wikidata Itemを内部主キーにせず、組織・建物・サービスとの対象範囲が一致しないItemを登録しない

## 旧データの出典（新設計では自動取込対象外）

### 東京都福祉局 保育所データ

- 出典: 東京都福祉局
- URL: https://catalog.data.metro.tokyo.lg.jp/dataset/t000054d0000000356/resource/f41234cd-bcf2-46df-90fc-6cc7d8398321
- License: Creative Commons Attribution 4.0 International

### 千代田区 幼稚園データ・公共施設一覧

- 出典: 千代田区
- 幼稚園: https://catalog.data.metro.tokyo.lg.jp/dataset/t131016d0000000007
- 公共施設一覧: https://catalog.data.metro.tokyo.lg.jp/dataset/t131016d0000000001
- License: Creative Commons Attribution 4.0 International

これらは旧JSONの来歴表示のために残します。新正本への継続取込ソースにはしません。

## 千代田区町名GeoJSON

- リポジトリ: https://github.com/nawashiro/chiyoda_city_town_geojson
- 元データ・表示: © Linked Open Addresses Japan
- License: Creative Commons Attribution-ShareAlike 4.0 International
- License URL: https://creativecommons.org/licenses/by-sa/4.0/
- 加工内容: 元データから丁目以降を削除し、ポリゴンを統合

町名は正本へ書き込まず、版固定した町名GeoJSONと正本代表点のpoint-in-polygonにより公開GeoJSON生成時だけ導出します。

## 日立自動車交通 風ぐるまGTFS

- 出典: 日立自動車交通株式会社 / Hitachi Motor Transportation Co. Ltd.
- URL: https://ckan.odpt.org/dataset/hitachi_automobile_transportation_chiyoda_alllines
- License: Creative Commons Attribution 4.0 International

## 更新時のルール

新しいソースを追加するときは、次を同じ変更に含めてください。

1. `config/sources.json`への登録
2. 出典URLとライセンスURL
3. 取得日またはソース版
4. 抽出・変換した旨の表示
5. 必要な著作権表示
