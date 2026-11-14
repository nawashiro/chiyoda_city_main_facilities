# Proposal

## Why

docs/には、CIやActionsがすでに実行する手順を人間に写経させる文書と、`openspec/specs`が管理するふるまいの説明の写しがある。人間が実際に行う操作は、`./fac` CLIの実行、確認Issueでの判断、外部データの利用者・取得元への契約表示の三つだけなので、それ以外の文書には読み手が存在せず、実態とのずれを保守する負担だけが残る。

## What Changes

- 削除する（システムのふるまいへの言及のみで、人間固有の操作がない文書）:
  - `docs/explanation/data-flow.md` — 更新のふるまいは`osm-maintenance`・`dataset-publication`仕様が管理する
  - `docs/reference/verification.md` — 検証手順は`validate.yml`がPRとmain pushで毎回実行する
  - `docs/tutorials/first-data-change.md` — 実質はCLI操作（`./fac in`・`assoc`）とCI検証の組み合わせで、独自の手順がない
- 瘦せる:
  - `docs/how-to/update-osm.md` — 「照合条件」（`osm-maintenance`仕様の写し）と「Jevの使用量と費用」（料金と使用量はTypeSafeのダッシュボードで確認できる）を削除する。「保存済み判断の提示」の`python3 -m src.osm_maintenance present .`は`docs/reference/cli.md`へ移す。一回限りの初期設定と、再実行・失敗時の対処は残す
  - `docs/reference/data-contracts.md` — 「判断記録」（生成物で人が直接編集しない`osm-decisions.json`の項目表）を削除する。公開JSON-LDと検索入力の契約は残す
  - `docs/how-to/publish-release-jsonld.md` — リリースworkflowが検証するため「正本を検証する」を削除し、workflowの動作説明を削る。手動実行、Releaseの公開、rollback手順は残す
- 更新する:
  - `README.md` — 削除した文書への案内を除く。「データを初めて編集する」と「実地調査で確定した接続先を反映する」をCLIの案内へ統合し、「変更を検証する」はCIが実行することを明示する
  - `docs/reference/cli.md` — `osm_maintenance`の再提示コマンドの節を追加する
- 削除対象文書への文書間リンクは、上記の更新で消える。システムのふるまい、データ契約の内容、CIの構成は変わらない

## Capabilities

### New Capabilities

（なし。文書の整理のみで、ふるまいのレベルでは何も変わらない）

### Modified Capabilities

（なし）

## Impact

- `docs/`は9ファイルから5ファイルになる（`cli.md`、`review-osm-candidates.md`、`sources-and-licenses.md`、`data-contracts.md`、`publish-release-jsonld.md`）。空になった`docs/explanation/`と`docs/tutorials/`は除去する
- READMEの作業表と文書への案内を更新する
- コード、workflow、`openspec/specs`は変更しない
- 外部から削除対象の文書URLへ張られたリンクは無効になる
