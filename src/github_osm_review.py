from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from pathlib import Path
from typing import Any


_METADATA = re.compile(r"<!-- osm-review-metadata:([A-Za-z0-9_-]+) -->")
_CHOICE = re.compile(
    r"^- \[([ xX])\] <!-- osm-choice:([0-9a-f-]+):(link|reject):([^ ]+) -->",
    re.MULTILINE,
)
_APPLY = re.compile(r"^- \[[xX]\] <!-- osm-apply -->", re.MULTILINE)


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _encode_metadata(document: dict[str, Any]) -> str:
    payload = json.dumps(document, ensure_ascii=True, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def parse_issue_metadata(body: str) -> dict[str, Any]:
    match = _METADATA.search(body)
    if match is None:
        raise ValueError("OSM review metadata is missing")
    encoded = match.group(1)
    encoded += "=" * (-len(encoded) % 4)
    try:
        metadata = json.loads(base64.urlsafe_b64decode(encoded))
    except (ValueError, json.JSONDecodeError) as error:
        raise ValueError("OSM review metadata is invalid") from error
    required = {"schemaVersion", "runId", "artifactName", "reportSha256", "queryIds"}
    if metadata.get("schemaVersion") == 3:
        required.add("reviewBranch")
        if not isinstance(metadata.get("reviewBranch"), str) or not metadata["reviewBranch"]:
            raise ValueError("OSM review branch is invalid")
    if set(metadata) != required or metadata.get("schemaVersion") not in {2, 3}:
        raise ValueError("OSM review metadata has an unsupported shape")
    if not isinstance(metadata["queryIds"], list) or not metadata["queryIds"] or not all(isinstance(item, str) for item in metadata["queryIds"]):
        raise ValueError("OSM review query IDs are invalid")
    if not re.fullmatch(r"[0-9]+", str(metadata["runId"])):
        raise ValueError("OSM review run ID is invalid")
    if not isinstance(metadata["artifactName"], str) or not metadata["artifactName"]:
        raise ValueError("OSM review artifact name is invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", str(metadata["reportSha256"])):
        raise ValueError("OSM review report hash is invalid")
    return metadata


def build_review_yaml(report: dict[str, Any], *, report_sha256: str) -> str:
    """Render a deliberately small, GitHub-editable YAML decision sheet."""
    queries = [query for query in report.get("queries", []) if query.get("status") == "needs_review"]
    lines = ["schemaVersion: 1", f"reportSha256: {report_sha256}", "choices:"]
    for query in queries:
        lines.extend(
            [
                f'  - queryId: {json.dumps(str(query["queryId"]))}',
                "    decision: null",
                "    candidateId: null",
            ]
        )
    return "\n".join(lines) + "\n"


def _parse_yaml_value(value: str) -> str | None:
    value = value.strip()
    if value == "null":
        return None
    if value.startswith('"'):
        parsed = json.loads(value)
        if not isinstance(parsed, str):
            raise ValueError("OSM review YAML value is invalid")
        return parsed
    if not value or any(character.isspace() for character in value):
        raise ValueError("OSM review YAML value is invalid")
    return value


def _parse_review_yaml(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    if len(lines) < 3 or lines[:3] != ["schemaVersion: 1", f"reportSha256: {lines[1][14:]}", "choices:"]:
        raise ValueError("OSM review YAML has an unsupported shape")
    report_sha256 = lines[1].removeprefix("reportSha256: ")
    if not re.fullmatch(r"[0-9a-f]{64}", report_sha256):
        raise ValueError("OSM review YAML report hash is invalid")
    choices = []
    for index in range(3, len(lines), 3):
        group = lines[index : index + 3]
        if len(group) != 3 or not group[0].startswith("  - queryId: ") or not group[1].startswith("    decision: ") or not group[2].startswith("    candidateId: "):
            raise ValueError("OSM review YAML choice is invalid")
        choices.append(
            {
                "queryId": _parse_yaml_value(group[0].removeprefix("  - queryId: ")),
                "decision": _parse_yaml_value(group[1].removeprefix("    decision: ")),
                "candidateId": _parse_yaml_value(group[2].removeprefix("    candidateId: ")),
            }
        )
    if not choices or not all(isinstance(choice["queryId"], str) for choice in choices):
        raise ValueError("OSM review YAML choices are invalid")
    return {"reportSha256": report_sha256, "choices": choices}


def build_issue_document(
    report: dict[str, Any],
    *,
    run_id: str,
    artifact_name: str,
    report_sha256: str,
    review_branch: str | None = None,
    repository_url: str = "https://github.com/nawashiro/chiyoda_city_main_facilities",
) -> dict[str, Any] | None:
    queries = [
        query for query in report.get("queries", []) if query.get("status") == "needs_review"
    ]
    if not queries:
        return None
    metadata = {
        "schemaVersion": 3 if review_branch else 2,
        "runId": str(run_id),
        "artifactName": artifact_name,
        "reportSha256": report_sha256,
        "queryIds": [str(query["queryId"]) for query in queries],
    }
    if review_branch:
        metadata["reviewBranch"] = review_branch
        edit_url = f"{repository_url}/edit/{review_branch}/reports/osm-review-needed.yaml"
        candidates_url = f"{repository_url}/blob/{review_branch}/reports/osm-candidates.json"
        body = "\n".join(
            [
                f"<!-- osm-review-metadata:{_encode_metadata(metadata)} -->",
                "## OSM候補の人間確認",
                "",
                "Issue本文は容量制限を避けるため、候補と選択をレビュー用ブランチへ分離しました。",
                "",
                f"1. [レビューYAMLをGitHubで編集]({edit_url})し、各項目の`decision`と`candidateId`を一組ずつ入力してコミットします。",
                f"2. 必要なら[候補の完全なJSON]({candidates_url})を参照します。",
                "3. このIssueの適用チェックを入れると、Actionsがコミット済みのYAMLと元の成果物を照合してPull Requestを作成します。",
                "",
                "- [ ] <!-- osm-apply --> **コミット済みの選択を適用してPull Requestを作成する**",
                "",
                f"元のActions run: `{run_id}` / artifact: `{artifact_name}`",
                "",
            ]
        )
        return {"title": f"OSM候補の人間確認（Actions run {run_id}）", "body": body, "labels": ["osm-human-review"]}
    lines = [
        f"<!-- osm-review-metadata:{_encode_metadata(metadata)} -->",
        "## OSM候補の人間確認",
        "",
        "LLM三者の合議が成立しなかった検索入力です。各項目で一つだけ選び、最後の適用チェックを押してください。JSONの編集は不要です。",
        "",
    ]
    perspective_names = {
        "visitor": "訪問者（同じ地物か）",
        "user": "利用者（同じ用途か）",
        "staff": "現地スタッフ（同じチームか）",
    }
    for query in queries:
        query_id = str(query["queryId"])
        lines.extend(
            [
                f"## {query['name']}",
                "",
                f"検索ID: `{query_id}`",
                "",
                "### 検索入力",
                "",
                "```json",
                json.dumps(
                    query.get("target", {"id": query_id, "name": query["name"]}),
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "```",
                "",
                "### LLM三者の見解",
                "",
            ]
        )
        for vote in query.get("llmVotes", []):
            if vote is None:
                lines.append("- 無効票")
                continue
            perspective = perspective_names.get(vote.get("perspective"), str(vote.get("perspective", "不明")))
            candidate_id = vote.get("candidateId") or "該当なし／判断保留"
            lines.append(f"- **{perspective}**: `{vote.get('decision')}` — `{candidate_id}`")
        lines.extend(["", "### 選択", ""])
        for candidate in query.get("candidates", []):
            record_id = str(candidate["recordId"])
            display_name = candidate.get("name") or candidate.get("tags", {}).get("name") or "名称なし"
            record_type, record_number = record_id.split("/", 1)
            lines.extend(
                [
                    f"- [ ] <!-- osm-choice:{query_id}:link:{record_id} --> **`{record_id}` {display_name}** — [OSMで開く](https://www.openstreetmap.org/{record_type}/{record_number})",
                    "",
                    "  <details><summary>候補の全属性</summary>",
                    "",
                    "  ```json",
                    "  "
                    + json.dumps(
                        candidate, ensure_ascii=False, separators=(",", ":")
                    ),
                    "  ```",
                    "",
                    "  </details>",
                    "",
                ]
            )
        lines.extend(
            [
                f"- [ ] <!-- osm-choice:{query_id}:reject:none --> **どの候補とも一致しない**",
                "",
            ]
        )
    lines.extend(
        [
            "---",
            "",
            "- [ ] <!-- osm-apply --> **すべての選択を適用してPull Requestを作成する**",
            "",
            f"元のActions run: `{run_id}` / artifact: `{artifact_name}`",
        ]
    )
    body = "\n".join(lines) + "\n"
    if len(body) > 65_536:
        raise ValueError("generated review exceeds the GitHub Issue body limit")
    return {
        "title": f"OSM候補の人間確認（Actions run {run_id}）",
        "body": body,
        "labels": ["osm-human-review"],
    }


def build_issue_documents(report: dict[str, Any], *, run_id: str, artifact_name: str, report_sha256: str) -> list[dict[str, Any]]:
    """Create one bounded GitHub Issue document per unresolved query."""
    documents = []
    for query in report.get("queries", []):
        if query.get("status") != "needs_review":
            continue
        document = build_issue_document({"queries": [query]}, run_id=run_id, artifact_name=artifact_name, report_sha256=report_sha256)
        if document is not None:
            documents.append(document)
    return documents


def apply_issue_selections(
    root: str | Path, body: str, *, issue_url: str
) -> dict[str, Any]:
    if _APPLY.search(body) is None:
        raise ValueError("apply checkbox is not checked")
    metadata = parse_issue_metadata(body)
    root = Path(root)
    report_path = root / "reports/osm-candidates.json"
    report_payload = report_path.read_bytes()
    if hashlib.sha256(report_payload).hexdigest() != metadata["reportSha256"]:
        raise ValueError("OSM candidate report does not match the reviewed artifact")
    report = json.loads(report_payload)
    review_queries = {
        str(query["queryId"]): query
        for query in report.get("queries", [])
        if query.get("status") == "needs_review" and str(query["queryId"]) in metadata["queryIds"]
    }
    if set(review_queries) != set(metadata["queryIds"]):
        raise ValueError("OSM review query IDs do not match the artifact")
    checked: dict[str, list[tuple[str, str]]] = {query_id: [] for query_id in review_queries}
    for mark, query_id, decision, candidate_id in _CHOICE.findall(body):
        if mark.lower() != "x" or query_id not in checked:
            continue
        checked[query_id].append((decision, candidate_id))
    for query_id, choices in checked.items():
        if len(choices) != 1:
            raise ValueError(f"exactly one choice is required for query {query_id}")

    normalized_path = root / "imports/openstreetmap/normalized.json"
    normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
    records = [
        record
        for record in normalized.get("records", [])
        if str(record.get("queryId")) not in review_queries
    ]
    record_owners: dict[str, str] = {}
    for record in records:
        record_id = f"{record['type']}/{record['id']}"
        owner = str(record["queryId"])
        if record_id in record_owners and record_owners[record_id] != owner:
            raise ValueError(f"duplicate current OSM recordId {record_id}")
        record_owners[record_id] = owner
    for query_id, query in review_queries.items():
        decision, candidate_id = checked[query_id][0]
        candidates = {
            str(candidate["recordId"]): candidate for candidate in query.get("candidates", [])
        }
        if decision == "link":
            candidate = candidates.get(candidate_id)
            if candidate is None:
                raise ValueError(f"selected candidate is not in the artifact: {candidate_id}")
            if candidate_id in record_owners and record_owners[candidate_id] != query_id:
                raise ValueError(f"duplicate current OSM recordId {candidate_id}")
            record_owners[candidate_id] = query_id
            records.append(
                {
                    "queryId": query_id,
                    "matchBasis": "human_review",
                    **{
                        key: value
                        for key, value in candidate.items()
                        if key not in {"recordId", "distanceMeters"}
                    },
                }
            )
            query["status"] = "linked_human"
        elif decision == "reject" and candidate_id == "none":
            query["status"] = "rejected_human"
        else:
            raise ValueError(f"invalid human review choice for query {query_id}")
        query["humanReview"] = {
            "decision": decision,
            "candidateId": None if candidate_id == "none" else candidate_id,
            "issueUrl": issue_url,
        }
    normalized["records"] = sorted(records, key=lambda item: item["queryId"])
    _write_json(normalized_path, normalized)
    _write_json(report_path, report)
    _write_json(
        root / "reports/osm-review-needed.json",
        {"version": report.get("version"), "queries": []},
    )
    return metadata


def apply_yaml_selections(
    root: str | Path, yaml_text: str, *, issue_url: str
) -> dict[str, Any]:
    """Validate committed YAML selections, then reuse the artifact-bound applier."""
    selection = _parse_review_yaml(yaml_text)
    root = Path(root)
    report_payload = (root / "reports/osm-candidates.json").read_bytes()
    if hashlib.sha256(report_payload).hexdigest() != selection["reportSha256"]:
        raise ValueError("OSM review YAML does not match the reviewed artifact")
    report = json.loads(report_payload)
    query_ids = [
        str(query["queryId"])
        for query in report.get("queries", [])
        if query.get("status") == "needs_review"
    ]
    choices = selection["choices"]
    if {choice["queryId"] for choice in choices} != set(query_ids) or len(choices) != len(query_ids):
        raise ValueError("OSM review YAML query IDs do not match the artifact")
    lines = [
        "<!-- osm-review-metadata:"
        + _encode_metadata(
            {
                "schemaVersion": 2,
                "runId": "0",
                "artifactName": "yaml-review",
                "reportSha256": selection["reportSha256"],
                "queryIds": query_ids,
            }
        )
        + " -->"
    ]
    for choice in choices:
        decision = choice["decision"]
        candidate_id = choice["candidateId"]
        if decision not in {"link", "reject"} or not isinstance(candidate_id, str):
            raise ValueError(f"OSM review YAML choice is incomplete for query {choice['queryId']}")
        lines.append(
            f"- [x] <!-- osm-choice:{choice['queryId']}:{decision}:{candidate_id} -->"
        )
    lines.append("- [x] <!-- osm-apply -->")
    apply_issue_selections(root, "\n".join(lines) + "\n", issue_url=issue_url)
    return selection


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and apply GitHub OSM review issues")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("root", nargs="?", default=".")
    build_parser.add_argument("--run-id", required=True)
    build_parser.add_argument("--artifact-name", required=True)
    build_parser.add_argument("--output", required=True)
    build_parser.add_argument("--review-branch")
    build_parser.add_argument("--repository-url")
    metadata_parser = subparsers.add_parser("metadata")
    metadata_parser.add_argument("--event", required=True)
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("root", nargs="?", default=".")
    apply_parser.add_argument("--event", required=True)
    apply_yaml_parser = subparsers.add_parser("apply-yaml")
    apply_yaml_parser.add_argument("root", nargs="?", default=".")
    apply_yaml_parser.add_argument("--event", required=True)
    apply_yaml_parser.add_argument("--yaml", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            root = Path(args.root)
            report_path = root / "reports/osm-candidates.json"
            payload = report_path.read_bytes()
            report = json.loads(payload)
            report_sha256 = hashlib.sha256(payload).hexdigest()
            if any(query.get("status") == "needs_review" for query in report.get("queries", [])):
                (root / "reports/osm-review-needed.yaml").write_text(
                    build_review_yaml(report, report_sha256=report_sha256), encoding="utf-8"
                )
            if args.review_branch:
                document = build_issue_document(
                    report,
                    run_id=args.run_id,
                    artifact_name=args.artifact_name,
                    report_sha256=report_sha256,
                    review_branch=args.review_branch,
                    repository_url=args.repository_url or "https://github.com/nawashiro/chiyoda_city_main_facilities",
                )
                issues = [] if document is None else [document]
            else:
                issues = build_issue_documents(
                    report,
                    run_id=args.run_id,
                    artifact_name=args.artifact_name,
                    report_sha256=report_sha256,
                )
            _write_json(Path(args.output), {"issues": issues})
        else:
            event = json.loads(Path(args.event).read_text(encoding="utf-8"))
            body = event["issue"]["body"]
            if args.command == "metadata":
                print(json.dumps(parse_issue_metadata(body), separators=(",", ":")))
            elif args.command == "apply-yaml":
                result = apply_yaml_selections(
                    args.root,
                    Path(args.yaml).read_text(encoding="utf-8"),
                    issue_url=event["issue"]["html_url"],
                )
                print(json.dumps(result, separators=(",", ":")))
            else:
                result = apply_issue_selections(
                    args.root, body, issue_url=event["issue"]["html_url"]
                )
                print(json.dumps(result, separators=(",", ":")))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
