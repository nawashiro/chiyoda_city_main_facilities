# 検証

変更を確認するときは、リポジトリ root で次のコマンドを実行します。

## 標準コマンド

```sh
./fac verify
```

`./fac verify` は、テスト、リポジトリと JSON-LD の検証、正本と公開コピーの byte-level 比較、`git diff --check` をまとめて実行します。成功時は終了コード 0、失敗時は非 0 です。`build` や公開コピーの同期は行いません。

## 失敗時の診断

出力に示された失敗を修正してから、`./fac verify` を再実行します。

- JSON-LD の入力を個別に確認する場合:

  ```sh
  ./fac jsonld-validate data/places.jsonld
  ```

- 公開コピーが正本と一致しない場合、正本の変更が意図したものか確認します。意図した変更であれば、次の順に実行します。

  ```sh
  ./fac build
  ./fac verify
  ```

- 差分の空白エラーを確認する場合:

  ```sh
  git diff --check
  ```
