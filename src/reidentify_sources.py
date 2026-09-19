"""Re-identify search inputs using retained, verified source snapshots."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from src.retrieve_osm import prepare_osm_snapshot
from src.retrieve_wam import prepare_wam_release


def _payload(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _verified_snapshot(root: Path, source: str) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_path, retrieval_path = root / f"imports/{source}/raw.json", root / f"imports/{source}/retrieval.json"
    raw_payload = raw_path.read_bytes()
    retrieval = json.loads(retrieval_path.read_text(encoding="utf-8"))
    label = "OpenStreetMap" if source == "openstreetmap" else "WAM"
    if hashlib.sha256(raw_payload).hexdigest() != retrieval.get("rawSha256"):
        raise ValueError(f"{label} rawSha256 does not match retained raw bytes")
    raw = json.loads(raw_payload)
    if raw.get("version") != retrieval.get("rawVersion") or not isinstance(retrieval.get("retrievedAt"), str):
        raise ValueError(f"{label} retrieval metadata is invalid")
    return raw, retrieval


def _write(root: Path, relative: str, document: dict[str, Any]) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    try:
        temporary.write_bytes(_payload(document)); temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def prepare_retained_reidentification(root: str | Path) -> dict[str, str]:
    """Regenerate normalized candidates from canonical JSON-LD and retained raws."""
    root = Path(root)
    wam_raw, wam_retrieval = _verified_snapshot(root, "wam")
    osm_raw, osm_retrieval = _verified_snapshot(root, "openstreetmap")
    canonical = json.loads((root / "data/places.jsonld").read_text(encoding="utf-8"))
    searches = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((root / "inputs/osm-search").rglob("*.json"))]
    wam_search, wam_normalized = prepare_wam_release(wam_raw.get("rows", []), searches, str(wam_raw["version"]), str(wam_retrieval["retrievedAt"]))
    del wam_search
    osm_normalized, osm_report = prepare_osm_snapshot(canonical, searches, osm_raw)
    osm_report["rawSha256"] = osm_retrieval["rawSha256"]
    _write(root, "imports/wam/normalized.json", wam_normalized)
    _write(root, "imports/openstreetmap/normalized.json", osm_normalized)
    _write(root, "reports/osm-candidates.json", osm_report)
    return {"wamRetrievedAt": str(wam_retrieval["retrievedAt"]), "osmRetrievedAt": str(osm_retrieval["retrievedAt"])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Re-identify search inputs from retained source snapshots")
    parser.add_argument("root", nargs="?", default="."); parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        result = prepare_retained_reidentification(args.root)
        text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output: Path(args.output).write_text(text, encoding="utf-8")
        else: print(text, end="")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}"); return 1
    return 0

if __name__ == "__main__": raise SystemExit(main())
