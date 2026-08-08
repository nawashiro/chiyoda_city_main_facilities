# データソースと利用条件

このrepositoryは由来と条件の異なるデータを組み合わせます。機械可読な台帳は [`config/sources.json`](config/sources.json)、公開物に実際に寄与したソースは[公開GeoJSONファイル](dist/public/places.geojson)の`sourceAttributions`を参照してください。

## プロジェクトのライセンス

このプロジェクトの独自著作物はCreative Commons Attribution-ShareAlike 4.0 Internationalで提供します。全文は[`LICENSE`](LICENSE)を参照してください。

- License: Creative Commons Attribution-ShareAlike 4.0 International
- URL: https://creativecommons.org/licenses/by-sa/4.0/

外部由来のデータには以下の各条件を適用します。個別ソースの条件をプロジェクトのライセンスで置き換えないでください。

## OSM (OpenStreetMap)

- 出典: © OpenStreetMap contributors
- URL: https://www.openstreetmap.org/copyright
- License: Open Data Commons Open Database License 1.0
- License URL: https://opendatacommons.org/licenses/odbl/1-0/

## Wikidata

- URL: https://www.wikidata.org/wiki/Wikidata:Licensing
- License: Creative Commons CC0 1.0 Universal
- License URL: https://creativecommons.org/publicdomain/zero/1.0/

## WAM NET

- 提供: 独立行政法人福祉医療機構
- 配布ページ: https://www.wam.go.jp/content/wamnet/pcpub/top/sfkopendata/
- 帰属表示: WAM NET

公式配布ページはオープンデータを「営利目的、非営利目的を問わず二次利用可能なルールが適用されたもの」「無償で利用できるもの」と説明し、掲載データを「利用規約の条件の下、自由にご利用いただけます」と記載しています。

ただし、2026年7月29日の確認時点で、そのページ内に独立した規約本文へのリンクは見つかりませんでした。利用条件欄から配布ページ自体を参照します。

## 千代田区町名GeoJSON

- リポジトリ: https://github.com/nawashiro/chiyoda_city_town_geojson
- 元データ・表示: © Linked Open Addresses Japan
- License: Creative Commons Attribution-ShareAlike 4.0 International
- License URL: https://creativecommons.org/licenses/by-sa/4.0/

## 旧データの出典

以下は旧データの来歴表示のために残します。現在の継続取込ソースではありません。

### 東京都福祉局 保育所データ

- URL: https://catalog.data.metro.tokyo.lg.jp/dataset/t000054d0000000356/resource/f41234cd-bcf2-46df-90fc-6cc7d8398321
- License: Creative Commons Attribution 4.0 International

### 千代田区 幼稚園データ・公共施設一覧

- 幼稚園: https://catalog.data.metro.tokyo.lg.jp/dataset/t131016d0000000007
- 公共施設一覧: https://catalog.data.metro.tokyo.lg.jp/dataset/t131016d0000000001
- License: Creative Commons Attribution 4.0 International

## 新しいソースを追加するとき

台帳だけを変更しても、公開生成処理へ新しいソースは追加されません。取得、正規化、適用、検証、公開生成、workflow、testsが必要な場合は、同じPull Requestで実装も変更してください。

公開物へ実際に寄与したソースは、生成後に次を確認します。

```bash
python3 -m src.facility_data validate .
python3 - <<'PY'
import json
from pathlib import Path

public = json.loads(Path("dist/public/places.geojson").read_text())
ledger = json.loads(Path("config/sources.json").read_text())
known = {item["id"] for item in ledger["sources"]}
used = {item["sourceId"] for item in public["sourceAttributions"]}
assert used <= known, (used - known)
print("attributed sources:", ", ".join(sorted(used)))
PY
```

各`sourceAttributions`の`version`、`retrievedAt`、`sha256`は、対応する取得台帳と照合します。旧データの出典は履歴情報で、現在の取得対象や公開物への寄与を意味しません。旧ソースを削除する場合は、正本、公開生成物、テスト、台帳に参照が残っていないことを確認します。

同じ変更に次を含めます。

1. `config/sources.json`への登録
2. 出典URLと確認できた利用条件URL
3. 取得日時または固定版
4. 抽出・変換内容
5. 必要な帰属表示
6. raw snapshotまたは保持しない理由と検証可能なhash
