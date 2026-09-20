# 公開済み JSON-LD を復元する

この手順は、既存の published Release を変更せず、過去の JSON-LD を新しい commit と Release として復元する作業者向けです。通常の公開は、[JSON-LD をリリースする](publish-release-jsonld.md)を参照します。

## 1. 復元元の published Release を確認する

作業者は、公開済み Release を変更しません。作業者は `main` を force-push しません。

作業者は、戻したい版の直前に published だった Release のタグを `<previous-published-tag>` とします。タグの一覧だけでは Release が published だったことを確認できないため、作業者は GitHub の Release 一覧で確認します。

作業者は、復元前にタグが移行後の JSON-LD を含むことを確認します。次のコマンドが失敗した場合、そのタグから JSON-LD だけを復元できません。作業者は復元を開始せず、JSON-LD を含む直前の published Release を確認します。

```sh
git cat-file -e <previous-published-tag>:data/places.jsonld
git cat-file -e <previous-published-tag>:site/places.jsonld
```

## 2. 新しい branch で JSON-LD を復元する

作業者は、`main` から新しい branch を作成します。作業者は、確認済みタグの JSON-LD だけを branch へ復元します。

```sh
git switch main
git switch -c rollback/restore-<previous-published-tag>
git restore --source <previous-published-tag> -- data/places.jsonld site/places.jsonld
git diff -- data/places.jsonld site/places.jsonld
```

作業者は、差分に `data/places.jsonld` と `site/places.jsonld` 以外を含めません。

作業者は[検証](../reference/verification.md)を完了します。

作業者は、差分と検証結果を記録した Pull Request を作成します。

## 3. 新しい tag と Release を公開する

作業者は、Pull Request を review して merge します。

作業者は、merge commit に新しい未使用タグを作成します。

作業者は、新しいタグの GitHub Release を published にします。

作業者は、workflow が成功し、新しい Release に `places-<tag>.jsonld` が公開 asset として存在することを確認します。

作業者は、既存タグを移動しません。作業者は、既存の published Release を削除、編集、再公開しません。
