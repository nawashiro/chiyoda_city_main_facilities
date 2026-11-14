# dataset-publication Specification

## Purpose

静的なDataset landing pageと版固定配布物を提供し、公開JSON-LDを発見、取得、引用できるようにします。

## Requirements

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
システム SHALL GitHub Releaseごとに、そのタグのコミットでビルドした公開JSON-LD、OSMミラー配布物、Wikidataミラー配布物を、版号つきの資産として公開します。資産名 MUST `places-<版>.jsonld`、`osm-<版>.json`、`wikidata-<版>.json`です。landing pageを版固定資産に含めません（MUST NOT）。

#### Scenario: User cites a release
- **WHEN** 利用者が特定の公開版を取得します
- **THEN** 利用者はその版に対応する固定JSON-LDと、両ミラーの版固定資産を取得できます

#### Scenario: Release assets are inspected
- **WHEN** publishedなReleaseの資産一覧を点検します
- **THEN** JSON-LDと両ミラーの資産があり、landing pageは資産に含まれません

### Requirement: Single-dispatch release publication
システム SHALL workflow_dispatchの1回の起動で、テストとビルドの実行、タグの作成、Releaseの公開、版固定資産の添付を完了します。システム MUST mainの最新コミットから公開し、テストまたはビルドが失敗したときReleaseを作成しません。公開に失敗したとき MUST 失敗を報告し、成功したと報告しません。

#### Scenario: A maintainer starts the release workflow
- **WHEN** maintainerがrelease workflowを起動します
- **THEN** テストとビルドが通り、タグとpublishedなReleaseが作られ、3つの版固定資産が添付されます

#### Scenario: Validation fails before publication
- **WHEN** 起動したworkflowでテストまたはビルドが失敗します
- **THEN** Releaseもタグも作成されず、workflowが失敗を報告します

### Requirement: Date-based immutable release tags
システム SHALL 公開Releaseのタグを実行日のUTC日付 `YYYY.MM.DD` とします。同じタグが既に存在するとき MUST 公開を失敗させ、タグを移動せず、Releaseを上書きしません。既存のpublishedなRelease MUST 削除・編集・再公開しません。

#### Scenario: The same day already has a release
- **WHEN** そのUTC日のタグが既に存在します
- **THEN** workflowは失敗して終わり、既存タグとReleaseは変更されません

### Requirement: Generated release notes
システム SHALL Release公開時にworkflowがリリースノートを生成します。リリースノート MUST 資産一覧を含み、OSMミラー資産にODbLとOpenStreetMap contributorsの出典を、Wikidataミラー資産にCC0を、資産単位で対応づけて明示します。

#### Scenario: Release notes are inspected
- **WHEN** publishedなReleaseの本文を読みます
- **THEN** 本文は添付資産の一覧と各資産のライセンス表示を含みます

### Requirement: JSON-LD-only public distribution
システム MUST GeoJSONを公開distribution、release snapshot、manifestから除外します。

#### Scenario: Current public distribution is generated
- **WHEN** システムがcurrent distributionを生成します
- **THEN** 出力はJSON-LDだけを公開形式として含みます

### Requirement: Separate source and project licensing

システム SHALL リポジトリ固有の資産をCC0として明示する。システム MUST OSMのODbLとWikidataのCC0を個別に明示し、複数sourceを含む公開Dataset全体をCC0と表示しない。WAMの配布ページと利用条件は参考資料の文書に残す。保持するWAM由来情報に必要な出典・帰属表示は継続し、WAMを稼働中の更新元として表示しない。

#### Scenario: Dataset metadata is published

- **WHEN** 利用者がDataset landing pageまたはrelease metadataを取得する
- **THEN** 利用者はproject asset licenseと各sourceの利用条件を区別できる

#### Scenario: WAM reference is inspected

- **WHEN** 利用者がWAMの参考資料を読む
- **THEN** 利用者は配布元と利用条件を参照でき、現在の更新がWAMに依存しないことを確認できる

### Requirement: Automatic publication of validated maintenance results

システム SHALL 月次更新とIssueで確定した判断について、データ検証と必要なテストに通った変更を`data/places.jsonld`へ反映し、GitHub Pagesへ自動公開する。人によるworkflow起動や更新PRのマージを通常の公開条件としない。公開は反映済みコミットに対応し、失敗時は成功したと報告しない。

#### Scenario: Monthly update commits a change

- **WHEN** 月次更新の確定分が検証に通り、正本に変更がある
- **THEN** システムはその変更を自動反映し、そのコミットのJSON-LDをPagesへ公開する

#### Scenario: Human choice is applied

- **WHEN** Issueの有効な確定内容が検証を通って正本へ反映される
- **THEN** システムは人による追加のマージ操作を待たずに公開する

#### Scenario: Publishing the commit fails

- **WHEN** 正本への反映後にPagesのデプロイが失敗する
- **THEN** システムは公開失敗を報告し、反映済みコミットから公開を再実行できる

### Requirement: Source mirror distributions on the landing page
landing page MUST OSM ミラー配布物と Wikidata ミラー配布物を、それぞれ個別の `DataDownload` として表現します。
各 `DataDownload` MUST `contentUrl` と `encodingFormat` を含みます。
landing page MUST OSM 配布物に ODbL を、Wikidata 配布物に CC0 を、配布物単位で対応づけて明示します。

#### Scenario: A visitor selects a mirror distribution
- **WHEN** 利用者が landing page を開く
- **THEN** OSM ミラーと Wikidata ミラーの取得 URL と、それぞれのライセンスを確認できる

#### Scenario: Licenses stay separated
- **WHEN** landing page の Dataset metadata を検査する
- **THEN** ミラー各配布物が、dataset 全体を CC0 と表示する記述を持たず、個別のライセンスを参照する
