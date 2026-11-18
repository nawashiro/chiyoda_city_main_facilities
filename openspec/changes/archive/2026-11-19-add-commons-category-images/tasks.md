# Tasks

## 1. Commons 取得のカテゴリ解決

- [x] 1.1 `src/commons_retrieval.py` に、OSM ミラーから `Category:` タグを集める処理を追加する。`Category:` を含む要素と含まない要素のテストで、集めたカテゴリ名を確認する。
- [x] 1.2 `pageimages` を50カテゴリずつ取得し、`pageimage` を `File:` のファイル名に直す処理を追加する。`normalized` と `redirects` を含む偽の応答で、元のカテゴリ名に対応が戻ることを確認する。
- [x] 1.3 `pageimages` が無いカテゴリについて `categorymembers` を1回取得し、カテゴリ名との語の一致数、タイトルの短さ、辞書順で1件を選ぶ処理を追加する。対象カテゴリに似た17ファイルのフィクスチャで、`File:MAAch ecute Kanda Manseibashi.jpg` が選ばれることを確認する。一致が無い場合は先頭ファイルが選ばれることも確認する。
- [x] 1.4 `run_commons_retrieval` で、カテゴリ由来のファイルを既存のファイル名集合に加え、`categories` マップを `imports/commons/raw.json` に保存する。テストで `files` に選んだファイルのメタデータが入り、`categories` がカテゴリ名からファイル名を指すことを確認する。
- [x] 1.5 代表画像もファイルメンバーも無いカテゴリでは、対応を記録せず取得を続ける。そのカテゴリだけが `categories` から欠けることをテストで確認する。

## 2. 公開時の画像選択

- [x] 2.1 `src/facility_data.py` の `_image_file_name` と `_apply_images` で、`imports/commons/raw.json` の `categories` を参照する。`Category:` のみの record に `schema:image` が付くことを `tests/test_published_images.py` で確認する。
- [x] 2.2 P18 と `Category:` が両方ある record では P18 を選ぶ。P18 のファイル URL が `schema:contentUrl` に入り、カテゴリのファイルが使われないことをテストで確認する。
- [x] 2.3 `categories` が無い、対応するファイルが無い、またはメタデータが不完全な場合は `schema:image` を付けない。3つの場合をテストで確認する。

## 3. 月次ワークフロー

- [x] 3.1 `.github/workflows/update-osm.yml` の `git add` に `imports/commons/` を追加する。workflow の該当行を確認し、`imports/openstreetmap/` などと同じコミット対象になっていることを確かめる。

## 4. 統合検証

- [x] 4.1 `python3 -m unittest discover -s tests -v` を実行し、既存テストと追加テストがすべて通ることを確認する。
- [x] 4.2 `python3 -m src.facility_data validate .`、`python3 -m src.facility_data build .`、`./fac jsonld-validate --published site/places.jsonld` を実行し、正本と公開物の検証が通ることを確認する。

## Workflow follow-up

- レビュー後に `openspec archive add-commons-category-images` で change を archive する。
- archive 後に `openspec validate --specs` を実行し、同期した spec を確認する。
