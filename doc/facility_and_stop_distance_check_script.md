# 施設と停留所の距離チェックスクリプト

## 概要

このスクリプトは、`json/main_facilities.json`および`json/key_locations.json`に記載されている施設と`stops.txt`に記載されている停留所の位置情報を比較し、
各施設から最も近い停留所までの距離を計算します。設定した距離（デフォルトでは 600m）以内の施設のみをフィルタリングして、元の構造と属性を維持したまま新しい JSON ファイルとして出力します。

## 必要環境

- Python 3.6 以降
- 必要なライブラリ: pandas, geopy

## インストール方法

1. 仮想環境を作成し、アクティベートします:

```
python -m venv venv
.\venv\Scripts\activate  # Windowsの場合
source venv/bin/activate  # Mac/Linuxの場合
```

2. 必要なパッケージをインストールします:

```
pip install -r requirements.txt
```

## 使用方法

```
python src/facilities_check.py
```

実行結果が画面に表示され、以下の JSON ファイルが生成されます:

- `kazaguruma_json/main_facilities.json`
- `kazaguruma_json/key_locations.json`

## 入力ファイル形式

### json/main_facilities.json および json/key_locations.json

施設情報を含む JSON ファイル。以下の形式を持っています:

```json
[
  {
    "category": "カテゴリー名",
    "category:en": "カテゴリー名（英語）", // この属性は任意
    "locations": [
      {
        "name": "施設名",
        "name:en": "施設名（英語）", // この属性は任意
        "description": "説明", // この属性は任意
        "imageUri": "画像URL", // この属性は任意
        "lat": 緯度(float),
        "lng": 経度(float),
        // その他の属性は全て保持されます
      },
      ...
    ]
  },
  ...
]
```

### stops.txt

停留所情報を含む CSV ファイル。以下のカラムを持っています:

- stop_id: 停留所 ID
- stop_name: 停留所名
- stop_desc: 説明
- stop_lat: 緯度
- stop_lon: 経度
- zone_id: ゾーン ID
- location_type: ロケーションタイプ

## 出力

- フィルタリング結果の概要がコンソールに表示されます
- 停留所から半径 600m 以内の施設のみが抽出され、元のファイルと同じ構造の JSON ファイルとして出力されます:
  - `main_facilities.json` → `kazaguruma_json/main_facilities.json`
  - `key_locations.json` → `kazaguruma_json/key_locations.json`
- 出力される JSON ファイルには、元の施設データの構造と全ての属性を維持したまま、600m 圏内の施設のみが含まれます
- 施設の各属性（description, imageUri, name:en など）はすべて保持されます
