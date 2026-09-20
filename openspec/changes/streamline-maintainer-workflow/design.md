# Design

## Context

proposal.md の Why を参照します。現行の `src.facility_data build` は repository validation の後に canonical path を返すだけで、公開コピーを生成しません。`fac` は JSON-LD validation と OSM search input 操作だけを公開し、通常の検証は文書内の複数の低レベルコマンドに分散しています。

`site/places.jsonld` は canonical JSON-LD の byte-for-byte 公開コピーです。外部データ更新 workflow は canonical を更新しますが、このコピーを同期しません。

## Goals / Non-Goals

**Goals:**

- maintainer-facing な build / verify 操作を `./fac` に追加する。
- build を唯一の公開コピー同期境界にする。
- verify を非変更の検査境界にする。
- SpecKit と重複した文書手順を除去する。
- OpenSpec durable specs を strict validation で警告なく維持する。

**Non-Goals:**

- canonical Place record、`schema:geo`、公開 distribution、release artifact、OSM review の意味を変更しない。
- GitHub Actions に公開コピー同期を移さない。
- `./fac` を一般的な JSON editor や source-update CLI に拡張しない。
- formatter で CJK / ASCII 境界空白を強制的に挿入しない。

## Decisions

### `fac` が build と verify の公開入口を持つ

`src.fac_cli` に root を省略可能な `build` と `verify` subcommand を追加します。既存の `./fac` launcher を維持するため、作業者は repository root で短い command を実行できます。

`build` は `facility_data.build_repository(root)` による repository validation を最初に行い、成功後に canonical bytes を temporary file 経由で `site/places.jsonld` に置換します。validation failure と copy failure は non-zero exit とし、validation failure では既存 public copy を残します。

`verify` は `build` を呼ばず、全 `unittest`、repository validation、canonical JSON-LD validation、canonical/public bytes の比較、`git diff --check` を順に実行します。`verify` 自身は write helper、copy、source update を呼びません。

代替案は `verify` が `build` を実行する方式です。検証が追跡対象ファイルを変更し、stale copy を発見できなくなるため採用しません。

### 公開コピー同期は build に限定する

`site/places.jsonld` の更新を `./fac build` に限定します。tutorial は `build` の後に `verify` を実行し、手動 `cp` / `cmp` を示しません。

代替案は GitHub Actions に同期を移す方式です。現行 workflow の責務と実装を変え、ローカルで公開結果を確認する最短経路を失うため採用しません。

### verify は既存の検証を合成する

verify は既存の validation functions と test suite を合成し、新しい並行した validator を実装しません。失敗した検査の command と出力をそのまま返し、次の検査を実行しません。

文書本文の文字列を固定する tests は削除または意味的な CLI contract test に置換します。文書の正確な文言や行数は公開 API ではありません。

### Prettier を Markdown の基準 formatter にする

Prettier を repository-local dev dependency とし、Markdown を format / check できる script を追加します。既存の境界空白は人がレビューできる一回の文書差分で CJK と ASCII 間の空白ありへ揃えます。Prettier はこの空白を自動挿入しないため、独自 spacing formatter は追加しません。

代替案は custom rule による境界空白の自動修正です。通常の Markdown formatting を超える独自規約となるため採用しません。

### SpecKit を完全に削除し、OpenSpec を残す

`.specify/` をその内部参照とともに削除します。`.hermes/skills/openspec-*`、`openspec/specs/`、archive、in-flight change は維持します。

archive で durable specs に移した Purpose の strict-warning は、対象 spec の Purpose を 50 文字以上の正確な説明へ直します。

### 文書は操作と可視結果だけを扱う

`first-data-change` は canonical edit、`./fac build`、`./fac verify`、PR 差分確認へ絞ります。`verification` は command の契約と最小診断へ縮めます。

release how-to は workflow 成功と public asset の最小確認だけを残し、published release の復元は別 how-to に分離します。OSM review how-to は committed YAML / PR、merge 後の workflow、production PR のみを説明します。artifact download、run ID、hash binding、重複割当などの内部実装は OpenSpec と tests に置きます。

## Risks / Trade-offs

- [build が public copy を上書きする] → validation 成功後だけ temporary file を atomic replace する。
- [verify が長い] → 通常経路を一つにして、個別の診断 command は reference に限定する。
- [Prettier が spacing を自動統一しない] → 初回だけレビュー済み文書差分で揃え、以後は formatter が既存表記を保持する。
- [SpecKit deletion が隠れた automation を壊す] → repository 外の参照がないことを確認し、削除後に repository tests と CI configuration validation を実行する。

## Migration Plan

1. `adopt-standards-jsonld` archive と durable specs の Purpose 修正を同じ branch で確認する。
2. `build` / `verify` の focused tests を先に追加する。
3. CLI と atomic public-copy synchronization を実装する。
4. SpecKit を完全に削除し、Prettier と Markdown scripts を追加する。
5. 文書を最短経路へ更新し、release restore how-to を分離する。
6. focused tests、全 tests、`./fac build`、`./fac verify`、OpenSpec strict validation、formatter check、`git diff --check` を実行する。
7. failure 時は `./fac build` 追加前の手動 public-copy 同期手順へ戻せるよう、commit / PR を revert する。
