# Design

## Context

現行のリリースは2本立てです。`release-jsonld.yml` が `release: published` と手動dry-run(`workflow_dispatch` + `tag`入力)を持ち、人がGitHub Releaseを作成・公開したときだけ検証と `places-<tag>.jsonld` の添付が走ります。Pages配布物は `site/` 一式(landing page + `places.jsonld` + 両ミラー)ですが、Releaseに凍結されるのはJSON-LD単体です。`scripts/prepare_release_jsonld.py` はJSON-LD単体を検証・複製します。手動dry-runのartifactを人がReleaseへ運んだ痕跡が、v3.0.0の重複資産です。

ビルドは `python3 -m src.facility_data build .` が `site/places.jsonld` と `site/mirrors/*.json` を生成し、両ミラーはコミット済み(`imports/openstreetmap/raw.json` は除く)なので、タグのcheckoutだけで再現します。Pagesの `publish-pages.yml` は「checkoutコミット == origin/mainのHEAD」の検査を公開前に持っています。

## Goals / Non-Goals

Goals

- Actions起動1回で、タグ作成からリリース公開・資産添付まで完了すること。
- Release資産をそのコミットのPages配布物と同等(JSON-LD + 両ミラー)にすること。
- タグ・Releaseの不変性を機械的に守ること。

Non-Goals

- 既存published Release(v3.0.0を含む)の編集・資産整理。
- 月次パイプラインからの自動リリース起動(`workflow_call`連携)。必要になったときに足します。
- landing pageの版固定。

## Decisions

**1. workflowは1本の `release.yml` に統合し、トリガーは `workflow_dispatch` のみ。**
`release: published` トリガーを廃止します。workflow自身がタグとReleaseを作るので、releaseイベントを待つ経路は不要です。GITHUB_TOKENで作成したReleaseはイベントを発火してもworkflowが再帰しないため、廃止で検証経路が消えることはありません。旧 `release-jsonld.yml` は削除します。
代替案(現行の二段構えを維持)は、手作業と手動運搬の混入を今後も生むため採りません。

**2. タグは実行日のUTC日付 `YYYY.MM.DD`、存在したら失敗。**
タグ作成前に `git ls-remote --tags origin` で存在を確認し、存在する場合は明示的なエラーで停止します。サフィックス自動採番(`.1`等)は「意図せず同じ日に2回出す」を隠すので採りません。旧semverタグとの混在は、Release一覧が作成日順のため実害ありません。

**3. 資産は個別ファイル添付。zipバンドルは作らない。**
`dataset-publication` specが配布物単位のライセンス明示を要求するため、資産ごとにライセンスが確定する個別添付にします。`prepare_release_jsonld.py` を `prepare_release.py` に置き換え、`site/` の3資産を `release/` に版号つきで複製します。JSON-LDは既存どおり検証(`validate_published_document`)してから複製し、両ミラーはビルド済みのバイト列を複製します。旧スクリプトは削除します。

**4. 公開前の検査はテスト+ビルド+main最新確認。**
`publish-pages.yml` と同じ「checkoutコミット == origin/main HEAD」検査を公開前に置き、起動時のmainとのずれを防ぎます。dry-runによる人の目視は廃止し、代わりにテスト(`unittest`)とビルド検証がどちらかでも失敗すればReleaseを作らず停止します。Pagesは既にmain pushで全自動公開なので、Release自動化は既存の公開哲学と整合します。

**5. リリースノートはworkflowが生成する。**
softprops/action-gh-release の `body` に固定テンプレート(資産一覧+各資産のライセンス)を渡します。本文と資産の不整合が構造的に起きなくなります。

## Risks / Trade-offs

- [ dry-runの目視検査がなくなる ] → テストとビルド検証で失敗時停止。Pagesは常時最新を公開しているため、Releaseの失敗は配布の欠落にならない。
- [ workflow_dispatchを誤起動して即公開される ] → タグ・Releaseは不変で、逆に取り消しはできない。起動自体を人の判断と位置づける。
- [ 日付タグの衝突 ] → 失敗して止まる。衝突時は人の対処(翌日起動など)に委ねる。

## Migration Plan

1. workflow・スクリプト・テスト・文書を入れ替えてmainにpushします。push自体はリリースを起こしません。
2. 初回のリリースは新しいworkflowの起動で行い、資産3点とノートを確認します。
3. 旧 `release-jsonld.yml` と `prepare_release_jsonld.py` は削除済みのため、追加の撤退作業はありません。

## Open Questions

(なし)
