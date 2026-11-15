# Design

## Context

正本は`data/places.jsonld`の91施設で、`inputs/facilities.json`が検索入力、`data/osm-decisions.json`が関連付け判断、公開物は`site/places.jsonld`と`site/mirrors/osm.json`（関連付け済み89要素のタグ全文）とRelease資産である。分類の情報はどこにもない。kazaguruma-transitはv2.1.1の`kazaguruma_json`をpinし、`category:en`をルートの`/locations/[category-id]`に使う。

GIF POIコード表（651項目、4桁コード、GitHub `digital-go-jp/GIF`で版管理）は、神社/寺院/教会、博物館/美術館/記念・資料館、銭湯、児童館/学童保育クラブ/保育園/幼稚園を日本の常識どおりに分ける。一方、福祉の細分は1499「その他の社会福祉施設」までしかない。手元のミラーの一次タグは約15パターンであり、タグから約8割の分類が規則で決まる。

## Goals / Non-Goals

**Goals:**

- カテゴリを施設ごとに確定した判断として持ち、公開に`schema:additionalType`のterm URLで渡す
- 語彙はGIF POIコード表の採用サブセットとし、版をGitHubのタグで固定する
- 判断の見直しを関連付けの変更時だけに限定し、月々の分類負担をゼロに保つ

**Non-Goals:**

- 障害者・高齢者福祉の細分（1499に集約。必要になったときに改めて設計する）
- GIFコード651全項目の採用と、コードごとの翻訳規則の整備
- kazaguruma-transit側の移行とサブセット絞り込み
- 公開recordへの日本語ラベルやコード値の複製
- 分類の強制（判断のないrecordは未分類のままでよい）

## Decisions

### Vocabulary IDs are GIF POI codes with term URLs in a DefinedTermSet

語彙文書はschema.orgの`DefinedTermSet`と`DefinedTerm`だけで構成する。各termの`@id`を`https://nawashiro.github.io/chiyoda_city_main_facilities/categories.jsonld#<4桁コード>`にする。外部コードは`schema:identifier`の`schema:PropertyValue`（`propertyID: gif-poi`）に書く。SKOSの`ConceptScheme`と`skos:notation`は採用しない。schema.orgに寄せることで公開レコードと同じ語彙系で完結するからである。GIFはRDF語彙として公開されていないため、term URLと識別子の形式はこのリポジトリが提供する。

代替案としてSKOSを採る路線は、既存のWAM識別子契約（`schema:identifier`の`PropertyValue`）と表記が分かれるため退けた。

### Categories are frozen decisions, not publish-time derivations

判断は`data/categories.json`に施設UUIDごとに保存し、公開生成は保存済み判断だけを写す。OSMタグの揺れで分類が月次で動くのは、公開物の安定性を損なうため採らない。見直しの条件は関連付けOSM要素の変更と人の指示だけである（osm-maintenanceの「根拠が変われば再評価する」と同じ哲学）。分類が変わるときは施設の同一性が変わっているという前提から、名称やタグの変化は見直しの条件にしない。

### Assignment pipeline: rules, then Jev with threshold, then humans only for unresolved

rule（翻訳規則の一意な一致）→ Jev（閾値以上なら`method: jev`で自動採用）→ 未解決だけを確認Issueで人に示す。人手はJevが判断できないとき（閾値未満・該当なし・候補なし）だけに絞り、osm-maintenanceの既存の流れと同じ形にする。人手の直接記録は`fac category assign`で行う。該当なしは判断を記録せず未分類のままにし、関連付けが変われば再評価する。

翻訳規則はコードごとではなく、観測されたタグのパターンごとに書く。規則は`data/category-rules.json`に置き、人が編集する。一次タグのパターンは約15であり、規則の整備はこの表の範囲で終わる。名称の部分一致規則は最小限にし、残りはJevに任せる。

### Vocabulary growth is need-driven

採用コードは、収録する施設の分類に必要な範囲にとどめる（初回の判断を終えた時点で約20）。新しい施設が採用していないコードを必要としたとき、語彙に追加してから判断する。全651コードの体系を抱える設計は、翻訳規則とJev候補の幅を不必要に広げるため採らない。

### Decision storage is separate from association decisions

判断記録は`data/osm-decisions.json`の施設エントリに入れず、`data/categories.json`を分ける。関連付けの判断は候補一覧と根拠を持つのに対し、カテゴリ判断はコードとmethodだけで済み、目的と失効の条件が異なるからである。

## Risks / Trade-offs

- [GIFコード表のGitHub参照が変わる] → 語彙文書にタグ付きの版を記録し、取り込み時にその版の表との突合を検証する
- [term URLの恒久維持] → GitHub Pagesの既存正本と同じURL基盤を使い、新規ドメインを導入しない
- [名称の部分一致規則が脆い] → 規則はタグの一致を主とし、名称規則を最小限にする。誤一致は初回の一括判断で人へ出る
- [rule結果と保存済み判断の乖離が積もる] → `fac category review`が乖離を報告し、人が`clear`して再評価できる
- [未分類recordが分類閲覧の消費者に穴を開ける] → 仕様は未分類を許し、穴の詰め方（kazaguruma側の「その他」扱い）は消費者の設計に任せる

## Migration Plan

1. 語彙文書と翻訳規則表を用意し、採用版のGIFコード表との突合テストを通す
2. `fac category review`でrule提案を確認し、Jev判定を実行して残りを確認Issueで人へ出す。初回の一括判断を完了する
3. 正本の生成に`schema:additionalType`を加え、検証を更新する。specの修正（`public-jsonld-dataset`、`dataset-publication`）を反映する
4. siteとReleaseの配布物に語彙文書を加える
5. 公開recordが増えるだけで既存の`@id`、座標、参照は変わらないため、ロールバックは語彙文書と判断記録を消して生成経路を戻すだけでよい

## Open Questions

なし。語彙の形式、版の固定先、fragmentの形、福祉の集約は探索で決めてある。
