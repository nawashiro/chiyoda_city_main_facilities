from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any



def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )



def _yaml_scalar(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _review_candidates(query: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        candidate
        for candidate in query.get("candidates", [])
        if isinstance(candidate.get("name"), str) and candidate["name"].strip()
    ]


def _review_reason_text(query: dict[str, Any]) -> str | None:
    reason = query.get("reviewReason")
    if not isinstance(reason, dict) or reason.get("code") != "candidate_already_linked":
        return None
    name = reason.get("conflictingQueryName")
    query_id = reason.get("conflictingQueryId")
    if isinstance(name, str) and name:
        return f"候補は別の施設に紐付け済みです: {name}"
    if isinstance(query_id, str) and query_id:
        return f"候補は別の施設に紐付け済みです（検索ID: {query_id}）"
    return "候補は別の施設に紐付け済みです"


def build_review_yaml(report: dict[str, Any], *, report_sha256: str) -> str:
    """Render a compact, editable one-choice-per-query review sheet."""
    queries = [query for query in report.get("queries", []) if query.get("status") == "needs_review"]
    lines = [
        "# OSM候補の人間確認",
        "# 操作手順",
        "# 1. 各「選択肢」で採用する候補を一つだけtrueに変更します。",
        "# 2. 採用しない場合は「候補なし（どの候補とも一致しない）」をtrueに変更します。",
        "# 3. それ以外のtrue/false、ID、施設名、reportSha256は変更しません。",
        "# 4. GitHubでコミットし、このレビューPull Requestをmergeします。",
        "schemaVersion: 2",
        f"reportSha256: {report_sha256}",
        "確認対象:",
    ]
    for query in queries:
        query_id = str(query["queryId"])
        lines.extend(
            [
                f"  - 検索ID: {_yaml_scalar(query_id)}",
                f"    施設名: {_yaml_scalar(query['name'])}",
            ]
        )
        reason = _review_reason_text(query)
        if reason is not None:
            lines.append(f"    自動取り込みしない理由: {_yaml_scalar(reason)}")
        lines.append("    選択肢:")
        for candidate in _review_candidates(query):
            name = candidate.get("name") or candidate.get("tags", {}).get("name") or "名称なし"
            label = f"候補 {candidate['recordId']}: {name}"
            lines.append(f"      {_yaml_scalar(label)}: false")
        lines.append(f"      {_yaml_scalar('候補なし（どの候補とも一致しない）')}: false")
    return "\n".join(lines) + "\n"


def _parse_review_yaml(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    report_sha256 = next((line.removeprefix("reportSha256: ") for line in lines if line.startswith("reportSha256: ")), None)
    if not isinstance(report_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", report_sha256):
        raise ValueError("OSM review YAML report hash is invalid")
    choices = []
    current_query_id: str | None = None
    in_options = False
    for line in lines:
        if line.startswith("  - 検索ID: "):
            current_query_id = json.loads(line.removeprefix("  - 検索ID: "))
            if not isinstance(current_query_id, str):
                raise ValueError("OSM review YAML query ID is invalid")
            in_options = False
        elif line == "    選択肢:":
            if current_query_id is None:
                raise ValueError("OSM review YAML choice has no query ID")
            choices.append({"queryId": current_query_id, "options": []})
            in_options = True
        elif line.startswith("    ") and not line.startswith("      "):
            in_options = False
        elif in_options and line.startswith("      "):
            key, separator, value = line[6:].rpartition(": ")
            if separator != ": " or value not in {"true", "false"}:
                raise ValueError("OSM review YAML option is invalid")
            label = json.loads(key)
            if not isinstance(label, str):
                raise ValueError("OSM review YAML option label is invalid")
            choices[-1]["options"].append((label, value == "true"))
    if not choices:
        raise ValueError("OSM review YAML choices are missing")
    selections = []
    for choice in choices:
        selected = [label for label, marked in choice["options"] if marked]
        if len(selected) != 1:
            raise ValueError(f"exactly one YAML option is required for query {choice['queryId']}")
        label = selected[0]
        if label == "候補なし（どの候補とも一致しない）":
            decision, candidate_id = "reject", "none"
        elif label.startswith("候補 ") and ": " in label:
            decision, candidate_id = "link", label.removeprefix("候補 ").split(": ", 1)[0]
        else:
            raise ValueError(f"OSM review YAML option is unsupported for query {choice['queryId']}")
        selections.append({"queryId": choice["queryId"], "decision": decision, "candidateId": candidate_id})
    return {"reportSha256": report_sha256, "choices": selections}


def apply_yaml_selections(
    root: str | Path, yaml_text: str, *, review_url: str
) -> dict[str, Any]:
    """Apply artifact-bound selections from a committed review YAML."""
    selection = _parse_review_yaml(yaml_text)
    root = Path(root)
    report_path = root / "reports/osm-candidates.json"
    report_payload = report_path.read_bytes()
    if hashlib.sha256(report_payload).hexdigest() != selection["reportSha256"]:
        raise ValueError("OSM review YAML does not match the reviewed artifact")
    report = json.loads(report_payload)
    query_ids = [
        str(query["queryId"])
        for query in report.get("queries", [])
        if query.get("status") == "needs_review"
    ]
    choices = {choice["queryId"]: choice for choice in selection["choices"]}
    if set(choices) != set(query_ids) or len(choices) != len(query_ids):
        raise ValueError("OSM review YAML query IDs do not match the artifact")
    review_queries = {str(query["queryId"]): query for query in report["queries"] if query.get("status") == "needs_review"}
    normalized_path = root / "imports/openstreetmap/normalized.json"
    normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
    records = [record for record in normalized.get("records", []) if str(record.get("queryId")) not in review_queries]
    record_owners: dict[str, str] = {}
    for record in records:
        record_id, owner = f"{record['type']}/{record['id']}", str(record["queryId"])
        if record_id in record_owners and record_owners[record_id] != owner:
            raise ValueError(f"duplicate current OSM recordId {record_id}")
        record_owners[record_id] = owner
    for query_id, query in review_queries.items():
        choice = choices[query_id]
        decision, candidate_id = choice["decision"], choice["candidateId"]
        candidates = {str(candidate["recordId"]): candidate for candidate in _review_candidates(query)}
        if decision == "link":
            candidate = candidates.get(candidate_id)
            if candidate is None:
                raise ValueError(f"selected candidate is not in the artifact: {candidate_id}")
            if candidate_id in record_owners and record_owners[candidate_id] != query_id:
                raise ValueError(f"duplicate current OSM recordId {candidate_id}")
            record_owners[candidate_id] = query_id
            records.append({"queryId": query_id, "matchBasis": "human_review", **{key: value for key, value in candidate.items() if key not in {"recordId", "distanceMeters"}}})
            query["status"] = "linked_human"
        elif decision == "reject" and candidate_id == "none":
            query["status"] = "rejected_human"
        else:
            raise ValueError(f"invalid human review choice for query {query_id}")
        query["humanReview"] = {"decision": decision, "candidateId": None if candidate_id == "none" else candidate_id, "reviewUrl": review_url}
    normalized["records"] = sorted(records, key=lambda item: item["queryId"])
    _write_json(normalized_path, normalized)
    _write_json(report_path, report)
    _write_json(root / "reports/osm-review-needed.json", {"version": report.get("version"), "queries": []})
    return selection


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and apply committed GitHub OSM reviews")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("root", nargs="?", default=".")
    build_parser.add_argument("--output", required=True)
    build_parser.add_argument("--report")
    apply_yaml_parser = subparsers.add_parser("apply-yaml")
    apply_yaml_parser.add_argument("root", nargs="?", default=".")
    apply_yaml_parser.add_argument("--yaml", required=True)
    apply_yaml_parser.add_argument("--review-url", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            root = Path(args.root)
            report_path = Path(args.report) if args.report else root / "reports/osm-candidates.json"
            payload = report_path.read_bytes()
            report = json.loads(payload)
            report_sha256 = hashlib.sha256(payload).hexdigest()
            if any(query.get("status") == "needs_review" for query in report.get("queries", [])):
                (root / "reports/osm-review-needed.yaml").write_text(
                    build_review_yaml(report, report_sha256=report_sha256), encoding="utf-8"
                )
            _write_json(
                Path(args.output),
                {
                    "reviewNeeded": any(
                        query.get("status") == "needs_review"
                        for query in report.get("queries", [])
                    )
                },
            )
        else:
            result = apply_yaml_selections(
                args.root,
                Path(args.yaml).read_text(encoding="utf-8"),
                review_url=args.review_url,
            )
            print(json.dumps(result, separators=(",", ":")))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
