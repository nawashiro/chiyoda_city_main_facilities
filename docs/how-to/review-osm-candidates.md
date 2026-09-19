# OSM 候補をレビューする

この手順は、`needs_review` の施設候補を確定する作業者向けです。

## 事前条件

作業者は、レビュー用 Pull Request への書込みと merge に必要な権限を持ちます。

## 1. レビュー対象を開く

作業者は、`automation/osm-review-<Actions run ID>` ブランチから作成された下書き Pull Request を開き、`reports/osm-review-needed.yaml` を確認します。

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

作業者は YAML の変更を Pull Request にコミットします。

## 4. レビュー Pull Request を merge する

作業者は、通常のレビューと承認を完了して下書き Pull Request を merge します。Issue 本文の編集やチェック操作は適用経路に含まれません。

merge を受けた workflow は、merge 済みの `reports/osm-review-needed.yaml` を読み、ブランチ名の Actions run ID に対応する artifact を再取得します。YAML の `reportSha256` が artifact 内の candidate report と一致し、各選択が report 内の候補だけを参照し、OSM record の重複割当がない場合にだけ適用用 Pull Request を作成します。

失敗時、workflow は適用用 Pull Request を作成しません。作業者は Actions の失敗ログを確認し、レビュー Pull Request の YAML と元 artifact の整合を確認します。
