import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.github_osm_review import apply_yaml_selections, build_review_yaml, main


class GithubOsmReviewTests(unittest.TestCase):
    def review_report(self):
        return {
            "version": "2026-07-29T00:00:00Z",
            "queries": [
                {
                    "queryId": "019c0000-0000-7000-8000-000000000301",
                    "name": "施設A",
                    "target": {"id": "019c0000-0000-7000-8000-000000000301", "name": "施設A", "coordinates": [139.75, 35.69]},
                    "status": "needs_review",
                    "candidates": [
                        {"type": "node", "id": "1", "name": "候補A", "coordinates": [139.7501, 35.6901], "recordId": "node/1", "distanceMeters": 12.0, "tags": {"name": "候補A"}},
                        {"type": "way", "id": "2", "name": "候補B", "coordinates": [139.7502, 35.6902], "recordId": "way/2", "distanceMeters": 18.0, "tags": {"name": "候補B"}},
                    ],
                }
            ],
        }

    def write_artifact(self, root, payload):
        (root / "reports").mkdir()
        (root / "imports/openstreetmap").mkdir(parents=True)
        (root / "reports/osm-candidates.json").write_bytes(payload)
        (root / "imports/openstreetmap/normalized.json").write_text(json.dumps({"records": []}), encoding="utf-8")

    def test_builds_yaml_without_any_issue_document(self):
        report = self.review_report()
        payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "reports").mkdir()
            (root / "reports/osm-candidates.json").write_text(payload, encoding="utf-8")
            output = root / "review.json"
            result = main(["build", root.as_posix(), "--output", output.as_posix()])
            document = json.loads(output.read_text(encoding="utf-8"))
            review_yaml = (root / "reports/osm-review-needed.yaml").read_text(encoding="utf-8")
        self.assertEqual(0, result)
        self.assertEqual({"reviewNeeded": True}, document)
        self.assertIn("レビューPull Requestをmerge", review_yaml)
        self.assertNotIn("Issue", review_yaml)
        self.assertNotIn("osm-apply", review_yaml)

    def test_applies_exactly_one_committed_yaml_choice_after_artifact_hash_validation(self):
        report = self.review_report()
        payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
        report_sha = hashlib.sha256(payload).hexdigest()
        review_yaml = build_review_yaml(report, report_sha256=report_sha).replace('"候補 node/1: 候補A": false', '"候補 node/1: 候補A": true')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_artifact(root, payload)
            result = apply_yaml_selections(root, review_yaml, review_url="https://github.com/example/repo/pull/7")
            normalized = json.loads((root / "imports/openstreetmap/normalized.json").read_text())
            updated_report = json.loads((root / "reports/osm-candidates.json").read_text())
        self.assertEqual(report_sha, result["reportSha256"])
        self.assertEqual("human_review", normalized["records"][0]["matchBasis"])
        self.assertEqual("node/1", f"{normalized['records'][0]['type']}/{normalized['records'][0]['id']}")
        self.assertEqual("linked_human", updated_report["queries"][0]["status"])
        self.assertEqual("https://github.com/example/repo/pull/7", updated_report["queries"][0]["humanReview"]["reviewUrl"])

    def test_rejects_an_incomplete_yaml_selection(self):
        report = self.review_report()
        payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
        review_yaml = build_review_yaml(report, report_sha256=hashlib.sha256(payload).hexdigest())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_artifact(root, payload)
            with self.assertRaisesRegex(ValueError, "exactly one YAML option"):
                apply_yaml_selections(root, review_yaml, review_url="https://example/7")

    def test_rejects_an_artifact_with_a_different_hash(self):
        report = self.review_report()
        payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
        review_yaml = build_review_yaml(report, report_sha256=hashlib.sha256(payload).hexdigest()).replace('"候補 node/1: 候補A": false', '"候補 node/1: 候補A": true')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_artifact(root, payload + b" ")
            with self.assertRaisesRegex(ValueError, "does not match the reviewed artifact"):
                apply_yaml_selections(root, review_yaml, review_url="https://example/7")

    def test_rejects_same_osm_candidate_selected_for_multiple_queries(self):
        report = self.review_report()
        second = copy.deepcopy(report["queries"][0])
        second["queryId"] = "019c0000-0000-7000-8000-000000000302"
        second["name"] = "施設B"
        report["queries"].append(second)
        payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
        review_yaml = build_review_yaml(report, report_sha256=hashlib.sha256(payload).hexdigest()).replace('"候補 node/1: 候補A": false', '"候補 node/1: 候補A": true')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_artifact(root, payload)
            with self.assertRaisesRegex(ValueError, "duplicate current OSM recordId"):
                apply_yaml_selections(root, review_yaml, review_url="https://example/7")


if __name__ == "__main__":
    unittest.main()
