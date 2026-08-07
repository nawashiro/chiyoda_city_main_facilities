from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import unicodedata
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from src.facility_data import source_refresh_due
from src.http_utils import read_limited_response
from src.wam_contract import WAM_PUBLIC_ATTRIBUTE_HEADERS, WAM_PUBLIC_ATTRIBUTE_SET


_WAM_ADDRESS = "東京都千代田区"
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_CSV_BYTES = 64 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
MAX_CSV_ROWS = 500_000
WAM_INCLUDED_SERVICE_CODES = ("52", "53", "54", "70")
_REQUIRED_HEADERS = WAM_PUBLIC_ATTRIBUTE_SET


def _distance_metres(first: list[float], second: list[float]) -> float:
    lon1, lat1 = map(math.radians, first)
    lon2, lat2 = map(math.radians, second)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6_371_000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _comparison_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = normalized.replace("千代田区立", "")
    return re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠々ー]+", "", normalized)


def _names_match(first: str, second: str) -> bool:
    left = _comparison_name(first)
    right = _comparison_name(second)
    if left == right:
        return True
    shorter, longer = sorted((left, right), key=len)
    return len(shorter) >= 6 and shorter in longer


def _stable_uuid7(release: str, source_record_ids: list[str]) -> str:
    if not re.fullmatch(r"20[0-9]{4}", release):
        raise ValueError("WAM release must be YYYYMM")
    year = int(release[:4])
    month = int(release[4:])
    if not 1 <= month <= 12:
        raise ValueError("WAM release month must be 01 through 12")
    milliseconds = int(datetime(year, month, 1, tzinfo=timezone.utc).timestamp() * 1000)
    digest = int.from_bytes(
        hashlib.sha256(("wam:" + ":".join(sorted(source_record_ids))).encode()).digest()[:10],
        "big",
    )
    random_a = (digest >> 68) & 0xFFF
    random_b = digest & ((1 << 62) - 1)
    value = (milliseconds << 80) | (7 << 76) | (random_a << 64) | (2 << 62) | random_b
    return str(uuid.UUID(int=value))


def fetch_wam_release(
    release: str, fetcher
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, bytes]]:
    """Fetch the fixed non-visiting service archive set and record provenance."""
    if not re.fullmatch(r"20[0-9]{4}", release):
        raise ValueError("WAM release must be YYYYMM")
    rows = []
    artifacts = []
    downloads = {}
    for service_code in WAM_INCLUDED_SERVICE_CODES:
        url = (
            "https://www.wam.go.jp/content/files/pcpub/top/sfkopendata/"
            f"{release}/sfkopendata_{release}_{service_code}.zip"
        )
        payload, headers = fetcher(url)
        if not isinstance(payload, bytes) or not payload:
            raise ValueError(f"empty WAM archive: {service_code}")
        if len(payload) > MAX_ARCHIVE_BYTES:
            raise ValueError(f"WAM archive is too large: {service_code}")
        rows.extend(parse_wam_zip(payload, service_code))
        downloads[service_code] = payload
        artifacts.append(
            {
                "serviceCode": service_code,
                "url": url,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "etag": headers.get("ETag"),
                "lastModified": headers.get("Last-Modified"),
                "contentLength": len(payload),
            }
        )
    return (
        sorted(rows, key=lambda item: (item["sourceRecordId"], item["serviceCode"])),
        artifacts,
        downloads,
    )


def parse_wam_zip(payload: bytes, service_code: str) -> list[dict[str, Any]]:
    """Parse one official WAM service archive and retain valid Chiyoda rows."""
    if not re.fullmatch(r"[0-9]{2}", service_code):
        raise ValueError("invalid WAM service code")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = [item for item in archive.infolist() if not item.is_dir()]
        if len(members) != 1 or not members[0].filename.lower().endswith(".csv"):
            raise ValueError("WAM archive must contain exactly one CSV")
        member = members[0]
        if member.file_size > MAX_CSV_BYTES:
            raise ValueError("WAM expanded CSV is too large")
        if member.file_size / max(member.compress_size, 1) > MAX_COMPRESSION_RATIO:
            raise ValueError("WAM ZIP compression ratio is too high")
        text = archive.read(member).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or not _REQUIRED_HEADERS.issubset(reader.fieldnames):
        raise ValueError("WAM CSV is missing required headers")
    rows = []
    for source in reader:
        if reader.line_num > MAX_CSV_ROWS + 1:
            raise ValueError("WAM CSV has too many rows")
        if source.get("事業所住所（市区町村）") != _WAM_ADDRESS:
            continue
        source_id = (source.get("NO（※システム内の固有の番号、連番）") or "").strip()
        office_id = (source.get("事業所番号") or "").strip()
        name = (source.get("事業所の名称") or "").strip()
        service_type = (source.get("サービス種別") or "").strip()
        if not source_id or not office_id or not name or not service_type:
            raise ValueError("WAM row is missing a stable ID, name, or service")
        try:
            coordinates = [float(source["事業所経度"]), float(source["事業所緯度"])]
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("WAM row has invalid coordinates") from error
        if not (-180 <= coordinates[0] <= 180 and -90 <= coordinates[1] <= 90):
            raise ValueError("WAM row has invalid coordinates")
        rows.append(
            {
                "sourceRecordId": source_id,
                "officeId": office_id,
                "serviceCode": service_code,
                "serviceType": service_type,
                "name": name,
                "coordinates": coordinates,
                "attributes": {
                    header: (source.get(header) or "").strip()
                    for header in WAM_PUBLIC_ATTRIBUTE_HEADERS
                },
            }
        )
    return rows


