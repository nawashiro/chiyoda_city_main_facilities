# Design

## Context

現状の公開物は`site/places.jsonld`で、正本`data/places.jsonld`に画像を足して作る。カテゴリ名は`site/category-names.jsonld`へ複製し、旧`site/categories.jsonld`は生成も参照もされないまま残っている。正本のPlaceは`schema:identifier`に`gif-poi`コードを持ち、判断は`data/categories.json`にある。語彙の正本`data/category-names.jsonld`はHTTP term URLの`DefinedTermSet`で、公開物と一体ではない。

`site/places.jsonld`はビルドだけでなく、`assoc`、`link`、`in rm`、保留、`category assign`/`clear`/`refresh`も書き換える。このため、公開グラフにカテゴリや形状を足すと、部分更新で欠落する経路が増える。プロジェクトは標準ライブラリだけで動き、RDF/SHACLの実行系は持っていない。外部のkazaguruma-transitは`gif-poi`識別子を読んでいる。

本変更は、正本と公開物を分けたまま、公開物だけを自己完結したグラフにする。方針はユーザー決定に従う。すなわち、ビルド時マージ、Placeの`gif-poi`識別子の削除、カテゴリの`schema:keywords`参照、UUID識別、公開物の`dataset.jsonld`への改名、`site/`のGit管理、Releaseによる版固定である。

## Goals / Non-Goals

**Goals:**

- 公開JSON-LD一文書で、Place、カテゴリ語彙、record形状を取得できる。
- カテゴリをHTTP URIではなくUUIDで識別し、人間用の名前とGIF-POIコードをtermに持たせる。
- Placeのカテゴリを属性として複数参照できる。
- 画像作者の必須・任意を含むrecord契約を機械可読にする。
- 公開物の書き込みをビルドだけに集約し、正本と判断記録を操作するCLIと分離する。
- 別ファイルのカテゴリ公開と旧`categories.jsonld`を除去する。

**Non-Goals:**

- CIにSHACL実行系（pyshacl/rdflib）を追加すること。形状は公開契約とし、既存のPython検証と形状の構造テストで支える。
- `site/v1/...`のようなURLパス版管理。版固定はRelease資産で行う。
- カテゴリ判断の規則・Jev・保留の意味論の変更。
- `places.jsonld`の互換エイリアス維持。
- 外部kazaguruma-transitの変更。移行は利用側の作業として文書化する。
- `schema:keywords`以外の専用カテゴリプロパティの導入。

## Decisions

### Public graph is composed at build time and named dataset.jsonld

`data/places.jsonld`はPlaceだけの正本として維持する。`data/category-vocabulary.jsonld`と`data/dataset-shape.jsonld`をソースにし、ビルドがPlace、カテゴリ語彙、形状を`site/dataset.jsonld`の一つの`@graph`へ合成する。正本はビルドで書き換えない。

```text
data/places.jsonld ──────────────┐
data/category-vocabulary.jsonld ─┼─ build ─> site/dataset.jsonld
data/dataset-shape.jsonld ───────┘           @graph = Place*, DefinedTermSet,
data/categories.json ──────────────────────>         DefinedTerm*, NodeShape*
```

`@graph`の順序はPlace（正本順）、`DefinedTermSet`、`DefinedTerm`（コード順）、形状（固定順）に固定する。`@context`は正本の`schema`と`rdfs`に`sh`を足す。公開物は`site/`配下でGit管理し、Release資産は`dataset-<版>.jsonld`、`osm-<版>.json`、`wikidata-<版>.json`の3つにする。

正本まで一つのグラフにする案（カテゴリtermを`data/places.jsonld`へ移す）は採らない。Placeだけを読む既存CLIの前提を壊し、語彙の編集と施設の編集を同じファイルに混ぜるためである。公開物の自己完結にはビルド時合成で足りる。

### Categories are attributes referencing DefinedTerm nodes

Placeは`schema:keywords`でカテゴリtermを参照する。複数値を許し、Placeの`@type`は`schema:Place`のままにする。

```json
{
  "@id": "urn:uuid:<place>",
  "@type": "schema:Place",
  "schema:keywords": [
    { "@id": "urn:uuid:<category-0702>" },
    { "@id": "urn:uuid:<category-0703>" }
  ]
}
```

```json
{
  "@id": "urn:uuid:<category-0702>",
  "@type": "schema:DefinedTerm",
  "schema:name": "寺院",
  "schema:inDefinedTermSet": { "@id": "urn:uuid:<category-set>" },
  "schema:identifier": {
    "@type": "schema:PropertyValue",
    "schema:propertyID": "gif-poi",
    "schema:value": "0702"
  }
}
```

