from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen


Vote = dict[str, Any]
Voter = Callable[[dict[str, Any], int], Vote]


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _valid_vote(vote: Any, candidate_ids: set[str]) -> Vote | None:
    if not isinstance(vote, dict):
        return None
    decision = vote.get("decision")
    candidate_id = vote.get("candidateId")
    if decision == "link" and candidate_id in candidate_ids:
        return {"decision": "link", "candidateId": candidate_id}
    if decision in {"reject", "review"} and candidate_id is None:
        return {"decision": decision, "candidateId": None}
    return None


def _consensus(votes: list[Vote | None]) -> Vote | None:
    if len(votes) != 3 or any(vote is None for vote in votes):
        return None
    counts = Counter((vote["decision"], vote["candidateId"]) for vote in votes if vote)
    winner, count = counts.most_common(1)[0]
    if count < 2:
        return None
    return {"decision": winner[0], "candidateId": winner[1]}


def resolve_osm_candidates(root: str | Path, voter: Voter) -> tuple[Path, Path]:
    root = Path(root)
    report_path = root / "reports/osm-candidates.json"
    normalized_path = root / "imports/openstreetmap/normalized.json"
    review_path = root / "reports/osm-review-needed.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
    records = list(normalized.get("records", []))
    existing_query_ids = {record["queryId"] for record in records}
    review_queries = []

    for query in report.get("queries", []):
        candidates = query.get("candidates", [])
        if (
            query.get("status") not in {"candidates", "ambiguous"}
            or not candidates
            or query.get("queryId") in existing_query_ids
        ):
            continue
        candidate_ids = {candidate["recordId"] for candidate in candidates}
        votes: list[Vote | None] = []
        for reviewer_number in range(1, 4):
            try:
                vote = voter(query, reviewer_number)
            except Exception:
                vote = None
            votes.append(_valid_vote(vote, candidate_ids))
        query["llmVotes"] = votes
        result = _consensus(votes)
        if result and result["decision"] == "link":
            candidate = next(
                item for item in candidates if item["recordId"] == result["candidateId"]
            )
            records.append(
                {
                    "queryId": query["queryId"],
                    "matchBasis": "language_model",
                    **{
                        key: value
                        for key, value in candidate.items()
                        if key not in {"recordId", "distanceMeters"}
                    },
                }
            )
            existing_query_ids.add(query["queryId"])
            query["status"] = "linked_llm"
        elif result and result["decision"] == "reject":
            query["status"] = "rejected_llm"
        else:
            query["status"] = "needs_review"
            review_queries.append(query)

    normalized["records"] = sorted(records, key=lambda item: item["queryId"])
    _write_json(normalized_path, normalized)
    _write_json(report_path, report)
    _write_json(
        review_path,
        {"version": report.get("version"), "queries": review_queries},
    )
    return normalized_path, review_path


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    return json.loads(text)


def openai_compatible_voter(
    api_key: str, base_url: str, model: str
) -> Voter:
    endpoint = base_url.rstrip("/") + "/chat/completions"

    def vote(query: dict[str, Any], reviewer_number: int) -> Vote:
        candidate_ids = [item["recordId"] for item in query["candidates"]]
        prompt = {
            "target": {
                "name": query["name"],
                "queryId": query["queryId"],
            },
            "candidates": query["candidates"],
            "allowedCandidateIds": candidate_ids,
        }
        body = json.dumps(
            {
                "model": model,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are independent map reviewer %d of 3. Decide whether one OSM "
                            "candidate is the same real-world facility as the target. Reply only "
                            "with JSON: {\"decision\":\"link\",\"candidateId\":\"node/1\"}, "
                            "{\"decision\":\"reject\",\"candidateId\":null}, or "
                            "{\"decision\":\"review\",\"candidateId\":null}. Use only an "
                            "allowed candidate ID. Reject means the candidates are clearly other "
                            "places; review means genuinely uncertain."
                        )
                        % reviewer_number,
                    },
                    {
                        "role": "user",
                        "content": json.dumps(prompt, ensure_ascii=False),
                    },
                ],
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "chiyoda-city-main-facilities/1",
            },
            method="POST",
        )
        with urlopen(request, timeout=120) as response:
            document = json.loads(response.read(2 * 1024 * 1024))
        content = document["choices"][0]["message"]["content"]
        return _extract_json_object(content)

    return vote


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve OSM candidates by three LLM votes")
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    api_key = os.environ.get("LLM_API_KEY")
    model = os.environ.get("LLM_MODEL")
    base_url = os.environ.get("LLM_BASE_URL") or "https://api.openai.com/v1"
    if not api_key or not model:
        print("ERROR: LLM_API_KEY and LLM_MODEL are required")
        return 1
    try:
        _, review_path = resolve_osm_candidates(
            args.root, openai_compatible_voter(api_key, base_url, model)
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 1
    print(review_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
