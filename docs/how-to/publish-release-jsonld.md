# JSON-LD をリリースする

この手順は、検証済みの正本 JSON-LD を GitHub Release で配布する作業者向けです。

## 1. 正本を検証する

作業者は、リリース前に[検証](../reference/verification.md)を実行します。

## 2. GitHub Actions で試行する

作業者は Actions の `release-jsonld` を手動実行し、`tag` に版番号を入力します。

版番号は英数字で始めます。版番号は英数字、`.`、`_`、`-` だけを含めます。

手動実行は dry-run です。workflow は `release/places-<tag>.jsonld` を artifact `release-jsonld-<tag>` としてアップロードします。

作業者は artifact の存在と内容を確認します。

## 3. GitHub Release を公開する

作業者は、配布するタグを対象に GitHub Release を作成します。作業者は Release を published にします。

下書きの作成と既存タグだけでは workflow は起動しません。workflow は Release の公開時に起動します。

workflow は正本を検証し、版付き JSON-LD を作成します。workflow は作成物を artifact と Release 添付へ追加します。

## 4. 配布物を確認する

作業者は Release 添付の `places-<tag>.jsonld` を確認します。作業者は artifact と Release 添付が存在することを確認します。

workflow は入力不能、JSON 不正、JSON-LD 検証失敗、書込失敗で停止します。

## 5. 公開済み版へ戻す

作業者は公開済み Release を変更しません。作業者は `main` を force-push しません。

作業者は、戻したい版の直前に published だった Release のタグを `<previous-published-tag>` とします。タグの一覧だけでは Release が published だったことを確認できないため、作業者は GitHub の Release 一覧で確認します。

復元前に、タグが移行後の JSON-LD を含むことを確認します。次のコマンドが失敗した場合、そのタグから JSON-LD だけを復元できません。作業者は復元を開始せず、JSON-LD を含む直前の published Release を確認します。

```sh
git cat-file -e <previous-published-tag>:data/places.jsonld
git cat-file -e <previous-published-tag>:site/places.jsonld
```

作業者は `main` から新しい branch を作成します。作業者は確認済みタグの JSON-LD だけを branch へ復元します。

```sh
git switch main
git switch -c rollback/restore-<previous-published-tag>
git restore --source <previous-published-tag> -- data/places.jsonld site/places.jsonld
git diff -- data/places.jsonld site/places.jsonld
```

作業者は、差分に `data/places.jsonld` と `site/places.jsonld` 以外を含めません。作業者は[検証](../reference/verification.md)を完了します。作業者は差分と検証結果を記録した Pull Request を作成します。

作業者は Pull Request を review して merge します。作業者は merge commit に新しい未使用タグを作成します。

作業者は新しいタグの GitHub Release を published にします。作業者は workflow の artifact と新しい Release 添付を確認します。

作業者は既存タグを移動しません。作業者は既存の published Release を削除、編集、再公開しません。
