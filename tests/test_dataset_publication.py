import json
import re
import tempfile
import shutil

from src.facility_data import build_repository
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DATASET_URL = "https://nawashiro.github.io/chiyoda_city_main_facilities/"
EXPECTED_DISTRIBUTION_URL = (
    "https://nawashiro.github.io/chiyoda_city_main_facilities/places.jsonld"
)


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

    def test_build_publishes_exact_canonical_bytes_without_changing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            canonical = root / "data/places.jsonld"
            shutil.copyfile(ROOT / "data/places.jsonld", canonical)
            original = canonical.read_bytes()
            artifact = build_repository(root)
            self.assertEqual(root / "site/places.jsonld", artifact)
            self.assertEqual(original, artifact.read_bytes())
            self.assertEqual(original, canonical.read_bytes())
            artifact.write_text("stale copy", encoding="utf-8")
            build_repository(root)
            self.assertEqual(original, artifact.read_bytes())
            self.assertEqual(original, canonical.read_bytes())

    def test_invalid_canonical_data_does_not_replace_published_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "site").mkdir()
            (root / "data/places.jsonld").write_text("{}", encoding="utf-8")
            artifact = root / "site/places.jsonld"
            artifact.write_bytes(b"previous publication")
            with self.assertRaises(ValueError):
                build_repository(root)
            self.assertEqual(b"previous publication", artifact.read_bytes())

    def test_pages_landing_page_exposes_jsonld_distribution(self):
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

        raw_distribution = metadata.get("distribution")
        if isinstance(raw_distribution, dict):
            distributions = [raw_distribution]
        elif isinstance(raw_distribution, list):
            distributions = raw_distribution
        else:
            distributions = []

        data_downloads = [
            entry
            for entry in distributions
            if isinstance(entry, dict)
            and entry.get("@type") in ("DataDownload", "schema:DataDownload")
        ]
        self.assertTrue(
            data_downloads,
            "landing page dataset JSON-LD must include a DataDownload distribution",
        )

        data_download = data_downloads[0]
        self.assertEqual(EXPECTED_DISTRIBUTION_URL, data_download.get("contentUrl"))
        self.assertEqual("application/ld+json", data_download.get("encodingFormat"))


if __name__ == "__main__":
    unittest.main()
