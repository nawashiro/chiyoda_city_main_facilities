"""Repository data validation helpers."""

import argparse
import json
from collections import Counter
from pathlib import Path


REQUIRED_LOCATION_FIELDS = (
    "id",
    "name",
    "lat",
    "lng",
    "nodeCopyright",
    "licence",
    "licenceUri",
)


def _allowed_values(allowed_duplicates, key):
    return {
        item["value"]
        for item in allowed_duplicates.get(key, [])
        if item.get("value") and item.get("reason")
    }


def validate_key_locations(dataset, allowed_duplicates):
    """Return human-readable validation issues for key_locations data."""
    locations = [
        (category.get("category", "<missing category>"), location)
        for category in dataset
        for location in category.get("locations", [])
    ]
    ids = [location.get("id") for _, location in locations if location.get("id")]
    allowed_ids = _allowed_values(allowed_duplicates, "id")
    issues = [
        f"duplicate id: {location_id}"
        for location_id, count in Counter(ids).items()
        if count > 1 and location_id not in allowed_ids
    ]
    source_ids = [
        str(location.get("nodeSourceId"))
        for _, location in locations
        if location.get("nodeSourceId") not in (None, "")
    ]
    allowed_source_ids = _allowed_values(allowed_duplicates, "nodeSourceId")
    issues.extend(
        f"duplicate nodeSourceId: {source_id}"
        for source_id, count in Counter(source_ids).items()
        if count > 1 and source_id not in allowed_source_ids
    )
    for category_name, location in locations:
        display_name = location.get("name", "<missing name>")
        prefix = f"{category_name}/{display_name}"
        for field in REQUIRED_LOCATION_FIELDS:
            if field not in location or location[field] in (None, ""):
                issues.append(f"{prefix}: missing required field: {field}")

        latitude = location.get("lat")
        longitude = location.get("lng")
        if latitude is not None:
            if not isinstance(latitude, (int, float)) or isinstance(latitude, bool):
                issues.append(f"{prefix}: latitude must be a number")
            elif not -90 <= latitude <= 90:
                issues.append(f"{prefix}: latitude out of range: {latitude}")
        if longitude is not None:
            if not isinstance(longitude, (int, float)) or isinstance(longitude, bool):
                issues.append(f"{prefix}: longitude must be a number")
            elif not -180 <= longitude <= 180:
                issues.append(f"{prefix}: longitude out of range: {longitude}")
    return issues


def validate_sources(document):
    """Return validation issues for the source and license registry."""
    required_fields = ("id", "title", "url", "license", "license_url")
    issues = []
    for source in document.get("sources", []):
        source_id = source.get("id", "<missing id>")
        for field in required_fields:
            if source.get(field) in (None, ""):
                issues.append(f"source {source_id}: missing required field: {field}")
    return issues


def validate_repository(root):
    """Validate the repository's canonical data and configuration files."""
    root = Path(root)
    dataset = json.loads((root / "json/key_locations.json").read_text(encoding="utf-8"))
    exceptions = json.loads(
        (root / "config/validation_exceptions.json").read_text(encoding="utf-8")
    )
    sources = json.loads((root / "config/sources.json").read_text(encoding="utf-8"))
    return validate_key_locations(dataset, exceptions) + validate_sources(sources)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate repository data")
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    issues = validate_repository(args.root)
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        return 1
    print("Validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
