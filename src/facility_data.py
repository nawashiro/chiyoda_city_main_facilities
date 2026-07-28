"""Small, dependency-free facility data pipeline."""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
import secrets
import time
import uuid
from pathlib import Path
from typing import Any


_QID = re.compile(r"^Q[1-9][0-9]*$")

_OUT_OF_SCOPE = {"保育所", "幼稚園", "学校", "劇場"}
_CATEGORY_IDS = {
    "区役所・出張所": "public-office",
    "障害者福祉センター": "disability-support",
    "図書館": "library",
    "社会福祉施設": "social-welfare",
    "自然環境公園": "park",
    "仏教": "buddhist-temple",
    "キリスト教": "christian-church",
    "映画館": "cinema",
    "公衆浴場": "public-bath",
    "美術館": "art-museum",
    "博物館": "museum",
}


def new_uuid7(timestamp_ms: int | None = None, random_bits: int | None = None) -> str:
    """Create a UUIDv7 without adding a package dependency."""
    timestamp_ms = timestamp_ms if timestamp_ms is not None else time.time_ns() // 1_000_000
    random_bits = random_bits if random_bits is not None else secrets.randbits(74)
    value = (
        ((timestamp_ms & ((1 << 48) - 1)) << 80)
        | (0x7 << 76)
        | (((random_bits >> 62) & 0xFFF) << 64)
        | (0b10 << 62)
        | (random_bits & ((1 << 62) - 1))
    )
    return str(uuid.UUID(int=value))


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
        current_osm = [
            ref
            for ref in place.get("externalRefs", [])
            if ref.get("sourceId") == "openstreetmap" and ref.get("status") == "current"
        ]
        if len(current_osm) > 1:
            issues.append(f"place {place_id}: multiple current OSM refs")
        for audit in place.get("audit", []):
            if set(audit) != {"at", "method", "action", "target"}:
                issues.append(f"place {place_id}: audit must have exactly four keys")
            if audit.get("method") not in {
                "language_model",
                "calculation_model",
                "human_inference",
                "field_observation",
            }:
                issues.append(
                    f"place {place_id}: invalid audit method: {audit.get('method')}"
                )
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


