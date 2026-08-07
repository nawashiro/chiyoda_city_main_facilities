# ソースを更新する

更新前後の確認は[更新チェックリスト](source-update-checklist.md)を使ってください。

## WAMを更新する

WAMは相談支援4サービスだけを取得します。

```bash
AT=$(date --iso-8601=seconds)
python3 -m src.retrieve_wam . --release <YYYYMM> --at "$AT"
python3 -m src.facility_data update . --source wam --at "$AT"
python3 -m src.facility_data validate .
```

`facility_data update`は正本、公開GeoJSON、manifestを再生成します。

## OSMを更新する

```bash
export LLM_API_KEY="..."
export LLM_MODEL="使用するモデル名"
AT=$(date --iso-8601=seconds)
python3 -m src.retrieve_osm . --at "$AT"
python3 -m src.resolve_osm_candidates .
python3 -m src.facility_data update . --source openstreetmap --at "$AT"
python3 -m src.facility_data validate .
```

OpenAI以外を使う場合、`LLM_BASE_URL`を設定してください。
GitHub Actionsでは、`LLM_API_KEY`をsecret、モデル設定をvariableへ登録してください。

合議不成立では、workflowが候補確認Issueを作ります。
JSONを直接編集しないでください。

## 町名を更新する

```bash
AT=$(date --iso-8601=seconds)
python3 -m src.retrieve_towns . --commit <40-character-commit-sha> --at "$AT"
python3 -m src.facility_data build .
python3 -m src.facility_data validate .
```

町名は正本へ書き込みません。
公開buildがPointと町名Polygonから導出します。

## GitHub Actionsのartifactを取り込む

```bash
gh run download <RUN_ID> --name <ARTIFACT_NAME> --dir /tmp/chiyoda-update
cp -a /tmp/chiyoda-update/. .
python3 -m src.facility_data validate .
python3 -m unittest discover -s tests -v
python3 -m src.facility_data build .
git diff --check
git diff --stat
git add inputs imports data dist reports
git commit -m "data: apply source update"
git push -u origin data/<作業内容>
```

UUID変更、Place削除、意図しない削除を確認してからcommitしてください。
WAMと町名artifactは14日間、OSM artifactは30日間保存します。
