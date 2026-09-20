# Spec Delta

## Purpose

静的なDataset landing pageと版固定配布物を提供し、公開JSON-LDを発見、取得、引用できるようにします。

## ADDED Requirements

### Requirement: Dataset landing page
システム SHALL GitHub PagesにDataset landing pageを公開します。
page MUST `schema:Dataset`、dataset name、description、landing page URLを含みます。

#### Scenario: Dataset crawler reads the landing page
- **WHEN** crawlerがlanding pageを取得します
- **THEN** crawlerはDataset metadataをJSON-LDで取得できます

### Requirement: Actionable JSON-LD distribution
landing page MUST JSON-LD配布物を`DataDownload`として表現します。
distribution MUST `contentUrl`と`encodingFormat`を含みます。

#### Scenario: User selects the current distribution
- **WHEN** 利用者がlanding pageを開きます
- **THEN** 利用者は最新JSON-LDの取得URLと形式を確認できます

### Requirement: Immutable release snapshot
システム SHALL GitHub Releaseごとに版固定JSON-LD snapshotを公開します。

#### Scenario: User cites a release
- **WHEN** 利用者が特定の公開版を取得します
- **THEN** 利用者はその版に対応する固定JSON-LDを取得できます

### Requirement: JSON-LD-only public distribution
システム MUST GeoJSONを公開distribution、release snapshot、manifestから除外します。

#### Scenario: Current public distribution is generated
- **WHEN** システムがcurrent distributionを生成します
- **THEN** 出力はJSON-LDだけを公開形式として含みます

### Requirement: Separate source and project licensing
システム SHALL リポジトリ固有の資産をCC0として明示します。
システム MUST OSMのODbL、WikidataのCC0、WAM配布ページの利用条件URLを個別に明示します。
システム MUST 複数sourceを含む公開Dataset全体をCC0と表示しません。

#### Scenario: Dataset metadata is published
- **WHEN** 利用者がDataset landing pageまたはrelease metadataを取得します
- **THEN** 利用者はproject asset licenseと各sourceの利用条件を区別できます
