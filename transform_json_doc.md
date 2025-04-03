# JSON 変換スクリプト ドキュメント

## 概要

`transform_json.py`は、OpenStreetMap から抽出した施設データ（./.temp/filtered 内の JSON ファイル）を、千代田区主要施設座標データ用の形式（./json/key_locations.json）に変換するスクリプトです。

## 機能

- 入力ディレクトリ内のすべての JSON ファイルを処理
- ファイル名をカテゴリとして使用
- 各施設の基本情報（名前、位置情報など）と多言語名を抽出
- Web サイト情報がある場合は URI として保存
- 変換したデータを key_locations.json に保存

## 技術的詳細

### 入力データ形式

入力 JSON は、OpenStreetMap の API 出力形式で、以下のような構造です:

```json
{
  "version": 0.6,
  "generator": "Overpass API",
  "elements": [
    {
      "type": "node",
      "id": 260409658,
      "lat": 35.6728254,
      "lon": 139.7592046,
      "tags": {
        "name": "施設名",
        "name:en": "English name",
        "website": "https://example.com"
        // その他のタグ
      }
    }
    // 他の施設
  ]
}
```

### 出力データ形式

出力 JSON は、以下の構造に変換されます:

```json
[
  {
    "category": "カテゴリ名",
    "locations": [
      {
        "name": "施設名",
        "name:en": "English name",
        "description": null,
        "imageUri": null,
        "imageCopylight": null,
        "uri": "https://example.com",
        "lat": 35.6728254,
        "lng": 139.7592046
      }
      // 他の施設
    ]
  }
  // 他のカテゴリ
]
```

## 使用方法

1. Python 仮想環境（venv）がセットアップされていることを確認
2. 以下のコマンドでスクリプトを実行:

```
python transform_json.py
```

## 処理フロー

1. 仮想環境をアクティベート
2. 入力ディレクトリから全 JSON ファイルを取得
3. 各ファイルについて:
   - ファイル名からカテゴリを抽出
   - JSON データを読み込み
   - 各ノード要素を処理して必要な情報を抽出
   - 名前を持つ施設のみをロケーションとして追加
4. 結果を JSON ファイルに書き込み

## 依存関係

- Python 3.x
- 標準ライブラリのみ使用（json, os, glob）
- 事前に設定された仮想環境（venv）
