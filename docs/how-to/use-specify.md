# Spec Kitを使って仕様を保守する

このrepositoryはGitHub Spec Kitを使って仕様駆動の変更を管理します。

## 事前準備

uvをインストールします。

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
specify version
```

`specify`がPATHにない場合は、shellのPATHへuvのtool binを追加するか、次の一時実行を使います。

```bash
uvx --from git+https://github.com/github/spec-kit.git specify version
```

既存の作業branchを確認します。

```bash
git status --short --branch
git switch -c <作業branch>
```

## 仕様を作成する

機能の目的と利用者の行動を短く記述します。

```text
/speckit.specify <作りたい機能の目的と利用者の行動>
```

仕様は`specs/NNN-<feature-name>/spec.md`へ保存します。

仕様には次を記述します。

- 利用者シナリオ
- 受入シナリオ
- 機能要件
- 境界条件
- 測定可能な成功基準
- 前提条件と依存関係

仕様は技術実装の手順ではなく、利用者の価値と検証可能な要求を記述します。

## 実装計画へ進む

仕様の曖昧さを解消します。

```text
/speckit.clarify
```

実装方針を作成します。

```text
/speckit.plan <既存の実装制約と採用する方針>
```

作業を依存関係付きの小さなtaskへ分解します。

```text
/speckit.tasks
```

実装前に仕様、plan、tasksの整合性を確認します。

```text
/speckit.analyze
```

## このrepository固有の確認

Spec Kitの検証だけで、データの正しさを判定してはなりません。実装変更後は、次の検証を実行します。

```bash
python3 -m unittest discover -s tests -v
python3 -m src.facility_data validate .
python3 -m src.facility_data build .
git diff --check
```

公開GeoJSONを直接編集してはなりません。`data/registry.json`、検索入力、保持済みsnapshotなど、保守仕様が定める正本または入力だけを変更します。

作業を完了するとき、仕様、実装、workflow、tests、生成物の差分を確認してからcommitとpushを行います。

## 構成

- `.specify/memory/constitution.md`: このrepositoryの開発原則
- `.specify/templates/`: 仕様、plan、tasksのテンプレート
- `.specify/commands/`: generic agent向けのSpec Kit command prompt
- `specs/`: featureごとの仕様と計画
