# Design

## Context

現行の Commons 取得は `imports/commons/raw.json` にファイル単位のメタデータを保存し、公開時の `_apply_images` が P18 と `File:` タグのファイル名で引きます。`Category:` タグは取得対象外で、公開時も無視されます。

`build_repository` は `publish-pages` と release の checkout でも動きます。これらの checkout には `imports/openstreetmap/raw.json` が無く、ネットワーク取得も前提にしていません。したがって、カテゴリ解決は公開時ではなく月次の取得時に済ませ、結果をコミット済みの `imports/commons/raw.json` に残す必要があります。

対象の `Category:MAAch ecute Kanda-Manseibashi` は、`pageimages` も `wikibase_item` も持ちません。ファイルは17件あり、すべて `LicenseShortName` と `Artist` を持ちます。カテゴリ順の先頭は秋葉原の街景で、施設の代表画像としては弱いものです。カテゴリ名に一致する `File:MAAch ecute Kanda Manseibashi.jpg` は施設の夜景で、メタデータも揃っています。この1件が、`pageimages` だけでは足りないことと、メンバー選択に工夫が要ることを示しています。

## Goals / Non-Goals

**Goals:**

- `Category:` タグから画像ファイルを決め、公開時の `schema:image` に使えるようにする。
- カテゴリ解決の結果を取得物に残し、公開をネットワークから独立させる。
- 既存の P18 優先と1 record 1画像を保つ。

**Non-Goals:**

- サブカテゴリを再帰的にたどること。
- 公開時に Commons API を呼ぶこと。
- `Artist` を持たないファイルを画像にすること。
- 現在画像のない4件を、この変更だけで救うこと。

## Decisions

### 1. カテゴリ解決は取得時に行い、`imports/commons/raw.json` に記録する

`run_commons_retrieval` で `Category:` タグをファイル名に解決し、`categories` マップとして保存します。公開時の `_apply_images` はこのマップを読むだけです。

代替案として、公開時に Commons API を呼ぶ方法があります。しかし `publish-pages` の checkout には `imports/openstreetmap/raw.json` が無く、公開のたびに外部 API の可用性へ依存します。取得物から決定的に公開物を作る既存の方針にも反します。

### 2. 第一候補は `pageimages`

カテゴリの代表画像は `action=query&prop=pageimages&piprop=name&redirects=1` で、50カテゴリまでまとめて取得します。現在ミラーにある27カテゴリはすべて `pageimage` を持ち、27件中25件はライセンスと作者も揃っています。1リクエストで済み、カテゴリ内の先頭ファイルを無条件に取るより代表画像性が高い。

代替案として、常に `categorymembers` の先頭ファイルを使う方法があります。1カテゴリにつき1リクエストが必要で、27カテゴリでは27回になります。試したところ、短時間に10回程度で HTTP 429 が返りました。先頭がベンチマークの石板や1989年の空撮になることもあり、代表画像性も劣ります。

### 3. `pageimages` が無いカテゴリだけ `categorymembers` に落とす

`pageimages` が無いカテゴリについて、`action=query&list=categorymembers&cmtitle=...&cmtype=file&cmlimit=50&cmprop=title|sortkey` を1回呼び、ファイルメンバーを最大50件取得します。サブカテゴリは対象にしません。

対象カテゴリはこの経路に落ちます。17ファイルのうち、カテゴリ名との語の一致数が最も多いものを選びます。

### 4. メンバー選択はカテゴリ名との語の一致で決める

カテゴリ名から `Category:` と区切りを除いて小文字化し、Unicode の文字種で語に分けます。各ファイル名も同じように語に分け、カテゴリ名の語がファイル名にいくつ含まれるかを点数にします。点数の降順、タイトルの短い順、辞書順で1件を選びます。点数がすべて0なら、カテゴリ順の先頭を使います。

対象カテゴリでは、`MAAch ecute Kanda Manseibashi.jpg`、`MAAch ecute Kanda-Manseibashi - viewed from...`、`MAAch ecute Kanda-Manseibashi riverside deck...` が同点になり、最も短い `MAAch ecute Kanda Manseibashi.jpg` が選ばれます。先頭の秋葉原の街景は選ばれません。

