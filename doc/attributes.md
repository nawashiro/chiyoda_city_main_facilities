# 属性リファレンス

このデータベースが保持する2つの主要ファイル — 正本（`data/registry.json`）と公開用GeoJSON（`dist/public/places.geojson`）の各属性と取りうる値を説明します。

## データの関係

`data/registry.json` が唯一の正本（canonical source of truth）です。`dist/public/places.geojson` は正本から機械的に生成される公開用の派生物であり、公開に適さない内部情報（監査記録、外部参照の履歴、座標の採用元など）を含みません。

---

## `data/registry.json` — 正本（Placeレジストリ）

施設（Place）の完全な情報を保持します。1施設 = 1つのPlaceオブジェクトです。

### トップレベル

| 属性 | 型 | 説明 |
|------|----|------|
| `schemaVersion` | 整数 | スキーマの版。現在は `1` のみ |
| `places` | 配列 | Placeオブジェクトの配列 |

### Placeオブジェクト

#### 基本属性

| 属性 | 型 | 必須 | 説明 |
|------|----|:--:|------|
| `id` | 文字列 | ✓ | 施設の永続識別子。UUIDv7形式（生成時刻でソート可能なUUID。例：`019fa880-5cd4-78e1-aa8b-c4ce83a065bc`） |
| `name` | 文字列 | ✓ | 施設の表示名。日本語表記で、検索入力時に人が与えた名称 |
| `categoryIds` | 文字列の配列 | ✓ | 施設の分類。1件以上のカテゴリIDを持つ（[カテゴリ一覧](#カテゴリ一覧)参照） |
| `tags` | 文字列の配列 | ✓ | 任意の文字列ラベル。空配列も可。施設をアプリケーション側で絞り込むための付加情報として使われる（例：`kazaguruma.home-shortcut` は特定アプリのホーム画面ショートカット対象） |

#### 位置情報

| 属性 | 型 | 必須 | 説明 |
|------|----|:--:|------|
| `geometry` | オブジェクト | ✓ | 施設の位置。GeoJSON Point形式（地理空間データの標準形式、RFC 7946）。`{"type": "Point", "coordinates": [経度, 緯度]}` |
| `geometrySource` | オブジェクト | ✓ | 現在の座標がどの外部ソースから採用されたかの記録 |

`geometrySource` の内訳：

| 属性 | 型 | 説明 |
|------|----|------|
| `sourceId` | 文字列 | 採用元：`"openstreetmap"`（OpenStreetMap）/ `"wam"`（WAM NET福祉施設オープンデータ）/ `"search-input"`（人手入力の座標） |
| `recordId` | 文字列 | 採用元でのレコードID（OSMなら `node/123` や `way/456`、WAMなら `A0000110598` や `E0000085562` 等） |
| `confirmedAt` | 日時 | この座標の採用を確定した時刻（ISO 8601） |

#### 画像

| 属性 | 型 | 必須 | 説明 |
|------|----|:--:|------|
| `images` | オブジェクトの配列 | ✓ | 施設の画像。空配列も可 |

各画像オブジェクト：

| 属性 | 型 | 説明 |
|------|----|------|
| `url` | 文字列 | 画像のURL |
| `rights` | 文字列 | 権利表記（例：`"© Nawashiro"`） |

#### 外部参照

| 属性 | 型 | 必須 | 説明 |
|------|----|:--:|------|
| `externalRefs` | オブジェクトの配列 | ✓ | 外部データソース（OSM (OpenStreetMap)、WAM）の参照記録 |

各参照の内訳：

| 属性 | 型 | 説明 |
|------|----|------|
| `sourceId` | 文字列 | 参照元：`"openstreetmap"` / `"wam"` |
| `recordId` | 文字列 | 参照元でのレコードID |
| `status` | 文字列 | 参照の状態。`"current"`（有効な参照）または`"superseded"`（差し替え済み） |
| `firstConfirmedAt` | 日時 | この参照が最初に確定した時刻 |
| `lastConfirmedAt` | 日時 | この参照が最後に（再）確定された時刻 |
| `supersededAt` | 日時またはnull | 差し替えられた時刻。`"current"`の間は`null` |
| `basis` | 文字列 | 同定の根拠：`"name_coordinates"`（名称＋座標の一致）/ `"source_record"`（WAMの直接レコード）/ `"language_model"`（大規模言語モデルによる合議判断）/ `"human_review"`（人手による確認） |

#### ライフサイクルと公開範囲

| 属性 | 型 | 必須 | 説明 |
|------|----|:--:|------|
| `lifecycle` | オブジェクト | ✓ | 施設の運用状態 |

`lifecycle` の内訳：

| 属性 | 型 | 説明 |
|------|----|------|
| `status` | 文字列 | 現在は`"active"`（運用中）。閉鎖などの状態は未実装 |
| `changedAt` | 日時 | この状態になった時刻 |

| 属性 | 型 | 必須 | 説明 |
|------|----|:--:|------|
| `visibility` | オブジェクト | ✓ | 公開範囲 |

`visibility` の内訳：

| 属性 | 型 | 説明 |
|------|----|------|
| `status` | 文字列 | `"public"`（公開）または`"private"`（非公開） |
| `changedAt` | 日時 | この状態になった時刻 |

#### 監査記録

| 属性 | 型 | 必須 | 説明 |
|------|----|:--:|------|
| `audit` | オブジェクトの配列 | ✓ | このPlaceに対して行われた操作の監査証跡 |

各監査エントリの内訳：

| 属性 | 型 | 説明 |
|------|----|------|
| `at` | 日時 | 操作が行われた時刻 |
| `method` | 文字列 | 操作の主体：`"human_inference"`（人手）/ `"calculation_model"`（自動計算）/ `"language_model"`（大規模言語モデルによる判断） |
| `action` | 文字列 | 操作の種類：`"created"`（Place作成）/ `"linked_osm"`（OSM参照追加）/ `"linked_wam"`（WAM参照追加）/ `"updated_geometry"`（座標更新） |
| `target` | 文字列 | 操作対象。Place作成時は `"place"`、OSM/WAMの参照操作時は `"node/123"` 等のレコードID、座標更新時はPlaceのUUID |

---

## `dist/public/places.geojson` — 公開用GeoJSON

正本から自動生成される、配布・利用者向けのファイルです。RFC 7946（GeoJSON）準拠。

### トップレベル

| 属性 | 型 | 説明 |
|------|----|------|
| `type` | 文字列 | 固定値 `"FeatureCollection"` |
| `sourceAttributions` | 配列 | 使用した外部データソースの帰属情報。施設データのソース（OSM (OpenStreetMap)、WAM）に加え、町名判定に使用した町名ポリゴンデータ（`chiyoda-city-town-geojson`）も含む |
| `features` | 配列 | Featureオブジェクトの配列（施設数と同数） |

### `sourceAttributions` の各要素

| 属性 | 型 | 説明 |
|------|----|------|
| `sourceId` | 文字列 | ソース識別子（`"chiyoda-city-town-geojson"` / `"openstreetmap"` / `"wam"`） |
| `url` | 文字列 | ソースの公式URL |
| `license` | 文字列 | ライセンス名 |
| `licenseUrl` | 文字列 | ライセンス文書のURL |
| `version` | 文字列 | 取得時の版（コミットハッシュ、リリース版等） |
| `retrievedAt` | 日時 | 取得日時 |
| `sha256` | 文字列 | 取得データのSHA-256ハッシュ |
| `attribution` | 文字列 | 表示用の帰属表記 |
| `transformation` | 文字列 | このDBで適用した加工の概要 |

### Featureの`properties`

各施設はGeoJSON Featureとして表現され、`geometry`はPoint（`[経度, 緯度]`）です。

| 属性 | 型 | 説明 |
|------|----|------|
| `id` | 文字列 | 正本と同じUUIDv7 |
| `name` | 文字列 | 正本と同じ施設名 |
| `categoryIds` | 文字列の配列 | 正本と同じカテゴリID（[カテゴリ一覧](#カテゴリ一覧)参照） |
| `tags` | 文字列の配列 | 正本と同じタグ |
| `images` | オブジェクトの配列 | 正本と同じ画像情報（`url` と `rights`） |
| `town` | 文字列またはnull | 町名ポリゴンとの点包含判定で得た町名。データの粒度を「町」レベルに統一するため丁目以降を削除している。該当施設がどの町ポリゴンにも含まれない場合は`null` |
| `lifecycleStatus` | 文字列 | 正本の `lifecycle.status` と同じ。現在は `"active"` のみ |
| `sources` | オブジェクト | 外部ソースから取得した参照データ。以下のキーを持ちうる：<br>`openstreetmap` — 存在する場合、`retrievedAt`（取得日時）と `record`（OSMノード/ウェイ/リレーションのスナップショット）を含む<br>`wam` — 存在する場合、`retrievedAt`（取得日時）と `records`（WAMレコードの配列）を含む |

> **注**: `sources`に含まれる`openstreetmap`および`wam`の詳細な属性は、それぞれOpenStreetMapとWAM NETが提供する外部データです。このデータベースの責務範囲外のため、本ドキュメントでは説明しません。各ソースの公式ドキュメントを参照してください。

### 正本にのみ存在する属性（公開GeoJSONに含まれないもの）

公開GeoJSONには以下の属性は**含まれません**。

- `geometrySource` — 座標の採用元記録
- `externalRefs` — 外部参照の履歴と同定根拠
- `lifecycle.changedAt` / `visibility.changedAt` — 状態変更の時刻
- `visibility` — 公開範囲。`public`以外のPlaceは公開GeoJSONから除外
- `audit` — 監査証跡

---

## カテゴリ一覧

`categoryIds` で使用されるカテゴリIDとその意味です。

| 値 | 意味 |
|----|------|
| `art-museum` | 美術館 |
| `buddhist-temple` | 寺院 |
| `christian-church` | 教会 |
| `cinema` | 映画館 |
| `disability-support` | 障害者相談支援事業所 |
| `library` | 図書館 |
| `museum` | 博物館 |
| `park` | 公園 |
| `public-bath` | 公衆浴場・銭湯 |
| `public-office` | 区役所・出張所等の公的窓口 |
| `social-welfare` | 社会福祉施設 |
