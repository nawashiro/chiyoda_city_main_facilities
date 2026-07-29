from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from src.facility_data import source_refresh_due
from src.http_utils import read_limited_response


_REPOSITORY = "nawashiro/chiyoda_city_town_geojson"
_SOURCE_PATH = "chiyoda_city.json"
_COMMIT = re.compile(r"[0-9a-f]{40}")
MAX_TOWN_BYTES = 8 * 1024 * 1024


def _validate_ring(ring: Any) -> None:
    if not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]:
        raise ValueError("town polygon ring must be closed and contain at least four points")
    for point in ring:
        if (
            not isinstance(point, list)
            or len(point) != 2
            or isinstance(point[0], bool)
            or isinstance(point[1], bool)
            or not isinstance(point[0], (int, float))
            or not isinstance(point[1], (int, float))
            or not math.isfinite(point[0])
            or not math.isfinite(point[1])
            or not -180 <= point[0] <= 180
            or not -90 <= point[1] <= 90
        ):
            raise ValueError("town polygon contains invalid coordinates")
    vertices = ring[:-1]
    if len({tuple(point) for point in vertices}) < 3:
        raise ValueError("town polygon ring must contain at least three distinct vertices")
    origin_x, origin_y = vertices[0]
    shifted = [[point[0] - origin_x, point[1] - origin_y] for point in vertices]
    doubled_area = sum(
        first[0] * second[1] - second[0] * first[1]
        for first, second in zip(shifted, shifted[1:] + shifted[:1])
    )
    if math.isclose(doubled_area, 0.0, abs_tol=1e-15):
        raise ValueError("town polygon ring must have non-zero area")


def _validate_polygon(polygon: Any) -> None:
    if not isinstance(polygon, list) or not polygon:
        raise ValueError("town polygon must contain at least one ring")
    for ring in polygon:
        _validate_ring(ring)


def validate_town_geojson(document: dict[str, Any]) -> None:
    if document.get("type") != "FeatureCollection" or not isinstance(
        document.get("features"), list
    ) or not document["features"]:
        raise ValueError("town source must be a non-empty FeatureCollection")
    names = set()
    for index, feature in enumerate(document["features"]):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError(f"invalid town feature at index {index}")
        name = feature.get("properties", {}).get("name")
        if not isinstance(name, str) or not name.startswith("東京都千代田区"):
            raise ValueError(f"invalid town name at index {index}")
        if name in names:
            raise ValueError(f"duplicate town name: {name}")
        names.add(name)
        geometry = feature.get("geometry", {})
        if geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            raise ValueError(f"invalid town geometry at index {index}")
        if not isinstance(geometry.get("coordinates"), list) or not geometry["coordinates"]:
            raise ValueError(f"empty town geometry at index {index}")
        if geometry["type"] == "Polygon":
            _validate_polygon(geometry["coordinates"])
        else:
            for polygon in geometry["coordinates"]:
                _validate_polygon(polygon)


def run_town_retrieval(
    root: str | Path,
    commit: str,
    at: str,
    fetcher,
) -> tuple[Path, Path]:
    if _COMMIT.fullmatch(commit) is None:
        raise ValueError("town source commit must be a full 40-character SHA")
    root = Path(root)
    metadata_path = root / "data/pinned/towns.retrieval.json"
    if metadata_path.exists():
        previous = json.loads(metadata_path.read_text(encoding="utf-8")).get("retrievedAt")
        if not source_refresh_due(previous, at):
            raise ValueError("town source was retrieved less than 30 days ago")
    else:
        source_refresh_due(None, at)
    url = f"https://raw.githubusercontent.com/{_REPOSITORY}/{commit}/{_SOURCE_PATH}"
    payload, headers = fetcher(url)
    if not isinstance(payload, bytes) or not payload:
        raise ValueError("empty town GeoJSON response")
    if len(payload) > MAX_TOWN_BYTES:
        raise ValueError("town GeoJSON response is too large")
    document = json.loads(payload)
    validate_town_geojson(document)
    metadata = {
        "sourceId": "chiyoda-city-town-geojson",
        "repository": f"https://github.com/{_REPOSITORY}",
        "commit": commit,
        "path": _SOURCE_PATH,
        "retrievedAt": at,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "etag": headers.get("ETag"),
        "lastModified": headers.get("Last-Modified"),
        "featureCount": len(document["features"]),
        "license": "CC BY-SA 4.0",
        "attribution": "© Linked Open Addresses Japan",
    }
    pinned_path = root / "data/pinned/towns.geojson"
    pinned_path.parent.mkdir(parents=True, exist_ok=True)
    pinned_path.write_bytes(payload)
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return pinned_path, metadata_path


def _http_fetch(url: str) -> tuple[bytes, dict[str, str | None]]:
    request = Request(url, headers={"User-Agent": "chiyoda-city-main-facilities/1"})
    with urlopen(request, timeout=120) as response:
        return read_limited_response(response, MAX_TOWN_BYTES, "town GeoJSON"), {
            "ETag": response.headers.get("ETag"),
            "Last-Modified": response.headers.get("Last-Modified"),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retrieve a commit-pinned Chiyoda town GeoJSON")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--commit", required=True)
    parser.add_argument("--at", required=True)
    args = parser.parse_args(argv)
    try:
        pinned_path, metadata_path = run_town_retrieval(
            args.root, args.commit, args.at, _http_fetch
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}")
        return 1
    print(pinned_path)
    print(metadata_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
