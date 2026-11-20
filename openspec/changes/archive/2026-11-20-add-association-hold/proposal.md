# Proposal

## Why

西神田コスモス館のOSM関連付けは、2012年に国土数値情報（公共施設データ2006）から取り込まれた`node/1655927382`を指しています。この要素の名称「西神田児童・家庭支援センター」は区の現行の施設一覧にない名前で、タグ`social_facility=assisted_living`もこの種の施設には当たりません。正しい接続先は実地調査とOSMの修正でしか確定できません。

しかし現状は、月次更新がこの関連付けを前提に関連付け判定と公開を続け、カテゴリ1499もその輸入タグから導かれています。実地調査待ちを明示して関連付けの対象から外す仕組みがないため、誤った接続先が判断記録と公開物に残り続けます。

## What Changes

- 施設のOSM関連付けに「保留」状態を追加します。保留は理由・編集者・実行時刻つきで判断記録`data/osm-decisions.json`に保存します。
- 専用CLIに`./fac assoc <query_id> --hold --reason <理由> [--editor <editor>]`を追加します。保留の記録時にOSM参照と照合由来のWikidata参照を解除し、施設UUIDと座標を残し、カテゴリ判断を取り消します。
- 保留の記録・解除・確認はすべて専用CLI（`./fac assoc`、`./fac category review`）から行います。判断記録や公開物を直接編集する経路は設けません。
- 月次更新と手動再実行は、保留中の施設を関連付けの再評価と確認Issueの対象にしません。候補・タグ・名称が変わっても保留を維持します。
- 保留の解除は、実地調査で確定した接続先を`./fac assoc <query_id> --osm-id <id>`で記録するか、`./fac assoc <query_id> --choice none`で人の「該当なし」を確定したときに行います。
- 西神田コスモス館に保留を適用します。OSM要素の修正は実地調査の別作業です。

## Capabilities

### New Capabilities

なし。

### Modified Capabilities

- `osm-maintenance`: 実地調査待ちの保留状態、専用CLI、月次更新からの除外、参照の解除、解除条件を追加します。
- `facility-categories`: 保留中の施設のカテゴリ判断を取り消し、カテゴリ確認Issueに提示しないようにします。

## Impact

- `data/osm-decisions.json`（保留エントリ）、`data/categories.json`、`data/places.jsonld`と公開物
- `src/fac_cli.py`（`assoc --hold`）、`src/resolve_osm_candidates.py`（保留の維持）、`src/osm_maintenance.py`（`present`の除外）、`src/facility_categories.py`（保留の除外と判断取り消し）
- `docs/reference/cli.md`、`docs/reference/data-contracts.md`、`docs/how-to/review-osm-candidates.md`
- テスト（保留の維持・解除、公開recordの参照とgif-poiの非出力、確認Issueの非提示）
