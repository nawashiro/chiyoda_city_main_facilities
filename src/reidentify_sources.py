from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from src.facility_data import search_input_sha256
from src.retrieve_osm import prepare_osm_snapshot
from src.retrieve_wam import prepare_wam_release


def _json_payload(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _verified_snapshot(root: Path, source: str) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_path = root / f"imports/{source}/raw.json"
    retrieval_path = root / f"imports/{source}/retrieval.json"
    raw_payload = raw_path.read_bytes()
    retrieval = json.loads(retrieval_path.read_text(encoding="utf-8"))
    label = "OpenStreetMap" if source == "openstreetmap" else "WAM"
    if hashlib.sha256(raw_payload).hexdigest() != retrieval.get("rawSha256"):
        raise ValueError(f"{label} rawSha256 does not match retained raw bytes")
    raw = json.loads(raw_payload)
    if raw.get("version") != retrieval.get("rawVersion"):
        raise ValueError(f"{label} raw version does not match retrieval metadata")
    if not isinstance(retrieval.get("retrievedAt"), str):
        raise ValueError(f"{label} retrieval timestamp is missing")
    return raw, retrieval


def _replace_documents(root: Path, documents: dict[str, dict[str, Any]]) -> None:
    temporaries: list[tuple[Path, Path]] = []
    try:
        for relative, document in documents.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f".{target.name}.reidentify.tmp")
            temporary.write_bytes(_json_payload(document))
            temporaries.append((temporary, target))
        for temporary, target in temporaries:
            temporary.replace(target)
    finally:
        for temporary, _ in temporaries:
            temporary.unlink(missing_ok=True)


def _stable_osm_query_ids(
    registry: dict[str, Any], queries: list[dict[str, Any]], raw: dict[str, Any]
) -> set[str]:
    available: dict[str, int] = {}
    for element in raw.get("elements", []):
        if element.get("type") not in {"node", "way", "relation"} or not isinstance(
            element.get("id"), int
        ):
            continue
        record_id = f"{element['type']}/{element['id']}"
        available[record_id] = available.get(record_id, 0) + 1
    stable: set[str] = set()
    for place in registry.get("places", []):
        query_id = str(place.get("id"))
        query = next((item for item in queries if str(item.get("id")) == query_id), None)
        if query is None:
            continue
        current = [
            ref
            for ref in place.get("externalRefs", [])
            if ref.get("sourceId") == "openstreetmap" and ref.get("status") == "current"
        ]
        audits = [
            audit
            for audit in place.get("audit", [])
            if audit.get("action") == "linked_osm"
            and isinstance(audit.get("searchInputSha256"), str)
        ]
        if (
            len(current) == 1
            and available.get(str(current[0].get("recordId"))) == 1
            and audits
            and audits[-1]["searchInputSha256"] == search_input_sha256(query)
        ):
            stable.add(query_id)
    return stable


def _stable_unlinked_osm_query_ids(
    registry: dict[str, Any],
    queries: list[dict[str, Any]],
    report: dict[str, Any],
    raw_sha256: str,
) -> set[str]:
    """Keep previously unlinked queries when the reviewed raw snapshot is unchanged."""
    if report.get("rawSha256") != raw_sha256:
        return set()
    current_by_query_id = {
        str(place.get("id")): [
            ref
            for ref in place.get("externalRefs", [])
            if ref.get("sourceId") == "openstreetmap" and ref.get("status") == "current"
        ]
        for place in registry.get("places", [])
    }
    stable: set[str] = set()
    for previous in report.get("queries", []):
        if not isinstance(previous, dict) or not isinstance(previous.get("target"), dict):
            continue
        query_id = str(previous.get("queryId"))
        query = next((item for item in queries if str(item.get("id")) == query_id), None)
        if query is None or current_by_query_id.get(query_id, []):
            continue
        try:
            unchanged = search_input_sha256(previous["target"]) == search_input_sha256(query)
        except (KeyError, TypeError):
            unchanged = False
        if unchanged:
            stable.add(query_id)
    return stable


def _filtered_documents(
    documents: list[dict[str, Any]], query_ids: set[str]
) -> list[dict[str, Any]]:
    return [
        {
            **document,
            "queries": [
                query
                for query in document.get("queries", [])
                if str(query.get("id")) in query_ids
            ],
        }
        for document in documents
    ]


def _preserved_osm_records(root: Path, query_ids: set[str]) -> list[dict[str, Any]]:
    path = root / "imports/openstreetmap/normalized.json"
    if not path.exists():
        return []
    normalized = json.loads(path.read_text(encoding="utf-8"))
    return [
        record
        for record in normalized.get("records", [])
        if str(record.get("queryId")) in query_ids
    ]


