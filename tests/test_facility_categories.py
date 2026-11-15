import json
import tempfile
import unittest
from pathlib import Path

from src import facility_categories
from src.facility_data import _write_json, validate_jsonld_document

ROOT = Path(__file__).resolve().parents[1]
UUID = "01990000-0000-7000-8000-000000000001"


def term(code):
    return {
        "@type": "schema:DefinedTerm",
        "@id": f"https://nawashiro.github.io/chiyoda_city_main_facilities/categories.jsonld#{code}",
        "schema:name": f"ラベル{code}",
        "schema:identifier": {"@type": "schema:PropertyValue", "schema:propertyID": "gif-poi", "schema:value": code},
    }


def vocabulary(*codes):
    return {
        "@context": {"@version": 1.1, "schema": "https://schema.org/"},
        "@type": "schema:DefinedTermSet",
        "@id": "https://nawashiro.github.io/chiyoda_city_main_facilities/categories.jsonld",
        "schema:name": "テスト語彙",
        "schema:citation": {
            "@type": "schema:CreativeWork",
            "schema:name": "GIF POIコード表",
            "schema:url": "https://github.com/digital-go-jp/GIF/blob/v2.4/490_%E3%81%9D%E3%81%AE%E4%BB%96/491-3-1_POI%E3%82%B3%E3%83%BC%E3%83%89%E8%A1%A8.xlsx",
            "schema:version": "v2.4",
        },
        "hasDefinedTerm": [term(code) for code in codes],
    }


def rules():
    return {"version": 1, "rules": [
        {"id": "library-tag", "category": "1512", "tags": {"amenity": "library"}},
        {"id": "art-name", "category": "0802", "nameIncludes": ["美術館"]},
        {"id": "museum-tag", "category": "0801", "tags": {"tourism": "museum"}},
    ]}


def canonical_record():
    return {
        "@id": f"urn:uuid:{UUID}",
        "@type": ["schema:Place"],
        "schema:geo": {"@type": "schema:GeoCoordinates", "schema:longitude": 139.75, "schema:latitude": 35.69},
        "rdfs:seeAlso": ["https://www.openstreetmap.org/node/123"],
    }


def repository(record=None, name="テスト美術館", decisions=None):
    temporary = tempfile.TemporaryDirectory()
    root = Path(temporary.name)
    _write_json(root / "data/categories.jsonld", vocabulary("1512", "0801", "0802", "1499"))
    _write_json(root / "data/category-rules.json", rules())
    document = {"@context": {"@version": 1.1, "schema": "https://schema.org/", "rdfs": "http://www.w3.org/2000/01/rdf-schema#"},
                "@graph": [record or canonical_record()]}
    _write_json(root / "data/places.jsonld", document)
    _write_json(root / "inputs/facilities.json", {"queries": [{"id": UUID, "name": name, "coordinates": [139.75, 35.69]}]})
    _write_json(root / "site/mirrors/osm.json", {"elements": [
        {"type": "node", "id": 123, "lat": 35.69, "lon": 139.75, "tags": {"name": "テスト美術館", "tourism": "museum"}},
        {"type": "node", "id": 456, "lat": 35.69, "lon": 139.76, "tags": {"name": "図書館", "amenity": "library"}},
    ]})
    if decisions is not None:
        _write_json(root / "data/categories.json", decisions)
    return temporary, root


def jev_result(choice, confidence):
    return {"choice": choice, "confidence": confidence, "probabilities": {}, "usage": {"input_tokens": 1, "output_tokens": 1}, "model": "jev-1.14.0"}


class VocabularyValidationTests(unittest.TestCase):
    def test_valid_vocabulary_passes(self):
        facility_categories.validate_vocabulary(vocabulary("1512"))

    def test_rejects_non_four_digit_fragment(self):
        with self.assertRaises(ValueError):
            facility_categories.validate_vocabulary(vocabulary("703"))

    def test_rejects_duplicate_terms(self):
        with self.assertRaises(ValueError):
            facility_categories.validate_vocabulary(vocabulary("1512", "1512"))

    def test_rejects_citation_without_version(self):
        broken = vocabulary("1512")
        del broken["schema:citation"]["schema:version"]
        with self.assertRaises(ValueError):
            facility_categories.validate_vocabulary(broken)


