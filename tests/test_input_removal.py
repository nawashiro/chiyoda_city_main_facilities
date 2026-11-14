import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src import fac_cli
from src.facility_data import new_uuid7

CONTEXT = {"@version": 1.1, "schema": "https://schema.org/", "rdfs": "http://www.w3.org/2000/01/rdf-schema#"}


def place(identifier):
    return {"@id": f"urn:uuid:{identifier}", "@type": ["schema:Place"],
            "schema:geo": {"@type": "schema:GeoCoordinates", "schema:longitude": 139.75, "schema:latitude": 35.69},
            "rdfs:seeAlso": ["https://www.openstreetmap.org/node/7"]}


class InputRemovalTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.removed, self.kept = new_uuid7(), new_uuid7()
        (self.root / "inputs").mkdir()
        (self.root / "data").mkdir()
        (self.root / "inputs/facilities.json").write_text(json.dumps({"queries": [
            {"id": self.removed, "name": "日本ハリストス正教会修道院", "coordinates": [139.7650572, 35.6981854]},
            {"id": self.kept, "name": "ニコライ堂", "qid": "Q2660430"},
        ]}, ensure_ascii=False), encoding="utf-8")
        self.places = {"@context": CONTEXT, "@graph": [place(self.removed), place(self.kept)]}
        (self.root / "data/places.jsonld").write_text(json.dumps(self.places, ensure_ascii=False), encoding="utf-8")
        (self.root / "data/osm-decisions.json").write_text(json.dumps({"version": 1, "facilities": {
            self.removed: {"status": "decided", "choice": "way/67027576"},
            self.kept: {"status": "decided", "choice": "relation/4080936"},
        }}, ensure_ascii=False), encoding="utf-8")

    def test_rm_removes_query_place_and_ledger_entry(self):
        result = fac_cli.main(["in", "rm", str(self.root), self.removed])
        self.assertEqual(0, result)
        self.assertEqual([{"id": self.kept, "name": "ニコライ堂", "qid": "Q2660430"}],
                         json.loads((self.root / "inputs/facilities.json").read_text(encoding="utf-8"))["queries"])
        self.assertEqual([place(self.kept)], json.loads((self.root / "data/places.jsonld").read_text(encoding="utf-8"))["@graph"])
        self.assertEqual({self.kept}, set(json.loads((self.root / "data/osm-decisions.json").read_text(encoding="utf-8"))["facilities"]))

    def test_rm_also_updates_the_published_copy(self):
        (self.root / "site").mkdir()
        (self.root / "site/places.jsonld").write_text(json.dumps(self.places, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(0, fac_cli.main(["in", "rm", str(self.root), self.removed]))
        self.assertEqual([place(self.kept)], json.loads((self.root / "site/places.jsonld").read_text(encoding="utf-8"))["@graph"])

    def test_rm_without_a_matching_query_fails(self):
        self.assertEqual(1, fac_cli.main(["in", "rm", str(self.root), new_uuid7()]))
        self.assertEqual(2, len(json.loads((self.root / "data/places.jsonld").read_text(encoding="utf-8"))["@graph"]))


if __name__ == "__main__":
    unittest.main()