def _preserved_current_osm_records(
    root: Path,
    registry: dict[str, Any],
    raw: dict[str, Any],
    query_ids: set[str],
) -> list[dict[str, Any]]:
    """Keep retained current records when the new search cannot replace them."""
    path = root / "imports/openstreetmap/normalized.json"
    if not path.exists():
        return []
    available = {
        f"{element['type']}/{element['id']}"
        for element in raw.get("elements", [])
        if element.get("type") in {"node", "way", "relation"}
        and isinstance(element.get("id"), int)
    }
    current_by_query_id = {
        str(place.get("id")): [
            ref
            for ref in place.get("externalRefs", [])
            if ref.get("sourceId") == "openstreetmap" and ref.get("status") == "current"
        ]
        for place in registry.get("places", [])
    }
    normalized = json.loads(path.read_text(encoding="utf-8"))
    preserved = []
    for record in normalized.get("records", []):
        query_id = str(record.get("queryId"))
        current = current_by_query_id.get(query_id, [])
        record_id = f"{record.get('type')}/{record.get('id')}"
        if (
            query_id in query_ids
            and len(current) == 1
            and current[0].get("recordId") == record_id
            and record_id in available
        ):
            preserved.append(record)
    return preserved


def prepare_retained_reidentification(root: str | Path) -> dict[str, str]:
    """Re-identify current search inputs against retained WAM and OSM raw snapshots."""
    root = Path(root)
    wam_raw, wam_retrieval = _verified_snapshot(root, "wam")
    osm_raw, osm_retrieval = _verified_snapshot(root, "openstreetmap")
    search_documents = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "inputs/osm-search").rglob("*.json"))
    ]
    queries = [
        query
        for document in search_documents
        for query in document.get("queries", [])
    ]
    query_ids = [str(query["id"]) for query in queries]
    if len(query_ids) != len(set(query_ids)):
        raise ValueError("duplicate search query ID")
    current_query_ids = set(query_ids)
    registry = json.loads((root / "data/registry.json").read_text(encoding="utf-8"))
    stable_osm_query_ids = _stable_osm_query_ids(registry, queries, osm_raw)
    report_path = root / "reports/osm-candidates.json"
    if report_path.exists():
        stable_osm_query_ids |= _stable_unlinked_osm_query_ids(
            registry,
            queries,
            json.loads(report_path.read_text(encoding="utf-8")),
            str(osm_retrieval["rawSha256"]),
        )
    affected_osm_query_ids = current_query_ids - stable_osm_query_ids
    if not affected_osm_query_ids:
        return {
            "wamRetrievedAt": str(wam_retrieval["retrievedAt"]),
            "osmRetrievedAt": str(osm_retrieval["retrievedAt"]),
        }

    _unused_search, wam_normalized = prepare_wam_release(
        wam_raw.get("rows", []),
        search_documents,
        str(wam_raw["version"]),
        str(wam_retrieval["retrievedAt"]),
    )
    wam_normalized["records"] = [
        record
        for record in wam_normalized.get("records", [])
        if str(record.get("queryId")) in current_query_ids
    ]

    osm_normalized, osm_report = prepare_osm_snapshot(
        registry,
        _filtered_documents(search_documents, affected_osm_query_ids),
        osm_raw,
    )
    osm_report["rawSha256"] = osm_retrieval["rawSha256"]
    refreshed_osm_query_ids = {
        str(record["queryId"]) for record in osm_normalized.get("records", [])
    }
    osm_normalized["records"] = sorted(
        _preserved_osm_records(root, stable_osm_query_ids)
        + _preserved_current_osm_records(
            root,
            registry,
            osm_raw,
            affected_osm_query_ids - refreshed_osm_query_ids,
        )
        + list(osm_normalized.get("records", [])),
        key=lambda record: str(record["queryId"]),
    )

    wam_record_by_query = {
        str(record["queryId"]): record for record in wam_normalized.get("records", [])
    }
    wam_raw_by_id = {
        str(row["sourceRecordId"]): row for row in wam_raw.get("rows", [])
    }
    for query in osm_report.get("queries", []):
        wam_record = wam_record_by_query.get(str(query["queryId"]))
        if wam_record is None:
            continue
        query.setdefault("target", {})["wam"] = {
            "normalized": wam_record,
            "rows": [
                wam_raw_by_id[source_id]
                for source_id in wam_record.get("sourceRecordIds", [])
                if source_id in wam_raw_by_id
            ],
        }

    _replace_documents(
        root,
        {
            "imports/wam/normalized.json": wam_normalized,
            "imports/openstreetmap/normalized.json": osm_normalized,
            "reports/osm-candidates.json": osm_report,
        },
    )
    return {
        "wamRetrievedAt": str(wam_retrieval["retrievedAt"]),
        "osmRetrievedAt": str(osm_retrieval["retrievedAt"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Re-identify search inputs from retained WAM and OSM raw snapshots"
    )
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        result = prepare_retained_reidentification(args.root)
        payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(payload, encoding="utf-8")
        else:
            print(payload, end="")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
