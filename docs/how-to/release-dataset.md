# データセットをリリースする

検証済みの公開配布物を GitHub Release で版固定する手順です。

## 1. Actions でリリースする

GitHub Actions の `release` workflow を `main` ブランチに対して起動します。起動すると workflow が自動で行うのは次のとおりです。

1. checkout したコミットが `main` の最新であることを確認し、テストとビルドを実行します。
2. 実行日の UTC 日付 `YYYY.MM.DD` をタグにします。タグが既に存在するときは失敗して終わります。タグの移動と上書きはしません。
3. Release を公開し、`places-<タグ>.jsonld`、`osm-<タグ>.json`、`wikidata-<タグ>.json` を添付します。リリースノートは workflow が生成します。

テストまたはビルドが失敗したときは、Release とタグを作成せずに終わります。原因を取り除いてから起動し直します。

## 2. 公開物を確認する

Release の資産とリリースノートを確認します。資産は JSON-LD と OSM ミラー、Wikidata ミラーの 3 点で、landing page は含みません。資産の内容は、そのコミットで Pages に公開した配布物と同じです。

## 3. 公開済み版へ戻す

既存 published Release の削除・編集・再公開をしません。タグを移動しません。`main` を force-push しません。

戻したい版の直前に published だった Release のタグを `<previous-published-tag>` とします。タグの一覧からは Release が published だったかを確認できないため、GitHub の Release 一覧で確認します。タグに `data/places.jsonld` が含まれることを、次のコマンドで確認します。

```sh
git cat-file -e <previous-published-tag>:data/places.jsonld
```

このコマンドが失敗した場合、そのタグから JSON-LD だけを復元できません。`data/places.jsonld` を含む、より前の published Release を探してください。

`main` から新しい branch を作り、そのタグから `data/places.jsonld` だけを復元します。

```sh
git switch main
git switch -c rollback/restore-<previous-published-tag>
git restore --source <previous-published-tag> -- data/places.jsonld
git diff -- data/places.jsonld
```

差分に `data/places.jsonld` 以外を含めず、Pull Request の `Validate data` workflow が通ることを確認します。差分と検証結果を記録した Pull Request を review して merge し、`release` workflow を起動します。Release の資産とリリースノートを確認します。
