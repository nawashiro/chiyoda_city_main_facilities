# Spec Delta

## MODIFIED Requirements

### Requirement: Category name dictionary from the GIF POI code table
システム SHALL デジタル庁GIFのPOIコード表から採用したカテゴリの名前辞書を、語彙文書`data/category-names.jsonld`に定義します。辞書 MUST schema.orgの`DefinedTermSet`で構成し、`@id` MUST 公開URL `https://nawashiro.github.io/chiyoda_city_main_facilities/category-names.jsonld`です。各term MUST `schema:DefinedTerm`で、`@id`は辞書のURLにGIF POIコードの4桁fragmentを付けたterm URLを持ち、GIFの分類を指す日本語の表示名を持ちます。表示名はGIFの項目名と一致する必要はありません。表示名は人が決め、GIFの分類名を基礎にします。コードが指す分類の範囲を変えません。辞書 MUST GIFへの出典や体系名の参照を含みません。出典はDatasetのmetadataで表現します。

#### Scenario: Name dictionary is inspected

- **WHEN** 利用者が名前辞書を取得します
- **THEN** 各termは`#4桁コード`のterm URLと日本語の表示名を持ちます

#### Scenario: Display name differs from the item name

- **WHEN** 収録施設の実態に合わせてGIFの項目名と異なる表示名を付けます
- **THEN** コードは採用した版の分類を指したまま、表示名だけが変わります

#### Scenario: Dictionary stays a name list

- **WHEN** 名前辞書を点検します
- **THEN** 出典や体系名の参照は含まれません

#### Scenario: Adopted version is documented

- **WHEN** 利用者がDatasetのmetadataを取得します
- **THEN** 採用したGIFコード表のGitHubのタグ付き版を確認できます
