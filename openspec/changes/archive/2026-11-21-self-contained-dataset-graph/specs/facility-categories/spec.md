# Spec Delta

## ADDED Requirements

### Requirement: Category vocabulary source is a non-public DefinedTermSet
システム SHALL デジタル庁GIFのPOIコード表から採用したカテゴリの語彙を、非公開ソース`data/category-vocabulary.jsonld`に定義します。語彙 MUST `schema:DefinedTermSet`と、採用したカテゴリごとの`schema:DefinedTerm`で構成します。各term MUST `urn:uuid:`の`@id`と、GIFの分類を指す日本語の`schema:name`を持ちます。term MUST HTTP URIのterm URLを持ちません（MUST NOT）。語彙ソース MUST 公開distributionとして配布されません（MUST NOT）。

#### Scenario: Category vocabulary source is inspected

- **WHEN** 利用者が`data/category-vocabulary.jsonld`を点検します
- **THEN** 各termはUUIDと日本語の表示名を持ちます

#### Scenario: Display name differs from the item name

- **WHEN** 収録施設の実態に合わせてGIFの項目名と異なる表示名を付けます
- **THEN** コードは採用した版の分類を指したまま、表示名だけが変わります

### Requirement: Category terms carry GIF-POI identifiers
各カテゴリterm MUST GIF POIコードを表す`schema:identifier`の`schema:PropertyValue`（`propertyID`が`gif-poi`、`value`が4桁コード）を持ちます。表示名は人が決め、GIFの分類名を基礎にします。コードが指す分類の範囲を変えません。

#### Scenario: Category term identifier is inspected

- **WHEN** 利用者がカテゴリtermの`schema:identifier`を点検します
- **THEN** `propertyID`が`gif-poi`の4桁コードを取得できます

### Requirement: Category vocabulary source carries no provenance or rules
語彙 MUST GIFへの出典URLやライセンス表示、判断のmethod、翻訳規則の根拠を含みません。出典はDatasetのmetadataで表現します。

#### Scenario: Vocabulary stays a category list

- **WHEN** 語彙ソースを点検します
- **THEN** GIFへの出典URL、ライセンス表示、判断のmethod、翻訳規則の根拠を含みません

#### Scenario: Adopted version is documented

- **WHEN** 利用者がDatasetのmetadataを取得します
- **THEN** 採用したGIFコード表のGitHubのタグ付き版を確認できます

## MODIFIED Requirements

### Requirement: Frozen category decisions
システム SHALL 施設ごとのカテゴリ判断を`data/categories.json`に、`method: rule`、`method: jev`、`method: human`のいずれかで確定した判断として保存します。公開生成 MUST 保存済み判断だけを使い、判断のコードをカテゴリtermへの`schema:keywords`として公開recordに適用します。判断のない施設 MUST 分類なしのrecordとして公開し続けます。Place record MUST `gif-poi`の`schema:identifier`を持ちません（MUST NOT）。判断が語彙にないコードを持つとき、検証と公開 MUST 失敗します。

#### Scenario: Decided record keeps its category

- **WHEN** 判断の保存後に公開生成を実行します
- **THEN** recordはカテゴリtermへの`schema:keywords`を持ちます

#### Scenario: Undecided record stays uncategorized

- **WHEN** 判断のない施設を公開します
- **THEN** recordは分類なしのまま公開されます

#### Scenario: Unknown code blocks publication

- **WHEN** 判断に語彙にないPOIコードが入る
- **THEN** 検証と公開は失敗し、正本と公開物は変わらないまま残ります

### Requirement: Category maintenance follows the OSM update
システム SHALL 月次更新および手動再実行の完了時に、語彙`data/category-vocabulary.jsonld`と規則`data/category-rules.json`が存在する場合、未決定および関連付けが変わった施設のカテゴリを再評価します。カテゴリ再評価の対象 MUST OSM関連付けのある施設に限ります。システム MUST 関連付け済みでカテゴリを確定できない施設をカテゴリ確認Issueに提示します。語彙または規則がない場合、システム MUST カテゴリ処理を省略し、OSM更新を継続します。

