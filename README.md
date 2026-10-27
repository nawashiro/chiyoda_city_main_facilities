# 千代田区主要施設データ

千代田区で利用される主要施設をJSON-LDで公開します。

OpenStreetMapの取得、施設の照合、確定分の反映、GitHub Pagesへの公開を毎月1日にGitHub Actionsで実行します。自動判定できない施設だけ、確認Issueで人が判断します。

| 作業 | 手順 |
| --- | --- |
| 検索対象を追加・編集する | [CLI](docs/reference/cli.md)、[データ契約](docs/reference/data-contracts.md) |
| 更新を再実行する | [OpenStreetMapの更新](docs/how-to/update-osm.md) |
| 通知された候補を判断する | [Issueでの確認・修正](docs/how-to/review-osm-candidates.md) |
| データを初めて編集する | [最初のデータ変更](docs/tutorials/first-data-change.md) |
| 変更を検証する | [検証](docs/reference/verification.md) |
| 版を固定して配布する | [JSON-LDのリリース](docs/how-to/publish-release-jsonld.md) |

GitHub Pagesは`site/places.jsonld`、GitHub Releasesは`places-<version>.jsonld`を配布します。形式と関連参照は[データ契約](docs/reference/data-contracts.md)、更新の流れは[データフロー](docs/explanation/data-flow.md)、再利用条件は[出典とライセンス](docs/reference/licenses.md)を参照してください。
