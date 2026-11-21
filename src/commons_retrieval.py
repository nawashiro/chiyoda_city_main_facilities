"""Retain Commons file metadata for the images of the associated elements."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.commons_files import commons_file_title
from src.facility_data import _read_json, _write_json
from src.http_utils import read_limited_response


COMMONS_API = "https://commons.wikimedia.org/w/api.php"
PAGE_SIZE = 50
EXTMETADATA = "LicenseShortName|LicenseUrl|Artist"
_WORDS = re.compile(r"[^\W_]+")
_UNKNOWN_ARTIST = re.compile(r"^unknown\b", re.IGNORECASE)


def _get(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "chiyoda-city-main-facilities/1"})
    with urlopen(request, timeout=240) as response:
        return read_limited_response(response, 16 * 1024 * 1024, "Commons file metadata")


def _common_title(value: str) -> str:
    return value if value.startswith("File:") else f"File:{value}"


def _osm_commons_tags(root: Path) -> list[str]:
    osm_mirror = root / "site/mirrors/osm.json"
    if not osm_mirror.exists():
        return []
    tags = []
    for element in _read_json(osm_mirror).get("elements", []):
        tag = (element.get("tags") or {}).get("wikimedia_commons")
        if isinstance(tag, str):
            tags.append(tag)
    return tags


def collect_categories(root: str | Path) -> list[str]:
    return sorted({tag for tag in _osm_commons_tags(Path(root)) if tag.startswith("Category:")})


def collect_file_names(root: str | Path) -> list[str]:
    """The committed mirrors already hold the association-scoped elements and entities."""
    root = Path(root)
    names: set[str] = set()
    for tag in _osm_commons_tags(root):
        if tag.startswith("File:"):
            names.add(tag)
    wikidata_mirror = root / "site/mirrors/wikidata.json"
    if wikidata_mirror.exists():
        for entity in _read_json(wikidata_mirror).get("entities", {}).values():
            for claim in (entity.get("claims") or {}).get("P18", []):
                value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
                if isinstance(value, str) and value:
                    names.add(_common_title(value))
    places_path = root / "data/places.jsonld"
    if places_path.exists():
        for place in _read_json(places_path).get("@graph", []):
            image = place.get("schema:image") if isinstance(place, dict) else None
            if not isinstance(image, dict) or set(image) != {"@id"} or not isinstance(image.get("@id"), str):
                continue
            try:
                names.add(commons_file_title(image["@id"]))
            except ValueError:
                continue
    return sorted(names)


def _metadata_text(extmetadata: dict[str, Any], key: str) -> str | None:
    value = extmetadata.get(key, {}).get("value") if isinstance(extmetadata.get(key), dict) else None
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


class _VisibleText(HTMLParser):
    _VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._hidden = [False]
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self._VOID:
            self._hidden.append(self._hidden[-1] or _hidden_element(attrs))

    def handle_endtag(self, tag: str) -> None:
        if tag not in self._VOID and len(self._hidden) > 1:
            self._hidden.pop()

    def handle_data(self, data: str) -> None:
        if not self._hidden[-1]:
            self._parts.append(data)

    def text(self) -> str:
        return re.sub(r"\s+", " ", "".join(self._parts)).strip()


def _hidden_element(attrs: list[tuple[str, str | None]]) -> bool:
    return any(name == "hidden" or (name == "style" and value is not None and re.search(r"display\s*:\s*none", value, re.IGNORECASE)) for name, value in attrs)


def _artist_text(extmetadata: dict[str, Any]) -> str | None:
    value = _metadata_text(extmetadata, "Artist")
    if value is None:
        return None
    parser = _VisibleText()
    parser.feed(value)
    parser.close()
    text = parser.text()
    if not text or _UNKNOWN_ARTIST.match(text):
        return None
    return text


def _content_url(info: dict[str, Any]) -> str | None:
    value = info.get("url")
    if not isinstance(value, str) or not value.startswith("https://"):
        return None
    # Commons API appends utm tracking parameters to imageinfo urls.
    return value.split("?", 1)[0] or None


def _query_files(titles: list[str], fetch) -> dict[str, dict[str, Any]]:
    url = f"{COMMONS_API}?{urlencode({'action': 'query', 'titles': '|'.join(titles), 'prop': 'imageinfo', 'iiprop': 'url|extmetadata', 'iiextmetadatafilter': EXTMETADATA, 'format': 'json'})}"
    query = (json.loads(fetch(url)).get("query") or {})
    files: dict[str, dict[str, Any]] = {}
    for page in (query.get("pages") or {}).values():
        if not isinstance(page, dict) or "missing" in page:
            continue
        title = page.get("title")
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


def _plain_title(title: str) -> str:
    return title.split(":", 1)[-1]


def _title_words(title: str) -> set[str]:
    return set(_WORDS.findall(_plain_title(title).lower()))


def _origin_titles(query: dict[str, Any]) -> dict[str, str]:
    """Map a response title back to the requested title through normalization and redirects."""
    origin: dict[str, str] = {}
    for item in query.get("normalized", []):
        if isinstance(item, dict) and isinstance(item.get("from"), str) and isinstance(item.get("to"), str):
            origin[item["to"]] = item["from"]
    for item in query.get("redirects", []):
        if isinstance(item, dict) and isinstance(item.get("from"), str) and isinstance(item.get("to"), str):
            origin[item["to"]] = origin.get(item["from"], item["from"])
    return origin


def _query_page_images(categories: list[str], fetch) -> dict[str, str]:
    url = f"{COMMONS_API}?{urlencode({'action': 'query', 'titles': '|'.join(categories), 'prop': 'pageimages', 'piprop': 'name', 'redirects': '1', 'format': 'json'})}"
    query = (json.loads(fetch(url)).get("query") or {})
    origin = _origin_titles(query)
    images: dict[str, str] = {}
    for page in (query.get("pages") or {}).values():
        if not isinstance(page, dict) or "missing" in page:
            continue
        title = origin.get(page.get("title"), page.get("title"))
        name = page.get("pageimage")
        if isinstance(title, str) and isinstance(name, str) and name:
            images[title] = _common_title(name)
    return images


def _query_category_members(category: str, fetch) -> list[str]:
    url = f"{COMMONS_API}?{urlencode({'action': 'query', 'list': 'categorymembers', 'cmtitle': category, 'cmtype': 'file', 'cmlimit': PAGE_SIZE, 'cmprop': 'title|sortkey', 'format': 'json'})}"
    members = (json.loads(fetch(url)).get("query") or {}).get("categorymembers") or []
    return [member["title"] for member in members if isinstance(member, dict) and isinstance(member.get("title"), str) and member["title"]]


def _select_member(category: str, titles: list[str]) -> str | None:
    if not titles:
        return None
    wanted = _title_words(category)
    scored = [(len(wanted & _title_words(title)), title) for title in titles]
    best = max(score for score, _ in scored)
    if best == 0:
        return titles[0]
    return min((title for score, title in scored if score == best), key=lambda title: (len(title), title))


def resolve_categories(categories: list[str], fetch) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for start in range(0, len(categories), PAGE_SIZE):
        resolved.update(_query_page_images(categories[start:start + PAGE_SIZE], fetch))
    for category in categories:
        if category in resolved:
            continue
        selected = _select_member(category, _query_category_members(category, fetch))
        if selected:
            resolved[category] = selected
    return {category: resolved[category] for category in categories if category in resolved}


def run_commons_retrieval(root: str | Path, at: str, fetch=_get) -> Path:
    root = Path(root)
    categories = resolve_categories(collect_categories(root), fetch)
    names = sorted(set(collect_file_names(root)) | set(categories.values()))
    files: dict[str, dict[str, Any]] = {}
    pages = 0
    for start in range(0, len(names), PAGE_SIZE):
        chunk = names[start:start + PAGE_SIZE]
        files.update(_query_files(chunk, fetch))
        pages += 1
    document = {"sourceId": "commons", "retrievedAt": at, "files": files, "categories": categories}
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
