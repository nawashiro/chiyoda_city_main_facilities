# Tasks

## 1. Commonsファイル参照の共通処理

- [x] 1.1 `src/commons_files.py` に`File:`タイトルとCommonsファイルページURLの正規化・検証を実装し、`tests/test_commons_files.py`で`File:`タイトル、ページURL、クエリ付きURL、`Category:`、直接アップロードURL、空文字の受理・拒否が通ることを確認する
- [x] 1.2 正規化したページURLから元の`File:`タイトルへ戻る往復と、空白・アンダースコア・パーセントエンコードの扱いを`tests/test_commons_files.py`で確認する

## 2. 正本の参照形と公開ビルド

- [x] 2.1 `src/facility_data.py`の正本検証を、`schema:image`が`{"@id": "https://commons.wikimedia.org/wiki/File:..."}`の形だけを許可するよう変更し、`ImageObject`、非Commons、余計なフィールドを拒否するテストを`tests/test_published_images.py`に追加して通す
- [x] 2.2 `src/facility_data.py`の`_apply_images`を、正本の参照を公開用documentから必ず取り除き、手動参照をP18・OSMタグより優先し、メタデータ欠落時はフォールバックせず警告する実装に変更し、`tests/test_published_images.py`で手動優先・非フォールバック・警告・既存の自動選択が通ることを確認する
- [x] 2.3 `src/facility_data.py`の`apply_decisions`経由でOSM関連付けを置換しても正本の`schema:image`参照が残ることを`tests/test_published_images.py`または`tests/test_source_mirrors.py`で確認する
- [x] 2.4 `docs/reference/data-contracts.md`の正本・公開物の画像記述を、Commonsファイルページ参照と公開時の解決に合わせて更新し、記載した正本例と公開例が`./fac jsonld-validate`と`./fac jsonld-validate --published`で通ることを確認する

## 3. 手動参照のCommons取得

- [x] 3.1 `src/commons_retrieval.py`の`collect_file_names`が正本`data/places.jsonld`の`schema:image`を含めるよう変更し、P18とOSMタグに現れない手動参照が取得対象になるテストを`tests/test_commons_retrieval.py`に追加して通す
- [x] 3.2 `run_commons_retrieval`が手動参照の直接URL・ライセンス・作者を`imports/commons/raw.json`へ保存し、既存のカテゴリ対応・作者の非表示要素・プレースホルダ処理を壊さないことを`tests/test_commons_retrieval.py`で確認する

## 4. CLIと利用者向け文書

- [x] 4.1 `src/fac_cli.py`に`./fac image set`、`./fac image clear`、`./fac image review`を実装し、タイトルとURLの正規化、未知Placeの拒否、既存参照の置換、clear後の参照削除、reviewの解決済み・未解決表示をCLIテストで確認する
- [x] 4.2 `./fac image set`と`clear`が正本だけを書き、`site/dataset.jsonld`を変更しないことをCLIテストで確認する
- [x] 4.3 `docs/reference/cli.md`と`README.md`に画像指定のコマンドと、指定直後は月次取得まで公開物に反映されないことを記載し、`./fac image --help`と`./fac image review`の記載どおりの実行結果を確認する

## 5. 統合検証

- [x] 5.1 一時ディレクトリで手動参照を設定してビルドし、公開recordが手動参照の`schema:ImageObject`を持ち、P18・OSMの別ファイルへフォールバックしないことを確認する
- [x] 5.2 一時ディレクトリで手動参照のメタデータを欠落させてビルドし、画像なしの公開recordと警告が出ることを確認する
- [x] 5.3 `python3 -m unittest discover -s tests -v`、`./fac jsonld-validate data/places.jsonld`、`./fac jsonld-validate --published site/dataset.jsonld`、`python3 -m src.facility_data build .`が通ることを確認する
- [x] 5.4 `openspec validate add-manual-commons-image --strict`が警告なしで通ることを確認する

## Workflow follow-up

- 実装とレビューが完了したら、この変更をアーカイブする。
