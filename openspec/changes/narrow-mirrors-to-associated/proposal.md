# Proposal

## Why

`site/mirrors/osm.json` と `site/mirrors/wikidata.json` は公開用ミラーであるにもかかわらず、調査用プールデータがそのまま含まれている。OSM ミラーは 919 要素中 832 要素が places に未紐付け（レストラン・自動販売機等の ±50m 雑多 POI）、Wikidata ミラーは 94 QID 中 50 QID が未紐付け（東日本旅客鉄道の全ステートメント等、1.10 MB / 全体の 59%）。公開配下から見ると内容が「変」であり、(pub) 配布物 の容量も約 2 倍に膨らんでいる。 Root cause は検索入力座標 ±50m の広域抽出（調査用途）が、そのまま公開ミラーへ流れていること。

## What Changes

- **BREAKING**: `site/mirrors/osm.json` の内容を、places.jsonld に紐付けられた OSM 要素のみに絞る。検索入力座標 ±50m の広域抽出・wikidata タグ一致抽出は公開ミラーから除外する
- **BREAKING**: `site/mirrors/wikidata.json` の内容を、places.jsonld が参照する QID のみに絞る
- `imports/openstreetmap/raw.json` / `imports/wikidata/raw.json` は調査プールとして広域抽出を保持し続ける（非公開、Pages 配信対象外）
- 月次 `update-osm` パイプラインで、imports 抽出物のうち紐付け分だけを選別して site/mirrors/ へ書き出す
- 新たに紐付けを追加した際、次回月次更新で自動的にミラーへ反映される

## Capabilities

### New Capabilities

- なし

### Modified Capabilities

- `source-mirrors`: 配布物 MUST の範囲を「抽出された各 OSM 要素」から「.places.jsonld に紐付けられた OSM 要素」に変更、Wikidata 配布物 MUST の範囲を「同定された Wikidata QID それぞれ」から「places.jsonld が参照する QID」に変更。未紐付けデータは調査用 raw に留まることを追加

## Impact

- `src/retrieve_osm.py`・`src/wikidata_retrieval.py`: 公開ミラー用の生成経路に選別を追加
- `.github/workflows/update-osm.yml`: site/mirrors/ への書き出し手順
- `site/mirrors/osm.json`（420 KB → 約 190 KB 弱の見込み）・`site/mirrors/wikidata.json`（3.6 MB → 0.8 MB 弱の見込み）
- 公開ページの licensee LICENSE 表記（ODbL/CC0）の対象範囲は紐付け分のみに縮む
- この変更は完了済み change `add-source-mirrors` の main specs への同期（アーカイブ）を前提とする。未同期のため、apply の最初にその同期を行う
