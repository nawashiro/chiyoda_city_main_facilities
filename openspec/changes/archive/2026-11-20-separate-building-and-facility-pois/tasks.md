# Tasks

## 1. 建物POI

- [x] 1.1 昌平童夢館を`way/173230196`に付け替え、カテゴリを1307で確定する。`./fac assoc . 019fa880-5cd5-7241-a976-801eef6324a9 --osm-id way/173230196 --editor Navi`、`./fac category refresh .`、`./fac category assign . 019fa880-5cd5-7241-a976-801eef6324a9 1307 --editor Navi`を実行し、`./fac category review .`で`decided human 1307`になることを確認する
- [x] 1.2 いきいきプラザ一番町を`way/144866171`に付け替え、カテゴリ1499を再確定する。`./fac assoc . 019fa880-5cd5-7d11-8560-3ac4e0486633 --osm-id way/144866171 --editor Navi`、`./fac category assign . 019fa880-5cd5-7d11-8560-3ac4e0486633 1499 --editor Navi`を実行し、`./fac category review .`で1499になることを確認する
- [x] 1.3 岩本町ほほえみプラザのカテゴリ1499が維持されていることを`./fac category review .`で確認する（参照`node/14337499601`とカテゴリ1499は変更しない）
- [x] 1.4 西神田コスモス館の保留を解除し、`relation/9323146`に付け替えて1307で確定する。`./fac assoc . 019fa880-5cd5-7b01-9dd8-2e4787f423aa --osm-id relation/9323146 --editor Navi`、`./fac category assign . 019fa880-5cd5-7b01-9dd8-2e4787f423aa 1307 --editor Navi`を実行し、`./fac category review .`から`held`が消えて1307になることを確認する
- [x] 1.5 神田さくら館を検索入力に追加し、`way/187756645`に関連付けて1307で確定する。`./fac in add . 神田さくら館 --lon 139.7684459 --lat 35.693118`で得たUUIDに`./fac assoc . <uuid> --osm-id way/187756645 --editor Navi`と`./fac category assign . <uuid> 1307 --editor Navi`を実行し、`./fac category review .`で1307になることを確認する
- [x] 1.6 富士見みらい館（`way/179575985`）とちよだパークサイドプラザ（`node/14337531401`）が1307のままであることを`./fac category review .`で確認する（参照の付け替えは不要）

## 2. 施設POI

- [x] 2.1 神田児童館を検索入力に追加し、`node/2263796343`に関連付けて1403で確定する。`./fac in add . 神田児童館 --lon 139.7696731 --lat 35.7011916`で得たUUIDに`./fac assoc`と`./fac category assign`を実行し、`./fac category review .`で`decided human 1403`になることを確認する
- [x] 2.2 いずみこどもプラザを検索入力に追加し、`node/14337525601`に関連付けて1403で確定する。`./fac in add . いずみこどもプラザ --lon 139.7787853 --lat 35.6992391`で得たUUIDに同じ手順を実行し、`./fac category review .`で1403になることを確認する
- [x] 2.3 富士見小学校を`way/460729041`に付け替え、1503を維持する。`./fac assoc . 01a1e8ab-f109-7794-bbe6-d6d05f476328 --osm-id way/460729041 --editor Navi`を実行し、`./fac category review .`で1503のままであることを確認する

## 3. 文書と検証

- [x] 3.1 `docs/reference/data-contracts.md`に、建物と内部施設は別IDのPlaceとして並列に公開し、包含関係を持たないことを追記する。文書の記述が公開recordの実際と一致することを確認する
- [x] 3.2 テスト一式と`./fac jsonld-validate data/places.jsonld`を実行し、建物7件と施設（神田児童館、いずみこどもプラザ、富士見小学校）のrecordが期待どおりの参照とカテゴリで公開されることを確認する

## Workflow follow-up

- データコミット後に変更をアーカイブする
- アーカイブ後の公開データとカテゴリ配分を確認する
