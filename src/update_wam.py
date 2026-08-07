from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.facility_data import normalize_wam_rows, source_refresh_due


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize one version-pinned WAM snapshot")
    parser.add_argument("raw")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--at", required=True)
    args = parser.parse_args(argv)
    root = Path(args.root)
    metadata_path = root / "imports/wam/retrieval.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    source_refresh_due(None, args.at)
    raw = json.loads(Path(args.raw).read_text(encoding="utf-8"))
    if not isinstance(raw.get("version"), str) or not raw["version"].strip():
        print("ERROR: WAM raw snapshot requires a version")
        return 1
    if not isinstance(raw.get("rows"), list):
        print("ERROR: WAM raw snapshot requires a rows array")
        return 1
    records = normalize_wam_rows(raw["rows"])
    normalized_path = root / "imports/wam/normalized.json"
    normalized_path.write_text(
        json.dumps({"records": records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    metadata["retrievedAt"] = args.at
    metadata["rawVersion"] = raw.get("version")
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(normalized_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
