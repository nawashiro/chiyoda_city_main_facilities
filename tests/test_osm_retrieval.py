import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.osm_mirror import coordinate_matcher, relation_out_center
from src.retrieve_osm import run_osm_retrieval


class OsmRetrievalTests(unittest.TestCase):
    def test_retrieval_uses_confirmed_ids_and_keeps_name_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'inputs').mkdir()
            (root/'imports/openstreetmap').mkdir(parents=True)
            (root/'inputs/facilities.json').write_text(json.dumps({'queries': []}))
            (root/'imports/openstreetmap/retrieval.json').write_text('{}')
            canonical = {'@graph': [{'rdfs:seeAlso': ['https://www.openstreetmap.org/way/8']}]}
            manifest = {'features': [{'properties': {'prefix': 'JP-13-', 'timestamp': 123, 'bytes': 3}}]}
            def fetch(url):
                return (b'pbf' if url.endswith('.osm.pbf') else json.dumps(manifest).encode()), {}
            def extract(path, typed_ids, qids, coordinates, bbox):
                self.assertEqual({'way/8'}, typed_ids)
                return [{'type': 'way', 'id': 8, 'tags': {'name': '施設'}},
                        {'type': 'node', 'id': 9, 'tags': {}}]
            raw_path, _ = run_osm_retrieval(root, '2026-10-28T00:00:00Z', fetch, extract, canonical=canonical)
            retained = json.loads(raw_path.read_text())
            self.assertEqual([8], [element['id'] for element in retained['elements']])
            metadata = json.loads((root/'imports/openstreetmap/retrieval.json').read_text())
            self.assertEqual(hashlib.sha256(raw_path.read_bytes()).hexdigest(), metadata['rawSha256'])

    def test_geohash_neighbour_matcher_keeps_exact_fifty_metre_boundary(self):
        matches = coordinate_matcher([[139.7500000, 35.6900000]])

        self.assertTrue(matches(139.7500000, 35.6904490))
        self.assertFalse(matches(139.7500000, 35.6910000))

    def test_relation_center_keeps_available_members_and_warns_about_missing_member(self):
        warnings = []

        center = relation_out_center(
            "relation/9",
            [
                {"type": "n", "ref": 1},
                {"type": "w", "ref": 2},
                {"type": "w", "ref": 3},
                {"type": "r", "ref": 4},
            ],
            {1: (139.70, 35.68)},
            {2: (139.72, 35.69, 139.74, 35.71)},
            warnings.append,
        )

        self.assertEqual({"lon": 139.72, "lat": 35.695}, center)
        self.assertEqual(
            ["OSM regional mirror relation/9 lacks member way/3; center may be inaccurate"],
            warnings,
        )


if __name__ == "__main__":
    unittest.main()
