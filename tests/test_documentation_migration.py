import re
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PAGES_URL = "https://nawashiro.github.io/chiyoda_city_main_facilities/"
PAGES_JSONLD_URL = f"{PAGES_URL}places.jsonld"
JSONLD_VALIDATE_COMMAND = "python3 -m src.fac_cli jsonld-validate data/places.jsonld"

DOCUMENT_PATHS = (
    "README.md",
    "docs/explanation/data-model.md",
    "docs/how-to/update-source-data.md",
    "docs/how-to/source-update-checklist.md",
    "docs/how-to/use-specify.md",
    "docs/how-to/maintain-a-place.md",
    "docs/tutorials/first-data-change.md",
    "docs/reference/attributes.md",
    "docs/reference/cli.md",
)

LEGACY_REFERENCES = (
    "data/registry.json",
    "dist/public/places.geojson",
    "places.geojson",
    "manifest.json",
    "src.retrieve_towns",
    "update-towns.yml",
    "docs/reference/data-maintenance-spec.md",
)

MARKDOWN_LINK = re.compile(
    r"(?<!!)\[[^\]]+\]\(\s*(?:<([^>]+)>|([^\s)]+))[^)]*\)"
)
DIRECT_EDITING = re.compile(
    r"(?:直接.{0,12}編集|direct(?:ly)?\s+(?:edit|editing|editable))",
    re.IGNORECASE,
)


def relative_markdown_links(markdown: str) -> list[str]:
    """Return repository-relative Markdown link paths outside code spans."""
    without_fenced_code = re.sub(r"```.*?```", "", markdown, flags=re.DOTALL)
    without_inline_code = re.sub(r"`[^`\n]*`", "", without_fenced_code)

    links = []
    for match in MARKDOWN_LINK.finditer(without_inline_code):
        target = match.group(1) or match.group(2)
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or target.startswith("#"):
            continue
        path = unquote(parsed.path)
        if not path or path.startswith("/"):
            continue
        links.append(path)
    return links


class DocumentationMigrationTests(unittest.TestCase):
    def read_document(self, relative_path: str) -> str:
        path = ROOT / relative_path
        self.assertTrue(path.is_file(), f"missing required document: {relative_path}")
        return path.read_text(encoding="utf-8")

    def test_required_migration_documents_exist(self):
        for relative_path in DOCUMENT_PATHS:
            with self.subTest(document=relative_path):
                self.assertTrue(
                    (ROOT / relative_path).is_file(),
                    f"missing required document: {relative_path}",
                )

    def test_migration_documents_do_not_reference_legacy_paths_or_commands(self):
        for relative_path in DOCUMENT_PATHS:
            document = self.read_document(relative_path)
            for legacy_reference in LEGACY_REFERENCES:
                with self.subTest(document=relative_path, legacy=legacy_reference):
                    self.assertFalse(
                        legacy_reference in document,
                        f"{relative_path} still references {legacy_reference}",
                    )

    def test_readme_describes_canonical_source_validation_and_acquisition(self):
        readme = self.read_document("README.md")
        for required_text in (
            "data/places.jsonld",
            "jsonld-validate",
            PAGES_URL,
            PAGES_JSONLD_URL,
            "GitHub Release",
            "current JSON-LD",
        ):
            with self.subTest(text=required_text):
                self.assertTrue(
                    required_text in readme,
                    f"README.md must mention {required_text!r}",
                )

    def test_data_model_and_source_update_docs_describe_jsonld_validation(self):
        source_documents = (
            "docs/explanation/data-model.md",
            "docs/how-to/update-source-data.md",
            "docs/how-to/source-update-checklist.md",
        )
        for relative_path in source_documents:
            document = self.read_document(relative_path)
            with self.subTest(document=relative_path):
                self.assertTrue(
                    "data/places.jsonld" in document,
                    f"{relative_path} must mention data/places.jsonld",
                )
                self.assertTrue(
                    JSONLD_VALIDATE_COMMAND in document,
                    f"{relative_path} must mention {JSONLD_VALIDATE_COMMAND}",
                )

    def test_cli_reference_documents_jsonld_validation_without_town_option(self):
        cli_reference = self.read_document("docs/reference/cli.md")
        self.assertTrue(
            "jsonld-validate" in cli_reference,
            "docs/reference/cli.md must mention jsonld-validate",
        )
        self.assertFalse(
            "--town" in cli_reference,
            "docs/reference/cli.md must not mention --town",
        )

    def test_tutorial_and_place_maintenance_explain_direct_canonical_editing(self):
        tutorial_documents = (
            "docs/tutorials/first-data-change.md",
            "docs/how-to/maintain-a-place.md",
        )
        for relative_path in tutorial_documents:
            document = self.read_document(relative_path)
            with self.subTest(document=relative_path):
                self.assertTrue(
                    "data/places.jsonld" in document,
                    f"{relative_path} must mention data/places.jsonld",
                )
                self.assertTrue(
                    JSONLD_VALIDATE_COMMAND in document,
                    f"{relative_path} must mention {JSONLD_VALIDATE_COMMAND}",
                )
                self.assertTrue(
                    DIRECT_EDITING.search(document),
                    f"{relative_path} must explain direct canonical JSON-LD editing",
                )

    def test_attributes_reference_documents_standard_jsonld_terms(self):
        attributes = self.read_document("docs/reference/attributes.md")
        self.assertTrue(
            "schema:PropertyValue" in attributes,
            "docs/reference/attributes.md must mention schema:PropertyValue",
        )
        self.assertTrue(
            "geo:geoJSONLiteral" in attributes,
            "docs/reference/attributes.md must mention geo:geoJSONLiteral",
        )

    def test_readme_relative_markdown_links_target_existing_files(self):
        readme = self.read_document("README.md")
        links = relative_markdown_links(readme)
        self.assertTrue(links, "README must contain relative Markdown links")

        for link in links:
            with self.subTest(link=link):
                self.assertTrue(
                    (ROOT / link).is_file(),
                    f"README link target does not exist: {link}",
                )


if __name__ == "__main__":
    unittest.main()
