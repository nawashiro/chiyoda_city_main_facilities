# 千代田区主要施設データベース 保守仕様

## 1. 目的と範囲

この文書は、現在のrepositoryに実装されているデータ保守契約を記述する。将来案は末尾へ分離し、現行機能として扱わない。

対象は、千代田区で生活・支援・余暇のために実際に訪れる主要施設である。網羅性より、単独保守できる単純さと誤案内を避けることを優先する。

WAM NETから取り込むのは相談支援4サービスだけである。

- 計画相談支援: `52`
- 地域相談支援（地域移行）: `53`
- 地域相談支援（地域定着）: `54`
- 障害児相談支援: `70`

利用可能時間の空欄では除外しない。就労、生活介護、児童発達、居住等のサービスはこの取込対象に含めない。

## 2. 正本と生成物

### 2.1 検索入力

`inputs/osm-search/{source}/{batch}.json`は外部ソース照合の入力であり、正本ではない。

各queryは先に採番したUUIDv7と検索語を持ち、次のどちらか一方だけを持つ。

- `id + name + coordinates`
- `id + name + qid`

QIDと座標の併記は禁止する。同じUUIDが正本にあれば作成済み、なければ未作成と判断する。

### 2.2 正本

`data/registry.json`が唯一のPlace正本である。Placeは検索入力と同じUUIDと`name`を保持する。正本には代表点、分類、用途タグ、画像欄、lifecycle、visibility、外部参照履歴、短いauditがある。

代表点の更新優先順位は次のとおり。

1. WAM
2. OpenStreetMap
3. 検索入力座標

OSMとWAMの参照は`externalRefs`へ保持する。OSM IDが変わった場合、旧IDを削除せず`superseded`へ変更する。

### 2.3 公開GeoJSON

`dist/public/places.geojson`は正本から決定的に生成する公開用の影である。

公開条件は`visibility.status == "public"`である。各FeatureはPointだけを持ち、propertiesは次の5項目だけを持つ。

- `id`
- `name`
- `categoryIds`
- `tags`
- `town`

画像、lifecycle、visibility、外部参照、audit、OSM属性、OSMポリゴン、町名ポリゴンは公開GeoJSONへ含めない。

`sourceAttributions`には、公開物の生成に実際に寄与したソースのURL、版、取得日時、SHA-256、利用条件、帰属、加工内容を含める。

`dist/public/manifest.json`には公開GeoJSONのSHA-256を記録する。

## 3. 現在実装されている検証

`python3 -m src.facility_data validate .`は、現在次を確認する。

### 検索入力

- documentとqueryの許可フィールド
- source種別
- UUIDv7形式と重複
- 非空の`name`
- QID形式
- QIDと座標の排他
- 座標の型と範囲
- 複数ファイル間のquery ID重複

### 正本

- Place IDの重複
- 対応する検索入力の存在
- 検索入力との`name`一致
- Point geometryと座標範囲
- current OSM参照が最大1件
- auditが4キーであること
- audit methodが許可値であること

### WAM snapshot

- normalized documentとrecordの基本形式
- query IDの存在と重複
- WAM ID、`sourceRecordIds`、名称、座標
- `imports/wam/raw.json`のSHA-256と取得台帳の一致
- raw版と取得台帳の版の一致
- raw rowの必須フィールド、座標、source ID重複
- normalized recordの全source IDがrawに存在すること
- primary ID、事業所番号、サービスコード・種別、名称、座標がraw groupから再計算した値と一致すること
- 検索入力との名称照合
- 座標検索入力の場合は50m以内であること

### OSM snapshot

- typeと正のID
- QID形式
- `matchBasis`が`source_record`、`qid`、`name_coordinates`、`language_model`のいずれか
- QID照合では検索入力QIDとの一致
- 名称＋座標照合では名称完全一致かつ50m以内
- current参照照合では既存current IDであること、名称・QIDの競合がないこと、既存代表点から50m以内であること

町名GeoJSONのPolygon/MultiPolygon構造、閉ring、異なる頂点数、非ゼロ面積、座標範囲、町名重複は`src.retrieve_towns`の取得時に検証する。

この一覧にないSchema全体、画像権利、業務上の正しさを`validate`が自動判定するとはみなさない。

## 4. WAM更新

手動実行例:

