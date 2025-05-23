# 千代田区主要施設座標データ

東京都千代田区内の主要な施設の座標をまとめた json データです。

## ディレクトリ

- `json`: 千代田区の市民にとって主要な場所をまとめています。
- `kazaguruma_json`: 千代田区の市民にとって主要な場所であり、かつ千代田区福祉交通「風ぐるま」の停留所から徒歩圏内（600m 以内）である場所の座標をまとめた JSON データを提供しています。[施設と停留所の距離チェックスクリプト](./doc/facility_and_stop_distance_check_script.md)を実行して`json`から自動的に抽出できます。

## ファイル

- `main_facilities.json`ファイルには、千代田区内の市民にとって主要だと思われる福祉施設の位置情報（緯度・経度）が含まれています。
- `key_locations.json`ファイルには、千代田区内のさまざまな場所の位置情報が含まれています。項目は多くを含めることができます。

## データ形式

### main_facilities.json

主要な施設を簡易な形式でまとめています。

データは次の形式で構成されています：

```json
[
  {
    "category": "カテゴリ名",
    "locations": [
      {
        "name": "施設名",
        "name:en": "Facility name",
        "lat": 緯度,
        "lng": 経度,
        "copyright": "© このアイテムの作者",
        "licence": "MIT License",
        "licenceUri": "https://opensource.org/license/mit"
      },
      ...
    ]
  },
  ...
]
```

### key_locations.json

主要な場所を、詳細な形式でまとめています。

```json
[
  {
    "category": "カテゴリ名（必須）",
    "category:en": "英語カテゴリ名",
    "locations": [
      {
        "id": "uuid4（必須）",
        "name": "施設名（必須）",
        "name:en": "Facility name",
        "description": "説明（nullを許容する）",
        "descriptionCopyright": "© 説明の作者（説明がない場合のみnullを許容する）",
        "imageUri": "写真のURI（nullを許容する）",
        "imageCopyright": "© 写真の作者（写真のURIが存在しない時のみnullを許容する）",
        "uri": "URI（nullを許容する）",
        "lat": 緯度（必須）,
        "lng": 経度（必須）,
        "nodeCopyright": "© 座標の作者（必須）",
        "nodeSourceId": 提供元のid（ない場合nullを許容する）,
        "licence": "ライセンス（必須）",
        "licenceUri": "ライセンスURI（必須）",
      },
      ...
    ]
  },
  ...
]
```

## 画像

`/img`以下にカテゴリ名でフォルダ分けします。

600x450 の webp 画像です。

## 貢献方法

このデータは随時更新していく必要があります。以下の方法で貢献いただけます：

1. 新しい施設を追加する
2. 既存の施設情報を更新する
3. 誤った情報を修正する

- OSM からデータを受け入れる場合、[JSON 変換スクリプト](./doc/transform_json_doc.md)が使用できます。
- 保育所のデータを受け入れる場合、[CSV 変換スクリプト](./doc/nursery_data_conversion.md)が使用できます。
- [JSON 圧縮ツール](./doc/json_minifier_readme.md)があります。配信用のファイルを作成するために必要です。
- Windows をお使いであれば、[施設データ処理バッチ](./doc/process.md)を使用すると風ぐるまデータ変換 → 配信ファイル作成が自動化できます。

## ライセンス

この JSON データは OpenStreetMap のデータを元に作成されています。OpenStreetMap のデータは [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/) の下で提供されています。従って、この JSON データも同じライセンスが適用されます。

## その他のデータ取得元

[© OpenStreetMap contributors](https://www.openstreetmap.org/copyright)

保育所のデータは東京都福祉保健局のデータをもとに作成されています。

[© 東京都福祉保健局 CC BY](https://spec.api.metro.tokyo.lg.jp/spec/t000010d0000000106-187b68210aea92ed432db83b37265504-0)

stops.txt は[公共交通オープンデータセンター](https://ckan.odpt.org/dataset/hitachi_automobile_transportation_chiyoda_alllines)から取得しました。この GTFS データは [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)によって提供されています。

© 日立自動車交通株式会社 / Hitachi Motor Transportation Co. Ltd.
