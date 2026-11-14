# Tasks

## 1. Commons取得モジュール

- [x] 1.1 `src/commons_retrieval.py`を新設する。`run_commons_retrieval(root, at, fetch=_get)`で、Wikidata P18とOSMの`File:`タグからファイル名を集め、Commons APIの`imageinfo`（`url`と`extmetadata`の`LicenseShortName`、`LicenseUrl`、`Artist`）を50ファイル/リクエストで取得し、`imports/commons/raw.json`と`imports/commons/retrieval.json`を書く。
- [x] 1.2 取得モジュールのテストを書く。フェッチの差し替えで、ページング、SHA256の記録、紐付け集合に由来しないファイルの除外、API応答の異常を検証する。

## 2. 月次パイプラインへの組み込み

- [x] 2.1 `src/osm_maintenance.py`の`update`に`commons=run_commons_retrieval`を組み込み、Wikidata取得のあとに呼ぶ。保存済み判断だけで再実行する経路では呼ばないようにする。
- [x] 2.2 Commons取得の失敗が実行を失敗させないことをテストで確認する。Wikidataと同じ付加的扱いにする。

## 3. 公開時の合成と検証

- [x] 3.1 `src/facility_data.py`の`build_repository`で、ミラー再生成のあとに公開配布物へ`schema:image`を合成する。先頭P18、`File:`タグ、`Category:`除外、施設あたり1枚、`LicenseUrl`の無いときはライセンス名文字列、`imports/commons/raw.json`が無いときは画像なしで公開する。
- [x] 3.2 正本の検証に`schema:image`の禁止を加え、公開物の検証に`schema:ImageObject`の形の要求を加える。`fac jsonld-validate site/places.jsonld`が公開物を検証することを含める。
- [x] 3.3 合成と検証のテストを書く。正本が`schema:image`を持たないこと、P18優先とCategory除外、ライセンスURLとライセンス名の分岐、`Artist`のHTMLからのテキスト抽出、メタデータ欠落時の画像なし公開を検証する。

## 4. 全体の検証

- [x] 4.1 `python3 -m unittest discover -s tests`と`python3 -m src.facility_data validate .`を通し、既存テストの破れがあれば直す。
- [x] 4.2 三つのworkflow（`update-osm`、`publish-pages`、`release-jsonld`）の呼び出し経路が変更なしで済むことを確認し、必要なら`./fac`の動作を確認する。
