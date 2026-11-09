# Tasks

## 1. データモデルと検証

- [x] 1.1 `facility_data.py` に `schema:subjectOf` の読み込み検証を追加（WebPageノード、許容ドメイン `walkingnavi.com` / `lwd.tokyo` の `schema:url`、不正時 ValueError）し、既存の検証テストに失敗ケース／成功ケースを追加して通す
- [x] 1.2 公開出力が `subjectOf` をそのまま出力することを確認するテストを追加し通す

## 2. CLI

- [x] 2.1 `fac link`（追加）と `fac link rm`（解除）を実装し、Outlet例で正常系と許容ドメイン外URL拒否のテストを追加して通す
- [x] 2.2 `fac --help` と `fac link --help` の表示が実際の挙動と一致することを確認

## 3. 関連付け実施（施行者: Chiyoda-Dev）

- [x] 3.1 言葉の道案内の該当施設を特定し、`fac link` で登録する
- [x] 3.2 東京バリアフリーマップの該当施設を特定し、`fac link` で登録する
- [x] 3.3 登録結果一覧をissue #67へ報告する（`[bot]` 付き）

## 4. 統合確認

- [x] 4.1 実データ `data/places.jsonld` に対して追加・解除・jsonld-validate の一連を実行し、UUIDと `rdfs:seeAlso` が不変であることを `./fac jsonld-validate` で確認
