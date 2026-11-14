"""Retain Commons file metadata for the images of the associated elements."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.facility_data import _read_json, _write_json
from src.http_utils import read_limited_response


COMMONS_API = "https://commons.wikimedia.org/w/api.php"
PAGE_SIZE = 50
EXTMETADATA = "LicenseShortName|LicenseUrl|Artist"


def _get(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "chiyoda-city-main-facilities/1"})
    with urlopen(request, timeout=240) as response:
        return read_limited_response(response, 16 * 1024 * 1024, "Commons file metadata")


def _common_title(value: str) -> str:
    return value if value.startswith("File:") else f"File:{value}"


def collect_file_names(root: str | Path) -> list[str]:
    """The committed mirrors already hold the association-scoped elements and entities."""
    root = Path(root)
    names: set[str] = set()
    osm_mirror = root / "site/mirrors/osm.json"
    if osm_mirror.exists():
        for element in _read_json(osm_mirror).get("elements", []):
            tag = (element.get("tags") or {}).get("wikimedia_commons")
            if isinstance(tag, str) and tag.startswith("File:"):
                names.add(tag)
    wikidata_mirror = root / "site/mirrors/wikidata.json"
    if wikidata_mirror.exists():
        for entity in _read_json(wikidata_mirror).get("entities", {}).values():
            for claim in (entity.get("claims") or {}).get("P18", []):
                value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
                if isinstance(value, str) and value:
                    names.add(_common_title(value))
    return sorted(names)


def _metadata_text(extmetadata: dict[str, Any], key: str) -> str | None:
    value = extmetadata.get(key, {}).get("value") if isinstance(extmetadata.get(key), dict) else None
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _artist_text(extmetadata: dict[str, Any]) -> str | None:
    value = _metadata_text(extmetadata, "Artist")
    if value is None:
        return None
    text = html.unescape(re.sub(r"<[^>]*>", "", value)).strip()
    return text or None


def _content_url(info: dict[str, Any]) -> str | None:
    value = info.get("url")
    if not isinstance(value, str) or not value.startswith("https://"):
        return None
    # Commons API appends utm tracking parameters to imageinfo urls.
    return value.split("?", 1)[0] or None


def _query_files(titles: list[str], fetch) -> dict[str, dict[str, Any]]:
    url = f"{COMMONS_API}?{urlencode({'action': 'query', 'titles': '|'.join(titles), 'prop': 'imageinfo', 'iiprop': 'url|extmetadata', 'iiextmetadatafilter': EXTMETADATA, 'format': 'json'})}"
    query = (json.loads(fetch(url)).get("query") or {})
    normalized = {item["to"]: item["from"] for item in query.get("normalized", []) if isinstance(item, dict) and "from" in item and "to" in item}
    files: dict[str, dict[str, Any]] = {}
    for page in (query.get("pages") or {}).values():
        if not isinstance(page, dict) or "missing" in page:
            continue
        title = normalized.get(page.get("title"), page.get("title"))
        info = (page.get("imageinfo") or [{}])[0]
        content_url = _content_url(info)
        extmetadata = info.get("extmetadata") or {}
        license_name = _metadata_text(extmetadata, "LicenseShortName")
        if not title or not content_url or not license_name:
            continue
        files[title] = {
            "url": content_url,
            "license": license_name,
            "licenseUrl": _metadata_text(extmetadata, "LicenseUrl"),
            "artist": _artist_text(extmetadata),
        }
    return files


def run_commons_retrieval(root: str | Path, at: str, fetch=_get) -> Path:
    root = Path(root)
    names = collect_file_names(root)
    files: dict[str, dict[str, Any]] = {}
    pages = 0
    for start in range(0, len(names), PAGE_SIZE):
        chunk = names[start:start + PAGE_SIZE]
        files.update(_query_files(chunk, fetch))
        pages += 1
    document = {"sourceId": "commons", "retrievedAt": at, "files": files}
    payload = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    metadata = {"sourceId": "commons", "retrievedAt": at, "endpoint": COMMONS_API, "fileCount": len(names), "pages": pages, "rawSha256": hashlib.sha256(payload).hexdigest()}
    _write_json(root / "imports/commons/raw.json", document)
    _write_json(root / "imports/commons/retrieval.json", metadata)
    print(f"Commons metadata: {len(names)} files in {pages} requests", file=sys.stderr)
    return root / "imports/commons/raw.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retrieve the Commons metadata for associated image files")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--at", required=True)
    args = parser.parse_args(argv)
    try:
        print(run_commons_retrieval(args.root, args.at))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
