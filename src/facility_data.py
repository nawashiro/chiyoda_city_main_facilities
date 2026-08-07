"""Small, dependency-free facility data pipeline."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import secrets
import time
import unicodedata
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.wam_contract import WAM_PUBLIC_ATTRIBUTE_HEADERS, WAM_PUBLIC_ATTRIBUTE_SET


_QID = re.compile(r"^Q[1-9][0-9]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_WAM_VISITING_SERVICE_TYPES = {
    "11",
    "12",
    "13",
    "14",
    "15",
    "66",
    "67",
    "居宅介護",
    "重度訪問介護",
    "行動援護",
    "重度障害者等包括支援",
    "同行援護",
    "居宅訪問型児童発達支援",
    "保育所等訪問支援",
}

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
    if not isinstance(document, dict):
        return ["search document must be an object"]
    extra_top = set(document) - {"source", "queries"}
    if extra_top:
        issues.append(f"unexpected top-level fields: {', '.join(sorted(extra_top))}")
    source = document.get("source")
    if not isinstance(source, dict):
        issues.append("source must be an object")
    else:
        extra_source = set(source) - {"kind", "sourceId", "retrievedAt"}
        if extra_source:
            issues.append(
                f"source has unexpected fields: {', '.join(sorted(extra_source))}"
            )
        if source.get("kind") not in {"human", "source"}:
            issues.append("source.kind must be human or source")
        if source.get("kind") == "source":
            if not isinstance(source.get("sourceId"), str) or not source["sourceId"].strip():
                issues.append("source.sourceId must be a non-empty string")
            retrieved_at = source.get("retrievedAt")
            if not isinstance(retrieved_at, str):
                issues.append("source.retrievedAt must be timezone-aware ISO 8601")
            else:
                try:
                    source_refresh_due(None, retrieved_at)
                except ValueError:
                    issues.append("source.retrievedAt must be timezone-aware ISO 8601")
    queries = document.get("queries")
    if not isinstance(queries, list):
        issues.append("queries must be an array")
        return issues
    seen: set[str] = set()
    for index, query in enumerate(queries):
        prefix = f"queries[{index}]"
        if not isinstance(query, dict):
            issues.append(f"{prefix}: query must be an object")
            continue
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
    current_osm_owners: dict[str, str] = {}
    for place in registry.get("places", []):
        place_id = str(place.get("id"))
        if place_id in seen:
            issues.append(f"duplicate place id: {place_id}")
        seen.add(place_id)
        query = search_by_id.get(place_id)
        is_disabled = (
            place.get("lifecycle", {}).get("status") == "closed"
            and place.get("visibility", {}).get("status") == "private"
        )
        if query is None and not is_disabled:
            issues.append(f"place {place_id}: search input not found")
        elif query is not None and place.get("name") != query.get("name"):
            issues.append(f"place {place_id}: name differs from search input")
        geometry = place.get("geometry", {})
        if geometry.get("type") != "Point":
            issues.append(f"place {place_id}: geometry must be Point")
        elif not _valid_coordinates(geometry.get("coordinates")):
            issues.append(f"place {place_id}: invalid Point coordinates")
        current_osm = [
            ref
            for ref in place.get("externalRefs", [])
            if ref.get("sourceId") == "openstreetmap" and ref.get("status") == "current"
        ]
        if len(current_osm) > 1:
            issues.append(f"place {place_id}: multiple current OSM refs")
        for ref in current_osm:
            record_id = str(ref.get("recordId"))
            owner = current_osm_owners.get(record_id)
            if owner is not None and owner != place_id:
                issues.append(f"duplicate current OSM recordId {record_id}")
            else:
                current_osm_owners[record_id] = place_id
        for audit in place.get("audit", []):
            required_audit_keys = {"at", "method", "action", "target"}
            audit_keys = set(audit)
            has_search_hash = "searchInputSha256" in audit
            if audit_keys != required_audit_keys and audit_keys != required_audit_keys | {"searchInputSha256"}:
                issues.append(f"place {place_id}: audit must have exactly four keys")
            if has_search_hash and audit.get("action") != "linked_osm":
                issues.append(f"place {place_id}: searchInputSha256 requires linked_osm")
            if has_search_hash and not _SHA256.fullmatch(str(audit.get("searchInputSha256"))):
                issues.append(f"place {place_id}: invalid searchInputSha256")
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
        coordinates = geometry.get("coordinates")
        if geometry.get("type") == "Polygon":
            polygons = [coordinates]
        elif geometry.get("type") == "MultiPolygon":
            polygons = coordinates
        else:
            continue
        if not polygons:
            continue
        if any(
            rings
            and _inside_ring(point, rings[0])
            and not any(_inside_ring(point, hole) for hole in rings[1:])
            for rings in polygons
        ):
            name = feature.get("properties", {}).get("name")
            if isinstance(name, str) and name:
                matches.append(name.removeprefix("東京都千代田区"))
    return matches[0] if len(matches) == 1 else None


def build_public_geojson(
    registry: dict[str, Any],
    source_attributions: list[dict[str, Any]],
    towns: dict[str, Any] | None = None,
    source_records: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the deterministic public GeoJSON shadow."""
    source_records = source_records or {}
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
                    "images": place.get("images", []),
                    "town": _town_for_point(point, towns),
                    "lifecycleStatus": place.get("lifecycle", {}).get("status"),
                    "sources": source_records.get(place["id"], {}),
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
    place_by_id = {str(place["id"]): place for place in registry.get("places", [])}
    for source in ("wam", "openstreetmap"):
        relative = f"imports/{source}/normalized.json"
        path = Path(root) / relative
        if not path.exists():
            continue
        snapshot = _read_json(path)
        if not isinstance(snapshot, dict):
            issues.append(f"{relative}: document must be an object")
            continue
        records = snapshot.get("records")
        if not isinstance(records, list):
            issues.append(f"{relative}: records must be an array")
            continue
        wam_raw_by_id: dict[str, dict[str, Any]] | None = None
        if source == "wam":
            raw_path = Path(root) / "imports/wam/raw.json"
            metadata_path = Path(root) / "imports/wam/retrieval.json"
            try:
                raw_payload = raw_path.read_bytes()
                raw_document = json.loads(raw_payload)
                metadata = _read_json(metadata_path)
                expected_hash = metadata.get("rawSha256")
                actual_hash = hashlib.sha256(raw_payload).hexdigest()
                if expected_hash != actual_hash:
                    raise ValueError("WAM rawSha256 does not match retained raw bytes")
                if raw_document.get("version") != metadata.get("rawVersion"):
                    raise ValueError("WAM raw version differs from retrieval metadata")
                wam_raw_by_id = _index_wam_raw_rows(raw_document.get("rows"))
            except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
                issues.append(f"imports/wam/raw.json: {error}")
        seen_snapshot_ids = set()
        for index, record in enumerate(records):
            prefix = f"{relative}: records[{index}]"
            if not isinstance(record, dict):
                issues.append(f"{prefix}: record must be an object")
                continue
            query_id = record.get("queryId")
            disabled_place = place_by_id.get(str(query_id))
            is_disabled = (
                isinstance(disabled_place, dict)
                and disabled_place.get("lifecycle", {}).get("status") == "closed"
                and disabled_place.get("visibility", {}).get("status") == "private"
            )
            if not _is_uuid7(query_id) or (query_id not in search_by_id and not is_disabled):
                issues.append(f"{prefix}: unknown or invalid queryId")
            elif query_id in seen_snapshot_ids:
                issues.append(f"{prefix}: duplicate queryId")
            seen_snapshot_ids.add(query_id)
            if not _valid_coordinates(record.get("coordinates")):
                issues.append(f"{prefix}: invalid coordinates")
            if source == "wam":
                record_id = record.get("id")
                if (
                    isinstance(record_id, bool)
                    or not isinstance(record_id, (str, int))
                    or not str(record_id).strip()
                ):
                    issues.append(f"{prefix}: invalid WAM id")
                if not isinstance(record.get("name"), str) or not record["name"].strip():
                    issues.append(f"{prefix}: invalid WAM name")
                source_record_ids = record.get("sourceRecordIds")
                if (
                    not isinstance(source_record_ids, list)
                    or not source_record_ids
                    or any(not isinstance(item, str) or not item for item in source_record_ids)
                    or len(source_record_ids) != len(set(source_record_ids))
                    or str(record_id) not in source_record_ids
                ):
                    issues.append(f"{prefix}: invalid WAM sourceRecordIds")
                if query_id in search_by_id and wam_raw_by_id is not None:
                    try:
                        _validate_wam_record_match(
                            record, search_by_id[query_id], wam_raw_by_id
                        )
                    except (KeyError, TypeError, ValueError) as error:
                        issues.append(f"{prefix}: {error}")
            else:
                if record.get("type") not in {"node", "way", "relation"}:
                    issues.append(f"{prefix}: invalid OSM type")
                record_id = record.get("id")
                if not isinstance(record_id, str) or not record_id.isdigit() or int(record_id) <= 0:
                    issues.append(f"{prefix}: invalid OSM id")
                if record.get("qid") is not None and not _QID.fullmatch(str(record["qid"])):
                    issues.append(f"{prefix}: invalid OSM QID")
                if record.get("matchBasis") not in {
                    "source_record",
                    "qid",
                    "name_coordinates",
                    "language_model",
                    "human_review",
                }:
                    issues.append(f"{prefix}: invalid OSM matchBasis")
                if record.get("matchBasis") == "qid" and record.get("qid") is None:
                    issues.append(f"{prefix}: qid matchBasis requires qid")
                if query_id in search_by_id:
                    try:
                        _validate_osm_record_match(
                            record,
                            search_by_id[query_id],
                            place_by_id.get(query_id),
                        )
                    except (KeyError, TypeError, ValueError) as error:
                        issues.append(f"{prefix}: {error}")
    return issues