代替案として、先頭ファイルをそのまま使う方法があります。実装は最も簡単ですが、対象カテゴリでは施設と関係の薄い街景が公開されます。施設名を含むファイルを優先するだけの規則で、この問題は避けられます。

### 5. `categories` は `files` と分けて持つ

`imports/commons/raw.json` は次の形にします。

```json
{
  "sourceId": "commons",
  "retrievedAt": "at",
  "files": {
    "File:MAAch ecute Kanda Manseibashi.jpg": {
      "url": "https://upload.wikimedia.org/...",
      "license": "CC BY-SA 4.0",
      "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/",
      "artist": "Tyuvc"
    }
  },
  "categories": {
    "Category:MAAch ecute Kanda-Manseibashi": "File:MAAch ecute Kanda Manseibashi.jpg"
  }
}
```

`files` はファイル名でメタデータを共有し、`categories` はタグからファイル名への対応だけを持ちます。カテゴリ名を `files` のキーにすると、同じファイルのメタデータがカテゴリごとに重複し、ファイル名で引く既存の公開処理と意味が混ざります。

### 6. 公開時の優先順位は P18、`File:`、`Category:` の順

`_image_file_name` は、まず P18、次に OSM の `File:` タグ、最後に `categories` の対応を見ます。P18 がある record ではカテゴリの代表画像を使いません。

P18 のファイルメタデータが不完全なときにカテゴリへ落とす案もあります。しかし現行仕様の「先頭の P18 を画像にする」を変えることになり、今回の依頼の範囲を超えます。P18 が無いときだけカテゴリを使います。

### 7. ワークフローの `git add` に `imports/commons/` を加える

`.github/workflows/update-osm.yml` の `git add` は現在 `imports/commons/` を含んでいません。月次ボットが `categories` を書いてもコミットされず、Pages のビルドは古い `raw.json` を使います。`imports/commons/` を追加し、取得物を他のミラーと同じようにコミットします。

## Risks / Trade-offs

- [未解決カテゴリが多いと `categorymembers` のリクエストが増え、429 になり得る] → `pageimages` を先に使い、落ちたカテゴリだけに限定します。対象カテゴリを紐付けた場合でも、追加は1回だけです。失敗した場合は既存どおり Commons 取得全体をスキップし、公開は止めずに次月へ持ち越します。
- [語の一致による選択は、施設と関係の薄いファイルを選ぶことがある] → 選んだ対応を `raw.json` に残し、監査できるようにします。点数がすべて0ならカテゴリ順の先頭に落とすため、選択自体は決定的です。
- [`pageimage` は月次で変わり得る] → 取得のたびに対応を上書きします。公開物は次回のビルドで追随します。
- [カテゴリメンバーの先頭50件だけを見る] → 51件目以降にしか名前の一致するファイルがない場合は、先頭ファイルに落ちます。大規模カテゴリで全件を走査するとリクエスト数が読めないため、1ページに限定します。
- [`Artist` が無いファイルは画像にならない] → 公開スキーマが作者を要求するため、現行どおり画像なしにします。代表画像が作者なしの場合は、その施設に画像が付きません。
- [いま画像のない4件は救われない] → いずれも P18 のファイルが `raw.json` に未収録か、`Artist` が空です。カテゴリ代表画像も同じファイルなので、別途 Commons メタデータの再取得が必要です。

## Migration Plan

データの移行は不要です。`categories` が無い `raw.json` は空の対応として扱い、従来どおり P18 と `File:` だけで公開します。次の月次更新で `categories` が入り、その次のビルドからカテゴリ画像が公開物に現れます。手元で先に反映する場合は、Commons 取得を実行して `imports/commons/raw.json` をコミットします。

ロールバックは、`categories` の参照を外すか、`raw.json` から `categories` を削除して再ビルドします。P18 と `File:` の経路はそのまま残ります。
