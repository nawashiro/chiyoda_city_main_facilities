# Spec Delta

## MODIFIED Requirements

### Requirement: Commons license metadata extraction
システム SHALL 月次パイプラインで、収集したCommonsのファイル名それぞれについて、Commons APIから直接URL、ライセンス、作者を取得し、`imports/commons/raw.json`に保持します。ファイル名の収集 SHALL Wikidata P18、OSMの`File:`タグ、OSMの`Category:`タグが指すCommonsカテゴリ、および正本`data/places.jsonld`の`schema:image`が指すCommonsファイルに由来します。P18、OSMタグ、カテゴリ由来のファイル名 MUST 紐付け集合の要素に限定します。正本の手動参照 MUST 紐付けの有無にかかわらず対象に含めます。カテゴリは代表画像を優先し、無いときはカテゴリ内のファイルからカテゴリ名に最も一致するものを選びます。作者欄のHTMLに含まれる非表示要素（`display:none`、`hidden`）の文字列 MUST 作者名に含めません。作者名がCommonsのプレースホルダ（`Unknown author`など）のとき、システム MUST 作者なしとして扱い、`artist`を`null`にします。システム MUST カテゴリ名からファイル名への対応を`imports/commons/raw.json`に記録します。抽出物 MUST Pages配信の対象にしません。システム MUST 取得メタ（取得日時・エンドポイント・応答SHA256）を既存のretrievalメタと同種の記録として残します。

#### Scenario: Monthly pipeline refreshes the metadata

- **WHEN** 月次`update-osm`パイプラインが走る
- **THEN** 紐付け済み要素に由来するファイルと正本の手動参照のメタデータが`imports/commons/raw.json`に保存される

#### Scenario: Unassociated files are excluded

- **WHEN** 手動参照ではないファイル名が、紐付けの存在しない要素から集められる
- **THEN** そのファイルは`imports/commons/raw.json`の対象にならない

#### Scenario: Manual reference is retrieved

- **WHEN** 正本の`schema:image`がCommonsファイルを指し、そのファイルを指すWikidata P18とOSMタグがない
- **THEN** そのファイル名が取得対象になり、メタデータが`imports/commons/raw.json`に保存される

#### Scenario: Manual reference stays outside the published mirrors

- **WHEN** 正本の手動参照から取得したメタデータが保存される
- **THEN** そのメタデータは`imports/commons/`に留まり、`site/mirrors/`の配布物に現れない

#### Scenario: Extraction stays outside the published mirrors

- **WHEN** `site/mirrors/`の配布物が点検される
- **THEN** Commonsのメタデータ抽出物は配布物の外の`imports/commons/`に留まる

#### Scenario: Category page image is resolved

- **WHEN** OSM要素の`wikimedia_commons`が`Category:`を指し、そのカテゴリに代表画像がある
- **THEN** 代表画像のファイル名が取得対象になり、カテゴリ名からファイル名への対応が`imports/commons/raw.json`に記録される

#### Scenario: Category without a page image falls back to its files

- **WHEN** カテゴリに代表画像がなく、ファイルメンバーがある
- **THEN** カテゴリ名に最も一致するファイル名が取得対象になり、対応が`imports/commons/raw.json`に記録される

#### Scenario: Category without files stays unresolved

- **WHEN** カテゴリに代表画像もファイルメンバーもない
- **THEN** そのカテゴリの対応は記録されず、公開時に画像は付かない

#### Scenario: Hidden author text is ignored

- **WHEN** 作者欄が可視テキストと非表示要素（`display:none`）の文字列をあわせて持つ
- **THEN** 保存される`artist`は可視テキストだけになる

#### Scenario: Unknown author placeholder yields no author

- **WHEN** 作者欄が`{{unknown|author}}`由来のプレースホルダのみである
- **THEN** `imports/commons/raw.json`の`artist`は`null`になる
