# Spec Delta

## Purpose

自動関連付けの三者判断が単一モデルの反復にならないよう、独立した接続先とモデルを検証します。

## ADDED Requirements

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
