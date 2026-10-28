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
