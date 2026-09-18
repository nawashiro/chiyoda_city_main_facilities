# 最初のJSON-LDデータ変更

このチュートリアルでは、`data/places.jsonld`の1件のPlaceを`urn:uuid:`で確認し、標準語彙の値を1つ変更します。

`data/places.jsonld`はcanonical JSON-LD（正本）です。GitHub Pagesのcurrent JSON-LDとGitHub Releaseの版固定snapshotは、正本から作る派生公開コピーです。公開コピーを編集せず、正本だけを変更してください。

`JSON-LD-only`への移行はbreaking change（互換性を壊す変更）です。以前の公開形式や独自項目に依存する利用者は、JSON-LDへ移行してください。

## 1. 作業branchを作る

新しいcheckoutを作る場合は、次を実行してください。

```bash
git clone https://github.com/nawashiro/chiyoda_city_main_facilities.git
cd chiyoda_city_main_facilities
git switch -c data/first-jsonld-change
```

既存checkoutでは、作業開始時にbranchと作業ツリーを確認してください。

```bash
git switch -c data/first-jsonld-change
git status --short
```

未確認の変更がある場合、変更を保存してから作業してください。

## 2. `urn:uuid`でPlaceを確認する

この例では、最初のrecordの`@id`を使います。

```bash
UUID='urn:uuid:019fa880-5cd4-78e1-aa8b-c4ce83a065bc'
python3 - "$UUID" <<'PY'
import json
import sys
from pathlib import Path

document = json.loads(Path("data/places.jsonld").read_text(encoding="utf-8"))
record = next(item for item in document["@graph"] if item["@id"] == sys.argv[1])
print(json.dumps(record, ensure_ascii=False, indent=2))
PY
```

出力の`@id`が指定したURNと一致することを確認してください。
`schema:identifier`内の`schema:PropertyValue`が、外部recordの識別子を表します。

## 3. 標準JSON-LDの値を1つ編集する

```bash
$EDITOR data/places.jsonld
```

対象の`@id`を検索し、そのrecordだけを編集してください。
`schema:propertyID`が`openstreetmap`の`schema:PropertyValue`を確認してください。
レビューで確認済みの新しい識別子へ、その`schema:value`だけを置き換えてください。
`@id`、`@type`、`schema:propertyID`、geometryは変更しないでください。

変更前の値は、次の値です。

```json
"schema:value": "node/1420770185"
```

この例の変更前後は、次の形式です。

```diff
- "schema:value": "node/1420770185"
+ "schema:value": "node/1234567890"
```

`node/1234567890`は説明用の具体例です。実際の置換値は、出典レビュー（source review）で対象Placeとの一致を確認した識別子にしてください。

## 4. 変更後の検証を実行する

次のコマンドを順番に実行してください。

```bash
python3 -m src.fac_cli jsonld-validate data/places.jsonld
python3 -m src.facility_data validate .
python3 -m unittest discover -s tests -v
git diff --check
```

`jsonld-validate`は、直接編集したJSON-LDの構文と必須構造を確認します。
`facility_data validate`は、repository全体のデータ整合性を確認します。
`unittest`は、実装とworkflowの回帰を確認します。
失敗したコマンドの出力を読み、原因を直してから全コマンドを再実行してください。

## 5. 差分をレビューする

```bash
git diff --name-only
git diff -- data/places.jsonld
```

変更対象が`data/places.jsonld`だけであることを確認してください。
対象の`@id`が変わらず、標準JSON-LDの値を1つだけ変更したことを確認してください。
派生公開コピーを手編集していないことを確認してください。

## 6. commitを作る

レビューと検証が成功した場合だけ、commitを作成してください。

```bash
git add data/places.jsonld
git commit -m "data: canonical JSON-LDを更新"
git status --short
```

commit後の公開処理は、`data/places.jsonld`からPagesのcurrent JSON-LDとReleaseの版固定snapshotを作ります。
利用者へ互換性を告知し、JSON-LDを読める方法へ移行してから公開版を利用してください。
