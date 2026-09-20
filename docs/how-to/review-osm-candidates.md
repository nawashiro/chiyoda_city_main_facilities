# OSM 候補をレビューする

この手順は、`needs_review` の施設候補を確定し、production PR に反映する作業者向けです。

## 事前条件

作業者は、review Pull Request と production Pull Request の review、書込み、merge に必要な権限を持ちます。

## 1. review Pull Request と YAML を確認する

workflow が作成した draft Pull Request を開き、Pull Request の差分と `reports/osm-review-needed.yaml` を確認します。

人手 review の編集面は、commit 済みの review YAML とその Pull Request です。Issue 本文やチェック操作で候補を選択しません。

## 2. 候補を選択する

各 `確認対象` の `選択肢` で、採用する候補の値だけを `true` にし、他の候補をすべて `false` にします。

```yaml
選択肢:
  "候補 node/123: 施設名": true
  "候補なし（どの候補とも一致しない）": false
```

一致する候補がない場合は、`候補なし（どの候補とも一致しない）` だけを `true` にします。

変更するのは各 `選択肢` の `true` / `false` だけです。候補文字列、`検索ID`、`施設名`、`自動取り込みしない理由`、`schemaVersion`、その他の YAML の項目は変更しません。

## 3. 選択結果を commit して review Pull Request を merge する

すべての `確認対象` で `true` が一つだけになっていることを確認し、選択結果を review Pull Request に commit します。Pull Request の差分が選択結果だけであることを確認して、通常の review と承認の後に review Pull Request を merge します。

## 4. merge 後の workflow を監視する

review Pull Request の merge 後、GitHub Actions で後続 workflow が完了するまで実行状況と結果を確認します。

workflow が成功すると、選択結果を反映する production Pull Request（適用用 Pull Request）が作成されます。workflow が失敗した場合は production Pull Request は作成されず、失敗したこととその内容が Actions に表示されます。失敗ログを確認し、必要な修正または再実行を行います。

## 5. production Pull Request を review して merge する

作成された production Pull Request の差分とチェック結果を確認します。期待した施設データの変更だけであることを review し、問題がなければ production Pull Request を merge します。
