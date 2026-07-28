import json
import tempfile
import unittest
from pathlib import Path

from src.facility_data import (
    build_public_geojson,
    choose_geometry,
    make_place,
    main,
    validate_repository,
    validate_registry,
    validate_search_document,
)


class SearchInputTests(unittest.TestCase):
    def test_accepts_uuid_name_and_exactly_one_search_key(self):
        document = {
            "source": {"kind": "human", "sourceId": None, "retrievedAt": None},
            "queries": [
                {
                    "id": "019c0000-0000-7000-8000-000000000001",
                    "name": "北の丸公園",
                    "qid": "Q1075966",
                },
                {
                    "id": "019c0000-0000-7000-8000-000000000002",
                    "name": "施設A",
                    "coordinates": [139.75, 35.69],
                },
            ],
        }

        self.assertEqual([], validate_search_document(document))

    def test_rejects_malformed_search_rows(self):
        duplicate_id = "019c0000-0000-7000-8000-000000000001"
        document = {
            "source": {"kind": "human", "sourceId": None, "retrievedAt": None},
            "queries": [
                {"id": duplicate_id, "name": "施設A", "coordinates": [139.75, 35.69]},
                {"id": duplicate_id, "name": "施設B", "qid": "Q1"},
                {
                    "id": "not-a-uuid",
                    "name": "施設C",
                    "qid": "Q0",
                    "coordinates": [200, 100],
                },
            ],
        }

        issues = validate_search_document(document)

        self.assertIn(f"queries[1]: duplicate id: {duplicate_id}", issues)
        self.assertIn("queries[2]: id must be UUIDv7", issues)
        self.assertIn(
            "queries[2]: exactly one of coordinates or qid is required", issues
        )

    def test_rejects_invalid_names_qids_coordinates_and_extra_fields(self):
        document = {
            "queries": [
                {
                    "id": "019c0000-0000-7000-8000-000000000003",
                    "name": " ",
                    "qid": "Q0",
                    "name:en": "Facility",
                },
                {
                    "id": "019c0000-0000-7000-8000-000000000004",
                    "name": "施設D",
                    "coordinates": [181, True],
                },
            ]
        }

        issues = validate_search_document(document)

        self.assertIn("queries[0]: name must be a non-empty string", issues)
        self.assertIn("queries[0]: invalid qid: Q0", issues)
        self.assertIn("queries[0]: unexpected fields: name:en", issues)
        self.assertIn(
            "queries[1]: coordinates must be [longitude, latitude]", issues
        )


class GeometrySelectionTests(unittest.TestCase):
    def test_uses_wam_then_osm_then_search_coordinates(self):
        query = {
            "id": "019c0000-0000-7000-8000-000000000005",
            "name": "施設E",
            "coordinates": [139.70, 35.60],
        }
        wam = {"id": "wam-1", "coordinates": [139.71, 35.61]}
        osm = {"type": "node", "id": "123", "coordinates": [139.72, 35.62]}

        with self.subTest("WAM wins"):
            self.assertEqual(
                ([139.71, 35.61], "wam", "wam-1"),
                choose_geometry(query, wam_record=wam, osm_record=osm),
            )
        with self.subTest("OSM is second"):
            self.assertEqual(
                ([139.72, 35.62], "openstreetmap", "node/123"),
                choose_geometry(query, wam_record=None, osm_record=osm),
            )
        with self.subTest("search input is fallback"):
            self.assertEqual(
                ([139.70, 35.60], "search-input", query["id"]),
                choose_geometry(query, wam_record=None, osm_record=None),
            )

    def test_place_keeps_search_uuid_and_name(self):
        query = {
            "id": "019c0000-0000-7000-8000-000000000005",
            "name": "施設E",
            "coordinates": [139.70, 35.60],
        }

        place = make_place(
            query,
            category_ids=["public-office"],
            tags=["kazaguruma.home-shortcut"],
            at="2026-07-28T00:00:00Z",
        )

        self.assertEqual(query["id"], place["id"])
        self.assertEqual(query["name"], place["name"])
        self.assertNotIn("names", place)
        self.assertEqual("search-input", place["geometrySource"]["sourceId"])
        self.assertEqual("active", place["lifecycle"]["status"])


