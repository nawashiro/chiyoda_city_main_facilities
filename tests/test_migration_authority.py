import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY_SPEC = "docs/reference/data-maintenance-spec.md"
MIGRATION_CHANGE = "adopt-standards-jsonld"
MIGRATION_CHANGE_PATH = f"openspec/changes/{MIGRATION_CHANGE}"


class MigrationAuthorityTests(unittest.TestCase):
    def test_deleted_maintenance_spec_is_absent(self):
        self.assertFalse(
            (ROOT / LEGACY_SPEC).exists(),
            f"deleted maintenance spec still exists: {LEGACY_SPEC}",
        )

    def test_readme_and_use_specify_identify_openspec_migration_authority(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        use_specify = (ROOT / "docs/how-to/use-specify.md").read_text(encoding="utf-8")

        self.assertIn(
            MIGRATION_CHANGE_PATH,
            readme,
            "README.md must link to the adopt-standards-jsonld OpenSpec change",
        )
        self.assertIn(
            MIGRATION_CHANGE_PATH,
            use_specify,
            "use-specify.md must link to the adopt-standards-jsonld OpenSpec change",
        )
        self.assertIn(
            MIGRATION_CHANGE,
            use_specify,
            "use-specify.md must name the migration OpenSpec change",
        )
        self.assertRegex(
            use_specify,
            re.compile(r"移行の判断記録|migration\s+(?:authority|decision\s+record)", re.IGNORECASE),
            "use-specify.md must identify the OpenSpec change as the migration authority",
        )

    def test_readme_and_markdown_docs_do_not_reference_deleted_spec(self):
        markdown_paths = [ROOT / "README.md"]
        markdown_paths.extend(sorted((ROOT / "docs").rglob("*.md")))

        for path in markdown_paths:
            relative_path = path.relative_to(ROOT)
            with self.subTest(document=str(relative_path)):
                self.assertNotIn(
                    LEGACY_SPEC,
                    path.read_text(encoding="utf-8"),
                    f"{relative_path} still references {LEGACY_SPEC}",
                )


if __name__ == "__main__":
    unittest.main()
