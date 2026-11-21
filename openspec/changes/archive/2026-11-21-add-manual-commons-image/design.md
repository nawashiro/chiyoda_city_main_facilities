# Design

## Context

正本`data/places.jsonld`は施設の関連付けだけを載せ、公開時の`schema:image`はWikidata P18、OSMの`wikimedia_commons`タグ、Commonsカテゴリの代表画像から`build_repository`が合成しています。正本の検証は`schema:image`を拒否し、公開物の検証は`schema:ImageObject`を要求します。Commonsのファイル名収集は`site/mirrors/{osm,wikidata}.json`に限定され、メタデータは`imports/commons/raw.json`に保持されます。

OSM、Wikidata、Commonsはこの施設グラフにIRIを提供する情報源であり、その選択方針がデータセットの用途と一致するとは限りません。手動の画像選択は、正本の関連付けとして扱います。動機はproposal.mdのWhyを参照してください。

## Goals / Non-Goals

**Goals:**

- 正本のPlace recordにCommonsファイルページのIRI参照を一つ置けるようにする。
- 公開ビルドで手動参照を最優先し、参照のメタデータが得られないときは自動候補へ戻さない。
- 手動参照を専用CLIだけで設定・解除・確認できるようにする。
- 正本には派生値（直接URL、ライセンス、作者）を置かず、公開物だけに`schema:ImageObject`を出す。

**Non-Goals:**

- 画像を付けないという明示的な抑制。`clear`は手動参照を外して自動選択に戻す操作であり、画像なしの指定ではない。
- 新しい判断記録ファイルの追加。`data/images.json`のような台帳は作らない。
- `data/osm-decisions.json`と`data/categories.json`の棚卸し。カテゴリ判断を正本の`schema:keywords`へ寄せるかは別の変更で扱う。
- Commonsを`data/sources.json`やlanding pageのデータセット源として追加すること。画像ごとの`schema:license`と`schema:creator`で帰属を表す。
- 画像の複数指定、カテゴリ指定、Commons以外のURLの指定。

## Decisions

### 正本にはCommonsファイルページのIRI参照だけを置く

正本の`schema:image`は`{"@id": "https://commons.wikimedia.org/wiki/File:..."}`の形にします。`File:`タイトルの文字列はJSON-LDのIRIにならず、直接アップロードURLはファイルページから導出できる派生値だからです。完全な`ImageObject`を正本へ置く案は、ライセンスと作者の鮮度を正本へ閉じ込め、公開時の取得を無意味にするため採りません。

### 手動参照は自動選択より優先し、欠落時もフォールバックしない

手動参照がある施設では、P18、OSMの`File:`タグ、`Category:`タグを評価しません。参照先のメタデータが得られないときは、その施設に`schema:image`を付けず、ビルドで警告を出します。人間の指定を黙って別の画像に差し替えると、指定していない画像が公開され、データセットの信用を損なうためです。公開は止めず、`./fac image review`で未解決を確認できるようにします。

### 新しい判断記録を作らず、正本を関連付けのグラフとして保つ

画像の選択は`data/places.jsonld`のPlace recordに置きます。`data/images.json`のような判断記録を追加する案は、施設の同一性を決める場所が正本、OSM判断、カテゴリ判断、画像判断の四つに分かれるため採りません。`data/osm-decisions.json`は候補、根拠ハッシュ、保留、確認状態という自動化の状態を持ち、正本のIRIだけでは表現できません。画像の選択はその種の運用状態ではなく、正本の関連付けそのものです。

### 正本と公開物で検証を分ける

正本の検証はCommonsファイルページ参照の形だけを許可し、`schema:contentUrl`、`schema:license`、`schema:creator`、その他のフィールドを拒否します。公開物の検証は従来どおり`schema:ImageObject`を要求します。`build_repository`は公開用に複製したdocumentから正本の参照を必ず取り除き、メタデータが揃うときだけ`schema:ImageObject`を設定します。ミラーや`imports/commons/raw.json`が無いcheckoutでも参照が公開物へ漏れないよう、取り除く処理は入力の有無を確認する前に行います。

