"""Local OpenStreetMap regional-mirror extraction."""

from __future__ import annotations

import math
import warnings
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any


def _distance_metres(first: tuple[float, float], second: tuple[float, float]) -> float:
    lon1, lat1 = map(math.radians, first)
    lon2, lat2 = map(math.radians, second)
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6_371_000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _center(bounds: tuple[float, float, float, float]) -> dict[str, float]:
    west, south, east, north = bounds
    return {"lon": (west + east) / 2, "lat": (south + north) / 2}


def _merge_bounds(bounds: Iterable[tuple[float, float, float, float]]) -> tuple[float, float, float, float] | None:
    items = list(bounds)
    if not items:
        return None
    return (min(x[0] for x in items), min(x[1] for x in items), max(x[2] for x in items), max(x[3] for x in items))


def relation_out_center(relation_id: str, members: Iterable[Mapping[str, object]], node_coordinates: Mapping[int, tuple[float, float]], way_bounds: Mapping[int, tuple[float, float, float, float]], warn: Callable[[str], None]) -> dict[str, float] | None:
    """Return an Overpass-compatible center from available direct members."""
    bounds = []
    for member in members:
        kind, ref = member.get("type"), member.get("ref")
        if kind == "r":
            continue
        if not isinstance(ref, int):
            raise ValueError(f"{relation_id} has an invalid member reference")
        if kind == "n":
            point = node_coordinates.get(ref)
            if point is None:
                warn(f"OSM regional mirror {relation_id} lacks member node/{ref}; center may be inaccurate")
                continue
            bounds.append((point[0], point[1], point[0], point[1]))
        elif kind == "w":
            bound = way_bounds.get(ref)
            if bound is None:
                warn(f"OSM regional mirror {relation_id} lacks member way/{ref}; center may be inaccurate")
                continue
            bounds.append(bound)
        else:
            raise ValueError(f"{relation_id} has an unsupported member type: {kind}")
    merged = _merge_bounds(bounds)
    return _center(merged) if merged else None


def extract_elements(pbf_path: Path, typed_ids: set[str], qids: set[str], coordinates: list[list[float]], chiyoda_bbox: tuple[float, float, float, float]) -> list[dict[str, Any]]:
    """Extract selected PBF elements with Overpass ``out center`` geometry."""
    try:
        import osmium
    except ImportError as error:  # pragma: no cover - exercised by workflow setup
        raise RuntimeError("local OSM mirror extraction requires osmium") from error

    selected_ids = {(item.split("/", 1)[0], int(item.split("/", 1)[1])) for item in typed_ids}
    target_points = [(float(point[0]), float(point[1])) for point in coordinates]
    south, west, north, east = chiyoda_bbox
    required_nodes: set[int] = set()
    required_ways: set[int] = set()

    class RelationDependencies(osmium.SimpleHandler):
        def relation(self, relation):
            for member in relation.members:
                if member.type == "n": required_nodes.add(member.ref)
                elif member.type == "w": required_ways.add(member.ref)

    RelationDependencies().apply_file(str(pbf_path))
    relation_nodes: dict[int, tuple[float, float]] = {}
    relation_ways: dict[int, tuple[float, float, float, float]] = {}
    selected: dict[tuple[str, int], dict[str, Any]] = {}

    def include(kind: str, identifier: int, tags: dict[str, str], center: dict[str, float]) -> bool:
        if (kind, identifier) in selected_ids:
            return True
        if tags.get("wikidata") in qids and south <= center["lat"] <= north and west <= center["lon"] <= east:
            return True
        return any(_distance_metres(point, (center["lon"], center["lat"])) <= 50 for point in target_points)

    class Geometry(osmium.SimpleHandler):
        def node(self, node):
            if not node.location.valid(): return
            lon, lat = float(node.location.lon), float(node.location.lat)
            if node.id in required_nodes: relation_nodes[node.id] = (lon, lat)
            tags = dict(node.tags)
            center = {"lon": lon, "lat": lat}
            if include("node", node.id, tags, center):
                selected[("node", node.id)] = {"type": "node", "id": node.id, "lon": lon, "lat": lat, "tags": tags}
        def way(self, way):
            points = []
            missing = []
            for ref in way.nodes:
                if ref.location.valid(): points.append((float(ref.location.lon), float(ref.location.lat)))
                else: missing.append(ref.ref)
            if missing:
                warnings.warn(f"OSM regional mirror way/{way.id} lacks node members; center omitted", RuntimeWarning)
                return
            bounds = _merge_bounds((lon, lat, lon, lat) for lon, lat in points)
            if bounds is None: return
            if way.id in required_ways: relation_ways[way.id] = bounds
            center = _center(bounds); tags = dict(way.tags)
            if include("way", way.id, tags, center):
                selected[("way", way.id)] = {"type": "way", "id": way.id, "center": center, "tags": tags}

    Geometry().apply_file(str(pbf_path), locations=True, idx="flex_mem")

    class Relations(osmium.SimpleHandler):
        def relation(self, relation):
            members = [{"type": member.type, "ref": member.ref} for member in relation.members]
            center = relation_out_center(f"relation/{relation.id}", members, relation_nodes, relation_ways, lambda message: warnings.warn(message, RuntimeWarning))
            if center is None: return
            tags = dict(relation.tags)
            if include("relation", relation.id, tags, center):
                selected[("relation", relation.id)] = {"type": "relation", "id": relation.id, "center": center, "tags": tags}

    Relations().apply_file(str(pbf_path))
    order = {"node": 0, "way": 1, "relation": 2}
    return [selected[key] for key in sorted(selected, key=lambda key: (order[key[0]], key[1]))]
