# 千代田区主要施設データベース 保守仕様

## 1. 目的と範囲

この文書は、現在のrepositoryに実装されているデータ保守契約を記述する。将来案は末尾へ分離し、現行機能として扱わない。

対象は、千代田区で生活・支援・余暇のために実際に訪れる主要施設である。網羅性より、単独保守できる単純さと誤案内を避けることを優先する。

WAM NETから取り込むのは相談支援4サービスだけである。

初参加者は、まず[最初の施設変更](../tutorials/first-data-change.md)を読み、作業branchを作成する。通常のデータ修正では、検索入力または正本だけを変更し、公開生成物を直接編集しない。

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

人が作るファイルの例は`inputs/osm-search/human/202607.json`で、`source`は`{"kind": "human", "sourceId": null, "retrievedAt": null}`とする。座標順は`[経度, 緯度]`である。UUIDv7は`python3 -c 'from src.facility_data import new_uuid7; print(new_uuid7())'`で生成できる。入力の追加・修正は[施設を保守する](../how-to/maintain-a-place.md)を参照する。

### 2.2 正本

`data/registry.json`が唯一のPlace正本である。Placeは検索入力と同じUUIDと`name`を保持する。正本には代表点、分類、用途タグ、画像欄、lifecycle、visibility、外部参照履歴、短いauditがある。

代表点の更新優先順位は次のとおりです。

1. WAM
2. OSM (OpenStreetMap)
3. 検索入力座標

OSMとWAMの参照は`externalRefs`へ保持する。OSM IDが変わった場合、旧IDを削除せず`superseded`へ変更する。

### 2.3 公開GeoJSON

`dist/public/places.geojson`は正本から決定的に生成する公開用の影である。

公開条件は`visibility.status == "public"`である。各Featureのgeometryは正本の代表点を複写したPointだけとし、propertiesは次を持つ。

- `id`
- `name`
- `categoryIds`
- `tags`
- `images`
- `town`
- `lifecycleStatus`
- `sources`

`images`は正本の画像を公開利用者が直接扱える形で含める。`sources.openstreetmap`には現在採用したOSMレコードの型・ID・代表点・タグと取得時刻を、`sources.wam`には対応するWAM元レコードのID・事業所ID・サービスコード・サービス種別・名称・座標と取得時刻を含める。住所、運営者、連絡先、アクセシビリティ等はトップレベルへ統合せず、OSMタグまたはWAMレコードのソース別名前空間で公開する。

正本の`externalRefs`、過去OSM ID、確認時刻、失効時刻、同定根拠、`audit`、OSMポリゴン・relation member、町名ポリゴンは公開GeoJSONへ含めない。内部データの重複を削減する場合も、公開利用者が直接扱う画像・OSM属性・WAM属性は削らず、検索入力、正本、normalized snapshot等の内部ファイル間で重複を減らす。

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
- 名称＋座標照合では、NFKC正規化と空白・記号除去後に6文字以上あり、編集距離が名称長の15%以内（最低1文字、最大3文字）かつ50m以内
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

取得処理は4サービスZIPを各1回だけ読み、応答サイズ、ZIP展開サイズ、圧縮率、CSV行数を制限する。東京都千代田区の有効行だけを`imports/wam/raw.json`へ保持し、normalized snapshotを作る。raw rowの`attributes`には公式CSVの29列を列名そのまま（空欄は空文字）で保持し、法人・事業所の住所、電話、FAX、URL、利用時間、定休日、定員等を公開GeoJSONから直接利用できるようにする。

公式ZIPそのものはrepositoryやActions artifactへ恒久保存しない。`imports/wam/retrieval.json`には取得URL、content length、ETag等、ZIPのSHA-256を記録する。

適用時はnormalized recordを検索入力とretained raw rowsの双方に照らして再検証する。WAM recordがあるのにraw rowsがない場合は適用を拒否する。

