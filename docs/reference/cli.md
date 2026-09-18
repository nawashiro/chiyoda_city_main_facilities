# JSON-LD検証コマンドリファレンス

この文書は、直接JSON-LD文書を読み取り専用で検証するコマンドを説明します。

## 直接JSON-LD文書を検証する

リポジトリのルートで次のコマンドを実行します。

```bash
python3 -m src.fac_cli jsonld-validate data/places.jsonld
```

`jsonld-validate`は、引数で指定したJSON-LD文書を直接読み取ります。
このコマンドは、JSONとJSON-LDの構造、識別子、型、位置情報、外部識別子の形式を検証します。
このコマンドは外部URLを取得せず、入力文書を再解釈して保存しません。

### 入出力

- 入力には、検証対象のJSON-LDファイルを1つ指定します。
- 検証に成功した場合、コマンドは標準出力へメッセージを出さずに終了します。
- 検証に失敗した場合、コマンドは標準エラー出力へエラー内容を出します。
- コマンドは、成功時と失敗時のどちらも入力ファイルを書き換えません。
- コマンドは、検証前後の入力ファイルのバイト列を保持します。

### 終了コード

| 終了コード | 意味 |
|---:|---|
| `0` | 指定したJSON-LD文書の検証に成功しました。 |
| `1` | ファイルの読み込みまたはJSON-LD文書の検証に失敗しました。 |

## リポジトリ全体を確認する

JSON-LD文書の直接検証に加えて、変更後に次の確認を実行します。

```bash
python3 -m unittest discover -s tests -v
python3 -m src.facility_data validate .
git diff --check
```

テストは、実装と文書の契約を確認します。
`validate`は、リポジトリ内のデータと入力文書の整合性を確認します。
`git diff --check`は、差分の空白エラーを確認します。

## 関連資料

- [データモデル](../explanation/data-model.md): JSON-LD文書の位置付けを説明します。
- [属性リファレンス](attributes.md): JSON-LD属性の意味と値を説明します。
- [CLI実装](../../src/fac_cli.py): コマンドの引数と終了処理を定義します。
- [JSON-LD検証実装](../../src/facility_data.py): 文書の検証規則を定義します。
- [CLIテスト](../../tests/test_fac_cli.py): 成功、失敗、バイト保持を検証します。
- [データ文書テスト](../../tests/test_jsonld_repository.py): 収録文書の検証を実行します。