def prepare_wam_release(
    rows: list[dict[str, Any]],
    existing_search_documents: list[dict[str, Any]],
    release: str,
    retrieved_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Group service rows, reuse safe existing queries, and create stable new searches."""
    existing_queries = [
        query
        for document in existing_search_documents
        for query in document.get("queries", [])
        if "coordinates" in query
    ]
    groups: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: item["sourceRecordId"]):
        matches = [
            group
            for group in groups
            if _names_match(group["name"], row["name"])
            and _distance_metres(group["coordinates"], row["coordinates"]) <= 50
        ]
        if len(matches) > 1:
            raise ValueError("WAM row matches multiple grouped facilities")
        if matches:
            matches[0]["rows"].append(row)
        else:
            groups.append(
                {
                    "name": row["name"],
                    "coordinates": list(row["coordinates"]),
                    "rows": [row],
                }
            )

    new_queries = []
    records = []
    used_query_ids: set[str] = set()
    for group in groups:
        candidates = [
            query
            for query in existing_queries
            if _names_match(group["name"], query["name"])
            and _distance_metres(group["coordinates"], query["coordinates"]) <= 50
        ]
        if len(candidates) > 1:
            raise ValueError("WAM facility matches multiple existing search queries")
        source_ids = sorted({row["sourceRecordId"] for row in group["rows"]})
        if candidates:
            query_id = candidates[0]["id"]
        else:
            query_id = _stable_uuid7(release, source_ids)
            new_queries.append(
                {
                    "id": query_id,
                    "name": group["name"],
                    "coordinates": group["coordinates"],
                }
            )
        if query_id in used_query_ids:
            raise ValueError("duplicate WAM query mapping")
        used_query_ids.add(query_id)
        primary = sorted(group["rows"], key=lambda item: item["sourceRecordId"])[0]
        records.append(
            {
                "queryId": query_id,
                "id": primary["sourceRecordId"],
                "sourceRecordIds": source_ids,
                "officeIds": sorted({row["officeId"] for row in group["rows"]}),
                "serviceCodes": sorted({row["serviceCode"] for row in group["rows"]}),
                "serviceTypes": sorted({row["serviceType"] for row in group["rows"]}),
                "name": group["name"],
                "coordinates": group["coordinates"],
            }
        )
    search = {
        "source": {
            "kind": "source",
            "sourceId": "wam",
            "retrievedAt": retrieved_at,
        },
        "queries": sorted(new_queries, key=lambda item: item["id"]),
    }
    return search, {"records": sorted(records, key=lambda item: item["queryId"])}


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def run_wam_retrieval(
    root: str | Path,
    release: str,
    at: str,
    fetcher,
) -> tuple[Path, Path]:
    """Retrieve and prepare one complete WAM release for application."""
    root = Path(root)
    metadata_path = root / "imports/wam/retrieval.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    source_refresh_due(None, at)
    rows, artifacts, _downloads = fetch_wam_release(release, fetcher)
    target_search = root / f"inputs/osm-search/wam/{release}.json"
    existing_documents = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "inputs/osm-search").rglob("*.json"))
        if path != target_search
    ]
    search, normalized = prepare_wam_release(rows, existing_documents, release, at)
    raw = {"version": release, "rows": rows}
    raw_payload = (json.dumps(raw, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    retrieval = {
        **metadata,
        "sourceId": "wam",
        "retrievedAt": at,
        "rawVersion": release,
        "rawSha256": hashlib.sha256(raw_payload).hexdigest(),
        "artifacts": artifacts,
    }
    normalized_path = root / "imports/wam/normalized.json"
    _write_json(target_search, search)
    raw_path = root / "imports/wam/raw.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(raw_payload)
    _write_json(normalized_path, normalized)
    _write_json(metadata_path, retrieval)
    return target_search, normalized_path


def _http_fetch(url: str) -> tuple[bytes, dict[str, str | None]]:
    request = Request(url, headers={"User-Agent": "chiyoda-city-main-facilities/1"})
    with urlopen(request, timeout=120) as response:
        return read_limited_response(response, MAX_ARCHIVE_BYTES, "WAM"), {
            "ETag": response.headers.get("ETag"),
            "Last-Modified": response.headers.get("Last-Modified"),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retrieve one official WAM release")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--release", required=True)
    parser.add_argument("--at", required=True)
    args = parser.parse_args(argv)
    try:
        search_path, normalized_path = run_wam_retrieval(
            args.root, args.release, args.at, _http_fetch
        )
    except (OSError, ValueError, zipfile.BadZipFile, UnicodeError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 1
    print(search_path)
    print(normalized_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
