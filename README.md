# 千代田区主要施設データベース

千代田区で生活、支援、余暇のために訪れる主要施設を、標準語彙のJSON-LDで公開します。
作業言語は日本語です。

## 正本と配布

`data/places.jsonld`はレジストリではありません。直接編集するcanonical JSON-LD正本です。
JSON-LD 1.1の各施設は`schema:Place`と`geo:Feature`を持ちます。
Point geometryはGeoSPARQLの`geo:hasGeometry`、`geo:asGeoJSON`、`geo:geoJSONLiteral`で表します。
外部識別子は`schema:identifier`内の`schema:PropertyValue`で保持します。
外部ソースのraw snapshotは`imports/`に保持し、公開JSON-LDへ運用履歴を追加しません。

- Dataset landing page: <https://nawashiro.github.io/chiyoda_city_main_facilities/>
- current JSON-LD: <https://nawashiro.github.io/chiyoda_city_main_facilities/places.jsonld>
- versioned snapshot: [GitHub Releases](https://github.com/nawashiro/chiyoda_city_main_facilities/releases)の`places-<tag>.jsonld`

GitHub Pagesはcurrent JSON-LDを配布します。
GitHub Releaseはタグごとの版固定snapshotを配布します。

## 変更とレビュー

canonical JSON-LDを直接編集してください。
外部レコードの人手レビューは、コミット済みYAMLをPRで確認してください。
Git commit、PR、Releaseを変更履歴とレビュー履歴に使います。

## 検証

Python 3.13で実行します。外部パッケージは使いません。

```bash
python3 -m src.fac_cli jsonld-validate data/places.jsonld
python3 -m src.facility_data validate .
python3 -m unittest discover -s tests -v
git diff --check
```

## 旧利用者への移行

この変更はbreaking changeです。

- 取得先をcurrent JSON-LDまたはGitHub Releaseへ切り替えてください。
- Place IDは`urn:uuid:`の値を使ってください。
- Point geometryはGeoSPARQLのgeometryから読み取ってください。
- 外部識別子は`schema:PropertyValue`から読み取ってください。
- GeoJSON、registry、manifest、町名導出は公開経路として提供しません。
- 公開JSON-LDに運用履歴、投票ログ、派生した町名を追加しないでください。

## 文書

このrepositoryはDiátaxisで文書を分けます。

| 種類 | 文書 |
|---|---|
| チュートリアル | [最初の施設変更](docs/tutorials/first-data-change.md) |
| ハウツー | [施設を保守する](docs/how-to/maintain-a-place.md) |
| ハウツー | [ソースを更新する](docs/how-to/update-source-data.md) |
| ハウツー | [更新チェックリスト](docs/how-to/source-update-checklist.md) |
| ハウツー | [Spec Kitを使って仕様を保守する](docs/how-to/use-specify.md) |
| リファレンス | [CLI](docs/reference/cli.md) |
| リファレンス | [属性](docs/reference/attributes.md) |
| リファレンス | [執筆規範](docs/reference/writing-style.md) |
| 説明 | [データモデル](docs/explanation/data-model.md) |
| 説明 | [文書構成](docs/explanation/documentation.md) |
| OpenSpec change | [adopt-standards-jsonld](openspec/changes/adopt-standards-jsonld/proposal.md) |

## 出典とライセンス

このリポジトリ固有資産（repository-specific assets）は[CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/)で提供します。
外部ソースのライセンスは個別に適用されます。統合データセット（combined Dataset）は、単一の一様なCC0ライセンスではありません。
外部データの出典と利用条件は[SOURCES_AND_LICENSES.md](SOURCES_AND_LICENSES.md)と`config/sources.json`に記録します。
