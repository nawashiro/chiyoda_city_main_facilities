import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleaseWorkflowTests(unittest.TestCase):
    def _on_block(self, workflow):
        head = workflow.split("permissions:", 1)[0]
        return head.split("on:", 1)[1]

    def test_release_workflow_publishes_frozen_distribution(self):
        workflow_path = ROOT / ".github/workflows/release.yml"
        self.assertTrue(
            workflow_path.is_file(),
            f"missing release workflow: {workflow_path}",
        )
        workflow = workflow_path.read_text(encoding="utf-8")

        self.assertNotIn("dry[-_]run", workflow)
        on_block = self._on_block(workflow)
        self.assertIn("workflow_dispatch:", on_block)
        self.assertRegex(on_block, r"(?m)^\s+workflow_dispatch:\s*$")

        self.assertRegex(
            workflow,
            r"(?m)^.*git ls-remote origin refs/heads/main.*$",
            "workflow must require the checked-out commit to be latest main",
        )
        self.assertRegex(
            workflow,
            r"(?m)^.*python3 -m unittest discover -s tests.*$",
        )
        self.assertRegex(
            workflow,
            r"(?m)^.*src\.facility_data build \..*$",
        )

        tag_step = self._workflow_step_containing(workflow, "%Y.%m.%d")
        self.assertTrue(tag_step, "workflow must derive the tag from the UTC date")
        self.assertRegex(tag_step, r"git ls-remote --exit-code --tags origin")
        self.assertRegex(tag_step, r"exit 1")

        self.assertRegex(
            workflow,
            r"(?m)^\s*-?\s*uses:\s*softprops/action-gh-release@[^\s]+$",
            "workflow must use a GitHub Release upload action",
        )

        for asset_marker in ("places-", "osm-", "wikidata-"):
            with self.subTest(asset_marker=asset_marker):
                self.assertIn(asset_marker, workflow)
        self.assertIn("files: release/*", workflow)
        for license_marker in ("ODbL", "CC0", "OpenStreetMap contributors"):
            with self.subTest(license_marker=license_marker):
                self.assertIn(license_marker, workflow)

        self.assertFalse(
            (ROOT / ".github/workflows/release-jsonld.yml").exists(),
            "the legacy release workflow must be removed",
        )

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


class PrepareReleaseTests(unittest.TestCase):
    def _run_prepare(self, site_dir, output_dir, version):
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/prepare_release.py"),
                "--site-dir",
                str(site_dir),
                "--output-dir",
                str(output_dir),
                "--version",
                version,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_prepare_release_copies_versioned_assets(self):
        script = ROOT / "scripts/prepare_release.py"
        canonical = ROOT / "data/places.jsonld"
        self.assertTrue(script.is_file(), f"missing release preparation script: {script}")
        self.assertTrue(canonical.is_file(), f"missing canonical JSON-LD source: {canonical}")
        canonical_bytes = canonical.read_bytes()
        version = "2026.11.14"
        expected = {
            "places-2026.11.14.jsonld": canonical_bytes,
            "osm-2026.11.14.json": b'{"elements": []}',
            "wikidata-2026.11.14.json": b'{"entities": {}}',
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            site_dir = temporary_root / "site"
            (site_dir / "mirrors").mkdir(parents=True)
            (site_dir / "places.jsonld").write_bytes(canonical_bytes)
            (site_dir / "mirrors/osm.json").write_bytes(expected["osm-2026.11.14.json"])
            (site_dir / "mirrors/wikidata.json").write_bytes(
                expected["wikidata-2026.11.14.json"]
            )
            output_dir = temporary_root / "release"
            completed = self._run_prepare(site_dir, output_dir, version)

            self.assertEqual(0, completed.returncode, completed.stderr)
            outputs = sorted(path for path in output_dir.iterdir() if path.is_file())
            self.assertEqual(
                sorted(expected), [path.name for path in outputs],
                "release must prepare three versioned assets",
            )
            for name, payload in expected.items():
                self.assertEqual(payload, (output_dir / name).read_bytes(), name)

        self.assertEqual(canonical_bytes, canonical.read_bytes())

    def test_prepare_release_rejects_invalid_version(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            site_dir = temporary_root / "site"
            (site_dir / "mirrors").mkdir(parents=True)
            (site_dir / "places.jsonld").write_bytes(
                (ROOT / "data/places.jsonld").read_bytes()
            )
            completed = self._run_prepare(site_dir, temporary_root / "release", "×invalid")

        self.assertNotEqual(0, completed.returncode)
        self.assertIn("invalid release version", completed.stderr)

    def test_prepare_release_fails_on_invalid_document(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            site_dir = temporary_root / "site"
            (site_dir / "mirrors").mkdir(parents=True)
            (site_dir / "places.jsonld").write_bytes(b"{}")
            (site_dir / "mirrors/osm.json").write_bytes(b"{}")
            (site_dir / "mirrors/wikidata.json").write_bytes(b"{}")
            output_dir = temporary_root / "release"
            completed = self._run_prepare(site_dir, output_dir, "2026.11.14")

        self.assertNotEqual(0, completed.returncode, completed.stdout)
        self.assertFalse(output_dir.exists(), "failed preparation must not write assets")


if __name__ == "__main__":
    unittest.main()
