# facility-categories Specification

## Purpose

GIF POIコード表を語彙の正本とし、OSMタグと施設名称からの翻訳規則とJev、人手で決めた施設ごとのカテゴリを確定した判断として保存します。保存済み判断だけを公開にgif-poi識別子で渡し、名称やタグの変化で判断を再審査しません。

## Requirements

### Requirement: Category name dictionary from the GIF POI code table
システム SHALL デジタル庁GIFのPOIコード表から採用したカテゴリの名前辞書を、語彙文書`data/category-names.jsonld`に定義します。辞書 MUST schema.orgの`DefinedTermSet`で構成し、`@id` MUST 公開URL `https://nawashiro.github.io/chiyoda_city_main_facilities/category-names.jsonld`です。各term MUST `schema:DefinedTerm`で、`@id`は辞書のURLにGIF POIコードの4桁fragmentを付けたterm URLを持ち、GIFの項目名を日本語ラベルとして持ちます。辞書 MUST GIFへの出典や体系名の参照を含みません。出典はDatasetのmetadataで表現します。

#### Scenario: Name dictionary is inspected

- **WHEN** 利用者が名前辞書を取得します
- **THEN** 各termは`#4桁コード`のterm URLと日本語ラベルを持ちます

#### Scenario: Dictionary stays a name list

- **WHEN** 名前辞書を点検します
- **THEN** 出典や体系名の参照は含まれません

#### Scenario: Adopted version is documented

- **WHEN** 利用者がDatasetのmetadataを取得します
- **THEN** 採用したGIFコード表のGitHubのタグ付き版を確認できます

### Requirement: Adopted subset groups welfare under code 1499
システム SHALL 語彙を、GIF POIコード表から採用したサブセットとして維持し、収録する施設の分類に必要なコードだけを採用します。福祉の細分 MUST コード1499「その他の社会福祉施設」に集約します。システム MUST GIFにないコードを語彙に追加しません。

#### Scenario: Welfare facility is categorized

- **WHEN** 障害者福祉センターまたは高齢者福祉施設を分類します
- **THEN** 判断は1499に集約され、独自の福祉コードは作られません

#### Scenario: New category is needed

- **WHEN** 採用していないコードに該当する施設が収録されます
- **THEN** そのコードを語彙に採用してから判断できます

### Requirement: Translation rules decide rule assignments
システム SHALL `data/category-rules.json`に、関連付けOSM要素のタグと施設の名称からPOIコードを決める翻訳規則を持ちます。人が規則を編集します。rule判断はこの規則だけで決まります。規則が一つのカテゴリも決めないとき、または複数を決めるとき、システム MUST rule判断を確定しません。

#### Scenario: Single match decides

- **WHEN** 関連付けOSM要素のタグが規則の単一パターンに一致します
- **THEN** そのPOIコードがrule判断として確定します

#### Scenario: Ambiguous match does not decide

- **WHEN** 規則が複数のカテゴリに一致する
- **THEN** rule判断は確定せず、施設は未解決のまま残ります

### Requirement: Frozen category decisions
システム SHALL 施設ごとのカテゴリ判断を`data/categories.json`に、`method: rule`、`method: jev`、`method: human`のいずれかで確定した判断として保存します。公開生成 MUST 保存済み判断だけを使います。判断のない施設 MUST 分類なしのrecordとして公開し続けます。判断が語彙にないコードを持つとき、検証と公開 MUST 失敗します。

#### Scenario: Decided record keeps its category

- **WHEN** 判断の保存後に公開生成を実行します
- **THEN** recordは保存済みのカテゴリをgif-poi識別子として持ちます

#### Scenario: Undecided record stays uncategorized

- **WHEN** 判断のない施設を公開します
- **THEN** recordは分類なしのまま公開されます

#### Scenario: Unknown code blocks publication

- **WHEN** 判断に語彙にないPOIコードが入る
- **THEN** 検証と公開は失敗し、正本と公開物は変わらないまま残ります

### Requirement: Re-evaluation follows association changes
システム SHALL カテゴリ判断の見直しを、施設の関連付けOSM要素が変わったときと、人が指示したときだけ行います。名称・タグ・座標の変化 MUST 見直しの条件にしません。

#### Scenario: Retagging does not re-review

- **WHEN** 関連付けOSM要素が同じままタグと名称が変わります
- **THEN** 保存済み判断は再審査されず保持されます

#### Scenario: Re-association triggers re-evaluation

- **WHEN** 施設の関連付けが別のOSM要素へ変わります
- **THEN** その施設のカテゴリ判断を現在の根拠で再評価します

### Requirement: Category maintenance follows the OSM update
システム SHALL 月次更新および手動再実行の完了時に、語彙`data/category-names.jsonld`と規則`data/category-rules.json`が存在する場合、未決定および関連付けが変わった施設のカテゴリを再評価します。カテゴリ再評価の対象 MUST OSM関連付けのある施設に限ります。システム MUST 関連付け済みでカテゴリを確定できない施設をカテゴリ確認Issueに提示します。語彙または規則がない場合、システム MUST カテゴリ処理を省略し、OSM更新を継続します。

#### Scenario: Monthly update decides a category

- **WHEN** 月次更新で未分類施設のOSM関連付けが確定する
- **THEN** システムは規則またはJevでカテゴリ判断を記録し、公開recordにgif-poi識別子を適用します

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

### Requirement: Jev assignments adopt high-confidence results
システム SHALL ruleで確定しない施設のカテゴリをJevで判定し、閾値以上の結果を`method: jev`で採用します。閾値未満の結果、該当なし、候補なし MUST 確認Issueで人に示します。Jevが閾値以上で該当なしを選んだ場合、システム MUST 判断を記録せず施設を未分類のまま保ちます。Jevの認証・通信失敗と不正なAPI応答 MUST 判断として扱わず、その実行の判断記録を変更しません。

#### Scenario: High-confidence result is adopted

- **WHEN** Jevが閾値以上の信頼度でカテゴリを選びます
- **THEN** 人の確認を待たずに`method: jev`の判断を記録します

#### Scenario: Unresolved result goes to human review

- **WHEN** Jevの結果が閾値未満である、または該当なしである
- **THEN** 施設を確認Issueに示し、人の確定を待ちます

#### Scenario: Operational failure is not a decision

- **WHEN** Jevの呼び出しが通信エラーで終了する
- **THEN** システムは失敗を報告し、判断記録を変更しません

### Requirement: Human category decisions through the CLI
システム SHALL 専用CLIの`category`サブコマンドで人の判断を記録・取り消しできるようにします。`assign` MUST 語彙にあるPOIコードだけを受理し、`method: human`の判断を判断記録へ保存します。`clear` MUST 判断を取り消して施設を未分類へ戻します。`review` MUST ruleで確定した提案と、確定していない施設の一覧を示します。

#### Scenario: Assign records a human decision

- **WHEN** 保守者が`./fac category assign <uuid> 1499 --editor <editor>`を実行します
- **THEN** `method: human`の判断を判断記録へ保存します

#### Scenario: Assign rejects unknown codes

- **WHEN** 語彙にないPOIコードを`assign`に指定します
- **THEN** システムは判断記録を変更せず失敗を報告します

#### Scenario: Clear reverts to uncategorized

- **WHEN** 保守者が判断のある施設に`clear`を実行します
- **THEN** 判断は取り消され、施設は未分類へ戻ります
