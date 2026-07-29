import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.facility_data import (
    _public_source_records,
    apply_source_updates,
    build_osm_batch_query,
    build_public_geojson,
    choose_geometry,
    collect_osm_ids,
    compact_audit,
    decide_consensus,
    match_osm_candidates,
    make_place,
    main,
    migrate_legacy,
    migrate_repository,
    new_uuid7,
    normalize_osm_elements,
    normalize_wam_rows,
    update_osm_reference,
    update_repository,
    validate_repository,
    validate_registry,
    validate_search_document,
    source_refresh_due,
)
from src.update_osm import main as update_osm_main
from src.update_wam import main as update_wam_main


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

        self.assertIn("source must be an object", issues)
        self.assertIn("unexpected top-level fields: unexpected", validate_search_document({"source": {"kind": "human", "sourceId": None, "retrievedAt": None}, "queries": [], "unexpected": True}))
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

    def test_rejects_invalid_point_coordinates(self):
        query = {
            "id": "019c0000-0000-7000-8000-000000000063",
            "name": "座標異常施設",
            "coordinates": [139.70, 35.60],
        }
        place = make_place(query, ["park"], [], "2026-07-28T00:00:00Z")
        place["geometry"]["coordinates"] = [True, 95.0]

        issues = validate_registry(
            {"schemaVersion": 1, "places": [place]}, {query["id"]: query}
        )

        self.assertIn(f"place {query['id']}: invalid Point coordinates", issues)

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
    def test_emits_images_lifecycle_and_source_namespaces(self):
        query = {
            "id": "019c0000-0000-7000-8000-000000000007",
            "name": "施設F",
            "coordinates": [139.75, 35.69],
        }
        place = make_place(query, ["park"], ["featured"], "2026-07-28T00:00:00Z")
        place["images"] = [
            {"url": "https://example.com/facility.webp", "rights": "© Photographer"}
        ]
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
            source_records={
                query["id"]: {
                    "openstreetmap": {
                        "retrievedAt": "2026-07-28T00:00:00Z",
                        "record": {
                            "type": "node",
                            "id": "1",
                            "coordinates": [139.75, 35.69],
                            "tags": {
                                "name": "施設F",
                                "operator": "運営者F",
                                "wheelchair": "yes",
                            },
                        },
                    },
                    "wam": {
                        "retrievedAt": "2026-07-28T00:00:00Z",
                        "records": [
                            {
                                "sourceRecordId": "wam-1",
                                "officeId": "office-1",
                                "serviceCode": "52",
                                "serviceType": "計画相談支援",
                                "name": "施設F",
                                "coordinates": [139.75, 35.69],
                            }
                        ],
                    },
                }
            },
        )

        self.assertEqual("Point", public["features"][0]["geometry"]["type"])
        self.assertEqual(
            {
                "id",
                "name",
                "categoryIds",
                "tags",
                "images",
                "town",
                "lifecycleStatus",
                "sources",
            },
            set(public["features"][0]["properties"]),
        )
        properties = public["features"][0]["properties"]
        self.assertEqual("北の丸公園", properties["town"])
        self.assertEqual(place["images"], properties["images"])
        self.assertEqual("active", properties["lifecycleStatus"])
        self.assertEqual("運営者F", properties["sources"]["openstreetmap"]["record"]["tags"]["operator"])
        self.assertEqual("計画相談支援", properties["sources"]["wam"]["records"][0]["serviceType"])
        rendered = str(public)
        self.assertNotIn("externalRefs", rendered)
        self.assertNotIn("audit", rendered)
        self.assertNotIn("matchBasis", rendered)
        self.assertNotIn("Polygon", rendered)

    def test_derives_short_town_name_from_multipolygon(self):
        query = {
            "id": "019c0000-0000-7000-8000-000000000008",
            "name": "施設G",
            "coordinates": [139.75, 35.69],
        }
        place = make_place(query, ["public-office"], [], "2026-07-28T00:00:00Z")
        towns = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "東京都千代田区内幸町"},
                    "geometry": {
                        "type": "MultiPolygon",
                        "coordinates": [
                            [
                                [
                                    [139.7, 35.6],
                                    [139.8, 35.6],
                                    [139.8, 35.7],
                                    [139.7, 35.7],
                                    [139.7, 35.6],
                                ]
                            ]
                        ],
                    },
                }
            ],
        }

        public = build_public_geojson(
            {"schemaVersion": 1, "places": [place]}, [], towns
        )

        self.assertEqual("内幸町", public["features"][0]["properties"]["town"])


