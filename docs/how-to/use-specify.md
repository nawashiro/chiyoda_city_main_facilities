# OpenSpec changeを使って正本JSON-LDを変更する

このハウツーは、OpenSpec changeを移行の判断記録として読み、小さな正本変更を安全に完了する手順です。

## OpenSpec changeを移行の判断記録として読む

移行の目的、設計判断、検証可能な契約、実装順序は、`adopt-standards-jsonld` changeにまとまっています。
このchangeを移行の判断記録（decision record）として扱います。

- [proposal.md](../../openspec/changes/adopt-standards-jsonld/proposal.md): 移行の目的、範囲、互換性の判断
- [design.md](../../openspec/changes/adopt-standards-jsonld/design.md): 正本、語彙、履歴、配布の設計判断
- [public-jsonld-datasetのspec](../../openspec/changes/adopt-standards-jsonld/specs/public-jsonld-dataset/spec.md): Placeとgeometryの要件
- [related-record-linksのspec](../../openspec/changes/adopt-standards-jsonld/specs/related-record-links/spec.md): 外部識別子と関連リンクの要件
- [dataset-publicationのspec](../../openspec/changes/adopt-standards-jsonld/specs/dataset-publication/spec.md): Datasetと配布物の要件
- [tasks.md](../../openspec/changes/adopt-standards-jsonld/tasks.md): 実装と検証の進捗

changeの状態と整合性を確認します。

```bash
openspec status --change adopt-standards-jsonld --json
openspec validate adopt-standards-jsonld --strict
```

仕様と実装が一致しない場合、正本データを先に変更しません。
proposal、design、specsを読み直し、判断の境界をレビューで確認します。

## 作業branchと変更前の検証

作業前に、現在の差分とbranchを確認します。

```bash
git status --short --branch
git switch -c data/<作業内容>
```

変更前の正本とrepositoryを検証します。

```bash
python3 -m src.fac_cli jsonld-validate data/places.jsonld
python3 -m src.facility_data validate .
python3 -m unittest discover -s tests -v
```

変更前の検証が失敗した場合、正本を編集せずに原因を解消します。

## 正本JSON-LDを直接編集する

[正本JSON-LD](../../data/places.jsonld)をテキストエディターで直接編集します。

```bash
$EDITOR data/places.jsonld
```

小さな変更では、次の手順を守ります。

1. `@graph`から対象`@id`のrecordを探します。
2. 変更対象のプロパティだけを編集します。
3. `@id`の`urn:uuid:`形式を維持します。
4. `@type`へ`schema:Place`と`geo:Feature`を維持します。
5. geometryの`@value`へPointのJSON文字列を設定します。
6. 座標配列を`[経度,緯度]`の順序で記述します。

geometryを修正する場合、`geo:hasGeometry`以下の構造を維持します。

```json
"geo:hasGeometry": {
  "geo:asGeoJSON": {
    "@type": "geo:geoJSONLiteral",
    "@value": "{\"type\":\"Point\",\"coordinates\":[139.7535624,35.6941626]}"
  }
}
```

外部識別子を追加する場合、`schema:identifier`へ`schema:PropertyValue`を追加します。
`schema:propertyID`と`schema:value`には、空でない出典識別子を設定します。

```json
{
  "@type": "schema:PropertyValue",
  "schema:propertyID": "openstreetmap",
  "schema:value": "node/1420770185"
}
```

編集後に、正本以外のファイルを自動生成しません。

## 変更後の検証

JSON-LDの構文と契約をCLIで検証します。

```bash
python3 -m src.fac_cli jsonld-validate data/places.jsonld
```

repository全体、build、tests、OpenSpec changeを検証します。

```bash
python3 -m src.facility_data validate .
python3 -m src.facility_data build .
python3 -m unittest discover -s tests -v
openspec validate adopt-standards-jsonld --strict
git diff --check
```

いずれかの検証が失敗した場合、差分を確認して修正し、すべての検証を再実行します。

## 差分をレビューしてcommitする

commit前に、対象recordと変更範囲を確認します。

```bash
git status --short
git diff -- data/places.jsonld
git diff --stat
git diff --check
```

次の条件をすべて確認します。

- 意図した`@id`のrecordだけが変わっています。
- 意図したプロパティだけが変わっています。
- JSON-LD以外の不要なファイルが変わっていません。
- 変更後の全検証が成功しています。

確認後に、意図したファイルだけをstageします。

```bash
git add data/places.jsonld
git diff --cached -- data/places.jsonld
git diff --cached --check
git commit -m "data: update canonical JSON-LD"
```

文書も同じ変更に含める場合、文書のpathを`git add`へ明示的に追加します。
commit後に`git show --stat --oneline HEAD`で記録を確認します。

## 関連文書

- [データモデル](../explanation/data-model.md): JSON-LDの役割と標準語彙
- [CLIリファレンス](../reference/cli.md): JSON-LD検証CLIの引数
- [更新チェックリスト](source-update-checklist.md): 更新前後の確認項目
- [最初の施設変更](../tutorials/first-data-change.md): branch、検証、レビューの基本手順
