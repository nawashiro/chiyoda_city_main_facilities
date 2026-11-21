# Proposal

## Why

`./fac assoc --osm-id` は OSM API から要素の実データを取得して人の判断を記録しますが、保持しているOSMスナップショット`imports/openstreetmap/raw.json`にその要素が収録されているかは確認しません。スナップショットより後に作られた要素、またはスナップショット時点で名称が付いていなかった要素を関連付けると、次の月次更新はその要素を見つけられず、関連付けを確認Issueへ戻します。そこで「該当なし」を確定するとリンクが失われます。2026-11-20に西神田コスモス館と神田さくら館で発生し、保留として復旧しました。

## What Changes

- `./fac assoc --osm-id` は、指定された要素が保持スナップショットに収録されているかを記録前に確認します。
- 収録されていない場合、`WARNING`を表示し、確定した人の判断ではなく保留として判断記録に保存します。保留は`status: hold`、`previous`に指定要素、自動の理由、`human`を持ちます。施設UUIDと座標はそのまま残り、OSM参照とWikidata参照は付きません。カテゴリ判断は既存の保留と同じく取り消します。
- スナップショットが無い、または取得メタとハッシュが一致しない場合は、照合できなかったことを`WARNING`で示し、従来どおり確定した人の判断を記録します。
- 保留の解除は既存の経路だけを使います。ミラー更新後に`assoc --osm-id`を再実行するか、`assoc --choice none`で確定します。システムは保留を自動解除しません。

## Capabilities

### New Capabilities

なし。

### Modified Capabilities

- `osm-maintenance`: `assoc --osm-id`の記録前照合、スナップショット未収録時の自動保留、照合できない場合の警告を、人の判断記録の要件へ追加します。

## Impact

- `src/fac_cli.py`（`assoc --osm-id`の照合と保留への分岐）
- 保持スナップショットの検証と収録確認を共有するヘルパー（`src/osm_maintenance.py`の`verified_snapshot`を再利用）
- `docs/reference/cli.md`、`docs/how-to/review-osm-candidates.md`（照合、警告、自動保留、解除手順）
- テスト（収録済み、未収録、スナップショット無し、ハッシュ不一致、保留の解除）
- 既存データの移行はありません。次の`assoc`実行から効きます。
