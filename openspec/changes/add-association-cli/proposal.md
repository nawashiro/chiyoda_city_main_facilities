# Proposal: 実地調査の関連付けを反映するCLIサブコマンド

## Why
接続先がない施設へのOSM収録など、実地調査で確定したOSM IDを人の判断として正本へ反映する経路がCLIに存在しない。自動判定できないこの種の反映は、`data/osm-decisions.json`と`data/places.jsonld`のアドホックな直接編集でしか行えず、根拠・判断記録の形式を守る責任を実行者に負わせる手作業になっている。専用CLIで一つの操作にまとめる。

## What Changes
- `./fac`に新サブコマンド`assoc`を追加する。
  - `./fac assoc <query_id> --osm-id <element_id>`: OSM APIから要素（node/way/relation）の実データを取得し、`IDENTITY_TAGS`に基づく根拠（候補一つ）を作り、`method: human`の判断を`data/osm-decisions.json`へ保存して`data/places.jsonld`へ適用する。
  - `--choice none`で「該当なし」を記録できる。
  - 編集者は`--editor`またはgit設定のuser.nameから取り、`editedAt`は実行時刻とする。
- 反映は既存の`apply_decisions`経由のみとし、二重実装やフォールバック経路を持たない。

## Capabilities
### Modified Capabilities
- `osm-maintenance`: 人の判断の記録と正本への適用に、実地調査の接続先を人の判断として保存・適用する要件を追加する。

## Impact
- `src/fac_cli.py`（サブコマンド追加）、`src/resolve_osm_candidates.py`（既存の`evidence_for`/`apply_decisions`を再利用）。
- OSM API（api.openstreetmap.org / openstreetmap.org/api/0.6）へのネットワーク取得がCLI実行時に必要。既存の`data/places.jsonld`・`data/osm-decisions.json`の形式は変わらない。
- `update-osm.md`・`review-osm-candidates.md`で実地調査結果の反映手順を参照する箇所の更新。
