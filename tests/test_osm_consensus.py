import json
import tempfile
import unittest
from pathlib import Path

from src.resolve_osm_candidates import REVIEW_PERSPECTIVES, resolve_osm_candidates


class OsmConsensusTests(unittest.TestCase):
    def test_calls_three_distinct_perspectives_with_all_candidates_at_once(self):
        query_id = "019c0000-0000-7000-8000-000000000205"
        report = {
            "version": "2026-07-29T00:00:00Z",
            "queries": [
                {
                    "queryId": query_id,
                    "name": "施設E",
                    "target": {
                        "id": query_id,
                        "name": "施設E",
                        "coordinates": [139.75, 35.69],
                    },
                    "status": "candidates",
                    "candidates": [
                        {
                            "type": "node",
                            "id": "5",
                            "name": "候補E1",
                            "coordinates": [139.75, 35.69],
                            "recordId": "node/5",
                            "distanceMeters": 1.0,
                            "tags": {"name": "候補E1", "operator": "法人E"},
                        },
                        {
                            "type": "way",
                            "id": "6",
                            "name": "候補E2",
                            "coordinates": [139.7501, 35.6901],
                            "recordId": "way/6",
                            "distanceMeters": 12.0,
                            "tags": {"name": "候補E2", "amenity": "social_facility"},
                        },
                    ],
                }
            ],
        }
        calls = []

        def voter(query, perspective):
            calls.append((query, perspective))
            return {"decision": "reject", "candidateId": None}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "imports/openstreetmap").mkdir(parents=True)
            (root / "imports/wam").mkdir(parents=True)
            (root / "reports").mkdir()
            (root / "imports/openstreetmap/normalized.json").write_text(
                json.dumps({"records": []}), encoding="utf-8"
            )
            (root / "reports/osm-candidates.json").write_text(
                json.dumps(report), encoding="utf-8"
            )
            (root / "imports/wam/normalized.json").write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "queryId": query_id,
                                "id": "A0001",
                                "sourceRecordIds": ["A0001"],
                                "name": "施設E",
                                "coordinates": [139.75, 35.69],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "imports/wam/raw.json").write_text(
                json.dumps(
                    {
                        "version": "202603",
                        "rows": [
                            {
                                "sourceRecordId": "A0001",
                                "name": "施設E",
                                "attributes": {"法人の名称": "法人E"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            resolve_osm_candidates(root, voter)
            resolved = json.loads((root / "reports/osm-candidates.json").read_text())

        self.assertEqual(list(REVIEW_PERSPECTIVES), [perspective for _, perspective in calls])
        self.assertTrue(all(len(query["candidates"]) == 2 for query, _ in calls))
        self.assertTrue(all(query["candidates"][0]["tags"]["operator"] == "法人E" for query, _ in calls))
        self.assertTrue(
            all(
                query["target"]["wam"]["rows"][0]["attributes"]["法人の名称"]
                == "法人E"
                for query, _ in calls
            )
        )
        self.assertEqual(
            list(REVIEW_PERSPECTIVES),
            [vote["perspective"] for vote in resolved["queries"][0]["llmVotes"]],
        )

    def test_links_or_rejects_by_two_votes_and_queues_only_no_consensus(self):
        report = {
            "version": "2026-07-29T00:00:00Z",
            "queries": [
                {
                    "queryId": "019c0000-0000-7000-8000-000000000201",
                    "name": "施設A",
                    "status": "candidates",
                    "candidates": [
                        {
                            "type": "node",
                            "id": "1",
                            "name": "候補A",
                            "coordinates": [139.75, 35.69],
                            "recordId": "node/1",
                            "distanceMeters": 12.0,
                        }
                    ],
                },
                {
                    "queryId": "019c0000-0000-7000-8000-000000000202",
                    "name": "施設B",
                    "status": "candidates",
                    "candidates": [
                        {
                            "type": "way",
                            "id": "2",
                            "name": "別施設",
                            "coordinates": [139.76, 35.70],
                            "recordId": "way/2",
                            "distanceMeters": 8.0,
                        }
                    ],
                },
                {
                    "queryId": "019c0000-0000-7000-8000-000000000203",
                    "name": "施設C",
                    "status": "ambiguous",
                    "candidates": [
                        {
                            "type": "node",
                            "id": "3",
                            "name": "候補C",
                            "coordinates": [139.77, 35.71],
                            "recordId": "node/3",
                            "distanceMeters": 4.0,
                        }
                    ],
                },
                {
                    "queryId": "019c0000-0000-7000-8000-000000000204",
                    "name": "施設D",
                    "status": "none",
                    "candidates": [],
                },
                {
                    "queryId": "019c0000-0000-7000-8000-000000000205",
                    "name": "施設E",
                    "status": "candidates",
                    "candidates": [
                        {
                            "type": "node",
                            "id": "1",
                            "name": "候補A",
                            "coordinates": [139.75, 35.69],
                            "recordId": "node/1",
                            "distanceMeters": 12.0,
                        }
                    ],
                },
            ],
        }
        votes = {
            report["queries"][0]["queryId"]: [
                {"decision": "link", "candidateId": "node/1"},
                {"decision": "link", "candidateId": "node/1"},
                {"decision": "review", "candidateId": None},
            ],
            report["queries"][1]["queryId"]: [
                {"decision": "reject", "candidateId": None},
                {"decision": "reject", "candidateId": None},
                {"decision": "review", "candidateId": None},
            ],
            report["queries"][2]["queryId"]: [
                {"decision": "link", "candidateId": "node/3"},
                {"decision": "reject", "candidateId": None},
                {"decision": "review", "candidateId": None},
            ],
            report["queries"][4]["queryId"]: [
                {"decision": "link", "candidateId": "node/1"},
                {"decision": "link", "candidateId": "node/1"},
                {"decision": "review", "candidateId": None},
            ],
        }

        def voter(query, _perspective):
            return votes[query["queryId"]].pop(0)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "imports/openstreetmap").mkdir(parents=True)
            (root / "reports").mkdir()
            (root / "imports/openstreetmap/normalized.json").write_text(
                json.dumps({"records": []}), encoding="utf-8"
            )
            (root / "reports/osm-candidates.json").write_text(
                json.dumps(report), encoding="utf-8"
            )

            resolve_osm_candidates(root, voter)

            normalized = json.loads(
                (root / "imports/openstreetmap/normalized.json").read_text()
            )
            resolved = json.loads((root / "reports/osm-candidates.json").read_text())
            review = json.loads((root / "reports/osm-review-needed.json").read_text())

        self.assertEqual(1, len(normalized["records"]))
        self.assertEqual("node/1", f"{normalized['records'][0]['type']}/{normalized['records'][0]['id']}")
        self.assertEqual("language_model", normalized["records"][0]["matchBasis"])
        statuses = {item["queryId"]: item["status"] for item in resolved["queries"]}
        self.assertEqual("linked_llm", statuses["019c0000-0000-7000-8000-000000000201"])
        self.assertEqual("rejected_llm", statuses["019c0000-0000-7000-8000-000000000202"])
        self.assertEqual("needs_review", statuses["019c0000-0000-7000-8000-000000000203"])
        self.assertEqual("none", statuses["019c0000-0000-7000-8000-000000000204"])
        self.assertEqual("needs_review", statuses["019c0000-0000-7000-8000-000000000205"])
        self.assertEqual(
            [
                "019c0000-0000-7000-8000-000000000203",
                "019c0000-0000-7000-8000-000000000205",
            ],
            [item["queryId"] for item in review["queries"]],
        )


if __name__ == "__main__":
    unittest.main()
