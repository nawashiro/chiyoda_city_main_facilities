# Tasks

## 1. OpenSpec 移行の衛生化

- [x] 1.1 `adopt-standards-jsonld` を archive し、durable specs が `openspec/specs/` に同期されたことを `openspec list --specs --json` で確認する
- [x] 1.2 `independent-link-review` と `public-jsonld-dataset` の Purpose を修正し、各 `openspec validate <spec> --strict` が成功することを確認する

## 2. Maintainer workflow の CLI contract

- [x] 2.1 `./fac build` と非変更の `./fac verify` の成功・失敗・public-copy 不変性を扱う focused CLI tests を追加し、対象 tests が失敗から始まることを確認する
- [x] 2.2 `./fac build` を実装し、canonical validation 成功後にだけ temporary file 経由で `site/places.jsonld` を同期する。成功・不正 canonical・copy failure の tests で確認する
- [x] 2.3 `./fac verify` を実装し、全 tests、repository / JSON-LD validation、byte equality、`git diff --check` を非変更で実行する。同期済み・stale copy・書式エラーの tests で確認する
- [x] 2.4 文書の固定文言を検査する既存 test を、CLI の入出力と終了状態を検査する test に置換し、全 CLI tests が成功することを確認する

## 3. Formatter と SpecKit の除去

- [x] 3.1 repository-local Prettier dependency、format / check scripts、ignore 設定を追加し、Markdown check が成功することを確認する
- [x] 3.2 `.specify/` の commands、templates、scripts、workflow registry、constitution を削除し、`.specify` / `speckit` の repository 外参照がないことを検索で確認する
- [x] 3.3 Markdown を Prettier で整え、CJK と ASCII の境界空白をレビュー可能な差分で統一し、formatter check と `git diff --check` が成功することを確認する

## 4. 作業者向け文書の再構成

- [x] 4.1 README と `first-data-change` を canonical edit、`./fac build`、`./fac verify`、PR 差分確認の最短経路へ更新し、deprecated low-level command examples がないことを確認する
- [x] 4.2 `verification` を command contract と最小診断へ縮小し、仕様・契約の重複説明を OpenSpec に委ねる。`./fac verify` の成功と失敗を実行して確認する
- [x] 4.3 JSON-LD release how-to を通常公開の最小手順へ縮小し、published release 復元を独立した how-to へ分離する。links と Markdown check を確認する
- [x] 4.4 OSM review how-to を committed YAML / PR、merge 後 workflow、production PR の操作と可視結果へ絞り、内部 artifact / hash 処理を除去する。既存 OpenSpec review spec と矛盾しないことを確認する
- [x] 4.5 GeoSPARQL の作業者向け説明を削除し、`schema:geo` を使用する公開 JSON-LD contract を維持する。JSON-LD publication tests が成功することを確認する

## 5. 統合検証

- [x] 5.1 `openspec validate streamline-maintainer-workflow --strict` と strict durable-spec validation を実行し、すべて成功することを確認する
- [x] 5.2 全 test suite、`./fac build`、`./fac verify`、formatter check、`git diff --check` を実行し、すべて成功することを確認する
- [x] 5.3 clean worktree から build / verify を再実行し、public copy が canonical と byte-level で一致し、検証が追跡対象ファイルを変更しないことを確認する
