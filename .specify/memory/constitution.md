<!--
Sync Impact Report
- Version change: 0.0.0 → 1.0.0
- Modified principles: none; initial project constitution
- Added sections: Data and publication constraints; Development workflow
- Removed sections: template placeholders
- Deferred items: none
-->

# 千代田区主要施設データベース憲章

## Core Principles

### I. 正本と生成物を分離する

`data/registry.json`をPlaceの唯一の正本として扱う。検索入力と保持済み外部snapshotを正本の入力として扱う。公開GeoJSONとmanifestを正本から決定的に生成する。生成物を直接編集してはならない。

この原則は、手動変更の場所を限定し、再生成による再現性を守る。

### II. 出典と判断履歴を保持する

外部参照の現在値と過去値を`externalRefs`へ保持する。外部参照を差し替えるとき、旧参照を削除せず`superseded`として残す。正本の変更には、短い監査記録と変更時刻を残す。取得時刻と判断時刻を同一視してはならない。LLMの長い推論本文を保存してはならない。

この原則は、公開データの再検証と、保守判断の追跡可能性を守る。

### III. 誤同定を避ける

WAM、OpenStreetMap (OSM)、検索入力座標の順で代表点を採用する。OSMの自動同定には型付きID、QID、名称、距離、既存current参照の独立した制約を適用する。曖昧な候補を自動採用してはならず、人手確認へ送る。外部ソースから消えたことだけを理由にPlaceを削除してはならない。閉鎖または非公開のPlaceを再同定対象へ含めてはならない。

この原則は、誤案内と意図しない削除を最小化する。

### IV. 検証を変更の完了条件にする

変更前に対象範囲と既存状態を確認する。実装変更には、再現可能なテストまたは検証ケースを伴わせる。変更後に全tests、`python3 -m src.facility_data validate .`、必要な決定的build、`git diff --check`を実行する。失敗した検証を成功として報告してはならない。

この原則は、データ・コード・生成物の不整合を早期に検出する。

### V. 公開範囲とライセンスを守る

公開GeoJSONには、公開対象Placeの利用に必要な画像、OSM属性、WAM属性、出典帰属だけを含める。監査記録、外部参照履歴、内部判断情報、非公開Placeを公開物へ含めてはならない。取得データの版、取得時刻、SHA-256、ライセンス、帰属、加工内容を記録する。認証情報と不要な個人情報をrepositoryへ保存してはならない。

この原則は、利用者への説明責任と、意図しない情報公開の防止を両立する。

## Data and publication constraints

- `data/registry.json`だけをPlace正本として編集する。
- `dist/public/places.geojson`は`visibility.status == "public"`のPlaceだけから生成する。
- WAMの取込対象は保守仕様で定義した相談支援サービスに限定する。
- OSM取得は地域範囲と50メートル距離条件を守り、施設ごとのN+1問い合わせを行わない。
- 空のsnapshotを削除指示として扱わない。
- `responseRetained=false`の外部応答本文または生成diffを追跡しない。

## Development workflow

1. `main`を最新化し、作業branchを作成する。
2. 既存の仕様、実装、workflow、生成物、testsを確認する。
3. 仕様を`specs/`へ作成し、必要ならclarify、plan、tasksの順に進める。
4. 小さなTDD単位で実装し、担当者と独立したレビューを行う。
5. 全tests、repository validator、決定的build、`git diff --check`を実行する。
6. 差分と生成物を確認してcommitし、feature branchへpushする。
7. push後にremote SHAと対象CI workflowを確認する。

## Governance

この憲章は、仕様、実装、workflow、tests、レビューの判断基準を定める。変更者は、憲章へ反する複雑さ、公開範囲の拡大、検証ゲートの省略を導入してはならない。例外が必要な場合、理由、影響範囲、移行方法、検証方法を同じ変更で記録する。

憲章を変更するとき、変更理由とSync Impact Reportを本文冒頭へ記録する。原則の追加または意味の拡張はMINOR、原則の削除または互換性を壊す再定義はMAJOR、文言の明確化はPATCHとしてsemantic versioningに従いversionを更新する。作業者は変更後に関連するspec、tests、workflow、文書を確認する。

**Version**: 1.0.0 | **Ratified**: 2026-08-28 | **Last Amended**: 2026-08-28
