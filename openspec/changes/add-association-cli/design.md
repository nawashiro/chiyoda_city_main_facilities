# Design: 実地調査の関連付けを反映するCLIサブコマンド

## Context
`./fac`は検索入力（`inputs/facilities.json`）の編集だけを扱い、確定したOSM接続の反映はActionsの`osm-maintenance`にしか存在しない。実地調査で人が確定した接続は、根拠・判断・正本を一貫した形で保存する経路がない（proposal参照）。

## Goals / Non-Goals
- Goals: `./fac assoc`で根拠の作成・判断の記録・正本への適用を一操作で行う。
- Non-Goals: 取得・Jev・未解決Issueの再提示は行わない。`update`系処理の別経路の用意もしない。

## Decisions
- **OSM要素の取得はOSM API 0.6の単一要素取得（`https://www.openstreetmap.org/api/0.6/{type}/{id}.json`）を使う。** 候補の名称・座標・タグは確認Issueと同じ情報源でなければ判断根拠として一貫するため。Movisdaスナップショットには反映遅延があり不採用。way/relationは中心座標（`/centroid.json`相当）を算出して候補座標とする。
- **根拠の構築は`resolve_osm_candidates.evidence_for`のタグ選別（`IDENTITY_TAGS`）に沿って候補一つを作る。** 確認Issueの根拠と同じ形式を保つ。`evidence_for`自体は候補集合の絞り込みが前提なので、単一要素用の小さな構築関数を`resolve_osm_candidates.py`に追加し、タグ選別は`IDENTITY_TAGS`を共有する。
- **適用は`apply_decisions`一本道。** 判断レコードの形状は`apply_confirmations`（GitHub回答処理）と同じ`{choice, editor, editedAt, url?, issue?}`。`url`/`issue`は渡された場合だけ保存する。
- **後月の更新で参照が変えても維持される。** `current`への要素は既存参照継続が優先されるため、このCLIで確定した接続は以後の月次でソースレコード継続扱いになる。仕様の追加の措置は不要。
- **ネットワーク失敗時は変更を一切書かない。** 取得→判断オブジェクト構築→`apply_decisions`（検証込み）が全部通ってから両ファイルを書く。

## Risks / Trade-offs
- [OSM APIのレート制限] → 単一リクエストで問題になる量ではない。失敗時は変更なしなので再実行可能。
- [人の編集者の本人確認] → CLI実行者がそのまま記録される。`--editor`を省いた場合はgit `user.name`。GitHub経路のような権限検証はしない（ローカル実行は保守者自身の操作とみなす）。

## Migration Plan
新コマンドの追加のみで既存データ・経路の変更はない。ロールバックはコミットのrevertで足りる。

## Open Questions
なし。
