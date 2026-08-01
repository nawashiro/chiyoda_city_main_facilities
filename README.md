# 千代田区主要施設データベース

千代田区で「生活する・助けてもらう・楽しむ」ために訪れる主要施設を、小規模に保守するデータベースです。

## 初めて作業する人へ

このリポジトリは、外部パッケージなしでPython 3.13から実行できます。データ更新では、検索入力、正本、公開生成物を順に確認します。

### 1. リポジトリを準備する

```bash
git clone git@github.com:nawashiro/chiyoda_city_main_facilities.git
cd chiyoda_city_main_facilities
git switch -c data/<作業内容>
```

SSH鍵を使えない場合は、GitHubのHTTPS URLを`git clone`へ指定してください。既存の作業がある場合は、作業前に`git status`で未コミット変更を確認してください。

### 2. 現在の状態を検証する

```bash
python3 -m unittest discover -s tests -v
python3 -m src.facility_data validate .
python3 -m src.facility_data build .
git diff --check
```

既存の検証が失敗した場合は、データを変更せずに失敗内容をIssueへ報告してください。`build`は`data/registry.json`と固定済みソースから公開GeoJSONとmanifestを再生成します。

### 3. 作業の入口を選ぶ

| 目的 | 最初に読む文書 | 主な入口 |
|---|---|---|
| 施設の分類、タグ、公開状態を直す | [`doc/attributes.md`](doc/attributes.md) | `./fac set` |
| OSM検索入力を追加・修正する | [`doc/data_maintenance_spec.md`](doc/data_maintenance_spec.md) | `./fac in add`、`./fac in set` |
| WAM、OSM、町名を更新する | [`doc/maintenance_plan.md`](doc/maintenance_plan.md) | GitHub Actionsまたは更新コマンド |
| 公開データの出典と利用条件を確認する | [`SOURCES_AND_LICENSES.md`](SOURCES_AND_LICENSES.md) | `config/sources.json`、`sourceAttributions` |

通常の変更は、作業branchで入力または正本を更新し、検証、再生成、差分確認の順に進めます。`dist/public/`を直接編集してはいけません。作業終了時はPull Requestを作成し、GitHub Actionsの`Validate data`が対象commitで成功したことを確認してください。

### 4. 最初の変更からPull Requestまで

施設の分類、タグ、ライフサイクル、公開範囲を変更する場合は、次を実行します。

```bash
./fac ls
./fac set <UUID> --cat library --tag example.tag
python3 -m src.facility_data validate .
python3 -m src.facility_data build .
git diff --check
git diff -- data/registry.json dist/public/
git add data/registry.json dist/public/
git commit -m "data: update facility metadata"
git push -u origin data/<作業内容>
```

OSM検索入力を変更する場合は、`./fac in add`または`./fac in set`を実行してから、同じ検証とPull Requestの手順へ進みます。`./fac set`の`--cat`、`--tag`は指定した値で配列全体を置き換えるため、既存値を残す場合は先に`./fac get <UUID>`で確認してください。

WAMまたは町名をGitHub Actionsで更新する場合は、後述のartifact取込手順を使います。更新workflowは自動でPull Requestを作成しません。

## 公開データ

公開物は代表点をPointで収録し、画像・OSM属性・WAM属性を各Featureから直接利用できるGeoJSONです。

```text
https://cdn.jsdelivr.net/gh/nawashiro/chiyoda_city_main_facilities@<version>/dist/public/places.geojson
```

本番利用では`latest`ではなくリリースまたはコミットを指定してください。`dist/public/manifest.json`のSHA-256で取得物を確認できます。

公開GeoJSONには名称、分類、用途タグ、画像、代表点、派生町名、lifecycle、ソース別のOSM (OpenStreetMap)・WAM属性を含めます。
OSMの過去ID・同定監査、OSMポリゴン・relation member、町名ポリゴンは含めません。

## データ構成

- `inputs/osm-search/`: OSM同定用の検索入力。正本ではありません
- `data/registry.json`: 唯一のPlace正本
- `dist/public/places.geojson`: 正本から生成する公開用派生物
- `schema/`: 検索入力、正本、公開GeoJSONの契約
- `reports/`: 一時移行や更新結果の短いレポート
- `img/`: 正本から参照する画像

各ファイルの属性と取りうる値の詳細は[`doc/attributes.md`](doc/attributes.md)を参照してください。

検索入力は次のいずれかです。

```text
UUIDv7 + name + coordinates
UUIDv7 + name + qid
```

同じUUIDを正本Placeへ引き継ぎます。正本の`name`は検索入力語だけです。座標はWAM、OSM、検索入力座標の順で採用します。

手入力は、たとえば`inputs/osm-search/human/202607.json`として次の形で作ります。座標順は`[経度, 緯度]`です。

