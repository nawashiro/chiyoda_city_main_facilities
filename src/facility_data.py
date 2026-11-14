"""Canonical JSON-LD facility data validation and source update helpers."""
from __future__ import annotations

import argparse
import copy
import json
import math
import re
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


_QID = re.compile(r"^Q[1-9][0-9]*$")
_OSM_TYPED_OBJECT_ID = re.compile(r"^(node|way|relation)/([1-9][0-9]*)$")
_WIKIDATA_ENTITY_URI = re.compile(r"^https://www\.wikidata\.org/entity/Q[1-9][0-9]*$")
_URN_UUID = re.compile(r"^urn:uuid:[0-9a-fA-F-]{36}$")
_BARRIER_FREE_SOURCES = {
    "https://walkingnavi.com/": "言葉の道案内",
    "https://www.lwd.tokyo/": "東京バリアフリーマップ",
}
_LEGACY_FIELDS = frozenset({"audit", "auditTrail", "externalRefs", "history", "referenceHistory", "refHistory", "changeHistory", "changedAt", "updatedAt", "confirmedAt", "firstConfirmedAt", "lastConfirmedAt", "supersededAt", "current", "superseded", "llmVote", "llmVotes", "llmVoteLog", "voteLog", "voteHistory", "decisionLog", "votes"})



def new_uuid7(timestamp_ms: int | None = None, random_bits: int | None = None) -> str:
    import secrets
    timestamp_ms = timestamp_ms if timestamp_ms is not None else time.time_ns() // 1_000_000
    random_bits = random_bits if random_bits is not None else secrets.randbits(74)
    value = ((timestamp_ms & ((1 << 48) - 1)) << 80) | (0x7 << 76) | (((random_bits >> 62) & 0xFFF) << 64) | (0b10 << 62) | (random_bits & ((1 << 62) - 1))
    return str(uuid.UUID(int=value))


def _is_uuid7(value: Any) -> bool:
    try: return uuid.UUID(str(value)).version == 7
    except (ValueError, TypeError, AttributeError): return False


def _valid_coordinates(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in value) and -180 <= value[0] <= 180 and -90 <= value[1] <= 90


def barrier_free_source(prefix: str) -> str:
    for source_prefix, name in _BARRIER_FREE_SOURCES.items():
        if prefix.startswith(source_prefix): return name
    raise ValueError(f"URL is outside the allowed barrier-free link domains: {prefix}")


