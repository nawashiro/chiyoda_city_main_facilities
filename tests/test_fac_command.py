import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
USER_FACING_MARKDOWN = (ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md")))


class FacCommandTests(unittest.TestCase):
    def test_fac_validates_canonical_jsonld_from_repository_root(self):
        result = subprocess.run(
            ["./fac", "jsonld-validate", "data/places.jsonld"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)

    def test_user_facing_markdown_uses_fac_instead_of_the_module_command(self):
        stale_examples = [
            str(path.relative_to(ROOT))
            for path in USER_FACING_MARKDOWN
            if "python3 -m src.fac_cli" in path.read_text(encoding="utf-8")
        ]

        self.assertEqual([], stale_examples)


if __name__ == "__main__":
    unittest.main()
