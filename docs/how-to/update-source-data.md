# 外部sourceを更新してJSON-LDを公開する

このhow-toは、WAMまたはOpenStreetMap（OSM）の外部sourceを更新し、公開JSON-LDのPull Request（PR）を作る手順です。保持済みsnapshotの再同定と、確認済み事実の直接訂正も扱います。公開データの正本は[`data/places.jsonld`](../../data/places.jsonld)です。

## 範囲と前提

リポジトリのルートで、一人が一つのrouteだけを実行します。次の条件を一つでも満たさない場合は、作業を開始せずに停止します。

1. `git status --short --untracked-files=all`が空で、作業ツリーがcleanです。
2. 対象branchへpushし、GitHub Actionsを実行し、PRを作る権限があります。
3. `python3 --version`がPython 3.13です。
4. WAM、OSM、reidentify、factual correctionから一つだけ選びます。
5. OSMでは、管理者が設定した`LLM_API_KEY` secretと`LLM_MODEL` variableを使えます。

```bash
git rev-parse --show-toplevel
git status --short --untracked-files=all
python3 --version
```

secret、token、Authorization header、個人情報をログ、artifact、YAML、PR本文へ書きません。secretの値が不明または未設定なら、値を推測せずに管理者へ連絡します。

## 一本道の手順

### 1. routeを一つ選ぶ

| route | 選ぶ条件 | 次に使うもの | 許可された変更 |
|---|---|---|---|
| WAM | 新しいWAM公開版を取得する | [Update WAM data workflow](../../.github/workflows/update-wam.yml) | source snapshotと対応するreport・input artifact |
| OSM | 新しいOSM snapshotを取得する | [Update OpenStreetMap data workflow](../../.github/workflows/update-osm.yml) | source snapshotと対応するreport・input artifact。人手reviewは`reports/osm-review-needed.yaml`をcommitし、review PRで確認 |
| reidentify | 検索入力だけを変更し、外部dataを再取得しない | [Re-identify retained source snapshots workflow](../../.github/workflows/reidentify-sources.yml) | 検索入力とreport。raw bytesと`retrieval.json`は変更しない |
| factual correction | 出典を確認した公開事実だけを訂正する | [Placeを直接保守する](maintain-a-place.md) | 通常のdata PRでcanonical JSON-LD（`data/places.jsonld`）だけを変更 |

詳細な確認は[更新チェックリスト](source-update-checklist.md)を使います。

新しい外部dataが必要なら、reidentifyを選びません。検索入力を変更した場合は、変更をcommitしてからreidentifyを実行します。一つのPRで複数routeを混ぜません。

### 2. routeを実行する

- **WAM**: Actionsでworkflowを開き、`Run workflow`を選び、`release`へ対象公開版を`YYYYMM`で入力します。
- **OSM**: Actionsからworkflowを実行します。secretの値を入力欄やログへ貼りません。
- **reidentify**: 検索入力をcommitしたbranchでworkflowを実行します。workflowは外部sourceを再取得しません。
- **factual correction**: workflowを実行せず、[Placeを直接保守する](maintain-a-place.md)に従って`data/places.jsonld`だけを編集します。

### 3. 対象run、artifact、commitを照合する

Actionsの対象workflowから対象runを開き、branch、結論、run URL、`Summary`の`Artifacts`欄を確認します。run IDはrun URLの`/actions/runs/`の後ろの数値です。artifact名は`Summary`に表示された名前をそのまま使います。

artifact名の規則は次のとおりです。別runの名前を使わず、表示名と一致させます。

- WAM: `wam-update-` + 入力した`release`
- OSM: `osm-update-` + run ID
- reidentify: `reidentify-update-` + run ID

WAM、OSM、reidentifyでは、確認した実値を次の変数へ設定してからartifactを取得します。

```bash
export RUN_ID='Actionsで確認した対象runの数値'
export ARTIFACT_NAME='対象runのSummaryで確認したartifact名'
rm -rf /tmp/chiyoda-source-update
mkdir -p /tmp/chiyoda-source-update
gh run download "$RUN_ID" --name "$ARTIFACT_NAME" --dir /tmp/chiyoda-source-update
cp -a /tmp/chiyoda-source-update/. .
git status --short --untracked-files=all
git diff -- imports inputs reports data/places.jsonld
git diff --stat
```

artifact取得後に予期しないファイルが表示されたら、artifactを破棄して停止します。

workflowが作ったdata PR、review PR、YAML commitも、同じrunとartifactに対応するものだけを確認します。Issue番号や識別子を推測しません。factual correctionではartifactを取得せず、対象commitの`data/places.jsonld`差分を確認します。

### 4. 許可されたreview経路だけを適用する

raw bytes、`retrieval.json`、`rawSha256`、`rawVersion`を手で変更しません。raw bytesを更新する場合は、対応するworkflowを再実行します。reidentifyではraw bytesと`retrieval.json`を実行前後で同一に保ちます。

