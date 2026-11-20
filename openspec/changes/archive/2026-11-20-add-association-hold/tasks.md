# Tasks

## 1. 判断記録と関連付け判定

- [x] 1.1 `data/osm-decisions.json`に保留エントリ（`status: hold`、`reason`、`previous`、`human`）を保存できるようにし、`resolve`が保留エントリを再評価せず引き継ぐことを確認する。保留を維持するテストが通る
- [x] 1.2 `apply_decisions`が保留中の施設からOSM参照とWikidata参照を外し、UUID、座標、`schema:subjectOf`を残すことを確認する。公開recordに参照が残らないテストが通る
- [x] 1.3 保留エントリの検証（理由、編集者、実行時刻の必須）を追加し、理由のない保留エントリを拒むテストが通る

## 2. 専用CLI

- [x] 2.1 `./fac assoc <query_id> --hold --reason <理由> --editor <名前>`を追加し、判断記録を手で編集せずに保留を記録できるようにする。保留の記録時に既存のOSM参照とWikidata参照を解除して`data/places.jsonld`と`site/places.jsonld`を更新し、CLIのテストが通る
- [x] 2.2 保留の記録時にカテゴリ判断を取り消し、公開recordから`gif-poi`識別子を外すことを確認する。テストが通る
- [x] 2.3 `--hold`を`--osm-id`、`--choice`と排他にし、`--reason`のない保留と`--hold`なしの`--reason`を`ERROR`と終了コード1で拒むことを確認する。引数検証のテストが通る
- [x] 2.4 `./fac assoc <query_id> --osm-id <id>`と`./fac assoc <query_id> --choice none`が保留を人の判断に置き換えることを確認する。CLIのテストが通る

## 3. 更新とレビュー

- [x] 3.1 カテゴリ確認Issueの対象から保留を外し、`category review`が保留を理由つきで一覧表示することを確認する。テストが通る
- [x] 3.2 `present`と`./fac category refresh`が保留を対象にしないことを確認する。テストが通る
- [x] 3.3 `docs/reference/cli.md`（`assoc --hold`）、`docs/reference/data-contracts.md`（判断記録の状態）、`docs/how-to/review-osm-candidates.md`（保留の記録と解除）を更新し、記載したコマンドがそのまま動くことを確認する

## 4. 西神田コスモス館への適用

- [x] 4.1 `./fac assoc 019fa880-5cd5-7b01-9dd8-2e4787f423aa --hold --reason "OSM要素が国土数値情報（公共施設データ2006）由来で、区の現行施設名と一致しない。実地調査で接続先を確定後に解除" --editor <編集者>`を実行し、公開recordから`node/1655927382`参照とカテゴリ1499が消えたことを`./fac jsonld-validate data/places.jsonld`と`./fac category review`で確認する
- [x] 4.2 実地調査とOSM修正の完了後に、`./fac assoc <query_id> --osm-id <id>`と`./fac category assign`で接続先とカテゴリを記録する手順をdocsへ追記し、CLIの実装と一致することを確認する

## 5. 統合検証

- [x] 5.1 テストスイート全体を実行し、保留を含む公開データが契約を満たすことを確認する
- [ ] 5.2 次回の月次更新（Actionsの`Update OpenStreetMap data`）で、保留が維持され、公開recordに参照と`gif-poi`識別子が戻らないことを確認する（このワークツリーのローカル`imports/openstreetmap/raw.json`が追跡済みの取得メタデータと一致しないため、`refresh --offline`は次回に回す）

## Workflow follow-up

- 実装とレビューが済んだら変更をアーカイブする
- アーカイブ後のspecと公開データを確認する
