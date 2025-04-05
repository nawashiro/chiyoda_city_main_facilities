# JSON 変換スクリプト ドキュメント

## 概要

`transform_json.py`は、OpenStreetMap から抽出した施設データ（./.temp/filtered 内の JSON ファイル）を、千代田区主要施設座標データ用の形式（./json/key_locations.json）に変換するスクリプトです。このスクリプトは増分更新をサポートしており、既存のデータを保持しつつ新しい施設のみを追加します。

人力でのカテゴリ分けが必要です。新しい入力ファイルは新しいカテゴリとして受け入れる仕様になっていますが、これは自動でのカテゴリ分けが難しいためです。

## 機能

- 入力ディレクトリ内のすべての JSON ファイルを処理
- ファイル名をカテゴリとして使用
- 各施設の基本情報（名前、位置情報など）と多言語名を抽出
- Web サイト情報がある場合は URI として保存
- 変換したデータを key_locations.json に保存
- node と way の両方のデータタイプをサポート
- 既存データとの重複を`nodeSourceId`で照合して増分更新

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
    },
    {
      "type": "way",
      "id": 99999997,
      "center": {
        "lat": 35.697,
        "lon": 139.757
      },
      "nodes": [10000001, 10000002, 10000003, 10000004, 10000001],
      "tags": {
        "name": "テスト広場",
        "name:en": "Test Square",
        "leisure": "park"
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
    "category:en": "英語カテゴリ名",
    "locations": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000", // UUID
        "name": "施設名",
        "name:en": "English name",
        "description": null,
        "descriptionCopyright": null,
        "imageUri": null,
        "imageCopyright": null,
        "uri": "https://example.com",
        "lat": 35.6728254,
        "lng": 139.7592046,
        "nodeCopyright": "© OpenStreetMap contributors",
        "nodeSourceId": 260409658,
        "licence": "Open Database License (ODbL) 1.0",
        "licenceUri": "https://opendatacommons.org/licenses/odbl/"
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
2. 既存の出力 JSON ファイルがある場合は読み込み、`nodeSourceId`を抽出して重複チェック用に保存
3. 入力ディレクトリから全 JSON ファイルを取得
4. 各ファイルについて:
   - ファイル名からカテゴリを抽出
   - JSON データを読み込み
   - 各要素（node または way）を処理:
     - 名前を持つ施設のみを処理
     - 既存データに存在しない場合のみ追加
     - 座標情報を取得（node と way で取得方法が異なる）
     - 必要な情報を抽出し、新規施設として追加
5. 新しい施設が追加された場合のみ、結果を JSON ファイルに書き込み

## 依存関係

- Python 3.x
- 標準ライブラリのみ使用（json, os, glob, uuid）
- 事前に設定された仮想環境（venv）
