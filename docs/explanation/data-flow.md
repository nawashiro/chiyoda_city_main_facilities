# データフロー

このリポジトリは、施設データの由来と公開物を分離して保守します。

## 正本と公開

`data/places.jsonld` は唯一の正本です。`site/places.jsonld` は GitHub Pages 用の公開コピーです。

作業者は両ファイルをバイト単位で一致させます。GitHub Release は正本の版固定コピーを `places-<tag>.jsonld` として添付します。

公開経路は JSON-LD だけです。公開物と Release snapshot は GeoJSON、`registry.json`、manifest を含めません。

## 外部更新

WAM の取得物は `imports/wam/` に保存します。OpenStreetMap の取得物は `imports/openstreetmap/` に保存します。

作業者は GitHub Actions から外部更新を開始します。workflow は取得物を検証し、canonical JSON-LD を更新し、review 用 Pull Request を作成します。

人手 OSM レビューは候補の自動選択を補完します。レビュー結果はコミット済み YAML だけで受け付けます。

## 移行と rollback

この移行は breaking change です。利用者は旧 registry と GeoJSON の取得を停止します。

利用者は[データ契約](../reference/data-contracts.md)に従って JSON-LD を処理します。作業者は旧形式を互換出力として追加しません。

公開済み版へ戻す場合、作業者は[JSON-LD をリリースする](../how-to/publish-release-jsonld.md)の rollback 手順を実行します。作業者は `main` を force-push しません。