def _public_source_records(root: Path) -> dict[str, dict[str, Any]]:
    source_records: dict[str, dict[str, Any]] = {}

    osm_normalized_path = root / "imports/openstreetmap/normalized.json"
    osm_raw_path = root / "imports/openstreetmap/raw.json"
    osm_metadata_path = root / "imports/openstreetmap/retrieval.json"
    osm_paths = (osm_normalized_path, osm_raw_path, osm_metadata_path)
    if any(path.is_file() for path in osm_paths) and not all(
        path.is_file() for path in osm_paths
    ):
        raise ValueError("incomplete OpenStreetMap snapshot")
    if all(path.is_file() for path in osm_paths):
        normalized = _read_json(osm_normalized_path).get("records", [])
        raw_payload = osm_raw_path.read_bytes()
        metadata = _read_json(osm_metadata_path)
        if hashlib.sha256(raw_payload).hexdigest() != metadata.get("rawSha256"):
            raise ValueError("OSM rawSha256 does not match retained raw bytes")
        raw_elements = json.loads(raw_payload).get("elements", [])
        raw_by_id = {}
        for element in raw_elements:
            key = (element.get("type"), str(element.get("id")))
            if key in raw_by_id:
                raise ValueError(f"duplicate OSM raw record: {key[0]}/{key[1]}")
            raw_by_id[key] = element
        for selected in normalized:
            key = (selected.get("type"), str(selected.get("id")))
            raw = raw_by_id.get(key)
            if raw is None:
                raise ValueError(
                    f"selected OSM raw record is missing: {key[0]}/{key[1]}"
                )
            raw_tags = raw.get("tags", {})
            if not isinstance(raw_tags, dict) or any(
                not isinstance(tag, str) or not isinstance(value, str)
                for tag, value in raw_tags.items()
            ):
                raise ValueError("OSM tags must contain only strings")
            source_records.setdefault(selected["queryId"], {})["openstreetmap"] = {
                "retrievedAt": metadata["retrievedAt"],
                "record": {
                    "type": selected["type"],
                    "id": str(selected["id"]),
                    "coordinates": list(selected["coordinates"]),
                    "tags": copy.deepcopy(raw_tags),
                },
            }

    wam_normalized_path = root / "imports/wam/normalized.json"
    wam_raw_path = root / "imports/wam/raw.json"
    wam_metadata_path = root / "imports/wam/retrieval.json"
    wam_paths = (wam_normalized_path, wam_raw_path, wam_metadata_path)
    if any(path.is_file() for path in wam_paths) and not all(
        path.is_file() for path in wam_paths
    ):
        raise ValueError("incomplete WAM snapshot")
    if all(path.is_file() for path in wam_paths):
        normalized = _read_json(wam_normalized_path).get("records", [])
        raw_rows = _read_json(wam_raw_path).get("rows", [])
        metadata = _read_json(wam_metadata_path)
        raw_by_id = _index_wam_raw_rows(raw_rows)
        for selected in normalized:
            public_rows = []
            for record_id in selected["sourceRecordIds"]:
                raw = raw_by_id.get(str(record_id))
                if raw is None:
                    raise ValueError(f"selected WAM raw record is missing: {record_id}")
                attributes = raw["attributes"]
                public_rows.append(
                    {
                        "sourceRecordId": str(raw["sourceRecordId"]),
                        "officeId": str(raw["officeId"]),
                        "serviceCode": str(raw["serviceCode"]),
                        "serviceType": str(raw["serviceType"]),
                        "name": str(raw["name"]),
                        "coordinates": list(raw["coordinates"]),
                        "attributes": {
                            name: attributes[name]
                            for name in WAM_PUBLIC_ATTRIBUTE_HEADERS
                        },
                    }
                )
            source_records.setdefault(selected["queryId"], {})["wam"] = {
                "retrievedAt": metadata["retrievedAt"],
                "records": public_rows,
            }
    return source_records


