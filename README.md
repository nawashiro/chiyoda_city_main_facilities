# 千代田区主要施設データ

千代田区で利用される主要施設を、再利用できる JSON-LD として公開します。

## 最初の 30 秒

初めてデータを変更する作業者は、Python 3.13 を確認し、[最初のデータ変更](docs/tutorials/first-data-change.md)を実行します。

```sh
python3 --version
git status --short
```

作業者は、他者の未コミット変更がある場合、変更範囲を分けます。

## 作業別の入口

- 施設データを初めて変更する: [最初のデータ変更](docs/tutorials/first-data-change.md)
- CLI の全コマンドを使う: [CLI](docs/reference/cli.md)
- WAM NET を更新する: [WAM を更新する](docs/how-to/update-wam.md)
- OpenStreetMap を更新する: [OpenStreetMap を更新する](docs/how-to/update-osm.md)
- OSM 候補を人手で確定する: [OSM 候補をレビューする](docs/how-to/review-osm-candidates.md)
- JSON-LD をリリースする: [JSON-LD をリリースする](docs/how-to/publish-release-jsonld.md)
- 変更を検証する: [検証](docs/reference/verification.md)

## 公開物

GitHub Pages は最新の `site/places.jsonld` を配布します。GitHub Releases はタグごとの `places-<version>.jsonld` を配布します。

利用者は JSON-LD と[データ契約](docs/reference/data-contracts.md)を確認します。作業者は[データフロー](docs/explanation/data-flow.md)で rollback 手順を確認します。

作業者は、データ構造と出典条件を変更前に確認します。

- [データ契約](docs/reference/data-contracts.md)
- [出典とライセンス](docs/reference/licenses.md)
- [データフロー](docs/explanation/data-flow.md)
