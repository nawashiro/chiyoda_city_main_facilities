# Proposal

## Why

作業者向け文書は、低レベルの Python コマンド、手動公開コピー同期、workflow の内部実装、古い SpecKit 手順を露出しています。これらを `./fac` の明確な build / verify 操作と OpenSpec 中心の仕様管理へ置き換え、初参加者が安全に変更を検証できる最短経路を作ります。

## What Changes

- `./fac build` を追加し、canonical JSON-LD を検証して `site/places.jsonld` を同期します。
- `./fac verify` を追加し、ファイルを変更せずにテスト、JSON-LD、公開コピー整合性、差分書式を検査します。
- `./fac verify` は `build` を実行しません。作業者は `build` の後に `verify` を実行します。
- **BREAKING** `.specify/` の SpecKit commands、templates、scripts、workflow registry、constitution を削除します。
- 完了済み OpenSpec change を archive し、OpenSpec durable specs を仕様の正本として維持します。
- 作業者向け文書を最短の build / verify 経路へ再構成します。公開コピーの手動同期、workflow 内部処理、重複した検証手順、GeoSPARQL の説明を削除または分離します。
- Markdown を一般的な formatter で整え、CJK と ASCII の境界空白を一貫させます。
- archive により明らかになった durable spec の短すぎる Purpose を修正し、strict validation の警告を解消します。

## Capabilities

### New Capabilities

- `maintainer-workflow`: 作業者が `./fac build` と `./fac verify` を使い、canonical JSON-LD、公開コピー、検証結果を安全かつ再現可能に扱う契約を定義します。

### Modified Capabilities

- なし。

## Impact

- `fac`、`src/fac_cli.py`、公開コピー生成・検証処理、テスト、GitHub Actions の確認手順に影響します。
- `.specify/` を削除し、OpenSpec の archive、durable specs、change artifacts を維持します。
- `README.md`、Diátaxis 文書、Markdown formatter 設定、作業者向け command examples に影響します。
- 公開 Place JSON-LD の record 内容、`schema:geo` 表現、公開 distribution の内容、OSM review の committed YAML / PR 契約は変更しません。
