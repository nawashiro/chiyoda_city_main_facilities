import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from src.validate_data import (
    validate_key_locations,
    main,
    validate_repository,
    validate_sources,
)


class ValidateKeyLocationsTests(unittest.TestCase):
    def test_reports_duplicate_location_id(self):
        dataset = [
            {
                "category": "図書館",
                "locations": [
                    self.location("same-id", "施設A"),
                    self.location("same-id", "施設B"),
                ],
            }
        ]

        issues = validate_key_locations(dataset, allowed_duplicates={})

        self.assertIn("duplicate id: same-id", issues)

    def test_reports_missing_required_location_field(self):
        location = self.location("id-1", "施設A")
        del location["lat"]
        dataset = [{"category": "図書館", "locations": [location]}]

        issues = validate_key_locations(dataset, allowed_duplicates={})

        self.assertIn("図書館/施設A: missing required field: lat", issues)

    def test_reports_invalid_coordinates(self):
        location = self.location("id-1", "施設A")
        location["lat"] = 139.75
        location["lng"] = "35.69"
        dataset = [{"category": "図書館", "locations": [location]}]

        issues = validate_key_locations(dataset, allowed_duplicates={})

        self.assertIn("図書館/施設A: latitude out of range: 139.75", issues)
        self.assertIn("図書館/施設A: longitude must be a number", issues)

    def test_reports_duplicate_node_source_id(self):
        first = self.location("id-1", "施設A")
        second = self.location("id-2", "施設B")
        first["nodeSourceId"] = "179575985"
        second["nodeSourceId"] = "179575985"
        dataset = [{"category": "学校", "locations": [first, second]}]

        issues = validate_key_locations(dataset, allowed_duplicates={})

        self.assertIn("duplicate nodeSourceId: 179575985", issues)

    def test_legacy_validator_allows_declared_duplicate_values_for_diagnosis(self):
        first = self.location("same-id", "施設A")
        second = self.location("same-id", "施設B")
        first["nodeSourceId"] = "179575985"
        second["nodeSourceId"] = "179575985"
        dataset = [{"category": "学校", "locations": [first, second]}]
        allowed = {
            "id": [{"value": "same-id", "reason": "複合施設の既知重複"}],
            "nodeSourceId": [
                {"value": "179575985", "reason": "一つのOSM要素を共有"}
            ],
        }

        issues = validate_key_locations(dataset, allowed_duplicates=allowed)

        self.assertEqual([], issues)

    def test_validates_repository_files_together(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "json").mkdir()
            (root / "config").mkdir()
            dataset = [
                {
                    "category": "図書館",
                    "locations": [self.location("id-1", "施設A")],
                }
            ]
            (root / "json/key_locations.json").write_text(
                json.dumps(dataset), encoding="utf-8"
            )
            (root / "config/validation_exceptions.json").write_text(
                json.dumps({"id": [], "nodeSourceId": []}), encoding="utf-8"
            )
            (root / "config/sources.json").write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "id": "manual",
                                "title": "Manual curation",
                                "url": "https://example.com/source",
                                "license": "Example",
                                "license_url": "https://example.com/license",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            issues = validate_repository(root)

        self.assertEqual([], issues)

    def test_reports_incomplete_source_metadata(self):
        sources = {
            "sources": [
                {
                    "id": "osm",
                    "title": "OpenStreetMap",
                    "url": "https://www.openstreetmap.org/",
                }
            ]
        }

        issues = validate_sources(sources)

        self.assertIn("source osm: missing required field: license", issues)
        self.assertIn("source osm: missing required field: license_url", issues)

    def test_cli_returns_nonzero_when_validation_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "json").mkdir()
            (root / "config").mkdir()
            duplicate = self.location("same-id", "施設A")
            dataset = [
                {
                    "category": "図書館",
                    "locations": [duplicate, dict(duplicate, name="施設B")],
                }
            ]
            (root / "json/key_locations.json").write_text(
                json.dumps(dataset), encoding="utf-8"
            )
            (root / "config/validation_exceptions.json").write_text(
                json.dumps({"id": [], "nodeSourceId": []}), encoding="utf-8"
            )
            (root / "config/sources.json").write_text(
                json.dumps({"sources": []}), encoding="utf-8"
            )

            with redirect_stdout(StringIO()) as output:
                exit_code = main([str(root)])

        self.assertEqual(1, exit_code)
        self.assertIn("duplicate id: same-id", output.getvalue())

    def test_legacy_repository_passes_transitional_validation(self):
        repository_root = Path(__file__).resolve().parents[1]

        issues = validate_repository(repository_root)

        self.assertEqual([], issues)

    def test_phase_zero_documents_exist_and_plan_stays_in_scope(self):
        repository_root = Path(__file__).resolve().parents[1]
        required = [
            repository_root / "LICENSE",
            repository_root / "SOURCES_AND_LICENSES.md",
            repository_root / "doc/data_maintenance_spec.md",
            repository_root / "doc/maintenance_plan.md",
            repository_root / ".github/workflows/validate.yml",
        ]

        self.assertEqual([], [str(path) for path in required if not path.is_file()])
        documents = [
            (repository_root / "doc/maintenance_plan.md").read_text(
                encoding="utf-8"
            ),
            (repository_root / "doc/data_maintenance_spec.md").read_text(
                encoding="utf-8"
            ),
        ]
        for document in documents:
            for omitted_term in ("RDF", "JSON-LD"):
                self.assertNotIn(omitted_term, document)
            self.assertIn("月1回以下", document)
            self.assertIn("LLM", document)
            self.assertIn("3分の2", document)
            self.assertIn("最終判断を最後に置く", document)
            self.assertIn("記憶・資料・既有知識", document)
            self.assertIn("review_hold", document)
            self.assertIn("data/registry.json", document)
            self.assertIn("schema/search-input.schema.json", document)
            self.assertNotIn("dist/master/places.json", document)
            self.assertIn("後方互換を要件としない", document)
            self.assertIn("legacy_record", document)
            self.assertIn("UUIDv7", document)
            self.assertIn("重複UUID", document)
            self.assertIn("kazaguruma.home-shortcut", document)
            self.assertIn("dist/public/places.geojson", document)
            self.assertIn("クライアント実行時", document)
            self.assertIn("out_of_scope", document)
            self.assertIn("一般入院機能", document)
            self.assertNotIn("dist/kazaguruma/locations.json", document)
            self.assertNotIn("千代田区公式施設一覧", document)
            self.assertIn("nawashiro/chiyoda_city_town_geojson", document)
            self.assertIn("point-in-polygon", document)
            self.assertIn("ソース別名前空間", document)
            self.assertIn("sourceAttributions", document)
            self.assertIn("name + coordinates", document)
            self.assertIn("name + qid", document)
            self.assertIn("QID", document)
            self.assertIn("geometrySource", document)
            self.assertIn("superseded", document)
            self.assertIn("language_model", document)
            self.assertIn("calculation_model", document)
            self.assertIn("画像URL", document)
            self.assertIn("`images`", document)
            self.assertIn("長大", document)
            self.assertIn("OSM ID履歴", document)
            self.assertIn("OSMポリゴン", document)
            self.assertIn("町名ポリゴン", document)
            self.assertIn("Point", document)
            self.assertIn("50m", document)

    @staticmethod
    def location(location_id, name):
        return {
            "id": location_id,
            "name": name,
            "lat": 35.69,
            "lng": 139.75,
            "nodeCopyright": "example",
            "licence": "example",
            "licenceUri": "https://example.com/license",
        }


if __name__ == "__main__":
    unittest.main()
