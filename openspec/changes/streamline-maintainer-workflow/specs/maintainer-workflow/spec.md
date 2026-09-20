# Spec Delta

## Purpose

作業者が canonical JSON-LD と公開コピーを安全に更新し、変更しない検証を一貫した `./fac` の操作で実行できるようにします。

## ADDED Requirements

### Requirement: 作業者は公開コピーを build できる
リポジトリ root の `./fac build` SHALL canonical JSON-LD を検証し、成功時だけ `data/places.jsonld` とバイト単位で同一の `site/places.jsonld` を生成または更新します。canonical JSON-LD の検証に失敗した場合、コマンド MUST 非ゼロで終了し、既存の公開コピーを変更しません。

#### Scenario: 正本から公開コピーを同期する
- **WHEN** 作業者が有効な canonical JSON-LD を持つリポジトリ root で `./fac build` を実行する
- **THEN** `site/places.jsonld` は `data/places.jsonld` とバイト単位で一致する

#### Scenario: 不正な正本では公開コピーを残す
- **WHEN** canonical JSON-LD の検証が失敗した状態で作業者が `./fac build` を実行する
- **THEN** コマンドは非ゼロで終了し、既存の `site/places.jsonld` は変更されない

### Requirement: 作業者は変更しない検証を実行できる
リポジトリ root の `./fac verify` SHALL 全 test suite、canonical JSON-LD の検証、公開コピーの byte-level 整合性、`git diff --check` を実行します。`./fac verify` MUST `build` を実行せず、追跡対象ファイルを変更しません。

#### Scenario: 同期済みの変更を検証する
- **WHEN** canonical JSON-LD と公開コピーが一致し、全検査が成功する状態で作業者が `./fac verify` を実行する
- **THEN** コマンドはゼロで終了し、追跡対象ファイルを変更しない

#### Scenario: stale な公開コピーを検出する
- **WHEN** `site/places.jsonld` が canonical JSON-LD と一致しない状態で作業者が `./fac verify` を実行する
- **THEN** コマンドは非ゼロで終了し、公開コピーを同期または変更しない

#### Scenario: 書式エラーを検出する
- **WHEN** 作業ツリーの差分に `git diff --check` が検出する書式エラーがある状態で作業者が `./fac verify` を実行する
- **THEN** コマンドは非ゼロで終了し、追跡対象ファイルを変更しない
