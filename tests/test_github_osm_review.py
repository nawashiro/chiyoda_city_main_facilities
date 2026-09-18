import base64
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.github_osm_review import (
    apply_yaml_selections,
    build_issue_document,
    build_review_yaml,
    main,
    parse_issue_metadata,
)


class GithubOsmReviewTests(unittest.TestCase):
    def review_report(self):
        return {
            "version": "2026-07-29T00:00:00Z",
            "queries": [
                {
                    "queryId": "019c0000-0000-7000-8000-000000000301",
                    "name": "施設A",
                    "target": {
                        "id": "019c0000-0000-7000-8000-000000000301",
                        "name": "施設A",
                        "coordinates": [139.75, 35.69],
                    },
                    "status": "needs_review",
                    "llmVotes": [
                        {"perspective": "visitor", "decision": "link", "candidateId": "node/1"},
                        {"perspective": "user", "decision": "reject", "candidateId": None},
                        {"perspective": "staff", "decision": "review", "candidateId": None},
                    ],
                    "candidates": [
                        {
                            "type": "node",
                            "id": "1",
                            "name": "候補A",
                            "coordinates": [139.7501, 35.6901],
                            "recordId": "node/1",
                            "distanceMeters": 12.0,
                            "tags": {
                                "name": "候補A",
                                "operator": "法人A",
                                "contact:phone": "03-0000-0000",
                            },
                        },
                        {
                            "type": "way",
                            "id": "2",
                            "name": "候補B",
                            "coordinates": [139.7502, 35.6902],
                            "recordId": "way/2",
                            "distanceMeters": 18.0,
                            "tags": {"name": "候補B", "amenity": "library"},
                        },
                    ],
                }
            ],
        }

    def test_rejects_legacy_issue_body_candidate_selection(self):
        report = self.review_report()
        payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()

        # API assumption for the cutover: legacy calls fail explicitly rather than
        # returning an Issue body that exposes candidate-selection controls.
        with self.assertRaisesRegex(ValueError, "candidate selection.*disabled"):
            build_issue_document(
                report,
                run_id="12345",
                artifact_name="osm-update-12345",
                report_sha256=hashlib.sha256(payload).hexdigest(),
            )

    def test_keeps_branch_pr_issue_body_yaml_only(self):
        report = self.review_report()
        payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()

        issue = build_issue_document(
            report,
            run_id="12345",
            artifact_name="osm-update-12345",
            report_sha256=hashlib.sha256(payload).hexdigest(),
            review_branch="automation/osm-review-12345",
            review_pull_request_number=42,
        )

        if issue is None:
            self.fail("branch+PR review should produce an Issue document")
        body = issue["body"]
        edit_url = (
            "https://github.com/nawashiro/chiyoda_city_main_facilities"
            "/edit/automation/osm-review-12345/reports/osm-review-needed.yaml"
        )
        self.assertEqual(1, body.count(edit_url))
        self.assertEqual(1, body.count("/edit/"))
        self.assertEqual(1, body.count("]("))
        self.assertEqual(1, body.count("<!-- osm-apply -->"))
        self.assertIn("- [ ] <!-- osm-apply -->", body)
        checkbox_lines = [line for line in body.splitlines() if line.startswith("- [")]
        self.assertEqual(1, len(checkbox_lines))
        self.assertNotIn("osm-candidates.json", body)
        self.assertNotIn("osm-candidates", body)
        self.assertNotIn(".json", body)
        self.assertNotIn("candidateId", body)
        self.assertNotIn("recordId", body)
        self.assertNotIn("osm-choice:", body)
        self.assertNotIn("候補の全属性", body)
        self.assertNotIn("候補なし（どの候補とも一致しない）", body)
        for candidate in report["queries"][0]["candidates"]:
            self.assertNotIn(candidate["name"], body)
            self.assertNotIn(candidate["recordId"], body)
        self.assertNotIn("contact:phone", body)

    def test_applies_exactly_one_yaml_choice_after_artifact_hash_validation(self):
        report = self.review_report()
        payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
        report_sha = hashlib.sha256(payload).hexdigest()
        review_yaml = build_review_yaml(report, report_sha256=report_sha).replace(
            '"候補 node/1: 候補A": false', '"候補 node/1: 候補A": true'
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "reports").mkdir()
            (root / "imports/openstreetmap").mkdir(parents=True)
            (root / "reports/osm-candidates.json").write_bytes(payload)
            (root / "imports/openstreetmap/normalized.json").write_text(
                json.dumps({"records": []}), encoding="utf-8"
            )

            result = apply_yaml_selections(
                root,
                review_yaml,
                issue_url="https://github.com/example/repo/issues/7",
            )
            normalized = json.loads(
                (root / "imports/openstreetmap/normalized.json").read_text()
            )
            updated_report = json.loads(
                (root / "reports/osm-candidates.json").read_text()
            )

        self.assertEqual(report_sha, result["reportSha256"])
        self.assertEqual(
            [
                {
                    "queryId": "019c0000-0000-7000-8000-000000000301",
                    "decision": "link",
                    "candidateId": "node/1",
                }
            ],
            result["choices"],
        )
        self.assertEqual("human_review", normalized["records"][0]["matchBasis"])
        self.assertEqual("node/1", f"{normalized['records'][0]['type']}/{normalized['records'][0]['id']}")
        self.assertEqual("linked_human", updated_report["queries"][0]["status"])
        self.assertEqual(
            "https://github.com/example/repo/issues/7",
            updated_report["queries"][0]["humanReview"]["issueUrl"],
        )

    def test_rejects_an_incomplete_yaml_selection(self):
        report = self.review_report()
        payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
        review_yaml = build_review_yaml(
            report, report_sha256=hashlib.sha256(payload).hexdigest()
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "reports").mkdir()
            (root / "imports/openstreetmap").mkdir(parents=True)
            (root / "reports/osm-candidates.json").write_bytes(payload)
            (root / "imports/openstreetmap/normalized.json").write_text(
                json.dumps({"records": []}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "exactly one YAML option"):
                apply_yaml_selections(root, review_yaml, issue_url="https://example/7")

    def test_rejects_an_artifact_with_a_different_hash(self):
        report = self.review_report()
        payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
        review_yaml = build_review_yaml(
            report, report_sha256=hashlib.sha256(payload).hexdigest()
        ).replace('"候補 node/1: 候補A": false', '"候補 node/1: 候補A": true')

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "reports").mkdir()
            (root / "imports/openstreetmap").mkdir(parents=True)
            (root / "reports/osm-candidates.json").write_bytes(payload + b" ")
            (root / "imports/openstreetmap/normalized.json").write_text(
                json.dumps({"records": []}), encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "does not match the reviewed artifact"):
                apply_yaml_selections(root, review_yaml, issue_url="https://example/7")

    def test_rejects_same_osm_candidate_selected_for_multiple_queries(self):
        report = self.review_report()
        second = copy.deepcopy(report["queries"][0])
        second["queryId"] = "019c0000-0000-7000-8000-000000000302"
        second["name"] = "施設B"
        second["target"] = {
            "id": second["queryId"],
            "name": second["name"],
            "coordinates": [139.75, 35.69],
        }
        report["queries"].append(second)
        payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
        review_yaml = build_review_yaml(
            report, report_sha256=hashlib.sha256(payload).hexdigest()
        ).replace('"候補 node/1: 候補A": false', '"候補 node/1: 候補A": true')
        self.assertEqual(2, review_yaml.count('"候補 node/1: 候補A": true'))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "reports").mkdir()
            (root / "imports/openstreetmap").mkdir(parents=True)
            (root / "reports/osm-candidates.json").write_bytes(payload)
            (root / "imports/openstreetmap/normalized.json").write_text(
                json.dumps({"records": []}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "duplicate current OSM recordId"):
                apply_yaml_selections(root, review_yaml, issue_url="https://example/7")

    def test_builds_compact_issue_and_editable_yaml_for_an_oversized_review(self):
        report = self.review_report()
        report["queries"][0]["candidates"][0]["tags"]["oversized"] = "x" * 70000

        report["queries"][0]["reviewReason"] = {
            "code": "candidate_already_linked",
            "conflictingQueryId": "019c0000-0000-7000-8000-000000000302",
            "conflictingQueryName": "施設B",
        }
        review_yaml = build_review_yaml(report, report_sha256="0" * 64)
        issue = build_issue_document(
            report,
            run_id="12345",
            artifact_name="osm-update-12345",
            report_sha256="0" * 64,
            review_branch="automation/osm-review-12345",
            review_pull_request_number=42,
        )

        metadata = parse_issue_metadata(issue["body"])

        self.assertIn("# 操作手順", review_yaml)
        self.assertIn('"候補 node/1: 候補A": false', review_yaml)
        self.assertIn('"候補なし（どの候補とも一致しない）": false', review_yaml)
        self.assertIn("候補は別の施設に紐付け済み", review_yaml)
        self.assertIn("施設B", review_yaml)
        self.assertNotIn("contact:phone", review_yaml)
        self.assertNotIn("oversized", review_yaml)
        self.assertNotIn("検索入力:", review_yaml)
        self.assertNotIn("候補の詳細:", review_yaml)
        self.assertLess(len(issue["body"]), 65_536)
        self.assertIn('/edit/automation/osm-review-12345/reports/osm-review-needed.yaml', issue["body"])
        self.assertNotIn("osm-candidates.json", issue["body"])
        self.assertNotIn("oversized", issue["body"])
        self.assertEqual(4, metadata["schemaVersion"])
        self.assertEqual(42, metadata["reviewPullRequestNumber"])
        self.assertEqual("automation/osm-review-12345", metadata["reviewBranch"])

    def test_rejects_invalid_issue_metadata_shapes(self):
        valid = {
            "schemaVersion": 4,
            "runId": "12345",
            "artifactName": "osm-update-12345",
            "reportSha256": "0" * 64,
            "queryIds": ["019c0000-0000-7000-8000-000000000301"],
            "reviewBranch": "automation/osm-review-12345",
            "reviewPullRequestNumber": 42,
        }
        invalid_documents = [
            {**valid, "schemaVersion": 9},
            {**valid, "runId": "not-a-run"},
            {**valid, "artifactName": ""},
            {**valid, "reportSha256": "0" * 63},
            {**valid, "reviewBranch": ""},
            {**valid, "reviewPullRequestNumber": 0},
            {**valid, "unexpected": True},
        ]

        for document in invalid_documents:
            with self.subTest(document=document):
                encoded = json.dumps(document, separators=(",", ":")).encode()
                marker = base64.urlsafe_b64encode(encoded).decode().rstrip("=")
                with self.assertRaisesRegex(ValueError, "OSM review"):
                    parse_issue_metadata(f"<!-- osm-review-metadata:{marker} -->")

    def test_prepare_build_writes_yaml_without_rendering_an_oversized_issue(self):
        report = self.review_report()
        report["queries"][0]["candidates"][0]["tags"]["oversized"] = "x" * 70000
        payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "reports").mkdir()
            (root / "reports/osm-candidates.json").write_text(payload, encoding="utf-8")
            output = root / "review.json"

            result = main(
                [
                    "build", root.as_posix(), "--run-id", "12345", "--artifact-name",
                    "osm-update-12345", "--prepare", "--output", output.as_posix(),
                ]
            )
            document = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(0, result)
        self.assertTrue(document["reviewNeeded"])

    def test_build_uses_explicit_report_after_the_worktree_changes_branch(self):
        reviewed_report = self.review_report()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "reports").mkdir()
            (root / "reports/osm-candidates.json").write_text(
                json.dumps({"queries": []}), encoding="utf-8"
            )
            reviewed_path = root / "reviewed-osm-candidates.json"
            reviewed_path.write_text(json.dumps(reviewed_report), encoding="utf-8")
            output = root / "issue.json"

            result = main(
                [
                    "build", root.as_posix(), "--run-id", "12345", "--artifact-name",
                    "osm-update-12345", "--review-branch", "automation/osm-review-12345",
                    "--review-pull-request-number", "42", "--report", reviewed_path.as_posix(), "--output", output.as_posix(),
                ]
            )
            document = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(0, result)
        self.assertEqual(1, len(document["issues"]))

    def test_applies_choices_from_review_yaml_after_artifact_hash_validation(self):
        report = self.review_report()
        payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
        review_yaml = build_review_yaml(
            report, report_sha256=hashlib.sha256(payload).hexdigest()
        ).replace('"候補 node/1: 候補A": false', '"候補 node/1: 候補A": true')

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "reports").mkdir()
            (root / "imports/openstreetmap").mkdir(parents=True)
            (root / "reports/osm-candidates.json").write_bytes(payload)
            (root / "imports/openstreetmap/normalized.json").write_text(
                json.dumps({"records": []}), encoding="utf-8"
            )

            result = apply_yaml_selections(
                root,
                review_yaml,
                issue_url="https://github.com/example/repo/issues/7",
            )
            normalized = json.loads(
                (root / "imports/openstreetmap/normalized.json").read_text()
            )

        self.assertEqual("human_review", normalized["records"][0]["matchBasis"])
        self.assertEqual("node/1", f"{normalized['records'][0]['type']}/{normalized['records'][0]['id']}")
        self.assertEqual(hashlib.sha256(payload).hexdigest(), result["reportSha256"])


if __name__ == "__main__":
    unittest.main()