def _build_public_document(root: Path, registry: dict[str, Any]) -> dict[str, Any]:
    source_document = _read_json(root / "config/sources.json")
    towns_path = root / "data/pinned/towns.geojson"
    towns = _read_json(towns_path) if towns_path.is_file() else None
    source_records = _public_source_records(root)
    public_places = [
        place
        for place in registry.get("places", [])
        if place.get("visibility", {}).get("status") == "public"
    ]
    for place in public_places:
        source_id = place.get("geometrySource", {}).get("sourceId")
        if source_id in {"openstreetmap", "wam"} and source_id not in source_records.get(
            place["id"], {}
        ):
            raise ValueError(
                f"public source record is missing for place {place['id']}: {source_id}"
            )
    used_source_ids = {
        source_id
        for place in public_places
        for source_id in source_records.get(place["id"], {})
    }
    if towns is not None:
        used_source_ids.add("chiyoda-city-town-geojson")
    metadata_paths = {
        "openstreetmap": root / "imports/openstreetmap/retrieval.json",
        "wam": root / "imports/wam/retrieval.json",
        "chiyoda-city-town-geojson": root / "data/pinned/towns.retrieval.json",
    }
    sources_by_id = {
        source["id"]: source for source in source_document.get("sources", [])
    }
    attributions = []
    for source_id in sorted(used_source_ids):
        source = sources_by_id[source_id]
        metadata = _read_json(metadata_paths[source_id])
        if source_id == "chiyoda-city-town-geojson":
            version = metadata["commit"]
            sha256 = metadata["sha256"]
        else:
            version = metadata["rawVersion"]
            sha256 = metadata["rawSha256"]
        attributions.append(
            {
                "sourceId": source_id,
                "url": source["url"],
                "license": source["license"],
                "licenseUrl": source["license_url"],
                "version": version,
                "retrievedAt": metadata["retrievedAt"],
                "sha256": sha256,
                "attribution": source["attribution"],
                "transformation": source["transformation"],
            }
        )
    return build_public_geojson(
        registry,
        attributions,
        towns,
        source_records=source_records,
    )


