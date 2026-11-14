# Spec Delta

## MODIFIED Requirements

### Requirement: Immutable release snapshot
システム SHALL GitHub Releaseごとに、そのタグのコミットでビルドした公開JSON-LD、OSMミラー配布物、Wikidataミラー配布物を、版号つきの資産として公開します。資産名 MUST `places-<版>.jsonld`、`osm-<版>.json`、`wikidata-<版>.json`です。landing pageを版固定資産に含めません（MUST NOT）。

#### Scenario: User cites a release
- **WHEN** 利用者が特定の公開版を取得します
- **THEN** 利用者はその版に対応する固定JSON-LDと、両ミラーの版固定資産を取得できます

#### Scenario: Release assets are inspected
- **WHEN** publishedなReleaseの資産一覧を点検します
- **THEN** JSON-LDと両ミラーの資産があり、landing pageは資産に含まれません

## ADDED Requirements

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