class PublicSourceRecordTests(unittest.TestCase):
    def test_rejects_tampered_or_missing_osm_raw_records_and_invalid_tags(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "imports/openstreetmap"
            path.mkdir(parents=True)
            (path / "normalized.json").write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "queryId": "019c0000-0000-7000-8000-000000000007",
                                "type": "node",
                                "id": "1",
                                "coordinates": [139.75, 35.69],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            def write_raw(document):
                payload = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode()
                (path / "raw.json").write_bytes(payload)
                (path / "retrieval.json").write_text(
                    json.dumps(
                        {
                            "retrievedAt": "2026-07-28T00:00:00Z",
                            "rawSha256": hashlib.sha256(payload).hexdigest(),
                        }
                    ),
                    encoding="utf-8",
                )

            write_raw({"elements": []})
            with self.assertRaisesRegex(ValueError, "selected OSM raw record is missing"):
                _public_source_records(root)

            write_raw(
                {"elements": [{"type": "node", "id": 1, "tags": {"name": "施設F"}}]}
            )
            self.assertEqual(
                "施設F",
                _public_source_records(root)[
                    "019c0000-0000-7000-8000-000000000007"
                ]["openstreetmap"]["record"]["tags"]["name"],
            )
            (path / "raw.json").write_text(
                json.dumps(
                    {"elements": [{"type": "node", "id": 1, "tags": {"name": "改変"}}]}
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "OSM rawSha256 does not match"):
                _public_source_records(root)

            write_raw(
                {"elements": [{"type": "node", "id": 1, "tags": {"name": 123}}]}
            )
            with self.assertRaisesRegex(ValueError, "OSM tags must contain only strings"):
                _public_source_records(root)

    def test_projects_only_public_wam_fields_and_rejects_missing_components(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "imports/wam"
            path.mkdir(parents=True)
            (path / "normalized.json").write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "queryId": "019c0000-0000-7000-8000-000000000007",
                                "sourceRecordIds": ["wam-1"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "incomplete WAM snapshot"):
                _public_source_records(root)

            (path / "retrieval.json").write_text(
                json.dumps({"retrievedAt": "2026-07-28T00:00:00Z"}), encoding="utf-8"
            )
            (path / "raw.json").write_text(
                json.dumps(
                    {
                        "rows": [
                            {
                                "sourceRecordId": "wam-1",
                                "officeId": "office-1",
                                "serviceCode": "52",
                                "serviceType": "計画相談支援",
                                "name": "施設F",
                                "coordinates": [139.75, 35.69],
                                "internalHistory": "must not be public",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            records = _public_source_records(root)
            public_row = records["019c0000-0000-7000-8000-000000000007"]["wam"]["records"][0]
            self.assertEqual(
                {
                    "sourceRecordId",
                    "officeId",
                    "serviceCode",
                    "serviceType",
                    "name",
                    "coordinates",
                },
                set(public_row),
            )


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
            [
                "id",
                "name",
                "categoryIds",
                "tags",
                "images",
                "town",
                "lifecycleStatus",
                "sources",
            ],
            public_schema["$defs"]["feature"]["properties"]["properties"]["required"],
        )
        self.assertEqual([], validate_search_document(search_fixture))
        search_by_id = {item["id"]: item for item in search_fixture["queries"]}
        self.assertEqual([], validate_registry(registry_fixture, search_by_id))

    def test_pinned_town_source_populates_every_current_place(self):
        root = Path(__file__).resolve().parents[1]
        towns_path = root / "data/pinned/towns.geojson"
        metadata = json.loads(
            (root / "data/pinned/towns.retrieval.json").read_text(encoding="utf-8")
        )
        payload = towns_path.read_bytes()

        self.assertEqual(
            "0be816edaa8d0f8d22714a2f1146f2d9e133e09f", metadata["commit"]
        )
        self.assertEqual(hashlib.sha256(payload).hexdigest(), metadata["sha256"])
        registry = json.loads(
            (root / "data/registry.json").read_text(encoding="utf-8")
        )
        public = json.loads(
            (root / "dist/public/places.geojson").read_text(encoding="utf-8")
        )
        self.assertEqual(len(registry["places"]), len(public["features"]))
        self.assertTrue(
            all(feature["properties"]["town"] for feature in public["features"])
        )
        self.assertEqual(
            {"openstreetmap", "wam", "chiyoda-city-town-geojson"},
            {item["sourceId"] for item in public["sourceAttributions"]},
        )
        for attribution in public["sourceAttributions"]:
            self.assertTrue(
                {
                    "sourceId",
                    "url",
                    "license",
                    "version",
                    "retrievedAt",
                    "sha256",
                    "attribution",
                    "transformation",
                }.issubset(attribution)
            )

    def test_current_public_data_contains_images_and_direct_source_attributes(self):
        root = Path(__file__).resolve().parents[1]
        public = json.loads(
            (root / "dist/public/places.geojson").read_text(encoding="utf-8")
        )
        features = {item["properties"]["id"]: item for item in public["features"]}
        registry = json.loads((root / "data/registry.json").read_text(encoding="utf-8"))
        places = {item["id"]: item for item in registry["places"]}
        osm_record = json.loads(
            (root / "imports/openstreetmap/normalized.json").read_text(encoding="utf-8")
        )["records"][0]
        wam_record = json.loads(
            (root / "imports/wam/normalized.json").read_text(encoding="utf-8")
        )["records"][0]

        osm_properties = features[osm_record["queryId"]]["properties"]
        wam_properties = features[wam_record["queryId"]]["properties"]
        self.assertEqual(places[osm_record["queryId"]]["images"], osm_properties["images"])
        self.assertEqual("active", osm_properties["lifecycleStatus"])
        self.assertEqual(osm_record["type"], osm_properties["sources"]["openstreetmap"]["record"]["type"])
        self.assertTrue(osm_properties["sources"]["openstreetmap"]["record"]["tags"])
        self.assertEqual(
            wam_record["sourceRecordIds"],
            [
                row["sourceRecordId"]
                for row in wam_properties["sources"]["wam"]["records"]
            ],
        )

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
        self.assertIn("python3 -m src.retrieve_wam", readme)
        self.assertIn("python3 -m src.retrieve_osm", readme)
        self.assertIn("python3 -m src.retrieve_towns", readme)
        self.assertNotIn("/path/to/wam.json", readme)
        self.assertNotIn("/path/to/osm.json", readme)
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


class SourceUpdateTests(unittest.TestCase):
    def test_repository_validation_checks_normalized_snapshots(self):
        repository = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "inputs/osm-search/manual").mkdir(parents=True)
            (root / "data").mkdir()
            (root / "config").mkdir()
            (root / "imports/wam").mkdir(parents=True)
            (root / "imports/openstreetmap").mkdir(parents=True)
            (root / "inputs/osm-search/manual/base.json").write_text(
                (repository / "tests/fixtures/search-input.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "data/registry.json").write_text(
                (repository / "tests/fixtures/registry.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "config/sources.json").write_text(
                json.dumps({"sources": []}), encoding="utf-8"
            )
            (root / "imports/wam/normalized.json").write_text(
                json.dumps({"records": "not-an-array"}), encoding="utf-8"
            )
            query_id = json.loads(
                (repository / "tests/fixtures/search-input.json").read_text(encoding="utf-8")
            )["queries"][0]["id"]
            (root / "imports/openstreetmap/normalized.json").write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "queryId": query_id,
                                "type": "node",
                                "id": "1",
                                "coordinates": [139.75, 35.69],
                                "matchBasis": "invented",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            issues = validate_repository(root)

            osm_document = json.loads(
                (root / "imports/openstreetmap/normalized.json").read_text(encoding="utf-8")
            )
            osm_document["records"][0]["matchBasis"] = "name_coordinates"
            (root / "imports/openstreetmap/normalized.json").write_text(
                json.dumps(osm_document), encoding="utf-8"
            )
            name_coordinate_issues = validate_repository(root)

        self.assertIn("imports/wam/normalized.json: records must be an array", issues)
        self.assertTrue(any("invalid OSM matchBasis" in issue for issue in issues))
        self.assertFalse(
            any("invalid OSM matchBasis" in issue for issue in name_coordinate_issues)
        )

    def test_wam_cli_requires_a_pinned_raw_version(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "imports/wam").mkdir(parents=True)
            (root / "imports/wam/retrieval.json").write_text(
                json.dumps({"retrievedAt": None, "minimumIntervalDays": 30}),
                encoding="utf-8",
            )
            raw = root / "raw.json"
            raw.write_text(json.dumps({"rows": []}), encoding="utf-8")

            result = update_wam_main(
                [str(raw), str(root), "--at", "2026-07-28T00:00:00Z"]
            )
            raw.write_text(json.dumps({"version": "2026-H1"}), encoding="utf-8")
            missing_rows_result = update_wam_main(
                [str(raw), str(root), "--at", "2026-07-28T00:00:00Z"]
            )

        self.assertEqual(1, result)
        self.assertEqual(1, missing_rows_result)

    def test_osm_cli_prefers_current_id_and_can_link_by_qid(self):
        current_query = {
            "id": "019c0000-0000-7000-8000-000000000060",
            "name": "現在ID施設",
            "coordinates": [139.70, 35.60],
        }
        qid_query = {
            "id": "019c0000-0000-7000-8000-000000000061",
            "name": "QID施設",
            "qid": "Q123",
        }
        current_place = make_place(
            current_query, ["community"], [], "2026-07-01T00:00:00Z"
        )
        current_place["externalRefs"] = [
            {"sourceId": "openstreetmap", "recordId": "node/2", "status": "current"},
            {"sourceId": "openstreetmap", "recordId": "way/3", "status": "superseded"},
        ]
        qid_place = make_place(
            {**qid_query, "coordinates": [139.71, 35.61]},
            ["community"],
            [],
            "2026-07-01T00:00:00Z",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "data").mkdir()
            (root / "inputs/osm-search/manual").mkdir(parents=True)
            (root / "imports/openstreetmap").mkdir(parents=True)
            (root / "data/registry.json").write_text(
                json.dumps({"places": [current_place, qid_place]}), encoding="utf-8"
            )
            (root / "inputs/osm-search/manual/batch.json").write_text(
                json.dumps({"queries": [current_query, qid_query]}), encoding="utf-8"
            )
            (root / "imports/openstreetmap/retrieval.json").write_text(
                json.dumps({"retrievedAt": None, "minimumIntervalDays": 30}),
                encoding="utf-8",
            )
            raw = root / "raw.json"
            raw.write_text(
                json.dumps(
                    {
                        "version": "2026-07-28",
                        "elements": [
                            {"type": "node", "id": 2, "lat": 35.62, "lon": 139.72},
                            {
                                "type": "way",
                                "id": 3,
                                "center": {"lat": 35.63, "lon": 139.73},
                                "tags": {"wikidata": "Q123"},
                            },
                            {
                                "type": "relation",
                                "id": 4,
                                "center": {"lat": 35.64, "lon": 139.74},
                                "tags": {"wikidata": "Q123"},
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                0,
                update_osm_main(
                    ["normalize", str(root), "--raw", str(raw), "--at", "2026-07-28T00:00:00Z"]
                ),
            )
            records = json.loads(
                (root / "imports/openstreetmap/normalized.json").read_text(encoding="utf-8")
            )["records"]

        self.assertEqual(
            [(current_query["id"], "node", "2"), (qid_query["id"], "relation", "4")],
            [(record["queryId"], record["type"], record["id"]) for record in records],
        )
        self.assertEqual("source_record", records[0]["matchBasis"])
        self.assertEqual("qid", records[1]["matchBasis"])

    def test_repository_has_small_manual_source_update_contract(self):
        root = Path(__file__).resolve().parents[1]
        required = [
            "src/retrieve_wam.py",
            "src/retrieve_osm.py",
            "imports/wam/normalized.json",
            "imports/wam/retrieval.json",
            "imports/openstreetmap/normalized.json",
            "imports/openstreetmap/retrieval.json",
            ".github/workflows/update-wam.yml",
            ".github/workflows/update-osm.yml",
        ]
        for relative in required:
            self.assertTrue((root / relative).is_file(), relative)
        for source in ("wam", "openstreetmap"):
            metadata = json.loads(
                (root / f"imports/{source}/retrieval.json").read_text(encoding="utf-8")
            )
            self.assertGreaterEqual(metadata["minimumIntervalDays"], 30)
        workflows = "\n".join(
            (root / f".github/workflows/update-{source}.yml").read_text(encoding="utf-8")
            for source in ("wam", "osm")
        )
        self.assertIn("workflow_dispatch", workflows)
        self.assertNotIn("schedule:", workflows)
        self.assertNotIn("raw_path", workflows)
        self.assertNotIn("curl ", workflows)
        self.assertIn("src.retrieve_wam", workflows)
        self.assertIn("src.retrieve_osm", workflows)
        self.assertIn("src.resolve_osm_candidates", workflows)
        self.assertIn("secrets.LLM_API_KEY", workflows)
        self.assertIn("vars.LLM_MODEL", workflows)
        self.assertEqual(2, workflows.count("src.facility_data update"))
        self.assertEqual(2, workflows.count("actions/upload-artifact"))
        self.assertEqual(2, workflows.count("git add -N ."))
        sources = json.loads((root / "config/sources.json").read_text(encoding="utf-8"))
        source_ids = {source["id"] for source in sources["sources"]}
        self.assertIn("wam", source_ids)
        self.assertNotIn("tokyo-welfare-nursery", source_ids)
        self.assertNotIn("chiyoda-kindergarten", source_ids)
        self.assertNotIn("hitachi-kazaguruma", source_ids)

    def test_source_refresh_is_due_only_after_thirty_days(self):
        self.assertFalse(
            source_refresh_due(
                "2026-07-01T00:00:00Z", "2026-07-28T00:00:00Z"
            )
        )
        self.assertTrue(
            source_refresh_due(
                "2026-06-28T00:00:00Z", "2026-07-28T00:00:00Z"
            )
        )
        self.assertTrue(source_refresh_due(None, "2026-07-28T00:00:00Z"))
        for previous, current in (
            (None, "not-a-time"),
            (None, "2026-07-28T00:00:00"),
            ("2026-07-29T00:00:00Z", "2026-07-28T00:00:00Z"),
        ):
            with self.assertRaises(ValueError):
                source_refresh_due(previous, current)

    def test_repository_update_rejects_invalid_timestamp_before_io(self):
        with self.assertRaisesRegex(ValueError, "retrieval time"):
            update_repository(Path("/does/not/exist"), "not-a-time", "wam")

    def test_normalizes_only_stationary_wam_facilities(self):
        rows = [
            {
                "placeId": "019c0000-0000-7000-8000-000000000050",
                "facilityId": "wam-1",
                "name": "施設K",
                "longitude": 139.75,
                "latitude": 35.69,
                "serviceType": "通所",
            },
            {
                "placeId": "019c0000-0000-7000-8000-000000000064",
                "facilityId": "wam-4",
                "name": "非訪問型施設",
                "longitude": 139.77,
                "latitude": 35.71,
                "serviceType": "非訪問型",
            },
        ]
        visiting_types = [
            11,
            12,
            13,
            14,
            15,
            66,
            67,
            "居宅介護",
            "重度訪問介護",
            "行動援護",
            "重度障害者等包括支援",
            "同行援護",
            "居宅訪問型児童発達支援",
            "保育所等訪問支援",
        ]
        rows.extend(
            {
                "placeId": f"019c0000-0000-7000-8000-{100 + index:012x}",
                "facilityId": f"wam-visiting-{index}",
                "name": f"訪問系{index}",
                "longitude": 139.76,
                "latitude": 35.70,
                "serviceType": service_type,
            }
            for index, service_type in enumerate(visiting_types)
        )

        self.assertEqual(
            [
                {
                    "queryId": "019c0000-0000-7000-8000-000000000050",
                    "id": "wam-1",
                    "name": "施設K",
                    "coordinates": [139.75, 35.69],
                },
                {
                    "queryId": "019c0000-0000-7000-8000-000000000064",
                    "id": "wam-4",
                    "name": "非訪問型施設",
                    "coordinates": [139.77, 35.71],
                },
            ],
            normalize_wam_rows(rows),
        )
        with self.assertRaises(ValueError):
            normalize_wam_rows(
                [
                    {
                        "placeId": "019c0000-0000-7000-8000-000000000050",
                        "facilityId": "wam-bad",
                        "name": "壊れた施設",
                        "longitude": 139.75,
                        "latitude": 95.0,
                        "serviceType": "通所",
                    }
                ]
            )
        with self.assertRaises(ValueError):
            normalize_wam_rows(
                [
                    {
                        "placeId": "019c0000-0000-7000-8000-000000000050",
                        "facilityId": True,
                        "name": "boolean ID",
                        "longitude": 139.75,
                        "latitude": 35.69,
                        "serviceType": "通所",
                    }
                ]
            )

    def test_normalizes_osm_centres_without_polygons_or_members(self):
        elements = [
            {"type": "node", "id": 1, "lat": 35.69, "lon": 139.75, "tags": {"name": "施設L"}},
            {
                "type": "relation",
                "id": 2,
                "center": {"lat": 35.70, "lon": 139.76},
                "members": [{"type": "way", "ref": 9}],
                "geometry": [{"lat": 35.7, "lon": 139.7}],
                "tags": {"name": "施設M", "wikidata": "Q123"},
            },
        ]

        normalized = normalize_osm_elements(elements)

        self.assertEqual(2, len(normalized))

        self.assertEqual([139.75, 35.69], normalized[0]["coordinates"])
        self.assertEqual("Q123", normalized[1]["qid"])
        self.assertNotIn("members", str(normalized))
        self.assertNotIn("geometry", str(normalized))
        for malformed in (
            {"type": "area", "id": 3, "center": {"lat": 35.71, "lon": 139.77}},
            {"type": "node", "id": "bad", "lat": 35.71, "lon": 139.77},
            {"type": "node", "id": 4, "lat": 35.71, "lon": 139.77, "tags": {"wikidata": "Q0"}},
            {"type": "node", "id": 5, "lat": 95.0, "lon": 139.77},
        ):
            with self.assertRaises(ValueError):
                normalize_osm_elements([malformed])

    def test_applies_wam_geometry_before_osm_and_keeps_osm_reference(self):
        query = {
            "id": "019c0000-0000-7000-8000-000000000052",
            "name": "施設N",
            "coordinates": [139.70, 35.60],
        }
        place = make_place(query, ["social-welfare"], [], "2026-07-01T00:00:00Z")
        wam = {
            "queryId": query["id"],
            "id": "wam-52",
            "sourceRecordIds": ["wam-52", "wam-70"],
            "officeIds": ["office-52", "office-70"],
            "serviceCodes": ["52", "70"],
            "serviceTypes": ["計画相談支援", "障害児相談支援"],
            "name": "施設N",
            "coordinates": [139.7001, 35.6001],
        }
        wam_raw_rows = [
            {
                "sourceRecordId": "wam-52",
                "officeId": "office-52",
                "serviceCode": "52",
                "serviceType": "計画相談支援",
                "name": "施設N",
                "coordinates": [139.7001, 35.6001],
            },
            {
                "sourceRecordId": "wam-70",
                "officeId": "office-70",
                "serviceCode": "70",
                "serviceType": "障害児相談支援",
                "name": "施設N",
                "coordinates": [139.7001, 35.6001],
            },
        ]
        osm = {
            "queryId": query["id"],
            "type": "node",
            "id": "52",
            "name": "施設N",
            "coordinates": [139.7001, 35.6001],
            "matchBasis": "name_coordinates",
        }

        updated = apply_source_updates(
            {"schemaVersion": 1, "places": [place]},
            {query["id"]: query},
            [wam],
            [osm],
            "2026-07-28T00:00:00Z",
            wam_raw_rows=wam_raw_rows,
        )

        result = updated["places"][0]
        self.assertEqual([139.7001, 35.6001], result["geometry"]["coordinates"])
        self.assertEqual("wam", result["geometrySource"]["sourceId"])
        self.assertEqual("node/52", result["externalRefs"][-1]["recordId"])
        self.assertEqual("name_coordinates", result["externalRefs"][-1]["basis"])
        self.assertEqual({"at", "method", "action", "target"}, set(result["audit"][-1]))
        self.assertIn("linked_wam", [item["action"] for item in result["audit"]])
        self.assertEqual(
            {"wam-52", "wam-70"},
            {
                ref["recordId"]
                for ref in result["externalRefs"]
                if ref["sourceId"] == "wam" and ref["status"] == "current"
            },
        )

        osm_only = apply_source_updates(
            updated,
            {query["id"]: query},
            [],
            [{**osm, "id": "53", "coordinates": [139.7002, 35.6002]}],
            "2026-10-28T00:00:00Z",
        )["places"][0]
        self.assertEqual([139.7001, 35.6001], osm_only["geometry"]["coordinates"])
        self.assertEqual("wam", osm_only["geometrySource"]["sourceId"])
        self.assertEqual("node/53", osm_only["externalRefs"][-1]["recordId"])

    def test_revalidates_wam_record_against_query_and_raw_rows(self):
        query = {
            "id": "019c0000-0000-7000-8000-000000000053",
            "name": "施設W",
            "coordinates": [139.75, 35.69],
        }
        place = make_place(query, ["disability-support"], [], "2026-07-01T00:00:00Z")
        raw_rows = [
            {
                "sourceRecordId": "wam-1",
                "officeId": "office-1",
                "serviceCode": "52",
                "serviceType": "計画相談支援",
                "name": "施設W",
                "coordinates": [139.7501, 35.6901],
            }
        ]
        record = {
            "queryId": query["id"],
            "id": "wam-1",
            "sourceRecordIds": ["wam-1"],
            "officeIds": ["office-1"],
            "serviceCodes": ["52"],
            "serviceTypes": ["計画相談支援"],
            "name": "施設W",
            "coordinates": [139.7501, 35.6901],
        }

        for forged, rows in (
            ({**record, "name": "別施設"}, raw_rows),
            ({**record, "coordinates": [0, 0]}, raw_rows),
            ({**record, "sourceRecordIds": ["wam-2"], "id": "wam-2"}, raw_rows),
            ({**record, "serviceCodes": ["70"]}, raw_rows),
            (record, None),
        ):
            with self.subTest(forged=forged, rows=rows):
                with self.assertRaises(ValueError):
                    apply_source_updates(
                        {"schemaVersion": 1, "places": [place]},
                        {query["id"]: query},
                        [forged],
                        [],
                        "2026-07-29T00:00:00Z",
                        wam_raw_rows=rows,
                    )

    def test_revalidates_osm_match_basis_before_application(self):
        query = {
            "id": "019c0000-0000-7000-8000-000000000054",
            "name": "施設O",
            "coordinates": [139.75, 35.69],
        }
        place = make_place(query, ["community"], [], "2026-07-01T00:00:00Z")
        base = {
            "queryId": query["id"],
            "type": "node",
            "id": "54",
            "name": "施設O",
            "coordinates": [139.75, 35.69],
        }
        forged_records = [
            base,
            {**base, "matchBasis": "qid", "qid": "Q123"},
            {
                **base,
                "matchBasis": "name_coordinates",
                "name": "別施設",
                "coordinates": [140.5, 36.5],
            },
            {**base, "matchBasis": "source_record"},
        ]

        for record in forged_records:
            with self.subTest(record=record):
                with self.assertRaises(ValueError):
                    apply_source_updates(
                        {"schemaVersion": 1, "places": [place]},
                        {query["id"]: query},
                        [],
                        [record],
                        "2026-07-29T00:00:00Z",
                    )

    def test_applies_nearby_candidate_selected_by_language_model_consensus(self):
        query = {
            "id": "019c0000-0000-7000-8000-000000000055",
            "name": "相談支援センター",
            "coordinates": [139.75, 35.69],
        }
        place = make_place(query, ["disability-support"], [], "2026-07-01T00:00:00Z")
        record = {
            "queryId": query["id"],
            "type": "node",
            "id": "55",
            "name": "同じ建物の別表記",
            "coordinates": [139.7501, 35.6901],
            "matchBasis": "language_model",
        }

        updated = apply_source_updates(
            {"schemaVersion": 1, "places": [place]},
            {query["id"]: query},
            [],
            [record],
            "2026-07-29T00:00:00Z",
        )

        result = updated["places"][0]
        self.assertEqual("node/55", result["geometrySource"]["recordId"])
        self.assertEqual("language_model", result["externalRefs"][-1]["basis"])

    def test_builds_one_batch_query_for_current_and_historical_osm_ids(self):
        registry = {
            "places": [
                {
                    "externalRefs": [
                        {"sourceId": "openstreetmap", "recordId": "node/2", "status": "current"},
                        {"sourceId": "openstreetmap", "recordId": "way/3", "status": "superseded"},
                        {"sourceId": "openstreetmap", "recordId": "node/2", "status": "superseded"},
                    ]
                }
            ]
        }

        ids = collect_osm_ids(registry)
        query = build_osm_batch_query(ids, ["Q123"])

        self.assertEqual(["node/2", "way/3"], ids)
        self.assertEqual(1, query.count("[out:json]"))
        self.assertIn("node(id:2)", query)
        self.assertIn("way(id:3)", query)
        self.assertIn('nwr["wikidata"="Q123"]', query)
        self.assertIn("out center", query)
        self.assertEqual("", build_osm_batch_query([], []))

    def test_repository_update_uses_snapshots_without_deleting_places(self):
        repository = Path(__file__).resolve().parents[1]
        query = {
            "id": "019c0000-0000-7000-8000-000000000053",
            "name": "施設O",
            "coordinates": [139.70, 35.60],
        }
        place = make_place(query, ["community"], [], "2026-07-01T00:00:00Z")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "inputs/osm-search/manual").mkdir(parents=True)
            (root / "data").mkdir()
            (root / "config").mkdir()
            (root / "imports/wam").mkdir(parents=True)
            (root / "imports/openstreetmap").mkdir(parents=True)
            (root / "inputs/osm-search/manual/batch.json").write_text(
                json.dumps(
                    {
                        "source": {
                            "kind": "human",
                            "sourceId": None,
                            "retrievedAt": None,
                        },
                        "queries": [query],
                    }
                ),
                encoding="utf-8",
            )
            (root / "data/registry.json").write_text(
                json.dumps({"schemaVersion": 1, "places": [place]}), encoding="utf-8"
            )
            (root / "config/sources.json").write_text(
                (repository / "config/sources.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            wam_raw = {
                "version": "202603",
                "rows": [
                    {
                        "sourceRecordId": "stale-wam",
                        "officeId": "office-stale",
                        "serviceCode": "52",
                        "serviceType": "計画相談支援",
                        "name": "施設O",
                        "coordinates": [139.7002, 35.6002],
                    }
                ],
            }
            wam_raw_payload = (json.dumps(wam_raw, ensure_ascii=False, indent=2) + "\n").encode()
            (root / "imports/wam/raw.json").write_bytes(wam_raw_payload)
            (root / "imports/wam/retrieval.json").write_text(
                json.dumps(
                    {
                        "rawVersion": "202603",
                        "retrievedAt": "2026-07-28T00:00:00Z",
                        "rawSha256": hashlib.sha256(wam_raw_payload).hexdigest(),
                    }
                ),
                encoding="utf-8",
            )
            (root / "imports/openstreetmap/retrieval.json").write_text(
                json.dumps(
                    {
                        "rawVersion": "2026-07-28T00:00:00Z",
                        "retrievedAt": "2026-07-28T00:00:00Z",
                        "rawSha256": "0" * 64,
                    }
                ),
                encoding="utf-8",
            )
            (root / "imports/openstreetmap/raw.json").write_text(
                json.dumps(
                    {
                        "elements": [
                            {
                                "type": "node",
                                "id": 53,
                                "lat": 35.6001,
                                "lon": 139.7001,
                                "tags": {"name": "施設O"},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            osm_metadata_path = root / "imports/openstreetmap/retrieval.json"
            osm_metadata = json.loads(osm_metadata_path.read_text(encoding="utf-8"))
            osm_metadata["rawSha256"] = hashlib.sha256(
                (root / "imports/openstreetmap/raw.json").read_bytes()
            ).hexdigest()
            osm_metadata_path.write_text(json.dumps(osm_metadata), encoding="utf-8")
            (root / "imports/wam/normalized.json").write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "queryId": query["id"],
                                "id": "stale-wam",
                                "sourceRecordIds": ["stale-wam"],
                                "officeIds": ["office-stale"],
                                "serviceCodes": ["52"],
                                "serviceTypes": ["計画相談支援"],
                                "name": "施設O",
                                "coordinates": [139.7002, 35.6002],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "imports/openstreetmap/normalized.json").write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "queryId": query["id"],
                                "type": "node",
                                "id": "53",
                                "name": "施設O",
                                "coordinates": [139.7001, 35.6001],
                                "matchBasis": "name_coordinates",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            update_repository(root, "2026-07-28T00:00:00Z", "openstreetmap")
            self.assertEqual(
                0,
                main(
                    [
                        "update",
                        str(root),
                        "--source",
                        "openstreetmap",
                        "--at",
                        "2026-07-28T00:00:00Z",
                    ]
                ),
            )
            updated = json.loads((root / "data/registry.json").read_text(encoding="utf-8"))

        self.assertEqual(1, len(updated["places"]))
        self.assertEqual([139.7001, 35.6001], updated["places"][0]["geometry"]["coordinates"])

    def test_update_does_not_write_registry_when_public_build_fails(self):
        query = {
            "id": "019c0000-0000-7000-8000-000000000062",
            "name": "施設R",
            "coordinates": [139.70, 35.60],
        }
        registry = {
            "schemaVersion": 1,
            "places": [make_place(query, ["community"], [], "2026-07-01T00:00:00Z")],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "inputs/osm-search/manual").mkdir(parents=True)
            (root / "data").mkdir()
            (root / "config").mkdir()
            (root / "imports/openstreetmap").mkdir(parents=True)
            (root / "inputs/osm-search/manual/batch.json").write_text(
                json.dumps(
                    {
                        "source": {
                            "kind": "human",
                            "sourceId": None,
                            "retrievedAt": None,
                        },
                        "queries": [query],
                    }
                ),
                encoding="utf-8",
            )
            registry_path = root / "data/registry.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            before = registry_path.read_bytes()
            (root / "config/sources.json").write_text(
                json.dumps({"sources": [{"id": "broken"}]}), encoding="utf-8"
            )
            (root / "imports/openstreetmap/normalized.json").write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "queryId": query["id"],
                                "type": "node",
                                "id": "62",
                                "name": "施設R",
                                "coordinates": [139.7001, 35.6001],
                                "matchBasis": "name_coordinates",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "imports/openstreetmap/raw.json").write_text(
                json.dumps(
                    {
                        "elements": [
                            {
                                "type": "node",
                                "id": 62,
                                "lat": 35.6001,
                                "lon": 139.7001,
                                "tags": {"name": "施設R"},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "imports/openstreetmap/retrieval.json").write_text(
                json.dumps(
                    {
                        "rawVersion": "2026-07-28T00:00:00Z",
                        "retrievedAt": "2026-07-28T00:00:00Z",
                        "rawSha256": hashlib.sha256(
                            (root / "imports/openstreetmap/raw.json").read_bytes()
                        ).hexdigest(),
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(KeyError):
                update_repository(root, "2026-07-28T00:00:00Z", "openstreetmap")

            self.assertEqual(before, registry_path.read_bytes())

    def test_empty_snapshots_do_not_touch_registry(self):
        query = {
            "id": "019c0000-0000-7000-8000-000000000054",
            "name": "施設P",
            "coordinates": [139.70, 35.60],
        }
        registry = {
            "schemaVersion": 1,
            "places": [make_place(query, ["community"], [], "2026-07-01T00:00:00Z")],
        }

        updated = apply_source_updates(
            registry, {query["id"]: query}, [], [], "2026-07-28T00:00:00Z"
        )

        self.assertEqual(registry, updated)

    def test_rejects_duplicate_or_unknown_snapshot_query_ids(self):
        query = {
            "id": "019c0000-0000-7000-8000-000000000055",
            "name": "施設Q",
            "coordinates": [139.70, 35.60],
        }
        registry = {
            "schemaVersion": 1,
            "places": [make_place(query, ["community"], [], "2026-07-01T00:00:00Z")],
        }
        record = {
            "queryId": query["id"],
            "id": "wam-55",
            "name": "施設Q",
            "coordinates": [139.71, 35.61],
        }

        with self.assertRaises(ValueError):
            apply_source_updates(
                registry,
                {query["id"]: query},
                [record, record],
                [],
                "2026-07-28T00:00:00Z",
            )
        with self.assertRaises(ValueError):
            apply_source_updates(
                registry,
                {query["id"]: query},
                [{**record, "queryId": "019c0000-0000-7000-8000-000000000099"}],
                [],
                "2026-07-28T00:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
