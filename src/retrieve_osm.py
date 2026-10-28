from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from src.osm_mirror import extract_elements

from src.facility_data import (
    load_queries,
    collect_osm_ids,
    source_refresh_due,
)
from src.http_utils import read_limited_response


CHIYODA_BBOX = "35.6680,139.7290,35.7060,139.7840"


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


def _named_osm_elements(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Discard OSM elements without a usable name before writing raw artifacts."""
    return [
        element
        for element in elements
        if isinstance(element.get("tags"), dict)
        and isinstance(element["tags"].get("name"), str)
        and element["tags"]["name"].strip()
    ]


def run_osm_retrieval(root: str | Path, at: str, fetch, extractor=extract_elements, *, canonical=None) -> tuple[Path, Path]:
    """Download the Tokyo mirror once and prepare reviewable local artifacts."""
    root = Path(root)
    metadata_path = root / "imports/openstreetmap/retrieval.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    source_refresh_due(None, at)
    if canonical is None:
        canonical = json.loads((root / "data/places.jsonld").read_text(encoding="utf-8"))
    queries = load_queries(root)
    qids = sorted({query["qid"] for query in queries if "qid" in query})
    coordinates = [query["coordinates"] for query in queries if "coordinates" in query]
    print(f"OSM mirror: download manifest {MOVISDA_MANIFEST_URL}", file=sys.stderr)
    manifest_payload, manifest_headers = fetch(MOVISDA_MANIFEST_URL)
    mirror_url, mirror = _select_tokyo_mirror(json.loads(manifest_payload))
    print(f"OSM mirror: download Tokyo PBF {mirror_url} ({mirror['bytes']} bytes)", file=sys.stderr)
    pbf_payload, pbf_headers = fetch(mirror_url)
    if len(pbf_payload) != mirror["bytes"]:
        raise ValueError("Movisda Tokyo extract has an unexpected size")
    print(f"OSM mirror: extract {len(collect_osm_ids(canonical))} IDs, {len(qids)} QIDs, {len(coordinates)} coordinate queries", file=sys.stderr)
    with tempfile.TemporaryDirectory() as directory:
        pbf_path = Path(directory) / "tokyo.osm.pbf"
        pbf_path.write_bytes(pbf_payload)
        extracted_elements = extractor(pbf_path, set(collect_osm_ids(canonical)), set(qids), coordinates, tuple(map(float, CHIYODA_BBOX.split(","))))
    elements = _named_osm_elements(extracted_elements)
    print(f"OSM mirror: retained {len(elements)} named elements", file=sys.stderr)
    raw = {"version": str(mirror["timestamp"]), "elements": elements}
    raw_payload = (json.dumps(raw, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    selection = {"typedIds": sorted(collect_osm_ids(canonical)), "qids": qids, "coordinates": coordinates, "bbox": CHIYODA_BBOX}
    selection_payload = (json.dumps(selection, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    retrieval = {**metadata, "sourceId": "openstreetmap", "retrievedAt": at, "rawVersion": raw["version"], "manifestUrl": MOVISDA_MANIFEST_URL, "pbfUrl": mirror_url, "pbfSha256": hashlib.sha256(pbf_payload).hexdigest(), "pbfBytes": len(pbf_payload), "manifestSha256": hashlib.sha256(manifest_payload).hexdigest(), "extractor": "pyosmium", "selectionSha256": hashlib.sha256(selection_payload).hexdigest(), "rawSha256": hashlib.sha256(raw_payload).hexdigest(), "etag": pbf_headers.get("ETag"), "lastModified": pbf_headers.get("Last-Modified")}
    imports_path = root / "imports/openstreetmap"; imports_path.mkdir(parents=True, exist_ok=True)
    (imports_path / "selection.json").write_bytes(selection_payload)
    (imports_path / "raw.json").write_bytes(raw_payload)
    _write_json(metadata_path, retrieval)
    return imports_path / "raw.json", metadata_path



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
        raw_path, metadata_path = run_osm_retrieval(args.root, args.at, _http_get)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 1
    print(raw_path)
    print(metadata_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
