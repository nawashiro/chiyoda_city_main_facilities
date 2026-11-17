# Design

## Context

語彙は20コード、公開施設は90件、カテゴリ判断は89件である。今日追加した14件（小学校8校、病院6院）のうち、placeを持つのは杏雲堂病院だけで、残り13件は検索入力のままである。既存の89判断は凍結済みで、今回の追加で変更しない。

`src/osm_maintenance.py`の`_maintain_categories`と`present`は、リファクタで削除された`data/categories.jsonld`を初期化済みの目印にしている。ファイルが存在しないため、月次更新ではカテゴリ再評価もカテゴリ確認Issueの提示も実行されない。`./fac category refresh`を直接実行すれば動くが、CIの更新経路では動かない。

## Goals / Non-Goals

**Goals:**

- 語彙に1503「小学校」と1601「病院」を追加し、追加14件を分類できるようにする
- 病院・小学校を一意に決める翻訳規則を追加する
- 月次更新と手動再実行でカテゴリ再評価と未解決提示が動くようにする
- 自動分類の対象をOSM関連付けのある施設に限定し、関連付けのない入力に名前だけの判断を記録しない
- 追加14件の判断を記録し、公開recordにgif-poi識別子を付ける

**Non-Goals:**

- 1502「学校」、1504「中学校」、1602「診療所」など他の学校・医療コードの採用
- 既存89件の判断の見直し
- `site/categories.jsonld`の削除（旧世代の未参照物として別途扱う）
- kazaguruma-transit側のサブセット設計
- OSM関連付けの判定アルゴリズムの変更

## Decisions

### Adopt 1503 and 1601, not their broader alternatives

小学校には1503「小学校」、病院には1601「病院」を採用する。1502「学校」は小中学校・高校をまとめる総称で、1504「中学校」を将来追加したときに区別できない。1606「保健所」は医療法上の病院ではなく、1499「その他の社会福祉施設」も病院の受け皿ではない。既存語彙が保育園・児童館・図書館を具体的に分けている方針に合わせる。

### Rules are tag-first; the school rule also requires the name

病院は`amenity=hospital`だけで1601に決める。小学校は`amenity=school`だけでは将来の中学校も1503に誤分類するため、`amenity=school`と名称の「小学校」をANDで要求する。関連付け後の実タグが`healthcare=hospital`や`school=elementary`中心であれば、名称だけの規則に逃げず、同じカテゴリへの並列のタグ規則を追加する。名称だけの規則は関連付けのない検索入力にも一致し得るため採用しない。

### The vocabulary file is the initialization marker

`_maintain_categories`と`present`のガードを`data/categories.jsonld`から`data/category-names.jsonld`へ変える。語彙はカテゴリ機能の初期化に必ず存在し、判断記録`data/categories.json`は空でもよい。`data/categories.jsonld`を目印に戻す選択肢は、ファイルが存在せず機能が永久に動かないため採らない。`present`も同じ条件に揃え、カテゴリ確認Issueの提示を再開する。

### Auto-classification requires an OSM association

`facility_categories.refresh`は、OSM関連付けのある施設だけを規則提案とJevの対象にする。placeのない検索入力やOSM参照のないplaceは、関連付けが確定するまで未分類のまま保つ。現状の`refresh`はplaceのない入力も名称だけでJevに渡し、`osmId: null`の判断を記録し得る。これを放置すると、ガード修正後に月次更新が未関連付け13件へ名前だけの判断を書き込む。人手の`fac category assign`はplaceがあれば従来どおり使える。

### Category Jev runs inside the monthly update

`update`の`judge`はOSM候補の照合用で、カテゴリのJevとは引数の形が違う。カテゴリ用は別の`category_judge`として受け取り、`TYPESAFE_API_KEY`がある場合に`_request_category`を渡す。鍵がない実行では規則だけで再評価し、Jevを省略したことを出力する。鍵があるCIでは、規則で決まらない関連付け済み施設が閾値以上なら`method: jev`で確定し、人へ回るのは閾値未満だけになる。Jevの失敗は更新全体の失敗として扱い、判断を書かない。

カテゴリ確認Issueの対象は、判断の失効・消失だけでなく、関連付け済みで判断のない施設も含める。規則でもJevでも決まらなかった施設をIssueから漏らすと、月次更新は未分類を黙って残すことになる。

### Use the standard OSM update for the 13 associations

残り13件はアドホックなスクリプトでplaceを作らず、既存の`python -m src.osm_maintenance refresh`のQID一致・Jev判定に任せる。関連付けが確定しない施設は既存のOSM確認Issueに残し、カテゴリは関連付け後に決める。杏雲堂病院は既存の`node/1420766935`があるため、語彙追加後に`fac category assign`または再評価で1601を記録できる。

### The site vocabulary is generated, not hand-edited

`site/category-names.jsonld`は`build_repository`が`data/category-names.jsonld`のバイト列を複製する。語彙追加後にsiteを手で編集せず、ビルドで追随させる。Release資産`category-names-<版>.jsonld`も同じsiteから作られるため、workflowの変更は不要である。

## Risks / Trade-offs

- [実際のOSMタグが想定と違う] → 関連付け後にタグを確認し、`healthcare=hospital`や`school=elementary`には並列のタグ規則を追加する。名称だけの規則は使わない
- [13件の関連付けが自動で確定しない] → 既存のOSM確認Issueで人へ渡す。カテゴリは関連付け後に決まり、分類の完成は関連付けの完了に依存する
- [ガード修正でCIのJev呼び出しが増える] → 対象は関連付け済みの未決定・stale施設に限る。Jevの認証・通信失敗は更新全体の失敗として扱い、判断を公開しない
- [学校規則の名称条件が実名称と合わない] → 一意に決まらない施設はJevへフォールバックする。規則の追加・修正は`fac category review`で確認できる
- [語彙追加後にロールバックする] → 1503/1601の判断を先に`fac category clear`で消し、その後で語彙からコードを外す。逆順だと未知コードで検証が失敗する

## Migration Plan

1. 語彙に1503/1601を追加し、病院・小学校の規則を追加する
2. `_maintain_categories`と`present`のガードを直し、`refresh`をOSM関連付けのある施設だけに限定する
3. 月次更新のカテゴリJevと、判断のない関連付け済み施設のIssue提示を配線する
4. ガード、関連付け限定、Jev、未解決提示の回帰テストと、病院・小学校規則のテストを追加する
5. siteをビルドし、語彙と公開recordの検証を通す
6. 標準のOSM更新で13件の関連付けを確定し、杏雲堂病院と合わせて14件のカテゴリ判断を記録する
7. 未解決があればカテゴリ確認Issueで人へ渡し、全14件の判断または意図的な未分類を確認する
8. 再度ビルドし、`site/places.jsonld`の14件にgif-poi識別子があることを確認する

## Open Questions

なし。実タグの確認と関連付けの成否は実装時の検証で決まり、仕様・方針・タスク分割を変えない。
