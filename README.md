# 千代田区主要施設座標データ

東京都千代田区内の主要な施設の座標をまとめた json データです。

## 使いかた

ダウンロードするか、CDN を経由して利用してください。

```
// 主要・簡易
https://cdn.jsdelivr.net/gh/nawashiro/chiyoda_city_main_facilities@latest/json_min/main_facilities.json
// 多数・詳細
https://cdn.jsdelivr.net/gh/nawashiro/chiyoda_city_main_facilities@latest/json_min/key_locations.json

// 風ぐるまで到達可能な場所（主要・簡易）
https://cdn.jsdelivr.net/gh/nawashiro/chiyoda_city_main_facilities@latest/kazaguruma_json_min/main_facilities.json
// 風ぐるまで到達可能な場所（多数・詳細）
https://cdn.jsdelivr.net/gh/nawashiro/chiyoda_city_main_facilities@latest/kazaguruma_json_min/key_locations.json

// 本番環境ではlatestではなくバージョンを指定してください。互換性に問題が発生するかもしれません。
```

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

`/img`以下に保存します。600x450 の webp 画像です。

## 貢献方法

このデータは随時更新していく必要があります。以下の方法で貢献いただけます：

1. 新しい施設を追加する
2. 既存の施設情報を更新する
3. 誤った情報を修正する

- OSM からデータを受け入れる場合、[JSON 変換スクリプト](./doc/transform_json_doc.md)が使用できます。
- 保育所のデータを受け入れる場合、[CSV 変換スクリプト](./doc/nursery_data_conversion.md)が使用できます。
- [JSON 圧縮ツール](./doc/json_minifier_readme.md)があります。配信用のファイルを作成するために必要です。
- [リリースノート生成スクリプト](./doc/release_notes_generator.md)があります。データの統計情報をまとめたリリースノートを自動生成できます。
- Windows をお使いであれば、[施設データ処理バッチ](./doc/process.md)を使用すると風ぐるまデータ変換 → 配信ファイル作成が自動化できます。

## ライセンス

この JSON データは OpenStreetMap のデータを元に作成されています。OpenStreetMap のデータは [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/) の下で提供されています。従って、この JSON データも同じライセンスが適用されます。

[© OpenStreetMap contributors](https://www.openstreetmap.org/copyright)

## その他のデータ取得元

保育所のデータは東京都福祉局から取得しました。

[© 東京都福祉局](https://catalog.data.metro.tokyo.lg.jp/dataset/t000054d0000000356/resource/f41234cd-bcf2-46df-90fc-6cc7d8398321)

[クリエイティブ・コモンズ 表示（CC BY）](https://creativecommons.org/licenses/by/4.0/deed.ja)

幼稚園のデータは千代田区から取得しました。

[© 千代田区](https://catalog.data.metro.tokyo.lg.jp/dataset/t131016d0000000007)

[クリエイティブ・コモンズ 表示（CC BY）](https://creativecommons.org/licenses/by/4.0/deed.ja)

データの整合性を確認するための公共施設一覧は千代田区から取得しました。

[© 千代田区](https://catalog.data.metro.tokyo.lg.jp/dataset/t131016d0000000001)

[クリエイティブ・コモンズ 表示（CC BY）](https://creativecommons.org/licenses/by/4.0/deed.ja)

stops.txt は日立自動車交通から取得しました。

[© 日立自動車交通株式会社 / Hitachi Motor Transportation Co. Ltd.](https://ckan.odpt.org/dataset/hitachi_automobile_transportation_chiyoda_alllines)

[Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)
