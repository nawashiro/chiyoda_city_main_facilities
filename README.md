# 千代田区主要施設座標データ

東京都千代田区内の主要な施設の座標をまとめた json データです。

## ディレクトリ

- `json`: 千代田区の市民にとって主要な場所をまとめています。
- `kazaguruma_json`: 千代田区の市民にとって主要な場所であり、かつ千代田区福祉交通「風ぐるま」の停留所から徒歩圏内（600m 以内）である場所の座標をまとめた JSON データを提供しています。[施設と停留所の距離チェックスクリプト](./facility_and_stop_distance_check_script.md)を実行して`json`から自動的に抽出できます。

## ファイル

- `main_facilities.json`ファイルには、千代田区内の市民にとって主要だと思われる施設の位置情報（緯度・経度）が含まれています。項目はなるべく厳選する必要があります。
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
        "lng": 経度
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
    "locations": [
      {
        "name": "施設名（必須）",
        "name:en": "Facility name",
        "description": "説明（nullを許容する）",
        "imageUri": "写真のURI（nullを許容する）",
        "imageCopylight": "写真の著作権表示（写真のURIが存在しない時のみnullを許容する）",
        "uri": "URI（nullを許容する）",
        "lat": 緯度（必須）,
        "lng": 経度（必須）
      },
      ...
    ]
  },
  ...
]
```

## 貢献方法

このデータは随時更新していく必要があります。以下の方法で貢献いただけます：

1. 新しい施設を追加する
2. 既存の施設情報を更新する
3. 誤った情報を修正する

プルリクエストを歓迎しています。変更を提案する際は、以下の点にご注意ください：

- JSON の構造を維持してください
- 施設名は正確に記載してください
- 緯度・経度の値はかならず入力してください

## ライセンス

この JSON データは OpenStreetMap のデータを元に作成されています。OpenStreetMap のデータは [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/) の下で提供されています。従って、この JSON データも同じライセンスが適用されます。

[© OpenStreetMap contributors](https://www.openstreetmap.org/copyright)

stops.txt は[公共交通オープンデータセンター](https://ckan.odpt.org/dataset/hitachi_automobile_transportation_chiyoda_alllines)から取得しました。この GTFS データは [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)によって提供されています。

© 日立自動車交通株式会社 / Hitachi Motor Transportation Co. Ltd.
