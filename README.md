# 千代田区主要施設データベース

千代田区で「生活する・助けてもらう・楽しむ」ために訪れる主要施設を、小規模に保守するデータベースです。

## 公開データ

公開物は代表点をPointで収録し、画像・OSM属性・WAM属性を各Featureから直接利用できるGeoJSONです。

```text
https://cdn.jsdelivr.net/gh/nawashiro/chiyoda_city_main_facilities@<version>/dist/public/places.geojson
```

本番利用では`latest`ではなくリリースまたはコミットを指定してください。`dist/public/manifest.json`のSHA-256で取得物を確認できます。

公開GeoJSONには名称、分類、用途タグ、画像、代表点、派生町名、lifecycle、ソース別のOSM/WAM属性を含めます。OSMの過去ID・同定監査、OSMポリゴン・relation member、町名ポリゴンは含めません。

## データ構成

- `inputs/osm-search/`: OSM同定用の検索入力。正本ではありません
- `data/registry.json`: 唯一のPlace正本
- `schema/`: 検索入力、正本、公開GeoJSONの契約
- `dist/public/places.geojson`: 正本から生成する公開用派生物
- `reports/`: 一時移行や更新結果の短いレポート
- `img/`: 正本から参照する画像

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

`--color`と`--hyperlink`の既定値は`auto`です。対応する対話端末では属性名をシアン、`true`/`current`/`active`/`public`を緑、`false`/`superseded`を赤で表示し、`geo:` URIを青のOSC 8ハイパーリンクにします。パイプやファイルへの出力は平文のままです。端末の自動判定を上書きする場合は、それぞれ`always`または`never`を指定します。色を無効化する標準的な`NO_COLOR`環境変数にも対応します。

### 一覧の属性

`./fac ls` が表示する各行の意味と取りうる値です。

| 属性 | 意味 | 取りうる値 |
|------|------|-----------|
| `id` | 施設の永続識別子。検索入力から引き継ぐUUIDv7 | `019…` 形式のUUIDv7文字列 |
| `cat` | 分類（`categoryIds`）。複数ある場合は `,` 区切り | `art-museum` `buddhist-temple` `christian-church` `cinema` `disability-support` `library` `museum` `park` `public-bath` `public-office` `social-welfare` |
| `tags` | ショートカットタグの有無 | `true`（あり） `false`（なし） |
| `img` | 画像の有無 | `true`（あり） `false`（なし） |
| `osm` | OpenStreetMap 参照の状態 | `current`（現在の参照あり） `superseded`（過去の参照のみ） `false`（参照なし） |
| `wam` | WAM 参照の状態 | `current` `superseded` `false`（`osm` と同じ意味） |
| `life` | 施設の運用状態（`lifecycle.status`） | `active`（運用中）— 将来 `closed`（閉鎖）`planned`（計画中）等も想定 |
| `vis` | 公開範囲（`visibility.status`） | `public`（公開）— 将来 `restricted`（制限付き）等も想定 |
| `geo:` | クリック可能な地図URI。座標は `geo:緯度,経度` 形式 | RFC 5870 準拠のgeo URI |

`osm`と`wam`は、正本`externalRefs`内の参照のうち最新の`status`を集約して表示します。`current`が一件でもあれば`current`、`current`がなく`superseded`があれば`superseded`、一件もなければ`false`です。

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

OSMの曖昧候補は、検索入力1件と50m以内の全候補を一括でOpenAI互換APIへ提示します。候補にはOSM rawの全タグを含め、訪問者（同じ地物か）、利用者（同じ用途か）、現地スタッフ（同じチームか）という異なる3つのプロンプトで判断します。2票以上が同じ候補またはrejectで一致すれば自動処理します。最初に次を設定します。

```bash
export LLM_API_KEY="..."
export LLM_MODEL="使用するモデル名"
# OpenAI以外を使う場合だけ設定
export LLM_BASE_URL="https://api.example.com/v1"
```

GitHub Actionsでは`LLM_API_KEY`をActions secret、`LLM_MODEL`をActions variableとして登録します。OpenAI以外を使う場合だけ`LLM_BASE_URL`もvariableへ登録します。

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

GitHub Actionsの`Update WAM data`、`Update OpenStreetMap data`、`Update town polygons`からも同じ経路を手動実行できます。WAMは`YYYYMM`版、町名はfull commit SHAだけを入力し、OSMは入力不要です。OSM更新で人間確認が残らなければPull Requestを作り、残れば30日間のartifactに結び付いた確認Issueを作ります。WAMと町名は従来どおりレビュー用artifactを作ります。

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
