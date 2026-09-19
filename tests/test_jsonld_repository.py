import json
import re
import unittest
from pathlib import Path

import src.facility_data as facility_data


ROOT = Path(__file__).resolve().parents[1]


class JsonLdRepositoryArtifactTests(unittest.TestCase):
    def test_canonical_jsonld_is_valid_and_contains_92_public_places(self):
        path = ROOT / "data/places.jsonld"
        self.assertTrue(path.is_file(), f"missing canonical JSON-LD artifact: {path}")

        document = json.loads(path.read_text(encoding="utf-8"))
        facility_data.validate_jsonld_document(document)

        graph = document["@graph"]
        public_places = [
            record
            for record in graph
            if "schema:Place" in record.get("@type", [])
        ]
        self.assertEqual(92, len(public_places))

        place_ids = [record["@id"] for record in public_places]
        self.assertTrue(all(place_id.startswith("urn:uuid:") for place_id in place_ids))
        self.assertEqual(len(place_ids), len(set(place_ids)))

    def test_fixture_and_canonical_jsonld_integrate_public_place_contract(self):
        documents = {
            "fixture": (
                ROOT / "tests/fixtures/jsonld-integration.json",
                1,
            ),
            "canonical": (ROOT / "data/places.jsonld", 92),
        }
        forbidden_terms = {
            "geo:hasGeometry",
            "geo:asWKT",
            "geo:asGeoJSON",
            "GeoSPARQL",
            "GeoJSON",
            "schema:sameAs",
            "skos:exactMatch",
            "skos:closeMatch",
            "prov:wasDerivedFrom",
            "registry",
            "audit",
            "auditTrail",
            "history",
            "referenceHistory",
        }

        for label, (path, expected_place_count) in documents.items():
            with self.subTest(document=label):
                document = json.loads(path.read_text(encoding="utf-8"))
                public_places = [
                    record
                    for record in document["@graph"]
                    if "schema:Place" in record.get("@type", [])
                ]
                self.assertEqual(expected_place_count, len(public_places))

                place_ids = [record.get("@id") for record in public_places]
                self.assertEqual(len(place_ids), len(set(place_ids)))
                self.assertTrue(
                    all(
                        isinstance(place_id, str)
                        and re.fullmatch(
                            r"urn:uuid:[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}",
                            place_id,
                        )
                        for place_id in place_ids
                    )
                )

                for record in public_places:
                    geo = record.get("schema:geo")
                    self.assertEqual("schema:GeoCoordinates", geo.get("@type"))
                    for field, lower, upper in (
                        ("schema:latitude", -90, 90),
                        ("schema:longitude", -180, 180),
                    ):
                        value = geo.get(field)
                        with self.subTest(document=label, place=record["@id"], field=field):
                            self.assertIsInstance(value, (int, float))
                            self.assertNotIsInstance(value, bool)
                            self.assertGreaterEqual(value, lower)
                            self.assertLessEqual(value, upper)

                    links = record.get("rdfs:seeAlso", [])
                    self.assertIsInstance(links, list)
                    self.assertTrue(
                        all(
                            re.fullmatch(
                                r"https://www\.openstreetmap\.org/(?:node|way|relation)/[1-9][0-9]*",
                                uri,
                            )
                            or re.fullmatch(
                                r"https://www\.wikidata\.org/entity/Q[1-9][0-9]*",
                                uri,
                            )
                            for uri in links
                        )
                    )
                    self.assertFalse(any("wam" in uri.casefold() for uri in links))

                    for identifier in record.get("schema:identifier", []):
                        self.assertEqual("schema:PropertyValue", identifier.get("@type"))
                        self.assertEqual("wam", identifier.get("schema:propertyID"))
                        self.assertRegex(identifier.get("schema:value"), r"^[AE][0-9]{10}$")

                osm_links = [
                    uri
                    for record in public_places
                    for uri in record.get("rdfs:seeAlso", [])
                    if "openstreetmap.org" in uri
                ]
                wikidata_links = [
                    uri
                    for record in public_places
                    for uri in record.get("rdfs:seeAlso", [])
                    if "wikidata.org" in uri
                ]
                wam_identifiers = [
                    identifier
                    for record in public_places
                    for identifier in record.get("schema:identifier", [])
                ]
                self.assertTrue(osm_links)
                self.assertTrue(wikidata_links)
                self.assertTrue(wam_identifiers)

                serialized = json.dumps(document, ensure_ascii=False)
                self.assertFalse(any(term in serialized for term in forbidden_terms))

    def test_legacy_repository_artifacts_and_code_paths_are_removed(self):
        legacy_paths = (
            ROOT / "data/registry.json",
            ROOT / "dist/public/places.geojson",
            ROOT / "dist/public/manifest.json",
            ROOT / "schema/registry.schema.json",
            ROOT / "schema/public-geojson.schema.json",
        )
        present_paths = [str(path.relative_to(ROOT)) for path in legacy_paths if path.exists()]
        self.assertEqual([], present_paths, "legacy artifacts and schemas must be removed")

        legacy_symbols = {
            "validate_registry",
            "build_public_geojson",
            "migrate_legacy",
            "migrate_repository",
            "compact_audit",
            "update_osm_reference",
            "synchronize_registry_names",
        }
        self.assertFalse(
            legacy_symbols & set(vars(facility_data)),
            "facility_data must not retain registry/history compatibility APIs",
        )
        for source_path in (ROOT / "src").glob("*.py"):
            self.assertNotIn(
                "data/registry.json",
                source_path.read_text(encoding="utf-8"),
                f"{source_path.relative_to(ROOT)} still depends on the registry",
            )


if __name__ == "__main__":
    unittest.main()
