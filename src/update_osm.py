from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.facility_data import (
    build_osm_batch_query,
    collect_osm_ids,
    normalize_osm_elements,
    source_refresh_due,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare or normalize one OSM batch snapshot")
    parser.add_argument("command", choices=("query", "normalize"))
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--raw")
    parser.add_argument("--at")
    args = parser.parse_args(argv)
    root = Path(args.root)
    registry = json.loads((root / "data/registry.json").read_text(encoding="utf-8"))
    qid_by_query_id = {}
    for path in sorted((root / "inputs/osm-search").rglob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        for query in document.get("queries", []):
            qid = query.get("qid")
            if qid is not None:
                if qid in qid_by_query_id:
                    print(f"ERROR: duplicate search QID: {qid}")
                    return 1
                qid_by_query_id[qid] = query["id"]
    if args.command == "query":
        print(
            build_osm_batch_query(
                collect_osm_ids(registry), sorted(qid_by_query_id)
            )
        )
        return 0
    if args.raw is None or args.at is None:
        print("ERROR: normalize requires --raw and --at")
        return 1
    metadata_path = root / "imports/openstreetmap/retrieval.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not source_refresh_due(metadata.get("retrievedAt"), args.at):
        print("ERROR: OSM snapshot was retrieved less than 30 days ago")
        return 1
    raw = json.loads(Path(args.raw).read_text(encoding="utf-8"))
    if not isinstance(raw.get("version"), str) or not raw["version"].strip():
        print("ERROR: OSM raw snapshot requires a version")
        return 1
    if not isinstance(raw.get("elements"), list):
        print("ERROR: OSM raw snapshot requires an elements array")
        return 1
    current_by_record_id = {
        ref["recordId"]: place["id"]
        for place in registry.get("places", [])
        for ref in place.get("externalRefs", [])
        if ref.get("sourceId") == "openstreetmap" and ref.get("status") == "current"
    }
    superseded_record_ids = {
        ref["recordId"]
        for place in registry.get("places", [])
        for ref in place.get("externalRefs", [])
        if ref.get("sourceId") == "openstreetmap"
        and ref.get("status") == "superseded"
    }
    records = []
    for record in normalize_osm_elements(raw["elements"]):
        typed_id = f"{record['type']}/{record['id']}"
        query_id = current_by_record_id.get(typed_id)
        match_basis = "source_record"
        if query_id is None and typed_id in superseded_record_ids:
            continue
        if query_id is None and record.get("qid") is not None:
            query_id = qid_by_query_id.get(record["qid"])
            if query_id is not None:
                match_basis = "qid"
        if query_id is not None:
            records.append(
                {"queryId": query_id, "matchBasis": match_basis, **record}
            )
    normalized_path = root / "imports/openstreetmap/normalized.json"
    normalized_path.write_text(
        json.dumps({"records": records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    metadata["retrievedAt"] = args.at
    metadata["rawVersion"] = raw.get("version")
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(normalized_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