```json
{
  "source": {"kind": "human", "sourceId": null, "retrievedAt": null},
  "queries": [
    {
      "id": "019ca6b1-dc00-7000-8000-000000000001",
      "name": "施設名",
      "coordinates": [139.75, 35.69]
    },
    {
      "id": "019ca6b1-dc00-7000-8000-000000000002",
      "name": "QIDで探す施設名",
      "qid": "Q12345"
    }
  ]
}
```

UUIDv7はCLIで自動生成します。個別に値だけ必要な場合は、次でも生成できます。

```bash
python3 -c 'from src.facility_data import new_uuid7; print(new_uuid7())'
```

## 保守CLI

リポジトリ直下の`fac`から、正本とOSM検索入力を短いコマンドで確認・更新できます。

```bash
# 正本一覧。名称、主要属性の有無・状態、geo URIを表示
./fac ls
./fac ls --town 神田神保町
./fac ls --cat library
./fac ls --name 図書館
./fac ls --osm false
./fac ls --life active
# 色・クリック可能なgeo URIは対応端末で自動有効。明示指定も可能
./fac ls --color always --hyperlink always

# 正本Placeを完全なJSONで確認
./fac get <UUID>

# 人が保守する正本項目を更新。--catと--tagは複数指定可能
./fac set <UUID> --cat library --tag kazaguruma.home-shortcut
./fac set <UUID> --life active --vis public

# OSM参照を手動確定。既存currentは同時にsupersededとなる
./fac ref <UUID> osm way/123456
# 現在参照を解除し、履歴だけ残す
./fac ref <UUID> osm none
```

`--color`と`--hyperlink`の既定値は`auto`です。対応する対話端末では属性名をシアン、`true`を緑、`false`を赤で表示し、`geo:` URIをOSC 8ハイパーリンクにします。パイプやファイルへの出力は平文のままです。端末の自動判定を上書きする場合は、それぞれ`always`または`never`を指定します。色を無効化する標準的な`NO_COLOR`環境変数にも対応します。

`ref`による手動確定は`basis=human_review`と`human_inference`監査を記録し、同じ型付きOSM IDが別Placeのcurrent参照にならないことを検証してから原子的に保存します。参照追加だけでは代表点を変更しません。保存済みrawを反映するには、commit後に`Re-identify retained source snapshots`を実行します。

検索入力は`in`配下で扱います。

```bash
./fac in ls
./fac in get <UUID>
./fac in add "施設名" --lon 139.75 --lat 35.69
./fac in add "施設名" --qid Q12345
./fac in set <UUID> --name "修正後の施設名"
./fac in set <UUID> --lon 139.75 --lat 35.69
./fac in set <UUID> --qid Q12345
```

`--lon`と`--lat`は常に組で指定します。内部のGeoJSON座標は`[経度, 緯度]`、一覧に出す`geo:` URIは`geo:緯度,経度`です。`in set`で座標とQIDを切り替えると、以前の検索キーは自動的に除去されます。

別のcheckoutを操作するテストや保守スクリプトでは、各コマンドのUUID等より前にrootパスを指定できます（例：`./fac ref /tmp/checkout <UUID> osm node/1`）。通常はリポジトリ直下で実行するため指定不要です。

## 検証と生成

外部パッケージは不要です。Python 3.13で実行します。

```bash
python3 -m unittest discover -s tests -v
python3 -m src.facility_data validate .
python3 -m src.facility_data build .
```

公開ファイルを直接編集してはいけません。通常は`./fac`で検索入力または正本の許可された項目を更新し、検証後に再生成します。緊急時にJSONへ戻れるようファイル形式自体は保ちますが、正本の`geometry`、`geometrySource`、`audit`は直接編集しません。

## ソースsnapshotの更新

外部ソースを一括取得し、取得版・時刻・ハッシュを記録してから正規化・適用・公開物生成を行います。施設ごとの問い合わせは行わず、同一ソースの取得間隔は30日以上とします。

OSM (OpenStreetMap)の曖昧候補は、検索入力1件と50m以内の全候補を一括でOpenAI互換APIへ提示します。
候補にはOSM rawの全タグを含めます。
訪問者、利用者、現地スタッフの3つのプロンプトで判断します。
2票以上が同じ候補またはrejectで一致すれば自動処理します。
最初に次を設定します。

```bash
export LLM_API_KEY="..."
export LLM_MODEL="使用するモデル名"
# OpenAI以外を使う場合だけ設定
export LLM_BASE_URL="https://api.example.com/v1"
```

GitHub Actionsでは`LLM_API_KEY`をActions secretとして登録します。
`LLM_MODEL`をActions variableとして登録します。
OpenAI以外を使う場合は`LLM_BASE_URL`もvariableへ登録します。

