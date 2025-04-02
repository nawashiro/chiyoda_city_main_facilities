# 千代田区主要施設座標データ

風ぐるま乗り換え案内（非公式）で使用するデータです。千代田区の市民にとって主要な場所であり、かつ千代田区福祉交通「風ぐるま」の停留所から徒歩圏内である場所の座標をまとめた JSON データを提供しています。

## 概要

`json/address.json`ファイルには、以下のカテゴリに分類された千代田区内の主要施設の位置情報（緯度・経度）が含まれています：

- 主要な病院
- 区役所・出張所
- 会館
- 葬祭施設
- 区立の学校
- 高齢者福祉施設
- 障害者福祉施設
- 図書館
- リサイクル施設

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
    "category": "カテゴリ名",
    "locations": [
      {
        "name": "施設名",
        "description": "説明",
        "imageUri": "写真のURI",
        "imageCopylight": "写真の著作権表示",
        "uri": "URI",
        "lat": 緯度,
        "lng": 経度
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
- 緯度・経度の値は正確に入力してください
- [施設と停留所の距離チェックスクリプト](./施設と停留所の距離チェックスクリプト.md)を実行して千代田区福祉交通「風ぐるま」の停留所から徒歩圏内であることを確認してください。

## ライセンス

JSON データは[MIT ライセンス](LICENSE)の下で提供されています。

stops.txt は[公共交通オープンデータセンター](https://ckan.odpt.org/dataset/hitachi_automobile_transportation_chiyoda_alllines)から取得しました。このファイルのみ、ライセンスは [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)です。著作権は日立自動車交通株式会社 / Hitachi Motor Transportation Co. Ltd.に帰属します。
