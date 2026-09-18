import json
import unittest
from pathlib import Path

import src.facility_data as facility_data


ROOT = Path(__file__).resolve().parents[1]


class JsonLdRepositoryArtifactTests(unittest.TestCase):
    def test_canonical_jsonld_is_valid_and_contains_92_public_places(self):
        path = ROOT / "data/places.jsonld"
        self.assertTrue(path.is_file(), f"missing canonical JSON-LD artifact: {path}")

        document = json.loads(path.read_text(encoding="utf-8"))
        facility_data.validate_jsonld_document(document)

        graph = document["@graph"]
        public_places = [
            record
            for record in graph
            if "schema:Place" in record.get("@type", [])
        ]
        self.assertEqual(92, len(public_places))

        place_ids = [record["@id"] for record in public_places]
        self.assertTrue(all(place_id.startswith("urn:uuid:") for place_id in place_ids))
        self.assertEqual(len(place_ids), len(set(place_ids)))

    def test_legacy_repository_artifacts_are_removed(self):
        legacy_paths = (
            ROOT / "data/registry.json",
            ROOT / "dist/public/places.geojson",
            ROOT / "dist/public/manifest.json",
        )
        present_paths = [str(path.relative_to(ROOT)) for path in legacy_paths if path.exists()]

        self.assertEqual([], present_paths, "legacy artifacts must be removed")


if __name__ == "__main__":
    unittest.main()
