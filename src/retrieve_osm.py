from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from src.osm_mirror import extract_elements

from src.facility_data import (
    _osm_names_match,
    collect_osm_ids,
    normalize_osm_elements,
    source_refresh_due,
)
from src.http_utils import read_limited_response


_QID = re.compile(r"Q[1-9][0-9]*")
_TYPED_ID = re.compile(r"(node|way|relation)/([1-9][0-9]*)")
OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"
MAX_OVERPASS_BYTES = 32 * 1024 * 1024
CHIYODA_BBOX = "35.6680,139.7290,35.7060,139.7840"


def _distance_metres(first: list[float], second: list[float]) -> float:
    lon1, lat1 = map(math.radians, first)
    lon2, lat2 = map(math.radians, second)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6_371_000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_discovery_query(
    typed_ids: list[str],
    qids: list[str],
    coordinates: list[list[float]] | None = None,
) -> str:
    """Build one bounded Overpass query for refresh and Chiyoda discovery."""
    grouped: dict[str, list[str]] = {"node": [], "way": [], "relation": []}
    for typed_id in sorted(set(typed_ids)):
        match = _TYPED_ID.fullmatch(typed_id)
        if match is None:
            raise ValueError(f"invalid OSM typed ID: {typed_id}")
        grouped[match.group(1)].append(match.group(2))
    qids = sorted(set(qids))
    if any(_QID.fullmatch(qid) is None for qid in qids):
        raise ValueError("invalid QID in OSM discovery query")
    selectors = [
        f"{record_type}(id:{','.join(grouped[record_type])});"
        for record_type in ("node", "way", "relation")
        if grouped[record_type]
    ]
    selectors.extend(
        f'nwr({CHIYODA_BBOX})["wikidata"="{qid}"];' for qid in qids
    )
    coordinate_selectors = []
    for coordinates_pair in sorted({tuple(pair) for pair in coordinates or []}):
        if len(coordinates_pair) != 2 or not all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in coordinates_pair
        ):
            raise ValueError("invalid coordinates in OSM discovery query")
        longitude, latitude = coordinates_pair
        latitude_delta = 50 / 111_320
        longitude_delta = 50 / (111_320 * math.cos(math.radians(latitude)))
        coordinate_selectors.append(
            "nwr("
            f"{latitude - latitude_delta:.7f},{longitude - longitude_delta:.7f},"
            f"{latitude + latitude_delta:.7f},{longitude + longitude_delta:.7f}"
            ");"
        )
    selectors.extend(coordinate_selectors)
    return (
        f"[out:json][timeout:180];({''.join(selectors)});"
        "out center;"
    )


