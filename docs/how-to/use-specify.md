# OpenSpec changeを移行の正本として使う（上級者向け補足）

> **適用範囲**
> この補足は、変更がOpenSpecの移行判断または仕様の正本に影響するときだけ使います。通常の1件のPlaceデータ編集には使いません。通常作業は[最初のJSON-LDデータ変更](../tutorials/first-data-change.md)または[Placeを直接保守する](maintain-a-place.md)を参照してください。
>
> 初学者はこの文書から開始しません。OpenSpec change、正本データ、実装の境界をレビューできる保守者を対象にします。

このrepositoryでは、`adopt-standards-jsonld` changeのproposal、design、specs、tasksを移行の判断記録と実装順序の正本として扱います。旧保守規約や実装だけを根拠に、移行の範囲を決めません。

## 1. OpenSpec changeの正本を確認する

change全体と成果物を、次の順序で確認します。

- [adopt-standards-jsonld change](../../openspec/changes/adopt-standards-jsonld/): change全体
- 目的と設計: [proposal.md](../../openspec/changes/adopt-standards-jsonld/proposal.md)、[design.md](../../openspec/changes/adopt-standards-jsonld/design.md)
- 仕様群: [specs/](../../openspec/changes/adopt-standards-jsonld/specs/)、[public-jsonld-dataset](../../openspec/changes/adopt-standards-jsonld/specs/public-jsonld-dataset/spec.md)、[related-record-links](../../openspec/changes/adopt-standards-jsonld/specs/related-record-links/spec.md)、[dataset-publication](../../openspec/changes/adopt-standards-jsonld/specs/dataset-publication/spec.md)、[independent-link-review](../../openspec/changes/adopt-standards-jsonld/specs/independent-link-review/spec.md)
- 実装順序: [tasks.md](../../openspec/changes/adopt-standards-jsonld/tasks.md)

repositoryのルートで、changeの状態と整合性を確認します。

```bash
openspec status --change adopt-standards-jsonld --json
openspec validate adopt-standards-jsonld --strict
```

`status`の`artifacts`、`applyRequires`、`nextSteps`を確認します。`openspec validate`はOpenSpec成果物の整合性を確認します。いずれかが失敗した場合、正本データや実装を変更せずに停止します。

実装を始める場合は、statusで示されたschemaを前提にapply instructionsを取得します。

```bash
openspec instructions apply --change "adopt-standards-jsonld" --json
```

出力の`contextFiles`とタスクを読み、仕様にない範囲を推測で追加しません。仕様と実装が一致しない場合、正本データを先に変更せず、proposal、design、specs、tasksの境界をレビューします。

## 2. clean worktreeを確認してからbranchを作る

作業branchを作る前に、作業ツリーを確認します。

```bash
git status --short --branch
```

branch名の行以外に出力がある場合、未確認の変更が残っています。変更を保存、commit、または別のcheckoutへ退避するまで作業を開始しません。

作業ツリーがcleanであることを確認した後、新しいbranchを作ります。

```bash
git switch -c spec/<change-name>
git status --short --branch
```

既存の適切な作業branchを使う場合も、clean worktreeの確認を先に実行します。branchを切り替えた後に、OpenSpecの状態を再確認します。

## 3. OpenSpecの権威とcanonical JSON-LDを分ける

OpenSpec成果物は移行の判断、契約、実装順序を決めます。`data/places.jsonld`は公開Placeデータのcanonical JSON-LD（正本）です。

- `data/places.jsonld`だけを正本データとして編集します。
- Git commit、Pull Request（PR）、Releaseへ変更履歴を残します。
- GitHub Pagesのcurrent JSON-LDとGitHub Releaseの版固定snapshotは、正本から作る派生公開物です。
- 派生公開物を手編集しません。
- OpenSpecのproposal、design、specs、tasksを、実装だけで置き換えません。

JSON-LDの属性、geometry、外部識別子、関連URIの規則は、次の文書を参照します。

- [データモデル](../explanation/data-model.md)
- [属性リファレンス](../reference/attributes.md)

この手順では、OpenSpecの権威とcanonical JSON-LDの編集対象を混同しません。

## 4. 正本JSON-LDを編集する

OpenSpecのstatus、strict validation、変更範囲を確認した後、タスクがcanonical JSON-LDの変更を求める場合だけ編集します。

```bash
$EDITOR data/places.jsonld
```

`EDITOR`が未設定の場合は、次のfallbackを使います。

```bash
vi data/places.jsonld
```

