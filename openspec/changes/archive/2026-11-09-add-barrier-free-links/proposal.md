# Proposal

## Why

区の施設には、バリアフリー観点で作られた第三者の案内ページ（言葉の道案内、東京バリアフリーマップ）がある。再利用者がこれらへたどれる関連情報として、施設単位のページへのリンクが無い。

## What Changes

- 公開Placeに `schema:subjectOf` として `schema:WebPage`（url, name, provider）を出力する。リンク掲載のみで、WebPage本文のデータは取り込まない（両ソースとも「全権利所有」とのため）
- 対応ソースは言葉の道案内（walkingnavi.com、施設単位ページ `https://walkingnavi.com/list_route.php?grp=5&no=57`）と東京バリアフリーマップ（lwd.tokyo、`#:~:text=` テキストフラグメントディープリンク）の2つ。同ソースのトイレマップは対象外（数が多く別検討、Non-goal）
- 対応付けの入力は `fac` サブコマンド（`link`）1本。実行時の自動照合は行わない
- 実装後、Chiyoda-Dev が両ソースの該当施設を特定し、`fac link` で関連付けまで実施する。対応の誤りは人が指摘し、`fac link rm` と再入力で訂正する
- `facility_data.py` のバリデーションに `subjectOf` のdomain制約を追加する。`rdfs:seeAlso` の現行制約（OSM/Wikidata公式URIのみ）は緩めない

## Capabilities

### New Capabilities

- `barrier-free-links`: 公開Placeへのバリアフリー案内ページ（schema.org WebPageサブジェクト）の関連付け（実施者はbot、誤りは人の訂正で反映）と、その検証・公開

### Modified Capabilities

（なし。`rdfs:seeAlso` と `related-record-links` の要件は変更しない）

## Impact

- `src/fac_cli.py` — `link` サブコマンド追加
- `src/facility_data.py` — `schema:subjectOf` の読み書き検証
- `data/places.jsonld` — 関連付け実施時に `subjectOf` を付与
- コメントID: nawashiro/chiyoda_city_main_facilities#67（進捗報告先）
- 公開JSON-LDの `@context` は既に schema 語彙を宣言済みで、新propertyはcontext変更不要
