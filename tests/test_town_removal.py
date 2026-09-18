import unittest
from pathlib import Path


LEGACY_TOWN_PATHS = (
    "src/retrieve_towns.py",
    ".github/workflows/update-towns.yml",
    "data/pinned/towns.geojson",
    "data/pinned/towns.retrieval.json",
    "tests/test_town_retrieval.py",
)

TOWN_SOURCE_TOKENS = {
    "src/fac_cli.py": ("_towns_by_id", "--town"),
    "src/facility_data.py": (
        "_town_for_point",
        "data/pinned/towns.geojson",
        "chiyoda-city-town-geojson",
    ),
}


class TownRemovalTests(unittest.TestCase):
    def test_legacy_town_paths_are_absent(self):
        root = Path(__file__).resolve().parents[1]
        for relative_path in LEGACY_TOWN_PATHS:
            with self.subTest(path=relative_path):
                self.assertFalse(
                    (root / relative_path).exists(),
                    f"legacy town path remains: {relative_path}",
                )

    def test_town_derived_production_entry_points_are_absent(self):
        root = Path(__file__).resolve().parents[1]
        for relative_path, forbidden_tokens in TOWN_SOURCE_TOKENS.items():
            source = (root / relative_path).read_text(encoding="utf-8")
            for token in forbidden_tokens:
                with self.subTest(path=relative_path, token=token):
                    self.assertFalse(
                        token in source,
                        f"legacy town entry point remains: {relative_path}: {token}",
                    )


if __name__ == "__main__":
    unittest.main()