class RegistryValidationTests(unittest.TestCase):
    def test_rejects_duplicate_ids_name_drift_and_non_point_geometry(self):
        query = {
            "id": "019c0000-0000-7000-8000-000000000006",
            "name": "検索入力名",
            "coordinates": [139.70, 35.60],
        }
        place = make_place(query, ["park"], [], "2026-07-28T00:00:00Z")
        invalid = dict(place, name="別名", geometry={"type": "Polygon", "coordinates": []})
        registry = {"schemaVersion": 1, "places": [invalid, dict(invalid)]}

        issues = validate_registry(registry, {query["id"]: query})

        self.assertIn(f"duplicate place id: {query['id']}", issues)
        self.assertIn(f"place {query['id']}: name differs from search input", issues)
        self.assertIn(f"place {query['id']}: geometry must be Point", issues)


class PublicGeoJsonTests(unittest.TestCase):
    def test_emits_only_public_point_and_display_properties(self):
        query = {
            "id": "019c0000-0000-7000-8000-000000000007",
            "name": "施設F",
            "coordinates": [139.75, 35.69],
        }
        place = make_place(query, ["park"], ["featured"], "2026-07-28T00:00:00Z")
        place["externalRefs"] = [
            {
                "sourceId": "openstreetmap",
                "recordId": "relation/1",
                "status": "superseded",
            }
        ]
        towns = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "北の丸公園"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[139.7, 35.6], [139.8, 35.6], [139.8, 35.7], [139.7, 35.7], [139.7, 35.6]]
                        ],
                    },
                }
            ],
        }

        public = build_public_geojson(
            {"schemaVersion": 1, "places": [place]},
            source_attributions=[{"sourceId": "openstreetmap", "license": "ODbL-1.0"}],
            towns=towns,
        )

        self.assertEqual("Point", public["features"][0]["geometry"]["type"])
        self.assertEqual(
            {"id", "name", "categoryIds", "tags", "town"},
            set(public["features"][0]["properties"]),
        )
        self.assertEqual("北の丸公園", public["features"][0]["properties"]["town"])
        rendered = str(public)
        self.assertNotIn("externalRefs", rendered)
        self.assertNotIn("audit", rendered)
        self.assertNotIn("Polygon", rendered)


class PhaseZeroFilesTests(unittest.TestCase):
    def test_schema_and_fixture_files_define_the_new_contract(self):
        root = Path(__file__).resolve().parents[1]
        search_schema = json.loads(
            (root / "schema/search-input.schema.json").read_text(encoding="utf-8")
        )
        registry_schema = json.loads(
            (root / "schema/registry.schema.json").read_text(encoding="utf-8")
        )
        search_fixture = json.loads(
            (root / "tests/fixtures/search-input.json").read_text(encoding="utf-8")
        )
        registry_fixture = json.loads(
            (root / "tests/fixtures/registry.json").read_text(encoding="utf-8")
        )

        self.assertEqual(["id", "name"], search_schema["$defs"]["query"]["required"][:2])
        self.assertEqual("Point", registry_schema["$defs"]["place"]["properties"]["geometry"]["properties"]["type"]["const"])
        self.assertEqual([], validate_search_document(search_fixture))
        search_by_id = {item["id"]: item for item in search_fixture["queries"]}
        self.assertEqual([], validate_registry(registry_fixture, search_by_id))

    def test_repository_cli_validates_and_builds_public_geojson(self):
        repository = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "inputs/osm-search/human").mkdir(parents=True)
            (root / "data").mkdir()
            (root / "config").mkdir()
            (root / "inputs/osm-search/human/base.json").write_text(
                (repository / "tests/fixtures/search-input.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "data/registry.json").write_text(
                (repository / "tests/fixtures/registry.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "config/sources.json").write_text(
                json.dumps({"sources": [{"id": "openstreetmap", "license": "ODbL-1.0"}]}),
                encoding="utf-8",
            )

            self.assertEqual([], validate_repository(root))
            self.assertEqual(0, main(["build", str(root)]))
            public = json.loads(
                (root / "dist/public/places.geojson").read_text(encoding="utf-8")
            )

        self.assertEqual("Point", public["features"][0]["geometry"]["type"])


if __name__ == "__main__":
    unittest.main()
