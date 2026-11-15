# Spec Delta

## MODIFIED Requirements

### Requirement: Immutable release snapshot
システム SHALL GitHub Releaseごとに、そのタグのコミットでビルドした公開JSON-LD、カテゴリ名辞書、OSMミラー配布物、Wikidataミラー配布物を、版号つきの資産として公開します。資産名 MUST `places-<版>.jsonld`、`category-names-<版>.jsonld`、`osm-<版>.json`、`wikidata-<版>.json`です。landing pageを版固定資産に含めません（MUST NOT）。

#### Scenario: User cites a release

- **WHEN** 利用者が特定の公開版を取得します
- **THEN** 利用者はその版に対応する固定JSON-LD、名前辞書、両ミラーの版固定資産を取得できます

#### Scenario: Release assets are inspected

- **WHEN** publishedなReleaseの資産一覧を点検します
- **THEN** JSON-LD、名前辞書、両ミラーの資産があり、landing pageは資産に含まれません

## ADDED Requirements

### Requirement: Category name dictionary distribution
システム SHALL カテゴリ名辞書をGitHub Pagesのsiteに配置します。辞書の`@id` MUST siteの取得URLと一致します。配布 MUST 正本`data/category-names.jsonld`のバイト列をそのまま複製します。判断のmethodと翻訳規則の根拠を辞書に含めません。

#### Scenario: Landing page exposes the name dictionary

- **WHEN** 利用者がlanding pageを開きます
- **THEN** 名前辞書の取得URLを`DataDownload`として確認できます

#### Scenario: Dictionary URL is byte-stable

- **WHEN** 利用者が辞書の`@id`を取得します
- **THEN** 応答は正本と同じバイト列の辞書です

### Requirement: Category source attribution
システム SHALL landing pageの`schema:Dataset`に、カテゴリ名辞書の源であるGIF POIコード表を、GitHubのタグ付き版とライセンス（CC0）付きの資源として表現します。判断のmethodと翻訳規則の根拠を表現しません。

#### Scenario: Dictionary source is displayed

- **WHEN** 利用者がlanding pageのDataset metadataを取得します
- **THEN** GIF POIコード表の版付き参照とCC0を確認できます
