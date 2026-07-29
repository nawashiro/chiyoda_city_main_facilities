import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import src.retrieve_towns as retrieve_towns
from src.retrieve_towns import run_town_retrieval, validate_town_geojson


class TownRetrievalTests(unittest.TestCase):
    def test_manual_workflow_retrieves_builds_and_uploads_without_raw_path(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/update-towns.yml").read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch", workflow)
        self.assertIn("commit:", workflow)
        self.assertNotIn("raw_path", workflow)
        self.assertIn("src.retrieve_towns", workflow)
        self.assertIn("src.facility_data build", workflow)
        self.assertIn("src.facility_data validate", workflow)
        self.assertIn("actions/upload-artifact", workflow)
        self.assertIn("git add -N .", workflow)

    def test_retrieves_commit_pinned_geojson_and_records_hash(self):
        commit = "0be816edaa8d0f8d22714a2f1146f2d9e133e09f"
        document = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "東京都千代田区内幸町"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[139.75, 35.67], [139.76, 35.67], [139.76, 35.68], [139.75, 35.67]]
                        ],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {"name": "東京都千代田区丸の内"},
                    "geometry": {
                        "type": "MultiPolygon",
                        "coordinates": [
                            [[[139.76, 35.68], [139.77, 35.68], [139.77, 35.69], [139.76, 35.68]]]
                        ],
                    },
                },
            ],
        }
        payload = json.dumps(document, ensure_ascii=False).encode()
        calls = []

        def fetch(url):
            calls.append(url)
            return payload, {"ETag": '"town-fixture"'}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_town_retrieval(root, commit, "2026-07-29T00:00:00Z", fetch)
            pinned = json.loads((root / "data/pinned/towns.geojson").read_text(encoding="utf-8"))
            metadata = json.loads(
                (root / "data/pinned/towns.retrieval.json").read_text(encoding="utf-8")
            )

        self.assertEqual(1, len(calls))
        self.assertIn(commit, calls[0])
        self.assertEqual(2, len(pinned["features"]))
        self.assertEqual(commit, metadata["commit"])
        self.assertEqual(64, len(metadata["sha256"]))
        self.assertEqual('"town-fixture"', metadata["etag"])

    def test_rejects_non_polygon_or_missing_town_name(self):
        for feature in (
            {"type": "Feature", "properties": {"name": "東京都千代田区内幸町"}, "geometry": {"type": "Point", "coordinates": [139.75, 35.68]}},
            {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": []}},
        ):
            with self.assertRaises(ValueError):
                validate_town_geojson({"type": "FeatureCollection", "features": [feature]})

    def test_rejects_malformed_or_oversized_town_geometry(self):
        invalid_coordinates = (
            [[[139.75, 35.67], [139.76, 35.67], [139.75, 35.68]]],
            [[[139.75, 35.67], [float("nan"), 35.67], [139.75, 35.67], [139.75, 35.67]]],
            [[[200.0, 35.67], [139.76, 35.67], [139.75, 35.68], [200.0, 35.67]]],
            [[[139.75, 35.67], [139.75, 35.67], [139.75, 35.67], [139.75, 35.67]]],
            [[[139.75, 35.67], [139.76, 35.68], [139.77, 35.69], [139.75, 35.67]]],
        )
        for coordinates in invalid_coordinates:
            with self.assertRaises(ValueError):
                validate_town_geojson(
                    {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "properties": {"name": "東京都千代田区内幸町"},
                                "geometry": {"type": "Polygon", "coordinates": coordinates},
                            }
                        ],
                    }
                )
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(retrieve_towns, "MAX_TOWN_BYTES", 10):
                with self.assertRaisesRegex(ValueError, "too large"):
                    run_town_retrieval(
                        Path(directory),
                        "0be816edaa8d0f8d22714a2f1146f2d9e133e09f",
                        "2026-07-29T00:00:00Z",
                        lambda url: (b"x" * 11, {}),
                    )


if __name__ == "__main__":
    unittest.main()