def build_repository(root: str | Path) -> Path:
    """Build the public GeoJSON from the canonical registry."""
    root = Path(root)
    _, registry, _ = _repository_documents(root)
    public = _build_public_document(root, registry)
    output = root / "dist/public/places.geojson"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(public, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    output.write_bytes(payload)
    _write_json(
        output.parent / "manifest.json",
        {"file": output.name, "sha256": hashlib.sha256(payload).hexdigest()},
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


def _osm_comparison_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠々ー]+", "", normalized)


def _edit_distance(first: str, second: str) -> int:
    if len(first) > len(second):
        first, second = second, first
    previous = list(range(len(first) + 1))
    for row, right_character in enumerate(second, start=1):
        current = [row]
        for column, left_character in enumerate(first, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (left_character != right_character),
                )
            )
        previous = current
    return previous[-1]


def _osm_names_match(first: str, second: str) -> bool:
    left = _osm_comparison_name(first)
    right = _osm_comparison_name(second)
    if not left or not right:
        return False
    if left == right:
        return True
    if min(len(left), len(right)) < 6:
        return False
    maximum_length = max(len(left), len(right))
    allowed_distance = min(3, max(1, round(maximum_length * 0.15)))
    return _edit_distance(left, right) <= allowed_distance


def _validate_osm_record_match(
    record: dict[str, Any],
    query: dict[str, Any],
    place: dict[str, Any] | None,
) -> None:
    basis = record.get("matchBasis")
    if basis not in {
        "source_record",
        "qid",
        "name_coordinates",
        "language_model",
        "human_review",
    }:
        raise ValueError("OSM matchBasis is required")
    if basis in {"language_model", "human_review"}:
        if "coordinates" in query and _distance_metres(
            query["coordinates"], record["coordinates"]
        ) > 50:
            raise ValueError(f"OSM {basis} match exceeds 50 metres")
        if (
            "qid" in query
            and record.get("qid") is not None
            and record["qid"] != query["qid"]
        ):
            raise ValueError(f"OSM {basis} match has a conflicting QID")
        return
    if basis == "qid":
        if "qid" not in query or record.get("qid") != query["qid"]:
            raise ValueError("OSM qid match does not match the search query")
        return
    if basis == "name_coordinates":
        if "coordinates" not in query:
            raise ValueError("OSM name_coordinates match requires query coordinates")
        if not isinstance(record.get("name"), str) or not _osm_names_match(
            record["name"], query["name"]
        ):
            raise ValueError("OSM name_coordinates match exceeds the allowed name distance")
        if _distance_metres(query["coordinates"], record["coordinates"]) > 50:
            raise ValueError("OSM name_coordinates match exceeds 50 metres")
        return
    if place is None:
        raise ValueError("OSM source_record match requires an existing place")
    record_id = f"{record['type']}/{record['id']}"
    if not any(
        ref.get("sourceId") == "openstreetmap"
        and ref.get("status") == "current"
        and ref.get("recordId") == record_id
        for ref in place.get("externalRefs", [])
    ):
        raise ValueError("OSM source_record is not the current reference")
    if record.get("name") is not None and (
        not isinstance(record["name"], str)
        or not _osm_names_match(record["name"], query["name"])
    ):
        raise ValueError("OSM current record has a conflicting name")
    if (
        "qid" in query
        and record.get("qid") is not None
        and record["qid"] != query["qid"]
    ):
        raise ValueError("OSM current record has a conflicting QID")
    if _distance_metres(
        place["geometry"]["coordinates"], record["coordinates"]
    ) > 50:
        raise ValueError("OSM current record moved more than 50 metres")