対象の`@id`を検索し、対象recordだけを編集します。対象外の`record`の順序と内容を変更しません。

編集後に、正本以外のファイルを自動生成しません。公開distribution、Release snapshot、manifestを手編集しません。

## 5. validationとbuildを区別する

次のコマンドは、確認対象が異なります。

| コマンド | 確認対象 | 現行canonical JSON-LD modeの書き込み |
| --- | --- | --- |
| `python3 -m src.fac_cli jsonld-validate data/places.jsonld` | 指定したJSON-LDの構文、識別子、型、geometry、外部識別子 | なし |
| `python3 -m src.facility_data validate .` | repository内のデータ、入力、snapshotの整合性 | なし |
| `openspec validate adopt-standards-jsonld --strict` | OpenSpec changeの成果物と仕様の整合性 | なし |
| `python3 -m src.facility_data build .` | repository validationとcanonical JSON-LDのbuild経路 | `data/places.jsonld`を再生成しない |

このrepositoryでは`data/places.jsonld`が存在します。そのため`python3 -m src.facility_data build .`はrepositoryを検証し、既存のcanonical JSON-LDのpathを返します。buildを実行しても、`data/places.jsonld`や派生公開物を自動更新しません。`build`を`validate`やOpenSpecのstrict validationの代わりに使いません。

変更後は、次の標準検証を順番に実行します。

```bash
python3 -m src.fac_cli jsonld-validate data/places.jsonld
python3 -m src.facility_data validate .
openspec validate adopt-standards-jsonld --strict
python3 -m unittest discover -s tests -v
git diff --check
```

OpenSpec changeがcanonical JSON-LDまたはbuild behaviorに触れる場合、次のbuildと`cmp`の手順も標準の必須検証です。

```bash
cp data/places.jsonld /tmp/places.jsonld
python3 -m src.facility_data build .
python3 -m src.fac_cli jsonld-validate data/places.jsonld
cmp /tmp/places.jsonld data/places.jsonld
```

仕様だけを変更するOpenSpec changeでは、このbuildと`cmp`の手順は必須ではありません。
canonical JSON-LDまたはbuild behaviorに触れるchangeでbuildまたは`cmp`が失敗した場合、PRを提出せず、build経路または正本の変更理由を確認します。

## 関連文書

- [データモデル](../explanation/data-model.md): JSON-LDの役割と標準語彙
- [CLIリファレンス](../reference/cli.md): JSON-LD検証CLIの引数
- [更新チェックリスト](source-update-checklist.md): 更新前後の確認項目
- [最初のJSON-LDデータ変更](../tutorials/first-data-change.md): branch、検証、レビューの基本手順
- [Placeを直接保守する](maintain-a-place.md): 1件のPlaceを直接編集する手順

## commit/PRの境界と停止条件

commit前に、対象recordと変更範囲を確認します。

```bash
git status --short
git diff -- data/places.jsonld
git diff --stat
git diff --check
```

次の条件をすべて確認した後に、意図したファイルだけをstageします。

- OpenSpecの`status`と`openspec validate ... --strict`が成功しています。
- JSON-LD、repository、tests、`git diff --check`の標準検証が成功しています。
- canonical JSON-LDまたはbuild behaviorに触れるchangeでは、build再現性と`cmp`の検証も成功しています。
- 仕様だけを変更するchangeでは、build再現性と`cmp`は必須条件ではありません。
- 意図した`@id`のrecordとプロパティだけが変わっています。
- 派生公開物と不要なファイルが変わっていません。

```bash
git add data/places.jsonld
git diff --cached -- data/places.jsonld
git diff --cached --check
git commit -m "data: update canonical JSON-LD"
git show --stat --oneline HEAD
```

commitはローカル検証の境界です。PRはcommit後に作成し、PRのCIが成功するまでmergeしません。OpenSpec成果物、production code、正本データの変更範囲が混ざる場合は、対象を分離してレビューします。

次の条件では停止します。

- branchを作る前のworktreeがcleanではありません。
- `openspec status`または`openspec validate adopt-standards-jsonld --strict`が失敗します。
- 標準検証または`git diff --check`が失敗します。
- canonical JSON-LDまたはbuild behaviorに触れるchangeで、buildまたは`cmp`が失敗します。
- 差分に意図しないproduction code、OpenSpec file、派生公開物が含まれます。
- 仕様と実装が矛盾するか、タスクの範囲を判断できません。

失敗を無視、推測で回避、無関係な変更で修正せず、出力を確認して正本のレビューへ戻ります。停止条件が解消するまでcommitまたはPRを作成しません。
