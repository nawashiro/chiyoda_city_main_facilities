# Tasks

## 1. 移行基盤

- [ ] 1.1 現行registryからJSON-LD候補を生成し、Place件数と既存UUIDの一致を検証するテストを追加する
- [ ] 1.2 JSON-LDの`@context`、URN UUID、schema.org、GeoSPARQLを定義し、JSON-LD展開検証を通す
- [ ] 1.3 Place geometryをGeoSPARQLへ出力し、Point geometryの検証テストを通す
- [ ] 1.4 公開Placeからaudit、参照履歴、更新時刻、投票ログを除き、非公開を検証するテストを通す
- [ ] 1.5 非公開Placeを公開JSON-LD distributionから除外し、漏えいを防ぐテストを通す

## 2. 関連データと照合

- [ ] 2.1 OSM、Wikidata、WAMの自動関連先を`rdfs:seeAlso`へ移し、強い同一性語彙を含まないテストを通す
- [ ] 2.2 WAMの住所とサービス種別の標準語彙を、施設とサービスを混同しない条件で選定し、対応表とテストを追加する
- [ ] 2.3 WAMの複数サービスrecordを施設recordへ複製せず、関連情報として保持するテストを通す
- [ ] 2.4 三者LLM設定を分離し、重複する正規化済み`(base_url, model)`を拒否するテストを通す
- [ ] 2.5 公開JSON-LDにLLM投票ログを保存しないことを検証するテストを通す

## 3. 更新経路の簡素化

- [ ] 3.1 registry、audit、current/superseded参照履歴に依存する更新処理をJSON-LD中心へ置換し、更新統合テストを通す
- [ ] 3.2 CLIと検証処理を新しい公開正本へ移し、旧独自スキーマへの書込みがないことを確認する
- [ ] 3.3 旧registry、旧公開GeoJSON、不要な生成ロジックを削除し、repository validationを通す

## 4. 配布

- [ ] 4.1 GitHub Pages用Dataset landing pageを作り、`schema:Dataset`のname、description、URLを検証する
- [ ] 4.2 current JSON-LDを`DataDownload`として公開し、content URLとencoding formatを検証する
- [ ] 4.3 GitHub Releaseへ版固定JSON-LD snapshotを添付するworkflowを追加し、dry-runまたはfixtureでartifactを検証する
- [ ] 4.4 READMEとDiátaxis文書を移行後の正本、取得方法、互換性変更へ更新し、文書リンクを検証する

## 5. 統合検証と移行

- [ ] 5.1 fixtureと本番データ候補でJSON-LDのID、件数、geometry、関連リンクを検証する
- [ ] 5.2 GitHub Actionsで公開物の再生成とbyte-level reproducibilityを検証する
- [ ] 5.3 全tests、`python3 -m src.facility_data validate .`、`openspec validate adopt-standards-jsonld --strict`、`git diff --check`を実行する
- [ ] 5.4 移行手順とrollback手順を確認し、Gitの直前公開版へ戻せることを文書で検証する
