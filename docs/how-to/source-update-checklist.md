# OSM・WAMソース更新チェックリスト

## 目的

このチェックリストは、OpenStreetMap（OSM）とWAMのsnapshotを更新するときに使う。取得元、取得時刻、ハッシュ、レビュー結果をPull Request（PR）で確認する。

canonical JSON-LD（正本）は`data/places.jsonld`である。保守者はこのファイルを直接レビューし、JSON-LDの検証結果とbyte単位の再現性を確認する。

手順の詳細は[ソースを更新する](update-source-data.md)を参照する。

## 参照するファイル

- 検索入力: `inputs/osm-search/`
- OSM snapshot: `imports/openstreetmap/raw.json`、`normalized.json`、`retrieval.json`、`query.overpassql`
- WAM snapshot: `imports/wam/raw.json`、`normalized.json`、`retrieval.json`
- ソース条件: `config/sources.json`
- canonical JSON-LD: `data/places.jsonld`
- 更新結果とレビュー: `reports/`
- OSM人手レビュー: `reports/osm-candidates.json`、`reports/osm-review-needed.json`、`reports/osm-review-needed.yaml`

## 更新前

- [ ] [Update WAM data workflow](../../.github/workflows/update-wam.yml)または[Update OpenStreetMap data workflow](../../.github/workflows/update-osm.yml)の入力値を確認する
- [ ] 作業branchを作成し、作業開始時の`git status --short`を記録する
- [ ] `python3 --version`がPython 3.13である
- [ ] 定期取得では、各`retrieval.json`の`retrievedAt`から最低取得間隔を確認する
- [ ] `config/sources.json`のsource ID、公式URL、ライセンス、帰属表示、加工説明を確認する
- [ ] OSMとWAMの取得時刻、版、取得元URLを更新対象のsnapshotと照合する
- [ ] 変更前の検証を実行し、失敗がないことを確認する

```bash
python3 -m unittest discover -s tests -v
python3 -m src.facility_data validate .
python3 -m src.fac_cli jsonld-validate data/places.jsonld
```

## 共通snapshot検証

各ソースのraw snapshotと取得メタデータを同じ更新単位で扱う。

- [ ] `imports/openstreetmap/retrieval.json`の`sourceId`が`openstreetmap`である
- [ ] `imports/wam/retrieval.json`の`sourceId`が`wam`である
- [ ] 各`retrieval.json`の`retrievedAt`がtimezone付きISO 8601である
- [ ] 各`retrieval.json`の`rawVersion`がraw snapshotの版と一致する
- [ ] 各`retrieval.json`の`rawSha256`が対応する`raw.json`のSHA-256と一致する
- [ ] 取得メタデータに実際の取得元URL、取得時刻、版、ハッシュを記録する
- [ ] `config/sources.json`にないsource IDをsnapshot、canonical JSON-LD、reportへ追加しない
- [ ] raw snapshot、normalized snapshot、reportのsource IDとquery IDを一致させる

raw snapshotのハッシュを検証する。

```bash
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

for source in ("openstreetmap", "wam"):
    directory = Path("imports") / source
    raw_path = directory / "raw.json"
    metadata_path = directory / "retrieval.json"
    raw_bytes = raw_path.read_bytes()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    actual_hash = hashlib.sha256(raw_bytes).hexdigest()
    assert metadata["sourceId"] == source
    assert metadata["rawVersion"]
    assert metadata["retrievedAt"]
    assert metadata["rawSha256"] == actual_hash, source
    print(f"{source}: {actual_hash}")
PY
```

- [ ] API key、token、Authorization header、個人情報をraw、normalized、report、YAML、PR本文、artifactへ書かない
- [ ] `LLM_API_KEY`をGitHub Actionsのsecretまたはローカル環境変数だけで扱う
- [ ] `LLM_MODEL`と`LLM_BASE_URL`をPR、artifact、ログへ秘密値として埋め込まない
- [ ] 三者のLLM設定で正規化後の`(base_url, model)`が重複しない

## WAM snapshot更新

WAMはサービスコード`52`、`53`、`54`、`70`を取得対象にする。

- [ ] WAM公開版を`YYYYMM`で指定する
- [ ] [Update WAM data workflow](../../.github/workflows/update-wam.yml)の`release`入力が対象公開版と一致する
- [ ] `imports/wam/retrieval.json`の`rawVersion`が対象公開版と一致する
- [ ] `retrieval.json`の各`artifacts[]`にサービスコード、URL、SHA-256、取得時刻に対応するHTTPメタデータ、byte数がある
- [ ] `imports/wam/raw.json`の行が対象範囲だけを含む
- [ ] `raw.json`の各行が安定ID、事業所番号、名称、サービス、座標を持つ
- [ ] `normalized.json`の各recordが検索入力のquery IDへ一意に対応する
- [ ] `normalized.json`の`sourceRecordIds`がrawの全対象行IDを保持する
- [ ] normalizedの名称、座標、サービス情報をrawの対応行から再計算できる
- [ ] 同じWAM source recordを複数のnormalized recordへ割り当てない
- [ ] `reports/latest-update.json`のsource、取得時刻、施設数、record数を確認する

## OSM snapshot更新

### 取得と検索入力

