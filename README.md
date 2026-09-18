# 千代田区主要施設データベース

千代田区で生活、支援、余暇のために訪れる主要施設を、標準語彙のJSON-LDで公開します。作業言語は日本語です。

## 最初の変更

編集するcanonical JSON-LD正本は`data/places.jsonld`だけです。`site/places.jsonld`はGitHub Pages用の配布コピーなので編集しないでください。

初参加者は[最初の施設変更](docs/tutorials/first-data-change.md)を読み、編集 → 検証 → 差分確認 → Pull Requestの順に進めます。

1. `data/places.jsonld`を編集する。
2. 次のコマンドを順番に実行する。

```bash
python3 -m src.fac_cli jsonld-validate data/places.jsonld
python3 -m src.facility_data validate .
python3 -m unittest discover -s tests -v
git diff --check
```

3. `git diff --name-only`と`git diff -- data/places.jsonld`で差分を確認し、変更対象が`data/places.jsonld`だけであることを確認する。
4. 検証と差分確認が成功したらcommitを作成し、Pull Requestを作成する。

- `jsonld-validate`: 成功（終了コード`0`）はJSON-LDの構造と識別子が有効、失敗（終了コード`1`）は読み込みまたは検証のエラーを意味します。
- `facility_data validate`: 成功はリポジトリ内のデータが整合、失敗は出力された不整合の修正が必要なことを意味します。
- `unittest`: 成功は回帰テストの完了、失敗は原因の修正が必要なことを意味します。
- `git diff --check`: 成功は空白エラーなし、失敗は差分の空白エラーを意味します。

## 公開先

- Dataset landing page: <https://nawashiro.github.io/chiyoda_city_main_facilities/>
- current JSON-LD: <https://nawashiro.github.io/chiyoda_city_main_facilities/places.jsonld>
- versioned snapshot: [GitHub Releases](https://github.com/nawashiro/chiyoda_city_main_facilities/releases)の`places-<tag>.jsonld`

GitHub Pagesはcurrent JSON-LDを配布します。GitHub Releaseはタグごとの版固定snapshotを配布します。

## データモデル

JSON-LD 1.1、`schema:Place`、`geo:Feature`、`urn:uuid:`、`schema:PropertyValue`、GeoSPARQLの仕様は[データモデル](docs/explanation/data-model.md)、[属性](docs/reference/attributes.md)、[CLI](docs/reference/cli.md)を参照してください。

## 文書

このrepositoryは[Diátaxis](docs/explanation/documentation.md)で文書を分けます。

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

このリポジトリ固有資産（repository-specific assets）は[CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/)で提供します。外部ソースのライセンスは個別に適用されます。統合データセット（combined Dataset）は、単一の一様なCC0ライセンスではありません。外部データの出典と利用条件は[SOURCES_AND_LICENSES.md](SOURCES_AND_LICENSES.md)と`config/sources.json`に記録します。

## 詳細と移行

外部ソースのraw snapshotは`imports/`に保持し、公開JSON-LDに運用履歴を追加しません。JSON-LD-onlyへの移行はbreaking changeです。旧利用者はcurrent JSON-LDまたはGitHub Releaseへ切り替えます。旧形式のGeoJSON、registry、manifest、町名導出は公開経路として提供しません。
