# Tasks

## 1. 語彙と文書

- [x] 1.1 `data/category-names.jsonld`の1402の表示名を「保育所・託児所」に変える。`python3 -m src.facility_data validate .`が成功し、語彙の1402が新しい表示名を持つことを確認する
- [x] 1.2 `docs/reference/sources-and-licenses.md`の本文と加工内容を、GIFの分類名を基礎にした表示名と、その翻案の記録へ直す。1402の表示名と加工内容の記述が一致することを確認する

## 2. ビルドと検証

- [x] 2.1 `python3 -m src.facility_data build .`を実行し、`site/category-names.jsonld`が`data/category-names.jsonld`と一致することを`cmp`で確認する
- [x] 2.2 `python3 -m unittest discover -s tests`を通し、語彙の検証を含むテストが成功することを確認する
- [x] 2.3 CIと同じ手順で`python3 -m src.facility_data validate .`、`./fac jsonld-validate data/places.jsonld`、ビルド後の`cmp`を通す。あわせて`openspec validate "curate-category-display-names"`が成功することを確認する

## Workflow follow-up

- Archive the change after the data association of node/14394442841 is recorded separately.
- Push the branch and let the validation workflow run.