#### Scenario: Monthly update decides a category

- **WHEN** 月次更新で未分類施設のOSM関連付けが確定する
- **THEN** システムは規則またはJevでカテゴリ判断を記録し、公開recordにカテゴリtermへの`schema:keywords`を適用します

#### Scenario: Unassociated facility is not auto-classified

- **WHEN** 施設にOSM関連付けがない
- **THEN** システムは規則とJevでカテゴリを決めず、未分類のまま保ちます

#### Scenario: Unresolved category is presented

- **WHEN** カテゴリを確定できない施設が残る
- **THEN** システムはその施設をカテゴリ確認Issueに示し、未分類のまま保ちます

#### Scenario: Vocabulary or rules are absent

- **WHEN** 語彙または規則が存在しない
- **THEN** システムはカテゴリ処理を省略し、OSM更新を成功させます

#### Scenario: Category maintenance fails

- **WHEN** カテゴリ判断が認証・通信エラーで失敗する
- **THEN** システムは更新全体を失敗として報告し、未検証の判断を公開しません

### Requirement: Human category decisions through the CLI
システム SHALL 専用CLIの`category`サブコマンドで人の判断を記録・取り消しできるようにします。`assign` MUST 語彙にあるPOIコードだけを受理し、`method: human`の判断を判断記録へ保存します。`clear` MUST 判断を取り消して施設を未分類へ戻します。`assign`と`clear` MUST place recordを変更せず、判断記録だけを更新します。公開recordへの反映はビルドが行います。`review` MUST ruleで確定した提案と、確定していない施設の一覧を示します。

#### Scenario: Assign records a human decision

- **WHEN** 保守者が`./fac category assign <uuid> 1499 --editor <editor>`を実行します
- **THEN** `method: human`の判断を判断記録へ保存します
- **AND** place recordは変更されません

#### Scenario: Assign rejects unknown codes

- **WHEN** 語彙にないPOIコードを`assign`に指定します
- **THEN** システムは判断記録を変更せず失敗を報告します

#### Scenario: Clear reverts to uncategorized

- **WHEN** 保守者が判断のある施設に`clear`を実行します
- **THEN** 判断は取り消され、施設は未分類へ戻ります
- **AND** place recordは変更されません

### Requirement: Association hold suspends category decisions
システム SHALL 関連付けを保留した施設のカテゴリ判断を取り消し、保留中は規則・Jevによるカテゴリ判断とカテゴリ確認Issueへの提示を行いません。システム MUST 保留の解除後に、確定した関連付けを根拠にカテゴリを再評価できるようにします。公開recordへの反映はビルドが行います。

#### Scenario: Hold withdraws the category decision

- **WHEN** 保守者が施設のOSM関連付けを保留として記録します
- **THEN** その施設のカテゴリ判断は取り消され、次のビルドで公開recordから`schema:keywords`が外れます

#### Scenario: Held facility is not presented

- **WHEN** カテゴリのない保留中の施設が残ります
- **THEN** システムはその施設をカテゴリ確認Issueに示しません

#### Scenario: Category is re-evaluated after the hold is lifted

- **WHEN** 保留を解除して関連付けを確定します
- **THEN** その施設は未決定施設としてカテゴリ再評価の対象に戻ります

## REMOVED Requirements

### Requirement: Category name dictionary from the GIF POI code table
**Reason**: 語彙はUUIDとGIF-POI識別子を持つ非公開のカテゴリ語彙へ移り、HTTP term URLの名前辞書ではなくなる。公開物のカテゴリは`dataset.jsonld`の`DefinedTerm`が担う。
**Migration**: `data/category-vocabulary.jsonld`の`DefinedTermSet`と`DefinedTerm`へ移行する。利用者は公開`dataset.jsonld`のカテゴリtermを読み、単独の名前辞書URLは使わない。
