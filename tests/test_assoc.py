import json
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src import fac_cli
from src.facility_data import new_uuid7
from src.resolve_osm_candidates import osm_candidate as real_osm_candidate

REPO = Path(__file__).resolve().parents[1]
CONTEXT = {"@version": 1.1, "schema": "https://schema.org/", "rdfs": "http://www.w3.org/2000/01/rdf-schema#"}


def osm_json(elements):
    return json.dumps({"version": "0.6", "generator": "test", "elements": elements}).encode()


class AssocTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.__enter_result__.name) if False else None
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        (self.root / "inputs").mkdir()
        self.query_id = new_uuid7()
        (self.root / "inputs/facilities.json").write_text(json.dumps({"queries": [{
            "id": self.query_id, "name": "テスト児童館", "coordinates": [139.736548, 35.688289],
        }]}, ensure_ascii=False), encoding="utf-8")
        self.places = {"@context": CONTEXT, "@graph": []}
        (self.root / "data/places.jsonld").write_text(json.dumps(self.places, ensure_ascii=False), encoding="utf-8")
        (self.root / "data/osm-decisions.json").write_text(json.dumps({"version": 1, "facilities": {}}), encoding="utf-8")

    def run_assoc(self, *args, elements):
        with patch("src.fac_cli.osm_candidate") as fetch_osm_candidate:
            fetch_osm_candidate.side_effect = lambda record_id, fetch=None: real_osm_candidate(record_id, fetch=lambda url: osm_json(elements()))
            return fac_cli.main(["assoc", str(self.root), self.query_id, "--editor", "tester", *args])

    def test_associates_node_as_human_decision(self):
        nodes = [{"type": "node", "id": 7, "lat": 35.6882993, "lon": 139.7365076,
                  "tags": {"name": "千代田区立テスト児童館", "amenity": "community_centre",
                           "website": "https://example.test/a.html", "check_date": "2026-11-03"}}]
        self.assertEqual(0, self.run_assoc("--osm-id", "node/7", elements=lambda: nodes))
        place = json.loads((self.root / "data/places.jsonld").read_text(encoding="utf-8"))["@graph"][0]
        self.assertEqual([f"https://www.openstreetmap.org/node/7"], place["rdfs:seeAlso"])
        self.assertEqual({"@type": "schema:GeoCoordinates", "schema:longitude": 139.7365076, "schema:latitude": 35.6882993}, place["schema:geo"])
        entry = json.loads((self.root / "data/osm-decisions.json").read_text(encoding="utf-8"))["facilities"][self.query_id]
        self.assertEqual("node/7", entry["choice"])
        self.assertEqual("human", entry["method"])
        self.assertEqual("tester", entry["human"]["editor"])
        self.assertEqual([{"recordId": "node/7", "name": "千代田区立テスト児童館", "coordinates": [139.7365076, 35.6882993],
                           "qid": None, "tags": {"amenity": "community_centre", "name": "千代田区立テスト児童館",
                                                 "website": "https://example.test/a.html"}}], entry["evidence"]["candidates"])

    def test_way_candidate_uses_member_centroid(self):
        elements = [{"type": "way", "id": 9, "tags": {"name": "テスト館", "building": "yes"},
                     "nodes": [1, 2]},
                    {"type": "node", "id": 1, "lat": 35.697, "lon": 139.746},
                    {"type": "node", "id": 2, "lat": 35.698, "lon": 139.747}]
        self.assertEqual(0, self.run_assoc("--osm-id", "way/9", elements=lambda: elements))
        entries = json.loads((self.root / "data/osm-decisions.json").read_text(encoding="utf-8"))["facilities"]
        [candidate] = entries[self.query_id]["evidence"]["candidates"]
        self.assertEqual("way/9", candidate["recordId"])
        self.assertEqual(139.7465, candidate["coordinates"][0])
        self.assertEqual(35.6975, candidate["coordinates"][1])
        self.assertEqual({"building": "yes", "name": "テスト館"}, candidate["tags"])

    def test_replaces_previous_choice(self):
        nodes = [{"type": "node", "id": 7, "lat": 35.6882993, "lon": 139.7365076, "tags": {"name": "旧"}}]
        self.run_assoc("--osm-id", "node/7", elements=lambda: nodes)
        other = [{"type": "node", "id": 8, "lat": 35.68829941, "lon": 139.73650761, "tags": {"name": "新"}}]
        self.assertEqual(0, self.run_assoc("--osm-id", "node/8", elements=lambda: other))
        place = json.loads((self.root / "data/places.jsonld").read_text(encoding="utf-8"))["@graph"][0]
        self.assertEqual(["https://www.openstreetmap.org/node/8"], place["rdfs:seeAlso"])
        ledger = json.loads((self.root / "data/osm-decisions.json").read_text(encoding="utf-8"))["facilities"]
        self.assertEqual("node/8", ledger[self.query_id]["current"])
        self.assertEqual("node/8", ledger[self.query_id]["human"]["choice"])

    def test_records_none_choice(self):
        self.assertEqual(0, self.run_assoc("--choice", "none", elements=lambda: []))
        place = json.loads((self.root / "data/places.jsonld").read_text(encoding="utf-8"))["@graph"]
        self.assertEqual([], place)
        entry = json.loads((self.root / "data/osm-decisions.json").read_text(encoding="utf-8"))["facilities"][self.query_id]
        self.assertEqual("none", entry["choice"])
        self.assertEqual([], entry["evidence"]["candidates"])
        self.assertIsNone(entry["current"])

    def test_missing_element_writes_nothing(self):
        before_places = (self.root / "data/places.jsonld").read_text(encoding="utf-8")
        result = self.run_assoc("--osm-id", "node/404", elements=lambda: [])
        self.assertEqual(1, result)
        self.assertEqual(before_places, (self.root / "data/places.jsonld").read_text(encoding="utf-8"))

    def test_nameless_element_is_refused(self):
        elements = [{"type": "node", "id": 7, "lat": 35.6882993, "lon": 139.7365076, "tags": {"amenity": "cafe"}}]
        self.assertEqual(1, self.run_assoc("--osm-id", "node/7", elements=lambda: elements))
        self.assertEqual({}, json.loads((self.root / "data/osm-decisions.json").read_text(encoding="utf-8"))["facilities"])

    def test_duplicate_allocation_is_refused(self):
        place_id = new_uuid7()
        self.places["@graph"] = [{"@id": f"urn:uuid:{place_id}", "@type": ["schema:Place"],
                                  "schema:geo": {"@type": "schema:GeoCoordinates", "schema:longitude": 139.7, "schema:latitude": 35.68},
                                  "rdfs:seeAlso": ["https://www.openstreetmap.org/node/7"]}]
        (self.root / "data/places.jsonld").write_text(json.dumps(self.places, ensure_ascii=False), encoding="utf-8")
        nodes = [{"type": "node", "id": 7, "lat": 35.6882993, "lon": 139.7365076, "tags": {"name": "重複"}}]
        self.assertEqual(1, self.run_assoc("--osm-id", "node/7", elements=lambda: nodes))
        self.assertNotIn(self.query_id, json.loads((self.root / "data/osm-decisions.json").read_text(encoding="utf-8"))["facilities"])

    def test_unknown_search_input_is_refused(self):
        self.assertEqual(1, fac_cli.main(["assoc", str(self.root), new_uuid7(), "--osm-id", "node/7", "--editor", "t"]))

    def test_editor_is_required(self):
        nodes = [{"type": "node", "id": 7, "lat": 35.6882993, "lon": 139.7365076, "tags": {"name": "テスト"}}]
        with patch("src.fac_cli.osm_candidate") as fetch_osm_candidate:
            fetch_osm_candidate.side_effect = lambda record_id, fetch=None: real_osm_candidate(record_id, fetch=lambda url: osm_json(nodes))
            with patch("src.fac_cli.subprocess.run") as run:
                run.return_value.stdout = ""
                result = fac_cli.main(["assoc", str(self.root), self.query_id, "--osm-id", "node/7"])
        self.assertEqual(1, result)


if __name__ == "__main__":
    unittest.main()