### Commons取得は正本の手動参照も対象にする

`collect_file_names`は`site/mirrors/{osm,wikidata}.json`に加えて`data/places.jsonld`の`schema:image`を読み、ファイルページから`File:`タイトルを取り出します。手動参照のファイルはP18やOSMタグに現れないことがあり、取得対象に含めなければ公開物へ画像を出せないためです。正本はすべてのcheckoutに存在し、月次取得の時点でも利用できます。

### CLIは正本だけを編集し、取得は月次に任せる

`./fac image set`は`File:`タイトルまたはCommonsファイルページURLを受け取り、正規化したページURLを正本へ書きます。ネットワーク取得は行いません。`./fac image clear`は参照を外し、`./fac image review`は保存済みの`imports/commons/raw.json`と照合して解決済み・未解決を表示します。`set`の時点でCommons APIを呼ぶ案は、取得経路を二つにし、`imports/commons/retrieval.json`の一貫性を崩すため採りません。指定直後はメタデータが未取得であり、次の月次更新後に公開物へ反映されることを文書に明記します。

### 正規化と検証は共通モジュールに置く

`File:`タイトルとCommonsファイルページURLの正規化・検証は`src/commons_files.py`に置きます。`src/facility_data.py`は正本検証と公開ビルドでこれを使い、`src/commons_retrieval.py`はファイル名収集で使います。`facility_data`から`commons_retrieval`を参照すると循環importになるため、どちらにも依存しない小さなモジュールに分けます。`Category:`、`Special:`、直接アップロードURLは拒否し、`File:`タイトルと`/wiki/File:`のページURLだけを受け付けます。

## Risks / Trade-offs

- [手動参照のファイルがCommonsで削除・改名される] → メタデータが得られず公開recordから画像が消える。ビルド警告と`image review`の未解決表示で気づき、人が参照を更新する。
- [手動参照のファイルのライセンスが変わる] → 月次のCommons取得が`imports/commons/raw.json`を更新し、次のビルドで公開recordのライセンスと作者が更新される。
- [指定直後は画像が公開物に現れない] → `set`は正本だけを書き、メタデータ取得は月次に任せる。`image review`で未取得を確認でき、必要なら既存のCommons取得を手動で回す。即時取得の`--fetch`は今回の範囲外。
- [正本と公開物で`schema:image`の形が違う] → 正本は参照形、公開物は`ImageObject`として検証を分ける。`./fac jsonld-validate`の既定と`--published`の違いを文書に明記する。
- [保留中の施設に手動参照が残る] → 関連付けの保留は画像の選択を自動的に外さない。人が`image clear`で外せる。保留と画像の整合は`image review`で確認する。
- [`imports/commons/raw.json`が古い] → `image review`は保存済みメタデータとの照合であり、Commonsの現在状態を保証しない。月次更新後の確認を運用に含める。

## Migration Plan

1. 既存の正本recordは`schema:image`を持たないため、データ移行は不要です。新しいフィールドは任意です。
2. 正本の検証、公開ビルド、Commons取得、CLI、テスト、文書を同じ変更で更新します。
3. 手動参照を追加するまで、公開物の画像選択は従来と同じです。手動参照を追加した施設だけ、次のビルドで選択が変わります。
4. ロールバックは、手動参照を`image clear`で外し、コードを戻します。公開物は従来の自動選択に戻ります。
5. 既存の`data/osm-decisions.json`、`data/categories.json`、`imports/`の形式は変更しません。

## Open Questions

- `./fac image set`に即時取得の`--fetch`を付けるか。付けなくても仕様と運用は成立し、必要になったときに追加できます。
- `image review`が手動参照だけでなく自動選択の画像も一覧するか。今回は手動参照の解決状況だけを対象にします。
