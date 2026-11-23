# Design

## Context

See [proposal.md](proposal.md)のWhy/What Changes。ここでは現状の抽出構造と、選んだ順序だけを扱います。

`extract_elements`は同じPBFを3回走査します。`RelationDependencies`（relationのみ）、`Geometry`（node/way、`locations=True`の`flex_mem`索引）、`Relations`（relationのみ）です。実測は手元で0.9秒、353.4秒、2.0秒でした。`Geometry`の内訳は、17,870,590ノードの`dict(node.tags)`が約220秒、Pythonコールバックの基礎が約32秒、`locations`索引とwayの再構成が約24秒、残りがwayのタグ辞書化と近傍判定です。

選択規則は`include`の3つだけで、追加の規則はありません。

1. typed IDが`selected_ids`にある
2. `wikidata`タグが`qids`にあり、中心が`CHIYODA_BBOX`の内側
3. 中心が検索座標から50m以内（`coordinate_matcher`で判定）

2はbbox内でしか成立せず、3は50m以内でしか成立しません。ならば、どちらの可能性もない要素はタグを読む前に捨てられます。

## Goals / Non-Goals

**Goals:**

- 同じPBFと同じ入力に対し、抽出結果を変えずに`Geometry`のタグ辞書化を選択要素だけに限定する
- ノード数・way数が今後増えても効く形にする（要素数に対して線形のまま、定数項を下げる）

**Non-Goals:**

- `osmium-tool`によるbbox事前切り出し（依存追加とrelation中心の再現性検証が必要）
- PBF読み込みの並列化、取得元・頻度の変更
- relationハンドラの最適化（走査2秒で辞書化がボトルネックでない）

## Decisions

### 判定順を「ID → 位置 → Wikidata → 辞書化」にする

`Geometry`のnode/wayハンドラで、まず選択可能性を判定し、選択が確定した要素だけ`dict(element.tags)`を作ります。候補判定に必要な`wikidata`は`TagList.get("wikidata")`で引き、辞書化しません。

- 代替案: geohash近傍の再実装。近傍照合は`coordinate_matcher`で既にO(1)で、効果は数秒。却下。
- 代替案: `osmium-tool`で千代田bboxに切り出してから走査。抽出は20〜30秒台になる見込みだが、実行環境への依存追加と、relationの中心計算がメンバー欠落で変わり得る検証コストが増える。今回の目的（同じ結果で待ち時間を減らす）には過剰なので却下。

### 早期足切りは検索座標由来の領域と`CHIYODA_BBOX`の和で行う

50m規則の可能性がある領域は、検索座標のmin/maxを50m超（この緯度で0.001度）広げた矩形です。50m規則の最終判定は従来どおり`coordinate_matches`に任せ、矩形は「候補になり得ない」ことの証明にだけ使います。座標が1件もない場合は矩形を作らず、50m規則は常に偽になります。Wikidata規則の可能性は`CHIYODA_BBOX`で判定します。ノードは両矩形の外側なら`coordinate_matches`も呼ばずに捨てます。

これで、検索座標が`CHIYODA_BBOX`のどこにあっても、現在の選択規則を1件も落としません。固定bboxの内側50m以上に座標があるという暗黙の前提を持ち込まずに済みます（現状の最小余白は416mだが、入力追加で壊れ得るため）。

wayは中心を出すためにnode位置の参照が必要なので、`locations=True`の走査と`_merge_bounds`は維持します。タグ辞書化だけを、選択済み・`CHIYODA_BBOX`内・50m以内のいずれかに限定します。

### 判定ロジックは1つのヘルパーに集約する

`include`を「タグ辞書を受け取って真偽を返す」関数から、`selection_predicate(...)`が返す`selectable(kind, identifier, center, wikidata)`へ変えます。`wikidata`は遅延評価できる呼び出し可能オブジェクトで、`(kind, identifier) in selected_ids`、`inside(query_region, center) and coordinate_matches(...)`、`inside(chiyoda, center) and wikidata() in qids`の順に評価します。真なら呼び出し側が`dict(element.tags)`を作って`selected`へ格納します。

`selection_predicate`はモジュールレベルに置き、`selected_ids`、`qids`、`query_region`、`chiyoda_bbox`、`coordinate_matches`を受け取って`selectable`を返します。PBFなしで境界テストを書けるようにするためです。relationはこのヘルパーを使いつつ、現行どおり`dict(relation.tags)`を先に作ります（2秒の走査で支配的でないため、挙動を変えない）。

### 同一性はテストと実データ比較の二段で確認する

- 境界テスト: 50mの内外、`CHIYODA_BBOX`の内外、bbox外のtyped ID、bbox外の`wikidata`一致、query領域外だが50m以内の座標（領域の余白が50m超であることの確認）
- 実データ比較: 変更前後で同じPBFを抽出し、`imports/openstreetmap/raw.json`の要素集合と各要素のtagsが一致することを確認する

## Risks / Trade-offs

- [早期足切りの矩形が狭すぎて候補を落とす] → 矩形は50mより十分広い0.001度（緯度約111m、経度約90m）で、最終判定は`coordinate_matches`。境界テストと同一PBF比較で確認する
- [`TagList.get`と`dict.get`で結果が違う] → OSMのタグキーは一意で、欠落時はどちらも`None`。対象要素の判定に使うキーは`wikidata`のみ
- [wayの中心が矩形外でもノードが矩形内、という取りこぼし] → 早期足切りは中心に対して行い、中心を出すためのnode位置参照は従来どおり全wayで行う。ノード側の判定とは独立
- [CIで短縮が再現しない] → 抽出の開始・終了ログで前後を比較し、3分以内を確認する。再現しない場合は`dict(way.tags)`の残りを切り分ける

## Migration Plan

データ変更はありません。コードとテストのみを変更し、`imports/`と公開物は同じ内容のままです。問題があれば当該コミットをrevertします。
