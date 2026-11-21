import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from src import facility_categories
from src.facility_data import build_repository

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DATASET_URL = "https://nawashiro.github.io/chiyoda_city_main_facilities/"
EXPECTED_DISTRIBUTION_URL = "https://nawashiro.github.io/chiyoda_city_main_facilities/dataset.jsonld"


def landing_metadata():
    html = (ROOT / "site/index.html").read_text(encoding="utf-8")
    match = re.search(
        r'<script\b[^>]*\s+type\s*=\s*["\']application/ld\+json["\'][^>]*>'
        r"(.*?)"
        r"</script>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        raise AssertionError("landing page must contain an application/ld+json script")
    return json.loads(match.group(1).strip())


def type_names(record):
    value = record.get("@type")
    return value if isinstance(value, list) else [value]


def place_nodes(document):
    return [record for record in document["@graph"] if "schema:Place" in type_names(record)]


def count_type(document, name):
    return sum(1 for record in document["@graph"] if name in type_names(record))


class DatasetPublicationTests(unittest.TestCase):
    def test_pages_landing_page_exposes_dataset_jsonld_metadata(self):
        metadata = landing_metadata()
        self.assertIsInstance(metadata, dict)
        self.assertEqual("https://schema.org", metadata.get("@context"))
        self.assertIn(metadata.get("@type"), ("schema:Dataset", "Dataset"))
        for field in ("name", "description", "url"):
            value = metadata.get(field)
            with self.subTest(field=field):
                self.assertIsInstance(value, str)
                self.assertTrue(value.strip())
        self.assertEqual(EXPECTED_DATASET_URL, metadata["url"])

    def test_build_publishes_dataset_graph_without_changing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            for name in ("places.jsonld", "category-vocabulary.jsonld", "dataset-shape.jsonld", "categories.json"):
                shutil.copyfile(ROOT / "data" / name, root / "data" / name)
            canonical = root / "data/places.jsonld"
            original = canonical.read_bytes()
            artifact = build_repository(root)
            self.assertEqual(root / "site/dataset.jsonld", artifact)
            self.assertEqual(original, canonical.read_bytes())
            published = json.loads(artifact.read_text(encoding="utf-8"))
            canonical_document = json.loads(original)
            self.assertEqual(len(place_nodes(canonical_document)), len(place_nodes(published)))
            self.assertEqual(1, count_type(published, "schema:DefinedTermSet"))
            vocabulary = facility_categories.load_vocabulary(root)
            self.assertEqual(len(vocabulary), count_type(published, "schema:DefinedTerm"))
            self.assertGreaterEqual(count_type(published, "sh:NodeShape"), 2)
            decisions = json.loads((root / "data/categories.json").read_text(encoding="utf-8"))["facilities"]
            by_id = {record["@id"]: record for record in place_nodes(published)}
            for record in place_nodes(canonical_document):
                published_record = by_id[record["@id"]]
                derived = ("schema:image", "schema:keywords")
                self.assertEqual(
                    {key: value for key, value in record.items() if key not in derived},
                    {key: value for key, value in published_record.items() if key not in derived},
                )
                entry = decisions.get(record["@id"].removeprefix("urn:uuid:"))
                if entry is None:
                    self.assertNotIn("schema:keywords", published_record)
                else:
                    self.assertEqual([{"@id": vocabulary[entry["category"]]["@id"]}], published_record["schema:keywords"])
                self.assertNotIn(
                    "gif-poi",
                    [item.get("schema:propertyID") for item in published_record.get("schema:identifier", [])],
                )
            first = artifact.read_bytes()
            build_repository(root)
            self.assertEqual(first, artifact.read_bytes(), "build must be deterministic")
            for stale in ("places.jsonld", "category-names.jsonld", "categories.jsonld"):
                self.assertFalse((root / "site" / stale).exists())

    def test_invalid_canonical_data_does_not_replace_published_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "site").mkdir()
            (root / "data/places.jsonld").write_text("{}", encoding="utf-8")
            artifact = root / "site/dataset.jsonld"
            artifact.write_bytes(b"previous publication")
            with self.assertRaises(ValueError):
                build_repository(root)
            self.assertEqual(b"previous publication", artifact.read_bytes())

    def test_pages_landing_page_exposes_jsonld_distribution(self):
        metadata = landing_metadata()
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
        self.assertTrue(data_downloads, "landing page dataset JSON-LD must include a DataDownload distribution")
        jsonld = [entry for entry in data_downloads if entry.get("encodingFormat") == "application/ld+json"]
        self.assertEqual([EXPECTED_DISTRIBUTION_URL], [entry.get("contentUrl") for entry in jsonld])
        self.assertNotIn(
            "category-names.jsonld",
            json.dumps(metadata, ensure_ascii=False),
            "the separate category dictionary distribution must be removed",
        )


if __name__ == "__main__":
    unittest.main()
