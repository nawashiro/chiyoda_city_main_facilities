# Proposal

## Why

v2.1.1の配布は人力カテゴリを持っていたが、JSON-LD移行時に独自`categoryIds`ごと削除された。kazaguruma-transitはv2.1.1の配布をpinしたままで、カテゴリがないと新配布へ移行できない。分類は施設の名前より変わりにくく、施設ごとに確定した判断として持たせられる。

## What Changes

- GIF POIコード表（デジタル庁GIF、GitHubのタグで版固定）の採用サブセットを、カテゴリ名辞書`data/category-names.jsonld`に定義する。辞書はschema.orgの`DefinedTermSet`で構成し、各termはterm URL（fragmentは4桁POIコード）と日本語ラベルだけを持ち、出典を辞書に含まない
- OSMタグと施設名称からPOIコードを決める翻訳規則表`data/category-rules.json`を人が編集する。規則は観測されたタグのパターンごとに書く
- 施設ごとのカテゴリ判断を`data/categories.json`に確定した判断として保存する（method: `rule`/`jev`/`human`）。ruleで一意に決まるものを記録し、残りをJevが判定し、閾値以上の結果を自動採用する。未解決（閾値未満・該当なし・候補なし）だけを確認Issueで人へ示し、人手は`fac category`サブコマンドでも記録できる
- 判断の見直しは、関連付けOSM要素が変わったときと、人が指示したときだけ行う。名称・タグ・座標の変化は見直しの条件にしない
- 公開Place recordに分類を`schema:identifier`の`schema:PropertyValue`（`propertyID: gif-poi`、`value: 4桁コード`）として追加する。**BREAKING**: 公開recordの「独自`categoryIds`を含みません」の除外条項を、分類はgif-poi識別子のみという契約へ置き換える。先行実装でrecordに入れた`schema:additionalType`は取り除く
- カテゴリ名辞書をGitHub PagesのsiteとReleaseの版固定資産（`category-names-<版>.jsonld`）に加える。GIF POIコード表（CC0）の出典はlanding pageの`schema:Dataset`で表現する

## Capabilities

### New Capabilities
- `facility-categories`: GIF POIコード表に基づくカテゴリ語彙、OSMタグと名称からの翻訳規則、施設ごとの確定した判断の記録、rule/Jev/人手による割当てと見直しの条件

### Modified Capabilities
- `public-jsonld-dataset`: 「Public record excludes derived and upstream-detail fields」を修正する。独自`categoryIds`の除外を除き、公開recordの分類を`schema:additionalType`の語彙文書term URLのみへ定める
- `dataset-publication`: Releaseの版固定資産とPages配布物に語彙文書を加える

## Impact

- `data/`（`category-names.jsonld`への改名、`category-rules.json`、`categories.json`の新設）、`src/facility_categories.py`、`src/facility_data.py`（正本の生成と検証、additionalType検証の除去）、`src/fac_cli.py`（`category`サブコマンド）、`scripts/prepare_release.py`（siteとReleaseの配布物）、`site/index.html`（DataDownloadとGIF出典）
- 判断記録`data/categories.json`と`fac category`の操作は形を変えず、recordへの適用だけがadditionalTypeからgif-poi識別子へ変わる
- Jevの呼び出しは既存のosm-maintenanceの流れに沿う
- kazaguruma-transit側はrecordの`propertyID: gif-poi`を見て名前辞書を引き、サブセット絞り込みは同リポジトリの設計とする
- GIF POIコード表は外部の標準で、GitHubの版固定ファイルを参照する（CC0-1.0）。バリアフリーリンクや関連付けの既存契約には影響しない
