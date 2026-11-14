#!/usr/bin/env python3
"""Prepare versioned release assets from a built site directory."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


_RELEASE_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from src.facility_data import validate_published_document


_ASSETS = (
    ("places.jsonld", "places-{}.jsonld"),
    ("mirrors/osm.json", "osm-{}.json"),
    ("mirrors/wikidata.json", "wikidata-{}.json"),
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare versioned release assets from a built site directory."
    )
    parser.add_argument("--site-dir", required=True, help="built site directory")
    parser.add_argument("--output-dir", required=True, help="release output directory")
    parser.add_argument("--version", required=True, help="release version token")
    return parser


def _validate_version(parser: argparse.ArgumentParser, version: str) -> None:
    if _RELEASE_VERSION.fullmatch(version) is None:
        parser.error(
            "invalid release version: expected "
            "[A-Za-z0-9][A-Za-z0-9._-]*"
        )


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    _validate_version(parser, args.version)

    site_dir = Path(args.site_dir)
    output_dir = Path(args.output_dir)

    try:
        payloads = [(template, (site_dir / source).read_bytes()) for source, template in _ASSETS]
        validate_published_document(json.loads(payloads[0][1]))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"ERROR: unable to prepare release assets: {error}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    for template, payload in payloads:
        output_path = output_dir / template.format(args.version)
        output_path.write_bytes(payload)
        print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
