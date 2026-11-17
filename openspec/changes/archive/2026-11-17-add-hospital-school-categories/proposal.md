# Proposal

## Why

千代田区立の小学校8校と病院6院を検索対象に追加したが、GIF POI語彙に「小学校」「病院」がなく、カテゴリ判断を記録できない。公開90件のうち89件は分類済みであり、追加14件が未分類のまま残ると分類閲覧の穴になる。加えて、月次更新のカテゴリ再評価が削除済みの`data/categories.jsonld`を参照しており、語彙を追加しても自動では分類されない。

## What Changes

- `data/category-names.jsonld`にGIF POIコード1503「小学校」と1601「病院」を追加する（20コードから22コードへ）。1502「学校」や1606「保健所」では代用しない。
- `data/category-rules.json`に、`amenity=hospital`を1601へ、`amenity=school`かつ名称に「小学校」を含むものを1503へ決める規則を追加する。実際のOSMタグは関連付け後に確認する。
- `src/osm_maintenance.py`のカテゴリ処理ガードを、削除済みの`data/categories.jsonld`から`data/category-names.jsonld`へ直す。月次更新と`present`でカテゴリ再評価とカテゴリ確認Issueの提示が動くようにする。月次更新でも、規則で決まらない関連付け済み施設をJevで判定し、閾値未満だけをIssueで人に示す。
- 追加14件のカテゴリ判断を`data/categories.json`へ記録する。杏雲堂病院は既存の関連付けで即時、残り13件は標準のOSM更新で関連付けを確立した後に判断する。関連付け済みでカテゴリを確定できない施設はカテゴリ確認Issueに残す。
- 語彙のsite配布物を更新し、追加14件がgif-poi識別子を持つことを検証する。既存89件の判断は変更しない。
- カテゴリ処理が語彙と規則の存在下で動くこと、および病院・小学校の規則が一意に決まることを回帰テストで固定する。

## Capabilities

### New Capabilities

なし。

### Modified Capabilities

- `facility-categories`: 月次更新と手動再実行の完了時にカテゴリを再評価し、未解決をカテゴリ確認Issueへ提示することを要求に加える。語彙または規則がない場合はカテゴリ処理を省略する。

## Impact

- データ: `data/category-names.jsonld`、`data/category-rules.json`、`data/categories.json`、`data/places.jsonld`、`data/osm-decisions.json`、`site/category-names.jsonld`、`site/places.jsonld`
- コード: `src/osm_maintenance.py`のガード、`tests/test_osm_maintenance.py`とカテゴリ関連テスト
- 公開物: 追加14件のrecordにgif-poi識別子が加わる。カテゴリ名辞書は2語増える。Release資産は既存のビルド経路で追随する。
- 外部: 追加13件のOSM関連付けは既存のQID一致・Jev判定の流れを使う。新しいAPIや依存は追加しない。
- 対象外: 旧世代の`site/categories.jsonld`の削除、kazaguruma-transit側のサブセット設計、GIFコード表の他の学校・医療コードの採用。
