# JSON-LD をリリースする

検証済みの公開対象JSON-LD を GitHub Release で配布する作業者向けの手順です。

## 1. 正本を検証する

リリース前に[検証](../reference/verification.md)を実行します。

## 2. GitHub Actions で作成する

Actions の `release-jsonld` を手動実行し、`tag` に版番号を入力します。版番号は英数字で始め、英数字、`.`、`_`、`-` だけを含めます。

手動実行は dry-run で、`release/places-<tag>.jsonld` を artifact `release-jsonld-<tag>` としてアップロードします。artifact の存在と内容を確認します。

## 3. GitHub Release を公開する

配布するタグを対象に GitHub Release を作成し、published にします。タグがまだ存在しない場合は、Release の作成時に作られます。下書きの作成や既存タグの存在だけでは workflow は起動せず、Release の公開時に起動します。

workflowは正本と検索入力を検証し、公開除外を反映したJSON-LDから版付きコピーを作成して、artifact と Release 添付に追加します。入力不能、JSON 不正、JSON-LD 検証失敗、書込失敗では停止します。Release 添付の `places-<tag>.jsonld` を確認します。

## 4. 公開済み版へ戻す

既存タグの移動と、既存 published Release の削除・編集・再公開をしません。`main` を force-push しません。

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

差分に `data/places.jsonld` 以外を含めず、[検証](../reference/verification.md)を完了します。差分と検証結果を記録した Pull Request を review して merge し、merge commit に新しい未使用タグを作成して GitHub Release を published にします。artifact と新しい Release 添付を確認します。
