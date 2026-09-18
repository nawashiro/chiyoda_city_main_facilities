# 最初のJSON-LDデータ変更

このチュートリアルの範囲は、`data/places.jsonld`の既存のPlaceを1件だけ変更し、検証してPull Requestを準備することです。`site/places.jsonld`は編集しません。

## 1. 作業ツリーを確認してbranchを作る

リポジトリのルートで、branchを作る前に状態を確認します。

```bash
git status --short
```

出力が空でない場合は、ここで停止します。既存の変更を混ぜず、作業内容を分離してから再開します。

出力が空の場合だけ、安全な作業branchを作ります。

```bash
git switch -c data/first-jsonld-change
```

branchが既にある場合は、別の作業名を選びます。`main`へ直接変更を加えません。

## 2. 既存のPlaceと人間向け情報を確認する

`data/places.jsonld`の`@graph`から、実在する対象を1件に絞ります。
ここでいうレビュー済みソースとは、担当メンテナーまたはレビュー手順が確認したsource recordまたはvalueです。
正本のPlaceには人間向け名称がないため、レビュー済みソースで施設名、住所などを確認します。
外部識別子または座標を照合し、確認済みの施設情報と正本の`@id`を対応付けます。
`@id`と施設名、住所などの人間向け情報を編集前に記録します。

レビュー済みソースで施設名、住所などを確認し、その情報に対応する実在する`@id`を控えます。
正本に対応する人間向け情報がない場合、またはソースや確認を得られない場合は停止し、識別子を入力しません。
控えた`@id`を入力し、正本に1件だけ一致することを確認します。

```bash
printf '確認済みの @id: '
read -r PLACE_ID
python3 - "$PLACE_ID" <<'PY'
import json
import sys
from pathlib import Path

document = json.loads(Path("data/places.jsonld").read_text(encoding="utf-8"))
matches = [
    record for record in document["@graph"] if record.get("@id") == sys.argv[1]
]
if not matches:
    raise SystemExit("停止: 正本に一致するPlaceがありません")
if len(matches) > 1:
    raise SystemExit("停止: 正本に一致するPlaceが複数あります")
print(f"確認した @id: {matches[0]['@id']}")
print(json.dumps(matches[0], ensure_ascii=False, indent=2))
PY
```

出力したrecordの外部識別子とgeometryが、施設名、住所などに一致しない場合は停止します。
人間向け情報と`@id`を一意に対応付けられない場合も停止します。

## 3. Placeを1件だけ編集する

`vi`で正本を開き、確認した`@id`を検索します。`$EDITOR`を設定済みなら`$EDITOR data/places.jsonld`を使えます。`nano`が利用できる場合は、簡単な編集方法として`nano data/places.jsonld`も使えます。

```bash
vi data/places.jsonld
```

対象recordの`schema:identifier`にある`schema:value`を1つだけ、レビュー済みソースの実値へ変更します。
外部識別子の実値を確認できない場合は、値を変更せず停止します。
`@id`、`@type`、`schema:propertyID`、geometry、他のrecordは変更しません。

## 4. 変更を順番に検証する

次のコマンドを、この順番で実行します。

```bash
python3 -m src.fac_cli jsonld-validate data/places.jsonld
python3 -m src.facility_data validate .
python3 -m unittest discover -s tests -v
git diff --check
```

最初のコマンドは、直接編集したJSON-LDの構造と必須値を検証します。
2番目のコマンドは、repository全体のデータ整合性を検証します。
3番目のコマンドは、実装とworkflowの回帰を検証します。
最後のコマンドは、差分の空白エラーを検証します。
各コマンドが終了コード`0`を返すことを成功条件にします。
1つでも失敗した場合は、commitやPull Requestへ進まず、原因を直して最初から再実行します。

## 5. 差分を確認してPull Requestを準備する

検証後に、変更対象と差分を確認します。

```bash
git diff --name-only
git diff -- data/places.jsonld
```

変更対象が`data/places.jsonld`だけであることを確認します。
`site/places.jsonld`や別のファイルが差分に出た場合は停止します。
対象の`@id`が変わらず、1件のrecordの1つの値だけが変わったことを確認します。

差分と検証結果をレビューできる場合だけ、commitとPull Requestへ進みます。

```bash
git add data/places.jsonld
git commit -m "data: canonical JSON-LDを更新"
git push -u origin HEAD
```

push後にGitHubでPull Requestを作成します。レビュー前にmergeしません。

次の条件では、commitやPull Requestを作成せず停止します。

- 開始時の`git status --short`が空でない。
- 人間向けの施設情報、またはレビュー済みソースを確認できない。
- `@id`に一致するPlaceが0件または複数件ある。
- 検証コマンドのいずれかが終了コード`0`を返さない。
- `data/places.jsonld`以外のファイルを変更した。
- `@id`、geometry、または未レビューの外部識別子を変更した。
