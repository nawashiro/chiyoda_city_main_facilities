import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.facility_data import (
    build_public_geojson,
    choose_geometry,
    compact_audit,
    decide_consensus,
    match_osm_candidates,
    make_place,
    main,
    migrate_legacy,
    migrate_repository,
    new_uuid7,
    update_osm_reference,
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

    def test_rejects_long_audit_and_multiple_current_osm_refs(self):
        query = {
            "id": "019c0000-0000-7000-8000-000000000043",
            "name": "施設J",
            "coordinates": [139.70, 35.60],
        }
        place = make_place(query, ["park"], [], "2026-07-28T00:00:00Z")
        place["audit"] = [
            {
                "at": "2026-07-28T00:00:00Z",
                "method": "unknown",
                "action": "created",
                "target": "place",
                "reasoning": "must not persist",
            }
        ]
        place["externalRefs"] = [
            {"sourceId": "openstreetmap", "recordId": "node/1", "status": "current"},
            {"sourceId": "openstreetmap", "recordId": "way/2", "status": "current"},
        ]

        issues = validate_registry(
            {"schemaVersion": 1, "places": [place]}, {query["id"]: query}
        )

        self.assertIn(f"place {query['id']}: audit must have exactly four keys", issues)
        self.assertIn(f"place {query['id']}: invalid audit method: unknown", issues)
        self.assertIn(f"place {query['id']}: multiple current OSM refs", issues)


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
        public_schema = json.loads(
            (root / "schema/public-geojson.schema.json").read_text(encoding="utf-8")
        )
        search_fixture = json.loads(
            (root / "tests/fixtures/search-input.json").read_text(encoding="utf-8")
        )
        registry_fixture = json.loads(
            (root / "tests/fixtures/registry.json").read_text(encoding="utf-8")
        )

        self.assertEqual(["id", "name"], search_schema["$defs"]["query"]["required"][:2])
        self.assertEqual("Point", registry_schema["$defs"]["place"]["properties"]["geometry"]["properties"]["type"]["const"])
        self.assertEqual(
            ["id", "name", "categoryIds", "tags", "town"],
            public_schema["$defs"]["feature"]["properties"]["properties"]["required"],
        )
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
            geojson_path = root / "dist/public/places.geojson"
            first_bytes = geojson_path.read_bytes()
            public = json.loads(first_bytes)
            manifest = json.loads(
                (root / "dist/public/manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(0, main(["build", str(root)]))
            second_bytes = geojson_path.read_bytes()

        self.assertEqual("Point", public["features"][0]["geometry"]["type"])
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(hashlib.sha256(first_bytes).hexdigest(), manifest["sha256"])
        self.assertEqual("places.geojson", manifest["file"])

    def test_readme_and_ci_use_only_the_new_pipeline(self):
        root = Path(__file__).resolve().parents[1]
        readme = (root / "README.md").read_text(encoding="utf-8")
        workflow = (root / ".github/workflows/validate.yml").read_text(encoding="utf-8")

        self.assertIn("dist/public/places.geojson", readme)
        self.assertIn("python3 -m src.facility_data validate .", readme)
        self.assertIn("python3 -m src.facility_data build .", readme)
        self.assertNotIn("json_min", readme)
        self.assertNotIn("pandas", readme)
        self.assertIn("python3 -m src.facility_data validate .", workflow)
        self.assertNotIn("src.validate_data", workflow)


class LegacyMigrationTests(unittest.TestCase):
    def test_generates_uuid7_values(self):
        value = new_uuid7(timestamp_ms=1_722_124_800_000, random_bits=1)

        self.assertRegex(
            value,
            r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        )

    def test_migrates_only_in_scope_records_with_new_search_ids(self):
        def location(old_id, name):
            return {
                "id": old_id,
                "name": name,
                "name:en": "Ignored multilingual name",
                "lat": 35.69,
                "lng": 139.75,
                "imageUri": None,
                "imageCopyright": None,
            }

        legacy = [
            {"category": "図書館", "locations": [location("duplicate", "図書館A")]},
            {"category": "学校", "locations": [location("school", "学校A")]},
            {"category": "病院", "locations": [location("hospital", "病院A")]},
            {"category": "美術館", "locations": [location("duplicate", "美術館A")]},
        ]
        shortcuts = [{"category": "主要", "locations": [{"name": "図書館A"}]}]
        ids = iter(
            [
                "019c0000-0000-7000-8000-000000000020",
                "019c0000-0000-7000-8000-000000000021",
            ]
        )

        search, registry, report = migrate_legacy(
            legacy, shortcuts, "2026-07-28T00:00:00Z", id_factory=lambda: next(ids)
        )

        self.assertEqual(2, len(search["queries"]))
        self.assertEqual(2, len(registry["places"]))
        self.assertEqual(search["queries"][0]["id"], registry["places"][0]["id"])
        self.assertEqual({"図書館A", "美術館A"}, {p["name"] for p in registry["places"]})
        self.assertNotIn("names", str(registry))
        self.assertIn("kazaguruma.home-shortcut", registry["places"][0]["tags"])
        self.assertEqual({"学校": 1}, report["outOfScope"])
        self.assertEqual({"病院": 1}, report["needsSelection"])

    def test_writes_search_registry_and_report_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "json").mkdir()
            legacy = [
                {
                    "category": "図書館",
                    "locations": [
                        {
                            "id": "old",
                            "name": "図書館A",
                            "lat": 35.69,
                            "lng": 139.75,
                        }
                    ],
                }
            ]
            (root / "json/key_locations.json").write_text(
                json.dumps(legacy), encoding="utf-8"
            )
            (root / "json/main_facilities.json").write_text("[]", encoding="utf-8")

            migrate_repository(
                root,
                "2026-07-28T00:00:00Z",
                id_factory=lambda: "019c0000-0000-7000-8000-000000000030",
            )

            self.assertTrue((root / "inputs/osm-search/legacy/migration-v2.json").is_file())
            self.assertTrue((root / "data/registry.json").is_file())
            report = json.loads(
                (root / "reports/migration-v2.json").read_text(encoding="utf-8")
            )
        self.assertEqual(1, report["migrated"])

    def test_legacy_code_and_generated_data_are_removed(self):
        root = Path(__file__).resolve().parents[1]
        obsolete = [
            "src/convert_nursery_data.py",
            "src/facilities_check.py",
            "src/generate_release_notes.py",
            "src/json_minifier.py",
            "src/transform_json.py",
            "src/validate_data.py",
            "config/validation_exceptions.json",
            "json",
            "json_min",
            "kazaguruma_json",
            "kazaguruma_json_min",
            "run_process.bat",
            "requirements.txt",
            "stops.txt",
            "doc/facility_and_stop_distance_check_script.md",
            "doc/json_minifier_readme.md",
            "doc/nursery_data_conversion.md",
            "doc/process.md",
            "doc/release_notes_generator.md",
            "doc/transform_json_doc.md",
            "CLAUDE.md",
            "RELEASE_NOTES.md",
            ".claude",
        ]

        self.assertEqual([], [path for path in obsolete if (root / path).exists()])


class CandidateMatchingTests(unittest.TestCase):
    def test_filters_by_qid_or_fifty_metre_limit_without_expansion(self):
        qid_query = {
            "id": "019c0000-0000-7000-8000-000000000040",
            "name": "施設G",
            "qid": "Q123",
        }
        coordinate_query = {
            "id": "019c0000-0000-7000-8000-000000000041",
            "name": "施設H",
            "coordinates": [139.75, 35.69],
        }
        candidates = [
            {"type": "node", "id": "1", "name": "別名", "qid": "Q123", "coordinates": [140, 36]},
            {"type": "node", "id": "2", "name": "施設H", "coordinates": [139.7503, 35.69]},
            {"type": "node", "id": "3", "name": "施設H", "coordinates": [139.751, 35.69]},
        ]

        self.assertEqual(["node/1"], [c["recordId"] for c in match_osm_candidates(qid_query, candidates)])
        self.assertEqual(["node/2"], [c["recordId"] for c in match_osm_candidates(coordinate_query, candidates)])

    def test_requires_three_valid_votes_and_two_agreeing_votes(self):
        votes = [
            {"candidateId": "node/2", "decision": "link"},
            {"candidateId": "node/2", "decision": "link"},
            {"candidateId": "node/3", "decision": "reject"},
        ]

        self.assertEqual("node/2", decide_consensus(votes))
        self.assertIsNone(decide_consensus(votes[:2]))
        self.assertIsNone(
            decide_consensus(
                [
                    {"candidateId": "node/2", "decision": "merge"},
                    {"candidateId": "node/2", "decision": "merge"},
                    {"candidateId": "node/2", "decision": "merge"},
                ]
            )
        )

    def test_compact_audit_has_only_four_keys(self):
        audit = compact_audit(
            "2026-07-28T00:00:00Z", "language_model", "linked", "node/2"
        )

        self.assertEqual({"at", "method", "action", "target"}, set(audit))

    def test_keeps_superseded_osm_id_and_short_audit(self):
        query = {
            "id": "019c0000-0000-7000-8000-000000000042",
            "name": "施設I",
            "coordinates": [139.75, 35.69],
        }
        place = make_place(query, ["park"], [], "2026-07-01T00:00:00Z")
        place["externalRefs"] = [
            {
                "sourceId": "openstreetmap",
                "recordId": "node/1",
                "status": "current",
                "firstConfirmedAt": "2026-07-01T00:00:00Z",
                "lastConfirmedAt": "2026-07-01T00:00:00Z",
                "supersededAt": None,
                "basis": "name_coordinates",
            }
        ]

        updated = update_osm_reference(
            place,
            {"type": "way", "id": "2", "coordinates": [139.751, 35.691]},
            at="2026-07-28T00:00:00Z",
            basis="qid",
            method="language_model",
        )

        refs = updated["externalRefs"]
        self.assertEqual("superseded", refs[0]["status"])
        self.assertEqual("2026-07-28T00:00:00Z", refs[0]["supersededAt"])
        self.assertEqual("current", refs[1]["status"])
        self.assertEqual("way/2", refs[1]["recordId"])
        self.assertEqual(
            {"at", "method", "action", "target"}, set(updated["audit"][-1])
        )


if __name__ == "__main__":
    unittest.main()