- **WAM**: 同じartifactのraw、metadata、normalized結果、report、canonical JSON-LDを一組として確認し、意図した生成差分だけをcommitします。
- **OSMで未解決候補がない場合**: workflowが作ったdata PRだけを確認します。候補を手で追加しません。
- **OSMで未解決候補がある場合**: workflowが作ったreview PRで`reports/osm-review-needed.yaml`だけを編集します。各検索IDで候補または候補なしを一つだけ`true`にします。`reportSha256`、検索ID、候補ID、施設名、他の値を変更せずにYAMLをcommitします。review PRを確認してから対応するIssueの適用チェックを入れます。[Apply OSM human review workflow](../../.github/workflows/apply-osm-review.yml)が元artifactを照合してdata PRを作ります。
- **reidentifyでOSM候補が未解決の場合**: OSMと同じYAML commitとreview PRの経路を使います。推測で適用しません。
- **factual correction**: [Placeを直接保守する](maintain-a-place.md)に従い、確認済みの事実だけを`data/places.jsonld`へ変更します。既存の`urn:uuid:`とgeometryを保持し、source snapshotを変更しません。

未解決の外部識別子を推測、生成、別候補への置換で解決しません。OSMの人手判断は、commit済みYAMLとreview PRに残します。Issue本文の候補を直接編集して公開dataへ反映しません。

### 5. 検証する

PRを作る前に、リポジトリのルートで次のコマンドを順番に実行します。

```bash
python3 -m src.fac_cli jsonld-validate data/places.jsonld
python3 -m src.facility_data validate .
python3 -m unittest discover -s tests -v
git diff --check
git diff --stat
```

canonical JSON-LDのbyte再現性を確認します。

```bash
cp data/places.jsonld /tmp/places.jsonld
python3 -m src.facility_data build .
python3 -m src.fac_cli jsonld-validate data/places.jsonld
cmp /tmp/places.jsonld data/places.jsonld
```

`cmp`が失敗した場合は、意図しない再生成を確認します。field、hash、source条件の詳細は[更新チェックリスト](source-update-checklist.md)、コマンドの詳細は[CLIリファレンス](../reference/cli.md)と[属性リファレンス](../reference/attributes.md)を参照します。[Validate data workflow](../../.github/workflows/validate.yml)も対象commitで成功させます。

### 6. commitしてPRを作る

PRを作る前に、次のコマンドを再実行します。

```bash
git status --short --untracked-files=all
```

選んだrouteで予期しないファイルが表示されたら、commitせずに停止します。

`git diff --name-only`で差分が選んだrouteの許可対象だけであることを確認します。PR本文へ、route、source releaseまたは検索入力、対象Actions run URL、正確なartifact名、review PRまたはIssueのリンク、検証結果を記録します。secret、token、個人情報、推測したIssue番号を記録しません。

OSM人手reviewでは、YAMLをcommitしたreview PRと、workflowが作ったdata PRの両方を確認します。すべての検証とPR checksが成功した後だけ、保守者がmergeします。

## 停止条件と公開先

次のいずれかに該当したら、結果を破棄して停止します。

- 作業ツリーがcleanでない、権限がない、またはrouteを一つに決められない。
- 対象runが失敗、未完了、branch違い、またはartifact名が一致しない。
- artifact、review PR、YAML、data PRの対応関係を確認できない。
- raw bytes、`retrieval.json`、hash、versionに意図しない差分がある。
- 未解決識別子を出典なしで確定する必要がある。
- secretがログ、artifact、YAML、PR本文へ出た。
- `jsonld-validate`、`validate`、unit test、byte比較、`git diff --check`、PR checksのいずれかが失敗した。

merge後のcurrent配布物は[GitHub PagesのDatasetページ](https://nawashiro.github.io/chiyoda_city_main_facilities/)と[current JSON-LD](https://nawashiro.github.io/chiyoda_city_main_facilities/places.jsonld)で確認します。

```bash
curl -fL 'https://nawashiro.github.io/chiyoda_city_main_facilities/places.jsonld' \
  -o /tmp/places.jsonld
python3 -m src.fac_cli jsonld-validate /tmp/places.jsonld
```

版固定の配布物は[GitHub Releases](https://github.com/nawashiro/chiyoda_city_main_facilities/releases)からtagを選びます。[release-jsonld.yml](../../.github/workflows/release-jsonld.yml)の詳細と、次の取得コマンドを参照します。

```bash
TAG='GitHub Releasesで選んだ対象tag'
gh release download "$TAG" \
  --repo nawashiro/chiyoda_city_main_facilities \
  --pattern "places-${TAG}.jsonld"
python3 -m src.fac_cli jsonld-validate "places-${TAG}.jsonld"
```
