# 施設を保守する

## Placeの分類、タグ、公開状態を変更する

```bash
./fac get <UUID>
./fac set <UUID> --cat library --tag example.tag
./fac set <UUID> --life active --vis public
python3 -m src.facility_data validate .
python3 -m src.facility_data build .
```

`--cat`と`--tag`は配列全体を置き換えます。
既存値を残す場合、先に`./fac get <UUID>`を実行してください。

## 一時的に公開を止める

```bash
./fac set <UUID> --vis private
python3 -m src.facility_data validate .
python3 -m src.facility_data build .
```

`private`は正本に残ります。公開GeoJSONだけから除外します。

## OSM参照を人手で確定する

```bash
./fac ref <UUID> osm way/123456
./fac ref <UUID> osm none
```

`ref`は`human_review`と`human_inference`監査を記録します。
同じ型付きOSM IDを複数Placeへ設定できません。

参照の追加だけでは代表点を変更しません。
保持済みrawを反映するには、commit後に`Re-identify retained source snapshots`を実行してください。

## 検索入力を変更する

```bash
./fac in ls
./fac in get <UUID>
./fac in add "施設名" --lon 139.75 --lat 35.69
./fac in add "施設名" --qid Q12345
./fac in set <UUID> --name "修正後の施設名"
./fac in set <UUID> --lon 139.75 --lat 35.69
./fac in set <UUID> --qid Q12345
```

`--lon`と`--lat`は組で指定してください。
座標は`[経度,緯度]`です。
座標とQIDを切り替えると、以前の検索キーを削除します。

検索入力をcommitした後、対象branchで再同定workflowを実行してください。
検索入力とcurrent OSM IDが不変なら、workflowはOSM再同定を省略します。
current OSM IDは保持済みraw内に一意に存在する必要があります。
current OSM参照がない場合、検索入力と候補reportのraw hashが不変なら、workflowはOSM再同定を省略します。
