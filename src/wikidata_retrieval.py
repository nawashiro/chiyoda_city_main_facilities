"""Retain Wikidata entities for the QIDs found in the OSM mirror."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.facility_data import _write_json
from src.http_utils import read_limited_response


WIKIDATA_API = "https://www.wikidata.org/w/api.php"
PAGE_SIZE = 50
PROPS = "info|labels|aliases|descriptions|claims|sitelinks"


def _get(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "chiyoda-city-main-facilities/1"})
    with urlopen(request, timeout=240) as response:
        return read_limited_response(response, 64 * 1024 * 1024, "Wikidata entities")


def collect_qids(raw: dict[str, Any]) -> list[str]:
    return sorted({
        tag
        for element in raw.get("elements", [])
        if isinstance(element.get("tags"), dict)
        for key in ("wikidata", "operator:wikidata")
        if isinstance(tag := element["tags"].get(key), str) and tag
    })


def run_wikidata_retrieval(root: str | Path, at: str, fetch=_get) -> Path:
    root = Path(root)
    raw_path = root / "imports/wikidata/raw.json"
    osm = json.loads((root / "imports/openstreetmap/raw.json").read_text(encoding="utf-8"))
    qids = collect_qids(osm)
    entities: dict[str, Any] = {}
    pages = 0
    for start in range(0, len(qids), PAGE_SIZE):
        chunk = qids[start:start + PAGE_SIZE]
        url = f"{WIKIDATA_API}?{urlencode({'action': 'wbgetentities', 'ids': '|'.join(chunk), 'props': PROPS, 'format': 'json'})}"
        entities.update(json.loads(fetch(url)).get("entities") or {})
        pages += 1
    document = {"sourceId": "wikidata", "retrievedAt": at, "entities": entities}
    payload = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    metadata = {"sourceId": "wikidata", "retrievedAt": at, "endpoint": WIKIDATA_API, "qidCount": len(qids), "pages": pages, "rawSha256": hashlib.sha256(payload).hexdigest()}
    _write_json(raw_path, document)
    _write_json(root / "imports/wikidata/retrieval.json", metadata)
    print(f"Wikidata mirror: {len(qids)} QIDs in {pages} requests", file=sys.stderr)
    return raw_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retrieve the Wikidata mirror for retained QIDs")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--at", required=True)
    args = parser.parse_args(argv)
    try:
        print(run_wikidata_retrieval(args.root, args.at))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
