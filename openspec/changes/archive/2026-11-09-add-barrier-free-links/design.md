# Design

## Context

`data/places.jsonld` は各Placeに `schema:geo` と `rdfs:seeAlso`（公式OSM/Wikidata URIのみ、`facility_data.py` で強制）を持つ。人手確定の関連付けは `fac assoc`（`resolve_osm_candidates.py` 由来のCLI）で行う流儀が既にある。`@context` は `schema` / `rdfs` を宣言済み。

## Goals / Non-Goals

**Goals:**

- 人が検証した案内ページリンクの記録・解除・公開（実施者はbot、誤りは人の訂正で反映）
- リンクデータのdomain制約とバリデーション

**Non-Goals:**

- 自動照合（対応表の自動生成は行わない。特定と登録は施行者が一回きりで判断する）
- 同ソースのトイレマップ対応（数が多く別検討）
- ソース本文のデータ取り込み。`data/sources.json` へのソース追加（リンク掲載のみでデータ消費なし）
- `rdfs:seeAlso` の緩和

## Decisions

- **語彙は `schema:subjectOf`**。「このPlaceについてのWebPage」のproperty定義と正確に一致。`schema:sameAs` は同一性の主張になり誤り、`rdfs:seeAlso` は既に公式ID専用の制約を持ち緩めたくない。`schema:hasMap` は地図サービスへのリンク向けで、言葉の道案内（文章の道順）には適さない。lwd.tokyoも「バリアフリー情報のWebPage」として扱う
- **`schema:WebPage` ノードに `url` / `name` / `provider` を機械的に持たせる**。provider（Organization）はソース定数から付与し、人の入力はURLのみ。nameは表示用途のラベルでソース定数から付与
- **`fac link` サブコマンド**。`fac in` はOSM検索入力専用、`fac assoc` はOSM照合確定専用で意味が違う。解除は `fac link rm`。既存のJSON-LD読み書き経路（`facility_data.py`）を使い、書き換えは既存チェクスル経由で行う
- **URL検証はdomainのprefix一致**（`https://walkingnavi.com/…`、`https://www.lwd.tokyo/…`）。検索トップページ等の施設単位でないページも構造上は区別できないため、スペックはドメインのみ制約する。誤対応もドメイン内なら受理されるので、正しさは施行者の判断と人の訂正ループ（指摘→`fac link rm`→再入力）で担保する
- **運用モデル**：関連付けの施行者はChiyoda-Dev（bot）。対応表をリポジトリに残さず、登録結果をissue #67に報告し、誤りはそこで指摘を受けて訂正する

## Risks / Trade-offs

- [lwd.tokyoの `#:~:text=` フラグメントがサイト側の文言変更で壊れる] → リンク切れ検知は別課題とし、このchangeでは導入しない
- [Test-fragmentの `#` とJSONのエスケープの混淆] → URLは文字列としてそのまま保持し、エンコード変換しない
- [name/providerのラベルがソース側変更で陳腐化] → リンクの機能性には影響しない。陳腐化したら一括で差し替え可能な定数として保持
