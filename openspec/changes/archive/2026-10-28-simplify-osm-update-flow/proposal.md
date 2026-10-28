# Proposal

## Why

外部データの更新が手動起動、三者投票、確認用PR、反映用PRに分かれ、一部の判断待ちで確定済みの更新まで止まる。WAMの更新経路と出典別の検索入力も残っているため、OSMの月次更新と判断が難しい施設の人手確認に整理する。

## What Changes

- 毎月のGitHub ActionsでOSMを取得し、検証に通った確定分を正本とGitHub Pagesへ自動反映する。手動起動は再実行用に残す。
- 照合は既存のOSM参照、一意なQID、Jevの順に行う。名称と近接座標だけによる自動確定を廃止し、距離は候補の抽出に使う。
- **BREAKING** 三者投票とChat Completions互換の接続設定を廃止し、TypeSafeのJev一つによる選択と信頼度の判定へ置き換える。
- **BREAKING** 人手確認用YAMLと二段階のPRを廃止する。判断が難しい施設についてIssueを作り、候補または「該当なし」のチェックと確定操作で判断を受け付ける。
- 既存の接続は取得結果に残る間維持する。人が選んだ接続も同じように扱い、入力ハッシュの変化だけで再審査しない。人の「該当なし」と未解決のJev結果は、照合根拠が同じ間は再利用する。
- 接続先がない施設は参照だけを解除し、一つの通常Issueへまとめて通知する。候補なしとJevの高信頼度の「該当なし」に、人の確定操作は求めない。
- 取得・判定結果をGitへ保存してからIssueへ提示する。回答処理は保存済み候補への回答の反映・保存・公開・完了に限定し、取得やJev判定、未解決Issueの再提示を行わない。push失敗では停止し、取得からの自動やり直しは行わない。
- **BREAKING** WAMの取得・同定・設定・保存データ・公開識別子を除去する。参考資料と必要な帰属表示を文書に残し、既存施設のUUID、検索対象、利用可能な座標を維持する。
- 出典別の検索入力を一つに統合し、未使用の更新コマンドと重複した再同定経路を削除する。

## Capabilities

### New Capabilities

- `osm-maintenance`: 登録済み施設の月次更新、照合順序、判断の再利用、確定分の公開、失敗時の扱い。

### Modified Capabilities

- `independent-link-review`: 独立した三者投票とYAML・PRを、Jev一つとIssueのチェックボックスによる人手判断に置き換える。
- `related-record-links`: WAM識別子の出力を廃止し、OSMとWikidataの関連参照を更新・解除する契約に整理する。
- `dataset-publication`: 自動更新後のPages公開と、WAMを参考資料に移した後の帰属表示を定める。

## Impact

対象は`src/retrieve_osm.py`、`src/resolve_osm_candidates.py`、`src/github_osm_review.py`、`src/facility_data.py`、そのテスト、GitHub Actions、検索入力、保存する判断、運用文書である。WAM専用コード・テスト・workflow、`reidentify-sources.yml`、確認用PRを処理するworkflowとスクリプト、古いreview用ファイルを削除する。

公開形式はJSON-LD、唯一の正本は`data/places.jsonld`とし、既存UUIDを維持する。施設の追加・除外は登録内容の明示的な変更で行い、月次取得から施設を自動追加しない。Jevの認証情報はGitHub Actionsのsecretに置く。本変更で新しい公開形式や確認用Webアプリは導入しない。