def prepare_osm_snapshot(
    registry: dict[str, Any],
    search_documents: list[dict[str, Any]],
    raw: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Select safe links and retain all local 50m candidates for review."""
    if not isinstance(raw.get("version"), str) or not raw["version"].strip():
        raise ValueError("OSM raw snapshot requires a version")
    if not isinstance(raw.get("elements"), list):
        raise ValueError("OSM raw snapshot requires an elements array")
    queries = [
        query
        for document in search_documents
        for query in document.get("queries", [])
    ]
    query_by_id = {query["id"]: query for query in queries}
    if len(query_by_id) != len(queries):
        raise ValueError("duplicate search query ID")
    qid_to_query_id: dict[str, str] = {}
    for query in queries:
        if "qid" in query:
            if query["qid"] in qid_to_query_id:
                raise ValueError(f"duplicate search QID: {query['qid']}")
            qid_to_query_id[query["qid"]] = query["id"]

    current_by_record_id: dict[str, str] = {}
    place_by_id = {str(place["id"]): place for place in registry.get("places", [])}
    superseded_record_ids: set[str] = set()
    for place in registry.get("places", []):
        for ref in place.get("externalRefs", []):
            if ref.get("sourceId") != "openstreetmap":
                continue
            record_id = str(ref.get("recordId"))
            if ref.get("status") == "current":
                if record_id in current_by_record_id:
                    raise ValueError(f"OSM record is current for multiple places: {record_id}")
                current_by_record_id[record_id] = place["id"]
            elif ref.get("status") == "superseded":
                superseded_record_ids.add(record_id)

    candidates_by_record_id: dict[str, dict[str, Any]] = {}
    for record in normalize_osm_elements(raw["elements"]):
        record_id = f"{record['type']}/{record['id']}"
        if record_id in candidates_by_record_id:
            raise ValueError(f"duplicate OSM element: {record_id}")
        candidates_by_record_id[record_id] = record

    selected: dict[str, dict[str, Any]] = {}
    report_queries = []
    for query in sorted(queries, key=lambda item: item["id"]):
        report_candidates = []
        exact_candidates = []
        for record_id, record in candidates_by_record_id.items():
            if record_id in superseded_record_ids and record_id not in current_by_record_id:
                continue
            if "qid" in query:
                if record.get("qid") != query["qid"]:
                    continue
                distance = None
            else:
                distance = _distance_metres(query["coordinates"], record["coordinates"])
                if distance > 50:
                    continue
            candidate = {
                **record,
                "recordId": record_id,
                "distanceMeters": distance,
            }
            report_candidates.append(candidate)
            if (
                "coordinates" in query
                and isinstance(record.get("name"), str)
                and _osm_names_match(record["name"], query["name"])
            ):
                exact_candidates.append(record)

        current_matches = [
            record
            for record_id, record in candidates_by_record_id.items()
            if current_by_record_id.get(record_id) == query["id"]
            and _distance_metres(
                place_by_id[query["id"]]["geometry"]["coordinates"],
                record["coordinates"],
            )
            <= 50
            and (
                record.get("name") is None
                or (
                    isinstance(record.get("name"), str)
                    and _osm_names_match(record["name"], query["name"])
                )
            )
            and (
                "qid" not in query
                or record.get("qid") is None
                or record.get("qid") == query["qid"]
            )
        ]
        qid_matches = [
            record
            for record in candidates_by_record_id.values()
            if "qid" in query
            and record.get("qid") == query["qid"]
            and f"{record['type']}/{record['id']}" not in superseded_record_ids
        ]
        chosen = None
        basis = None
        if len(current_matches) == 1:
            chosen, basis = current_matches[0], "source_record"
        elif len(current_matches) > 1:
            raise ValueError(f"multiple current OSM elements for query: {query['id']}")
        elif len(qid_matches) == 1:
            chosen, basis = qid_matches[0], "qid"
        elif len(exact_candidates) == 1:
            chosen, basis = exact_candidates[0], "name_coordinates"
        if chosen is not None:
            selected[query["id"]] = {
                "queryId": query["id"],
                "matchBasis": basis,
                **chosen,
            }
        if chosen is not None:
            status = "linked"
        elif len(exact_candidates) > 1 or len(qid_matches) > 1:
            status = "ambiguous"
        elif report_candidates:
            status = "candidates"
        else:
            status = "none"
        report_queries.append(
            {
                "queryId": query["id"],
                "name": query["name"],
                "target": dict(query),
                "status": status,
                "candidates": sorted(
                    report_candidates,
                    key=lambda item: (
                        item["distanceMeters"] is None,
                        item["distanceMeters"] or 0,
                        item["recordId"],
                    ),
                ),
            }
        )

    selected_record_ids: dict[str, list[str]] = {}
    for query_id, record in selected.items():
        record_id = f"{record['type']}/{record['id']}"
        selected_record_ids.setdefault(record_id, []).append(query_id)
    collisions = {
        query_id
        for query_ids in selected_record_ids.values()
        if len(query_ids) > 1
        for query_id in query_ids
    }
    for item in report_queries:
        if item["queryId"] in collisions:
            item["status"] = "ambiguous"
    records = [
        record
        for query_id, record in sorted(selected.items())
        if query_id not in collisions
    ]
    return {"records": records}, {"version": raw["version"], "queries": report_queries}


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


MOVISDA_MANIFEST_URL = "https://osm.download.movisda.io/admin/Admin-latest.geojson"
MOVISDA_ADMIN_PREFIX = "JP-13-"


def _select_tokyo_mirror(manifest: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    matches = [
        feature.get("properties", {})
        for feature in manifest.get("features", [])
        if feature.get("properties", {}).get("prefix") == MOVISDA_ADMIN_PREFIX
    ]
    if len(matches) != 1:
        raise ValueError("Movisda manifest lacks one Tokyo administrative extract")
    properties = matches[0]
    timestamp = properties.get("timestamp")
    if not isinstance(timestamp, int) or not isinstance(properties.get("bytes"), int):
        raise ValueError("Movisda Tokyo extract metadata is invalid")
    return f"https://osm.download.movisda.io/admin/{MOVISDA_ADMIN_PREFIX}{timestamp}.osm.pbf", properties


def run_osm_retrieval(root: str | Path, at: str, fetch, extractor=extract_elements) -> tuple[Path, Path]:
    """Download the Tokyo mirror once and prepare reviewable local artifacts."""
    root = Path(root)
    metadata_path = root / "imports/openstreetmap/retrieval.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    source_refresh_due(None, at)
    registry = json.loads((root / "data/registry.json").read_text(encoding="utf-8"))
    search_documents = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((root / "inputs/osm-search").rglob("*.json"))]
    qids = sorted({query["qid"] for document in search_documents for query in document.get("queries", []) if "qid" in query})
    coordinates = [query["coordinates"] for document in search_documents for query in document.get("queries", []) if "coordinates" in query]
    manifest_payload, manifest_headers = fetch(MOVISDA_MANIFEST_URL)
    mirror_url, mirror = _select_tokyo_mirror(json.loads(manifest_payload))
    pbf_payload, pbf_headers = fetch(mirror_url)
    if len(pbf_payload) != mirror["bytes"]:
        raise ValueError("Movisda Tokyo extract has an unexpected size")
    with tempfile.TemporaryDirectory() as directory:
        pbf_path = Path(directory) / "tokyo.osm.pbf"
        pbf_path.write_bytes(pbf_payload)
        elements = extractor(pbf_path, set(collect_osm_ids(registry)), set(qids), coordinates, tuple(map(float, CHIYODA_BBOX.split(","))))
    raw = {"version": str(mirror["timestamp"]), "elements": elements}
    raw_payload = (json.dumps(raw, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    selection = {"typedIds": sorted(collect_osm_ids(registry)), "qids": qids, "coordinates": coordinates, "bbox": CHIYODA_BBOX}
    selection_payload = (json.dumps(selection, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    normalized, report = prepare_osm_snapshot(registry, search_documents, raw)
    retrieval = {**metadata, "sourceId": "openstreetmap", "retrievedAt": at, "rawVersion": raw["version"], "manifestUrl": MOVISDA_MANIFEST_URL, "pbfUrl": mirror_url, "pbfSha256": hashlib.sha256(pbf_payload).hexdigest(), "pbfBytes": len(pbf_payload), "manifestSha256": hashlib.sha256(manifest_payload).hexdigest(), "extractor": "pyosmium", "selectionSha256": hashlib.sha256(selection_payload).hexdigest(), "rawSha256": hashlib.sha256(raw_payload).hexdigest(), "etag": pbf_headers.get("ETag"), "lastModified": pbf_headers.get("Last-Modified")}
    report["rawSha256"] = retrieval["rawSha256"]
    imports_path = root / "imports/openstreetmap"; imports_path.mkdir(parents=True, exist_ok=True)
    (imports_path / "raw-response.json").write_bytes(manifest_payload)
    (imports_path / "query.overpassql").write_bytes(selection_payload)
    (imports_path / "raw.json").write_bytes(raw_payload)
    normalized_path, report_path = imports_path / "normalized.json", root / "reports/osm-candidates.json"
    _write_json(normalized_path, normalized); _write_json(report_path, report); _write_json(metadata_path, retrieval)
    return normalized_path, report_path


def _http_get(url: str) -> tuple[bytes, dict[str, str | None]]:
    request = Request(url, headers={"User-Agent": "chiyoda-city-main-facilities/1"})
    with urlopen(request, timeout=240) as response:
        return read_limited_response(response, 1024 * 1024 * 1024, "OSM mirror"), {"ETag": response.headers.get("ETag"), "Last-Modified": response.headers.get("Last-Modified")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retrieve one bounded OSM discovery batch")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--at", required=True)
    args = parser.parse_args(argv)
    try:
        normalized_path, report_path = run_osm_retrieval(args.root, args.at, _http_get)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 1
    print(normalized_path)
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
