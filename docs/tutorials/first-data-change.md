# 最初のデータ変更

この手順は、施設データを初めて変更する作業者向けです。作業者は Python 3.13 と Git を使います。

## 1. 作業ツリーを確認する

```sh
python3 --version
git status --short
```

作業者は Python 3.13 を使います。他者の変更がある場合、作業者は変更範囲を分けます。

## 2. データ契約を確認する

作業者は、編集前に[データ契約](../reference/data-contracts.md)を確認します。

作業者は、出典や再利用条件を変える場合、[出典とライセンス](../reference/licenses.md)を確認します。

## 3. 正本を変更する

作業者は `data/places.jsonld` を正本として編集します。

作業者は、公開対象でない施設を公開データへ追加しません。

`python3 -m src.facility_data build .` は、既存の `data/places.jsonld` を上書きしません。このコマンドは正本を検証します。

## 4. 公開コピーを同期する

作業者は、正本を確認してから公開コピーへ複製します。

```sh
cp data/places.jsonld site/places.jsonld
cmp data/places.jsonld site/places.jsonld
```

## 5. 変更を検証する

作業者は、[検証](../reference/verification.md)の全手順を実行します。

## 6. 差分を確認する

```sh
git diff --check
git diff -- data/places.jsonld site/places.jsonld
```

作業者は、意図したデータと生成物だけが変わったことを確認します。作業者は、検証結果と差分を Pull Request に記録します。
