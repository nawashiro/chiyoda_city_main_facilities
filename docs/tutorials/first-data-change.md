# 最初のデータ変更

この手順は、施設データを初めて変更する作業者向けです。作業者はリポジトリ root で、正本の編集、`./fac build`、`./fac verify`、意図した差分の確認を順に実行します。

## 1. 環境と作業ツリーを確認する

```sh
python3 --version
git status --short
```

作業者は Python 3.13 を使います。他者の未コミット変更がある場合、作業者は変更範囲を分けます。

## 2. データ契約を確認する

作業者は、編集前に[データ契約](../reference/data-contracts.md)を確認します。

作業者は、出典や再利用条件を変える場合、[出典とライセンス](../reference/licenses.md)を確認します。

## 3. 正本を変更する

作業者は `data/places.jsonld` だけを正本として編集します。公開対象でない施設を公開データへ追加しません。

## 4. 公開コピーを更新する

正本の編集後、リポジトリ root で [`./fac build`](../reference/cli.md)を実行します。

```sh
./fac build
```

`build` は canonical JSON-LD を検証し、成功した場合だけ `site/places.jsonld` を正本とバイト単位で一致する公開コピーとして更新します。公開コピーを手動で編集または同期しません。

## 5. 変更を検証する

`build` の後、同じリポジトリ root で [`./fac verify`](../reference/cli.md)を実行します。

```sh
./fac verify
```

`verify` は全 test suite、repository / JSON-LD validation、公開コピーの byte-level 整合性、`git diff --check` を実行します。`verify` は `build` を実行せず、追跡対象ファイルを変更しません。失敗した場合は結果を確認して修正し、成功するまで先へ進みません。

## 6. 意図した差分を確認する

```sh
git diff -- data/places.jsonld site/places.jsonld
```

作業者は、正本と公開コピーの差分が意図した変更だけであることを確認します。`verify` が確認する byte-level 整合性と、目視した差分の両方を確認します。

## 7. Pull Request に記録する

作業者は Pull Request に次の確認結果を記録します。

- `./fac build` が成功した
- `./fac verify` が成功した
- `data/places.jsonld` と `site/places.jsonld` の意図した差分を確認した
