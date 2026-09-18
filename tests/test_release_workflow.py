import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleaseWorkflowTests(unittest.TestCase):
    def _workflow_step_containing(self, workflow, marker):
        lines = workflow.splitlines()
        for index, line in enumerate(lines):
            if marker not in line:
                continue
            step_indent = len(line) - len(line.lstrip())
            step_lines = [line]
            for candidate in lines[index + 1 :]:
                if candidate.strip():
                    candidate_indent = len(candidate) - len(candidate.lstrip())
                    if candidate_indent <= step_indent and candidate.lstrip().startswith("-"):
                        break
                step_lines.append(candidate)
            return "\n".join(step_lines)
        return ""

    def test_release_workflow_publishes_jsonld_snapshots(self):
        workflow_path = ROOT / ".github/workflows/release-jsonld.yml"
        self.assertTrue(
            workflow_path.is_file(),
            f"missing release workflow: {workflow_path}",
        )
        workflow = workflow_path.read_text(encoding="utf-8")

        self.assertIn("release:", workflow)
        self.assertIn("types: [published]", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertRegex(workflow, r"dry[-_]run")

        self.assertRegex(
            workflow,
            r"(?m)^.*jsonld-validate.*data/places\.jsonld.*$",
        )

        artifact_step = self._workflow_step_containing(
            workflow, "actions/upload-artifact@"
        )
        self.assertTrue(artifact_step, "workflow must upload a run artifact")
        self.assertRegex(
            artifact_step,
            r"\.jsonld",
            "run artifact upload must include a JSON-LD file",
        )

        self.assertRegex(
            workflow,
            r"(?m)^\s*-?\s*uses:\s*"
            r"(?:softprops/action-gh-release|ncipollo/release-action|"
            r"actions/upload-release-asset)@[^\s]+",
            "workflow must use a GitHub Release upload action",
        )

        for legacy_reference in (
            "places.geojson",
            "manifest.json",
            "data/registry.json",
            "dist/public",
        ):
            with self.subTest(legacy_reference=legacy_reference):
                self.assertNotIn(legacy_reference, workflow)

    def test_prepare_release_jsonld_preserves_canonical_bytes(self):
        script = ROOT / "scripts/prepare_release_jsonld.py"
        canonical = ROOT / "data/places.jsonld"
        self.assertTrue(script.is_file(), f"missing release preparation script: {script}")
        self.assertTrue(canonical.is_file(), f"missing canonical JSON-LD source: {canonical}")
        canonical_bytes = canonical.read_bytes()
        version = "v2026.09.18"

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            output_dir = temporary_root / "release"
            output_dir.mkdir()
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--input",
                    str(canonical),
                    "--output-dir",
                    str(output_dir),
                    "--version",
                    version,
                ],
                cwd=temporary_root,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            outputs = sorted(
                path for path in output_dir.rglob("*.jsonld") if path.is_file()
            )
            self.assertEqual(1, len(outputs), "release dry-run must produce one JSON-LD snapshot")
            self.assertEqual("places-v2026.09.18.jsonld", outputs[0].name)
            self.assertEqual(canonical_bytes, outputs[0].read_bytes())

        self.assertEqual(canonical_bytes, canonical.read_bytes())


if __name__ == "__main__":
    unittest.main()