class RulesTests(unittest.TestCase):
    def setUp(self):
        self.codes = {"1512": "図書館", "0801": "博物館", "0802": "美術館", "1499": "その他の社会福祉施設"}
        self.rule_list = rules()["rules"]

    def test_single_match_decides(self):
        matched = facility_categories.evaluate_rules(self.rule_list, {"amenity": "library"}, "図書館")
        self.assertEqual(["1512"], matched)

    def test_semicolon_tokens_match(self):
        matched = facility_categories.evaluate_rules(self.rule_list, {"tourism": "museum", "museum": "art;person"}, "美術館")
        self.assertEqual(["0801", "0802"], matched)

    def test_conflicting_matches_do_not_decide(self):
        matched = facility_categories.evaluate_rules(self.rule_list, {"tourism": "museum"}, "美術館")
        self.assertEqual(["0801", "0802"], matched)

    def test_rule_must_reference_adopted_code(self):
        document = {"version": 1, "rules": [{"id": "x", "category": "9999", "tags": {"amenity": "library"}}]}
        self.assertTrue(facility_categories.validate_rules(document, self.codes))


class DecisionAndApplyTests(unittest.TestCase):
    def test_apply_adds_and_removes_term_urls(self):
        temporary, root = repository()
        with temporary:
            codes = facility_categories.load_vocabulary(root)
            decisions = {"version": 1, "facilities": {UUID: {"category": "0801", "method": "rule", "osmId": "node/123"}}}
            document = json.loads((root / "data/places.jsonld").read_text(encoding="utf-8"))
            self.assertEqual([], facility_categories.apply_categories(document, decisions, codes))
            validate_jsonld_document(document, category_codes=set(codes))
            self.assertEqual([facility_categories.term_url("0801")], document["@graph"][0]["schema:additionalType"])
            stale = {"version": 1, "facilities": {UUID: {"category": "0801", "method": "rule", "osmId": "way/999"}}}
            self.assertEqual([UUID], facility_categories.apply_categories(document, stale, codes))
            self.assertNotIn("schema:additionalType", document["@graph"][0])

    def test_rejects_unknown_code_and_bad_method(self):
        temporary, root = repository()
        with temporary:
            codes = facility_categories.load_vocabulary(root)
            for entry in ({"category": "9999", "method": "rule", "osmId": None}, {"category": "0801", "method": "guess", "osmId": None}):
                with self.subTest(entry=entry):
                    issues = facility_categories.validate_decisions({"version": 1, "facilities": {UUID: entry}}, codes)
                    self.assertTrue(issues)

    def test_record_rejects_non_adopted_term(self):
        record = canonical_record()
        record["schema:additionalType"] = [facility_categories.term_url("9999")]
        with self.assertRaises(ValueError):
            validate_jsonld_document(
                {"@context": {"@version": 1.1, "schema": "https://schema.org/", "rdfs": "http://www.w3.org/2000/01/rdf-schema#"}, "@graph": [record]},
                category_codes={"0801", "0802", "1512", "1499"},
            )


