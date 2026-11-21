# CLI

作業者はリポジトリ root で `./fac` を実行します。

## 検証

```sh
./fac jsonld-validate data/places.jsonld
./fac jsonld-validate --published site/dataset.jsonld
./fac jsonld-validate --vocabulary data/category-vocabulary.jsonld
```

引数なしは施設の正本、`--published`はカテゴリ語彙とrecord形状を含む公開グラフ、`--vocabulary`は非公開のカテゴリ語彙ソースを検証します。成功時、コマンドは出力しません。

## 公開物をビルドする

```sh
python3 -m src.facility_data build .
```

正本`data/places.jsonld`、カテゴリ語彙、形状、判断記録から`site/dataset.jsonld`を合成します。正本は変更しません。公開recordへのカテゴリ反映と画像の付与はこのビルドで行います。

## 検索入力を確認する

```sh
./fac in ls .
./fac in get . SEARCH_ID
```

`inputs/facilities.json`を対象にします。`ls`は全検索入力の名称とIDを出力します。

## 検索入力を追加する

```sh
./fac in add . NAME --lon LONGITUDE --lat LATITUDE
./fac in add . NAME --qid QID
```

`in add` は経度と緯度の組、または Wikidata QID を受け取ります。

## 検索入力を編集する

```sh
./fac in set . SEARCH_ID --name NAME
./fac in set . SEARCH_ID --lon LONGITUDE --lat LATITUDE
./fac in set . SEARCH_ID --qid QID
```

`in set` は名称、経度と緯度の組、または Wikidata QID を変更します。

## 検索入力を除去する

```sh
./fac in rm . SEARCH_ID
```

`in rm` は `SEARCH_ID` の検索入力を `queries` から取り除き、同じIDのPlace recordを `data/places.jsonld` から、判断記録を `data/osm-decisions.json` からも取り除きます。公開物は次のビルドで更新します。除去された施設を参照する外部のURIは無効になりますが、過去の公開版はGitHub Releaseの版固定スナップショットで引き続き取得できます。

## 実地調査の関連付けを反映する

```sh
./fac assoc . SEARCH_ID --osm-id node/123456789
./fac assoc . SEARCH_ID --choice none
./fac assoc . SEARCH_ID --hold --reason "実地調査で接続先を確定するまで保留"
```

`assoc` は実地調査で確定したOSM要素を人の判断として正本に反映します。OSM APIから要素の名称・座標・タグを取得し、確認Issueと同じ根拠として`data/osm-decisions.json`へ保存し、`data/places.jsonld`へ参照と座標を適用します。`--choice none`は「該当なし」を記録し、既存のOSM参照を解除します。

`--osm-id`は記録の前に、指定された要素が保持スナップショット`imports/openstreetmap/raw.json`に収録されているかを、`imports/openstreetmap/retrieval.json`とハッシュを照合して確認します。収録されていない場合は`WARNING`を表示し、指定要素を`previous`とする保留を自動の理由つきで記録します。参照と座標は適用しません。ミラー更新後に同じ`--osm-id`で再実行すると、保留が人の確定判断に置き換わります。

`imports/openstreetmap/raw.json`が無い、またはハッシュが一致しない場合は、照合しなかった`WARNING`を表示し、指定要素を人の確定判断として記録します。この取得物はgitignore対象のため、fresh clone直後はこの経路になります。

`--hold`は実地調査を待つ保留を記録します。`--reason`を必須とし、OSMとWikidataの参照を解除してUUID・座標・既存の`schema:subjectOf`を残し、カテゴリ判断を取り消します。保留中は月次更新の関連付け再評価、Jev、確認Issueの対象になりません。解除は`--osm-id`または`--choice none`で行います。公開物は次のビルドで更新します。

編集者は`--editor NAME`を指定するか、リポジトリのgit `user.name`から取ります。

入力が不正な場合、コマンドは `ERROR: <理由>` を出力し、終了コード 1 で停止します。

## 画像を指定する

