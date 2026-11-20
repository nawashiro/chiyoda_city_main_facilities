# Tasks

## 1. 作者抽出

- [x] 1.1 `src/commons_retrieval.py`の`_artist_text`を`html.parser`で実装し、`display:none`または`hidden`を持つ要素の内側のテキストを読み飛ばす。`tests/test_commons_retrieval.py`に`Unknown author<span style="display: none;">Unknown author</span>`を渡すテストを追加し、`Unknown author`が返ることを確かめる
- [x] 1.2 可視テキストが`^unknown\b`（大文字小文字を無視）に一致するとき`_artist_text`が`None`を返す。同じテストファイルで、`Unknown author`と`Unknown artist`が`None`になることを確かめる

## 2. 公開処理

- [x] 2.1 `src/facility_data.py`の`_apply_images`を、`url`と`license`だけで`schema:image`を作り、`artist`があるときだけ`schema:creator`を付ける形にする。`tests/test_published_images.py`で、`artist`が`null`のファイルに画像とライセンスが付き、`schema:creator`が無いことを確かめる
- [x] 2.2 `src/facility_data.py`の`_valid_image`を`schema:creator`任意に変え、あるときは`schema:Person`と非空の名前を要求する。`tests/test_published_images.py`の検証テストに、`creator`なしが通り、`creator`の型や名前が壊れているものが落ちるケースを加え、エラーメッセージも合わせる
- [x] 2.3 `tests/test_published_images.py`の既存の期待値を、作者なしの画像が「画像なし」から「`creator`なしの画像」に変わるよう更新し、テスト一式が通ることを確かめる

## 3. ファイル名の照合

- [x] 3.1 `src/commons_retrieval.py`の`_query_files`を、APIが返すページ名をキーにする形に変える。`tests/test_commons_retrieval.py`で、アンダースコアで要求したファイルがスペースのページ名で保存されることを確かめる
- [x] 3.2 `src/facility_data.py`の`_apply_images`で、メタデータのキーと参照するファイル名の`_`をスペースに直して照合する。`tests/test_published_images.py`に、P18の`_`とページ名のスペースが違う組み合わせでも画像が付くケースを加え、テストが通ることを確かめる

## 4. 取り込みデータの更新

- [x] 4.1 `python3 -m src.commons_retrieval --at <取得時刻> .`で`imports/commons/raw.json`を再取得し、`File:Manseibashi Station original.jpg`の`artist`が`null`になることを確かめる。`retrieval.json`の`rawSha256`も更新されることを確かめる
- [x] 4.2 `git diff imports/commons/`で、`files`のキーがページ名にそろい、作者が`null`になるファイル以外の意図しない差分がないことを確かめる

## 5. 統合確認

- [x] 5.1 `python3 -m src.facility_data validate .`、`python3 -m src.facility_data build .`、`./fac jsonld-validate --published site/places.jsonld`を通し、`site/places.jsonld`の画像付きrecordが55件で、作者不明の4件が`schema:creator`を持たないことを確かめる
- [x] 5.2 `openspec validate optional-image-creator`が通り、仕様の差分と実装の振る舞いが一致することを確かめる

## Workflow follow-up

- レビューが済んだらchangeをアーカイブする
- アーカイブ後に`site/places.jsonld`の配信内容を確認する
