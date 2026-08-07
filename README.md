# 千代田区主要施設データベース

千代田区で生活、支援、余暇のために訪れる主要施設を保守します。

公開物は代表点、画像、OSM (OpenStreetMap)属性、WAM属性を含むGeoJSONです。

作業言語は日本語です。

## はじめに

Python 3.13だけで実行できます。外部パッケージは使いません。

```bash
git clone git@github.com:nawashiro/chiyoda_city_main_facilities.git
cd chiyoda_city_main_facilities
git switch -c data/<作業内容>
python3 -m unittest discover -s tests -v
python3 -m src.facility_data validate .
python3 -m src.facility_data build .
git diff --check
```

生成物の`dist/public/`を直接編集してはいけません。

## 文書

このrepositoryはDiátaxisで文書を分けます。

| 種類 | 読み始める文書 | 目的 |
|---|---|---|
| チュートリアル | [最初の施設変更](docs/tutorials/first-data-change.md) | 初めての変更を完了する |
| ハウツー | [施設を保守する](docs/how-to/maintain-a-place.md) | Placeと検索入力を変更する |
| ハウツー | [ソースを更新する](docs/how-to/update-source-data.md) | WAM、OSM、町名を更新する |
| ハウツー | [更新チェックリスト](docs/how-to/source-update-checklist.md) | 更新前後を確認する |
| リファレンス | [CLI](docs/reference/cli.md) | `fac`の引数を確認する |
| リファレンス | [属性](docs/reference/attributes.md) | 正本と公開GeoJSONの属性を確認する |
| リファレンス | [保守仕様](docs/reference/data-maintenance-spec.md) | 実装済みのデータ契約を確認する |
| リファレンス | [執筆規範](docs/reference/writing-style.md) | 文書を執筆・レビューする |
| 説明 | [データモデル](docs/explanation/data-model.md) | 入力、正本、公開物の関係を理解する |
| 説明 | [文書構成](docs/explanation/documentation.md) | Diátaxisの使い分けを理解する |

## 公開データ

```text
https://cdn.jsdelivr.net/gh/nawashiro/chiyoda_city_main_facilities@<version>/dist/public/places.geojson
```

本番では`latest`を使わず、releaseまたはcommitを指定してください。
`dist/public/manifest.json`のSHA-256で取得物を確認してください。

## 構成

- `inputs/osm-search/`: OSM同定用の検索入力
- `data/registry.json`: 唯一のPlace正本
- `imports/`: WAMとOSMの保持済みsnapshot
- `data/pinned/`: 固定町名Polygon
- `dist/public/`: 公開用の派生物
- `docs/`: 利用者別の文書

## 出典とライセンス

このプロジェクトの独自著作物はCreative Commons Attribution-ShareAlike 4.0 Internationalで提供します。外部データの出典と利用条件は[SOURCES_AND_LICENSES.md](SOURCES_AND_LICENSES.md)と`config/sources.json`に記録します。
