# 千代田区主要施設データベース 保守計画

## 目的

千代田区で「生活する・助けてもらう・楽しむ」ために実際に訪れる主要施設を、一人の体力と判断を主たる部品にせず保守する。網羅性より、使える単純さと誤案内を避けることを優先する。

## 運用原則

- 旧JSON構造との後方互換を要件としない。
- OSM検索入力は正本ではない。人間入力もWAM入力も、`name + coordinates`または`name + qid`の単純な形式にする。
- QIDを持つ検索入力には座標を書かない。
- 唯一の正本は`data/registry.json`の5.2 Placeとする。
- 正本Placeは名称、分類、タグ、OSM由来座標、画像、lifecycle、visibility、OSM・WAM等への参照履歴を持つ。
- QIDから現在のOSM地物を同定した場合、正本のgeometryにはそのOSM地物の代表点を書き、`geometrySource`でOSM参照と確認時刻を示す。
- OSM IDを新しい値で上書きして消さず、現在・過去のID、確認時刻、失効時刻、短い根拠を残す。以前のIDも次回同定へ使う。
- 監査記録は時刻、方法、操作、対象だけにする。方法は`language_model`、`calculation_model`、`human_inference`、`field_observation`の4種とする。
- 長大なAI推論や監査ログを正本へ保存しない。必要時だけ一時レポートにする。
- 5.2 Placeは画像URLと権利情報を持つ`images`を含む。
- 住所、町名、包含関係、統合済みの運営者、サービス、連絡先、アクセシビリティを正本へ置かない。
- 町名は`nawashiro/chiyoda_city_town_geojson`とのpoint-in-polygonで公開時だけ導出する。
- OSM、WAM等の属性はGeoJSONへソース別名前空間のまま含め、統合値へ丸めない。
- 公開GeoJSONのgeometryは正本Placeの代表点Pointだけとし、OSMポリゴンと町名ポリゴンを含めない。
- OSM ID履歴、確認時刻、失効時刻、根拠、auditは正本だけに保持し、公開GeoJSONへ含めない。
- 旧JSONは未検証の`legacy_record`として扱い、そのまま正本へコピーしない。
- 既知の重複UUIDは不具合であり、新正本では例外として許容しない。
- 風ぐるま乗換案内はクライアント実行時にデータを取得せず、版固定したGeoJSONをビルド時に読み込んで静的生成する。
- `key`と`main`を別マスタにせず、ショートカットはPlaceの`kazaguruma.home-shortcut`タグで表す。
- 外部サービスへ施設ごとの問い合わせを行わず、一括取得とローカル照合を使う。
- 自動取得・変更確認は月1回以下とする。
- LLMを確率的であることだけを理由に排除しない。自動同定は独立した最低3体の有効票と3分の2以上の一致を必要条件にする。
- 推論レポートが必要な場合は根拠・反証・不確実性を先に置き、候補IDと最終判断を最後に置く。
- 現地確認は`field_observation`、ヒトが記憶・資料・既有知識から導いた判断は`human_inference`とする。
- 正本Placeの削除と`visibility.status: review_hold`による一時掲載停止を分離する。

## データ構造

```text
inputs/osm-search/{source}/{batch}.json # 人間、WAM等から作る検索入力
data/registry.json                     # 5.2 Placeを持つ唯一の正本
schema/search-input.schema.json         # 検索入力Schema
schema/registry.schema.json             # 正本Schema
config/sources.json                     # ソース・ライセンス台帳
imports/{source}/normalized.json        # 取得・正規化結果
reports/migration-v2.json               # 旧データ移行結果
reports/inference/{run-id}.json         # 必要時だけ残す推論実行記録
dist/public/places.geojson              # 正本から作る互換・公開用の影
```

## 掲載責務

- 保育所、幼稚園、学校、劇場は`out_of_scope`とし、施設ごとの移行判定を行わない。
- 病院は一般入院機能と一般利用可能性がある比較的大きな病院に限定する。
- 診療所、単科病院、特定組織向け病院は原則対象外とする。
- 新カテゴリは具体的利用場面、保守意思、信頼できる更新元が揃う場合だけ追加する。