```bash
# WAM公式版の相談支援4サービスを取得・適用
AT=$(date --iso-8601=seconds)
python3 -m src.retrieve_wam . --release <YYYYMM> --at "$AT"
python3 -m src.facility_data update . --source wam --at "$AT"
python3 -m src.facility_data validate .

# 千代田区内の対象カテゴリをOverpassへ1回だけ問い合わせ、
# 既存のOSM参照、QID一意一致、または50m以内で
# 正規化・編集距離を満たす一意な名称候補を適用
AT=$(date --iso-8601=seconds)
python3 -m src.retrieve_osm . --at "$AT"
python3 -m src.resolve_osm_candidates .
python3 -m src.facility_data update . --source openstreetmap --at "$AT"
python3 -m src.facility_data validate .

# 町名Polygonをfull commit SHAで固定取得して公開物を再生成
AT=$(date --iso-8601=seconds)
python3 -m src.retrieve_towns . \
  --commit <40-character-commit-sha> --at "$AT"
python3 -m src.facility_data build .
```

`facility_data update`は正本と公開GeoJSONをまとめて再生成するため、WAM／OSM更新後に別の`build`は不要です。

合議できなかった候補は内部的には`reports/osm-review-needed.json`へ残りますが、人がJSONを編集する必要はありません。`Update OpenStreetMap data`が、検索入力、三者の票、全候補とその全属性、OSMリンク、選択チェックボックスをまとめたGitHub Issueを自動作成します。各検索入力で一つを選び、最後の適用チェックを押すと、別のActionが元のartifactと候補レポートSHAを検証し、正本と公開GeoJSONを再生成してPull Requestを作ります。

候補なしの場合、既存Placeは今の座標を保ちます。QIDだけを持つ新規検索入力で、WAMにもOSMにも対応データがなければ、新しいPlaceはまだ作られません。

GitHub Actionsの`Update WAM data`、`Update OpenStreetMap data`、`Update town polygons`からも同じ経路を手動実行できます。
WAMは`YYYYMM`版を入力します。
町名はfull commit SHAを入力します。
OSMは入力不要です。
OSM更新で人間確認が残らなければPull Requestを作ります。
人間確認が残れば、30日間のartifactに結び付いた確認Issueを作ります。
WAMと町名はレビュー用artifactを作ります。

WAMまたは町名の更新artifactをPull Requestへ取り込むには、GitHub CLI（GitHub Command Line Interface）を使います。
`<RUN_ID>`はActionsの実行番号です。
`<ARTIFACT_NAME>`は実行画面に表示されたartifact名です。

```bash
gh run download <RUN_ID> --name <ARTIFACT_NAME> --dir /tmp/chiyoda-update
cp -a /tmp/chiyoda-update/. .
python3 -m src.facility_data validate .
python3 -m unittest discover -s tests -v
python3 -m src.facility_data build .
git diff --check
git diff --stat
git add inputs imports data dist reports
git commit -m "data: apply source update"
git push -u origin data/<作業内容>
```

artifactの差分を確認してください。
意図しない削除やUUID変更がないことを確認してください。
確認後にcommitしてください。
WAM更新artifactの保存期間は14日です。
OSM更新artifactの保存期間は30日です。
町名更新artifactの保存期間は14日です。

検索入力を手動修正してcommitした後は、修正したbranchを選んで`Re-identify retained source snapshots`を実行します。このActionは外部通信や再取得をせず、保存済みWAM・OSM rawのSHAと版を検証してから現在の検索入力に対する同定を再実行します。WAM→OSMの順で適用し、検索名の変更は正本名へ同期します。合議不成立時は同じGitHub Issue経路へ進み、すべて解決できた場合は直接Pull Requestを作ります。

外部から消えたという理由だけでPlaceは削除しません。WAMは公式公開後の年2回、OSMと町名は四半期または手動を基本とし、更新は一ソース版ずつ扱います。

WAMから取得するのは、計画相談支援、地域移行、地域定着、障害児相談支援の4サービスです。対象行では公式CSVの29列（法人・事業所の住所、電話、FAX、URL、利用時間、定休日、定員等）を`attributes`として保持し、公開GeoJSONへ含めます。

## 運用方針

- UUID重複を許容しない
- OSMは決定規則で解ける候補を先に適用し、残りの全候補・全属性を三視点のLLM判断へ渡す
- 2票以上が同じ候補またはrejectで一致すれば、人の確認なしで処理する
- 合議不成立はGitHub Issueのチェックボックスで選び、JSONを人が手入力しない
- 外部ソースから消えたという理由だけでPlaceを削除しない
- 監査記録は`at`、`method`、`action`、`target`だけにする
- 外部ソース取得はソースごとに月1回以下にする

詳しい設計は[`doc/data_maintenance_spec.md`](doc/data_maintenance_spec.md)を参照してください。

## ライセンスと出典

ソースごとのライセンスと公開時の帰属は[`SOURCES_AND_LICENSES.md`](SOURCES_AND_LICENSES.md)および[`config/sources.json`](config/sources.json)に記録しています。
