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

    def test_osm_update_creates_review_pr_from_uploaded_run_artifact(self):
        workflow = self.workflow("update-osm.yml")
        self.assertIn("osm-update-${{ github.run_id }}", workflow)
        self.assertIn("src.github_osm_review build", workflow)
        self.assertIn("reports/osm-review-needed.yaml", workflow)
        self.assertIn("automation/osm-review-osm-update-${{ github.run_id }}", workflow)
        self.assertIn("commit済みYAMLと元artifactを照合", workflow)
        self.assertNotIn("issues: write", workflow)
        self.assertNotIn("github.rest.issues", workflow)
        self.assertNotIn("osm-apply", workflow)
        self.assertIn('--decision-at "$DECISION_AT"', workflow)
        self.assertIn("cp data/places.jsonld /tmp/places.jsonld", workflow)
        self.assertIn("python3 -m src.facility_data build .", workflow)
        self.assertIn("python3 -m src.fac_cli jsonld-validate data/places.jsonld", workflow)
        self.assertIn("cmp /tmp/places.jsonld data/places.jsonld", workflow)

    def test_merged_review_pr_is_the_only_osm_apply_route(self):
        workflow = self.workflow("apply-osm-review.yml")

        self.assertIn("pull_request:", workflow)
        self.assertIn("types: [closed]", workflow)
        self.assertIn("github.event.pull_request.merged == true", workflow)
        self.assertIn("github.head_ref", workflow)
        self.assertIn("automation/osm-review-", workflow)
        self.assertNotIn("issues:", workflow)
        self.assertNotIn("github.event.issue", workflow)
        self.assertNotIn("osm-apply", workflow)
        self.assertNotIn("src.github_osm_review metadata", workflow)
        self.assertNotIn("src.github_osm_review apply ", workflow)
        self.assertIn("gh run download", workflow)
        self.assertIn("src.github_osm_review apply-yaml", workflow)
        self.assertIn("reports/osm-review-needed.yaml", workflow)
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
        self.assertIn("automation/osm-review-reidentify-update-${{ github.run_id }}", workflow)
        self.assertNotIn("issues: write", workflow)
        self.assertNotIn("github.rest.issues", workflow)
        self.assertNotIn("src.retrieve_wam", workflow)
        self.assertIn("cp data/places.jsonld /tmp/places.jsonld", workflow)
        self.assertIn("python3 -m src.facility_data build .", workflow)
        self.assertIn("python3 -m src.fac_cli jsonld-validate data/places.jsonld", workflow)
        self.assertIn("cmp /tmp/places.jsonld data/places.jsonld", workflow)
        self.assertNotIn("src.retrieve_osm", workflow)
        self.assertNotIn("curl ", workflow)

    def test_update_osm_does_not_build_an_issue_after_review_pr_creation(self):
        workflow = self.workflow("update-osm.yml")

        self.assertNotIn("Build compact Issue", workflow)
        self.assertNotIn("github.rest.issues", workflow)
        self.assertNotIn("osm-apply", workflow)

    def test_external_updates_are_action_only_and_create_reviewable_prs_without_raw_review(self):
        osm_workflow = self.workflow("update-osm.yml")
        wam_workflow = self.workflow("update-wam.yml")
        update_docs = (
            ("update-osm.md", (self.root / "docs/how-to/update-osm.md").read_text(encoding="utf-8")),
            ("update-wam.md", (self.root / "docs/how-to/update-wam.md").read_text(encoding="utf-8")),
        )

        self.assertIn("src.retrieve_osm", osm_workflow)
        self.assertIn('_verified_snapshot(Path("."), "openstreetmap")', osm_workflow)
        self.assertIn("add-paths: reports/osm-review-needed.yaml", osm_workflow)
        self.assertIn("peter-evans/create-pull-request@v7", wam_workflow)
        self.assertIn('_verified_snapshot(Path("."), "wam")', wam_workflow)
        self.assertIn("contents: write", wam_workflow)
        self.assertIn("pull-requests: write", wam_workflow)
        self.assertIn("automation/wam-update-${{ github.run_id }}", wam_workflow)
        self.assertNotIn("manual review", wam_workflow.lower())

        prohibited = ("RAW_JSON", "生データを確認", "src.update_osm", "update_wam.py")
        for name, document in update_docs:
            with self.subTest(document=name):
                for text in prohibited:
                    self.assertNotIn(text, document)
                self.assertIn("GitHub Actions", document)
                self.assertIn("Pull Request", document)
                self.assertIn("SHA-256", document)

    def test_merged_osm_review_pr_needs_no_issue_or_draft_cleanup_marker(self):
        apply_workflow = self.workflow("apply-osm-review.yml")

        self.assertNotIn("osm-review-source", apply_workflow)
        self.assertNotIn("github.event.issue", apply_workflow)
        self.assertIn("github.event.pull_request.html_url", apply_workflow)


if __name__ == "__main__":
    unittest.main()
