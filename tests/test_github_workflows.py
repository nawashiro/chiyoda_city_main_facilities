import unittest
from pathlib import Path


class GithubWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def workflow(self, name):
        return (self.root / ".github/workflows" / name).read_text(encoding="utf-8")

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
        self.assertIn("cmp /tmp/places.geojson dist/public/places.geojson", workflow)

    def test_checked_review_issue_downloads_exact_artifact_and_opens_pull_request(self):
        workflow = self.workflow("apply-osm-review.yml")
        self.assertIn("issues:", workflow)
        self.assertIn("types: [edited]", workflow)
        self.assertIn("osm-apply", workflow)
        self.assertIn("src.github_osm_review metadata", workflow)
        self.assertIn("gh run download", workflow)
        self.assertIn("src.github_osm_review apply", workflow)
        self.assertIn("src.facility_data update", workflow)
        self.assertIn("peter-evans/create-pull-request@v7", workflow)
        self.assertIn("cmp /tmp/places.geojson dist/public/places.geojson", workflow)
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
        self.assertIn("cmp /tmp/places.geojson dist/public/places.geojson", workflow)
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
        self.assertIn("reviewPullRequestNumber", apply_workflow)
        self.assertIn("pulls.get", cleanup_workflow)
        self.assertNotIn("pulls.list", cleanup_workflow)
        self.assertIn("pull.draft", cleanup_workflow)
        self.assertIn("pulls.update", cleanup_workflow)


if __name__ == "__main__":
    unittest.main()
