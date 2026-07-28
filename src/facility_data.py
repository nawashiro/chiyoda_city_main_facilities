"""Small, dependency-free facility data pipeline."""

from __future__ import annotations

import argparse
import json
import re
import uuid
from pathlib import Path
from typing import Any


_QID = re.compile(r"^Q[1-9][0-9]*$")


def _is_uuid7(value: Any) -> bool:
    try:
        return uuid.UUID(str(value)).version == 7
    except (ValueError, TypeError, AttributeError):
        return False


def _valid_coordinates(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(
            isinstance(item, (int, float)) and not isinstance(item, bool)
            for item in value
        )
        and -180 <= value[0] <= 180
        and -90 <= value[1] <= 90
    )


def validate_search_document(document: dict[str, Any]) -> list[str]:
    """Return compact validation issues for an OSM search-input document."""
    issues: list[str] = []
    seen: set[str] = set()
    for index, query in enumerate(document.get("queries", [])):
        prefix = f"queries[{index}]"
        extra = set(query) - {"id", "name", "coordinates", "qid"}
        if extra:
            issues.append(f"{prefix}: unexpected fields: {', '.join(sorted(extra))}")
        place_id = query.get("id")
        if not _is_uuid7(place_id):
            issues.append(f"{prefix}: id must be UUIDv7")
        else:
            place_id = str(place_id)
            if place_id in seen:
                issues.append(f"{prefix}: duplicate id: {place_id}")
            seen.add(place_id)
        if ("coordinates" in query) == ("qid" in query):
            issues.append(f"{prefix}: exactly one of coordinates or qid is required")
        if not isinstance(query.get("name"), str) or not query["name"].strip():
            issues.append(f"{prefix}: name must be a non-empty string")
        if "qid" in query and (
            not isinstance(query["qid"], str) or not _QID.fullmatch(query["qid"])
        ):
            issues.append(f"{prefix}: invalid qid: {query['qid']}")
        if "coordinates" in query and not _valid_coordinates(query["coordinates"]):
            issues.append(f"{prefix}: coordinates must be [longitude, latitude]")
    return issues


def choose_geometry(
    query: dict[str, Any],
    wam_record: dict[str, Any] | None,
    osm_record: dict[str, Any] | None,
) -> tuple[list[float], str, str]:
    """Choose representative coordinates using WAM, OSM, then search input."""
    if wam_record is not None:
        return (wam_record["coordinates"], "wam", str(wam_record["id"]))
    if osm_record is not None:
        record_id = f"{osm_record['type']}/{osm_record['id']}"
        return (osm_record["coordinates"], "openstreetmap", record_id)
    return (query["coordinates"], "search-input", str(query["id"]))


def make_place(
    query: dict[str, Any],
    category_ids: list[str],
    tags: list[str],
    at: str,
    wam_record: dict[str, Any] | None = None,
    osm_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a small canonical Place from one search row."""
    coordinates, source_id, record_id = choose_geometry(query, wam_record, osm_record)
    return {
        "id": query["id"],
        "name": query["name"],
        "categoryIds": category_ids,
        "tags": tags,
        "geometry": {"type": "Point", "coordinates": coordinates},
        "geometrySource": {
            "sourceId": source_id,
            "recordId": record_id,
            "confirmedAt": at,
        },
        "images": [],
        "externalRefs": [],
        "lifecycle": {"status": "active", "changedAt": at},
        "visibility": {"status": "public", "changedAt": at},
        "audit": [
            {
                "at": at,
                "method": "human_inference",
                "action": "created",
                "target": "place",
            }
        ],
    }


def validate_registry(
    registry: dict[str, Any], search_by_id: dict[str, dict[str, Any]]
) -> list[str]:
    """Return issues for canonical Place records and their search-row identity."""
    issues: list[str] = []
    seen: set[str] = set()
    for place in registry.get("places", []):
        place_id = str(place.get("id"))
        if place_id in seen:
            issues.append(f"duplicate place id: {place_id}")
        seen.add(place_id)
        query = search_by_id.get(place_id)
        if query is None:
            issues.append(f"place {place_id}: search input not found")
        elif place.get("name") != query.get("name"):
            issues.append(f"place {place_id}: name differs from search input")
        if place.get("geometry", {}).get("type") != "Point":
            issues.append(f"place {place_id}: geometry must be Point")
    return issues


def _inside_ring(point: list[float], ring: list[list[float]]) -> bool:
    x, y = point
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous
        x2, y2 = current
        if (y1 > y) != (y2 > y):
            crossing_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < crossing_x:
                inside = not inside
        previous = current
    return inside


def _town_for_point(point: list[float], towns: dict[str, Any] | None) -> str | None:
    if not towns:
        return None
    matches = []
    for feature in towns.get("features", []):
        geometry = feature.get("geometry", {})
        if geometry.get("type") != "Polygon" or not geometry.get("coordinates"):
            continue
        rings = geometry["coordinates"]
        if _inside_ring(point, rings[0]) and not any(
            _inside_ring(point, hole) for hole in rings[1:]
        ):
            matches.append(feature.get("properties", {}).get("name"))
    return matches[0] if len(matches) == 1 else None


def build_public_geojson(
    registry: dict[str, Any],
    source_attributions: list[dict[str, Any]],
    towns: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the deterministic consumer-minimal public GeoJSON shadow."""
    features = []
    for place in sorted(registry.get("places", []), key=lambda item: item["id"]):
        if place.get("visibility", {}).get("status") != "public":
            continue
        point = list(place["geometry"]["coordinates"])
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": point},
                "properties": {
                    "id": place["id"],
                    "name": place["name"],
                    "categoryIds": place["categoryIds"],
                    "tags": place["tags"],
                    "town": _town_for_point(point, towns),
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "sourceAttributions": source_attributions,
        "features": features,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _repository_documents(
    root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    search_documents = [
        _read_json(path)
        for path in sorted((root / "inputs/osm-search").glob("**/*.json"))
    ]
    return (
        search_documents,
        _read_json(root / "data/registry.json"),
        _read_json(root / "config/sources.json"),
    )


def validate_repository(root: str | Path) -> list[str]:
    """Validate all current source-of-truth repository documents."""
    search_documents, registry, _ = _repository_documents(Path(root))
    issues = []
    search_by_id: dict[str, dict[str, Any]] = {}
    for document in search_documents:
        issues.extend(validate_search_document(document))
        for query in document.get("queries", []):
            query_id = str(query.get("id"))
            if query_id in search_by_id:
                issues.append(f"duplicate search id across files: {query_id}")
            search_by_id[query_id] = query
    issues.extend(validate_registry(registry, search_by_id))
    return issues


def build_repository(root: str | Path) -> Path:
    """Build the public GeoJSON from the canonical registry."""
    root = Path(root)
    _, registry, source_document = _repository_documents(root)
    attributions = [
        {
            "sourceId": source["id"],
            "license": source["license"],
            **(
                {"licenseUrl": source["license_url"]}
                if source.get("license_url")
                else {}
            ),
        }
        for source in source_document.get("sources", [])
    ]
    towns_path = root / "data/pinned/towns.geojson"
    towns = _read_json(towns_path) if towns_path.is_file() else None
    public = build_public_geojson(registry, attributions, towns)
    output = root / "dist/public/places.geojson"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Maintain Chiyoda Place data")
    parser.add_argument("command", choices=("validate", "build"))
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    issues = validate_repository(args.root)
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        return 1
    if args.command == "build":
        print(build_repository(args.root))
    else:
        print("Validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
