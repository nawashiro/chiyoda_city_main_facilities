# ソース更新とJSON-LD公開を保守する

このhow-toは、外部ソースの取得、保持済みスナップショットの再同定、公開JSON-LDの変更を安全に進める手順です。更新前後の確認には、[更新チェックリスト](source-update-checklist.md)を使います。

## 更新の原則

`data/places.jsonld`は公開データの唯一のcanonical JSON-LDです。ソース更新workflowは取得スナップショットと同定結果を更新します。ソース更新workflowは、公開事実を推測してcanonical JSON-LDへ直接書き込みません。

次のファイルを同じ更新結果として扱います。

- `imports/wam/raw.json`または`imports/openstreetmap/raw.json`: 取得したraw bytes
- `imports/wam/retrieval.json`または`imports/openstreetmap/retrieval.json`: 取得日時と取得版
- `imports/*/normalized.json`: 検証済みの正規化結果
- `reports/`: 同定候補と更新結果

新規取得では、rawと`retrieval.json`を同じartifactから取り込みます。`rawSha256`、`rawVersion`、`retrievedAt`を手で書き換えません。raw bytesを変更した場合は、同じ取得を再実行してhash metadataを作り直します。

再同定では、保持済みraw bytesと`retrieval.json`を変更しません。workflowが`rawSha256`と`rawVersion`を検証してから、現在の検索入力に対する正規化結果だけを再計算します。

## GitHub Actionsで更新する

GitHubの`Actions`タブで、対象branchからworkflowを実行します。各workflowは更新後にcanonical JSON-LDを検証し、unit testを実行します。artifactを取り込む前に、候補、件数、UUID、raw metadataの差分を確認します。

### WAMの新しい公開版を取得する

[update-wam.yml](../../.github/workflows/update-wam.yml)は、指定したWAM公開版を取得します。

1. `release`へ`YYYYMM`形式の公開版を入力します。
2. workflowが公式archiveを取得し、raw、取得metadata、正規化結果を同じartifactへ保存します。
3. workflowが`python3 -m src.facility_data validate .`、unit test、canonical JSON-LDのbyte比較を実行します。
4. artifact名`wam-update-<YYYYMM>`を取得します。
5. 差分を確認して、保守branchへcommitし、Pull Requestを作成します。

WAM artifactの保存期間は14日です。workflowは自動でPull Requestを作成しません。保存期間内にartifactを確認し、必要な差分だけをcommitします。

### OpenStreetMapを取得する

[update-osm.yml](../../.github/workflows/update-osm.yml)は、保持対象IDと検索入力を使ってOpenStreetMapスナップショットを取得します。

1. repository secretへ`LLM_API_KEY`を設定します。
2. repository variableへ`LLM_MODEL`を設定します。
3. OpenAI互換endpointを使う場合だけ`LLM_BASE_URL`を設定します。
4. workflowを実行し、raw、`retrieval.json`、hash metadata、候補reportを確認します。
5. 未解決候補がなければ、workflowが更新用Pull Requestを作成します。
6. 未解決候補があれば、次の人手確認手順を完了します。

OSM artifactの保存期間は30日です。候補reportの`reportSha256`は、確認したartifactとの対応を示します。hashが一致しないartifactやreportを適用しません。

### OSM候補を人手で確認する

未解決候補の人手判断は、コミット済みYAMLとPull Requestに残します。Issue本文の候補を直接編集して、公開データへ反映しません。

1. workflowが作成したレビュー用Pull Requestを開きます。
2. `reports/osm-review-needed.yaml`を編集します。
3. 各検索IDで採用候補を一つだけ`true`にします。
4. 候補がない検索IDでは、候補なしを一つだけ`true`にします。
5. `reportSha256`、検索ID、候補ID、施設名を変更せずにYAMLをcommitします。
6. YAMLをcommitしたレビュー用Pull Requestを確認します。
7. 対応するIssueで適用チェックを入れます。

[apply-osm-review.yml](../../.github/workflows/apply-osm-review.yml)は、commit済みYAMLと元のartifactを照合します。照合に成功すると、workflowが選択結果を適用したデータPull Requestを作成します。保守者はそのPull Requestで、raw、取得metadata、hash metadata、canonical JSON-LD、test結果を確認してmergeします。

### 保持済みスナップショットを再同定する

検索入力をcommitした後、[reidentify-sources.yml](../../.github/workflows/reidentify-sources.yml)を同じbranchで実行します。このworkflowは外部ソースを再取得しません。

