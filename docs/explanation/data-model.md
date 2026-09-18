# データモデル

このrepositoryは、施設データを次の層に分けます。

- 検索入力: [`inputs/osm-search/human/202608.json`](../../inputs/osm-search/human/202608.json) などが、OSM候補を探すための名称、識別子、座標を保持します。
- 取得スナップショット: [`imports/openstreetmap/normalized.json`](../../imports/openstreetmap/normalized.json) と [`imports/wam/normalized.json`](../../imports/wam/normalized.json) が、外部データの正規化結果を保持します。取得スナップショットは、取得元のrawデータと取得メタデータも保持します。
- canonical JSON-LD: [`data/places.jsonld`](../../data/places.jsonld) が公開Placeの正本です。保守者はこのファイルを直接編集します。
- Pagesのcurrent JSON-LD: [`site/places.jsonld`](../../site/places.jsonld) が、GitHub Pagesで配布する現在版です。これはcanonical JSON-LDと同じバイト列です。
- Release snapshot: [`release-jsonld.yml`](../../.github/workflows/release-jsonld.yml) が、canonical JSON-LDを版付きのJSON-LDファイルとしてGitHub Releaseへ添付します。準備処理は [`prepare_release_jsonld.py`](../../scripts/prepare_release_jsonld.py) が担当します。

入力と取得スナップショットは判断の材料です。canonical JSON-LDだけが公開Placeの編集対象です。PagesとReleaseはcanonical JSON-LDから作る配布物です。

## canonical JSON-LDの構造

`data/places.jsonld`は、JSON-LD 1.1の`@context`と`@graph`を持ちます。`@context`は、次の標準語彙を宣言します。

```json
{
  "@version": 1.1,
  "schema": "https://schema.org/",
  "geo": "http://www.opengis.net/ont/geosparql#",
  "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
}
```

`@graph`の各recordは、次の構造を持ちます。

- `@id`は、既存のUUIDを`urn:uuid:<uuid>`として表します。ドメイン名やリダイレクトに依存しない安定した施設識別子です。
- `@type`は、`schema:Place`と`geo:Feature`を同時に持ちます。前者は施設を表し、後者は地理空間の対象であることを表します。
- `geo:hasGeometry`の下に、GeoSPARQLの`geo:asGeoJSON`と`geo:geoJSONLiteral`を置きます。リテラルは経度、緯度の順のPoint座標を持ちます。
- `schema:identifier`は、外部recordの識別子を配列で表します。各要素は`schema:PropertyValue`です。

`schema:PropertyValue`は、`schema:propertyID`にソース識別子を、`schema:value`にソース側のrecord IDを設定します。たとえば、OSMの`node/…`やWAMのrecord IDを、施設の内部IDと混同せずに保持します。

## 関連リンクの扱い

`rdfs:seeAlso`は、ソース入力に明示された解決可能なURIがある場合だけ使う任意の関連リンクです。record IDからURIを推測または生成しません。明示的なURIがない外部recordは、`schema:PropertyValue`だけで表します。

この方針は、自動照合の結果を施設と外部recordの同一性として断定しないために採用します。現在の公開recordに関連リンクがない場合も、空のリンクを追加しません。

## 公開recordから除く情報

公開Placeは、識別子、型、Point、外部識別子、必要に応じた関連リンクだけを保持します。次の情報は公開recordへ入れません。

- `audit`、`history`、変更・参照の履歴、投票ログ（`voteLog`）などの運用情報
- `town`（町名）、`phone`（電話番号）、`images`（画像）
- 独自の`categoryIds`

Gitのcommit、Pull Request、Release snapshotが変更の履歴を保持します。公開JSON-LDへ監査用の履歴を複製せず、Gitを履歴の正本として扱います。

## 配布と検証

GitHub PagesのDataset landing pageは、[current JSON-LD](https://nawashiro.github.io/chiyoda_city_main_facilities/places.jsonld)への取得先を案内します。landing page本体は [`site/index.html`](../../site/index.html) です。Release snapshotは、特定の版を引用するための不変な取得単位です。

canonical JSON-LDの構文、識別子、Point、外部識別子は [`src/facility_data.py`](../../src/facility_data.py) の検証処理で確認します。編集後は、次のコマンドでcanonical JSON-LDを検証してからPagesとReleaseへ配布します。

```bash
python3 -m src.fac_cli jsonld-validate data/places.jsonld
```
