# Tasks

## 1. カテゴリ語彙文書

- [x] 1.1 採用コードの初版リストを確定する（初回判断の対象91施設の分類に必要な約20コードと、福祉は1499の集約）し、出典のGIF POIコード表のGitHubタグを記録する。検証: リストのレビューと、タグ参照URLの確認
- [x] 1.2 `data/categories.jsonld`を`DefinedTermSet`/`DefinedTerm`で作成する（`@id`は`#4桁コード`、`schema:identifier`の`PropertyValue`に`propertyID: gif-poi`、日本語ラベル）。検証: `./fac jsonld-validate data/categories.jsonld`または新設の語彙検証を通す
- [x] 1.3 語彙の検証（schema.org形式、fragmentの4桁コード、gif-poi識別子、出典の版記録）をテストに加える。検証: テストが通る

## 2. 翻訳規則と判断記録

- [x] 2.1 `data/category-rules.json`の読み込みと、タグ・名称の規則評価（一意な一致のみ確定）を実装する。検証: 単一一致・0一致・複数一致の3ケースのテストが通る
- [x] 2.2 `data/categories.json`の判断記録の読み書きと、語彙にないコードを検証で弾く処理を実装する。検証: 未知コードで検証が失敗するテストが通る
- [x] 2.3 関連付けOSM要素の変更時だけ判断を未解決へ戻す再評価の条件を実装する。検証: タグ変更で判断が保持され、関連付け変更で未解決になるテストが通る

## 3. Jev判定

- [x] 3.1 rule未確定の施設に対するJev判定（語彙の採用コードを候補にする）と、閾値以上の`method: jev`採用を実装する。検証: 高信頼度で自動採用されるテストが通る
- [x] 3.2 閾値未満・該当なし・候補なしを確認Issueへ出す流れと、該当なしを未分類のまま保つ処理を実装する。検証: 未解決のみIssue対象になり、判断記録が変わらないテストが通る
- [x] 3.3 Jevの認証・通信失敗を判断として扱わない処理を実装する。検証: 失敗時に判断記録と公開物が変わらないテストが通る

## 4. fac CLI

- [x] 4.1 `fac category review`（rule提案と未解決の一覧、rule結果と保存済み判断の乖離の報告）を実装する。検証: 疑似データで一覧と乖離報告を確認する
- [x] 4.2 `fac category assign <uuid> <poi-code> --editor <editor>`（語彙にあるコードのみ受理、`method: human`で記録）と`fac category clear <uuid>`を実装する。検証: 未知コードの拒否と取り消しのテストが通る
- [x] 4.3 `fac category refresh`（ruleの再評価とJev判定の実行、判断記録と正本の更新）を実装する。月次更新の流れからも呼ぶ。検証: 疑似データで再評価と採用のテストが通る

## 5. 正本と公開

- [x] 5.1 `src/facility_data.py`の正本生成に`schema:additionalType`（判断の数だけterm URL）を追加し、判断のないrecordに付与しない処理を入れる。検証: 分類あり・なしのrecord生成のテストが通る
- [x] 5.2 `src/facility_data.py`の検証に、additionalTypeのterm URLが語彙文書のtermと一致することの点検を加える。検証: 語彙外URLで検証が失敗するテストが通る
- [x] 5.3 spec修正をdelta spec（`public-jsonld-dataset`、`dataset-publication`）として確定させ、`openspec validate`を通す。正本specへの反映はアーカイブ時の同期で行う
- [x] 5.4 `scripts/prepare_release.py`と`site/index.html`に語彙文書のsite配置と`DataDownload`を加える。検証: site生成後にterm URLが実際に応答することを確認する
- [x] 5.5 Release資産に`categories-<版>.jsonld`を加える。検証: release workflowのビルドで資産が作られることを確認する

## 6. 初回の一括判断

- [ ] 6.1 `fac category review`でrule提案を確認し、Jev判定を実行する。検証: ruleとJevで確定した判断が`data/categories.json`に記録される
- [ ] 6.2 未解決施設を確認Issueへ出し、人の確定を反映する。検証: 全91施設の判断が確定または意図的な未分類になる
- [ ] 6.3 公開生成と検証を通して、additionalTypeつきの正本をsiteへ公開する。検証: `./fac jsonld-validate data/places.jsonld --published`を通す
