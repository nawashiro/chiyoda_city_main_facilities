# 文書構成

## 目的

READMEへ手順、契約、背景を混在させないでください。
利用者は目的に対応する文書から読み始めます。

## Diátaxisの使い分け

tutorialは、初学者が一つの結果を得るための学習手順です。
how-to guideは、保守者が特定の作業を完了する手順です。
referenceは、CLI、属性、データ契約の正確な一覧です。
explanationは、設計判断と保守方針を説明します。

同じ説明を複数の文書へ複写しないでください。
手順からreferenceへリンクしてください。
referenceから背景が必要な場合、explanationへリンクしてください。

## READMEの役割

READMEは最初の入口です。
READMEは目的、最初の検証、各文書へのリンクを提供します。
詳細な引数、更新手順、データ属性をREADMEへ追加しないでください。

## AIエージェント

AIエージェントは`AGENTS.md`から[執筆規範](../reference/writing-style.md)を読みます。
AIエージェントも、実装とtestsを確認してから文書を更新します。
