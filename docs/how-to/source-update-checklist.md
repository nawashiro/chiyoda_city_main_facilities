# OSM・WAMソース更新チェックリスト

## 目的と停止規則

初めて更新する人は、上から順に5つのゲートを通過させる。詳細な取得規則は[ソースを更新する](update-source-data.md)を参照する。canonical JSON-LDは`data/places.jsonld`である。

いずれかのゲートで失敗、mismatch、`unresolved query`、`missing review`、秘密値の露出（secret exposure）、`cmp`失敗があれば停止する。原因を解消するまでPull Request（PR）を提出しない。

## 早期分岐: 再同定

検索入力だけを修正し、raw snapshotを再取得しない場合は、Gate 1より前に[Re-identify retained source snapshots workflow](../../.github/workflows/reidentify-sources.yml)を選ぶ。raw snapshotの取得が必要な場合は、Gate 1で新規取得ルートを選ぶ。

- 再同定では、OSMとWAMのraw bytes、`retrieval.json`、`rawSha256`、`rawVersion`を変更しない。
- 再同定では、変更したqueryだけを確認し、`unresolved query`を推測で埋めない。
- bytes、hash、metadataの不一致またはレビュー不足なら停止し、PRを提出しない。

## Gate 1: route selection（ルート選択）

- [ ] **合格条件:** WAMの公開版を更新する場合は[Update WAM data workflow](../../.github/workflows/update-wam.yml)を選ぶ。OSM snapshotを更新する場合は[Update OpenStreetMap data workflow](../../.github/workflows/update-osm.yml)を選ぶ。検索入力だけを修正する場合は、早期分岐の再同定を選ぶ。
- **不合格条件:** 対象ソース、公開版、query、またはルートが不明である。再同定で外部取得を行う。誤ったworkflowを選ぶ。停止し、PRを提出しない。

## Gate 2: clean worktree / snapshot（作業ツリーとsnapshot）

- [ ] **合格条件:** 作業branchを作成し、開始時の`git status --short`が空である。対象artifactだけを取り込む。`rawSha256`がraw bytesと一致し、`rawVersion`、`retrievedAt`、取得元URLがsnapshotと一致する。raw、normalized、report、YAML、PR、artifact、ログに秘密値を含めない。
- **不合格条件:** 無関係な変更、raw bytesまたはhashの不一致、metadataの不一致、秘密値の露出（secret exposure）がある。停止し、PRを提出しない。

## Gate 3: source / review integrity（ソースとレビューの整合性）

- [ ] **合格条件:** raw、normalized、reportのsource IDとquery IDが一致し、`config/sources.json`の条件と外部IDが一致する。OSMではcandidate reportと`reports/osm-review-needed.json`・`reports/osm-review-needed.yaml`の`reportSha256`が一致し、YAMLをコミットして[OSM人手レビュー適用workflow](../../.github/workflows/apply-osm-review.yml)のPull Requestで確認する。各queryで候補または「候補なし」の`true`を1つだけ指定し、識別子を推測しない。
- **不合格条件:** sourceまたはqueryのmismatch、`unresolved query`、`missing review`、YAML未確認、候補の未選択または複数選択、report hashの不一致、推測した識別子がある。停止し、PRを提出しない。

## Gate 4: canonical JSON-LD and reproducibility validation（canonical JSON-LDと再現性検証）

- [ ] **合格条件:** `data/places.jsonld`だけをcanonical JSON-LDとして直接レビューし、構造と外部IDを確認する。次の全コマンドが成功し、`cmp`がbyte単位の一致を示す。

```bash
cp data/places.jsonld /tmp/places.jsonld
python3 -m src.facility_data build .
python3 -m src.fac_cli jsonld-validate data/places.jsonld
cmp /tmp/places.jsonld data/places.jsonld
```

- **不合格条件:** JSON-LD検証、build、または`cmp`が失敗する。canonical JSON-LDに意図しない差分、秘密値、推測した識別子がある。停止し、PRを提出しない。

## Gate 5: final PR gate（最終PRゲート）

- [ ] **合格条件:** 意図したファイルだけを差分に含め、必要な人手レビューを完了する。対象commitの[Validate data workflow](../../.github/workflows/validate.yml)が成功する。次の全コマンドが成功し、PR本文、レビューYAML、artifact、ログに秘密値がない。

```bash
python3 -m unittest discover -s tests -v
python3 -m src.facility_data validate .
python3 -m src.fac_cli jsonld-validate data/places.jsonld
git diff --check
```

- **不合格条件:** いずれかのコマンド、workflow、レビューが失敗または未実行である。未解決のquery、mismatch、`missing review`、secret exposure、意図しない差分がある。停止し、PRを提出しない。
