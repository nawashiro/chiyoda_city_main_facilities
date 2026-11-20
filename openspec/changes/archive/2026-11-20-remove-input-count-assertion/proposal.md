# Proposal

## Why

`tests/test_osm_maintenance.py`の`test_migration_preserves_targets_and_public_geometry`が検索入力の総数（現在106件）を固定しており、`./fac in add`や`./fac in rm`でデータを増減するたびにテストの書き換えが必要になります。今回も3件追加したため103から106へ更新しました。件数はシステムの振る舞いではなく、データのスナップショットです。

## What Changes

- 件数のassert（`len(queries)`と一意ID数の2行）を削除します。
- 残す不変条件は、公開recordのIDが一意であること、公開recordが宣言済みの検索入力だけであること、`gif-poi`以外の識別子が混ざらないことです。
- テスト名を実態に合わせて`test_published_places_are_declared_and_unique`に変更します（現在の名前は件数固定と移行の番人を想定しており、実態と合っていません）。

## Capabilities

### New Capabilities

なし。

### Modified Capabilities

なし（テストのみで、システムの振る舞いは変わりません）。

## Impact

- `tests/test_osm_maintenance.py`
- 非目標: 移行時のUUID一覧のfixture化、件数を別テストに残すこと、データやCLIの変更。