1. workflowがWAMとOpenStreetMapのraw bytesを`retrieval.json`と照合します。
2. workflowが`rawSha256`と`rawVersion`を検証します。
3. workflowが変更された検索入力だけを再同定します。
4. workflowが保持済みraw、取得日時、取得版、hash metadataを保持します。
5. OSMの未解決候補があれば、コミット済み`reports/osm-review-needed.yaml`とPull Requestで確認します。
6. artifactとPull Requestの差分を確認してmergeします。

再同定artifactの保存期間は30日です。新しい外部データが必要な場合は、再同定ではなく`update-wam.yml`または`update-osm.yml`を実行します。

## artifactを安全に取り込む

Actions runから、workflowが生成したartifactをそのまま取得します。

```bash
gh run download <RUN_ID> --name <ARTIFACT_NAME> --dir /tmp/chiyoda-source-update
cp -a /tmp/chiyoda-source-update/. .
git diff -- imports inputs reports data/places.jsonld
```

新規取得では、raw、`retrieval.json`、正規化結果、reportを一組で取り込みます。再同定では、rawと`retrieval.json`の差分を許可しません。hash不一致、取得版不一致、意図しないUUID変更、意図しないPlace削除を検出したら、commitせずにworkflow結果を破棄します。

## 公開事実を変更する

公開事実を変更するときだけ、[data/places.jsonld](../../data/places.jsonld)を直接編集します。ソース更新workflowで公開事実の変更を代用しません。既存Placeの`@id`を保持し、`@context`、`@graph`、型、geometry、外部識別子の構造を壊しません。

直接編集では、raw、`retrieval.json`、normalized結果、候補reportを変更しません。公開recordへ運用履歴、投票記録、取得metadataを追加しません。公開事実の変更理由は、commit messageとPull Request本文へ記録します。

変更後は、次の順番で検証します。

```bash
python3 -m src.fac_cli jsonld-validate data/places.jsonld
python3 -m src.facility_data validate .
python3 -m unittest discover -s tests -v
git diff --check
git diff --stat
```

[validate.yml](../../.github/workflows/validate.yml)と同じ検証が成功したことを確認してから、Pull Requestを作成します。

## 現在の公開データを取得する

### GitHub Pagesのcurrent JSON-LD

[GitHub PagesのDatasetページ](https://nawashiro.github.io/chiyoda_city_main_facilities/)は、現在の配布物と形式を示します。current JSON-LDは[Pagesのplaces.jsonld](https://nawashiro.github.io/chiyoda_city_main_facilities/places.jsonld)から取得します。repository内の[Pages用places.jsonld](../../site/places.jsonld)は、canonical JSON-LDとbyte-identicalです。

```bash
curl -fL 'https://nawashiro.github.io/chiyoda_city_main_facilities/places.jsonld' \
  -o /tmp/places.jsonld
python3 -m src.fac_cli jsonld-validate /tmp/places.jsonld
```

### GitHub Releaseの版固定snapshot

[release-jsonld.yml](../../.github/workflows/release-jsonld.yml)は、公開されたRelease tagでcanonical JSON-LDを検証します。workflowはcanonical bytesを`places-<TAG>.jsonld`として保存し、GitHub Releaseへ添付します。手動実行はdry-runとしてartifactだけを作成し、Releaseへ添付しません。

版固定snapshotは[GitHub Releases](https://github.com/nawashiro/chiyoda_city_main_facilities/releases)から対象tagを選んで取得します。

```bash
TAG=<release-tag>
gh release download "$TAG" \
  --repo nawashiro/chiyoda_city_main_facilities \
  --pattern "places-${TAG}.jsonld"
python3 -m src.fac_cli jsonld-validate "places-${TAG}.jsonld"
```

current配布物にはPages URLを使います。再現可能な引用や検証には、GitHub Releaseの版固定snapshotを使います。

## JSON-LDだけへの破壊的変更

公開配布形式はJSON-LDだけです。以前の公開形式、URL、ファイル名、属性を前提にする利用者は、Pagesの`places.jsonld`またはRelease assetへ移行します。以前の形式との並行配布や自動変換を行いません。

利用者は`application/ld+json`として取得し、`@graph`内の`schema:Place`と`geo:Feature`を処理します。既存のPlaceを追跡する利用者は、`urn:uuid:`の`@id`を保存します。破壊的変更を含む更新では、利用者向けの移行案内をPull RequestとRelease notesへ記録します。