class RefreshTests(unittest.TestCase):
    def test_rule_decides_unique_matches(self):
        temporary, root = repository(name="テスト図書館")
        with temporary:
            _document, _report = facility_categories.refresh(root)
            decisions = json.loads((root / "data/categories.json").read_text(encoding="utf-8"))
            self.assertEqual({"category": "0801", "method": "rule", "osmId": "node/123"}, decisions["facilities"][UUID])

    def test_jev_adopts_high_confidence_result(self):
        temporary, root = repository()
        with temporary:
            def judge(evidence, codes):
                self.assertIn("element", evidence)
                return jev_result("1499", 0.95)

            document, report = facility_categories.refresh(root, judge=judge)
            decisions = json.loads((root / "data/categories.json").read_text(encoding="utf-8"))
            entry = decisions["facilities"][UUID]
            self.assertEqual(("1499", "jev"), (entry["category"], entry["method"]))
            self.assertEqual({}, report["unresolved"])
            self.assertEqual([facility_categories.term_url("1499")], document["@graph"][0]["schema:additionalType"])

    def test_low_confidence_result_stays_unresolved(self):
        temporary, root = repository(record={**canonical_record(), "rdfs:seeAlso": ["https://www.openstreetmap.org/node/999"]}, name="なぞの施設")
        with temporary:
            def judge(evidence, codes):
                return jev_result("none", 0.4)

            _document, report = facility_categories.refresh(root, judge=judge)
            self.assertIn(UUID, report["unresolved"])
            decisions = json.loads((root / "data/categories.json").read_text(encoding="utf-8"))
            self.assertNotIn(UUID, decisions["facilities"])

    def test_high_confidence_none_keeps_uncategorized(self):
        temporary, root = repository(record={**canonical_record(), "rdfs:seeAlso": ["https://www.openstreetmap.org/node/999"]}, name="なぞの施設")
        with temporary:
            def judge(evidence, codes):
                return jev_result("none", 0.99)

            _document, report = facility_categories.refresh(root, judge=judge)
            self.assertEqual({}, report["unresolved"])
            decisions = json.loads((root / "data/categories.json").read_text(encoding="utf-8"))
            self.assertNotIn(UUID, decisions["facilities"])

    def test_operational_failure_records_nothing(self):
        temporary, root = repository(record={**canonical_record(), "rdfs:seeAlso": ["https://www.openstreetmap.org/node/999"]}, name="なぞの施設")
        with temporary:
            def judge(evidence, codes):
                raise ValueError("TYPESAFE_API_KEY is required")

            with self.assertRaises(ValueError):
                facility_categories.refresh(root, judge=judge)
            self.assertFalse((root / "data/categories.json").exists())

    def test_stale_decision_stays_until_reevaluated(self):
        decisions = {"version": 1, "facilities": {UUID: {"category": "1512", "method": "rule", "osmId": "node/456"}}}
        temporary, root = repository(decisions=decisions)
        with temporary:
            _document, report = facility_categories.refresh(root)
            self.assertEqual([UUID], report["stale"])
            self.assertEqual([UUID], report["pending"])
            decisions = json.loads((root / "data/categories.json").read_text(encoding="utf-8"))
            self.assertEqual("1512", decisions["facilities"][UUID]["category"])
            document = json.loads((root / "data/places.jsonld").read_text(encoding="utf-8"))
            self.assertNotIn("schema:additionalType", document["@graph"][0])


class CliDecisionTests(unittest.TestCase):
    def _main(self, *argv):
        import contextlib
        import io
        import src.fac_cli as fac_cli
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = fac_cli.main(list(argv))
        return code, buffer.getvalue()

    def test_assign_records_human_decision_and_clear_reverts(self):
        temporary, root = repository()
        with temporary:
            code, _output = self._main("category", "assign", str(root), UUID, "0801", "--editor", "tester")
            self.assertEqual(0, code)
            decisions = json.loads((root / "data/categories.json").read_text(encoding="utf-8"))
            entry = decisions["facilities"][UUID]
            self.assertEqual(("human", "0801", "tester"), (entry["method"], entry["category"], entry["editor"]))
            code, _output = self._main("category", "clear", str(root), UUID)
            self.assertEqual(0, code)
            decisions = json.loads((root / "data/categories.json").read_text(encoding="utf-8"))
            self.assertNotIn(UUID, decisions["facilities"])

    def test_assign_rejects_unknown_code(self):
        temporary, root = repository()
        with temporary:
            code, output = self._main("category", "assign", str(root), UUID, "9999", "--editor", "tester")
            self.assertEqual(1, code)
            self.assertIn("not in the vocabulary", output)


class CategoryReviewIssueTests(unittest.TestCase):
    def test_unresolved_facilities_are_presented_as_one_issue(self):
        class FakeGitHub:
            def __init__(self):
                self.created = None

            def api(self, path, data=None, method=None):
                self.created = (path, data)
                return {}

            def find_issue(self, query_id, marker=None):
                return None

            def issue(self, number):
                return {"state": "OPEN"}

        from src.github_osm_review import GitHub
        github = GitHub.__new__(GitHub)
        github.repository = "example/repo"
        created = []
        github.api = lambda path, data=None, method=None: created.append((path, data)) or {}
        github.find_issue = lambda query_id, marker=None: None
        github.issue = lambda number: {"state": "OPEN"}
        GitHub.save_category_review(github, [{"id": UUID, "name": "なぞの施設", "osmId": None}])
        self.assertEqual(1, len(created))
        path, body = created[0]
        self.assertEqual("/repos/example/repo/issues", path)
        self.assertIn("なぞの施設", body["body"])
        self.assertIn("category-review", body["body"])


if __name__ == "__main__":
    unittest.main()
