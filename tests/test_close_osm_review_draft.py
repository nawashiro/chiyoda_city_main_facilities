import json
import subprocess
import unittest
from pathlib import Path


class CloseOsmReviewDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.script = cls.root / "scripts/close_osm_review_draft.js"

    def close(self, *, body, pull, base_ref="main"):
        runner = """
const { closeRecordedDraftReview } = require(process.argv[1]);
const input = JSON.parse(process.argv[2]);
const calls = { get: [], update: [], info: [], warning: [] };
const github = { rest: { pulls: {
  get: async (args) => { calls.get.push(args); return { data: input.pull }; },
  update: async (args) => { calls.update.push(args); },
} } };
const core = {
  info: (message) => calls.info.push(message),
  warning: (message) => calls.warning.push(message),
};
closeRecordedDraftReview({
  body: input.body,
  baseRef: input.baseRef,
  owner: 'example',
  repo: 'facilities',
  github,
  core,
}).then(() => process.stdout.write(JSON.stringify(calls))).catch((error) => {
  console.error(error);
  process.exit(1);
});
"""
        completed = subprocess.run(
            ["node", "-e", runner, self.script.as_posix(), json.dumps({
                "body": body,
                "pull": pull,
                "baseRef": base_ref,
            })],
            cwd=self.root,
            check=True,
            text=True,
            capture_output=True,
        )
        return json.loads(completed.stdout)

    @staticmethod
    def marker(**overrides):
        source = {
            "schemaVersion": 1,
            "issueNumber": 7,
            "reviewPullRequestNumber": 42,
            "reviewBranch": "automation/osm-review-12345",
            **overrides,
        }
        return f"<!-- osm-review-source:{json.dumps(source, separators=(',', ':'))} -->"

    @staticmethod
    def matching_pull(**overrides):
        return {
            "state": "open",
            "draft": True,
            "head": {"ref": "automation/osm-review-12345"},
            "base": {"ref": "main"},
            **overrides,
        }

    def test_closes_only_the_open_matching_draft_review_pull_request(self):
        calls = self.close(body=self.marker(), pull=self.matching_pull())

        self.assertEqual([{"owner": "example", "repo": "facilities", "pull_number": 42}], calls["get"])
        self.assertEqual(
            [{"owner": "example", "repo": "facilities", "pull_number": 42, "state": "closed"}],
            calls["update"],
        )

    def test_does_not_load_or_close_a_pull_request_for_an_invalid_marker(self):
        calls = self.close(body=self.marker(reviewBranch="wrong-branch"), pull=self.matching_pull())

        self.assertEqual([], calls["get"])
        self.assertEqual([], calls["update"])
        self.assertEqual(1, len(calls["warning"]))

    def test_does_not_close_a_nonmatching_review_pull_request(self):
        cases = [
            self.matching_pull(state="closed"),
            self.matching_pull(draft=False),
            self.matching_pull(head={"ref": "automation/osm-review-999"}),
            self.matching_pull(base={"ref": "release"}),
        ]

        for pull in cases:
            with self.subTest(pull=pull):
                calls = self.close(body=self.marker(), pull=pull)
                self.assertEqual([], calls["update"])


if __name__ == "__main__":
    unittest.main()
