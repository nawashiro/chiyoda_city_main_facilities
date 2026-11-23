# Proposal

## Why

`Update OpenStreetMap data`の`process` jobは実測7分14秒かかり、うち6分40秒をPBF抽出が占めます。近傍検索は2026-08-07の`4975568`で空間インデックス化済みなので、これをgeohash近傍に置き換えても短縮は数秒です。実際の費用は、東京全体の17,870,590ノードと3,140,576 wayすべてについて`dict(element.tags)`を作っていることで、これが約220秒を消費しています。選択され得ない要素のタグを辞書化しなければ、同じ抽出結果のまま処理時間を約3分の1にできます。

## What Changes

- 要素が選択条件（既存ID、検索座標から50m以内、Wikidata一致）を満たすかを、座標と軽量なタグ照会で先に判定します。
- `dict(tags)`は、実際に選択された要素にだけ作ります。候補判定に必要な`wikidata`の照会は`TagList.get`で行い、辞書化しません。
- 50m以内の照合は既存の`coordinate_matcher`を維持します。位置による早期足切りは、検索座標から導いた領域と既存の`CHIYODA_BBOX`の和で行い、どちらの選択規則も取りこぼしません。
- wayもnodeと同じ判定順に揃えます。relationは現行のままにします（走査が2秒で、タグ辞書化がボトルネックになっていないため）。
- 選択結果が変わらないことを、選択境界のユニットテストと同一PBFでの出力比較で確認します。

## Capabilities

### New Capabilities

なし。

### Modified Capabilities

なし。選択規則も抽出物も変えず、処理時間だけを変えるため、仕様差分はありません（`.openspec.yaml`の`skip_specs: true`で明示）。

## Impact

- `src/osm_mirror.py`の`extract_elements`（node/wayハンドラの判定順）
- `tests/test_osm_retrieval.py`（選択境界のテスト追加）
- 依存パッケージ、PBFの取得元、`imports/`の保持物、Pages配信物は変更しません
