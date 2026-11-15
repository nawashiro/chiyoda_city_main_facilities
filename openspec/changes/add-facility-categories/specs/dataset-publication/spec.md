# Spec Delta

## MODIFIED Requirements

### Requirement: Immutable release snapshot
システム SHALL GitHub Releaseごとに、そのタグのコミットでビルドした公開JSON-LD、カテゴリ語彙文書、OSMミラー配布物、Wikidataミラー配布物を、版号つきの資産として公開します。資産名 MUST `places-<版>.jsonld`、`categories-<版>.jsonld`、`osm-<版>.json`、`wikidata-<版>.json`です。landing pageを版固定資産に含めません（MUST NOT）。

#### Scenario: User cites a release

- **WHEN** 利用者が特定の公開版を取得します
- **THEN** 利用者はその版に対応する固定JSON-LD、語彙文書、両ミラーの版固定資産を取得できます

#### Scenario: Release assets are inspected

- **WHEN** publishedなReleaseの資産一覧を点検します
- **THEN** JSON-LD、語彙文書、両ミラーの資産があり、landing pageは資産に含まれません

## ADDED Requirements

### Requirement: Category vocabulary distribution
システム SHALL カテゴリ語彙文書をGitHub Pagesのsiteに配置します。語彙文書のURL MUST 公開Place recordの`schema:additionalType`が指すURLと一致します。配布 MUST 正本`data/categories.jsonld`のバイト列をそのまま複製します。判断のmethodと翻訳規則の根拠を語彙文書に含めません。

#### Scenario: Landing page exposes the vocabulary document

- **WHEN** 利用者がlanding pageを開きます
- **THEN** 語彙文書の取得URLを`DataDownload`として確認できます

#### Scenario: Term URLs resolve to the published document

- **WHEN** 利用者が公開recordのadditionalTypeのURLを取得します
- **THEN** 応答は正本と同じバイト列の語彙文書です
