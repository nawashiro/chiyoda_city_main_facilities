# リリースノート生成スクリプト

このドキュメントでは、プロジェクトのリリースノートを自動生成するスクリプト `generate_release_notes.py` の使用方法について説明します。

## 概要

`src/generate_release_notes.py` は、JSON データファイルから統計情報を抽出し、指定された形式でリリースノートを生成する Python スクリプトです。

## 機能

- `json/` および `kazaguruma_json/` ディレクトリ内の JSON ファイルから統計情報を抽出
- カテゴリごとの座標件数と写真件数の集計
- 画像ファイルへの参照数のカウント
- 全 JSON ファイルからのライセンス情報の収集（重複なし）
- マークダウン形式でのリリースノート生成

## 使用方法

### 基本的な実行

```bash
python src/generate_release_notes.py
```

### 実行結果

1. コンソールにリリースノートが表示されます
2. プロジェクトルートに `RELEASE_NOTES.md` ファイルが生成されます

## 出力形式

生成されるリリースノートは以下の形式に従います：

```markdown
このバージョンには以下の内容が含まれます。

## json

### main_facilities.json

| 分類       | 座標件数 |
| ---------- | -------- |
| 主要な病院 | 4        |

...

### key_locations.json

| 分類           | 座標件数 | 写真件数 |
| -------------- | -------- | -------- |
| 区役所・出張所 | 5        | 4        |

...

## kazaguruma_json

### main_facilities.json

| 分類       | 座標件数 |
| ---------- | -------- |
| 主要な病院 | 4        |

...

### key_locations.json

| 分類           | 座標件数 | 写真件数 |
| -------------- | -------- | -------- |
| 区役所・出張所 | 5        | 4        |

...

## 含まれるライセンス

| 作者                         | ライセンス                                                                     |
| ---------------------------- | ------------------------------------------------------------------------------ |
| © OpenStreetMap contributors | [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/) |

...
```

## 処理対象ファイル

スクリプトは以下のファイルを処理します：

- `json/main_facilities.json`
- `json/key_locations.json`
- `kazaguruma_json/main_facilities.json`
- `kazaguruma_json/key_locations.json`
- `img/` ディレクトリ内の画像ファイル（.webp, .jpg, .jpeg, .png）

## 技術的な詳細

### 統計情報の集計

- **座標件数**: 各カテゴリ内の `locations` 配列の要素数
- **写真件数**: `key_locations.json` 形式のファイルで `imageUri` フィールドが存在する要素数

### ライセンス情報の抽出

以下のフィールドからライセンス情報を抽出します：

- `copyright` または `nodeCopyright`
- `licence`
- `licenceUri`

### Windows 環境対応

Windows 環境での Unicode エラーを回避するため、出力エンコーディングを UTF-8 に設定しています。

## 依存関係

- Python 3.x
- 標準ライブラリのみ使用（外部依存関係なし）

## エラー処理

- 存在しないファイルやディレクトリは安全に無視されます
- 不正な JSON 形式の場合は Python の標準エラーが表示されます

## 使用例

データ更新後にリリースノートを生成する場合：

```bash
# データ処理を実行
run_process.bat

# リリースノートを生成
python src/generate_release_notes.py
```

これにより、最新のデータに基づいたリリースノートが自動生成されます。
