# Proposal

## Why

公開JSON-LDには画像の取得先とライセンスが載っていない。WikidataのP18とOSMの`wikimedia_commons`タグがCommonsのファイル名を持っているのに、配布物の利用者はミラー全体を読んで初めてそれを知り、ライセンスに至ってはどこにもない。施設画像の再利用には帰属とライセンスの確認が付き物なので、公開配布物だけで完結した形にする。issue #71。

## What Changes

- 正本`data/places.jsonld`は変更しない。関連付けだけを載せる現行の方針を保つ。
- 月次パイプラインにCommonsの取得ステップを追加する。ミラーから集めたファイル名（Wikidata P18、OSMの`File:`タグ）について、Commons APIから直接URL・ライセンス・作者を取得し、`imports/commons/raw.json`に保存する。このファイルはPages配信しない。
- 公開時（`build_repository`）に、公開配布物の各Place recordへ`schema:image`を合成する。中身は`schema:ImageObject`で、`schema:contentUrl`（直接URL）・`schema:license`（`LicenseUrl`のCC URL。無いときはライセンス名の文字列）・`schema:creator`（作者名）を載せる。
- 画像の選び方は決定的にする。P18を優先し、無ければOSMの`File:`タグ。`Category:`タグは画像ではないので対象外。施設あたり1枚。
- Commons取得の失敗は公開を止めない。画像が欠けたまま公開する（Wikidataミラーと同じ扱い）。

## Capabilities

### New Capabilities

なし

### Modified Capabilities

- `public-jsonld-dataset`: 公開Place recordの除外規定から画像を外し、公開時にミラーから導出した`schema:image`を含める要件を追加する。正本recordが`schema:image`を持たないことも要件に書く。
- `source-mirrors`: Commonsのメタデータ取得を月次パイプラインの付加的ステップとして追加する。抽出物は`imports/commons/raw.json`に保持し、Pages配信の対象外とする。

## Impact

- 新規`src/commons_retrieval.py`（Commons APIの取得モジュール）
- `src/osm_maintenance.py`: 取得ステップの組み込み
- `src/facility_data.py`: 公開物の合成と、正本・公開物それぞれの検証
- `.github/workflows/update-osm.yml`: 公開物の検証に`--published`を付す（1行）
- `scripts/prepare_release_jsonld.py`: リリースsnapshotの検証を公開物の検証に差し替える
- 依存追加なし（Commons APIは標準HTTP GET）
- 実測（2026-11-14時点）: 対象51ファイル、ライセンスはCC BY-SA 30件、CC BY 12件、パブリックドメイン6件、CC0 2件、独自テンプレートのAttribution 1件
