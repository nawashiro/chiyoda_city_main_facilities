from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

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

    registry = json.loads((root / "data/registry.json").read_text(encoding="utf-8"))
    osm_normalized, osm_report = prepare_osm_snapshot(
        registry, search_documents, osm_raw
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
