import contextlib
import hashlib
import io
import json
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src import fac_cli
from src.facility_data import barrier_free_webpage, new_uuid7
from src.resolve_osm_candidates import osm_candidate as real_osm_candidate

REPO = Path(__file__).resolve().parents[1]
CONTEXT = {"@version": 1.1, "schema": "https://schema.org/", "rdfs": "http://www.w3.org/2000/01/rdf-schema#"}
def _vocabulary():
    from src.facility_categories import category_set_id, category_term_id
    terms = [{
        "@id": category_term_id(code), "@type": "schema:DefinedTerm", "schema:name": name,
        "schema:inDefinedTermSet": {"@id": category_set_id()},
        "schema:identifier": {"@type": "schema:PropertyValue", "schema:propertyID": "gif-poi", "schema:value": code},
    } for code, name in (("1403", "児童館（児童センター）"), ("1499", "その他の社会福祉施設"))]
    return {"@context": {"@version": 1.1, "schema": "https://schema.org/"},
            "@graph": [{"@id": category_set_id(), "@type": "schema:DefinedTermSet", "schema:name": "テスト語彙",
                        "schema:hasDefinedTerm": [{"@id": term["@id"]} for term in terms]}, *terms]}


VOCABULARY = _vocabulary()


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

    def run_assoc_output(self, *args, elements):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = self.run_assoc(*args, elements=elements)
        return code, buffer.getvalue()

    def write_snapshot(self, elements, version="202611200100"):
        directory = self.root / "imports/openstreetmap"
        directory.mkdir(parents=True, exist_ok=True)
        raw = {"version": version, "elements": elements}
        payload = (json.dumps(raw, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        (directory / "raw.json").write_bytes(payload)
        (directory / "retrieval.json").write_text(json.dumps(
            {"rawSha256": hashlib.sha256(payload).hexdigest(), "rawVersion": version}), encoding="utf-8")

    def element(self):
        return [{"type": "node", "id": 7, "lat": 35.6882993, "lon": 139.7365076, "tags": {"name": "千代田区立テスト児童館"}}]

    def ledger_entry(self):
        return json.loads((self.root / "data/osm-decisions.json").read_text(encoding="utf-8"))["facilities"].get(self.query_id)

    def test_associates_node_as_human_decision(self):
        nodes = [{"type": "node", "id": 7, "lat": 35.6882993, "lon": 139.7365076,
                  "tags": {"name": "千代田区立テスト児童館", "amenity": "community_centre",
                           "website": "https://example.test/a.html", "check_date": "2026-11-03"}}]
        (self.root / "site").mkdir()
        (self.root / "site/dataset.jsonld").write_bytes(b"previous publication")
        self.assertEqual(0, self.run_assoc("--osm-id", "node/7", elements=lambda: nodes))
        self.assertEqual(b"previous publication", (self.root / "site/dataset.jsonld").read_bytes())
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

    def seed_place(self):
        self.places["@graph"] = [{
            "@id": f"urn:uuid:{self.query_id}", "@type": ["schema:Place"],
            "schema:geo": {"@type": "schema:GeoCoordinates", "schema:longitude": 139.736548, "schema:latitude": 35.688289},
            "schema:subjectOf": [barrier_free_webpage("https://walkingnavi.com/list_route.php?grp=5&no=57&lang=ja")],
            "rdfs:seeAlso": ["https://www.openstreetmap.org/node/7", "https://www.wikidata.org/entity/Q1"],
        }]
        (self.root / "data/places.jsonld").write_text(json.dumps(self.places, ensure_ascii=False), encoding="utf-8")
        (self.root / "site").mkdir()
        (self.root / "site/places.jsonld").write_bytes(b"previous publication")
        (self.root / "data/category-vocabulary.jsonld").write_text(json.dumps(VOCABULARY, ensure_ascii=False), encoding="utf-8")
        (self.root / "data/categories.json").write_text(json.dumps({"version": 1, "facilities": {
            self.query_id: {"category": "1403", "method": "human", "editor": "tester",
                            "editedAt": "2026-11-01T00:00:00Z", "osmId": "node/7"}}}, ensure_ascii=False), encoding="utf-8")

    def test_hold_records_reason_and_withdraws_links_and_category(self):
        self.seed_place()
        self.assertEqual(0, fac_cli.main(["assoc", str(self.root), self.query_id, "--hold",
                                          "--reason", "実地調査待ち", "--editor", "tester"]))
        place = json.loads((self.root / "data/places.jsonld").read_text(encoding="utf-8"))["@graph"][0]
        self.assertNotIn("rdfs:seeAlso", place)
        self.assertNotIn("schema:identifier", place)
        self.assertIn("schema:subjectOf", place)
        entry = json.loads((self.root / "data/osm-decisions.json").read_text(encoding="utf-8"))["facilities"][self.query_id]
        self.assertEqual("hold", entry["status"])
        self.assertEqual("実地調査待ち", entry["reason"])
        self.assertEqual("node/7", entry["previous"])
        self.assertEqual("tester", entry["human"]["editor"])
        self.assertTrue(entry["human"]["editedAt"])
        self.assertEqual(b"previous publication", (self.root / "site/places.jsonld").read_bytes())
        self.assertNotIn(self.query_id, json.loads((self.root / "data/categories.json").read_text(encoding="utf-8"))["facilities"])

    def test_hold_requires_a_reason(self):
        self.seed_place()
        self.assertEqual(1, fac_cli.main(["assoc", str(self.root), self.query_id, "--hold", "--editor", "tester"]))
        self.assertEqual({}, json.loads((self.root / "data/osm-decisions.json").read_text(encoding="utf-8"))["facilities"])

    def test_reason_without_hold_is_refused(self):
        self.seed_place()
        self.assertEqual(1, fac_cli.main(["assoc", str(self.root), self.query_id, "--osm-id", "node/7",
                                          "--reason", "実地調査待ち", "--editor", "tester"]))

    def test_hold_is_exclusive_with_osm_id(self):
        self.seed_place()
        with self.assertRaises(SystemExit):
            fac_cli.main(["assoc", str(self.root), self.query_id, "--hold", "--osm-id", "node/7",
                          "--reason", "実地調査待ち", "--editor", "tester"])

    def test_survey_confirmed_association_replaces_a_hold(self):
        self.seed_place()
        fac_cli.main(["assoc", str(self.root), self.query_id, "--hold", "--reason", "実地調査待ち", "--editor", "tester"])
        nodes = [{"type": "node", "id": 8, "lat": 35.6882993, "lon": 139.7365076, "tags": {"name": "千代田区立テスト児童館"}}]
        self.assertEqual(0, self.run_assoc("--osm-id", "node/8", elements=lambda: nodes))
        place = json.loads((self.root / "data/places.jsonld").read_text(encoding="utf-8"))["@graph"][0]
        self.assertEqual(["https://www.openstreetmap.org/node/8"], place["rdfs:seeAlso"])
        entry = json.loads((self.root / "data/osm-decisions.json").read_text(encoding="utf-8"))["facilities"][self.query_id]
        self.assertEqual("decided", entry["status"])
        self.assertEqual("node/8", entry["choice"])

    def test_none_choice_replaces_a_hold(self):
        self.seed_place()
        fac_cli.main(["assoc", str(self.root), self.query_id, "--hold", "--reason", "実地調査待ち", "--editor", "tester"])
        self.assertEqual(0, self.run_assoc("--choice", "none", elements=lambda: []))
        place = json.loads((self.root / "data/places.jsonld").read_text(encoding="utf-8"))["@graph"][0]
        self.assertNotIn("rdfs:seeAlso", place)
        entry = json.loads((self.root / "data/osm-decisions.json").read_text(encoding="utf-8"))["facilities"][self.query_id]
        self.assertEqual("decided", entry["status"])
        self.assertEqual("none", entry["choice"])

    def test_snapshot_with_the_element_records_a_decision(self):
        self.seed_place()
        self.write_snapshot(self.element())
        code, output = self.run_assoc_output("--osm-id", "node/7", elements=self.element)
        self.assertEqual(0, code)
        self.assertNotIn("未収録", output)
        self.assertEqual("decided", self.ledger_entry()["status"])
        place = json.loads((self.root / "data/places.jsonld").read_text(encoding="utf-8"))["@graph"][0]
        self.assertEqual(["https://www.openstreetmap.org/node/7"], place["rdfs:seeAlso"])
        self.assertEqual(139.7365076, place["schema:geo"]["schema:longitude"])

    def test_snapshot_without_the_element_records_a_hold(self):
        self.seed_place()
        self.write_snapshot([{"type": "node", "id": 1, "lat": 35.68, "lon": 139.73, "tags": {"name": "別の施設"}}])
        code, output = self.run_assoc_output("--osm-id", "node/7", elements=self.element)
        self.assertEqual(0, code)
        self.assertIn("未収録", output)
        entry = self.ledger_entry()
        self.assertEqual("hold", entry["status"])
        self.assertEqual("node/7", entry["previous"])
        self.assertIn("202611200100", entry["reason"])
        self.assertEqual("tester", entry["human"]["editor"])
        place = json.loads((self.root / "data/places.jsonld").read_text(encoding="utf-8"))["@graph"][0]
        self.assertNotIn("rdfs:seeAlso", place)
        self.assertEqual({"@type": "schema:GeoCoordinates", "schema:longitude": 139.736548, "schema:latitude": 35.688289}, place["schema:geo"])

    def test_snapshot_hold_withdraws_the_category_decision(self):
        self.seed_place()
        self.write_snapshot([])
        self.assertEqual(0, self.run_assoc("--osm-id", "node/7", elements=self.element))
        categories = json.loads((self.root / "data/categories.json").read_text(encoding="utf-8"))["facilities"]
        self.assertNotIn(self.query_id, categories)

    def test_unreadable_snapshot_records_a_decision(self):
        self.seed_place()
        code, output = self.run_assoc_output("--osm-id", "node/7", elements=self.element)
        self.assertEqual(0, code)
        self.assertIn("保持スナップショットが無い", output)
        self.assertEqual("decided", self.ledger_entry()["status"])
        self.write_snapshot([])
        (self.root / "imports/openstreetmap/retrieval.json").write_text(
            json.dumps({"rawSha256": "0" * 64, "rawVersion": "202611200100"}), encoding="utf-8")
        code, output = self.run_assoc_output("--osm-id", "node/7", elements=self.element)
        self.assertEqual(0, code)
        self.assertIn("一致しない", output)
        self.assertEqual("decided", self.ledger_entry()["status"])

    def test_snapshot_hold_is_lifted_after_the_mirror_update(self):
        self.seed_place()
        self.write_snapshot([])
        self.assertEqual(0, self.run_assoc("--osm-id", "node/7", elements=self.element))
        self.assertEqual("hold", self.ledger_entry()["status"])
        self.write_snapshot(self.element())
        self.assertEqual(0, self.run_assoc("--osm-id", "node/7", elements=self.element))
        entry = self.ledger_entry()
        self.assertEqual("decided", entry["status"])
        self.assertEqual("node/7", entry["choice"])
        place = json.loads((self.root / "data/places.jsonld").read_text(encoding="utf-8"))["@graph"][0]
        self.assertEqual(["https://www.openstreetmap.org/node/7"], place["rdfs:seeAlso"])

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