```bash
python3 -m src.retrieve_wam . --release "$WAM_RELEASE" --at "$RETRIEVED_AT"
python3 -m src.facility_data update . --source wam --at "$RETRIEVED_AT"
python3 -m src.facility_data validate .
```

`WAM_RELEASE`は公式配布版の`YYYYMM`を明示指定する。

取得処理は4サービスZIPを各1回だけ読み、応答サイズ、ZIP展開サイズ、圧縮率、CSV行数を制限する。東京都千代田区の有効行だけを`imports/wam/raw.json`へ保持し、normalized snapshotを作る。

公式ZIPそのものはrepositoryやActions artifactへ恒久保存しない。`imports/wam/retrieval.json`には取得URL、content length、ETag等、ZIPのSHA-256を記録する。

適用時はnormalized recordを検索入力とretained raw rowsの双方に照らして再検証する。WAM recordがあるのにraw rowsがない場合は適用を拒否する。

## 5. OpenStreetMap更新

手動実行例:

```bash
python3 -m src.retrieve_osm . --at "$RETRIEVED_AT"
python3 -m src.resolve_osm_candidates .
python3 -m src.facility_data update . --source openstreetmap --at "$RETRIEVED_AT"
python3 -m src.facility_data validate .
```

既知ID、QID、千代田区内の対象カテゴリを単一Overpass queryで取得する。施設ごとのN+1問い合わせは行わない。

自動適用経路は次の3つである。

1. 既存current OSM参照
2. 検索入力QIDと一致する一意候補
3. 検索入力から50m以内、かつ名称完全一致の一意候補

残った近傍候補はOpenAI互換APIへ独立した3回の判断を依頼する。3つの有効票のうち2票以上が同じ候補へのlinkで一致すれば`matchBasis: language_model`として適用し、2票以上がrejectで一致すれば自動却下する。合議不成立だけを`reports/osm-review-needed.json`へ残す。候補がない施設は人手確認へ送らず、OSM参照なしのまま扱う。

LLMには検索入力の名称と、取得済みの候補だけを渡す。候補一覧にないIDは受理しない。長い推論本文は保存せず、短い票と結果だけを候補レポートへ残す。Overpass応答に`remark`または`error`がある場合は部分応答として拒否する。

成功した新規取得ではquery bytes、HTTP response bytes、canonical rawを別々に保存し、それぞれのSHA-256を記録する。過去snapshotでexact query/responseが残っていない場合はretention flagを`false`とし、存在しないbytesを保持済みと主張しない。

## 6. 町名更新

町名GeoJSONは`nawashiro/chiyoda_city_town_geojson`の40文字commit SHAを指定して取得する。

```bash
python3 -m src.retrieve_towns . --commit "$TOWN_COMMIT" --at "$RETRIEVED_AT"
python3 -m src.facility_data build .
python3 -m src.facility_data validate .
```

町名は正本へ書き込まない。公開build時に代表点と町名ポリゴンのpoint-in-polygonで導出する。一意に決まらない場合は`null`になる。

## 7. GitHub Actions

次のworkflowはすべて`workflow_dispatch`による手動実行である。

- `Update WAM data`
- `Update OpenStreetMap data`
- `Update town polygons`

workflowは取得、正規化、適用またはbuild、validate、unit testsを実行する。repositoryへcommit/pushせず、手動レビュー用artifactだけを作る。

review diff生成前に`git add -N .`を行い、新規ファイルもbinary diffへ含める。

同一ソースの再取得は30日未満では拒否する。運用目安はWAMが公式公開後の年2回、OSMと町名が四半期または必要時である。

## 8. レビュー手順

1. `reports/*-update.diff`を確認する。
2. 正本Placeの削除、UUID変更、名称変更がないことを確認する。
3. WAMは8相談支援施設という対象範囲を維持しているか確認する。
4. OSMの合議不成立候補だけが`reports/osm-review-needed.json`へ残っているか確認する。
5. `sourceAttributions`と取得台帳の版・SHAを確認する。
6. tests、validate、決定的buildを再実行する。
7. clean cloneでも同じ検証を行う。

## 9. 現在未実装の将来候補

OSM候補の3票合議は取得workflowへ接続済みである。`review_hold`への自動移行、画像権利の自動検証、Schema全体のruntime検証は現行運用ではない。

これらを実装する場合は、実行経路、失敗時の扱い、tests、文書を同じ変更で追加する。
