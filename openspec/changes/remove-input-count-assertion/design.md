# Design

## Context

`test_migration_preserves_targets_and_public_geometry`は、WAMからの移行時に施設を取りこぼさないための番人として、検索入力の総数を固定していました。総数は102、103とデータ追加のたびに更新され、今回106に更新しています。テストの他のassert（公開recordのID一意性、公開recordが宣言済みの検索入力だけであること、`gif-poi`以外の識別子がないこと）は、データが増減しても壊れない振る舞いの不変条件です。

## Goals / Non-Goals

**Goals:**

- 検索入力の総数を固定するassertを取り除く
- 公開recordの不変条件はそのまま残す
- テスト名を実際に検査している内容に合わせる

**Non-Goals:**

- 移行時のUUID一覧をfixtureで固定すること
- 件数の確認を別テストとして残すこと
- データ、CLI、公開物の変更

## Decisions

### 件数はテストしない

件数はデータのスナップショットであり、`./fac in add`と`./fac in rm`は人が明示的に実行する操作です。増減はコミットのdiffに必ず現れ、レビューで確認できます。件数が一致していること自体は振る舞いを守りません。一方、公開recordのID一意性、公開recordが宣言済みの検索入力だけであること、`gif-poi`以外の識別子がないことは、データが増えても意味を持つ不変条件なので残します。

### 移行UUID一覧はfixtureにしない

移行で残すべき施設のUUIDをfixtureに固定する案は、`in rm`で正当に施設を消すたびにfixtureの更新が要り、件数固定と手間が変わりません。移行は完了しており、以後の増減は明示的な操作としてレビューで確認できます。

### テスト名を実態に合わせる

`test_published_places_are_declared_and_unique`に変更します。件数固定や移行の番人を示唆する名前をやめ、検査内容をそのまま表します。

## Risks / Trade-offs

- [件数の増減を検知できなくなる] → `in add`・`in rm`は明示的な操作で、コミットのdiffで確認できる。公開recordの不変条件は残る

## Migration Plan

1. 件数のassertを削除し、`queries`を`declared`の構築に使う
2. テスト名を変更する
3. テストを実行する
4. ロールバックはテストのコミットを戻す

## Open Questions

なし。
