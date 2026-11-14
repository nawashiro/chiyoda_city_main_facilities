# 千代田区区民向け施設データ

千代田区区民向けの施設をJSON-LDで公開します。

略称は`0f05`です。文書やコミットで省略する場合に使います。

OpenStreetMapの取得、施設の照合、確定分の反映、GitHub Pagesへの公開を毎月1日にGitHub Actionsで実行します。自動判定できない施設だけ、確認Issueで人が判断します。

| 作業 | 手順 |
| --- | --- |
| 検索対象を追加・編集する | [CLI](docs/reference/cli.md)、[データ契約](docs/reference/data-contracts.md) |
| 実地調査で確定した接続先を反映する | [CLI](docs/reference/cli.md)の`assoc` |
| 更新を再実行する | [OpenStreetMapの更新](docs/how-to/update-osm.md) |
| 通知された候補を判断する | [Issueでの確認・修正](docs/how-to/review-osm-candidates.md) |
| 版を固定して配布する | [JSON-LDのリリース](docs/how-to/publish-release-jsonld.md) |

データ変更の検証は、`validate.yml`がPull Requestとmainへのpushで実行します。

GitHub Pagesは`site/places.jsonld`、GitHub Releasesは`places-<version>.jsonld`を配布します。形式と関連参照は[データ契約](docs/reference/data-contracts.md)、再利用条件は[出典とライセンス](docs/reference/sources-and-licenses.md)を参照してください。

## リポジトリの構成

| 場所 | 内容 |
| --- | --- |
| `data/` | 施設の正本`places.jsonld`、判断記録`osm-decisions.json`、更新元`sources.json` |
| `imports/` | OSMの取得元・バージョン・ハッシュの記録 |
| `inputs/` | 検索対象`facilities.json`（人が編集） |
| `site/` | GitHub Pagesの配布物 |
| `src/` `scripts/` | 検証・取得・照合・公開のPythonコードと`./fac` CLI |
| `tests/` | unittest一式 |
| `docs/` | この文書一式 |
| `.github/` | 取得・公開・リリース・検証のworkflow |
| `openspec/` | 仕様と変更の記録 |
