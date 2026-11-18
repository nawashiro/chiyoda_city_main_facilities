# Proposal

## Why

OSM の `wikimedia_commons` タグが `Category:` を指す施設は、現行では画像の対象外です。Wikidata P18 も `File:` タグも持たない施設は `schema:image` を持てません。対象の `Category:MAAch ecute Kanda-Manseibashi` は `pageimage` も Wikidata 項目も持たず、既存の「P18 → `File:`」だけでは画像 URL を得られません。

## What Changes

- Commons 取得で `Category:` タグを解決します。カテゴリの `pageimage` があればそれを使い、無ければ `categorymembers` からカテゴリ名に最も一致するファイルを選びます。
- カテゴリ名からファイル名への対応を `imports/commons/raw.json` の `categories` に記録します。公開時はこの記録だけを読み、ネットワークに依存しません。
- 公開画像の選択を P18 → OSM `File:` → OSM `Category:` の順に拡張します。1 record につき1画像は維持します。
- 月次ワークフローの `git add` に `imports/commons/` を加え、取得した対応表をコミットします。
- サブカテゴリの再帰、公開時の API 呼び出し、`Artist` を持たないファイルの画像化は対象外です。

## Capabilities

### New Capabilities

- なし

### Modified Capabilities

- `source-mirrors`: Commons のファイル名収集に `Category:` タグの解決を加え、カテゴリ名からファイル名への対応を `imports/commons/raw.json` に記録します。
- `public-jsonld-dataset`: `schema:image` の選択にカテゴリ代表画像を加え、`Category:` を対象外とする現行要件を置き換えます。

## Impact

- `src/commons_retrieval.py`: `Category:` の解決と `categories` の保存。
- `src/facility_data.py`: `_image_file_name` と `_apply_images` で `categories` を参照。
- `tests/test_commons_retrieval.py`、`tests/test_published_images.py`: カテゴリ解決と優先順位のテスト。
- `.github/workflows/update-osm.yml`: `git add` の対象追加。
- `imports/commons/raw.json`: `categories` フィールドが増えます。公開 JSON-LD の `schema:image` の形は変わりません。