## Phase 0: 単純な新設計の土台

- 検索入力と正本の2 Schemaを作る。
- 名前＋座標、名前＋QID、現在・過去のOSM ID、画像、GeoJSONのfixtureを作る。
- QIDと座標の併記を拒否する。
- UUIDv7重複を例外なしで拒否する。
- geometryと現在のOSM参照の対応を検証する。
- OSM ID履歴の時刻と状態を検証する。
- auditを4キー・4方法へ制限する。
- 町名、画像、ソース別公開属性を検証する。
- GeoJSONがPointだけを持ち、OSM来歴とポリゴンを含まないことを検証する。
- Pull Request CIを整える。

完了条件:

- すべてのfixtureが検証を通る。
- 無効なQID＋座標fixtureと重複UUID fixtureが失敗する。
- OSM ID更新fixtureで旧IDが`superseded`として残る。
- `review_hold`でも正本Placeが残り、通常GeoJSONからだけ除外される。

## Phase 1: 旧データの批判的インポート

- 旧`key_locations.json`と`main_facilities.json`を`legacy_record`として読む。
- 責務外カテゴリを先に一括除外する。
- 病院を再選定する。
- 旧UUIDを捨て、新しい一意なUUIDv7を割り当てる。
- 重複UUIDの2施設を別Placeにし、包含関係は作らない。
- 型を欠く旧OSM IDを未検証候補として再照合する。
- 対象候補を`imported`、`merged`、`split`、`rejected`、`unresolved`へ分類する。

## Phase 2: OSM同定とLLM合議

- 人間入力とWAM入力を同じ検索入力Schemaへ変換する。
- 既存Placeでは現在OSM ID、過去OSM ID、QID、名前と座標の順に検索手掛かりを使う。
- 地理候補の既定上限は50mとし、自動的に100mへ広げない。
- 決定的規則で候補を絞ってから最低3体へ独立に渡す。
- 3分の2以上の一致後もID、距離、カテゴリ、座標、ライセンスを検証する。
- 合議成立時、正本には長文ではなく短いauditだけを残す。
- 高リスク変更と合議不成立だけをヒト確認候補にし、期限を課さない。

## Phase 3: 正本・GeoJSON・風ぐるま乗換案内の切替

- `data/registry.json`を唯一のPlace正本として確定する。
- 現在と過去のOSM ID、時刻、根拠、短い監査記録を保持する。
- 正本と外部スナップショットから`dist/public/places.geojson`を決定的に生成する。
- GeoJSONには現在の代表点と公開属性だけを出し、OSM ID履歴、audit、OSM・町名ポリゴンを出力しない。
- 町名GeoJSONと外部ソースの版、SHA-256、ライセンスを`sourceAttributions`へ含める。
- 同じ入力から2回生成して同一ハッシュになることを確認する。
- 風ぐるま乗換案内を版固定したGeoJSONのビルド時読込へ切り替える。
- `kazaguruma.home-shortcut`タグからショートカットを静的生成する。

## Phase 4: 継続更新

- WAMは年2回の公式公開後に確認する。
- OSMは現在・過去の型付きIDを一括確認し、必要時だけ範囲候補を取得する。
- QID検索結果から同定した最新OSM座標を正本geometryへ反映する。
- 町名GeoJSONは版を固定し、四半期または必要時だけ更新する。
- Place削除や`inactive`への恒久変更はLLM合議だけで行わない。
- 正本を保持した`review_hold`への一時掲載停止は、合議と決定的検証で行える。

## 自動化の頻度

| 対象 | 最短頻度 |
|---|---|
| 障害福祉データ | 年2回の公式公開後 |
| OSM既知施設 | 四半期または手動 |
| 町名GeoJSON | 四半期または手動 |
| 依存関係更新 | 月1回 |
| LLM合議 | 入力または外部ソースに意味差分がある時だけ |