`schema:additionalType`は使わない。これは`rdf:type`の下位プロパティで、値は「属するクラス」を指す。カテゴリを属性として持つ今回のモデルとは逆向きになる。禁止条項は仕様変更の名残なので削除するが、カテゴリの器には採用しない。

カテゴリを`@type`へ入れる案も採らない。地物がカテゴリに属する表現になり、複数カテゴリが型の多重継承に見える。専用プロパティを新設する案は、語彙IRIの管理を増やす。`schema:keywords`は`Place`に使え、値に`DefinedTerm`を取れる標準の属性であり、今回の要件に足りる。

### Category identity is UUIDv5 derived from the GIF-POI code

カテゴリtermの`@id`は`urn:uuid:`とし、プロジェクト固定のUUID名前空間と`gif-poi:<4桁コード>`からUUIDv5を導出する。集合ノードは同じ名前空間の固定名から導出する。ソースには導出済みのUUIDを書き、検証器が導出結果と一致することを確認する。

```text
term @id   = urn:uuid:uuid5(namespace, "gif-poi:" + code)
set  @id   = urn:uuid:uuid5(namespace, "category-vocabulary")
```

UUIDv7の採番台帳は採らない。カテゴリにはGIF-POIコードという自然キーがあり、名前ベースUUIDで安定に導出できる。HTTP term URLはサイトURLの変更で壊れ、PlaceのURN方針とも揃わない。`urn:gif-poi:<code>`はIANA登録NIDではないため、標準準拠のURNとして採用しない。

コードが変わればUUIDも変わる。GIFの版更新でコードの意味が変わる場合は、同じカテゴリの付け替えではなく新しいtermとして扱う。名前空間の定数を変えることは公開識別子の破壊的変更であり、変更しない。

### Vocabulary source is a non-public JSON-LD graph

`data/category-vocabulary.jsonld`は`@graph`に一つの`schema:DefinedTermSet`と採用カテゴリの`schema:DefinedTerm`を持つ。集合は`schema:hasDefinedTerm`でtermを列挙し、termは`schema:inDefinedTermSet`で集合を指す。各termはUUID、`schema:name`、`gif-poi`の`schema:identifier`を持つ。

このソースは公開しない。`site/category-names.jsonld`への複製、landing pageのカテゴリ`DataDownload`、Release資産`category-names-<版>.jsonld`を廃止する。旧`site/categories.jsonld`も削除する。ソースは人が編集するが、GIFへの出典URL・ライセンス表示・判断method・翻訳規則は持たない。出典はlanding pageの`schema:Dataset`に残す。

集合とtermを`@graph`のトップレベルに置くのは、ビルドがそのまま公開`@graph`へ追加でき、利用者が型でtermを抽出できるためである。集合にtermをインラインで持つ案は、公開時に平坦化が必要で、ソースと公開物の構造がずれる。

### Record shape is published as SHACL in the same graph

`data/dataset-shape.jsonld`にSHACLの`sh:NodeShape`を置き、ビルドが公開`@graph`へ追加する。Place形状は`schema:Place`を対象に、`schema:geo`必須・単一、`schema:image`任意・単一、`schema:image`の`schema:contentUrl`と`schema:license`必須、`schema:creator`任意・単一、`schema:creator`がある場合の`schema:name`必須、`schema:keywords`の各値が`schema:DefinedTerm`であることを表す。カテゴリterm用の形状は`schema:DefinedTerm`を対象に、UUID、名前、GIF-POI識別子を必須にする。

```json
{
  "@type": "sh:NodeShape",
  "sh:targetClass": { "@id": "schema:Place" },
  "sh:property": [{
    "sh:path": { "@id": "schema:image" },
    "sh:maxCount": 1,
    "sh:node": {
      "@type": "sh:NodeShape",
      "sh:property": [
        { "sh:path": { "@id": "schema:contentUrl" }, "sh:minCount": 1 },
        { "sh:path": { "@id": "schema:license" }, "sh:minCount": 1 },
        { "sh:path": { "@id": "schema:creator" }, "sh:maxCount": 1,
          "sh:node": { "@type": "sh:NodeShape",
            "sh:property": [{ "sh:path": { "@id": "schema:name" }, "sh:minCount": 1 }] } }
      ]
    }
  }]
}
```

OWLの cardinality 制約は推論用で、欠落の検出には向かない。JSON SchemaはJSONの直列形には強いが、RDFのクラスとプロパティの意味を表せない。SHACLはRDFのままクラス・ cardinality・入れ子を表せ、同じ`@graph`に置ける。