def migrate_legacy(
    legacy_categories: list[dict[str, Any]],
    shortcut_categories: list[dict[str, Any]],
    at: str,
    id_factory,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Perform the one-time, scope-gated migration from the old JSON layout."""
    shortcut_names = {
        location.get("name")
        for category in shortcut_categories
        for location in category.get("locations", [])
    }
    queries = []
    places = []
    out_of_scope: dict[str, int] = {}
    needs_selection: dict[str, int] = {}
    migrated_from = []
    for category in legacy_categories:
        category_name = category.get("category", "")
        locations = category.get("locations", [])
        if category_name in _OUT_OF_SCOPE:
            out_of_scope[category_name] = len(locations)
            continue
        if category_name == "病院":
            needs_selection[category_name] = len(locations)
            continue
        category_id = _CATEGORY_IDS.get(category_name)
        if category_id is None:
            out_of_scope[category_name] = len(locations)
            continue
        for location in locations:
            place_id = id_factory()
            query = {
                "id": place_id,
                "name": location["name"],
                "coordinates": [location["lng"], location["lat"]],
            }
            tags = (
                ["kazaguruma.home-shortcut"]
                if location["name"] in shortcut_names
                else []
            )
            place = make_place(query, [category_id], tags, at)
            if location.get("imageUri"):
                place["images"] = [
                    {
                        "url": location["imageUri"],
                        "rights": location.get("imageCopyright") or "unknown",
                    }
                ]
            queries.append(query)
            places.append(place)
            migrated_from.append(
                {"legacyId": location.get("id"), "placeId": place_id}
            )
    return (
        {
            "source": {
                "kind": "human",
                "sourceId": "legacy_record",
                "retrievedAt": at,
            },
            "queries": queries,
        },
        {"schemaVersion": 1, "places": places},
        {
            "migrated": len(places),
            "outOfScope": out_of_scope,
            "needsSelection": needs_selection,
            "idMap": migrated_from,
        },
    )


def _write_json(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def migrate_repository(
    root: str | Path,
    at: str,
    id_factory=new_uuid7,
) -> tuple[Path, Path, Path]:
    """Write the one-time migration outputs into their final repository paths."""
    root = Path(root)
    legacy = json.loads((root / "json/key_locations.json").read_text(encoding="utf-8"))
    shortcuts = json.loads(
        (root / "json/main_facilities.json").read_text(encoding="utf-8")
    )
    search, registry, report = migrate_legacy(legacy, shortcuts, at, id_factory)
    search_path = root / "inputs/osm-search/legacy/migration-v2.json"
    registry_path = root / "data/registry.json"
    report_path = root / "reports/migration-v2.json"
    _write_json(search_path, search)
    _write_json(registry_path, registry)
    _write_json(report_path, report)
    return search_path, registry_path, report_path


def _distance_metres(first: list[float], second: list[float]) -> float:
    lon1, lat1 = map(math.radians, first)
    lon2, lat2 = map(math.radians, second)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6_371_000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def match_osm_candidates(
    query: dict[str, Any], candidates: list[dict[str, Any]], max_distance_m: float = 50
) -> list[dict[str, Any]]:
    """Return deterministic OSM candidates without widening the 50m boundary."""
    matches = []
    for candidate in candidates:
        if "qid" in query:
            if candidate.get("qid") != query["qid"]:
                continue
            distance = None
        else:
            if candidate.get("name") != query["name"]:
                continue
            distance = _distance_metres(query["coordinates"], candidate["coordinates"])
            if distance > max_distance_m:
                continue
        matches.append(
            {
                **candidate,
                "recordId": f"{candidate['type']}/{candidate['id']}",
                "distanceMeters": distance,
            }
        )
    return sorted(matches, key=lambda item: (item["distanceMeters"] is None, item["distanceMeters"] or 0, item["recordId"]))


def decide_consensus(votes: list[dict[str, Any]]) -> str | None:
    """Accept a low-risk link only when all three votes are valid and two agree."""
    if len(votes) != 3:
        return None
    if any(set(vote) != {"candidateId", "decision"} for vote in votes):
        return None
    link_counts: dict[str, int] = {}
    for vote in votes:
        if vote["decision"] not in {"link", "reject", "review"}:
            return None
        if vote["decision"] == "link" and isinstance(vote["candidateId"], str):
            candidate_id = vote["candidateId"]
            link_counts[candidate_id] = link_counts.get(candidate_id, 0) + 1
    winners = [candidate_id for candidate_id, count in link_counts.items() if count >= 2]
    return winners[0] if len(winners) == 1 else None


def compact_audit(at: str, method: str, action: str, target: str) -> dict[str, str]:
    """Create the entire persisted audit record—no traces or explanations."""
    return {"at": at, "method": method, "action": action, "target": target}


def update_osm_reference(
    place: dict[str, Any],
    osm_record: dict[str, Any],
    at: str,
    basis: str,
    method: str,
) -> dict[str, Any]:
    """Keep typed current/superseded OSM IDs and append one compact audit item."""
    updated = copy.deepcopy(place)
    refs = updated.setdefault("externalRefs", [])
    record_id = f"{osm_record['type']}/{osm_record['id']}"
    current = next(
        (
            ref
            for ref in refs
            if ref.get("sourceId") == "openstreetmap"
            and ref.get("recordId") == record_id
            and ref.get("status") == "current"
        ),
        None,
    )
    if current is not None:
        current["lastConfirmedAt"] = at
        current["basis"] = basis
    else:
        for ref in refs:
            if ref.get("sourceId") == "openstreetmap" and ref.get("status") == "current":
                ref["status"] = "superseded"
                ref["supersededAt"] = at
        refs.append(
            {
                "sourceId": "openstreetmap",
                "recordId": record_id,
                "status": "current",
                "firstConfirmedAt": at,
                "lastConfirmedAt": at,
                "supersededAt": None,
                "basis": basis,
            }
        )
    updated.setdefault("audit", []).append(
        compact_audit(at, method, "linked_osm", record_id)
    )
    return updated


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
