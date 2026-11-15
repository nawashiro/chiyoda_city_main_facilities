# 出典とライセンス

このデータセット全体に単一のライセンスは適用しません。リポジトリ固有アセットと外部データは、別の条件に従います。

## リポジトリ固有アセット

| 項目 | 内容 |
| --- | --- |
| ライセンス | Creative Commons CC0 1.0 Universal |
| ライセンス URL | <https://creativecommons.org/publicdomain/zero/1.0/> |
| 法的コード | <https://creativecommons.org/publicdomain/zero/1.0/legalcode> |

## OpenStreetMap

| 項目 | 内容 |
| --- | --- |
| 出典 | <https://www.openstreetmap.org/copyright> |
| ライセンス | Open Database License (ODbL) 1.0 |
| ライセンス URL | <https://opendatacommons.org/licenses/odbl/1-0/> |
| 帰属 | `© OpenStreetMap contributors` |
| 加工内容 | 千代田区内の対象候補を抽出し、同定済み施設の Point 座標へ変換する。 |

## Wikidata

| 項目 | 内容 |
| --- | --- |
| 出典 | <https://www.wikidata.org/wiki/Wikidata:Licensing> |
| ライセンス | Creative Commons CC0 1.0 Universal |
| ライセンス URL | <https://creativecommons.org/publicdomain/zero/1.0/> |
| 帰属 | なし |
| 加工内容 | なし |

## GIF POIコード表

カテゴリ名辞書 `data/category-names.jsonld` の項目名は、デジタル庁の政府相互運用性フレームワーク（GIF）POIコード表から採用しています。版は GitHub リポジトリ `digital-go-jp/GIF` のタグ `v2.4` に固定します。

| 項目 | 内容 |
| --- | --- |
| 出典 | <https://github.com/digital-go-jp/GIF/blob/v2.4/490_%E3%81%9D%E3%81%AE%E4%BB%96/491-3-1_POI%E3%82%B3%E3%83%BC%E3%83%89%E8%A1%A8.xlsx> |
| ライセンス | Creative Commons CC0 1.0 Universal |
| ライセンス URL | <https://creativecommons.org/publicdomain/zero/1.0/> |
| 帰属 | なし |
| 加工内容 | 採用したコードの項目名をそのまま用い、コードとの対応を `category-names.jsonld` に編集する。 |

## WAM NET由来の残存情報

このリポジトリで残るWAM由来の施設情報には、配布ページの利用条件が適用されます。

| 項目 | 内容 |
| --- | --- |
| 出典・利用条件 | <https://www.wam.go.jp/content/wamnet/pcpub/top/sfkopendata/> |
| ライセンス URL | <https://www.wam.go.jp/content/wamnet/pcpub/top/sfkopendata/> |
| 帰属 | `WAM NET` |
| 利用条件 | WAM NET 配布ページ記載のオープンデータ利用条件に従う。 |
| 加工内容 | 相談支援4サービスから東京都千代田区の施設を抽出し、同一施設を集約する。 |

WAMの定期取得や更新処理は設けません。

出典表示、利用条件、加工内容を維持します。`data/sources.json`は現在の更新元を列挙し、この文書は残存情報の出典も含めます。