CIの完全なSHACL検証は行わない。pyshacl/rdflibの追加は標準ライブラリ中心の構成とKISSに反するため、既存のPython検証器を公開物の実行検証に残し、形状の主要制約（geo必須、image単一、creator任意・name必須、keywordsの型）をテストで固定する。形状は公開契約であり、利用者は自分のSHACL実行系で検証できる。形状とPython検証の乖離は、このテストと仕様で抑える。将来、依存を許容できるならpyshaclを追加して完全検証へ移す。

### Only the build writes the published graph

`build_repository`だけが`site/dataset.jsonld`を書く。`assoc`、`link`、`in rm`、保留、`category assign`/`clear`/`refresh`は`data/places.jsonld`と判断記録だけを更新し、公開物を書かない。公開物は次のビルド（Pages workflowまたは手動`./fac build`）で合成する。

```text
CLI ─> data/places.jsonld, data/categories.json, data/osm-decisions.json
build ─> site/dataset.jsonld
```

公開物をCLIが部分更新すると、カテゴリtermや形状を落としたグラフを配布し得る。書き手をビルドに一本化すれば、合成順序と検証も一箇所に閉じる。`update-osm.yml`はビルド後に`site/dataset.jsonld`を検証し、Pages workflowは常にビルドから配布する。

`jsonld-validate`は正本用と`--published`用に分ける。正本検証はPlaceだけを見て、`gif-poi`識別子が残っていれば失敗する。公開検証は`@type`でPlace、DefinedTerm、NodeShapeを分岐し、Placeの`schema:keywords`がグラフ内のtermを指すこと、termのUUID・コード・名前、形状の存在を確認する。

### Data migration uses a one-time dedicated CLI path

正本の`schema:identifier`から`gif-poi`を除去し、語彙ソースを新形式へ変換する一度きりの移行は、`./fac`に一時的な移行サブコマンドを追加して行う。アドホックスクリプトで`data/`を直接書き換えない。移行コマンドは入力を検証し、語彙のUUID導出、コード識別子、正本の識別子除去を一度に行い、成功後に削除する。

判断記録`data/categories.json`はコードのまま変えない。ビルドがコードからterm UUIDを引き、Placeの`schema:keywords`を組み立てる。関連付けが変わった施設の判断を公開しない既存の`stale_facilities`判定はビルドでも使う。

## Risks / Trade-offs

- [kazaguruma-transitが`gif-poi`識別子を読めなくなる] → 破壊的変更として文書化し、`schema:keywords`からtermの`schema:identifier`を辿る移行を示す。過去のRelease資産は残る。
- [SHACL形状とPython検証が乖離する] → 形状の主要制約をテストで固定し、仕様を契約の正とする。完全検証が必要になったらpyshacl導入を別変更で行う。
- [UUIDv5の名前空間定数を変えると全カテゴリ識別子が変わる] → 定数をコード内の固定値として扱い、変更を破壊的変更と明記する。
- [ビルドの合成順序が揺れる] → Place、集合、term、形状の順序を固定し、公開物のテストで比較する。
- [`schema:keywords`は将来の一般タグと区別できない] → 値がカテゴリ集合の`DefinedTerm`であることを形状と語彙で示す。専用プロパティが必要になったら別変更で検討する。
- [`site/places.jsonld`の既存URLが404になる] → landing pageとRelease資産の新URLへ誘導する。互換エイリアスは二重配布になるため置かない。
- [移行中に正本と判断記録がずれる] → 移行CLIで正本・語彙・判断をまとめて検証し、移行後に全テストとビルドを通す。
- [語彙追加時にUUIDを手計算する] → `jsonld-validate`が期待UUIDを示す。追加が頻繁になったら語彙操作用CLIを別変更で追加する。

## Migration Plan

1. 新しい語彙ソース`data/category-vocabulary.jsonld`と形状ソース`data/dataset-shape.jsonld`の形式、検証、ビルド合成を実装する。
2. 一度きりの移行サブコマンドで、旧`data/category-names.jsonld`をUUID付き語彙へ変換し、`data/places.jsonld`から`gif-poi`識別子を除去する。判断記録は変更しない。
3. CLIの`assoc`、`link`、`in rm`、保留、`category assign`/`clear`/`refresh`から公開物への書き込みを外し、判断記録だけを更新する。
4. `site/dataset.jsonld`のビルド、正本／公開検証、landing page、Release資産、`update-osm.yml`、`validate.yml`を新名称へ揃える。旧`site/places.jsonld`、`site/category-names.jsonld`、`site/categories.jsonld`を削除する。
5. テスト、ドキュメント、出典表示を更新し、`./fac build`で`site/dataset.jsonld`を生成して検証する。
6. 移行サブコマンドを削除する。Releaseを作成し、資産名と利用側の移行を確認する。

ロールバックは、変更前のコミットへ戻し、旧`site/places.jsonld`を再ビルドして配布する。過去のRelease資産は不変のまま残る。
