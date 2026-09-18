# Placeを1件編集する

この手順の範囲は、`data/places.jsonld`の既存Placeオブジェクトを1件だけ直接編集し、検証済みのPull Request（PR）を準備することです。merge、公開、Releaseは範囲外です。

## 1. 作業ツリーを確認してbranchを作る

編集前に作業ツリーを確認します。

```bash
git status --short
```

出力が1行でもあれば停止します。出力がない場合だけbranchを作ります。

```bash
git switch -c data/<作業内容>
```

## 2. UUIDで対象Placeを1件に絞る

実在するUUIDを`urn:uuid:<UUID>`形式で指定し、`@id`を完全一致で検索します。名前だけで検索しません。

```bash
UUID='urn:uuid:<実在するUUID>'
MATCHES=$(grep -F -c "\"@id\": \"${UUID}\"" data/places.jsonld)
test "$MATCHES" -eq 1 || { printf '対象Placeが1件ではありません。\n' >&2; exit 1; }
```

一致したPlaceの`@id`と外部識別子を確認します。出典または確認資料の人間可読な施設名と照合できない場合は停止します。`@id`は変更しません。

## 3. Placeを編集する

```bash
$EDITOR data/places.jsonld
```

対象Placeの既存キーの通常値を先に編集します。対象Place以外を編集しません。予定外のキーを追加、削除、改名しません。

### Geometryを変更する場合だけ

`geo:hasGeometry.geo:asGeoJSON.@value`をJSON文字列のまま保ちます。`@type`は`geo:geoJSONLiteral`のままにします。

```json
"@value": "{\"type\":\"Point\",\"coordinates\":[139.75,35.69]}"
```

`coordinates`は必ず`[経度, 緯度]`の順序にします。GeoJSON文字列を通常のJSONオブジェクトへ変換しません。

### 外部識別子を変更する場合だけ

`schema:identifier`は`schema:PropertyValue`の配列にします。各要素の`schema:propertyID`と`schema:value`は文字列にします。出典で確認できない識別子や、推測したURLを追加しません。

## 4. 差分を対象Placeだけに限定する

```bash
git diff -- data/places.jsonld
```

対象Placeの意図した値だけが変わり、`@id`が変わらないことを確認します。他のPlace、整形差分、空白・改行・キー順の変更、予定外キー、GeoJSON文字列のエスケープ変更が差分にあれば停止します。

## 5. 検証してPRを作る

次のコマンドを上から順に実行します。

```bash
python3 -m src.fac_cli jsonld-validate data/places.jsonld
python3 -m src.facility_data validate .
python3 -m unittest discover -s tests -v
git diff --check
```

失敗した場合はPRを作りません。全コマンドが成功し、差分が対象Placeだけであることを確認してから、対象ファイルをcommitしてPull Requestを作成します。この手順はPull Request作成で終了し、merge、公開、Releaseを含めません。
