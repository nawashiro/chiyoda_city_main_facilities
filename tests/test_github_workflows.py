import unittest
from pathlib import Path


class GithubWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def workflow(self, name):
        return (self.root / ".github/workflows" / name).read_text(encoding="utf-8")

    def workflow_artifact_paths(self, workflow):
        paths = []
        lines = workflow.splitlines()
        for index, line in enumerate(lines):
            if not line.lstrip().startswith("path:"):
                continue
            path_indent = len(line) - len(line.lstrip())
            for candidate in lines[index + 1 :]:
                if not candidate.strip():
                    continue
                candidate_indent = len(candidate) - len(candidate.lstrip())
                if candidate_indent <= path_indent:
                    break
                paths.append(candidate.strip())
        return paths

    def test_jsonld_only_ci_workflows_do_not_reference_legacy_artifacts(self):
        workflow_names = (
            "validate.yml",
            "update-osm.yml",
            "update-wam.yml",
            "reidentify-sources.yml",
            "apply-osm-review.yml",
        )
        legacy_paths = (
            "places.geojson",
            "manifest.json",
            "data/registry.json",
            "dist/public/",
        )

        for name in workflow_names:
            workflow = self.workflow(name)
            with self.subTest(workflow=name):
                for path in legacy_paths:
                    self.assertFalse(
                        path in workflow,
                        f"{name} references legacy workflow path {path}",
                    )

    def test_validate_workflow_reproduces_only_canonical_jsonld(self):
        workflow = self.workflow("validate.yml")
        commands = (
            "cp data/places.jsonld /tmp/places.jsonld",
            "python3 -m src.facility_data build .",
            "cmp /tmp/places.jsonld data/places.jsonld",
        )

        for command in commands:
            self.assertTrue(
                command in workflow,
                f"validate.yml is missing canonical reproducibility command: {command}",
            )

        self.assertEqual(
            ["cmp /tmp/places.jsonld data/places.jsonld"],
            [
                line.strip()
                for line in workflow.splitlines()
                if line.strip().startswith("cmp ")
            ],
            "validate.yml must compare only data/places.jsonld bytes",
        )
        self.assertLess(
            workflow.index(commands[0]),
            workflow.index(commands[1]),
            "validate.yml must copy JSON-LD before building",
        )
        self.assertLess(
            workflow.index(commands[1]),
            workflow.index(commands[2]),
            "validate.yml must compare JSON-LD after building",
        )

    def test_update_and_review_artifacts_use_canonical_jsonld(self):
        workflow_names = (
            "update-osm.yml",
            "update-wam.yml",
            "reidentify-sources.yml",
            "apply-osm-review.yml",
        )
        workflows = {name: self.workflow(name) for name in workflow_names}

        for name, workflow in workflows.items():
            with self.subTest(workflow=name):
                self.assertTrue(
                    "data/places.jsonld" in workflow,
                    f"{name} does not reference the canonical JSON-LD artifact",
                )

        artifact_workflow_names = (
            "update-osm.yml",
            "update-wam.yml",
            "reidentify-sources.yml",
        )
        for name in artifact_workflow_names:
            with self.subTest(artifact_workflow=name):
                self.assertIn(
                    "data/places.jsonld",
                    self.workflow_artifact_paths(workflows[name]),
                    f"{name} artifact paths omit data/places.jsonld",
                )

    def test_osm_update_creates_review_issue_from_uploaded_run_artifact(self):
        workflow = self.workflow("update-osm.yml")
        self.assertIn("issues: write", workflow)
        self.assertIn("osm-update-${{ github.run_id }}", workflow)
        self.assertIn("src.github_osm_review build", workflow)
        self.assertIn("--prepare", workflow)
        self.assertIn("reports/osm-review-needed.yaml", workflow)
        self.assertIn("automation/osm-review-${{ github.run_id }}", workflow)
        self.assertIn("pull-request-branch", workflow)
        self.assertIn("actions/github-script@v7", workflow)
        self.assertIn("github.rest.issues.create", workflow)
        self.assertIn('--decision-at "$DECISION_AT"', workflow)
        self.assertIn("cp data/places.jsonld /tmp/places.jsonld", workflow)
        self.assertIn("python3 -m src.facility_data build .", workflow)
        self.assertIn("python3 -m src.fac_cli jsonld-validate data/places.jsonld", workflow)
        self.assertIn("cmp /tmp/places.jsonld data/places.jsonld", workflow)

    def test_checked_review_issue_downloads_exact_artifact_and_opens_pull_request(self):
        workflow = self.workflow("apply-osm-review.yml")
        self.assertIn("issues:", workflow)
        self.assertIn("types: [edited]", workflow)
        self.assertIn("github.event.issue.state == 'open'", workflow)
        self.assertIn("github.event.issue.labels.*.name", workflow)
        self.assertIn("osm-human-review", workflow)
        self.assertIn("group: osm-review-${{ github.event.issue.number }}", workflow)
        self.assertIn("cancel-in-progress: true", workflow)
        self.assertIn("osm-apply", workflow)
        self.assertIn("src.github_osm_review metadata", workflow)
        self.assertIn("gh run download", workflow)
        self.assertIn("src.github_osm_review apply", workflow)
        self.assertIn("cp /tmp/osm-review-needed.yaml reports/osm-review-needed.yaml", workflow)
        self.assertIn("src.facility_data update", workflow)
        self.assertIn("peter-evans/create-pull-request@v7", workflow)
        self.assertIn("cp data/places.jsonld /tmp/places.jsonld", workflow)
        self.assertIn("python3 -m src.facility_data build .", workflow)
        self.assertIn("python3 -m src.fac_cli jsonld-validate data/places.jsonld", workflow)
        self.assertIn("cmp /tmp/places.jsonld data/places.jsonld", workflow)
        self.assertIn("python3 -m unittest discover", workflow)
        self.assertIn("src.facility_data validate", workflow)

    def test_reidentify_workflow_uses_retained_raw_without_retrieval_commands(self):
        workflow = self.workflow("reidentify-sources.yml")
        self.assertIn("workflow_dispatch", workflow)
        self.assertIn("src.reidentify_sources", workflow)
        self.assertIn("src.resolve_osm_candidates", workflow)
        self.assertIn("--source wam", workflow)
        self.assertIn("--source openstreetmap", workflow)
        self.assertIn("--sync-search-names", workflow)
        self.assertEqual(2, workflow.count('--decision-at "$PROCESSED_AT"'))
        self.assertIn("src.github_osm_review build", workflow)
        self.assertNotIn("src.retrieve_wam", workflow)
        self.assertIn("cp data/places.jsonld /tmp/places.jsonld", workflow)
        self.assertIn("python3 -m src.facility_data build .", workflow)
        self.assertIn("python3 -m src.fac_cli jsonld-validate data/places.jsonld", workflow)
        self.assertIn("cmp /tmp/places.jsonld data/places.jsonld", workflow)
        self.assertNotIn("src.retrieve_osm", workflow)
        self.assertNotIn("curl ", workflow)

    def test_update_osm_builds_issue_from_the_reviewed_report_after_branch_creation(self):
        workflow = self.workflow("update-osm.yml")

        self.assertIn("cp reports/osm-candidates.json /tmp/osm-candidates.json", workflow)
        self.assertIn("--report /tmp/osm-candidates.json", workflow)

    def test_merged_osm_review_production_pr_closes_its_draft_review_pr(self):
        apply_workflow = self.workflow("apply-osm-review.yml")
        cleanup_path = self.root / ".github/workflows" / "close-osm-review-draft.yml"

        self.assertIn("<!-- osm-review-source:", apply_workflow)
        self.assertTrue(cleanup_path.is_file())
        cleanup_workflow = cleanup_path.read_text(encoding="utf-8")
        self.assertIn("pull_request:", cleanup_workflow)
        self.assertIn("types: [closed]", cleanup_workflow)
        self.assertIn("github.event.pull_request.merged == true", cleanup_workflow)
        self.assertIn("- uses: actions/checkout@v4", cleanup_workflow)
        self.assertIn("reviewPullRequestNumber", apply_workflow)
        self.assertIn("closeRecordedDraftReview", cleanup_workflow)
        self.assertIn("scripts/close_osm_review_draft.js", cleanup_workflow)


if __name__ == "__main__":
    unittest.main()
