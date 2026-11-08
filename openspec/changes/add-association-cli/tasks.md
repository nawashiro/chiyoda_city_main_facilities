# Tasks: 実地調査の関連付けを反映するCLIサブコマンド

## 1. 根拠構築の追加
- [x] 1.1 `src/resolve_osm_candidates.py`に単一OSM要素から候補一つの根拠を作る関数を追加する（`IDENTITY_TAGS`の選別とタグソートを再利用、要素 habitants URL/座標はAPIレスポンスから）。
- [x] 1.2 way/relationの座標は形状から中心点を算出するヘルパーを追加しテストする。

## 2. CLIサブコマンド
- [x] 2.1 `src/fac_cli.py`に`assoc <query_id> --osm-id <element_id>`と`--editor`、`--choice none`を実装する（OSM API取得→根拠→判断記録→`apply_decisions`→両ファイル保存の順に、検証が全て通ってから書く）。
- [x] 2.2 OSM APIが失敗した、要素が存在しない、対象検索入力がない、他施設への割り当て重複のとき、ファイルを書かずERRORを返す。

## 3. テスト
- [x] 3.1 API取得を差し替えたテストで、node/wayそれぞれの判断保存と正本適用を検証する。
- [x] 3.2 存在しない要素・該当なし・重複割り当てのテストを追加する。

## 4. ドキュメント
- [x] 4.1 `docs/reference/cli.md`に`assoc`を追記する。
- [x] 4.2 `docs/how-to/review-osm-candidates.md`の「OSM接続先なし」節に、実地調査後の反映手順として`./fac assoc`を追記する。
- [x] 4.3 `openspec validate --change add-association-cli`と`src.facility_data validate .`、`unittest`を通す。
