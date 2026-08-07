# データソースと利用条件

このrepositoryは由来と条件の異なるデータを組み合わせる。機械可読な台帳は [`config/sources.json`](config/sources.json)、公開物に実際に寄与したソースは`dist/public/places.geojson`の`sourceAttributions`を参照する。

## プロジェクトのデータベース

データベースはOpen Data Commons Open Database License 1.0で提供する。全文は[`LICENSE`](LICENSE)を参照する。

- License: Open Data Commons Open Database License 1.0
- URL: https://opendatacommons.org/licenses/odbl/1-0/

外部由来のデータには以下の各条件も適用される。個別ソースの条件をプロジェクトの包括ライセンスだけで置き換えない。

## OSM (OpenStreetMap)

- 出典: © OpenStreetMap contributors
- URL: https://www.openstreetmap.org/copyright
- License: Open Data Commons Open Database License 1.0
- License URL: https://opendatacommons.org/licenses/odbl/1-0/
- 加工: 千代田区内の対象候補を抽出し、同定済み施設の代表Point座標として利用

取得・照合手順は[保守仕様](docs/reference/data-maintenance-spec.md)に記載する。

## Wikidata

- URL: https://www.wikidata.org/wiki/Wikidata:Licensing
- License: Creative Commons CC0 1.0 Universal
- License URL: https://creativecommons.org/publicdomain/zero/1.0/
- 用途: 以前のOSM同定で同じ地物を指すと確認できたQIDを、次回のOSM検索入力に利用

Wikidata Itemを内部主キーにはしない。

## WAM NET

- 提供: 独立行政法人福祉医療機構
- 配布ページ: https://www.wam.go.jp/content/wamnet/pcpub/top/sfkopendata/
- 帰属表示: WAM NET
- 加工: 相談支援4サービスから東京都千代田区の行を抽出し、同一施設を集約

公式配布ページはオープンデータを「営利目的、非営利目的を問わず二次利用可能なルールが適用されたもの」「無償で利用できるもの」と説明し、掲載データを「利用規約の条件の下、自由にご利用いただけます」と記載している。

ただし、2026年7月29日の確認時点で、そのページ内に独立した規約本文へのリンクは見つからなかった。このrepositoryは架空の規約名やURLを補わず、利用条件欄から配布ページ自体を参照する。

公式配布ZIPそのものはrepositoryやGitHub Actions artifactへ恒久保存しない。取得台帳にはURL、版、取得時刻、content length、SHA-256等を残す。適用に必要な東京都千代田区の抽出rowは`imports/wam/raw.json`へ保持し、そのSHA-256を`imports/wam/retrieval.json`へ記録する。

対象コードは`52`、`53`、`54`、`70`だけである。

## 千代田区町名GeoJSON

- リポジトリ: https://github.com/nawashiro/chiyoda_city_town_geojson
- 元データ・表示: © Linked Open Addresses Japan
- License: Creative Commons Attribution-ShareAlike 4.0 International
- License URL: https://creativecommons.org/licenses/by-sa/4.0/
- 加工: 上流で丁目以降を削除して統合した町名ポリゴンと、施設Pointの包含判定により町名を付与

町名は正本へ書き込まず、公開GeoJSON生成時だけ導出する。町名ポリゴン自体は公開GeoJSONへ含めない。

## 旧データの出典

以下は旧データの来歴表示のために残す。現在の継続取込ソースではない。

### 東京都福祉局 保育所データ

- URL: https://catalog.data.metro.tokyo.lg.jp/dataset/t000054d0000000356/resource/f41234cd-bcf2-46df-90fc-6cc7d8398321
- License: Creative Commons Attribution 4.0 International

### 千代田区 幼稚園データ・公共施設一覧

- 幼稚園: https://catalog.data.metro.tokyo.lg.jp/dataset/t131016d0000000007
- 公共施設一覧: https://catalog.data.metro.tokyo.lg.jp/dataset/t131016d0000000001
- License: Creative Commons Attribution 4.0 International

## 新しいソースを追加するとき

台帳だけを変更しても、公開生成処理へ新しいソースは追加されない。取得、正規化、適用、検証、公開生成、workflow、testsが必要な場合は、同じPull Requestで実装も変更する。

公開物へ実際に寄与したソースは、生成後に次を確認する。

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

各`sourceAttributions`の`version`、`retrievedAt`、`sha256`は、対応する取得台帳と照合する。旧データの出典は履歴情報であり、現在の取得対象や公開物への寄与を意味しない。旧ソースを削除する場合は、正本、公開生成物、テスト、台帳に参照が残っていないことを確認する。

同じ変更に次を含める。

1. `config/sources.json`への登録
2. 出典URLと確認できた利用条件URL
3. 取得日時または固定版
4. 抽出・変換内容
5. 必要な帰属表示
6. raw snapshotまたは保持しない理由と検証可能なhash
