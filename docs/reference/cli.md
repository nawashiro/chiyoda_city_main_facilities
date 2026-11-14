# CLI

作業者はリポジトリ root で `./fac` を実行します。

## 検証

```sh
./fac jsonld-validate data/places.jsonld
```

成功時、コマンドは出力しません。

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

`in rm` は `SEARCH_ID` の検索入力を `queries` から取り除き、同じIDのPlace recordを `data/places.jsonld` と `site/places.jsonld` から、判断記録を `data/osm-decisions.json` からも取り除きます。除去された施設を参照する外部のURIは無効になりますが、過去の公開版はGitHub Releaseの版固定スナップショットで引き続き取得できます。

## 実地調査の関連付けを反映する

```sh
./fac assoc . SEARCH_ID --osm-id node/123456789
./fac assoc . SEARCH_ID --choice none
```

`assoc` は実地調査で確定したOSM要素を人の判断として正本に反映します。OSM APIから要素の名称・座標・タグを取得し、確認Issueと同じ根拠として`data/osm-decisions.json`へ保存し、`data/places.jsonld`へ参照と座標を適用します。`--choice none`は「該当なし」を記録し、既存のOSM参照を解除します。

編集者は`--editor NAME`を指定するか、リポジトリのgit `user.name`から取ります。

入力が不正な場合、コマンドは `ERROR: <理由>` を出力し、終了コード 1 で停止します。

## 保存済み判断を再提示する

```sh
python3 -m src.osm_maintenance present .
```

Gitへの保存後にIssue提示だけが失敗した場合に、保存済み判断の確認Issueを再提示します。実行には環境変数`GITHUB_REPOSITORY`と`GH_TOKEN`が必要です。取得、Jev判定、判断記録の書き換えは行いません。同じ内容で手動クローズしたIssueは再提示しません。
