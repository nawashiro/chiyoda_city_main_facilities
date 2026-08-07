# 千代田区主要施設データベース 保守計画

## 目的

主要施設DBを、一人でも継続して扱える小さな単位で更新する。網羅性より、誤案内を避けることと、変更根拠を後から確認できることを優先する。

現行仕様は[保守仕様](../reference/data-maintenance-spec.md)を正とする。本書は作業チェックリストである。

## 現在のデータ構成

- 検索入力: `inputs/osm-search/`
- 唯一の正本: `data/registry.json`
- WAM snapshot: `imports/wam/`
- OSM (OpenStreetMap) snapshot: `imports/openstreetmap/`
- 固定町名ポリゴン: `data/pinned/`
- レビューレポート: `reports/`
- 公開生成物: `dist/public/`
- ソース・利用条件台帳: `config/sources.json`

公開GeoJSONは`visibility.status == "public"`のPlaceだけをPointとして出力する。propertiesには`id`、`name`、`categoryIds`、`tags`、`images`、`town`、`lifecycleStatus`、`sources`を含める。

## 更新前チェック

- [ ] [最初の施設変更](../tutorials/first-data-change.md)を読んだ
- [ ] `main`とremoteの差分を確認した
- [ ] 作業branchを作った
- [ ] `python3 --version`がPython 3.13である
- [ ] 同一ソースの前回取得から30日以上経過している
- [ ] WAMなら公式配布版`YYYYMM`を確認した
- [ ] 町名なら上流の40文字commit SHAを確認した
- [ ] 変更前のtestsとvalidateが成功する

## WAM更新

対象は相談支援4サービスだけである。

- [ ] `52` 計画相談支援
- [ ] `53` 地域相談支援（地域移行）
- [ ] `54` 地域相談支援（地域定着）
- [ ] `70` 障害児相談支援

確認事項:

- [ ] 千代田区以外のrowがraw snapshotへ入っていない
- [ ] 利用可能時間の空欄を理由に除外していない
- [ ] normalized施設数が前回から大きく変わっていない（202603版の8施設は目安であり固定ではない）
- [ ] 元レコードの全IDが正本参照へ保持される（202603版は13件）
- [ ] raw snapshotのSHA-256が取得台帳と一致する
- [ ] normalized recordがraw rowから再計算した値と一致する
- [ ] 公式ZIPそのものをrepositoryやartifactへ恒久保存していない

## OSM更新

確認事項:

- [ ] Overpassを単一batch queryで呼び出している
- [ ] `remark`／`error`付き部分応答を拒否している
- [ ] current ID照合に名称・QID競合や50m超の移動がない
- [ ] QID照合は検索入力QIDと一致する一意候補だけ
- [ ] 名称＋座標照合は正規化後6文字以上、編集距離15%以内、50m以内の一意候補だけ
- [ ] 全候補が一度に提示され、OSM rawの全タグが候補属性へ含まれた
- [ ] 訪問者・利用者・現地スタッフの3視点で判定された
- [ ] 3票のうち2票以上一致した候補またはrejectが自動処理された
- [ ] 合議不成立だけがGitHub確認Issueへ出た
- [ ] IssueではJSONを編集せず、検索入力ごとにチェックボックスを一つ選べる
- [ ] 成功した新規取得ではquery／response／canonical rawのhashとretention flagが一致する

## 検索入力修正後の再同定

- [ ] 修正をcommitしたbranchで`Re-identify retained source snapshots`を実行した
- [ ] WAM・OSMのrawと取得台帳が実行前後で同一だった
- [ ] raw SHA・版を検証した
- [ ] 検索入力とcurrent OSM IDの差分から影響項目だけを選んだ
- [ ] 検索入力が不変でcurrent OSM IDも一意に残る項目を再同定しなかった
- [ ] current OSM参照がない項目は、検索入力と候補reportのraw hashが不変なら再同定しなかった
- [ ] 影響項目だけOSM normalizedとOSM候補を再生成した
- [ ] WAM normalizedを保持済みWAM rawと現在の検索入力から再生成した
- [ ] 影響項目だけ正本名を同期した
- [ ] WAM→OSMの順で影響項目を適用した
- [ ] 未解決候補だけをLLM照合した
- [ ] 項目ごとのコンテクスト分離を保てる場合は一括requestを使った
- [ ] 一括requestが不可能な場合は、実行前にrequest数を報告して確認を受けた
- [ ] 合議不成立はGitHub確認Issue、全解決時はPull Requestへ進んだ

## 町名更新

確認事項:

- [ ] 上流commitを40文字SHAで固定した
- [ ] Polygon／MultiPolygon、閉ring、3つ以上の異なる頂点、非ゼロ面積を検証した
- [ ] 全公開Pointの町名が意図どおりか確認した
- [ ] 町名ポリゴンを公開GeoJSONへ含めていない

GitHub Actionsのartifactを取得する場合は、[ソースを更新する](update-source-data.md)のartifact取込手順を使う。`update-wam.yml`と`update-towns.yml`はartifactを作成するが、Pull Requestを作成しない。

## 共通品質ゲート

```bash
python3 -m unittest discover -s tests -v
python3 -m src.facility_data validate .
python3 -m src.facility_data build .
```

- [ ] `git diff --check`が成功する
- [ ] buildを2回実行して同一hashになる
- [ ] Place削除がない
- [ ] 既存PlaceのUUID変更がなく、`name`変更は意図した検索入力修正だけである
- [ ] current OSM IDが重複していない
- [ ] 公開Feature数と正本のpublic Place数が一致する
- [ ] `sourceAttributions`が実際の寄与ソースだけを含む
- [ ] clean cloneでtests、validate、buildが成功する
- [ ] exact commit SHAのGitHub Actionsが成功する

Pull Requestでは、`Validate data`の実行結果を対象commitで確認する。workflowが実行されていない場合は、成功とは扱わず原因を確認する。

## 自動化頻度の目安

| 対象 | 目安 |
|---|---|
| WAM相談支援 | 年2回の公式公開後 |
| OSM | 四半期または必要時 |
| 町名GeoJSON | 四半期または必要時 |
| 依存関係 | 月1回以下 |

## 将来候補

OSM候補の3票合議は実装済みである。`review_hold`自動移行と画像権利の自動検証は現在の実行経路にない。追加する場合は、実行経路・tests・失敗時の扱い・文書を同じ変更で整える。
