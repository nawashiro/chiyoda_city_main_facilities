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
    required = {"schemaVersion", "runId", "artifactName", "reportSha256"}
    if set(metadata) != required or metadata["schemaVersion"] != 1:
        raise ValueError("OSM review metadata has an unsupported shape")
    if not re.fullmatch(r"[0-9]+", str(metadata["runId"])):
        raise ValueError("OSM review run ID is invalid")
    if not isinstance(metadata["artifactName"], str) or not metadata["artifactName"]:
        raise ValueError("OSM review artifact name is invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", str(metadata["reportSha256"])):
        raise ValueError("OSM review report hash is invalid")
    return metadata


def build_issue_document(
    report: dict[str, Any],
    *,
    run_id: str,
    artifact_name: str,
    report_sha256: str,
) -> dict[str, Any] | None:
    queries = [
        query for query in report.get("queries", []) if query.get("status") == "needs_review"
    ]
    if not queries:
        return None
    metadata = {
        "schemaVersion": 1,
        "runId": str(run_id),
        "artifactName": artifact_name,
        "reportSha256": report_sha256,
    }
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
        if query.get("status") == "needs_review"
    }
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and apply GitHub OSM review issues")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("root", nargs="?", default=".")
    build_parser.add_argument("--run-id", required=True)
    build_parser.add_argument("--artifact-name", required=True)
    build_parser.add_argument("--output", required=True)
    metadata_parser = subparsers.add_parser("metadata")
    metadata_parser.add_argument("--event", required=True)
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("root", nargs="?", default=".")
    apply_parser.add_argument("--event", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            root = Path(args.root)
            report_path = root / "reports/osm-candidates.json"
            payload = report_path.read_bytes()
            issue = build_issue_document(
                json.loads(payload),
                run_id=args.run_id,
                artifact_name=args.artifact_name,
                report_sha256=hashlib.sha256(payload).hexdigest(),
            )
            _write_json(Path(args.output), issue or {"skip": True})
        else:
            event = json.loads(Path(args.event).read_text(encoding="utf-8"))
            body = event["issue"]["body"]
            if args.command == "metadata":
                print(json.dumps(parse_issue_metadata(body), separators=(",", ":")))
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
