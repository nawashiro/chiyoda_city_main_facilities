# Design

## Context

作者の抽出は`src/commons_retrieval.py`の`_artist_text`が担い、HTMLタグを正規表現で落とすだけです。Commons APIの`extmetadata.Artist`は、`File:Manseibashi Station original.jpg`（wikitextは`{{Information|Author={{unknown|author}}}}`）で`Unknown author<span style="display: none;">Unknown author</span>`を返します。この非表示要素の文字列が可視テキストと連結され、`Unknown authorUnknown author`として保存されています。

公開は`src/facility_data.py`の`_apply_images`が`artist`を`schema:Person`の名前として書き、`_valid_image`は`schema:creator`を必須にしています。`_apply_images`は既に`artist`が空の画像を落としているため、作者の有無が画像の有無を決める構造です。`imports/commons/raw.json`はコミット済みの生成物で、ビルドはこれを読むだけです。

## Goals / Non-Goals

**Goals:**

- 可視テキストだけを作者として保存する
- 作者が分からない画像も公開し、`schema:creator`を付けない
- `creator`任意の扱いを、抽出・公開・検証・仕様・テストで揃える

**Non-Goals:**

- `{{unknown}}`を全言語で判定すること
- `schema:creditText`など別の帰属表現の追加
- 作者名の表記統一（`江戸村のとくぞう`と`江戸村のとくぞう (Edomura no Tokuzo)`など）
- ライセンス別に公開可否を変えること

## Decisions

作者の抽出は`html.parser.HTMLParser`で行い、`display:none`または`hidden`を持つ要素の内側のテキストを読み飛ばします。正規表現で`<span>`を消す案は短く書けますが、ネストした要素や`hidden`属性を取りこぼすため採りません。

プレースホルダの判定は可視テキストを正規化したうえで`^unknown\b`（大文字小文字を無視）に一致するとき作者なしとします。Commonsは`{{unknown|author}}`を英語の`Unknown author`として返し、取得時に`uselang`を渡さないため英語で安定します。全言語の「不明」を列挙する案は保守の負担が大きいため採りません。

作者の有無は保存時に決め、`artist`へ`null`を書きます。公開処理はHTMLを解釈せず、`artist`の値だけを見ます。公開時に正規化する案は、`raw.json`に壊れた文字列が残るため採りません。

Commonsのファイル名はMediaWikiが`_`とスペースを同じものとして扱うため、`imports/commons/raw.json`のキーはAPIが返すページ名にそろえ、公開時の照合では両辺の`_`をスペースに直します。取得時に要求した綴りをキーに残す案は、同じファイルがP18とOSMタグで別の綴りになると引けなくなるため採りません。

公開時は`schema:contentUrl`と`schema:license`が揃えば`schema:image`を作り、`artist`があるときだけ`schema:creator`を付けます。`_valid_image`は`creator`を任意にし、あるときは`schema:Person`と非空の名前を要求します。作者が不明な画像を落とす案は、今回の目的（画像を残す）に反するため採りません。

`imports/commons/raw.json`は`python3 -m src.commons_retrieval --at <取得時刻> .`で再取得し、コミットします。月次パイプラインの`update`は同じ抽出処理を通るため、別の変更は要りません。

## Risks / Trade-offs

[作者不明のCC BY画像を`creator`なしで公開する] → ニコライ堂、遊就館、皇居東御苑の航空写真が該当します。ライセンスが作者表示を求めるため、再利用者が条件を満たせない場合があります。今回は既知の制約として受け入れ、帰属表示の追加は別の変更で扱います。

[英語以外のプレースホルダを取り逃す] → 判定は抽出時の1か所に集約し、テストで固定します。ローカライズされたプレースホルダは作者名として残る可能性があります。

[非表示要素に有意な情報が入る将来の変化] → 作者欄では可視テキストが帰属表示として正しいという前提をテストに書きます。

[raw.jsonの再取得で他のファイルの値も動く] → 取得後に差分を確認し、意図しない変更がないことを確かめます。

[公開画像が55枚になる] → ビルド後の`site/places.jsonld`で画像数と`creator`の有無を確認します。件数は再取得したメタデータで決まります。

## Migration Plan

1. 抽出と公開のコードを直し、テストを合わせる
2. `python3 -m src.commons_retrieval --at <取得時刻> .`で`imports/commons/raw.json`を再取得する
3. `python3 -m src.facility_data validate .`、`python3 -m src.facility_data build .`、`./fac jsonld-validate --published site/places.jsonld`を通す
4. 公開はPagesのビルドで反映される。戻すときはコードと`raw.json`のコミットを戻す
