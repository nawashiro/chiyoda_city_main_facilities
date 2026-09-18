import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DATASET_URL = "https://nawashiro.github.io/chiyoda_city_main_facilities/"


class DatasetPublicationTests(unittest.TestCase):
    def test_pages_landing_page_exposes_dataset_jsonld_metadata(self):
        landing_page = ROOT / "site/index.html"
        self.assertTrue(
            landing_page.is_file(),
            f"missing GitHub Pages landing page: {landing_page}",
        )

        html = landing_page.read_text(encoding="utf-8")
        match = re.search(
            r'<script\b[^>]*\s+type\s*=\s*["\']application/ld\+json["\'][^>]*>'
            r"(.*?)"
            r"</script>",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if match is None:
            self.fail("landing page must contain an application/ld+json script")

        metadata = json.loads(match.group(1).strip())
        self.assertIsInstance(metadata, dict)
        self.assertEqual("https://schema.org", metadata.get("@context"))
        self.assertIn(metadata.get("@type"), ("schema:Dataset", "Dataset"))

        for field in ("name", "description", "url"):
            value = metadata.get(field)
            with self.subTest(field=field):
                self.assertIsInstance(value, str)
                self.assertTrue(value.strip())

        self.assertEqual(EXPECTED_DATASET_URL, metadata["url"])


if __name__ == "__main__":
    unittest.main()