```sh
./fac image set . SEARCH_ID "File:Chiyoda_Ward_Office.jpg"
./fac image set . SEARCH_ID "https://commons.wikimedia.org/wiki/File:Chiyoda_Ward_Office.jpg"
./fac image clear . SEARCH_ID
./fac image review .
```

`image set`は、正本`data/places.jsonld`のPlace recordへCommonsファイルページのIRI参照を一つ書きます。`File:`タイトルとCommonsファイルページURLを受け付け、空白・アンダースコアを正規化します。`Category:`、`Special:`、直接アップロードURLは受け付けません。

`image set`はCommons APIを呼びません。手動参照のファイルは月次のCommons取得の対象になり、次のビルドで公開recordの`schema:ImageObject`へ反映されます。指定直後はメタデータが未取得のため、公開物に画像は現れません。

`image clear`は手動参照を外し、Wikidata P18、OSMの`File:`タグ、OSMの`Category:`タグによる自動選択へ戻します。画像を付けない指定ではありません。

`image review`は読み取り専用で、手動参照ごとに、保存済みの`imports/commons/raw.json`と照合した結果を`resolved`または`unresolved`として出力します。`unresolved`は、ファイルのメタデータが未取得、またはライセンスが不完全であることを示します。ビルドは、手動参照のメタデータが得られないとき、自動候補へフォールバックせず、画像なしの公開recordを生成して警告を出します。

## カテゴリ判断を確認する

```sh
./fac category review .
```

`data/categories.json`の保存済み判断を`decided`、保存済み判断と規則の提案が食い違う施設を`divergent`、関連付けが変わった施設を`stale`、判断のない検索入力を`unresolved`として出力します。`unresolved`には、規則が一意に決めたコードを`proposal=コード`として添えます。関連付けを保留した施設は`held`として理由つきで出力し、`unresolved`には含めません。

## 人の判断でカテゴリを確定する

```sh
./fac category assign . SEARCH_ID POI_CODE --editor NAME
```

`assign`は、語彙`data/category-vocabulary.jsonld`にある4桁のPOIコードだけを受け付けます。判断は`method: human`として`data/categories.json`へ保存します。place recordは変更せず、公開recordへの`schema:keywords`の反映はビルドが行います。placeのない検索入力には記録できないため、先にOSMの関連付けを確定してください。

編集者は`--editor NAME`を指定するか、リポジトリのgit `user.name`から取ります。

## カテゴリ判断を取り消す

```sh
./fac category clear . SEARCH_ID
```

`clear`は判断を取り消し、施設を未分類へ戻します。place recordは変更せず、公開recordは次のビルドで未分類になります。

## 未決定のカテゴリを再評価する

```sh
./fac category refresh .
./fac category refresh . --present
```

`refresh`は規則`data/category-rules.json`で、OSM関連付けのある未決定施設と、関連付けが変わった施設だけを再評価します。関連付けのない検索入力は未分類のままです。環境変数`TYPESAFE_API_KEY`があれば、規則で決まらない施設をJevで判定します。`--present`は、カテゴリを確定できない施設をGitHubのカテゴリ確認Issueに提示し、`GITHUB_REPOSITORY`と`GH_TOKEN`が必要です。公開recordへの反映はビルドが行います。

## カテゴリの反映を検証する

```sh
./fac jsonld-validate data/places.jsonld
./fac category review .
```

`jsonld-validate`は、正本に`gif-poi`識別子が残っていないこと、公開recordの`schema:keywords`が語彙のtermを指すこと、カテゴリtermが名前と`gif-poi`識別子を持つことを検証します。`category review`は、確定した判断、未分類の施設、保留中の施設を一覧で示します。

## 保存済み判断を再提示する

```sh
python3 -m src.osm_maintenance present .
```

Gitへの保存後にIssue提示だけが失敗した場合に、保存済み判断の確認Issueを再提示します。実行には環境変数`GITHUB_REPOSITORY`と`GH_TOKEN`が必要です。取得、Jev判定、判断記録の書き換えは行いません。同じ内容で手動クローズしたIssueは再提示しません。
