"""Canonical JSON-LD facility data validation and source update helpers."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import time
import unicodedata
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.wam_contract import WAM_PUBLIC_ATTRIBUTE_HEADERS, WAM_PUBLIC_ATTRIBUTE_SET

_QID = re.compile(r"^Q[1-9][0-9]*$")
_OSM_TYPED_OBJECT_ID = re.compile(r"^(node|way|relation)/([1-9][0-9]*)$")
_WIKIDATA_ENTITY_URI = re.compile(r"^https://www\.wikidata\.org/entity/Q[1-9][0-9]*$")
_URN_UUID = re.compile(r"^urn:uuid:[0-9a-fA-F-]{36}$")
_LEGACY_FIELDS = frozenset({"audit", "auditTrail", "externalRefs", "history", "referenceHistory", "refHistory", "changeHistory", "changedAt", "updatedAt", "confirmedAt", "firstConfirmedAt", "lastConfirmedAt", "supersededAt", "current", "superseded", "llmVote", "llmVotes", "llmVoteLog", "voteLog", "voteHistory", "decisionLog", "votes"})
_WAM_VISITING_SERVICE_TYPES = {"11", "12", "13", "14", "15", "66", "67", "居宅介護", "重度訪問介護", "行動援護", "重度障害者等包括支援", "同行援護", "居宅訪問型児童発達支援", "保育所等訪問支援"}


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


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_search_document(document: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not isinstance(document, dict): return ["search document must be an object"]
    if set(document) - {"source", "queries"}: issues.append("unexpected top-level fields")
    source = document.get("source")
    if not isinstance(source, dict): issues.append("source must be an object")
    queries = document.get("queries")
    if not isinstance(queries, list): return issues + ["queries must be an array"]
    seen = set()
    for index, query in enumerate(queries):
        prefix = f"queries[{index}]"
        if not isinstance(query, dict): issues.append(f"{prefix}: query must be an object"); continue
        if set(query) - {"id", "name", "coordinates", "qid"}: issues.append(f"{prefix}: unexpected fields")
        if not _is_uuid7(query.get("id")): issues.append(f"{prefix}: id must be UUIDv7")
        elif query["id"] in seen: issues.append(f"{prefix}: duplicate id: {query['id']}")
        seen.add(query.get("id"))
        if not isinstance(query.get("name"), str) or not query["name"].strip(): issues.append(f"{prefix}: name must be a non-empty string")
        if ("coordinates" in query) == ("qid" in query): issues.append(f"{prefix}: exactly one of coordinates or qid is required")
        if "coordinates" in query and not _valid_coordinates(query["coordinates"]): issues.append(f"{prefix}: coordinates must be [longitude, latitude]")
        if "qid" in query and (not isinstance(query["qid"], str) or not _QID.fullmatch(query["qid"])): issues.append(f"{prefix}: invalid qid")
    return issues


def validate_jsonld_document(document: Any) -> None:
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
        geo = record.get("schema:geo")
        if "geo:hasGeometry" in record or "geo:asGeoJSON" in record or not isinstance(geo, dict) or geo.get("@type") != "schema:GeoCoordinates" or not _valid_coordinates([geo.get("schema:longitude"), geo.get("schema:latitude")]): raise ValueError(f"JSON-LD {path} schema:geo must be schema:GeoCoordinates with valid schema:latitude and schema:longitude")
        identifiers = record.get("schema:identifier", [])
        if not isinstance(identifiers, list): raise ValueError(f"JSON-LD {path} schema:identifier must be a list")
        for item in identifiers:
            if not isinstance(item, dict) or item.get("@type") != "schema:PropertyValue" or not isinstance(item.get("schema:propertyID"), str) or not item["schema:propertyID"] or not isinstance(item.get("schema:value"), str) or not item["schema:value"] or item["schema:propertyID"] in {"openstreetmap", "wikidata"}: raise ValueError(f"JSON-LD {path} has invalid schema:identifier")
        links = record.get("rdfs:seeAlso", [])
        if not isinstance(links, list) or any(not isinstance(uri, str) or (_OSM_TYPED_OBJECT_ID.fullmatch(uri.removeprefix("https://www.openstreetmap.org/")) is None and _WIKIDATA_ENTITY_URI.fullmatch(uri) is None) for uri in links): raise ValueError(f"JSON-LD {path} rdfs:seeAlso must be official HTTPS OpenStreetMap or Wikidata URIs")


def jsonld_place_index(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    validate_jsonld_document(document)
    return {record["@id"].removeprefix("urn:uuid:"): record for record in document["@graph"]}


def collect_osm_ids(document: dict[str, Any]) -> list[str]:
    return sorted({uri.removeprefix("https://www.openstreetmap.org/") for record in document.get("@graph", []) for uri in record.get("rdfs:seeAlso", []) if isinstance(uri, str) and uri.startswith("https://www.openstreetmap.org/") and _OSM_TYPED_OBJECT_ID.fullmatch(uri.removeprefix("https://www.openstreetmap.org/"))})


def _distance_metres(first: list[float], second: list[float]) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, [*first, *second]); dlon, dlat = lon2-lon1, lat2-lat1
    return 6_371_000 * 2 * math.atan2(math.sqrt(math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2), math.sqrt(1-(math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2)))


def _osm_comparison_name(value: str) -> str: return re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠々ー]+", "", unicodedata.normalize("NFKC", value).casefold())
def _osm_names_match(first: str, second: str) -> bool:
    left, right = _osm_comparison_name(first), _osm_comparison_name(second)
    if not left or not right: return False
    if left == right: return True
    if min(len(left),len(right)) < 6: return False
    previous = list(range(len(left)+1))
    for row, char in enumerate(right, 1):
        current=[row]
        for col, other in enumerate(left, 1): current.append(min(current[-1]+1, previous[col]+1, previous[col-1]+(char != other)))
        previous=current
    return previous[-1] <= min(3, max(1, round(max(len(left),len(right))*.15)))


def build_osm_batch_query(typed_ids: list[str], qids: list[str]) -> str:
    if any(_OSM_TYPED_OBJECT_ID.fullmatch(value) is None for value in typed_ids) or any(_QID.fullmatch(qid) is None for qid in qids): raise ValueError("invalid OSM ID or QID in batch query")
    grouped = {kind: [] for kind in ("node", "way", "relation")}
    for value in sorted(set(typed_ids)): kind, number = value.split("/", 1); grouped[kind].append(number)
    selectors = "".join(f"{kind}(id:{','.join(grouped[kind])});" for kind in grouped if grouped[kind]) + "".join(f'nwr["wikidata"="{qid}"];' for qid in sorted(set(qids)))
    return f"[out:json];({selectors});out center;" if selectors else ""


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


def normalize_wam_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized=[]
    for index,row in enumerate(rows):
        if str(row.get("serviceType","")).strip() in _WAM_VISITING_SERVICE_TYPES: continue
        coords=[row.get("longitude"),row.get("latitude")]
        if not _is_uuid7(row.get("placeId")) or isinstance(row.get("facilityId"),bool) or not isinstance(row.get("facilityId"),(str,int)) or not str(row["facilityId"]).strip() or not isinstance(row.get("name"),str) or not row["name"].strip() or not _valid_coordinates(coords): raise ValueError(f"invalid WAM row at index {index}")
        normalized.append({"queryId":row["placeId"],"id":str(row["facilityId"]),"name":row["name"],"coordinates":coords})
    return normalized


def _index_wam_raw_rows(rows: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(rows,list): raise ValueError("WAM raw rows must be an array")
    indexed={}
    for i,row in enumerate(rows):
        required={"sourceRecordId","officeId","serviceCode","serviceType","name"}
        if not isinstance(row,dict) or any(not isinstance(row.get(k),str) or not row[k] for k in required) or not _valid_coordinates(row.get("coordinates")) or not isinstance(row.get("attributes"),dict) or set(row["attributes"]) != WAM_PUBLIC_ATTRIBUTE_SET or any(not isinstance(v,str) for v in row["attributes"].values()): raise ValueError(f"WAM raw row {i} is invalid")
        if row["sourceRecordId"] in indexed: raise ValueError(f"duplicate WAM raw sourceRecordId: {row['sourceRecordId']}")
        indexed[row["sourceRecordId"]]=row
    return indexed


def validate_repository(root: str | Path) -> list[str]:
    root=Path(root); issues=[]; canonical=root/"data/places.jsonld"
    if not canonical.is_file(): return ["data/places.jsonld: canonical JSON-LD is required"]
    try: document=_read_json(canonical); validate_jsonld_document(document); place_by_id=jsonld_place_index(document)
    except (OSError,ValueError,TypeError,json.JSONDecodeError) as error: return [f"data/places.jsonld: {error}"]
    search_by_id={}
    for path in sorted((root/"inputs/osm-search").glob("**/*.json")):
        try: search=_read_json(path)
        except (OSError,json.JSONDecodeError) as error: issues.append(f"{path.relative_to(root)}: {error}"); continue
        issues.extend(validate_search_document(search))
        for query in search.get("queries",[]):
            if isinstance(query,dict):
                key=str(query.get("id")); issues.extend([f"duplicate search id across files: {key}"] if key in search_by_id else []); search_by_id[key]=query
    for source in ("wam","openstreetmap"):
        path=root/f"imports/{source}/normalized.json"
        if not path.exists(): continue
        try: records=_read_json(path).get("records",[])
        except (OSError,json.JSONDecodeError) as error: issues.append(f"imports/{source}/normalized.json: {error}"); continue
        if not isinstance(records,list): issues.append(f"imports/{source}/normalized.json: records must be an array"); continue
        for i,record in enumerate(records):
            if not isinstance(record,dict) or str(record.get("queryId")) not in search_by_id: issues.append(f"imports/{source}/normalized.json: records[{i}]: unknown or invalid queryId")
    site=root/"site/places.jsonld"
    if site.is_file() and site.read_bytes() != canonical.read_bytes(): issues.append("site/places.jsonld must be byte-identical to data/places.jsonld")
    return issues


def _set_osm_link(record: dict[str,Any], osm: dict[str,Any]) -> None:
    links=[uri for uri in record.get("rdfs:seeAlso",[]) if not (isinstance(uri,str) and (uri.startswith("https://www.openstreetmap.org/") or uri.startswith("https://www.wikidata.org/entity/")))]
    links.append(f"https://www.openstreetmap.org/{osm['type']}/{osm['id']}")
    if isinstance(osm.get("qid"),str) and _QID.fullmatch(osm["qid"]): links.append(f"https://www.wikidata.org/entity/{osm['qid']}")
    record["rdfs:seeAlso"]=links


def apply_source_updates(document: dict[str, Any], search_by_id: dict[str,dict[str,Any]], wam_records: list[dict[str,Any]], osm_records: list[dict[str,Any]], at: str, wam_raw_rows: list[dict[str,Any]] | None = None, decision_at: str | None = None) -> dict[str,Any]:
    """Apply selected sources directly to canonical JSON-LD, without history."""
    del at, decision_at
    updated=copy.deepcopy(document); index=jsonld_place_index(updated)
    if wam_records and wam_raw_rows is None: raise ValueError("retained WAM raw rows are required for application")
    raw=_index_wam_raw_rows(wam_raw_rows or [])
    for record in wam_records:
        query_id=str(record.get("queryId")); query=search_by_id.get(query_id)
        if query is None: raise ValueError(f"unknown WAM queryId: {query_id}")
        ids=record.get("sourceRecordIds",[record.get("id")])
        if not isinstance(ids,list) or not ids or any(str(value) not in raw for value in ids): raise ValueError("WAM sourceRecordIds are not present in raw rows")
        place=index.get(query_id)
        if place is None:
            place={"@id":f"urn:uuid:{query_id}","@type":["schema:Place"],"schema:identifier":[],"schema:geo":{"@type":"schema:GeoCoordinates","schema:latitude":record["coordinates"][1],"schema:longitude":record["coordinates"][0]}}; updated["@graph"].append(place); index[query_id]=place
        place["schema:identifier"]=[item for item in place.get("schema:identifier",[]) if item.get("schema:propertyID") != "wam"] + [{"@type":"schema:PropertyValue","schema:propertyID":"wam","schema:value":str(value)} for value in sorted(set(ids))]
        place["schema:geo"]={"@type":"schema:GeoCoordinates","schema:latitude":record["coordinates"][1],"schema:longitude":record["coordinates"][0]}
    for record in osm_records:
        query_id=str(record.get("queryId")); query=search_by_id.get(query_id)
        if query is None: raise ValueError(f"unknown OSM queryId: {query_id}")
        if record.get("type") not in {"node","way","relation"} or not isinstance(record.get("id"),str) or not record["id"].isdigit() or not _valid_coordinates(record.get("coordinates")): raise ValueError("invalid OSM record")
        place=index.get(query_id)
        if place is None:
            place={"@id":f"urn:uuid:{query_id}","@type":["schema:Place"],"schema:identifier":[],"schema:geo":{"@type":"schema:GeoCoordinates","schema:latitude":record["coordinates"][1],"schema:longitude":record["coordinates"][0]}}; updated["@graph"].append(place); index[query_id]=place
        _set_osm_link(place,record)
        place["schema:geo"]={"@type":"schema:GeoCoordinates","schema:latitude":record["coordinates"][1],"schema:longitude":record["coordinates"][0]}
    validate_jsonld_document(updated); return updated


def update_repository(root: str | Path, at: str, source: str, **_: Any) -> Path:
    if source not in {"wam","openstreetmap"}: raise ValueError(f"unsupported update source: {source}")
    source_refresh_due(None,at); root=Path(root)
    issues=validate_repository(root)
    if issues: raise ValueError("; ".join(issues))
    document=_read_json(root/"data/places.jsonld"); search_by_id={str(q["id"]):q for p in (root/"inputs/osm-search").glob("**/*.json") for q in _read_json(p).get("queries",[])}
    records=lambda name: _read_json(root/f"imports/{name}/normalized.json").get("records",[]) if (root/f"imports/{name}/normalized.json").exists() else []
    updated=apply_source_updates(document,search_by_id,records("wam") if source=="wam" else [],records("openstreetmap") if source=="openstreetmap" else [],at,wam_raw_rows=_read_json(root/"imports/wam/raw.json").get("rows",[]) if source=="wam" else None)
    _write_json(root/"data/places.jsonld",updated); _write_json(root/"site/places.jsonld",updated)
    return root/"data/places.jsonld"


def build_repository(root: str | Path) -> Path:
    issues=validate_repository(root)
    if issues: raise ValueError("; ".join(issues))
    return Path(root)/"data/places.jsonld"


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="Maintain canonical JSON-LD facility data"); parser.add_argument("command",choices=("validate","build","update")); parser.add_argument("root",nargs="?",default="."); parser.add_argument("--at"); parser.add_argument("--source",choices=("wam","openstreetmap")); args=parser.parse_args(argv)
    try:
        if args.command == "update":
            if args.at is None or args.source is None: raise ValueError("update requires --source and --at")
            print(update_repository(args.root,args.at,args.source))
        elif args.command == "build": print(build_repository(args.root))
        else:
            issues=validate_repository(args.root)
            if issues: raise ValueError("; ".join(issues))
            print("Validation passed")
    except (OSError,ValueError,json.JSONDecodeError) as error: print(f"ERROR: {error}"); return 1
    return 0

if __name__ == "__main__": raise SystemExit(main())
