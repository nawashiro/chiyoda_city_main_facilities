# 検証

Python 3.13を使い、リポジトリのルートで実行します。

```sh
python3 -m unittest discover -s tests -v
python3 -m src.facility_data validate .
./fac jsonld-validate data/places.jsonld
python3 -m src.facility_data build .
./fac jsonld-validate site/places.jsonld
git diff --check
```

`validate`は正本と検索入力、`build`は公開除外を反映した配布物を検証します。buildが正本を変えないことも確認してください。

```sh
cp data/places.jsonld /tmp/places.jsonld.before
python3 -m src.facility_data build .
cmp /tmp/places.jsonld.before data/places.jsonld
```

OSMの統合テストは、確定分と判断待ちの共存、参照の解除、Issue回答、API失敗時の不変性を固定データで確認します。取得済みデータから切り出した名称・座標一致の移行事例も含みます。APIの固定応答テストは、実際のモデル精度の評価とは分けます。

## Jevの実測評価

TypeSafeのキーを環境変数`TYPESAFE_API_KEY`へ安全に設定し、次を実行します。

```sh
python3 scripts/evaluate_jev.py --output reports/jev-evaluation.json
```

`tests/fixtures/jev-evaluation.json`は、日本語の実データと、同名施設・同一建物の別施設・既知の誤一致型・正解候補なしを表す合成事例を区別します。期待する候補と結果、信頼度、使用量、単価に基づく費用を出力します。通常のテストは外部APIを呼びません。

自動確定は`confidence >= 0.90`です。実測で期待と異なる選択を自動確定した場合、評価コマンドは失敗します。閾値を変更する場合は、評価結果を根拠に設定と境界テストを更新してください。実費は[更新手順](../how-to/update-osm.md#jevの使用量と費用)に従って確認します。

## 取得済みデータでの試行

作業用コピーで`python3 -m src.osm_maintenance refresh . --offline`を使うと、保存したrawとSHA-256を検証して照合できます。取得とGitHub操作は行わず、Jev接続は行います。実行すると作業用コピーの正本と判断記録を更新します。

workflowでは`refresh .`、Issue回答では`confirm .`、公開後は`close-published .`を使います。GitHub操作には環境変数`GITHUB_REPOSITORY`と`GH_TOKEN`が必要です。