def _wam_comparison_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = normalized.replace("千代田区立", "")
    return re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠々ー]+", "", normalized)


def _wam_names_match(first: str, second: str) -> bool:
    left = _wam_comparison_name(first)
    right = _wam_comparison_name(second)
    if left == right:
        return True
    shorter, longer = sorted((left, right), key=len)
    return len(shorter) >= 6 and shorter in longer


def _index_wam_raw_rows(rows: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("WAM raw rows must be an array")
    indexed: dict[str, dict[str, Any]] = {}
    required_strings = {
        "sourceRecordId",
        "officeId",
        "serviceCode",
        "serviceType",
        "name",
    }
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"WAM raw row {index} must be an object")
        if any(not isinstance(row.get(field), str) or not row[field] for field in required_strings):
            raise ValueError(f"WAM raw row {index} has invalid required fields")
        if not _valid_coordinates(row.get("coordinates")):
            raise ValueError(f"WAM raw row {index} has invalid coordinates")
        attributes = row.get("attributes")
        if (
            not isinstance(attributes, dict)
            or set(attributes) != WAM_PUBLIC_ATTRIBUTE_SET
            or any(not isinstance(value, str) for value in attributes.values())
        ):
            raise ValueError(
                f"WAM raw row {index} attributes must match the official 29-column contract"
            )
        source_id = row["sourceRecordId"]
        if source_id in indexed:
            raise ValueError(f"duplicate WAM raw sourceRecordId: {source_id}")
        indexed[source_id] = row
    return indexed


def _validate_wam_record_match(
    record: dict[str, Any],
    query: dict[str, Any],
    raw_by_id: dict[str, dict[str, Any]],
) -> None:
    if not _valid_coordinates(record.get("coordinates")):
        raise ValueError("WAM record has invalid coordinates")
    if not isinstance(record.get("name"), str) or not _wam_names_match(
        record["name"], query["name"]
    ):
        raise ValueError("WAM name does not match the search query")
    if "coordinates" in query and _distance_metres(
        query["coordinates"], record["coordinates"]
    ) > 50:
        raise ValueError("WAM record exceeds 50 metres from the search query")

    source_ids = record.get("sourceRecordIds")
    if (
        not isinstance(source_ids, list)
        or not source_ids
        or any(not isinstance(item, str) or not item for item in source_ids)
        or source_ids != sorted(set(source_ids))
    ):
        raise ValueError("WAM sourceRecordIds are invalid")
    if any(source_id not in raw_by_id for source_id in source_ids):
        raise ValueError("WAM sourceRecordIds are not present in raw rows")
    rows = [raw_by_id[source_id] for source_id in source_ids]
    primary = rows[0]
    expected = {
        "id": primary["sourceRecordId"],
        "sourceRecordIds": source_ids,
        "officeIds": sorted({row["officeId"] for row in rows}),
        "serviceCodes": sorted({row["serviceCode"] for row in rows}),
        "serviceTypes": sorted({row["serviceType"] for row in rows}),
        "name": primary["name"],
        "coordinates": primary["coordinates"],
    }
    for field, value in expected.items():
        if record.get(field) != value:
            raise ValueError(f"WAM {field} differs from retained raw rows")


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
            if not isinstance(candidate.get("name"), str) or not _osm_names_match(
                candidate["name"], query["name"]
            ):
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


def search_input_sha256(query: dict[str, Any]) -> str:
    """Hash the stable search-input fields used for OSM re-identification."""
    payload: dict[str, Any] = {"name": query["name"]}
    if "qid" in query:
        payload["qid"] = query["qid"]
    else:
        payload["coordinates"] = query["coordinates"]
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compact_audit(
    at: str,
    method: str,
    action: str,
    target: str,
    search_input_hash: str | None = None,
) -> dict[str, str]:
    """Create the entire persisted audit record—no traces or explanations."""
    audit = {"at": at, "method": method, "action": action, "target": target}
    if search_input_hash is not None:
        audit["searchInputSha256"] = search_input_hash
    return audit


