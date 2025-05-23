# 保育所データ変換スクリプト

このドキュメントでは、保育所の CSV データを JSON 形式に変換し、`key_locations.json`に追加するスクリプトの使用方法を説明します。

## 概要

`convert_nursery_data.py`スクリプトは、保育所の CSV データを読み込み、指定の形式に変換して`json/key_locations.json`ファイルに追加します。追加は増分更新となり、既存のデータは保持されます。CSV データは事前に千代田区内の施設だけにフィルタされている必要があります。

## 前提条件

- Python 3.6 以上
- 仮想環境（venv）が既に設定されていること

## 入力データ

入力データは以下の形式の CSV ファイルである必要があります：

`.temp/csv/保育所.csv`

CSV ファイルには以下のヘッダーが含まれている必要があります：

- `設置`
- `施設名`
- `郵便番号`
- `所在地`
- `経度`
- `緯度`
- `座標系`
- `電話番号`
- `認可定員`

## 出力データ

出力データは`json/key_locations.json`に保存されます。このファイルには、以下の形式で保育所データが追加されます：

```json
{
  "category": "保育所",
  "category:en": "nursery",
  "locations": [
    {
      "id": "uuid4（ランダム生成）",
      "name": "施設名",
      "name:en": "施設名",
      "description": "電話番号、認可定員情報",
      "descriptionCopyright": "© 東京都福祉保健局",
      "imageUri": null,
      "imageCopyright": null,
      "uri": null,
      "lat": 緯度,
      "lng": 経度,
      "nodeCopyright": "© 東京都福祉保健局",
      "nodeSourceId": null,
      "licence": "CC BY",
      "licenceUri": "https://creativecommons.org/licenses/by/4.0/"
    },
    ...
  ]
}
```

## 使用方法

1. 仮想環境を有効化します：

```bash
# Windowsの場合
venv\Scripts\activate

# macOS/Linuxの場合
source venv/bin/activate
```

2. スクリプトを実行します：

```bash
python src/convert_nursery_data.py
```

## 注意事項

- すでに「保育所」カテゴリが存在する場合は、既存のカテゴリに新しい施設が追加されます。
- 「保育所」カテゴリが存在しない場合は、新しいカテゴリが作成されます。
- 各施設には一意の UUID（v4）が割り当てられます。
- `nodeSourceId`は null に設定されます。
- 以下の項目は決め打ちで設定されます：
  - descriptionCopyright: `© 東京都福祉保健局`
  - nodeCopyright: `© 東京都福祉保健局`
  - licence: `CC BY`
  - licenceUri: `https://creativecommons.org/licenses/by/4.0/`
