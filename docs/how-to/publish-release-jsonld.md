# JSON-LD をリリースする

この手順は、検証済みの正本 JSON-LD を GitHub Release で通常公開する作業者向けです。公開済み版を復元する場合は、[公開済み JSON-LD を復元する](restore-published-jsonld.md)を参照します。

## 1. 正本を検証する

作業者は、リポジトリ root で[検証](../reference/verification.md)を完了します。

```sh
./fac verify
```

## 2. リリース workflow を dispatch する

作業者は、GitHub の **Actions** で **Release JSON-LD snapshot** を選びます。

作業者は **Run workflow** を選び、`tag` に公開する新しいタグを入力して実行します。

作業者は、手動実行が成功したことを Actions で確認します。

## 3. GitHub Release を公開する

作業者は、手動実行と同じタグで GitHub Release を作成します。

作業者は、Release を published にします。

## 4. workflow と公開 asset を確認する

作業者は、Release 公開後に起動した Actions run が成功したことを確認します。

作業者は、GitHub Release に `places-<tag>.jsonld` が公開 asset として存在することを確認します。
