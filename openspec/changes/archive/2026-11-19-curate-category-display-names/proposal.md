# Proposal

## Why

カテゴリ名辞書の1402は「保育園」ですが、GIFの解説はこの分類に保育園・保育所・託児所を含めています。収録している子育てひろば「あい・ぽーと」麹町は、施設型一時保育「こみち」を持つ託児所側の施設です。表示名が「保育園」だけでは、分類の範囲が辞書の利用者に伝わりません。現在の要件はGIFの項目名の写しを強制するため、表示名を選べません。

## What Changes

- 語彙の各termが持つ日本語ラベルを、GIFの項目名の写しから、GIFの分類を指す表示名へ変える。表示名は人が決め、コードが指す分類の範囲を変えない。
- コード1402の表示名を「保育園」から「保育所・託児所」へ変える。
- `docs/reference/sources-and-licenses.md`の出典と加工内容を、表示名の採用に合わせる。
- コード、判断記録、公開record、検証ロジックは変えない。

## Capabilities

### New Capabilities

なし。

### Modified Capabilities

- `facility-categories`: 名前辞書のラベル要件を、GIFの項目名の写しから、GIFの分類を指す表示名へ変える。

## Impact

- データ: `data/category-names.jsonld`、`site/category-names.jsonld`（ビルドで追随）
- 文書: `docs/reference/sources-and-licenses.md`
- コード: 変更なし
- 消費側: recordの`gif-poi`値は変わらないため、コードによる結合は影響を受けない。表示名を引く利用者だけが新しい表示名を見る。
