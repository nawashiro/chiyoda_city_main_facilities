import json
import tempfile
import unittest
from pathlib import Path

from src import facility_categories
from src.facility_categories import category_set_id, category_term_id
from src.facility_data import _write_json, validate_jsonld_document

ROOT = Path(__file__).resolve().parents[1]
UUID = "01990000-0000-7000-8000-000000000001"


def term(code):
    return {
        "@id": category_term_id(code),
        "@type": "schema:DefinedTerm",
        "schema:name": f"ラベル{code}",
        "schema:inDefinedTermSet": {"@id": category_set_id()},
        "schema:identifier": {
            "@type": "schema:PropertyValue",
            "schema:propertyID": "gif-poi",
            "schema:value": code,
        },
    }


def vocabulary(*codes):
    terms = [term(code) for code in codes]
    return {
        "@context": {"@version": 1.1, "schema": "https://schema.org/"},
        "@graph": [
            {
                "@id": category_set_id(),
                "@type": "schema:DefinedTermSet",
                "schema:name": "テスト語彙",
                "schema:hasDefinedTerm": [{"@id": item["@id"]} for item in terms],
            },
            *terms,
        ],
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
    _write_json(root / "data/category-vocabulary.jsonld", vocabulary("1512", "0801", "0802", "1499"))
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
    def setUp(self):
        self.document = vocabulary("1512")

    def term(self):
        return next(node for node in self.document["@graph"] if node.get("@type") == "schema:DefinedTerm")

    def test_valid_vocabulary_passes(self):
        facility_categories.validate_vocabulary(self.document)

    def test_rejects_non_four_digit_code(self):
        self.term()["schema:identifier"]["schema:value"] = "703"
        with self.assertRaises(ValueError):
            facility_categories.validate_vocabulary(self.document)

    def test_rejects_duplicate_terms(self):
        with self.assertRaises(ValueError):
            facility_categories.validate_vocabulary(vocabulary("1512", "1512"))

    def test_rejects_provenance_in_the_vocabulary(self):
        self.document["@graph"][0]["schema:citation"] = {"@type": "schema:CreativeWork", "schema:version": "v2.4"}
        with self.assertRaises(ValueError):
            facility_categories.validate_vocabulary(self.document)

    def test_rejects_http_term_url(self):
        self.term()["@id"] = "https://nawashiro.github.io/chiyoda_city_main_facilities/category-vocabulary.jsonld#1512"
        with self.assertRaises(ValueError):
            facility_categories.validate_vocabulary(self.document)

    def test_rejects_uuid_mismatch(self):
        self.term()["@id"] = "urn:uuid:01990000-0000-7000-8000-000000000099"
        with self.assertRaises(ValueError):
            facility_categories.validate_vocabulary(self.document)

    def test_rejects_missing_identifier(self):
        self.term().pop("schema:identifier")
        with self.assertRaises(ValueError):
            facility_categories.validate_vocabulary(self.document)


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


class HospitalAndSchoolRuleTests(unittest.TestCase):
    def setUp(self):
        self.codes = facility_categories.load_vocabulary(ROOT)
        self.rule_list = facility_categories.load_rules(ROOT, self.codes)

    def test_hospital_tag_decides_hospital(self):
        matched = facility_categories.evaluate_rules(self.rule_list, {"amenity": "hospital"}, "九段坂病院")
        self.assertEqual(["1601"], matched)

    def test_school_tag_with_elementary_name_decides_elementary_school(self):
        matched = facility_categories.evaluate_rules(self.rule_list, {"amenity": "school"}, "千代田区立麹町小学校")
        self.assertEqual(["1503"], matched)

    def test_school_name_without_school_tag_is_not_decided(self):
        matched = facility_categories.evaluate_rules(self.rule_list, {"building": "school"}, "千代田区立麹町小学校")
        self.assertEqual([], matched)

    def test_school_tag_without_elementary_name_is_not_decided(self):
        matched = facility_categories.evaluate_rules(self.rule_list, {"amenity": "school"}, "千代田区立麹町中学校")
        self.assertEqual([], matched)


class DecisionAndApplyTests(unittest.TestCase):
    def test_apply_adds_and_removes_keywords(self):
        temporary, root = repository()
        with temporary:
            codes = facility_categories.load_vocabulary(root)
            decisions = {"version": 1, "facilities": {UUID: {"category": "0801", "method": "rule", "osmId": "node/123"}}}
            document = json.loads((root / "data/places.jsonld").read_text(encoding="utf-8"))
            self.assertEqual([], facility_categories.apply_category_terms(document, decisions, codes))
            self.assertEqual([{"@id": codes["0801"]["@id"]}], document["@graph"][0]["schema:keywords"])
            self.assertNotIn("schema:identifier", document["@graph"][0])
            stale = {"version": 1, "facilities": {UUID: {"category": "0801", "method": "rule", "osmId": "way/999"}}}
            self.assertEqual([UUID], facility_categories.apply_category_terms(document, stale, codes))
            self.assertNotIn("schema:keywords", document["@graph"][0])

    def test_rejects_unknown_code_and_bad_method(self):
        temporary, root = repository()
        with temporary:
            codes = facility_categories.load_vocabulary(root)
            for entry in ({"category": "9999", "method": "rule", "osmId": None}, {"category": "0801", "method": "guess", "osmId": None}):
                with self.subTest(entry=entry):
                    issues = facility_categories.validate_decisions({"version": 1, "facilities": {UUID: entry}}, codes)
                    self.assertTrue(issues)

    def test_record_rejects_gif_poi_identifier(self):
        record = canonical_record()
        record["schema:identifier"] = [{"@type": "schema:PropertyValue", "schema:propertyID": "gif-poi", "schema:value": "0801"}]
        with self.assertRaises(ValueError):
            validate_jsonld_document(
                {"@context": {"@version": 1.1, "schema": "https://schema.org/", "rdfs": "http://www.w3.org/2000/01/rdf-schema#"}, "@graph": [record]},
            )

    def test_record_allows_additional_type(self):
        record = canonical_record()
        record["schema:additionalType"] = ["https://example.com/x"]
        validate_jsonld_document({"@context": {"@version": 1.1, "schema": "https://schema.org/", "rdfs": "http://www.w3.org/2000/01/rdf-schema#"}, "@graph": [record]})

    def test_canonical_record_rejects_keywords(self):
        record = canonical_record()
        record["schema:keywords"] = [{"@id": category_term_id("0801")}]
        with self.assertRaises(ValueError):
            validate_jsonld_document({"@context": {"@version": 1.1, "schema": "https://schema.org/", "rdfs": "http://www.w3.org/2000/01/rdf-schema#"}, "@graph": [record]})


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
            self.assertNotIn("schema:identifier", document["@graph"][0])

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

    def test_unassociated_place_is_not_classified(self):
        record = canonical_record()
        record.pop("rdfs:seeAlso")
        temporary, root = repository(record=record)
        with temporary:
            def judge(evidence, codes):
                self.fail("Jev must not judge a facility without an OSM association")

            _document, report = facility_categories.refresh(root, judge=judge)
            self.assertEqual([], report["pending"])
            decisions = json.loads((root / "data/categories.json").read_text(encoding="utf-8"))
            self.assertNotIn(UUID, decisions["facilities"])

    def test_facility_without_place_is_not_classified(self):
        temporary, root = repository()
        with temporary:
            _write_json(root / "data/places.jsonld", {"@context": {"@version": 1.1, "schema": "https://schema.org/", "rdfs": "http://www.w3.org/2000/01/rdf-schema#"}, "@graph": []})

            def judge(evidence, codes):
                self.fail("Jev must not judge a facility without a place")

            _document, report = facility_categories.refresh(root, judge=judge)
            self.assertEqual([], report["pending"])
            decisions = json.loads((root / "data/categories.json").read_text(encoding="utf-8"))
            self.assertNotIn(UUID, decisions["facilities"])

    def test_stale_decision_stays_until_reevaluated(self):
        decisions = {"version": 1, "facilities": {UUID: {"category": "1512", "method": "rule", "osmId": "node/456"}}}
        temporary, root = repository(decisions=decisions)
        with temporary:
            before = (root / "data/places.jsonld").read_bytes()
            _document, report = facility_categories.refresh(root)
            self.assertEqual([UUID], report["stale"])
            self.assertEqual([UUID], report["pending"])
            decisions = json.loads((root / "data/categories.json").read_text(encoding="utf-8"))
            self.assertEqual("1512", decisions["facilities"][UUID]["category"])
            self.assertEqual(before, (root / "data/places.jsonld").read_bytes())
            self.assertNotIn("schema:identifier", json.loads(before)["@graph"][0])

    def test_refresh_does_not_change_places(self):
        temporary, root = repository()
        with temporary:
            before = (root / "data/places.jsonld").read_bytes()
            (root / "site/dataset.jsonld").write_bytes(b"previous publication")
            facility_categories.refresh(root)
            self.assertEqual(before, (root / "data/places.jsonld").read_bytes())
            self.assertEqual(b"previous publication", (root / "site/dataset.jsonld").read_bytes())


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
            before = (root / "data/places.jsonld").read_bytes()
            (root / "site/dataset.jsonld").write_bytes(b"previous publication")
            code, _output = self._main("category", "assign", str(root), UUID, "0801", "--editor", "tester")
            self.assertEqual(0, code)
            decisions = json.loads((root / "data/categories.json").read_text(encoding="utf-8"))
            entry = decisions["facilities"][UUID]
            self.assertEqual(("human", "0801", "tester"), (entry["method"], entry["category"], entry["editor"]))
            self.assertEqual(before, (root / "data/places.jsonld").read_bytes())
            code, _output = self._main("category", "clear", str(root), UUID)
            self.assertEqual(0, code)
            decisions = json.loads((root / "data/categories.json").read_text(encoding="utf-8"))
            self.assertNotIn(UUID, decisions["facilities"])
            self.assertEqual(before, (root / "data/places.jsonld").read_bytes())
            self.assertEqual(b"previous publication", (root / "site/dataset.jsonld").read_bytes())

    def test_assign_rejects_unknown_code(self):
        temporary, root = repository()
        with temporary:
            code, output = self._main("category", "assign", str(root), UUID, "9999", "--editor", "tester")
            self.assertEqual(1, code)
            self.assertIn("not in the vocabulary", output)


class UnresolvedFacilityTests(unittest.TestCase):
    def test_associated_undecided_place_is_unresolved(self):
        temporary, root = repository()
        with temporary:
            self.assertEqual([{"id": UUID, "name": "テスト美術館", "osmId": "node/123"}],
                             facility_categories.unresolved_facilities(root))

    def test_current_decision_is_not_unresolved(self):
        decisions = {"version": 1, "facilities": {UUID: {"category": "0801", "method": "rule", "osmId": "node/123"}}}
        temporary, root = repository(decisions=decisions)
        with temporary:
            self.assertEqual([], facility_categories.unresolved_facilities(root))

    def test_facility_without_place_is_not_unresolved(self):
        temporary, root = repository()
        with temporary:
            _write_json(root / "data/places.jsonld", {"@context": {"@version": 1.1, "schema": "https://schema.org/", "rdfs": "http://www.w3.org/2000/01/rdf-schema#"}, "@graph": []})
            self.assertEqual([], facility_categories.unresolved_facilities(root))


class CategoryReviewIssueTests(unittest.TestCase):
    def test_unresolved_facilities_are_presented_as_one_issue(self):
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


class HeldFacilityTests(unittest.TestCase):
    def held_repository(self):
        record = {"@id": f"urn:uuid:{UUID}", "@type": ["schema:Place"],
                  "schema:geo": {"@type": "schema:GeoCoordinates", "schema:longitude": 139.75, "schema:latitude": 35.69}}
        temporary, root = repository(record=record)
        self.addCleanup(temporary.cleanup)
        _write_json(root / "data/osm-decisions.json", {"version": 1, "facilities": {UUID: {
            "status": "hold", "reason": "実地調査待ち", "previous": "node/123",
            "human": {"editor": "tester", "editedAt": "2026-11-20T00:00:00Z"}}}})
        return root

    def test_review_lists_holds_separately_from_unresolved(self):
        report = facility_categories.review(self.held_repository())
        self.assertEqual([{"id": UUID, "name": "テスト美術館", "reason": "実地調査待ち"}], report["held"])
        self.assertEqual([], report["uncategorized"])

    def test_unresolved_facilities_skip_holds(self):
        self.assertEqual([], facility_categories.unresolved_facilities(self.held_repository()))

    def test_refresh_skips_holds(self):
        _, report = facility_categories.refresh(self.held_repository())
        self.assertEqual([], report["pending"])
        self.assertEqual([], report["stale"])


if __name__ == "__main__":
    unittest.main()
