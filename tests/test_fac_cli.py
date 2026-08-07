import json
import subprocess
import tempfile
import unittest
import uuid
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from src.fac_cli import main


PLACE_ID = "019c0000-0000-7000-8000-000000000301"


def write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class FacilityListCliTests(unittest.TestCase):
    def test_lists_compact_attributes_and_geo_uri(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "data/registry.json",
                {
                    "schemaVersion": 1,
                    "places": [
                        {
                            "id": PLACE_ID,
                            "name": "千代田区役所",
                            "categoryIds": ["public-office"],
                            "tags": ["shortcut"],
                            "geometry": {
                                "type": "Point",
                                "coordinates": [139.7535624, 35.6941626],
                            },
                            "geometrySource": {},
                            "images": [],
                            "externalRefs": [
                                {
                                    "sourceId": "openstreetmap",
                                    "recordId": "relation/123",
                                    "status": "current",
                                },
                                {
                                    "sourceId": "wam",
                                    "recordId": "wam-1",
                                    "status": "superseded",
                                },
                            ],
                            "lifecycle": {"status": "active"},
                            "visibility": {"status": "public"},
                            "audit": [],
                        }
                    ],
                },
            )

            output = StringIO()
            with redirect_stdout(output):
                result = main(["ls", str(root)])

        self.assertEqual(0, result)
        self.assertEqual(
            "千代田区役所\n"
            "  id=019c0000-0000-7000-8000-000000000301\n"
            "  cat=public-office tags=true img=false osm=current wam=superseded "
            "life=active vis=public\n"
            "  geo:35.6941626,139.7535624?q=%E5%8D%83%E4%BB%A3%E7%94%B0%E5%8C%BA%E5%BD%B9%E6%89%80\n",
            output.getvalue(),
        )

    def test_lists_clickable_geo_uri_and_colored_attributes_when_forced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            place = {
                "id": PLACE_ID,
                "name": "対象施設",
                "categoryIds": ["disability-support"],
                "tags": [],
                "geometry": {"type": "Point", "coordinates": [139.75, 35.69]},
                "geometrySource": {},
                "images": ["image"],
                "externalRefs": [],
                "lifecycle": {"status": "active"},
                "visibility": {"status": "public"},
                "audit": [],
            }
            write_json(
                root / "data/registry.json",
                {"schemaVersion": 1, "places": [place]},
            )
            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "ls",
                        str(root),
                        "--color",
                        "always",
                        "--hyperlink",
                        "always",
                    ]
                )

        text = output.getvalue()
        self.assertEqual(0, result)
        self.assertIn("対象施設\n", text)
        self.assertIn(f"  \x1b[36mid\x1b[0m={PLACE_ID}\n", text)
        self.assertIn("\x1b[36mcat\x1b[0m=disability-support", text)
        self.assertIn("\x1b[31mfalse\x1b[0m", text)
        self.assertIn("\x1b[32mtrue\x1b[0m", text)
        self.assertIn("\x1b[32mactive\x1b[0m", text)
        self.assertIn("\x1b[32mpublic\x1b[0m", text)
        geo_uri = "geo:35.69,139.75?q=%E5%AF%BE%E8%B1%A1%E6%96%BD%E8%A8%AD"
        self.assertIn(
            f"\x1b]8;;{geo_uri}\x1b\\\x1b[34m{geo_uri}\x1b[0m\x1b]8;;\x1b\\", text
        )

    def test_filters_places_without_adding_town_to_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            places = []
            for index, (name, category, status) in enumerate(
                [
                    ("神保町図書館", "library", "current"),
                    ("神保町公園", "park", "superseded"),
                ],
                start=1,
            ):
                place = {
                    "id": f"019c0000-0000-7000-8000-00000000030{index}",
                    "name": name,
                    "categoryIds": [category],
                    "tags": [],
                    "geometry": {
                        "type": "Point",
                        "coordinates": [139.75 + index / 100, 35.69],
                    },
                    "geometrySource": {},
                    "images": [],
                    "externalRefs": [
                        {
                            "sourceId": "openstreetmap",
                            "recordId": f"node/{index}",
                            "status": status,
                        }
                    ],
                    "lifecycle": {"status": "active"},
                    "visibility": {"status": "public"},
                    "audit": [],
                }
                places.append(place)
            write_json(root / "data/registry.json", {"schemaVersion": 1, "places": places})
            write_json(
                root / "dist/public/places.geojson",
                {
                    "type": "FeatureCollection",
                    "sourceAttributions": [],
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": place["geometry"],
                            "properties": {
                                "id": place["id"],
                                "town": "神田神保町",
                            },
                        }
                        for place in places
                    ],
                },
            )

            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "ls",
                        str(root),
                        "--town",
                        "神田神保町",
                        "--cat",
                        "library",
                        "--name",
                        "図書館",
                        "--osm",
                        "current",
                        "--life",
                        "active",
                    ]
                )

        self.assertEqual(0, result)
        self.assertIn("神保町図書館", output.getvalue())
        self.assertNotIn("神保町公園", output.getvalue())
        self.assertNotIn("town=", output.getvalue())

    def test_get_prints_the_complete_canonical_place(self):
        place = {
            "id": PLACE_ID,
            "name": "施設A",
            "categoryIds": ["park"],
            "tags": [],
            "geometry": {"type": "Point", "coordinates": [139.75, 35.69]},
            "geometrySource": {},
            "images": [],
            "externalRefs": [],
            "lifecycle": {"status": "active"},
            "visibility": {"status": "public"},
            "audit": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / "data/registry.json", {"schemaVersion": 1, "places": [place]})
            output = StringIO()
            with redirect_stdout(output):
                result = main(["get", str(root), PLACE_ID])

        self.assertEqual(0, result)
        self.assertEqual(place, json.loads(output.getvalue()))

    def test_fac_launcher_runs_from_repository_root(self):
        place = {
            "id": PLACE_ID,
            "name": "起動確認施設",
            "categoryIds": ["park"],
            "tags": [],
            "geometry": {"type": "Point", "coordinates": [139.75, 35.69]},
            "geometrySource": {},
            "images": [],
            "externalRefs": [],
            "lifecycle": {"status": "active"},
            "visibility": {"status": "public"},
            "audit": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / "data/registry.json", {"schemaVersion": 1, "places": [place]})
            repository = Path(__file__).resolve().parents[1]
            completed = subprocess.run(
                [str(repository / "fac"), "ls", str(root)],
                cwd=repository,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("起動確認施設", completed.stdout)

    def test_ls_reports_malformed_registry_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "data/registry.json",
                {
                    "schemaVersion": 1,
                    "places": [
                        {
                            "id": PLACE_ID,
                            "name": "壊れた施設",
                            "categoryIds": ["park"],
                            "tags": [],
                            "images": [],
                            "externalRefs": [],
                            "lifecycle": {"status": "active"},
                            "visibility": {"status": "public"},
                            "audit": [],
                        }
                    ],
                },
            )
            output = StringIO()
            error = StringIO()
            with redirect_stdout(output), redirect_stderr(error):
                result = main(["ls", str(root), "--name", "存在しない名前"])

        self.assertEqual(1, result)
        self.assertEqual("", output.getvalue())
        self.assertTrue(error.getvalue().startswith("ERROR: "))
        self.assertNotIn("Traceback", error.getvalue())

    def test_get_rejects_malformed_place_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "data/registry.json",
                {
                    "schemaVersion": 1,
                    "places": [
                        {
                            "id": PLACE_ID,
                            "name": "壊れた施設",
                            "categoryIds": ["park"],
                            "tags": [],
                            "images": [],
                            "externalRefs": [],
                            "lifecycle": {"status": "active"},
                            "visibility": {"status": "public"},
                            "audit": [],
                        }
                    ],
                },
            )
            output = StringIO()
            error = StringIO()
            with redirect_stdout(output), redirect_stderr(error):
                result = main(["get", str(root), PLACE_ID])

        self.assertEqual(1, result)
        self.assertEqual("", output.getvalue())
        self.assertTrue(error.getvalue().startswith("ERROR: "))

    def test_ls_rejects_hidden_place_that_breaks_registry_schema(self):
        valid = {
            "id": PLACE_ID,
            "name": "正常施設",
            "categoryIds": ["park"],
            "tags": [],
            "geometry": {"type": "Point", "coordinates": [139.75, 35.69]},
            "geometrySource": {},
            "images": [],
            "externalRefs": [],
            "lifecycle": {"status": "active"},
            "visibility": {"status": "public"},
            "audit": [],
        }
        malformed = dict(valid)
        malformed.update(
            {
                "id": 7,
                "name": "壊れた施設",
                "categoryIds": [],
                "unexpected": "accepted",
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "data/registry.json",
                {"schemaVersion": 1, "places": [valid, malformed]},
            )
            output = StringIO()
            error = StringIO()
            with redirect_stdout(output), redirect_stderr(error):
                result = main(["ls", str(root), "--name", "正常施設"])

        self.assertEqual(1, result)
        self.assertEqual("", output.getvalue())
        self.assertTrue(error.getvalue().startswith("ERROR: "))


class FacilityRefCliTests(unittest.TestCase):
    def test_ref_replaces_current_osm_reference_and_preserves_history(self):
        at = "2026-07-30T12:00:00+00:00"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            query = {
                "id": PLACE_ID,
                "name": "施設A",
                "coordinates": [139.75, 35.69],
            }
            write_json(
                root / "inputs/osm-search/human/202607.json",
                {
                    "source": {"kind": "human", "sourceId": None, "retrievedAt": None},
                    "queries": [query],
                },
            )
            write_json(
                root / "data/registry.json",
                {
                    "schemaVersion": 1,
                    "places": [
                        {
                            "id": PLACE_ID,
                            "name": "施設A",
                            "categoryIds": ["park"],
                            "tags": [],
                            "geometry": {"type": "Point", "coordinates": [139.75, 35.69]},
                            "geometrySource": {},
                            "images": [],
                            "externalRefs": [
                                {
                                    "sourceId": "openstreetmap",
                                    "recordId": "node/1",
                                    "status": "current",
                                    "firstConfirmedAt": "2026-07-29T00:00:00+00:00",
                                    "lastConfirmedAt": "2026-07-29T00:00:00+00:00",
                                    "supersededAt": None,
                                    "basis": "name_coordinates",
                                }
                            ],
                            "lifecycle": {"status": "active"},
                            "visibility": {"status": "public"},
                            "audit": [],
                        }
                    ],
                },
            )

            result = main(["ref", str(root), PLACE_ID, "osm", "way/2", "--at", at])
            registry = json.loads((root / "data/registry.json").read_text(encoding="utf-8"))

        self.assertEqual(0, result)
        place = registry["places"][0]
        old_ref, new_ref = place["externalRefs"]
        self.assertEqual("superseded", old_ref["status"])
        self.assertEqual(at, old_ref["supersededAt"])
        self.assertEqual(
            {
                "sourceId": "openstreetmap",
                "recordId": "way/2",
                "status": "current",
                "firstConfirmedAt": at,
                "lastConfirmedAt": at,
                "supersededAt": None,
                "basis": "human_review",
            },
            new_ref,
        )
        self.assertEqual(
            {
                "at": at,
                "method": "human_inference",
                "action": "linked_osm",
                "target": "way/2",
            },
            place["audit"][-1],
        )

    def test_ref_reports_invalid_osm_id_without_traceback(self):
        with tempfile.TemporaryDirectory():
            error = StringIO()
            with redirect_stderr(error):
                result = main(["ref", PLACE_ID, "osm", "123"])

        self.assertEqual(1, result)
        self.assertEqual(
            "ERROR: OSM record ID must be node/N, way/N, or relation/N\n",
            error.getvalue(),
        )

    def test_ref_rejects_unsupported_source_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            error = StringIO()
            with redirect_stderr(error):
                result = main(["ref", str(root), PLACE_ID, "evil", "payload"])

        self.assertEqual(1, result)
        self.assertEqual("ERROR: ref currently supports only osm\n", error.getvalue())
        self.assertFalse((root / "data/registry.json").exists())


class FacilitySetCliTests(unittest.TestCase):
    def test_set_replaces_maintainer_fields_and_records_audit(self):
        at = "2026-07-30T13:00:00+00:00"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            query = {
                "id": PLACE_ID,
                "name": "施設A",
                "coordinates": [139.75, 35.69],
            }
            write_json(
                root / "inputs/osm-search/human/202607.json",
                {
                    "source": {"kind": "human", "sourceId": None, "retrievedAt": None},
                    "queries": [query],
                },
            )
            write_json(
                root / "data/registry.json",
                {
                    "schemaVersion": 1,
                    "places": [
                        {
                            "id": PLACE_ID,
                            "name": "施設A",
                            "categoryIds": ["park"],
                            "tags": [],
                            "geometry": {"type": "Point", "coordinates": [139.75, 35.69]},
                            "geometrySource": {},
                            "images": [],
                            "externalRefs": [],
                            "lifecycle": {"status": "active", "changedAt": at},
                            "visibility": {"status": "public", "changedAt": at},
                            "audit": [],
                        }
                    ],
                },
            )

            result = main(
                [
                    "set",
                    str(root),
                    PLACE_ID,
                    "--cat",
                    "library",
                    "--cat",
                    "museum",
                    "--tag",
                    "shortcut",
                    "--life",
                    "closed",
                    "--vis",
                    "private",
                    "--at",
                    at,
                ]
            )
            registry = json.loads((root / "data/registry.json").read_text(encoding="utf-8"))

        self.assertEqual(0, result)
        place = registry["places"][0]
        self.assertEqual(["library", "museum"], place["categoryIds"])
        self.assertEqual(["shortcut"], place["tags"])
        self.assertEqual({"status": "closed", "changedAt": at}, place["lifecycle"])
        self.assertEqual({"status": "private", "changedAt": at}, place["visibility"])
        self.assertEqual(
            ["updated_categories", "updated_tags", "updated_lifecycle", "updated_visibility"],
            [audit["action"] for audit in place["audit"]],
        )


class SearchInputCliTests(unittest.TestCase):
    def test_in_add_generates_uuid7_and_stores_geojson_coordinate_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "in",
                        "add",
                        str(root),
                        "新しい施設",
                        "--lon",
                        "139.75",
                        "--lat",
                        "35.69",
                        "--at",
                        "2026-07-30T14:00:00+00:00",
                    ]
                )
            document = json.loads(
                (root / "inputs/osm-search/human/202607.json").read_text(encoding="utf-8")
            )

        self.assertEqual(0, result)
        query = document["queries"][0]
        self.assertEqual(7, uuid.UUID(query["id"]).version)
        self.assertEqual("新しい施設", query["name"])
        self.assertEqual([139.75, 35.69], query["coordinates"])
        self.assertEqual(f"id={query['id']}\n", output.getvalue())

    def test_in_rm_removes_search_input_and_makes_place_closed_private(self):
        at = "2026-08-07T10:00:00+00:00"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            query = {"id": PLACE_ID, "name": "重複施設", "qid": "Q12345"}
            path = root / "inputs/osm-search/human/202607.json"
            write_json(
                path,
                {
                    "source": {"kind": "human", "sourceId": None, "retrievedAt": None},
                    "queries": [query],
                },
            )
            write_json(
                root / "data/registry.json",
                {
                    "schemaVersion": 1,
                    "places": [
                        {
                            "id": PLACE_ID,
                            "name": "重複施設",
                            "categoryIds": ["museum"],
                            "tags": [],
                            "geometry": {"type": "Point", "coordinates": [139.75, 35.69]},
                            "geometrySource": {},
                            "images": [],
                            "externalRefs": [],
                            "lifecycle": {"status": "active", "changedAt": at},
                            "visibility": {"status": "public", "changedAt": at},
                            "audit": [],
                        }
                    ],
                },
            )

            result = main(["in", "rm", str(root), PLACE_ID, "--at", at])
            document = json.loads(path.read_text(encoding="utf-8"))
            registry = json.loads((root / "data/registry.json").read_text(encoding="utf-8"))

        self.assertEqual(0, result)
        self.assertEqual([], document["queries"])
        place = registry["places"][0]
        self.assertEqual({"status": "closed", "changedAt": at}, place["lifecycle"])
        self.assertEqual({"status": "private", "changedAt": at}, place["visibility"])
        self.assertEqual(
            ["removed_search_input", "updated_lifecycle", "updated_visibility"],
            [audit["action"] for audit in place["audit"]],
        )

    def test_in_set_switches_coordinates_to_qid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "inputs/osm-search/human/202607.json"
            write_json(
                path,
                {
                    "source": {"kind": "human", "sourceId": None, "retrievedAt": None},
                    "queries": [
                        {
                            "id": PLACE_ID,
                            "name": "修正前",
                            "coordinates": [139.75, 35.69],
                        }
                    ],
                },
            )

            result = main(
                ["in", "set", str(root), PLACE_ID, "--name", "修正後", "--qid", "Q12345"]
            )
            document = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(0, result)
        self.assertEqual(
            {"id": PLACE_ID, "name": "修正後", "qid": "Q12345"},
            document["queries"][0],
        )

    def test_in_ls_shows_geo_uri_or_qid(self):
        qid_id = "019c0000-0000-7000-8000-000000000302"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "inputs/osm-search/human/202607.json",
                {
                    "source": {"kind": "human", "sourceId": None, "retrievedAt": None},
                    "queries": [
                        {
                            "id": PLACE_ID,
                            "name": "座標施設",
                            "coordinates": [139.75, 35.69],
                        },
                        {"id": qid_id, "name": "QID施設", "qid": "Q12345"},
                    ],
                },
            )
            output = StringIO()
            with redirect_stdout(output):
                result = main(["in", "ls", str(root)])

        self.assertEqual(0, result)
        self.assertEqual(
            f"座標施設\n  id={PLACE_ID}\n"
            "  geo:35.69,139.75?q=%E5%BA%A7%E6%A8%99%E6%96%BD%E8%A8%AD\n"
            f"QID施設\n  id={qid_id}\n  qid=Q12345\n",
            output.getvalue(),
        )

    def test_in_get_prints_complete_search_input(self):
        query = {"id": PLACE_ID, "name": "QID施設", "qid": "Q12345"}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "inputs/osm-search/human/202607.json",
                {
                    "source": {"kind": "human", "sourceId": None, "retrievedAt": None},
                    "queries": [query],
                },
            )
            output = StringIO()
            with redirect_stdout(output):
                result = main(["in", "get", str(root), PLACE_ID])

        self.assertEqual(0, result)
        self.assertEqual(query, json.loads(output.getvalue()))

    def test_in_ls_validates_every_row_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "inputs/osm-search/human/202607.json",
                {
                    "source": {"kind": "human", "sourceId": None, "retrievedAt": None},
                    "queries": [
                        {
                            "id": PLACE_ID,
                            "name": "正常施設",
                            "coordinates": [139.75, 35.69],
                        },
                        {
                            "id": "019c0000-0000-7000-8000-000000000302",
                            "name": "壊れた施設",
                        },
                    ],
                },
            )
            output = StringIO()
            error = StringIO()
            with redirect_stdout(output), redirect_stderr(error):
                result = main(["in", "ls", str(root)])

        self.assertEqual(1, result)
        self.assertEqual("", output.getvalue())
        self.assertTrue(error.getvalue().startswith("ERROR: "))


if __name__ == "__main__":
    unittest.main()
