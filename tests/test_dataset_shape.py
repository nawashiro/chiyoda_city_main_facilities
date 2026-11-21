import copy
import json
import unittest
from pathlib import Path

from src.facility_data import validate_published_document, validate_shape_document

ROOT = Path(__file__).resolve().parents[1]


def type_names(record):
    value = record.get("@type")
    return value if isinstance(value, list) else [value]


def shape_for(document, target):
    return next(
        shape for shape in document["@graph"]
        if "sh:NodeShape" in type_names(shape)
        and _target(shape.get("sh:targetClass")) == target
    )


def _target(value):
    return value.get("@id") if isinstance(value, dict) else value


def property_for(shape, predicate):
    return next(item for item in shape["sh:property"] if _target(item["sh:path"]) == predicate)


class DatasetShapeTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads((ROOT / "data/dataset-shape.jsonld").read_text(encoding="utf-8"))

    def test_shape_source_is_valid(self):
        validate_shape_document(self.document)

    def test_place_shape_expresses_image_creator_optionality(self):
        shape = shape_for(self.document, "schema:Place")
        image = property_for(shape, "schema:image")
        self.assertEqual(1, image["sh:maxCount"])
        self.assertNotIn("sh:minCount", image)
        fields = {_target(item["sh:path"]): item for item in image["sh:node"]["sh:property"]}
        self.assertEqual(1, fields["schema:contentUrl"]["sh:minCount"])
        self.assertEqual(1, fields["schema:license"]["sh:minCount"])
        creator = fields["schema:creator"]
        self.assertEqual(1, creator["sh:maxCount"])
        self.assertNotIn("sh:minCount", creator)
        self.assertEqual(1, property_for(creator["sh:node"], "schema:name")["sh:minCount"])

    def test_place_shape_requires_geo_and_typed_keywords(self):
        shape = shape_for(self.document, "schema:Place")
        geo = property_for(shape, "schema:geo")
        self.assertEqual(1, geo["sh:minCount"])
        self.assertEqual(1, geo["sh:maxCount"])
        keywords = property_for(shape, "schema:keywords")
        self.assertEqual("schema:DefinedTerm", _target(keywords["sh:class"]))
        see_also = property_for(shape, "rdfs:seeAlso")
        self.assertEqual("sh:IRI", _target(see_also["sh:nodeKind"]))

    def test_term_shape_requires_gif_poi_identifier(self):
        shape = shape_for(self.document, "schema:DefinedTerm")
        identifier = property_for(shape, "schema:identifier")
        fields = {_target(item["sh:path"]): item for item in identifier["sh:node"]["sh:property"]}
        self.assertEqual("gif-poi", fields["schema:propertyID"]["sh:hasValue"])
        self.assertEqual("^[0-9]{4}$", fields["schema:value"]["sh:pattern"])


class PublishedGraphValidationTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads((ROOT / "site/dataset.jsonld").read_text(encoding="utf-8"))

    def place(self):
        return next(record for record in self.document["@graph"] if "schema:Place" in type_names(record))

    def test_built_graph_is_valid(self):
        validate_published_document(self.document)

    def test_unknown_keyword_term_is_rejected(self):
        place = self.place()
        place["schema:keywords"] = [{"@id": "urn:uuid:01990000-0000-7000-8000-000000000099"}]
        with self.assertRaises(ValueError):
            validate_published_document(self.document)

    def test_gif_poi_identifier_is_rejected_on_a_place(self):
        place = self.place()
        place["schema:identifier"] = [{"@type": "schema:PropertyValue", "schema:propertyID": "gif-poi", "schema:value": "0702"}]
        with self.assertRaises(ValueError):
            validate_published_document(self.document)

    def test_terms_without_a_term_set_are_rejected(self):
        self.document["@graph"] = [
            record for record in self.document["@graph"]
            if "schema:DefinedTermSet" not in type_names(record)
        ]
        with self.assertRaises(ValueError):
            validate_published_document(self.document)


if __name__ == "__main__":
    unittest.main()