def source_refresh_due(last_retrieved_at: str | None, now: str) -> bool:
    """Return whether a scheduled source refresh is due after 30 days."""
    try:
        current = datetime.fromisoformat(now.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError("invalid current retrieval time") from error
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("retrieval time must include a timezone")
    if last_retrieved_at is None:
        return True
    try:
        previous = datetime.fromisoformat(last_retrieved_at.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError("invalid previous retrieval time") from error
    if previous.tzinfo is None or previous.utcoffset() is None:
        raise ValueError("previous retrieval time must include a timezone")
    if previous > current:
        raise ValueError("previous retrieval time is in the future")
    return current - previous >= timedelta(days=30)


def normalize_wam_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize selected WAM rows; visiting-only services are not places."""
    normalized = []
    for index, row in enumerate(rows):
        service_type = str(row.get("serviceType", "")).strip()
        if service_type in _WAM_VISITING_SERVICE_TYPES:
            continue
        coordinates = [row.get("longitude"), row.get("latitude")]
        if (
            not _is_uuid7(row.get("placeId"))
            or isinstance(row.get("facilityId"), bool)
            or not isinstance(row.get("facilityId"), (str, int))
            or not str(row.get("facilityId", "")).strip()
            or not isinstance(row.get("name"), str)
            or not row["name"].strip()
            or not _valid_coordinates(coordinates)
        ):
            raise ValueError(f"invalid WAM row at index {index}")
        normalized.append(
            {
                "queryId": row["placeId"],
                "id": str(row["facilityId"]),
                "name": row["name"],
                "coordinates": coordinates,
            }
        )
    return normalized


def normalize_osm_elements(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize Overpass elements to representative points only."""
    normalized = []
    for index, element in enumerate(elements):
        if element.get("type") not in {"node", "way", "relation"}:
            raise ValueError(f"unsupported OSM type at index {index}")
        if (
            isinstance(element.get("id"), bool)
            or not isinstance(element.get("id"), int)
            or element["id"] <= 0
        ):
            raise ValueError(f"invalid OSM id at index {index}")
        if element.get("type") == "node":
            coordinates = [element.get("lon"), element.get("lat")]
        else:
            center = element.get("center", {})
            coordinates = [center.get("lon"), center.get("lat")]
        if not _valid_coordinates(coordinates):
            raise ValueError(f"invalid OSM coordinates at index {index}")
        tags = element.get("tags", {})
        if not isinstance(tags, dict):
            raise ValueError(f"invalid OSM tags at index {index}")
        if any(
            not isinstance(tag, str) or not isinstance(value, str)
            for tag, value in tags.items()
        ):
            raise ValueError(f"invalid OSM tag value at index {index}")
        if tags.get("wikidata") is not None and not _QID.fullmatch(str(tags["wikidata"])):
            raise ValueError(f"invalid OSM Wikidata QID at index {index}")
        record = {
            "type": element["type"],
            "id": str(element["id"]),
            "name": tags.get("name"),
            "coordinates": coordinates,
            "tags": copy.deepcopy(tags),
        }
        if tags.get("wikidata"):
            record["qid"] = tags["wikidata"]
        normalized.append(record)
    return normalized


def collect_osm_ids(registry: dict[str, Any]) -> list[str]:
    """Collect typed current and historical IDs for one batch refresh."""
    ids = {
        str(ref["recordId"])
        for place in registry.get("places", [])
        for ref in place.get("externalRefs", [])
        if ref.get("sourceId") == "openstreetmap"
        and re.fullmatch(r"(?:node|way|relation)/[1-9][0-9]*", str(ref.get("recordId", "")))
    }
    return sorted(ids)


def build_osm_batch_query(typed_ids: list[str], qids: list[str]) -> str:
    """Build one Overpass query for known IDs and search-input QIDs."""
    qids = sorted(set(qids))
    if any(not _QID.fullmatch(qid) for qid in qids):
        raise ValueError("invalid QID in OSM batch query")
    if not typed_ids and not qids:
        return ""
    grouped: dict[str, list[str]] = {"node": [], "way": [], "relation": []}
    for typed_id in typed_ids:
        record_type, record_id = typed_id.split("/", 1)
        grouped[record_type].append(record_id)
    selectors = "".join(
        f"{record_type}(id:{','.join(grouped[record_type])});"
        for record_type in ("node", "way", "relation")
        if grouped[record_type]
    )
    selectors += "".join(f'nwr["wikidata"="{qid}"];' for qid in qids)
    return f"[out:json];({selectors});out center;"


def update_osm_reference(
    place: dict[str, Any],
    osm_record: dict[str, Any],
    at: str,
    basis: str,
    method: str,
    audit_at: str | None = None,
    search_input_hash: str | None = None,
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
        if method in {"language_model", "human_inference"}:
            current["basis"] = basis
            updated.setdefault("audit", []).append(
                compact_audit(
                    audit_at or at,
                    method,
                    "linked_osm",
                    record_id,
                    search_input_hash,
                )
            )
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
            compact_audit(
                audit_at or at,
                method,
                "linked_osm",
                record_id,
                search_input_hash,
            )
        )
    return updated


def _update_wam_reference(
    place: dict[str, Any],
    wam_record: dict[str, Any],
    at: str,
    audit_at: str | None = None,
) -> dict[str, Any]:
    updated = copy.deepcopy(place)
    refs = updated.setdefault("externalRefs", [])
    record_ids = [str(item) for item in wam_record.get("sourceRecordIds", [wam_record["id"]])]
    wanted = set(record_ids)
    for ref in refs:
        if (
            ref.get("sourceId") == "wam"
            and ref.get("status") == "current"
            and ref.get("recordId") not in wanted
        ):
            ref["status"] = "superseded"
            ref["supersededAt"] = at
    for record_id in record_ids:
        current = next(
            (
                ref
                for ref in refs
                if ref.get("sourceId") == "wam"
                and ref.get("recordId") == record_id
                and ref.get("status") == "current"
            ),
            None,
        )
        if current is not None:
            current["lastConfirmedAt"] = at
            continue
        refs.append(
            {
                "sourceId": "wam",
                "recordId": record_id,
                "status": "current",
                "firstConfirmedAt": at,
                "lastConfirmedAt": at,
                "supersededAt": None,
                "basis": "source_record",
            }
        )
    updated.setdefault("audit", []).append(
        compact_audit(
            audit_at or at,
            "calculation_model",
            "linked_wam",
            str(wam_record["id"]),
        )
    )
    return updated


def apply_source_updates(
    registry: dict[str, Any],
    search_by_id: dict[str, dict[str, Any]],
    wam_records: list[dict[str, Any]],
    osm_records: list[dict[str, Any]],
    at: str,
    wam_raw_rows: list[dict[str, Any]] | None = None,
    decision_at: str | None = None,
) -> dict[str, Any]:
    """Apply already-selected batch snapshots with WAM > OSM > search priority."""
    if decision_at is not None:
        source_refresh_due(None, decision_at)
    updated = copy.deepcopy(registry)
    original_by_id = {
        str(place["id"]): place for place in updated.get("places", [])
    }
    wam_by_id: dict[str, dict[str, Any]] = {}
    if wam_records and wam_raw_rows is None:
        raise ValueError("retained WAM raw rows are required for application")
    wam_raw_by_id = _index_wam_raw_rows(wam_raw_rows or [])
    for record in wam_records:
        query_id = str(record.get("queryId"))
        if query_id not in search_by_id:
            raise ValueError(f"unknown WAM queryId: {query_id}")
        if query_id in wam_by_id:
            raise ValueError(f"duplicate WAM queryId: {query_id}")
        _validate_wam_record_match(record, search_by_id[query_id], wam_raw_by_id)
        wam_by_id[query_id] = record
    osm_by_id: dict[str, dict[str, Any]] = {}
    for record in osm_records:
        query_id = str(record.get("queryId"))
        if query_id not in search_by_id:
            raise ValueError(f"unknown OSM queryId: {query_id}")
        if query_id in osm_by_id:
            raise ValueError(f"duplicate OSM queryId: {query_id}")
        _validate_osm_record_match(
            record,
            search_by_id[query_id],
            original_by_id.get(query_id),
        )
        osm_by_id[query_id] = record
    places = []
    originals = list(updated.get("places", []))
    existing_place_ids = {str(place["id"]) for place in originals}
    for query_id in sorted(wam_by_id):
        if query_id not in existing_place_ids:
            originals.append(
                make_place(
                    search_by_id[query_id],
                    ["disability-support"],
                    [],
                    at,
                )
            )
    for original in originals:
        place_id = str(original["id"])
        query = search_by_id.get(place_id)
        if query is None:
            is_disabled = (
                original.get("lifecycle", {}).get("status") == "closed"
                and original.get("visibility", {}).get("status") == "private"
            )
            if is_disabled:
                places.append(original)
                continue
            raise ValueError(f"missing search input for place: {place_id}")
        wam_record = wam_by_id.get(place_id)
        osm_record = osm_by_id.get(place_id)
        if (
            osm_record is not None
            and osm_record.get("matchBasis") == "source_record"
        ):
            record_id = f"{osm_record['type']}/{osm_record['id']}"
            current_osm = next(
                (
                    ref
                    for ref in original.get("externalRefs", [])
                    if ref.get("sourceId") == "openstreetmap"
                    and ref.get("status") == "current"
                    and ref.get("recordId") == record_id
                ),
                None,
            )
            if current_osm is not None:
                osm_record = None
        place = original
        if wam_record is not None:
            place = _update_wam_reference(place, wam_record, at, audit_at=decision_at)
        if osm_record is not None:
            osm_method = {
                "language_model": "language_model",
                "human_review": "human_inference",
            }.get(osm_record["matchBasis"], "calculation_model")
            place = update_osm_reference(
                place,
                osm_record,
                at,
                osm_record["matchBasis"],
                osm_method,
                audit_at=decision_at,
                search_input_hash=search_input_sha256(query),
            )
        if wam_record is not None or osm_record is not None:
            preserve_wam_geometry = (
                wam_record is None
                and original.get("geometrySource", {}).get("sourceId") == "wam"
            )
            if not preserve_wam_geometry:
                coordinates, source_id, record_id = choose_geometry(
                    query, wam_record, osm_record
                )
                previous = place.get("geometry", {}).get("coordinates")
                previous_source = place.get("geometrySource", {}).get("sourceId")
                place["geometry"] = {"type": "Point", "coordinates": coordinates}
                place["geometrySource"] = {
                    "sourceId": source_id,
                    "recordId": record_id,
                    "confirmedAt": at,
                }
                if previous != coordinates or previous_source != source_id:
                    place.setdefault("audit", []).append(
                        compact_audit(
                            decision_at or at,
                            "calculation_model",
                            "updated_geometry",
                            place_id,
                        )
                    )
        places.append(place)
    updated["places"] = places
    return updated


def synchronize_registry_names(
    registry: dict[str, Any],
    search_by_id: dict[str, dict[str, Any]],
    at: str,
) -> dict[str, Any]:
    """Copy manually edited search names into existing canonical Places."""
    source_refresh_due(None, at)
    updated = copy.deepcopy(registry)
    for place in updated.get("places", []):
        place_id = str(place["id"])
        query = search_by_id.get(place_id)
        if query is None or place.get("name") == query.get("name"):
            continue
        place["name"] = query["name"]
        place.setdefault("audit", []).append(
            compact_audit(at, "human_inference", "updated_name", place_id)
        )
    return updated


def update_repository(
    root: str | Path,
    at: str,
    source: str,
    *,
    sync_search_names: bool = False,
    name_sync_at: str | None = None,
    decision_at: str | None = None,
) -> Path:
    """Apply one local source snapshot, validate, then rebuild public data."""
    if source not in {"wam", "openstreetmap"}:
        raise ValueError(f"unsupported update source: {source}")
    source_refresh_due(None, at)
    root = Path(root)
    existing_issues = validate_repository(root)
    if sync_search_names:
        existing_issues = [
            issue for issue in existing_issues if "name differs from search input" not in issue
        ]
    if existing_issues:
        raise ValueError("; ".join(existing_issues))
    search_by_id: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "inputs/osm-search").rglob("*.json")):
        document = _read_json(path)
        search_by_id.update(
            {str(query["id"]): query for query in document.get("queries", [])}
        )
    registry = _read_json(root / "data/registry.json")
    if sync_search_names:
        if name_sync_at is None:
            raise ValueError("name_sync_at is required when synchronizing search names")
        registry = synchronize_registry_names(registry, search_by_id, name_sync_at)

    def records(path: Path) -> list[dict[str, Any]]:
        return _read_json(path).get("records", []) if path.exists() else []

    wam_records = records(root / "imports/wam/normalized.json") if source == "wam" else []
    wam_raw_rows = (
        _read_json(root / "imports/wam/raw.json").get("rows", [])
        if source == "wam"
        else None
    )
    osm_records = (
        records(root / "imports/openstreetmap/normalized.json")
        if source == "openstreetmap"
        else []
    )
    updated = apply_source_updates(
        registry,
        search_by_id,
        wam_records,
        osm_records,
        at,
        wam_raw_rows=wam_raw_rows,
        decision_at=decision_at,
    )
    issues = validate_registry(updated, search_by_id)
    if issues:
        raise ValueError("; ".join(issues))

    public = _build_public_document(root, updated)
    public_payload = (json.dumps(public, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )
    report = {
        "at": at,
        "source": source,
        "places": len(updated.get("places", [])),
        "records": len(wam_records) + len(osm_records),
    }
    targets = {
        root / "data/registry.json": (
            json.dumps(updated, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8"),
        root / "dist/public/places.geojson": public_payload,
        root / "dist/public/manifest.json": (
            json.dumps(
                {
                    "file": "places.geojson",
                    "sha256": hashlib.sha256(public_payload).hexdigest(),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        ).encode("utf-8"),
        root / "reports/latest-update.json": (
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8"),
    }
    temporary_paths = []
    try:
        for target, payload in targets.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f".{target.name}.tmp")
            temporary.write_bytes(payload)
            temporary_paths.append(temporary)
        originals = {
            target: target.read_bytes() if target.exists() else None for target in targets
        }
        replaced = []
        try:
            for temporary, target in zip(temporary_paths, targets, strict=True):
                temporary.replace(target)
                replaced.append(target)
        except OSError:
            for target in replaced:
                original = originals[target]
                if original is None:
                    target.unlink(missing_ok=True)
                else:
                    target.write_bytes(original)
            raise
    finally:
        for temporary in temporary_paths:
            temporary.unlink(missing_ok=True)
    return root / "reports/latest-update.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Maintain Chiyoda Place data")
    parser.add_argument("command", choices=("validate", "build", "update"))
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--at")
    parser.add_argument("--source", choices=("wam", "openstreetmap"))
    parser.add_argument("--sync-search-names", action="store_true")
    parser.add_argument("--name-sync-at")
    parser.add_argument("--decision-at")
    args = parser.parse_args(argv)
    if args.command == "update":
        if args.at is None or args.source is None:
            print("ERROR: update requires --source and --at")
            return 1
        print(
            update_repository(
                args.root,
                args.at,
                args.source,
                sync_search_names=args.sync_search_names,
                name_sync_at=args.name_sync_at,
                decision_at=args.decision_at,
            )
        )
        return 0
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
