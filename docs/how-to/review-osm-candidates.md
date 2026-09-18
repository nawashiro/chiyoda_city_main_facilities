# OSM 候補をレビューする

この手順は、`needs_review` の施設候補を確定する作業者向けです。

## 事前条件

作業者は、GitHub の Issue 編集、ブランチへの書込み、Pull Request 作成に必要な権限を持ちます。

作業者は、`osm-human-review` ラベル付きの open Issue を使います。Issue 本文はレビュー用メタデータを含みます。

## 1. レビュー対象を開く

作業者は Issue からレビュー用ブランチの `reports/osm-review-needed.yaml` を開きます。

## 2. 候補を一つ選ぶ

作業者は各 `確認対象` の `選択肢` を編集します。

作業者は、採用する候補文字列を変えず、その値だけを `true` にします。他の候補はすべて `false` にします。

```yaml
選択肢:
  "候補 node/123: 施設名": true
  "候補なし（どの候補とも一致しない）": false
```

一致候補がない場合、作業者は `候補なし（どの候補とも一致しない）` だけを `true` にします。

作業者は `検索ID`、`施設名`、`自動取り込みしない理由`、`schemaVersion`、`reportSha256` を変更しません。

## 3. 全対象を確認してコミットする

作業者は、全 `確認対象` で `選択肢` の `true` が一つだけであることを確認します。

作業者は YAML の変更を GitHub 上でコミットします。

## 4. 適用を依頼する

作業者は Issue 本文の `<!-- osm-apply -->` を含むチェック行だけをチェック済みにします。

workflow は Issue 編集を受けて適用します。workflow は更新、検証、テスト、JSON-LD の再現性確認を実行します。

成功時、workflow は Pull Request を作成し、Issue へ URL をコメントして Issue を閉じます。

失敗時、workflow は Pull Request を作成せず、Issue を閉じません。作業者は Actions の失敗ログを確認し、YAML と元 artifact の整合を確認します。
