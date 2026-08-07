# Agent instructions

文書を変更する前に、[執筆規範](docs/reference/writing-style.md)を読んでください。

文書はDiátaxisの区分へ配置してください。
実装、workflow、生成物、testsを確認してから文書を更新してください。
文書変更後、全tests、`python3 -m src.facility_data validate .`、`git diff --check`を実行してください。
