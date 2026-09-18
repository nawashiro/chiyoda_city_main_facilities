# Tasks

## 1. 移行基盤

- [x] 1.1 現行registryからJSON-LD候補を生成し、Place件数と既存UUIDの一致を検証するテストを追加する
- [x] 1.2 JSON-LDの`@context`、URN UUID、schema.org、GeoSPARQLを定義し、JSON-LD展開検証を通す
- [x] 1.3 Place geometryをGeoSPARQLへ出力し、Point geometryの検証テストを通す
- [x] 1.4 公開Placeからaudit、参照履歴、更新時刻、投票ログを除き、非公開を検証するテストを通す
- [x] 1.5 検索入力の`publish: false`を公開除外として実装し、対象PlaceがJSON-LD distributionにないテストを通す
- [x] 1.6 公開Placeから町名、電話番号、OSMタグを除外し、town polygonの導出がないことを検証するテストを通す
- [x] 1.7 独自`categoryIds`をcanonical JSON-LDと公開distributionから削除し、出力に残らないテストを通す
- [x] 1.8 公開Placeから画像とrights文字列を除外し、出力に残らないテストを通す

## 2. 関連データと照合

- [x] 2.1 OSM、Wikidata、WAMの外部識別子を`schema:PropertyValue`へ移し、明示URI以外の`rdfs:seeAlso`と強い同一性語彙を含まないテストを通す
- [x] 2.2 WAMの公開Placeへの反映を外部識別子に限定し、明示URIがある場合だけ`rdfs:seeAlso`を追加し、住所、サービス種別、電話番号が出力にないテストを通す
- [x] 2.3 WAMの複数サービスrecordを施設recordへ複製せず、各外部識別子として保持し、WAM IRIを合成しないテストを通す
- [x] 2.4 三者LLM設定を分離し、重複する正規化済み`(base_url, model)`を拒否するテストを通す
- [x] 2.5 公開JSON-LDにLLM投票ログを保存しないことを検証するテストを通す
- [x] 2.6 candidate reportのSHA-256 bindingと重複OSM割当拒否を維持したreview YAML/PR経路へ一本化し、Issue本文選択経路を削除するテストを通す

## 3. 更新経路の簡素化

- [x] 3.1 registry、audit、current/superseded参照履歴に依存する更新処理をJSON-LD中心へ置換し、更新統合テストを通す
- [x] 3.2 canonical JSON-LDの直接編集を検証する最小CLIへ置換し、属性、参照、履歴を自動変更しないことを確認する
- [x] 3.3 旧registry、旧公開GeoJSON、不要な生成ロジックを削除し、repository validationを通す
- [x] 3.4 GeoJSON専用manifest entry、互換生成、workflow artifact、reproducibility比較を削除し、JSON-LDだけを比較するCIを検証する
- [x] 3.5 `src.retrieve_towns`、pinned town data、town update workflow、town由来のCLIとtestを削除し、町名導出経路がないことを検証する

## 4. 配布

- [x] 4.1 GitHub Pages用Dataset landing pageを作り、`schema:Dataset`のname、description、URLを検証する
- [x] 4.2 current JSON-LDを`DataDownload`として公開し、content URLとencoding formatを検証する
- [ ] 4.3 GitHub Releaseへ版固定JSON-LD snapshotを添付するworkflowを追加し、dry-runまたはfixtureでartifactを検証する
- [ ] 4.4 READMEとDiátaxis文書を移行後の正本、取得方法、互換性変更へ更新し、文書リンクを検証する
- [ ] 4.5 旧保守規約を削除し、このOpenSpec changeを移行の正本として案内する文書を検証する
- [ ] 4.6 `test_documentation_uses_the_diataxis_directory_structure`を削除し、データ処理テストからMarkdownの配置、行数、見出し、文言への拘束を除く
- [ ] 4.7 repository固有資産のCC0と、OSM ODbL、Wikidata CC0、WAM配布ページURLをDataset metadataへ個別に表示し、全DatasetをCC0と表示しないテストを通す

## 5. 統合検証と移行

- [ ] 5.1 fixtureと本番データ候補でJSON-LDのID、件数、geometry、関連リンクを検証する
- [ ] 5.2 GitHub Actionsで公開物の再生成とbyte-level reproducibilityを検証する
- [ ] 5.3 全tests、`python3 -m src.facility_data validate .`、`openspec validate adopt-standards-jsonld --strict`、`git diff --check`を実行する
- [ ] 5.4 移行手順とrollback手順を確認し、Gitの直前公開版へ戻せることを文書で検証する