`facility_data update`は正本、公開GeoJSON、manifestをまとめて再生成する。更新後は`validate`だけを実行すればよく、別の`build`は不要である。

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
3. 検索入力から50m以内、かつ正規化後に6文字以上あり、編集距離が名称長の15%以内（最低1文字、最大3文字）の一意候補

残った近傍候補は、検索入力1件と50m以内の全候補を一括提示します。
OpenAI互換APIへ3回の判断を依頼します。
3回の判断では、訪問者、利用者、現地スタッフの視点を使います。
2票以上が同じ候補へのlinkで一致した場合は、`matchBasis: language_model`として適用します。
2票以上がrejectで一致した場合は、自動却下します。
合議不成立だけを`reports/osm-review-needed.json`へ残します。
候補がない施設は人手確認へ送らず、OSM参照なしのまま扱います。

候補がない既存Placeは今の座標を保つ。QIDだけを持つ新規検索入力で、WAMにもOSMにも対応データがなければ、新しいPlaceは作らない。

LLMには検索入力の全項目、対応するWAM record・raw rowsがあればその属性、取得済みOSM候補の型付きID・座標・距離・raw由来の全タグを渡す。候補一覧にないIDは受理しない。長い推論本文は保存せず、視点名、短い票、結果だけを候補レポートへ残す。Overpass応答に`remark`または`error`がある場合は部分応答として拒否する。

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
- `Re-identify retained source snapshots`

GitHub Actionsの更新workflowは、対象branchを選び、必要な版またはcommitを入力して実行する。WAMと町名の更新結果はartifactで確認し、必要な修正をbranchへ反映してPull Requestを作成する。OSMの確認Issueでは、検索入力ごとに候補を一つまたは「どれとも一致しない」を選び、最後に適用チェックを入れる。

通常の更新workflowは取得、正規化、適用またはbuild、validate、unit testsを実行する。OSMで合議不成立がなければ生成差分のPull Requestを作る。合議不成立があれば更新run固有のartifactを30日保持し、全候補を選べるGitHub Issueを一つ作る。

Issue本文のチェックボックスは検索入力ごとに一つだけ選択し、最後の適用チェックを押す。`Apply OSM human review` workflowはIssueに埋め込まれたrun IDとartifact名から元artifactを取得し、候補レポートSHA、候補集合、選択数を再検証する。`matchBasis: human_review`として反映し、監査方法を`human_inference`として正本・公開物を再生成し、testsとvalidate後にPull Requestを作る。人がJSONを編集・uploadする経路は設けない。

`Re-identify retained source snapshots`は検索入力修正後のbranchで手動実行する。外部取得コマンドを呼ばず、保存済みWAM・OSM rawと取得台帳のSHA・版を検証し、現在の検索入力に対してWAM normalizedとOSM候補を再生成する。処理時刻とsource取得時刻を分離し、正本名を修正後の検索名へ同期した後、WAM→OSMの順で適用する。合議不成立時は同じIssue経路へ進む。

review diff生成前に`git add -N .`を行い、新規ファイルもbinary diffへ含める。

同一ソースの再取得は30日未満では拒否する。運用目安はWAMが公式公開後の年2回、OSMと町名が四半期または必要時である。

## 8. レビュー手順

1. `reports/*-update.diff`を確認する。
2. 正本Placeの削除・UUID変更がなく、名称変更は意図した検索入力修正だけであることを確認する。
3. WAMの施設数・元レコード数が前回から大きく変わっていないか確認する。202603版の8施設・13元レコードは現在の目安であり、固定要件ではない。
4. OSMの合議不成立時は自動作成されたIssueで検索入力ごとに一候補または「どれとも一致しない」を選ぶ。
5. `sourceAttributions`と取得台帳の版・SHAを確認する。
6. tests、validate、決定的buildを再実行する。
7. clean cloneでも同じ検証を行う。

## 9. 現在未実装の将来候補

画像権利の自動検証、Schema全体のruntime検証は現行運用ではない。

これらを実装する場合は、実行経路、失敗時の扱い、tests、文書を同じ変更で追加する。
