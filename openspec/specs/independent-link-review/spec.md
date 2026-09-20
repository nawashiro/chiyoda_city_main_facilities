# independent-link-review Specification

## Purpose
自動関連付けにおける三者判断の独立性を保証するため、各判断者の正規化済み接続先とモデルが重複しないことを検証し、投票履歴を公開データから分離したうえで、必要な人手レビューを commit 済み YAML と PR で管理します。

## Requirements

### Requirement: Independent model configurations
システム SHALL 三者それぞれのAPI key、base URL、modelを設定できます。
実行前に、正規化した`(base_url, model)`の組が三者で重複しないことを検証します。

#### Scenario: Duplicate model configuration is supplied
- **WHEN** 二者以上が同じ正規化済み接続先とmodelを使います
- **THEN** システムは照合を開始せず明確なエラーを返します

### Requirement: Decision history stays outside public data
システム MUST 三者の投票内容を公開Place JSON-LDへ保存しません。

#### Scenario: A link decision is published
- **WHEN** 照合結果を公開データへ反映します
- **THEN** JSON-LDには投票ログを含めません

### Requirement: Committed review artifact
システム SHALL 人手OSM reviewをcommit済みreview YAMLとPRで実施します。
システム MUST Issue本文を候補選択の編集面として使いません。

#### Scenario: Candidate requires human review
- **WHEN** 自動照合がreviewを要求します
- **THEN** システムはartifact-bound review YAMLをPRで提供します
