# Design

## Context

正本`data/places.jsonld`は関連付けだけを載せる方針がspecと実装で確立している。画像の素材は既存のミラーに届いている: Wikidataミラー（`site/mirrors/wikidata.json`、コミット済み）のP18、OSMミラー（`site/mirrors/osm.json`、コミット済み）の`wikimedia_commons`タグ。ライセンスと作者はどのミラーにもなく、Commons APIの`extmetadata`（`LicenseShortName`、`LicenseUrl`、`Artist`）で取得する。

実測（2026-11-14）: ファイル名は重複を除き51個。`LicenseUrl`が無いライセンスが1件ある（独自テンプレート「Attribution」）。1つのentityが複数のP18を持つことがある。`build_repository`は`update-osm`、`publish-pages`、`release-jsonld`の三つのworkflowから呼ばれる。`imports/openstreetmap/raw.json`は`.gitignore`対象で、公開workflowのcheckoutには存在しない。

## Goals / Non-Goals

- Goals: 公開配布物だけで画像リンク・ライセンス・作者が完結すること。正本と判断記録の無変更。
- Non-Goals: 正本への画像の保存。CommonsミラーのPages配信。`Category:`タグの代表ファイル選出。landing pageの変更。

## Decisions

- **合成は公開時（`build_repository`）にする。** 正本は触らない。画像の鮮度は月次の取得で保ち、公開物は常にコミット済みの入力から決定的に作る。正本へ書く案はissueの議論で除外済み。
- **合成の入力はコミット済みの`site/mirrors/{osm,wikidata}.json`を使う。** 紐付け集合で絞られた配布物そのものであり、どのcheckoutにも存在する。`imports/*/raw.json`はpublish-pagesやreleaseの実行に無いため使えない。ミラー再生成のあとで配布物を書くよう、`build_repository`内の順序を入れ替える。
- **Commonsメタデータは`imports/commons/raw.json`にコミットし、配信しない。** 第三の配布物はライセンス宣言義務を生む一方、中身は公開物の`schema:image`に全部焼き込まれるため新しい情報がない。`retrieval.json`（取得日時・エンドポイント・応答SHA256）を同封し、監査はファイルページURLとretrievalメタで足りる。
- **取得モジュールは`wikidata_retrieval.py`と同型にする。** `run_commons_retrieval(root, at, fetch=_get)`を新設し、`osm_maintenance.update`に`commons`引数で組み込む。保存済み判断だけで再実行する経路では`wikidata=None`に合わせ`commons`を呼ばない。50ファイル/リクエストでページングし、応答は既存の`read_limited_response`で上限を取る。
- **`schema:license`はURL優先、無ければライセンス名の文字列。** schema.orgの`license`はTextも受け付ける。実測の「Attribution」のように`LicenseUrl`が付かないライセンスを落とさないため。
- **作者は`schema:creator`を`schema:Person`の`schema:name`として載せる。** Commonsの`Artist`はHTMLで人・組織の区別を持たないので、タグを外したプレーンテキストにし、型は`Person`で固定する。
- **選択規則はspecどおり。** 先頭のP18、無ければ`File:`タグ、`Category:`は無視、施設あたり1枚。同名ファイルはメタデータをファイル名で共有する。
- **検証は正本と公開物で分ける。** 正本の検証は`schema:image`を禁止し、公開物の検証は`schema:ImageObject`の形（`contentUrl`のhttps、`license`のURLまたは文字列、`creator`の形）を要求する。`fac jsonld-validate`は既定で正本の検証を保ち、`--published`で公開物の検証に切り替える。`update-osm.yml`の`site/places.jsonld`の検証と、release snapshotの作成（`scripts/prepare_release_jsonld.py`）は公開物の検証を使う。

## Risks / Trade-offs

- [正本に埋め込まないため、公開物と正本の内容が一致しない] → 差分は`schema:image`だけ。正本無変更の検証テストで守る。
- [Commons側の再ライセンス・削除で公開物が古びる] → 月次で`imports/commons/raw.json`が上書きされ、次の公開で直る。削除済みファイルは該当施設から画像が消える。
- [`Artist`のHTML構造の変化] → テキスト抽出はタグ剥がしに限定する。作者を抽出できないファイルは`schema:creator`を持てないため、そのファイルは画像にしない。
- [GFDLなど重いライセンスが将来混ざる] → `schema:license`が条件の確認を利用者へ流す。判断の代行はしない。
- [Commons APIの`imageinfo`のURLにutmtパラメータが付く] → 取得時にクエリ文字列を除いた直接URLを保存する。

## Migration Plan

初回の月次更新で`imports/commons/raw.json`ができてから、公開物に`schema:image`が現れる。それまでの公開物は現行どおり画像なし。rollbackは`imports/commons/raw.json`の削除と再公開で、画像の無い現行の形に戻る。正本と判断記録への影響はない。

## Open Questions

なし
