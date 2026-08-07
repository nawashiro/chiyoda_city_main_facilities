import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.facility_data import search_input_sha256
from src.reidentify_sources import prepare_retained_reidentification
from src.wam_contract import WAM_PUBLIC_ATTRIBUTE_HEADERS


def json_bytes(document):
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode()


class ReidentifySourcesTests(unittest.TestCase):
    def make_repository(self, root: Path):
        query_id = "019c0000-0000-7000-8000-000000000401"
        (root / "inputs/osm-search/manual").mkdir(parents=True)
        (root / "imports/wam").mkdir(parents=True)
        (root / "imports/openstreetmap").mkdir(parents=True)
        (root / "data").mkdir()
        (root / "reports").mkdir()
        (root / "inputs/osm-search/manual/facilities.json").write_bytes(
            json_bytes(
                {
                    "source": {"kind": "human", "sourceId": None, "retrievedAt": None},
                    "queries": [
                        {
                            "id": query_id,
                            "name": "修正後の施設名",
                            "coordinates": [139.75, 35.69],
                        }
                    ],
                }
            )
        )
        (root / "data/registry.json").write_bytes(
            json_bytes({"schemaVersion": 1, "places": []})
        )
        wam_row = {
            "sourceRecordId": "A0001",
            "officeId": "1310100001",
            "serviceCode": "52",
            "serviceType": "計画相談支援",
            "name": "修正後の施設名",
            "coordinates": [139.75, 35.69],
            "attributes": {header: "" for header in WAM_PUBLIC_ATTRIBUTE_HEADERS},
        }
        wam_raw = {"version": "202603", "rows": [wam_row]}
        wam_payload = json_bytes(wam_raw)
        (root / "imports/wam/raw.json").write_bytes(wam_payload)
        (root / "imports/wam/retrieval.json").write_bytes(
            json_bytes(
                {
                    "sourceId": "wam",
                    "retrievedAt": "2026-04-16T00:00:00Z",
                    "rawVersion": "202603",
                    "rawSha256": hashlib.sha256(wam_payload).hexdigest(),
                }
            )
        )
        osm_raw = {
            "version": "2026-07-29T00:00:00Z",
            "elements": [
                {
                    "type": "node",
                    "id": 10,
                    "lon": 139.7501,
                    "lat": 35.6901,
                    "tags": {
                        "name": "別名の候補",
                        "operator": "運営法人",
                        "custom:all": "全属性を保持",
                    },
                }
            ],
        }
        osm_payload = json_bytes(osm_raw)
        (root / "imports/openstreetmap/raw.json").write_bytes(osm_payload)
        (root / "imports/openstreetmap/retrieval.json").write_bytes(
            json_bytes(
                {
                    "sourceId": "openstreetmap",
                    "retrievedAt": "2026-07-29T01:00:00Z",
                    "rawVersion": "2026-07-29T00:00:00Z",
                    "rawSha256": hashlib.sha256(osm_payload).hexdigest(),
                }
            )
        )
        return query_id

    def test_rebuilds_wam_and_osm_identification_without_changing_retained_raw(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            query_id = self.make_repository(root)
            before = {
                path: (root / path).read_bytes()
                for path in (
                    "imports/wam/raw.json",
                    "imports/wam/retrieval.json",
                    "imports/openstreetmap/raw.json",
                    "imports/openstreetmap/retrieval.json",
                )
            }

            result = prepare_retained_reidentification(root)

            after = {path: (root / path).read_bytes() for path in before}
            wam = json.loads((root / "imports/wam/normalized.json").read_text())
            osm = json.loads((root / "reports/osm-candidates.json").read_text())

        self.assertEqual(before, after)
        self.assertEqual(query_id, wam["records"][0]["queryId"])
        self.assertEqual(query_id, osm["queries"][0]["target"]["id"])
        self.assertEqual("全属性を保持", osm["queries"][0]["candidates"][0]["tags"]["custom:all"])
        self.assertEqual("2026-04-16T00:00:00Z", result["wamRetrievedAt"])
        self.assertEqual("2026-07-29T01:00:00Z", result["osmRetrievedAt"])

    def test_keeps_osm_outputs_when_search_input_and_current_osm_id_are_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            query_id = self.make_repository(root)
            query = json.loads(
                (root / "inputs/osm-search/manual/facilities.json").read_text()
            )["queries"][0]
            (root / "data/registry.json").write_bytes(
                json_bytes(
                    {
                        "schemaVersion": 1,
                        "places": [
                            {
                                "id": query_id,
                                "externalRefs": [
                                    {
                                        "sourceId": "openstreetmap",
                                        "recordId": "node/10",
                                        "status": "current",
                                    }
                                ],
                                "audit": [
                                    {
                                        "at": "2026-07-01T00:00:00Z",
                                        "method": "calculation_model",
                                        "action": "linked_osm",
                                        "target": "node/10",
                                        "searchInputSha256": search_input_sha256(query),
                                    }
                                ],
                            }
                        ],
                    }
                )
            )
            normalized = json_bytes({"version": "retained", "records": [{"queryId": query_id, "id": "10"}]})
            report = json_bytes({"version": "retained", "queries": []})
            (root / "imports/openstreetmap/normalized.json").write_bytes(normalized)
            (root / "reports/osm-candidates.json").write_bytes(report)

            prepare_retained_reidentification(root)

            self.assertEqual(normalized, (root / "imports/openstreetmap/normalized.json").read_bytes())
            self.assertEqual(report, (root / "reports/osm-candidates.json").read_bytes())

    def test_keeps_unlinked_query_when_search_input_and_raw_osm_hash_are_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            query_id = self.make_repository(root)
            query = json.loads(
                (root / "inputs/osm-search/manual/facilities.json").read_text()
            )["queries"][0]
            raw_sha256 = json.loads(
                (root / "imports/openstreetmap/retrieval.json").read_text()
            )["rawSha256"]
            normalized = json_bytes(
                {"version": "retained", "records": [{"queryId": query_id, "id": "10"}]}
            )
            report = json_bytes(
                {
                    "version": "retained",
                    "rawSha256": raw_sha256,
                    "queries": [
                        {
                            "queryId": query_id,
                            "target": query,
                            "status": "none",
                            "candidates": [],
                        }
                    ],
                }
            )
            (root / "imports/openstreetmap/normalized.json").write_bytes(normalized)
            (root / "reports/osm-candidates.json").write_bytes(report)

            prepare_retained_reidentification(root)

            self.assertEqual(normalized, (root / "imports/openstreetmap/normalized.json").read_bytes())
            self.assertEqual(report, (root / "reports/osm-candidates.json").read_bytes())

    def test_reidentifies_only_query_with_changed_search_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            query_id = self.make_repository(root)
            document_path = root / "inputs/osm-search/manual/facilities.json"
            document = json.loads(document_path.read_text())
            stable_query = document["queries"][0]
            changed_query = {
                "id": "019c0000-0000-7000-8000-000000000402",
                "name": "再同定する施設",
                "coordinates": [139.7502, 35.6902],
            }
            document["queries"].append(changed_query)
            document_path.write_bytes(json_bytes(document))
            registry = {
                "schemaVersion": 1,
                "places": [
                    {
                        "id": query_id,
                        "name": stable_query["name"],
                        "geometry": {"type": "Point", "coordinates": [139.75, 35.69]},
                        "externalRefs": [{"sourceId": "openstreetmap", "recordId": "node/10", "status": "current"}],
                        "audit": [{"at": "2026-07-01T00:00:00Z", "method": "calculation_model", "action": "linked_osm", "target": "node/10", "searchInputSha256": search_input_sha256(stable_query)}],
                    }
                ],
            }
            (root / "data/registry.json").write_bytes(json_bytes(registry))
            (root / "imports/openstreetmap/normalized.json").write_bytes(
                json_bytes(
                    {
                        "version": "retained",
                        "records": [
                            {
                                "queryId": query_id,
                                "matchBasis": "source_record",
                                "type": "node",
                                "id": "10",
                                "name": "別名の候補",
                                "coordinates": [139.7501, 35.6901],
                                "tags": {"name": "別名の候補"},
                            }
                        ],
                    }
                )
            )

            prepare_retained_reidentification(root)

            normalized = json.loads((root / "imports/openstreetmap/normalized.json").read_text())
            report = json.loads((root / "reports/osm-candidates.json").read_text())
        self.assertEqual([query_id], [record["queryId"] for record in normalized["records"]])
        self.assertEqual([changed_query["id"]], [query["queryId"] for query in report["queries"]])

    def test_rejects_tampered_raw_before_replacing_existing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            sentinel = json_bytes({"records": [{"sentinel": True}]})
            (root / "imports/wam/normalized.json").write_bytes(sentinel)
            (root / "imports/openstreetmap/raw.json").write_text("{}\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "OpenStreetMap rawSha256"):
                prepare_retained_reidentification(root)

            self.assertEqual(sentinel, (root / "imports/wam/normalized.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
