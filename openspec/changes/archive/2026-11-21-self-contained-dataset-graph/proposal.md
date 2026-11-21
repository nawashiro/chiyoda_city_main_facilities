# Proposal

## Why

公開JSON-LDは地物だけを収録し、カテゴリ名は別ファイルに置いている。両者を結ぶ明示的な参照がないため、機械は`gif-poi`の4桁コードからカテゴリ名へ辿れない。さらに、カテゴリtermの`@id`はGitHub PagesのHTTP URLで、地物の`urn:uuid:`と識別子の流儀が揃っていない。旧`site/categories.jsonld`が現行の名前辞書とは別に公開され、16施設ぶんのコードを欠いたまま残っていることも、別ファイル公開が放置される危険を示している。

地物recordの契約も文章にしかない。`schema:Place`はクラスだが、schema.orgのクラスは必須・任意を持たないため、画像の作者名が必須かどうかを機械は判断できない。

## What Changes

- 公開JSON-LDを、地物、カテゴリ語彙、record形状を一つの`@graph`に収めた`dataset.jsonld`へ改名する。**BREAKING**: 配布URLとRelease資産名を`places-<版>.jsonld`から`dataset-<版>.jsonld`へ変える。
- カテゴリを`schema:DefinedTermSet`と`schema:DefinedTerm`として同じグラフに置く。各termは`urn:uuid:`の`@id`、人間用の`schema:name`、根拠のGIF-POIコードを`schema:identifier`に持つ。
- 地物は`schema:keywords`でカテゴリtermを参照する。複数カテゴリを許す。地物自身の`gif-poi`識別子は削除する。
- 地物recordの必須・任意をSHACLの`sh:NodeShape`として同じグラフに公開する。`schema:image`の作者は任意、作者を出すときは名前必須、といった契約を機械可読にする。
- 語彙の正本`data/category-names.jsonld`を`data/category-vocabulary.jsonld`へ改名し、UUID付きの非公開ソースにする。**BREAKING**: カテゴリ語彙の単独公開、landing pageのカテゴリ`DataDownload`、Release資産`category-names-<版>.jsonld`を廃止する。
- `schema:additionalType`の禁止を削る。これは仕様変更を表現するために置かれたもので、設計上の不変条件ではない。
- 公開物は正本`data/places.jsonld`のビルド成果物とする。正本は地物だけのまま保ち、ビルドがカテゴリterm、`schema:keywords`、SHACL形状を注入する。
- 役目を終えた`site/categories.jsonld`を削除する。
- 判断記録`data/categories.json`はコードのまま維持し、`category assign`/`clear`は判断記録だけを更新する。公開recordへの反映はビルドが行う。

## Capabilities

### New Capabilities

なし。

### Modified Capabilities

- `public-jsonld-dataset`: 地物recordのカテゴリ表現を`gif-poi`識別子から`schema:keywords`の`DefinedTerm`参照へ変える。カテゴリ語彙とSHACL形状を同じグラフに加え、`additionalType`禁止を外す。
- `dataset-publication`: 公開JSON-LDの資産名を`dataset.jsonld`／`dataset-<版>.jsonld`へ変える。カテゴリ語彙の単独配布と`category-names`資産を廃止し、GIF出典の表現をカテゴリtermのグラフ内表現に合わせる。
- `facility-categories`: 語彙の正本をUUID付き`data/category-vocabulary.jsonld`へ変え、公開URL前提を外す。カテゴリ判断の公開反映をビルドへ移し、`category assign`/`clear`は判断記録だけを更新する。

## Impact

- `src/facility_data.py`: 正本検証、`@graph`のノード種別、ビルド時のカテゴリ語彙・形状注入、公開検証。
- `src/facility_categories.py`: 語彙ソースのUUID・term構造、判断記録の適用方法。
- `src/fac_cli.py`: `category assign`/`clear`/`review`がplace recordを書き換えないこと。
- `scripts/prepare_release.py`、`.github/workflows/release.yml`: Release資産名と検証対象。
- `site/index.html`: `DataDownload`のURL・名称、カテゴリ配布の削除、GIF出典の文言。
- `data/category-names.jsonld` → `data/category-vocabulary.jsonld`、`site/places.jsonld` → `site/dataset.jsonld`。`site/categories.jsonld`を削除。
- `tests/`: 公開物のバイト一致前提、カテゴリ識別子、`additionalType`禁止、Release資産名。
- `docs/`: データ契約、CLI、出典、公開手順。
- 外部のkazaguruma-transitは`schema:identifier`の`gif-poi`ではなく`schema:keywords`と`DefinedTerm`を読む移行が必要。