- [ ] `inputs/osm-search/`の全JSONを確認する
- [ ] 各検索入力が`coordinates`または`qid`の一方だけを持つ
- [ ] 検索入力IDが全ファイルで重複しない
- [ ] QIDが複数の検索入力で重複しない
- [ ] 1施設につき検索入力を1件だけ割り当てる
- [ ] 取得選択を1回のbatchにまとめ、`imports/openstreetmap/query.overpassql`へ保存する
- [ ] `retrieval.json`の`selectionSha256`が保存した取得選択のSHA-256と一致する
- [ ] `retrieval.json`のmanifest、PBF、rawのURL、版、byte数、SHA-256を確認する
- [ ] OSM rawの各named elementが`normalized.json`またはcandidate reportへ追跡できる
- [ ] candidate reportが検索入力ごとに全候補と全OSM tagを保持する
- [ ] `remark`または`error`を含む不完全な取得結果を採用しない

### OSM ownership

- [ ] `imports/openstreetmap/normalized.json`で同じ`type/id`を複数のqueryへ割り当てない
- [ ] `data/places.jsonld`で同じOSM `type/id`を複数のPlaceへ割り当てない
- [ ] 既に別のPlaceへ割り当てた候補を自動で再利用しない
- [ ] duplicate ownershipを検出したqueryを`needs_review`として残す
- [ ] OSMのQID照合が一意である
- [ ] 名称と座標による照合が、許容距離内の一意候補だけを採用する
- [ ] 既存OSM参照の名称、QID、座標の競合をPRで確認する

### YAMLとPRによる人手レビュー

- [ ] `reports/osm-review-needed.json`のquery IDがcandidate reportの`needs_review`対象と一致する
- [ ] `reports/osm-review-needed.yaml`の`reportSha256`がcandidate reportのSHA-256と一致する
- [ ] 各queryで候補または「候補なし」の`true`を1つだけ指定する
- [ ] 1つのqueryに2つ以上の人手選択を指定しない
- [ ] query ID、施設名、候補ID、`reportSha256`、未選択候補を変更しない
- [ ] YAMLをcommitし、[OSM人手レビュー適用workflow](../../.github/workflows/apply-osm-review.yml)が参照するPRでレビューする
- [ ] PRレビューで候補の全属性、検索入力、OSM画面、別Placeのownerを確認する
- [ ] 人手レビューの選択が元artifactのcandidate reportへ限定される
- [ ] unresolved queryを推測でcanonical JSON-LDへ追加しない

[Update OpenStreetMap data workflow](../../.github/workflows/update-osm.yml)は、候補report、レビューYAML、snapshot、canonical JSON-LDを同じartifactに保存する。PRでは、これらのSHA-256と差分を同時に確認する。

## canonical JSON-LDの直接検証

- [ ] `data/places.jsonld`だけをcanonical JSON-LDとしてPR差分で確認する
- [ ] 各`@id`が既存UUIDの`urn:uuid:`である
- [ ] 各recordが`schema:Place`と`geo:Feature`を持つ
- [ ] 各geometryが有効なPointである
- [ ] `schema:identifier`のOSM・WAM IDが対応するnormalized snapshotと一致する
- [ ] `config/sources.json`のsource条件とcanonical JSON-LDの外部IDが一致する
- [ ] operational history、LLM投票、取得秘密値をcanonical JSON-LDへ追加しない
- [ ] canonical JSON-LDの直接編集後にJSON構文とschemaを検証する

canonical JSON-LDのbyte単位の再現性を確認する。

```bash
cp data/places.jsonld /tmp/places.jsonld
python3 -m src.facility_data build .
python3 -m src.fac_cli jsonld-validate data/places.jsonld
cmp /tmp/places.jsonld data/places.jsonld
```

`cmp`が成功しない場合は、PRを提出せず、canonical JSON-LDの変更理由と編集箇所を確認する。

## 最終品質ゲート

```bash
python3 -m unittest discover -s tests -v
python3 -m src.facility_data validate .
python3 -m src.fac_cli jsonld-validate data/places.jsonld
git diff --check
```

- [ ] testsがすべて成功する
- [ ] `python3 -m src.facility_data validate .`が成功する
- [ ] `python3 -m src.fac_cli jsonld-validate data/places.jsonld`が成功する
- [ ] `git diff --check`が成功する
- [ ] byte再現性の`cmp`が成功する
- [ ] `reports/latest-update.json`、candidate report、レビューYAMLの差分を確認する
- [ ] 入力、snapshot、canonical JSON-LD、report以外の意図しないファイルを変更しない
- [ ] PRの[Validate data workflow](../../.github/workflows/validate.yml)が対象commitで成功する
- [ ] workflowが未実行の場合、成功として扱わず原因を解消する
- [ ] PR本文、レビューYAML、artifact、ログに秘密値がない

## 取得済みsnapshotの再同定

検索入力だけを修正し、raw snapshotを再取得しない場合は、[Re-identify retained source snapshots workflow](../../.github/workflows/reidentify-sources.yml)を使う。

- [ ] OSMとWAMのraw bytesが実行前後で同一である
- [ ] OSMとWAMの`retrieval.json`が実行前後で同一である
- [ ] 変更したqueryだけをcandidate reportとPRで確認する
- [ ] 変更していないqueryのcanonical JSON-LD IDと外部IDを変更しない
- [ ] 再同定後もraw hash、ownership、YAMLの一query一選択を再検証する