def barrier_free_webpage(url: str) -> dict[str, Any]:
    name = barrier_free_source(url)
    return {"@type": "schema:WebPage", "schema:url": url, "schema:name": name,
            "schema:provider": {"@type": "schema:Organization", "schema:name": name}}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_search_document(document: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not isinstance(document, dict): return ["search document must be an object"]
    if set(document) - {"queries"}: issues.append("unexpected top-level fields")
    queries = document.get("queries")
    if not isinstance(queries, list): return issues + ["queries must be an array"]
    seen = set()
    for index, query in enumerate(queries):
        prefix = f"queries[{index}]"
        if not isinstance(query, dict): issues.append(f"{prefix}: query must be an object"); continue
        if set(query) - {"id", "name", "coordinates", "qid", "publish"}: issues.append(f"{prefix}: unexpected fields")
        if not _is_uuid7(query.get("id")): issues.append(f"{prefix}: id must be UUIDv7")
        elif query["id"] in seen: issues.append(f"{prefix}: duplicate id: {query['id']}")
        if isinstance(query.get("id"), str): seen.add(query["id"])
        if not isinstance(query.get("name"), str) or not query["name"].strip(): issues.append(f"{prefix}: name must be a non-empty string")
        if "coordinates" not in query and "qid" not in query: issues.append(f"{prefix}: coordinates or qid is required")
        if "publish" in query and not isinstance(query["publish"], bool): issues.append(f"{prefix}: publish must be boolean")
        if "coordinates" in query and not _valid_coordinates(query["coordinates"]): issues.append(f"{prefix}: coordinates must be [longitude, latitude]")
        if "qid" in query and (not isinstance(query["qid"], str) or not _QID.fullmatch(query["qid"])): issues.append(f"{prefix}: invalid qid")
    return issues


def validate_jsonld_document(document: Any, *, allow_image: bool = False) -> None:
    if not isinstance(document, dict): raise ValueError("JSON-LD document must be an object")
    context = document.get("@context")
    if not isinstance(context, dict) or context.get("@version") != 1.1 or context.get("schema") != "https://schema.org/" or context.get("rdfs") != "http://www.w3.org/2000/01/rdf-schema#": raise ValueError("JSON-LD @context must declare the canonical schema and rdfs prefixes")
    def reject(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                if key in _LEGACY_FIELDS or (key == "status" and nested in {"current", "superseded"}): raise ValueError(f"JSON-LD {path} contains legacy operational field: {key}")
                reject(nested, f"{path}.{key}")
        elif isinstance(value, list):
            for i, nested in enumerate(value): reject(nested, f"{path}[{i}]")
    reject(document, "document")
    graph = document.get("@graph")
    if not isinstance(graph, list): raise ValueError("JSON-LD document @graph must be a list")
    seen = set()
    for i, record in enumerate(graph):
        path = f"@graph[{i}]"
        if not isinstance(record, dict): raise ValueError(f"JSON-LD {path} must be an object")
        identifier = record.get("@id")
        if not isinstance(identifier, str) or not _URN_UUID.fullmatch(identifier): raise ValueError(f"JSON-LD {path} @id must be a urn:uuid UUID")
        if identifier in seen: raise ValueError(f"JSON-LD {path} @id duplicates a previous record: {identifier}")
        seen.add(identifier)
        if not isinstance(record.get("@type"), list) or "schema:Place" not in record["@type"]: raise ValueError(f"JSON-LD {path} @type must contain schema:Place")
        image = record.get("schema:image")
        if image is not None:
            if not allow_image: raise ValueError(f"JSON-LD {path} must not contain schema:image: the canonical dataset carries associations only")
            if not _valid_image(image): raise ValueError(f"JSON-LD {path} schema:image must be a single schema:ImageObject with schema:contentUrl, schema:license and schema:creator")
        geo = record.get("schema:geo")
        if "geo:hasGeometry" in record or "geo:asGeoJSON" in record or not isinstance(geo, dict) or geo.get("@type") != "schema:GeoCoordinates" or not _valid_coordinates([geo.get("schema:longitude"), geo.get("schema:latitude")]): raise ValueError(f"JSON-LD {path} schema:geo must be schema:GeoCoordinates with valid schema:latitude and schema:longitude")
        identifiers = record.get("schema:identifier", [])
        if not isinstance(identifiers, list): raise ValueError(f"JSON-LD {path} schema:identifier must be a list")
        for item in identifiers:
            if not isinstance(item, dict) or item.get("@type") != "schema:PropertyValue" or not isinstance(item.get("schema:propertyID"), str) or not item["schema:propertyID"] or not isinstance(item.get("schema:value"), str) or not item["schema:value"] or item["schema:propertyID"] in {"openstreetmap", "wikidata"}: raise ValueError(f"JSON-LD {path} has invalid schema:identifier")
        links = record.get("rdfs:seeAlso", [])
        if not isinstance(links, list) or any(not isinstance(uri, str) or (_OSM_TYPED_OBJECT_ID.fullmatch(uri.removeprefix("https://www.openstreetmap.org/")) is None and _WIKIDATA_ENTITY_URI.fullmatch(uri) is None) for uri in links): raise ValueError(f"JSON-LD {path} rdfs:seeAlso must be official HTTPS OpenStreetMap or Wikidata URIs")
        pages = record.get("schema:subjectOf", [])
        urls = []
        if not isinstance(pages, list) or any(not _valid_webpage(page) for page in pages): raise ValueError(f"JSON-LD {path} schema:subjectOf must be barrier-free schema:WebPage nodes")
        for page in pages:
            if page["schema:url"] in urls: raise ValueError(f"JSON-LD {path} schema:subjectOf duplicates a URL: {page['schema:url']}")
            urls.append(page["schema:url"])


def _valid_image(image: Any) -> bool:
    if not isinstance(image, dict) or not isinstance(image.get("@type"), list) or "schema:ImageObject" not in image["@type"]: return False
    if not isinstance(image.get("schema:contentUrl"), str) or not image["schema:contentUrl"].startswith("https://"): return False
    license_value = image.get("schema:license")
    if not isinstance(license_value, str) or not license_value.strip(): return False
    creator = image.get("schema:creator")
    if not isinstance(creator, dict) or not isinstance(creator.get("@type"), list) or "schema:Person" not in creator["@type"]: return False
    return isinstance(creator.get("schema:name"), str) and bool(creator["schema:name"].strip())


def validate_published_document(document: Any) -> None:
    validate_jsonld_document(document, allow_image=True)


def _valid_webpage(page: Any) -> bool:
    if not isinstance(page, dict) or page.get("@type") != "schema:WebPage": return False
    url = page.get("schema:url")
    if not isinstance(url, str): return False
    try: name = barrier_free_source(url)
    except ValueError: return False
    if page.get("schema:name") != name: return False
    return page.get("schema:provider") == {"@type": "schema:Organization", "schema:name": name}


def jsonld_place_index(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    validate_jsonld_document(document)
    return {record["@id"].removeprefix("urn:uuid:"): record for record in document["@graph"]}


def collect_osm_ids(document: dict[str, Any]) -> list[str]:
    return sorted({uri.removeprefix("https://www.openstreetmap.org/") for record in document.get("@graph", []) for uri in record.get("rdfs:seeAlso", []) if isinstance(uri, str) and uri.startswith("https://www.openstreetmap.org/") and _OSM_TYPED_OBJECT_ID.fullmatch(uri.removeprefix("https://www.openstreetmap.org/"))})


def collect_wikidata_ids(document: dict[str, Any]) -> set[str]:
    return {uri.rsplit("/", 1)[1] for record in document.get("@graph", []) for uri in record.get("rdfs:seeAlso", []) if isinstance(uri, str) and _WIKIDATA_ENTITY_URI.fullmatch(uri)}


def _distance_metres(first: list[float], second: list[float]) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, [*first, *second]); dlon, dlat = lon2-lon1, lat2-lat1
    return 6_371_000 * 2 * math.atan2(math.sqrt(math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2), math.sqrt(1-(math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2)))


def normalize_osm_elements(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result=[]
    for index, element in enumerate(elements):
        kind, identifier, tags = element.get("type"), element.get("id"), element.get("tags", {})
        if kind not in {"node","way","relation"} or isinstance(identifier,bool) or not isinstance(identifier,int) or identifier <= 0 or not isinstance(tags,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in tags.items()): raise ValueError(f"invalid OSM element at index {index}")
        coords=[element.get("lon"),element.get("lat")] if kind == "node" else [element.get("center",{}).get("lon"),element.get("center",{}).get("lat")]
        if not _valid_coordinates(coords): raise ValueError(f"invalid OSM coordinates at index {index}")
        if tags.get("wikidata") is not None and not _QID.fullmatch(tags["wikidata"]): raise ValueError(f"invalid OSM Wikidata QID at index {index}")
        item={"type":kind,"id":str(identifier),"name":tags.get("name"),"coordinates":coords,"tags":copy.deepcopy(tags)}
        if tags.get("wikidata"): item["qid"]=tags["wikidata"]
        result.append(item)
    return result


def source_refresh_due(last_retrieved_at: str | None, now: str) -> bool:
    try: current=datetime.fromisoformat(now.replace("Z","+00:00"))
    except (AttributeError,ValueError) as error: raise ValueError("invalid current retrieval time") from error
    if current.tzinfo is None or current.utcoffset() is None: raise ValueError("retrieval time must include a timezone")
    if last_retrieved_at is None: return True
    try: previous=datetime.fromisoformat(last_retrieved_at.replace("Z","+00:00"))
    except (AttributeError,ValueError) as error: raise ValueError("invalid previous retrieval time") from error
    if previous.tzinfo is None or previous.utcoffset() is None or previous > current: raise ValueError("invalid previous retrieval time")
    return current-previous >= timedelta(days=30)


def load_queries(root: Path) -> list[dict[str, Any]]:
    document = _read_json(root / "inputs/facilities.json")
    issues = validate_search_document(document)
    if issues:
        raise ValueError("; ".join(issues))
    return document["queries"]


def validate_repository(root: str | Path) -> list[str]:
    root = Path(root)
    try:
        validate_jsonld_document(_read_json(root / "data/places.jsonld"))
        if (root / "inputs/facilities.json").exists():
            load_queries(root)
    except (OSError, ValueError, TypeError) as error:
        return [str(error)]
    return []


def build_repository(root: str | Path) -> Path:
    issues=validate_repository(root)
    if issues: raise ValueError("; ".join(issues))
    root = Path(root)
    document = _read_json(root / "data/places.jsonld")
    excluded = {q["id"] for q in load_queries(root) if q.get("publish") is False} if (root / "inputs/facilities.json").exists() else set()
    document["@graph"] = [p for p in document["@graph"] if p["@id"].removeprefix("urn:uuid:") not in excluded]
    associated_ids = set(collect_osm_ids(document))
    referenced_qids = collect_wikidata_ids(document)
    for source_id, filename in (("openstreetmap", "osm.json"), ("wikidata", "wikidata.json")):
        source = root / f"imports/{source_id}/raw.json"
        if not source.exists(): continue
        mirrors = root / "site/mirrors"
        mirrors.mkdir(parents=True, exist_ok=True)
        filtered = _read_json(source)
        if source_id == "openstreetmap":
            filtered["elements"] = [element for element in filtered.get("elements", []) if f"{element.get('type')}/{element.get('id')}" in associated_ids]
        else:
            filtered["entities"] = {qid: entity for qid, entity in filtered.get("entities", {}).items() if qid in referenced_qids}
        _write_json(mirrors / filename, filtered)
    _apply_images(root, document)
    validate_jsonld_document(document, allow_image=True)
    artifact = root / "site/places.jsonld"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    _write_json(artifact, document)
    return artifact


def _image_file_name(place: dict[str, Any], osm_files: dict[str, Any], p18_files: dict[str, str]) -> str | None:
    for uri in place.get("rdfs:seeAlso", []):
        if isinstance(uri, str) and uri.startswith("https://www.wikidata.org/entity/"):
            value = p18_files.get(uri.rsplit("/", 1)[1])
            if value: return value
    for uri in place.get("rdfs:seeAlso", []):
        if isinstance(uri, str) and uri.startswith("https://www.openstreetmap.org/"):
            value = osm_files.get(uri.removeprefix("https://www.openstreetmap.org/"))
            if isinstance(value, str) and value.startswith("File:"): return value
    return None


def _apply_images(root: Path, document: dict[str, Any]) -> None:
    osm_mirror, wikidata_mirror, commons_path = root / "site/mirrors/osm.json", root / "site/mirrors/wikidata.json", root / "imports/commons/raw.json"
    if not (osm_mirror.exists() and wikidata_mirror.exists() and commons_path.exists()): return
    osm_files = {f"{element.get('type')}/{element.get('id')}": (element.get("tags") or {}).get("wikimedia_commons") for element in _read_json(osm_mirror).get("elements", []) if isinstance(element, dict)}
    p18_files = {}
    for qid, entity in _read_json(wikidata_mirror).get("entities", {}).items():
        claims = (entity.get("claims") or {}).get("P18", [])
        value = claims[0].get("mainsnak", {}).get("datavalue", {}).get("value") if claims else None
        if isinstance(value, str) and value:
            p18_files[qid] = value if value.startswith("File:") else f"File:{value}"
    metadata = _read_json(commons_path).get("files", {})
    for place in document["@graph"]:
        name = _image_file_name(place, osm_files, p18_files)
        meta = metadata.get(name) if name else None
        if not isinstance(meta, dict) or not meta.get("url") or not meta.get("license") or not meta.get("artist"): continue
        place["schema:image"] = {
            "@type": ["schema:ImageObject"],
            "schema:contentUrl": meta["url"],
            "schema:license": meta.get("licenseUrl") or meta["license"],
            "schema:creator": {"@type": ["schema:Person"], "schema:name": meta["artist"]},
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and publish canonical JSON-LD")
    parser.add_argument("command", choices=("validate", "build"))
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            print(build_repository(args.root))
        else:
            issues = validate_repository(args.root)
            if issues:
                raise ValueError("; ".join(issues))
            print("Validation passed")
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
