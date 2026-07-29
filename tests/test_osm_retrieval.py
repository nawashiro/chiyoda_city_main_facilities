import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.retrieve_osm import (
    OVERPASS_ENDPOINT,
    build_discovery_query,
    prepare_osm_snapshot,
    run_osm_retrieval,
)


class OsmRetrievalTests(unittest.TestCase):
    def test_rejects_partial_overpass_response_with_remark(self):
        def post(endpoint, query):
            return (
                json.dumps(
                    {
                        "version": 0.6,
                        "osm3s": {"timestamp_osm_base": "2026-07-29T00:00:00Z"},
                        "remark": "runtime error: Query timed out; partial data follows",
                        "elements": [],
                    }
                ).encode(),
                {},
            )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "inputs/osm-search/manual").mkdir(parents=True)
            (root / "imports/openstreetmap").mkdir(parents=True)
            (root / "data/registry.json").write_text(
                json.dumps({"schemaVersion": 1, "places": []}), encoding="utf-8"
            )
            (root / "inputs/osm-search/manual/batch.json").write_text(
                json.dumps({"source": {"kind": "human", "sourceId": None, "retrievedAt": None}, "queries": []}),
                encoding="utf-8",
            )
            (root / "imports/openstreetmap/retrieval.json").write_text(
                json.dumps({"retrievedAt": None, "minimumIntervalDays": 30}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "partial or errored"):
                run_osm_retrieval(root, "2026-07-29T01:00:00Z", post)

    def test_does_not_trust_current_id_after_conflicting_distant_move(self):
        query_id = "019c0000-0000-7000-8000-000000000104"
        query = {"id": query_id, "name": "施設D", "coordinates": [139.75, 35.69]}
        registry = {
            "schemaVersion": 1,
            "places": [
                {
                    "id": query_id,
                    "name": "施設D",
                    "geometry": {"type": "Point", "coordinates": [139.75, 35.69]},
                    "externalRefs": [
                        {"sourceId": "openstreetmap", "recordId": "node/9", "status": "current"}
                    ],
                }
            ],
        }
        raw = {
            "version": "2026-07-29T00:00:00Z",
            "elements": [
                {"type": "node", "id": 9, "lat": 36.5, "lon": 140.5, "tags": {"name": "別施設"}}
            ],
        }

        normalized, report = prepare_osm_snapshot(
            registry, [{"queries": [query]}], raw
        )

        self.assertEqual([], normalized["records"])
        self.assertEqual("none", report["queries"][0]["status"])

    def test_run_osm_retrieval_posts_once_and_writes_review_artifacts(self):
        query_id = "019c0000-0000-7000-8000-000000000103"
        calls = []

        def post(endpoint, query):
            calls.append((endpoint, query))
            return (
                json.dumps(
                    {
                        "version": 0.6,
                        "generator": "Overpass API",
                        "osm3s": {"timestamp_osm_base": "2026-07-29T00:00:00Z"},
                        "elements": [
                            {
                                "type": "node",
                                "id": 10,
                                "lat": 35.69,
                                "lon": 139.75,
                                "tags": {"name": "施設C", "amenity": "library"},
                            }
                        ],
                    }
                ).encode(),
                {"ETag": '"overpass-fixture"'},
            )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "inputs/osm-search/manual").mkdir(parents=True)
            (root / "imports/openstreetmap").mkdir(parents=True)
            (root / "data/registry.json").write_text(
                json.dumps({"schemaVersion": 1, "places": []}), encoding="utf-8"
            )
            (root / "inputs/osm-search/manual/batch.json").write_text(
                json.dumps(
                    {
                        "source": {"kind": "human", "sourceId": None, "retrievedAt": None},
                        "queries": [
                            {
                                "id": query_id,
                                "name": "施設C",
                                "coordinates": [139.75, 35.69],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (root / "imports/openstreetmap/retrieval.json").write_text(
                json.dumps({"retrievedAt": None, "rawVersion": None, "minimumIntervalDays": 30}),
                encoding="utf-8",
            )

            run_osm_retrieval(root, "2026-07-29T01:00:00Z", post)

            normalized = json.loads(
                (root / "imports/openstreetmap/normalized.json").read_text(encoding="utf-8")
            )
            report = json.loads(
                (root / "reports/osm-candidates.json").read_text(encoding="utf-8")
            )
            metadata = json.loads(
                (root / "imports/openstreetmap/retrieval.json").read_text(encoding="utf-8")
            )
            raw = json.loads(
                (root / "imports/openstreetmap/raw.json").read_text(encoding="utf-8")
            )
            raw_bytes = (root / "imports/openstreetmap/raw.json").read_bytes()
            raw_response_bytes = (root / "imports/openstreetmap/raw-response.json").read_bytes()
            query_bytes = (root / "imports/openstreetmap/query.overpassql").read_bytes()

        self.assertEqual(1, len(calls))
        self.assertEqual(OVERPASS_ENDPOINT, calls[0][0])
        self.assertEqual(query_id, normalized["records"][0]["queryId"])
        self.assertEqual("linked", report["queries"][0]["status"])
        self.assertEqual("2026-07-29T00:00:00Z", raw["version"])
        self.assertEqual("2026-07-29T00:00:00Z", metadata["rawVersion"])
        self.assertEqual(64, len(metadata["querySha256"]))
        self.assertEqual(64, len(metadata["responseSha256"]))
        self.assertIs(metadata["queryRetained"], True)
        self.assertIs(metadata["responseRetained"], True)
        self.assertEqual(
            metadata["responseSha256"], hashlib.sha256(raw_response_bytes).hexdigest()
        )
        self.assertEqual(
            metadata["querySha256"], hashlib.sha256(query_bytes).hexdigest()
        )
        self.assertEqual(metadata["rawSha256"], hashlib.sha256(raw_bytes).hexdigest())

    def test_builds_one_chiyoda_area_query_for_refresh_and_discovery(self):
        query = build_discovery_query(["node/2", "way/3"], ["Q123"])

        self.assertEqual(1, query.count("[out:json]"))
        self.assertEqual(1, query.count("->.searchArea"))
        self.assertIn("node(id:2)", query)
        self.assertIn("way(id:3)", query)
        self.assertIn('nwr["wikidata"="Q123"]', query)
        self.assertIn('nwr(area.searchArea)["amenity"~', query)
        self.assertIn('nwr(area.searchArea)["tourism"~', query)
        self.assertIn('nwr(area.searchArea)["leisure"="park"]', query)
        self.assertIn('nwr(area.searchArea)["office"="government"]', query)
        self.assertNotIn("around:", query)
        self.assertIn(");out center;", query)
        self.assertTrue(query.endswith("out center;"))

    def test_auto_links_only_unique_exact_name_and_reports_all_fifty_metre_candidates(self):
        query_id = "019c0000-0000-7000-8000-000000000101"
        search_documents = [
            {
                "source": {"kind": "human", "sourceId": None, "retrievedAt": None},
                "queries": [
                    {
                        "id": query_id,
                        "name": "施設A",
                        "coordinates": [139.75, 35.69],
                    }
                ],
            }
        ]
        registry = {"schemaVersion": 1, "places": []}
        raw = {
            "version": "2026-07-29T00:00:00Z",
            "elements": [
                {
                    "type": "node",
                    "id": 1,
                    "lat": 35.69005,
                    "lon": 139.75005,
                    "tags": {"name": "施設A", "amenity": "social_facility"},
                },
                {
                    "type": "way",
                    "id": 2,
                    "center": {"lat": 35.6901, "lon": 139.7501},
                    "tags": {"name": "別施設", "amenity": "social_facility"},
                },
                {
                    "type": "node",
                    "id": 3,
                    "lat": 35.70,
                    "lon": 139.76,
                    "tags": {"name": "施設A", "amenity": "social_facility"},
                },
            ],
        }

        normalized, report = prepare_osm_snapshot(registry, search_documents, raw)

        self.assertEqual(1, len(normalized["records"]))
        self.assertEqual(query_id, normalized["records"][0]["queryId"])
        self.assertEqual("name_coordinates", normalized["records"][0]["matchBasis"])
        self.assertEqual("1", normalized["records"][0]["id"])
        self.assertEqual(
            ["node/1", "way/2"],
            [candidate["recordId"] for candidate in report["queries"][0]["candidates"]],
        )

    def test_does_not_auto_link_ambiguous_exact_names(self):
        query_id = "019c0000-0000-7000-8000-000000000102"
        searches = [
            {
                "source": {"kind": "human", "sourceId": None, "retrievedAt": None},
                "queries": [
                    {"id": query_id, "name": "施設B", "coordinates": [139.75, 35.69]}
                ],
            }
        ]
        raw = {
            "version": "2026-07-29T00:00:00Z",
            "elements": [
                {"type": "node", "id": 4, "lat": 35.69, "lon": 139.75, "tags": {"name": "施設B"}},
                {"type": "node", "id": 5, "lat": 35.69001, "lon": 139.75001, "tags": {"name": "施設B"}},
            ],
        }

        normalized, report = prepare_osm_snapshot({"places": []}, searches, raw)

        self.assertEqual([], normalized["records"])
        self.assertEqual(2, len(report["queries"][0]["candidates"]))
        self.assertEqual("ambiguous", report["queries"][0]["status"])


if __name__ == "__main__":
    unittest.main()
