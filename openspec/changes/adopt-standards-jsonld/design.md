# Design

## Context

現行の`data/registry.json`は、施設属性、参照履歴、監査、更新状態を一つの独自構造へ入れます。
`dist/public/places.geojson`はその派生物です。
この設計は公開データと運用履歴を分離しません。

proposal.mdの背景と範囲を前提にします。

## Goals / Non-Goals

**Goals:**

- JSON-LDを公開Placeの唯一の正本にします。
- 標準語彙だけで施設、geometry、関連record、Datasetを表現します。
- Gitを変更履歴の唯一の正本にします。
- 自動照合は関連性だけを公開します。
- 静的配布で発見性と版固定取得を両立します。

**Non-Goals:**

- 独自オントロジー、独自URIドメイン、W3ID、DOIを導入しません。
- 営業時間を変換または公開しません。
- 町名、電話番号、OSMタグを公開または導出しません。
- 画像とrights文字列を公開しません。
- 独自`categoryIds`を公開または移行しません。
- OSM RDFやWikidata RDFを取り込みません。
- WAMを施設の同一性や正本として扱いません。

## Decisions

### Place identifier uses URN UUID

既存UUIDを`urn:uuid:<uuid>`へ写します。
この識別子はドメイン、DNS、redirect運用を必要としません。

独自ドメインまたはW3IDは採用しません。
どちらも恒久的なredirect保守を追加します。

### Place data uses standard vocabulary

Placeは`schema:Place`と`geo:Feature`を使います。
Point geometryは`geo:hasGeometry`、`geo:asGeoJSON`、`geo:geoJSONLiteral`で表現します。
Datasetは`schema:Dataset`と`DataDownload`を使います。

schema.orgだけでgeometryを表す案は採用しません。
GeoSPARQLはgeometryの明確な標準表現を提供します。

### Automated associations use rdfs:seeAlso

自動照合したOSM、Wikidata、WAMのURLまたは公開recordを`rdfs:seeAlso`へ出します。

`schema:sameAs`は採用しません。
これは同一性を曖昧なく示すため、自動照合の一般出力には強すぎます。
SKOS match関係は概念間の対応が必要な場合まで保留します。
`prov:wasDerivedFrom`はPlaceではなくDataset全体の入力来歴だけに使います。

WAMの公開Placeへの反映も`rdfs:seeAlso`だけにします。
WAMの住所、サービス種別、電話番号を公開Placeへ移しません。

### History belongs to Git

公開正本から`audit`、参照のcurrent/superseded履歴、changedAt、LLM投票ログを除きます。
レビューや更新の履歴はGit commit、PR、Releaseへ残します。

別の監査ストアは採用しません。
小規模データに新たな永続系を追加するためです。

### Publication exclusion belongs to search input

公開しない施設候補は、検索入力に`publish: false`を明示します。
この指定を持つ候補からPlace recordを公開生成しません。

JSONCのコメントは採用しません。
JSON-LDと通常のJSON処理系はコメントを許容せず、専用parserが必要になるためです。

### Canonical JSON-LD is directly editable

maintainerはcanonical JSON-LDを直接編集します。
CLIは構文、識別子、公開除外の検証だけを提供します。

`fac`による属性、参照、履歴の自動変更は採用しません。

### Dataset distribution uses GitHub Pages and Releases

GitHub PagesはDataset landing pageとcurrent JSON-LDを提供します。
GitHub Releaseは版固定snapshotを提供します。

Zenodoは外部引用が必要になった時まで保留します。
W3IDと独自ドメインは、URIのWeb解決が実際に必要になった時まで保留します。

### Human review uses committed YAML and pull requests

人手reviewはcommit済みYAMLだけを編集面にします。
YAMLはcandidate reportのSHA-256を持ち、選択をreport内candidateへ制限します。
PRはreviewの履歴と承認境界を提供します。

Issue本文のcheckboxと候補payloadは採用しません。
本文編集は入力形式を安定させず、旧parserの保守を増やすためです。

### GeoJSON ends at migration cutover

GeoJSONの公開、互換生成、manifest entryは移行時に終了します。
current distributionとRelease snapshotはJSON-LDだけを提供します。

一時的な並行配布は採用しません。
二つの公開形式を保守すると、正本の移行目的に反するためです。

### Town derivation ends at migration cutover

town polygonからの町名導出は終了します。
`src.retrieve_towns`、pinned town data、town update workflow、関連testを削除します。

町名は派生値であり、公開Place正本の責務にしません。
電話番号とOSMタグも、上流raw snapshotに留めて公開Placeへ出しません。

画像は公開可否と利用許諾を検証できないため、公開Placeへ出しません。

### Licensing separates project assets from sources

リポジトリ固有の資産はCC0で公開します。
OSMはODbL、WikidataはCC0、WAMは配布ページの利用条件URLを個別に表示します。

公開Dataset全体をCC0と主張しません。
sourceごとの条件が異なるためです。

### OpenSpec change replaces legacy maintenance policy

`docs/reference/data-maintenance-spec.md`を削除します。
このchangeのproposal、design、specs、tasksを移行の判断と実装順序の正本にします。

### Voters must be independent

三者の設定を分けます。
実行前に正規化済み`(base_url, model)`がすべて異なることを検証します。
API keyは公開データ、ログ、Release artifactへ書きません。

## Risks / Trade-offs

- [URN UUIDはブラウザで解決できない] → landing pageとdownload URLをDataset単位で提供します。
- [rdfs:seeAlsoは関係の意味を細かく示さない] → 同一性を誤って主張するより安全な初期値にします。
- [GeoJSON利用者が移行を要する] → 移行期間、変換物、明確なbreaking-change文書を用意します。
- [非公開指定を見落とす] → `publish: false`を必須の明示指定とし、公開生成テストで検証します。
- [WAMの住所が揺れる] → 住所を照合補助とし、無条件の正本値にしません。
- [独自categoryを失う] → 必要な場合はGit履歴から復元します。
- [外部モデルが利用不能] → 照合を失敗として扱い、既存の公開関連リンクを推測で変更しません。
- [GeoJSON利用者が即時移行できない] → breaking changeをREADME、landing page、Release notesで明示します。
- [町名を利用する利用者が移行できない] → town fieldの終了をbreaking changeとして明示します。
- [画像利用者が移行できない] → images fieldの終了をbreaking changeとして明示します。

## Migration Plan

1. 現行レジストリから候補JSON-LDを生成し、件数とIDを照合します。
2. JSON-LDのschema、geometry、関連リンクを検証します。
3. 公開生成処理、CLI、更新処理をJSON-LD中心へ移します。
4. PagesとRelease用の配布物を生成し、再現性を検証します。
5. 互換性の扱いを告知して旧registryと旧公開形式を削除します。
6. 問題があれば、Gitで直前の公開版へ戻します。

## Open Questions

- WAM service typeをどの既存標準語彙で表すかは、入力値と利用目的を確認して実装時に決めます。
- current JSON-LDをGitHub Pagesのどの固定pathへ置くかは、Pages設定時に決めます。
