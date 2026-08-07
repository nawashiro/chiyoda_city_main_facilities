# `fac`コマンドリファレンス

repository直下で`./fac`を実行してください。

## Placeを表示する

```bash
./fac ls
./fac ls --town 神田神保町
./fac ls --cat library
./fac ls --name 図書館
./fac ls --osm false
./fac ls --life active
./fac get <UUID>
```

`ls`は名称、状態、geo URIを表示します。
`--color`と`--hyperlink`は`auto`、`always`、`never`を受け取ります。

## Placeを変更する

```bash
./fac set <UUID> --cat library --tag example.tag
./fac set <UUID> --life active --vis public
./fac set <UUID> --vis private
```

`--cat`と`--tag`は複数回指定できます。
`--life`と`--vis`は指定値と変更時刻を保存します。

## OSM参照を変更する

```bash
./fac ref <UUID> osm node/123456
./fac ref <UUID> osm way/123456
./fac ref <UUID> osm relation/123456
./fac ref <UUID> osm none
```

現在参照を解除すると、履歴を`superseded`として残します。

## 検索入力を操作する

```bash
./fac in ls
./fac in get <UUID>
./fac in add "施設名" --lon 139.75 --lat 35.69
./fac in add "施設名" --qid Q12345
./fac in set <UUID> --name "修正後の施設名"
./fac in set <UUID> --lon 139.75 --lat 35.69
./fac in set <UUID> --qid Q12345
```

`in add`はUUIDv7を出力します。
`in set`は座標とQIDを排他的に保存します。

## 別checkoutを指定する

rootパスをUUIDより前へ指定できます。

```bash
./fac get /tmp/checkout <UUID>
./fac ref /tmp/checkout <UUID> osm node/1
```
