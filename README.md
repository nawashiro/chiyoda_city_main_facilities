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

UUIDv7は次のコマンドで1件ずつ生成できます。

```bash
python3 -c 'from src.facility_data import new_uuid7; print(new_uuid7())'
```

## 検証と生成

外部パッケージは不要です。Python 3.13で実行します。

```bash
python3 -m unittest discover -s tests -v
python3 -m src.facility_data validate .
python3 -m src.facility_data build .
```

公開ファイルを直接編集してはいけません。検索入力または`data/registry.json`を更新し、検証後に再生成します。

## ソースsnapshotの更新

外部ソースを一括取得し、取得版・時刻・ハッシュを記録してから正規化・適用・公開物生成を行います。施設ごとの問い合わせは行わず、同一ソースの取得間隔は30日以上とします。

OSMの曖昧候補はOpenAI互換APIへ独立した3回の判断を依頼し、2票以上が一致すれば自動処理します。最初に次を設定します。

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
# 既存のOSM参照、QID一意一致、または名称完全一致かつ
# 50m以内で一意な候補を適用
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

合議できなかった候補だけが`reports/osm-review-needed.json`へ残ります。通常、人が確認するのはこのファイルだけです。候補なしの場合、既存Placeは今の座標を保ちます。QIDだけを持つ新規検索入力で、WAMにもOSMにも対応データがなければ、新しいPlaceはまだ作られません。

GitHub Actionsの`Update WAM data`、`Update OpenStreetMap data`、`Update town polygons`からも同じ経路を手動実行できます。WAMは`YYYYMM`版、町名はfull commit SHAだけを入力し、OSMは入力不要です。各Actionはリポジトリへ直接pushせず、ソースごとの取得物・台帳・生成物とレビュー用diffを14日間artifactとして保存します。

外部から消えたという理由だけでPlaceは削除しません。WAMは公式公開後の年2回、OSMと町名は四半期または手動を基本とし、更新は一ソース版ずつ扱います。

WAMから取得するのは、計画相談支援、地域移行、地域定着、障害児相談支援の4サービスです。

## 運用方針

- UUID重複を許容しない
- OSMは決定規則で解ける候補を先に適用し、残りを3回のLLM判断へ渡す
- 2票以上が同じ候補またはrejectで一致すれば、人の確認なしで処理する
- 合議不成立だけを`reports/osm-review-needed.json`へ出す
- 外部ソースから消えたという理由だけでPlaceを削除しない
- 監査記録は`at`、`method`、`action`、`target`だけにする
- 外部ソース取得はソースごとに月1回以下にする

詳しい設計は[`doc/data_maintenance_spec.md`](doc/data_maintenance_spec.md)を参照してください。

## ライセンスと出典

ソースごとのライセンスと公開時の帰属は[`SOURCES_AND_LICENSES.md`](SOURCES_AND_LICENSES.md)および[`config/sources.json`](config/sources.json)に記録しています。
