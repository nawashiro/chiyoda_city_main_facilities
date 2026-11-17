# Tasks

## 1. 語彙と翻訳規則

- [x] 1.1 `data/category-names.jsonld`に1503「小学校」と1601「病院」をコード順で追加する。検証: `./fac jsonld-validate data/category-names.jsonld`が成功し、`load_vocabulary`が22コードを返す
- [x] 1.2 `data/category-rules.json`に`amenity=hospital`を1601へ、`amenity=school`と`nameIncludes: ["小学校"]`を1503へ決める規則を追加する。検証: `validate_rules`がissueを返さず、病院・小学校のタグで`evaluate_rules`が単一のコードを返す
- [x] 1.3 `tests/test_facility_categories.py`に病院・小学校の規則テストを追加する。検証: `python3 -m unittest tests.test_facility_categories`が通る

## 2. 更新経路の復旧

- [x] 2.1 `src/osm_maintenance.py`の`_maintain_categories`と`present`のガードを`data/category-names.jsonld`へ変更する。検証: 語彙と規則があるテスト用rootで、カテゴリ再評価と`save_category_review`が呼ばれる
- [x] 2.2 `facility_categories.refresh`と`rule_proposals`をOSM関連付けのある施設だけに限定する。検証: placeなし・OSM参照なしの施設では規則もJevも実行されず、判断が記録されない
- [x] 2.3 `tests/test_osm_maintenance.py`にガードの回帰テストを追加する。検証: 修正前は失敗し、修正後は通る。`present`のテストでは`FakeGitHub.save_category_review`を記録する
- [x] 2.4 `tests/test_facility_categories.py`に関連付けなし施設のスキップテストを追加する。検証: `judge`が呼ばれず、`data/categories.json`に判断が増えない
- [x] 2.5 カテゴリと更新経路のテストをまとめて実行する。検証: `python3 -m unittest tests.test_osm_maintenance tests.test_facility_categories`が通る
- [x] 2.6 `update`にカテゴリ用の`category_judge`を渡し、`TYPESAFE_API_KEY`がある実行で月次更新もカテゴリJevを使う。検証: `python3 -m unittest tests.test_osm_maintenance`が通り、Jev結果が閾値以上なら`method: jev`、Jevの失敗時は正本と台帳が変わらない
- [x] 2.7 カテゴリ確認Issueに、関連付け済みで判断のない施設も含める。検証: 低信頼度のJev結果が`present`のカテゴリ確認Issueに載る

## 3. 追加施設の関連付けと分類

- [x] 3.1 標準のOSM更新を実行し、追加13件の関連付けを処理する。検証: `python3 -m src.osm_maintenance refresh .`の後、`data/places.jsonld`の追加13件に`rdfs:seeAlso`があるか、未確定として既存のOSM確認Issueに残っている
- [x] 3.2 関連付け後の実タグを確認し、`healthcare=hospital`や`school=elementary`など想定と違うタグがあれば、同じカテゴリへの並列タグ規則を追加し、1.3の規則テストも更新する。検証: `./fac category review`で病院・小学校が一意に1601/1503へ決まり、`python3 -m unittest tests.test_facility_categories`が通る
- [x] 3.3 杏雲堂病院と関連付けが確定した13件のカテゴリ判断を確定する。検証: `data/categories.json`の追加14件が1601または1503で記録され、`data/places.jsonld`と`site/places.jsonld`の該当recordに`gif-poi`識別子がある。規則で決まらない施設は`./fac category assign`で確定する
- [x] 3.4 追加14件すべての関連付けと分類を確認する。検証: `data/places.jsonld`の14件にOSM参照があり、`data/categories.json`の14件が1601または1503で記録されている。未確定が残る場合は既存のOSM確認Issueで人へ渡し、完了までタスクを残す
- [x] 3.5 `docs/reference/cli.md`に`category review/assign/clear/refresh`の使い方と検証方法を追記する。検証: 記載したコマンド例の引数が`./fac category --help`と一致する

## 4. 統合検証と公開

- [x] 4.1 全テストを実行する。検証: `python3 -m unittest discover -s tests`が通る
- [x] 4.2 siteをビルドする。検証: `python3 -m src.facility_data build .`の後、`site/category-names.jsonld`が`data/category-names.jsonld`とバイト一致し、`site/places.jsonld`の追加14件に`gif-poi`識別子がある
- [x] 4.3 公開物を検証する。検証: `./fac jsonld-validate --published site/places.jsonld`と`./fac jsonld-validate data/category-names.jsonld`が成功する
- [x] 4.4 既存判断の不変を確認する。検証: `./fac category review`で既存89件のカテゴリとmethodが変わっておらず、追加14件が期待どおり分類されている
- [x] 4.5 OpenSpecの変更を検証する。検証: `openspec validate add-hospital-school-categories --strict`が通る

## Workflow follow-up

- レビュー後に変更をarchiveし、`facility-categories`のdeltaが`openspec/specs`のspecへ反映されたことを確認する。
