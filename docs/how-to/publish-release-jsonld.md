# JSON-LD をリリースする

この手順は、検証済みの正本 JSON-LD を GitHub Release で配布する作業者向けです。

## 1. 正本を検証する

作業者は、リリース前に[検証](../reference/verification.md)を実行します。

## 2. GitHub Actions で試行する

作業者は Actions の `release-jsonld` を手動実行し、`tag` に版番号を入力します。

版番号は英数字で始めます。版番号は英数字、`.`、`_`、`-` だけを含めます。

手動実行は dry-run です。workflow は `release/places-<tag>.jsonld` を artifact `release-jsonld-<tag>` としてアップロードします。

作業者は artifact の存在と内容を確認します。

## 3. GitHub Release を公開する

作業者は、配布するタグを対象に GitHub Release を作成します。作業者は Release を published にします。

下書きの作成と既存タグだけでは workflow は起動しません。workflow は Release の公開時に起動します。

workflow は正本を検証し、版付き JSON-LD を作成します。workflow は作成物を artifact と Release 添付へ追加します。

## 4. 配布物を確認する

作業者は Release 添付の `places-<tag>.jsonld` を確認します。作業者は artifact と Release 添付が存在することを確認します。

workflow は入力不能、JSON 不正、JSON-LD 検証失敗、書込失敗で停止します。
