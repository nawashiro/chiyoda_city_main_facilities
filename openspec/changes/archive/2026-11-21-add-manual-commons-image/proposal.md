# Proposal

## Why

公開画像の選択はWikidata P18、OSMの`wikimedia_commons`タグ、Commonsカテゴリの代表画像だけで決まっており、このデータセットの用途に合うファイルを人間が選ぶ方法がありません。OSM、Wikidata、Commonsはこの施設グラフにIRIを提供する情報源であり、その選択方針がデータセットの方針と一致するとは限らないため、正本の関連付けとして画像ファイルを指定できるようにします。

## What Changes

- 正本`data/places.jsonld`のPlace recordに、`schema:image`としてCommonsファイルページのIRI参照を一つ置けるようにします。正本に書くのは参照だけで、直接URL、ライセンス、作者は書きません。
- 専用CLI`./fac image set`、`./fac image clear`、`./fac image review`を追加します。`set`は`File:`タイトルとCommonsファイルページURLを受け付け、`clear`は手動参照を外して自動選択に戻し、`review`は手動参照の解決状況を表示します。
- 公開ビルドは手動参照をP18、OSMの`File:`タグ、OSMの`Category:`タグより優先します。手動参照のファイルメタデータが得られないときは自動候補へフォールバックせず、画像なしの公開recordを生成して警告を出します。
- Commonsメタデータの取得対象に、正本の手動参照が指すファイルを加えます。
- 正本の検証はCommonsファイルページ参照の形だけを許可し、公開物の検証は従来どおり`schema:ImageObject`を要求します。
- データ契約、CLI、画像の選択規則の文書と、`public-jsonld-dataset`、`source-mirrors`の仕様を更新します。

## Capabilities

### New Capabilities

なし

### Modified Capabilities

- `public-jsonld-dataset`: 正本のPlace recordがCommonsファイルページへの参照を一つ持てること、公開時の画像選択が手動参照を最優先すること、手動参照のメタデータが得られないときにフォールバックしないことを追加します。
- `source-mirrors`: Commonsメタデータの取得対象に、正本の手動参照が指すファイルを加えます。

## Impact

- 新規`src/commons_files.py`: `File:`タイトルとCommonsファイルページURLの正規化・検証。
- `src/facility_data.py`: 正本の参照形検証、公開ビルドでの手動優先・参照の除去・警告。
- `src/commons_retrieval.py`: 正本の手動参照をファイル名収集に追加。
- `src/fac_cli.py`: `./fac image`サブコマンド。
- `tests/`: 参照形の検証、手動優先、欠落時の非フォールバック、取得対象、CLIの回帰テスト。
- `docs/`、`openspec/specs/`: データ契約、CLI、画像選択、取得対象の更新。
- 依存追加なし。公開JSON-LDの`schema:image`の形は変わらない。
