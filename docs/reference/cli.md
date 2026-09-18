# JSON-LD検証コマンドリファレンス

この文書は、1つのJSON-LD文書を安全に検証する主導線と、追加の提出確認を説明します。

## 主導線: 1つのJSON-LD文書を検証する

リポジトリのルートで次のコマンドを実行します。

```bash
python3 -m src.fac_cli jsonld-validate data/places.jsonld
```

`data/places.jsonld`は例です。検証対象のJSON-LDファイル1つのパスに置き換えます。
このコマンドは読み取り専用で動作し、URLを取得せず、入力ファイルを変更しません。
検証に成功すると標準出力と標準エラー出力に何も出さず、終了コード`0`で終了します。
検証に失敗すると標準エラー出力へエラーを出し、終了コード`1`で終了します。

## 追加の提出確認

次の確認は、主導線の単一ファイルCLIコマンドとは別に実行します。

```bash
python3 -m src.facility_data validate .
python3 -m unittest discover -s tests -v
git diff --check
```

- `python3 -m src.facility_data validate .`は、リポジトリ全体のデータを検証します。
- `python3 -m unittest discover -s tests -v`は、全テストを実行します。
- `git diff --check`は、差分の空白エラーを確認します。

各確認は、成功時に終了コード`0`を返します。失敗時は非`0`の終了コードを返します。

## 関連資料

- [データモデル](../explanation/data-model.md): JSON-LD文書の位置付けを説明します。
- [属性リファレンス](attributes.md): JSON-LD属性の意味と値を説明します。
