import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.facility_data import barrier_free_webpage, validate_jsonld_document


ROOT = Path(__file__).resolve().parents[1]
WEBPAGE = barrier_free_webpage("https://walkingnavi.com/list_route.php?grp=5&no=57")


def document():
    return {
        "@context": {"@version": 1.1, "schema": "https://schema.org/", "rdfs": "http://www.w3.org/2000/01/rdf-schema#"},
        "@graph": [{
            "@id": "urn:uuid:01900000-0000-7000-8000-000000000001",
            "@type": ["schema:Place"],
            "schema:geo": {"@type": "schema:GeoCoordinates", "schema:longitude": 139.75, "schema:latitude": 35.69},
            "schema:subjectOf": [copy.deepcopy(WEBPAGE)],
        }],
    }


class BarrierFreeLinkValidationTests(unittest.TestCase):
    def test_valid_webpage_is_accepted(self):
        validate_jsonld_document(document())

    def test_lwd_tokyo_with_text_fragment_is_accepted(self):
        doc = document()
        doc["@graph"][0]["schema:subjectOf"] = [
            barrier_free_webpage("https://www.lwd.tokyo/public#:~:text=%E5%8D%83%E4%BB%A3%E7%94%B0%E5%8C%BA%E5%BD%B9%E6%89%80")
        ]
        validate_jsonld_document(doc)

    def test_disallowed_domain_is_rejected(self):
        doc = document()
        doc["@graph"][0]["schema:subjectOf"] = [{"@type": "schema:WebPage", "schema:url": "https://example.com/page", "schema:name": "x", "schema:provider": {"@type": "schema:Organization", "schema:name": "x"}}]
        with self.assertRaises(ValueError):
            validate_jsonld_document(doc)

    def test_non_webpage_kind_is_rejected(self):
        doc = document()
        doc["@graph"][0]["schema:subjectOf"] = [
            {"@type": "schema:WebSite", "schema:url": WEBPAGE["schema:url"], "schema:name": WEBPAGE["schema:name"], "schema:provider": WEBPAGE["schema:provider"]}
        ]
        with self.assertRaises(ValueError):
            validate_jsonld_document(doc)

    def test_wrong_name_or_provider_for_domain_is_rejected(self):
        doc = document()
        doc["@graph"][0]["schema:subjectOf"] = [
            barrier_free_webpage("https://www.lwd.tokyo/public#:~:text=a")
        ]
        doc["@graph"][0]["schema:subjectOf"][0]["schema:name"] = "言葉の道案内"
        with self.assertRaises(ValueError):
            validate_jsonld_document(doc)

    def test_duplicate_url_is_rejected(self):
        doc = document()
        doc["@graph"][0]["schema:subjectOf"] = [copy.deepcopy(WEBPAGE), copy.deepcopy(WEBPAGE)]
        with self.assertRaises(ValueError):
            validate_jsonld_document(doc)


class FacLinkCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        (root / "data").mkdir()
        (root / "data/places.jsonld").write_text(json.dumps(document(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.root = root

    def fac(self, *argv):
        import subprocess
        return subprocess.run(["./fac", *argv], cwd=ROOT, capture_output=True, text=True, check=False)

    def test_add_and_rm_roundtrip(self):
        result = self.fac("link", "add", self.tmp.name, "01900000-0000-7000-8000-000000000001", "https://www.lwd.tokyo/public#:~:text=a")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        stored = json.loads((self.root / "data/places.jsonld").read_text())
        self.assertTrue("https://www.lwd.tokyo/public#:~:text=a" in [p["schema:url"] for p in stored["@graph"][0]["schema:subjectOf"]])
        result = self.fac("link", "rm", self.tmp.name, "01900000-0000-7000-8000-000000000001", "https://www.lwd.tokyo/public#:~:text=a")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        removed = json.loads((self.root / "data/places.jsonld").read_text())
        self.assertNotIn("https://www.lwd.tokyo/public#:~:text=a", [p["schema:url"] for p in removed["@graph"][0]["schema:subjectOf"]])

    def test_add_rejects_disallowed_domain(self):
        result = self.fac("link", "add", self.tmp.name, "01900000-0000-7000-8000-000000000001", "https://example.com/page")
        self.assertEqual(1, result.returncode)
        self.assertIn("ERROR", result.stdout)

    def test_add_twice_is_rejected(self):
        url = "https://walkingnavi.com/list_route.php?grp=5&no=999"
        self.assertEqual(0, self.fac("link", "add", self.tmp.name, "01900000-0000-7000-8000-000000000001", url).returncode)
        again = self.fac("link", "add", self.tmp.name, "01900000-0000-7000-8000-000000000001", url)
        self.assertEqual(1, again.returncode)

    def test_unknown_place_is_rejected(self):
        result = self.fac("link", "add", self.tmp.name, "01900000-0000-7000-8000-000000000009", WEBPAGE["schema:url"])
        self.assertEqual(1, result.returncode)


if __name__ == "__main__":
    unittest.main()
