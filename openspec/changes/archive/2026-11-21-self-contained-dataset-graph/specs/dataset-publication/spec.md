# Spec Delta

## ADDED Requirements

### Requirement: Self-contained dataset distribution
システム SHALL 公開JSON-LD distributionとして`dataset.jsonld`を配布します。distribution MUST 地物、カテゴリ語彙、record形状を同じ文書に含みます。システム MUST カテゴリ語彙だけのdistributionを公開しません。

#### Scenario: JSON-LD distribution is inspected
- **WHEN** 利用者が`dataset.jsonld`を取得します
- **THEN** 文書は地物、カテゴリ語彙、record形状を同じ`@graph`に含みます

#### Scenario: Category-only distribution is inspected
- **WHEN** 利用者がlanding pageのdistribution一覧を点検します
- **THEN** カテゴリ語彙だけのJSON-LD distributionはありません

## MODIFIED Requirements

### Requirement: Actionable JSON-LD distribution
landing page MUST JSON-LD配布物を`DataDownload`として表現します。
distribution MUST `contentUrl`と`encodingFormat`を含みます。`contentUrl` MUST `https://nawashiro.github.io/chiyoda_city_main_facilities/dataset.jsonld`です。

#### Scenario: User selects the current distribution
- **WHEN** 利用者がlanding pageを開きます
- **THEN** 利用者は最新JSON-LDとして`dataset.jsonld`の取得URLと形式を確認できます

### Requirement: Immutable release snapshot
システム SHALL GitHub Releaseごとに、そのタグのコミットでビルドした公開JSON-LD、OSMミラー配布物、Wikidataミラー配布物を、版号つきの資産として公開します。資産名 MUST `dataset-<版>.jsonld`、`osm-<版>.json`、`wikidata-<版>.json`です。landing pageを版固定資産に含めません（MUST NOT）。

#### Scenario: User cites a release

- **WHEN** 利用者が特定の公開版を取得します
- **THEN** 利用者はその版に対応する固定JSON-LDと両ミラーの版固定資産を取得できます

#### Scenario: Release assets are inspected

- **WHEN** publishedなReleaseの資産一覧を点検します
- **THEN** JSON-LDと両ミラーの資産があり、landing pageは資産に含まれません

### Requirement: Category source attribution
システム SHALL landing pageの`schema:Dataset`に、データセットのカテゴリtermの根拠であるGIF POIコード表を、GitHubのタグ付き版とライセンス（CC0）付きの資源として表現します。判断のmethodと翻訳規則の根拠を表現しません。

#### Scenario: Dictionary source is displayed

- **WHEN** 利用者がlanding pageのDataset metadataを取得します
- **THEN** GIF POIコード表の版付き参照とCC0を確認できます

### Requirement: Single-dispatch release publication
システム SHALL workflow_dispatchの1回の起動で、テストとビルドの実行、タグの作成、Releaseの公開、版固定資産の添付を完了します。システム MUST mainの最新コミットから公開し、テストまたはビルドが失敗したときReleaseを作成しません。公開に失敗したとき MUST 失敗を報告し、成功したと報告しません。

#### Scenario: A maintainer starts the release workflow
- **WHEN** maintainerがrelease workflowを起動します
- **THEN** テストとビルドが通り、タグとpublishedなReleaseが作られ、dataset、OSM、Wikidataの3つの版固定資産が添付されます

#### Scenario: Validation fails before publication
- **WHEN** 起動したworkflowでテストまたはビルドが失敗します
- **THEN** Releaseもタグも作成されず、workflowが失敗を報告します

## REMOVED Requirements

### Requirement: Category name dictionary distribution
**Reason**: カテゴリ語彙は`dataset.jsonld`の`@graph`に含める。別ファイルの辞書は同じ情報を二重に公開し、実際に旧`site/categories.jsonld`が現行辞書から16施設ぶん欠落したまま残った。
**Migration**: 利用者は`dataset.jsonld`の`schema:DefinedTermSet`と`schema:DefinedTerm`からカテゴリ名とGIF-POIコードを取得する。カテゴリ語彙だけの公開URLは提供しない。
