"""Short maintainer-facing CLI for canonical places and OSM search inputs."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from src.facility_data import (
    compact_audit,
    new_uuid7,
    source_refresh_due,
    validate_registry,
    validate_search_document,
)


_SOURCE_ALIASES = {"osm": "openstreetmap", "wam": "wam"}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _validated_registry(root: Path) -> dict[str, Any]:
    registry = _read_json(root / "data/registry.json")
    if not isinstance(registry, dict) or registry.get("schemaVersion") != 1:
        raise ValueError("registry must be a schemaVersion 1 object")
    if set(registry) != {"schemaVersion", "places"}:
        raise ValueError("registry must contain only schemaVersion and places")
    places = registry.get("places")
    if not isinstance(places, list):
        raise ValueError("registry places must be an array")
    required = {
        "id",
        "name",
        "categoryIds",
        "tags",
        "geometry",
        "geometrySource",
        "images",
        "externalRefs",
        "lifecycle",
        "visibility",
        "audit",
    }
    for index, place in enumerate(places):
        if not isinstance(place, dict):
            raise ValueError(f"registry places[{index}] must be an object")
        missing = required - set(place)
        if missing:
            raise ValueError(
                f"registry places[{index}] missing fields: {', '.join(sorted(missing))}"
            )
        unexpected = set(place) - required
        if unexpected:
            raise ValueError(
                f"registry places[{index}] unexpected fields: "
                f"{', '.join(sorted(unexpected))}"
            )
        try:
            place_uuid = uuid.UUID(place["id"])
        except (AttributeError, TypeError, ValueError) as error:
            raise ValueError(f"registry places[{index}] has invalid UUIDv7 id") from error
        if place_uuid.version != 7 or str(place_uuid) != place["id"]:
            raise ValueError(f"registry places[{index}] has invalid UUIDv7 id")
        geometry = place["geometry"]
        coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
        if (
            not isinstance(geometry, dict)
            or set(geometry) != {"type", "coordinates"}
            or geometry.get("type") != "Point"
            or not isinstance(coordinates, list)
            or len(coordinates) != 2
            or any(
                isinstance(value, bool) or not isinstance(value, (int, float))
                for value in coordinates
            )
            or not -180 <= coordinates[0] <= 180
            or not -90 <= coordinates[1] <= 90
        ):
            raise ValueError(f"registry places[{index}] has invalid Point geometry")
        if not isinstance(place["name"], str) or not place["name"].strip():
            raise ValueError(f"registry places[{index}] has invalid name")
        categories = place["categoryIds"]
        if (
            not isinstance(categories, list)
            or not categories
            or any(not isinstance(value, str) or not value for value in categories)
        ):
            raise ValueError(f"registry places[{index}].categoryIds is invalid")
        tags = place["tags"]
        if not isinstance(tags, list) or any(not isinstance(value, str) for value in tags):
            raise ValueError(f"registry places[{index}].tags is invalid")
        for field in ("images", "externalRefs", "audit"):
            if not isinstance(place[field], list):
                raise ValueError(f"registry places[{index}].{field} must be an array")
        for field in ("geometrySource", "lifecycle", "visibility"):
            if not isinstance(place[field], dict):
                raise ValueError(f"registry places[{index}].{field} must be an object")
    return registry


def _validated_search_documents(root: Path) -> list[dict[str, Any]]:
    documents = [
        _read_json(path)
        for path in sorted((root / "inputs/osm-search").rglob("*.json"))
    ]
    issues: list[str] = []
    seen: set[str] = set()
    for document in documents:
        issues.extend(validate_search_document(document))
        if not isinstance(document, dict) or not isinstance(document.get("queries"), list):
            continue
        for query in document["queries"]:
            if not isinstance(query, dict):
                continue
            query_id = str(query.get("id"))
            if query_id in seen:
                issues.append(f"duplicate search id across files: {query_id}")
            seen.add(query_id)
    if issues:
        raise ValueError("; ".join(issues))
    return documents


def _source_status(place: dict[str, Any], source_id: str) -> str:
    statuses = [
        ref.get("status")
        for ref in place.get("externalRefs", [])
        if ref.get("sourceId") == source_id
    ]
    if "current" in statuses:
        return "current"
    if "superseded" in statuses:
        return "superseded"
    return "false"


def _coordinates_geo_uri(name: str, coordinates_value: list[float]) -> str:
    longitude, latitude = coordinates_value
    return f"geo:{latitude},{longitude}?q={quote(name, safe='')}"


def _display_mode_enabled(mode: str, *, color: bool = False) -> bool:
    if mode == "always":
        return True
    if mode == "never":
        return False
    if color and "NO_COLOR" in os.environ:
        return False
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


def _attribute(name: str, value: str, *, color: bool) -> str:
    if not color:
        return f"{name}={value}"
    styled_value = value
    if value == "true":
        styled_value = f"\x1b[32m{value}\x1b[0m"
    elif value == "false":
        styled_value = f"\x1b[31m{value}\x1b[0m"
    return f"\x1b[36m{name}\x1b[0m={styled_value}"


def _hyperlink(uri: str, *, enabled: bool) -> str:
    if not enabled:
        return uri
    return f"\x1b]8;;{uri}\x1b\\{uri}\x1b]8;;\x1b\\"


def _geo_uri(place: dict[str, Any]) -> str:
    return _coordinates_geo_uri(place["name"], place["geometry"]["coordinates"])


def _towns_by_id(root: Path) -> dict[str, str | None]:
    public_path = root / "dist/public/places.geojson"
    if not public_path.exists():
        return {}
    public = _read_json(public_path)
    return {
        str(feature.get("properties", {}).get("id")): feature.get("properties", {}).get("town")
        for feature in public.get("features", [])
    }


def _print_places(
    root: Path,
    *,
    town: str | None = None,
    category: str | None = None,
    name: str | None = None,
    osm: str | None = None,
    life: str | None = None,
    color_mode: str = "auto",
    hyperlink_mode: str = "auto",
) -> None:
    registry = _validated_registry(root)
    towns_by_id = _towns_by_id(root) if town is not None else {}
    places = registry.get("places", [])
    places = [
        place
        for place in places
        if (town is None or towns_by_id.get(str(place["id"])) == town)
        and (category is None or category in place.get("categoryIds", []))
        and (name is None or name.casefold() in str(place.get("name", "")).casefold())
        and (osm is None or _source_status(place, _SOURCE_ALIASES["osm"]) == osm)
        and (life is None or place.get("lifecycle", {}).get("status") == life)
    ]
    blocks = []
    color = _display_mode_enabled(color_mode, color=True)
    links = _display_mode_enabled(hyperlink_mode)
    for place in places:
        values = [
            ("cat", ",".join(place.get("categoryIds", []))),
            ("tags", str(bool(place.get("tags"))).lower()),
            ("img", str(bool(place.get("images"))).lower()),
            ("osm", _source_status(place, _SOURCE_ALIASES["osm"])),
            ("wam", _source_status(place, _SOURCE_ALIASES["wam"])),
            ("life", place.get("lifecycle", {}).get("status", "false")),
            ("vis", place.get("visibility", {}).get("status", "false")),
        ]
        attributes = "  " + " ".join(
            _attribute(key, value, color=color) for key, value in values
        )
        geo_uri = _geo_uri(place)
        blocks.append(
            f"{place['name']}\n  id={place['id']}\n{attributes}\n"
            f"  {_hyperlink(geo_uri, enabled=links)}"
        )
    if blocks:
        print("\n".join(blocks))


def _print_place(root: Path, place_id: str) -> None:
    registry = _validated_registry(root)
    place = next(
        (item for item in registry.get("places", []) if str(item.get("id")) == place_id),
        None,
    )
    if place is None:
        raise ValueError(f"place not found: {place_id}")
    print(json.dumps(place, ensure_ascii=False, indent=2))


def _search_by_id(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for document in _validated_search_documents(root):
        for query in document["queries"]:
            result[str(query["id"])] = query
    return result


def _write_registry(root: Path, registry: dict[str, Any]) -> None:
    issues = validate_registry(registry, _search_by_id(root))
    if issues:
        raise ValueError("; ".join(issues))
    target = root / "data/registry.json"
    temporary = target.with_name(f".{target.name}.tmp")
    try:
        temporary.write_text(
            json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def _set_reference(
    root: Path,
    place_id: str,
    source_name: str,
    record_id: str,
    at: str,
) -> None:
    source_refresh_due(None, at)
    if source_name != "osm":
        raise ValueError("ref currently supports only osm")
    source_id = _SOURCE_ALIASES["osm"]
    if record_id != "none":
        if re.fullmatch(r"(?:node|way|relation)/[1-9][0-9]*", record_id) is None:
            raise ValueError("OSM record ID must be node/N, way/N, or relation/N")
    registry = copy.deepcopy(_read_json(root / "data/registry.json"))
    place = next(
        (item for item in registry.get("places", []) if str(item.get("id")) == place_id),
        None,
    )
    if place is None:
        raise ValueError(f"place not found: {place_id}")
    refs = place.setdefault("externalRefs", [])
    for ref in refs:
        if ref.get("sourceId") != source_id or ref.get("status") != "current":
            continue
        if record_id == "none" or (
            source_id == "openstreetmap" and ref.get("recordId") != record_id
        ):
            ref["status"] = "superseded"
            ref["supersededAt"] = at
    if record_id == "none":
        place.setdefault("audit", []).append(
            compact_audit(at, "human_inference", f"unlinked_{source_name}", source_id)
        )
    else:
        selected = next(
            (
                ref
                for ref in refs
                if ref.get("sourceId") == source_id and ref.get("recordId") == record_id
            ),
            None,
        )
        if selected is None:
            selected = {
                "sourceId": source_id,
                "recordId": record_id,
                "status": "current",
                "firstConfirmedAt": at,
                "lastConfirmedAt": at,
                "supersededAt": None,
                "basis": "human_review",
            }
            refs.append(selected)
        else:
            selected["status"] = "current"
            selected.setdefault("firstConfirmedAt", at)
            selected["lastConfirmedAt"] = at
            selected["supersededAt"] = None
            selected["basis"] = "human_review"
        place.setdefault("audit", []).append(
            compact_audit(at, "human_inference", f"linked_{source_name}", record_id)
        )
    _write_registry(root, registry)


def _set_place(
    root: Path,
    place_id: str,
    *,
    categories: list[str] | None,
    tags: list[str] | None,
    life: str | None,
    visibility: str | None,
    at: str,
) -> None:
    source_refresh_due(None, at)
    registry = copy.deepcopy(_read_json(root / "data/registry.json"))
    place = next(
        (item for item in registry.get("places", []) if str(item.get("id")) == place_id),
        None,
    )
    if place is None:
        raise ValueError(f"place not found: {place_id}")
    changes = [categories is not None, tags is not None, life is not None, visibility is not None]
    if not any(changes):
        raise ValueError("set requires --cat, --tag, --life, or --vis")
    if categories is not None:
        if not categories:
            raise ValueError("at least one category is required")
        place["categoryIds"] = categories
        place.setdefault("audit", []).append(
            compact_audit(at, "human_inference", "updated_categories", place_id)
        )
    if tags is not None:
        place["tags"] = tags
        place.setdefault("audit", []).append(
            compact_audit(at, "human_inference", "updated_tags", place_id)
        )
    if life is not None:
        place["lifecycle"] = {"status": life, "changedAt": at}
        place.setdefault("audit", []).append(
            compact_audit(at, "human_inference", "updated_lifecycle", place_id)
        )
    if visibility is not None:
        place["visibility"] = {"status": visibility, "changedAt": at}
        place.setdefault("audit", []).append(
            compact_audit(at, "human_inference", "updated_visibility", place_id)
        )
    _write_registry(root, registry)


def _write_search_document(path: Path, document: dict[str, Any]) -> None:
    issues = validate_search_document(document)
    if issues:
        raise ValueError("; ".join(issues))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _add_search_input(
    root: Path,
    name: str,
    *,
    longitude: float | None,
    latitude: float | None,
    qid: str | None,
    at: str,
) -> str:
    source_refresh_due(None, at)
    has_coordinates = longitude is not None or latitude is not None
    if has_coordinates and (longitude is None or latitude is None):
        raise ValueError("--lon and --lat must be used together")
    if has_coordinates == (qid is not None):
        raise ValueError("use either --lon/--lat or --qid")
    moment = datetime.fromisoformat(at.replace("Z", "+00:00"))
    path = root / "inputs/osm-search/human" / f"{moment:%Y%m}.json"
    if path.exists():
        document = copy.deepcopy(_read_json(path))
    else:
        document = {
            "source": {"kind": "human", "sourceId": None, "retrievedAt": None},
            "queries": [],
        }
    query: dict[str, Any] = {"id": new_uuid7(), "name": name}
    if qid is not None:
        query["qid"] = qid
    else:
        query["coordinates"] = [longitude, latitude]
    document.setdefault("queries", []).append(query)
    _write_search_document(path, document)
    return str(query["id"])


def _print_search_inputs(root: Path) -> None:
    blocks = []
    for document in _validated_search_documents(root):
        for query in document["queries"]:
            location = (
                _coordinates_geo_uri(query["name"], query["coordinates"])
                if "coordinates" in query
                else f"qid={query['qid']}"
            )
            blocks.append(f"{query['name']}\n  id={query['id']}\n  {location}")
    if blocks:
        print("\n".join(blocks))


def _print_search_input(root: Path, query_id: str) -> None:
    matches = [
        query
        for document in _validated_search_documents(root)
        for query in document["queries"]
        if str(query.get("id")) == query_id
    ]
    if len(matches) != 1:
        message = "not found" if not matches else "is duplicated"
        raise ValueError(f"search input {message}: {query_id}")
    print(json.dumps(matches[0], ensure_ascii=False, indent=2))


def _set_search_input(
    root: Path,
    query_id: str,
    *,
    name: str | None,
    longitude: float | None,
    latitude: float | None,
    qid: str | None,
) -> None:
    selected: tuple[Path, dict[str, Any], dict[str, Any]] | None = None
    for path in sorted((root / "inputs/osm-search").rglob("*.json")):
        document = _read_json(path)
        for query in document.get("queries", []):
            if str(query.get("id")) == query_id:
                if selected is not None:
                    raise ValueError(f"duplicate search input: {query_id}")
                selected = (path, document, query)
    if selected is None:
        raise ValueError(f"search input not found: {query_id}")
    path, document, query = selected
    has_coordinates = longitude is not None or latitude is not None
    if has_coordinates and (longitude is None or latitude is None):
        raise ValueError("--lon and --lat must be used together")
    if has_coordinates and qid is not None:
        raise ValueError("use either --lon/--lat or --qid")
    if name is None and not has_coordinates and qid is None:
        raise ValueError("in set requires --name, --lon/--lat, or --qid")
    if name is not None:
        query["name"] = name
    if has_coordinates:
        query["coordinates"] = [longitude, latitude]
        query.pop("qid", None)
    if qid is not None:
        query["qid"] = qid
        query.pop("coordinates", None)
    _write_search_document(path, document)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fac", description="Maintain Chiyoda Place data")
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("ls", help="list canonical places")
    list_parser.add_argument("root", nargs="?", default=".")
    list_parser.add_argument("--town")
    list_parser.add_argument("--cat", dest="category")
    list_parser.add_argument("--name")
    list_parser.add_argument("--osm", choices=("current", "superseded", "false"))
    list_parser.add_argument("--life")
    list_parser.add_argument(
        "--color", choices=("auto", "always", "never"), default="auto"
    )
    list_parser.add_argument(
        "--hyperlink", choices=("auto", "always", "never"), default="auto"
    )
    get_parser = subparsers.add_parser("get", help="show one canonical place")
    get_parser.add_argument("root", nargs="?", default=".")
    get_parser.add_argument("place_id")
    set_parser = subparsers.add_parser("set", help="set canonical maintainer fields")
    set_parser.add_argument("root", nargs="?", default=".")
    set_parser.add_argument("place_id")
    set_parser.add_argument("--cat", dest="categories", action="append")
    set_parser.add_argument("--tag", dest="tags", action="append")
    set_parser.add_argument("--life")
    set_parser.add_argument("--vis", dest="visibility")
    set_parser.add_argument("--at")
    ref_parser = subparsers.add_parser("ref", help="set a manual external reference")
    ref_parser.add_argument("root", nargs="?", default=".")
    ref_parser.add_argument("place_id")
    ref_parser.add_argument("source")
    ref_parser.add_argument("record_id")
    ref_parser.add_argument("--at")
    input_parser = subparsers.add_parser("in", help="maintain OSM search inputs")
    input_subparsers = input_parser.add_subparsers(dest="input_command", required=True)
    input_list_parser = input_subparsers.add_parser("ls", help="list search inputs")
    input_list_parser.add_argument("root", nargs="?", default=".")
    input_get_parser = input_subparsers.add_parser("get", help="show one search input")
    input_get_parser.add_argument("root", nargs="?", default=".")
    input_get_parser.add_argument("query_id")
    input_add_parser = input_subparsers.add_parser("add", help="add a search input")
    input_add_parser.add_argument("root", nargs="?", default=".")
    input_add_parser.add_argument("name")
    input_add_parser.add_argument("--lon", dest="longitude", type=float)
    input_add_parser.add_argument("--lat", dest="latitude", type=float)
    input_add_parser.add_argument("--qid")
    input_add_parser.add_argument("--at")
    input_set_parser = input_subparsers.add_parser("set", help="edit a search input")
    input_set_parser.add_argument("root", nargs="?", default=".")
    input_set_parser.add_argument("query_id")
    input_set_parser.add_argument("--name")
    input_set_parser.add_argument("--lon", dest="longitude", type=float)
    input_set_parser.add_argument("--lat", dest="latitude", type=float)
    input_set_parser.add_argument("--qid")
    args = parser.parse_args(argv)
    if args.command == "ls":
        _print_places(
            Path(args.root),
            town=args.town,
            category=args.category,
            name=args.name,
            osm=args.osm,
            life=args.life,
            color_mode=args.color,
            hyperlink_mode=args.hyperlink,
        )
        return 0
    if args.command == "get":
        _print_place(Path(args.root), args.place_id)
        return 0
    if args.command == "set":
        at = args.at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        _set_place(
            Path(args.root),
            args.place_id,
            categories=args.categories,
            tags=args.tags,
            life=args.life,
            visibility=args.visibility,
            at=at,
        )
        return 0
    if args.command == "ref":
        at = args.at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        _set_reference(Path(args.root), args.place_id, args.source, args.record_id, at)
        return 0
    if args.command == "in" and args.input_command == "ls":
        _print_search_inputs(Path(args.root))
        return 0
    if args.command == "in" and args.input_command == "get":
        _print_search_input(Path(args.root), args.query_id)
        return 0
    if args.command == "in" and args.input_command == "add":
        at = args.at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        query_id = _add_search_input(
            Path(args.root),
            args.name,
            longitude=args.longitude,
            latitude=args.latitude,
            qid=args.qid,
            at=at,
        )
        print(f"id={query_id}")
        return 0
    if args.command == "in" and args.input_command == "set":
        _set_search_input(
            Path(args.root),
            args.query_id,
            name=args.name,
            longitude=args.longitude,
            latitude=args.latitude,
            qid=args.qid,
        )
        return 0
    return 1


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        AttributeError,
        IndexError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
