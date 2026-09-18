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

### History belongs to Git

公開正本から`audit`、参照のcurrent/superseded履歴、changedAt、LLM投票ログを除きます。
レビューや更新の履歴はGit commit、PR、Releaseへ残します。

別の監査ストアは採用しません。
小規模データに新たな永続系を追加するためです。

### Dataset distribution uses GitHub Pages and Releases

GitHub PagesはDataset landing pageとcurrent JSON-LDを提供します。
GitHub Releaseは版固定snapshotを提供します。

Zenodoは外部引用が必要になった時まで保留します。
W3IDと独自ドメインは、URIのWeb解決が実際に必要になった時まで保留します。

### Voters must be independent

三者の設定を分けます。
実行前に正規化済み`(base_url, model)`がすべて異なることを検証します。
API keyは公開データ、ログ、Release artifactへ書きません。

## Risks / Trade-offs

- [URN UUIDはブラウザで解決できない] → landing pageとdownload URLをDataset単位で提供します。
- [rdfs:seeAlsoは関係の意味を細かく示さない] → 同一性を誤って主張するより安全な初期値にします。
- [GeoJSON利用者が移行を要する] → 移行期間、変換物、明確なbreaking-change文書を用意します。
- [WAMの住所が揺れる] → 住所を照合補助とし、無条件の正本値にしません。
- [外部モデルが利用不能] → 照合を失敗として扱い、既存の公開関連リンクを推測で変更しません。

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
