#!/usr/bin/env python3
"""Prepare a byte-preserving versioned JSON-LD release snapshot."""

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

from src.facility_data import validate_jsonld_document


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare a byte-preserving JSON-LD release snapshot."
    )
    parser.add_argument("--input", required=True, help="canonical JSON-LD input path")
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

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_path = output_dir / f"places-{args.version}.jsonld"

    try:
        source_bytes = input_path.read_bytes()
        document = json.loads(source_bytes)
        validate_jsonld_document(document)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(source_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"ERROR: unable to prepare release snapshot: {error}", file=sys.stderr)
        return 1

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
