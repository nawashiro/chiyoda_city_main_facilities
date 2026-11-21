# Tasks

## 1. カテゴリ語彙ソースとUUID識別

- [x] 1.1 `data/category-vocabulary.jsonld`の`@graph`形式（1つの`DefinedTermSet`、`DefinedTerm`群、`schema:hasDefinedTerm`/`schema:inDefinedTermSet`、`schema:name`、`gif-poi`の`schema:identifier`）と、固定名前空間＋`gif-poi:<code>`からのUUIDv5導出を実装する。`tests/test_facility_categories.py`に形式・導出・重複拒否のテストを追加し、通ることを確認する。
- [x] 1.2 `load_vocabulary`と`validate_vocabulary`を新形式へ変え、コードとUUIDの一意性、UUID導出一致、HTTP term URLの不在、非公開ソースであることを検証する。`python3 -m unittest tests.test_facility_categories`が通ることを確認する。
- [x] 1.3 カテゴリ判断の検証と`review`を新しい語彙マッピング（コード→term）へ追従させ、判断記録がコードのままであることをテストする。`tests/test_facility_categories.py`と`tests/test_osm_maintenance.py`の関連テストが通ることを確認する。

## 2. 公開グラフの合成とrecord形状

- [x] 2.1 `data/dataset-shape.jsonld`にPlace用とDefinedTerm用の`sh:NodeShape`を作り、`schema:geo`必須、`schema:image`単一、`schema:contentUrl`/`schema:license`必須、`schema:creator`任意・単一、`schema:creator`がある場合の`schema:name`必須、`schema:keywords`の型を表現する。形状の構造テストを追加し、画像作者の任意性のケースが通ることを確認する。
- [x] 2.2 `build_repository`でカテゴリ語彙ノード、Placeの`schema:keywords`、形状を`site/dataset.jsonld`の`@graph`へ決定的な順序で合成し、`@context`に`sh`を足す。旧`site/places.jsonld`と`site/category-names.jsonld`への複製をやめる。`tests/test_dataset_publication.py`で`dataset.jsonld`の内容と正本不変を確認する。
- [x] 2.3 `validate_published_document`を`@type`でPlace/DefinedTerm/NodeShapeに分岐させ、公開Placeの`schema:keywords`がグラフ内termを指し、`gif-poi`識別子を持たないことを検証する。正本検証から`additionalType`禁止を外し、`tests/test_jsonld_repository.py`と`tests/test_published_images.py`を更新して通す。
- [x] 2.4 ビルドのPlace部分が正本と一致し、カテゴリterm・形状が追加されることを比較するテストを`tests/test_dataset_publication.py`に追加し、`python3 -m unittest tests.test_dataset_publication`が通ることを確認する。

## 3. CLI境界とデータ移行

- [x] 3.1 一度きりの移行サブコマンドを`./fac`へ追加し、`data/category-names.jsonld`を`data/category-vocabulary.jsonld`へ変換し、`data/places.jsonld`から`gif-poi`の`schema:identifier`を除去する。フィクスチャで変換・検証・旧ファイル削除をテストし、通ることを確認する。
- [x] 3.2 移行サブコマンドを実データに一度実行し、`data/category-vocabulary.jsonld`の全term、正本の`gif-poi`識別子ゼロ、`data/categories.json`不変を確認する。`./fac jsonld-validate data/places.jsonld`が通ることを確認する。
- [x] 3.3 `assoc`、`link`、`in rm`、保留、`category assign`/`clear`/`refresh`から`site/places.jsonld`への書き込みを外し、正本と判断記録だけを更新する。`tests/test_assoc.py`と`tests/test_facility_categories.py`で公開物が変更されないことを確認する。
- [x] 3.4 `jsonld-validate`の語彙探索を`data/category-vocabulary.jsonld`へ変え、`--published`が`site/dataset.jsonld`を検証できるようにする。CLIの検証テストが通ることを確認する。
- [x] 3.5 移行が完了したら一度きりの移行サブコマンドを削除し、`./fac --help`とテストに残っていないことを確認する。

## 4. 公開物・Release・landing page

- [x] 4.1 `site/index.html`のJSON-LD `DataDownload`を`dataset.jsonld`へ変え、カテゴリ`DataDownload`を削除し、GIF出典の`hasPart`を維持する。`tests/test_dataset_publication.py`のlanding pageテストが通ることを確認する。
- [x] 4.2 `scripts/prepare_release.py`の資産を`dataset.jsonld`/`osm.json`/`wikidata.json`へ変え、`category-names`を外す。`.github/workflows/release.yml`のリリースノートを3資産へ更新する。`tests/test_release_workflow.py`が通ることを確認する。
- [x] 4.3 `.github/workflows/update-osm.yml`と`validate.yml`の公開物パスを`site/dataset.jsonld`へ変え、ビルド後の検証と正本不変の確認を維持する。workflowの静的テストまたは該当テストが通ることを確認する。
- [x] 4.4 旧`site/places.jsonld`、`site/category-names.jsonld`、`site/categories.jsonld`を削除し、`python3 -m src.facility_data build .`の後に`site/dataset.jsonld`だけがJSON-LD公開物として存在することを確認する。

## 5. ドキュメントと利用側移行

- [x] 5.1 `docs/reference/data-contracts.md`を、公開`dataset.jsonld`のグラフ、`schema:keywords`、`DefinedTerm`、SHACL形状、Place識別子の削除に合わせて更新する。記載のJSON-LD例がビルド結果と一致することを確認する。
- [x] 5.2 `docs/reference/cli.md`を、カテゴリ操作が判断記録だけを更新し、公開反映がビルドであることに合わせて更新する。記載のコマンドを実行して確認する。
- [x] 5.3 `docs/reference/sources-and-licenses.md`と`README.md`を、語彙ソース名、`dataset-<版>.jsonld`、`category-names`廃止に合わせて更新する。記載の資産名がRelease設定と一致することを確認する。
- [x] 5.4 `docs/how-to/update-osm.md`と`docs/how-to/release-dataset.md`の公開物名を`dataset.jsonld`へ更新する。記載のコマンドが現行workflowと一致することを確認する。
- [x] 5.5 kazaguruma-transit向けに、`gif-poi`識別子から`schema:keywords`→`DefinedTerm`の`schema:identifier`へ移る手順を`docs/reference/data-contracts.md`へ追記する。公開`dataset.jsonld`の実データで参照を辿れることを確認する。

## 6. 統合検証

- [x] 6.1 `python3 -m unittest discover -s tests -v`が全件通ることを確認する。
- [x] 6.2 `python3 -m src.facility_data validate .`、`python3 -m src.facility_data build .`、`./fac jsonld-validate --published site/dataset.jsonld`が通ることを確認する。
- [x] 6.3 `site/dataset.jsonld`を点検し、Place数と語彙term数が正本・語彙ソースと一致し、1つの`DefinedTermSet`、Place形状とDefinedTerm形状、各Placeの`schema:keywords`解決、Placeの`gif-poi`識別子ゼロ、画像作者の任意性を確認する。
- [x] 6.4 `openspec validate self-contained-dataset-graph --strict`が通ることを確認する。

## Workflow follow-up

- 実装とレビューが完了したら、`/openspec-archive-change`で変更をアーカイブする。
- `dataset.jsonld`への破壊的変更をReleaseノートと利用側へ周知する。
