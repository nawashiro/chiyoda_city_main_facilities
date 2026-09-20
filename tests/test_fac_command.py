import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_JSONLD = ROOT / "data/places.jsonld"
PUBLIC_JSONLD = ROOT / "site/places.jsonld"
README = ROOT / "README.md"


def run_fac(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["./fac", *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def tracked_diff() -> bytes:
    return subprocess.run(
        ["git", "diff", "--binary", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


class FacCommandTests(unittest.TestCase):
    def test_fac_validates_canonical_jsonld_from_repository_root(self):
        result = run_fac("jsonld-validate", "data/places.jsonld")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)

    def test_fac_help_exposes_maintainer_commands(self):
        result = run_fac("--help")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("build", result.stdout)
        self.assertIn("verify", result.stdout)

    def test_build_synchronizes_public_copy_byte_for_byte(self):
        canonical_bytes = CANONICAL_JSONLD.read_bytes()
        original_public_bytes = PUBLIC_JSONLD.read_bytes()
        try:
            PUBLIC_JSONLD.write_bytes(b"stale public copy\n")

            result = run_fac("build")

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(canonical_bytes, PUBLIC_JSONLD.read_bytes())
        finally:
            PUBLIC_JSONLD.write_bytes(original_public_bytes)

    def test_build_with_invalid_canonical_keeps_existing_public_copy(self):
        original_canonical_bytes = CANONICAL_JSONLD.read_bytes()
        original_public_bytes = PUBLIC_JSONLD.read_bytes()
        try:
            CANONICAL_JSONLD.write_bytes(b"{ this is not valid JSON-LD\n")
            PUBLIC_JSONLD.write_bytes(b"existing public copy must survive\n")
            public_before_build = PUBLIC_JSONLD.read_bytes()

            result = run_fac("build")

            self.assertNotEqual(0, result.returncode)
            self.assertEqual(public_before_build, PUBLIC_JSONLD.read_bytes())
        finally:
            CANONICAL_JSONLD.write_bytes(original_canonical_bytes)
            PUBLIC_JSONLD.write_bytes(original_public_bytes)

    def test_verify_succeeds_without_changing_tracked_files(self):
        tracked_before_verify = tracked_diff()

        result = run_fac("verify")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(tracked_before_verify, tracked_diff())

    def test_verify_rejects_stale_public_copy_without_synchronizing_it(self):
        original_public_bytes = PUBLIC_JSONLD.read_bytes()
        try:
            PUBLIC_JSONLD.write_bytes(b"stale public copy\n")
            stale_public_bytes = PUBLIC_JSONLD.read_bytes()

            result = run_fac("verify")

            self.assertNotEqual(0, result.returncode)
            self.assertEqual(stale_public_bytes, PUBLIC_JSONLD.read_bytes())
        finally:
            PUBLIC_JSONLD.write_bytes(original_public_bytes)

    def test_verify_fails_when_git_diff_check_reports_whitespace_error(self):
        original_readme_bytes = README.read_bytes()
        try:
            README.write_bytes(original_readme_bytes + b"\ntrailing whitespace \n")

            result = run_fac("verify")

            self.assertNotEqual(0, result.returncode)
            self.assertIn("git diff --check", result.stdout + result.stderr)
        finally:
            README.write_bytes(original_readme_bytes)


if __name__ == "__main__":
    unittest.main()
