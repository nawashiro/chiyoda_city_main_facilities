"""One update path for monthly retrieval and confirmed Issue decisions."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from src.facility_data import _read_json, _write_json, load_queries, validate_repository
from src.github_osm_review import GitHub, apply_confirmations, close_published, read_confirmations
from src.resolve_osm_candidates import apply_decisions, current_id, resolve
from src.retrieve_osm import _http_get, run_osm_retrieval


def verified_snapshot(root):
    directory = root / "imports/openstreetmap"
    payload = (directory / "raw.json").read_bytes()
    metadata = _read_json(directory / "retrieval.json")
    if hashlib.sha256(payload).hexdigest() != metadata.get("rawSha256"):
        raise ValueError("OSM rawSha256 does not match retained raw bytes")
    raw = json.loads(payload)
    if raw.get("version") != metadata.get("rawVersion"):
        raise ValueError("OSM raw version differs from retrieval metadata")
    return raw


def update(root, *, refresh=False, github=None, judge=None, retrieve=run_osm_retrieval):
    root = Path(root)
    issues = validate_repository(root)
    if issues:
        raise ValueError("; ".join(issues))
    queries = load_queries(root)
    document = _read_json(root / "data/places.jsonld")
    ledger = _read_json(root / "data/osm-decisions.json")
    if ledger.get("version") != 1 or not isinstance(ledger.get("facilities"), dict):
        raise ValueError("invalid OSM decision ledger")
    ledger = copy.deepcopy(ledger)
    confirmations = read_confirmations(ledger, github) if github else {}
    existing = {p["@id"].removeprefix("urn:uuid:"): current_id(p) for p in document["@graph"]}
    while confirmations:
        allocations = {}
        for place in document["@graph"]:
            identifier = place["@id"].removeprefix("urn:uuid:")
            choice = confirmations.get(identifier, {}).get("choice", current_id(place))
            if choice and choice != "none":
                allocations.setdefault(choice, set()).add(identifier)
        for identifier, confirmation in confirmations.items():
            if confirmation["choice"] != "none":
                allocations.setdefault(confirmation["choice"], set()).add(identifier)
        conflicts = {i for i, c in confirmations.items() if c["choice"] != "none" and len(allocations[c["choice"]]) > 1 and existing.get(i) != c["choice"]}
        if not conflicts:
            break
        for identifier in conflicts:
            github.corrective_comment(confirmations[identifier]["issue"], "このOSM候補は別の施設にも割り当てられています。関連付けを確認し、候補か「該当なし」を選び直してください。")
            del confirmations[identifier]
    apply_confirmations(ledger, confirmations)
    if refresh:
        document = apply_decisions(document, queries, {k: ledger["facilities"][k] for k in confirmations})
        retrieve(root, datetime.now(timezone.utc).isoformat(timespec="seconds"), _http_get, canonical=document)
        raw = verified_snapshot(root)
        updated, ledger = resolve(document, queries, raw, ledger, **({"judge": judge} if judge else {}))
    else:
        updated = apply_decisions(document, queries, {k: ledger["facilities"][k] for k in confirmations})
    _write_json(root / "data/places.jsonld", updated)
    _write_json(root / "data/osm-decisions.json", ledger)
    return ledger


def present(root, github):
    ledger = _read_json(Path(root) / "data/osm-decisions.json")
    for query_id, entry in ledger["facilities"].items():
        if entry.get("status") == "needs_review":
            github.save_issue(query_id, entry)
    github.save_unmatched(ledger["facilities"])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Update OSM associations or apply confirmed Issues")
    parser.add_argument("command", choices=("refresh", "confirm", "present", "close-published"))
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--offline", action="store_true", help="Use the retained verified snapshot without GitHub")
    args = parser.parse_args(argv)
    root = Path(args.root)
    try:
        github = None if args.offline else GitHub()
        if args.command == "present":
            if not github:
                raise ValueError("present requires GitHub")
            present(root, github)
        elif args.command == "close-published":
            if not github:
                raise ValueError("close-published requires GitHub")
            close_published(_read_json(root / "data/osm-decisions.json"), github)
        else:
            kwargs = {"refresh": args.command == "refresh", "github": github}
            if args.offline:
                kwargs["retrieve"] = lambda *args, **kwargs: None
            update(root, **kwargs)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: {type(error).__name__}: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
