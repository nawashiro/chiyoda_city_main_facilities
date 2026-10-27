# Spec Delta

## MODIFIED Requirements

### Requirement: Conservative related-record links

システム SHALL 確定したOSM typed object IDと、そのrecordが直接持つWikidata QIDを、公式resource URIによる`rdfs:seeAlso`で出力する。システム MUST WAM識別子を公開Placeへ出力しない。自動出力 MUST `schema:sameAs`、SKOS match関係、Place単位の`prov:wasDerivedFrom`を含まない。

#### Scenario: Automated OSM association is exported

- **WHEN** 施設とOSM recordの照合結果を公開する
- **THEN** 出力はそのtyped object IDに対応する公式OSM resource URIを`rdfs:seeAlso`で表現する

#### Scenario: Wikidata association is exported

- **WHEN** OSM照合済みrecordが直接のWikidata QIDを含む
- **THEN** 出力はQIDに対応する公式Wikidata resource URIを`rdfs:seeAlso`で表現する

#### Scenario: Migrated facility is exported

- **WHEN** WAM由来の検索対象を移行した後に公開する
- **THEN** 出力は既存の施設UUIDを持ち、WAM識別子とWAMから合成した参照を含まない

## REMOVED Requirements

### Requirement: WAM service distinction

**Reason**: WAMのサービスrecordを取得・同定・公開する経路を削除する。
**Migration**: 既存施設のUUIDと必要な検索情報を統合入力へ移し、WAM専用ファイルと公開識別子を除去する。参考資料と必要な帰属表示は文書に残す。

## ADDED Requirements

### Requirement: Replacement and rejection update related references

システム SHALL 新しい関連付けを確定したとき、対象施設の以前のOSM参照とその照合由来のWikidata参照を現在の結果に置き換える。人が「該当なし」を確定した場合は両参照を解除する。システム MUST 関連付けの変更・解除だけを理由に施設UUIDを変更したり施設を削除したりしない。

#### Scenario: New object lacks the previous Wikidata tag

- **WHEN** 新しく確定したOSM recordに前回のWikidata QIDがない
- **THEN** システムは前回のOSM照合由来のWikidata参照を残さない

#### Scenario: Human rejects every candidate

- **WHEN** 人が「該当なし」を確定した結果を公開する
- **THEN** 対象のOSM参照とその照合由来のWikidata参照を含めず、施設UUIDを維持する
