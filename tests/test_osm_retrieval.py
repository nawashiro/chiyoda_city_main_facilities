import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.osm_mirror import coordinate_matcher, query_region, relation_out_center, selection_predicate
from src.retrieve_osm import run_osm_retrieval


CHIYODA_BBOX = (35.6680, 139.7290, 35.7060, 139.7840)


def predicate(*, coordinates=((139.75, 35.69),), qids=frozenset(), selected=frozenset()):
    coordinates = [list(point) for point in coordinates]
    return selection_predicate(set(selected), set(qids), query_region(coordinates), CHIYODA_BBOX, coordinate_matcher(coordinates))


class SelectionPredicateTests(unittest.TestCase):
    def test_query_region_covers_the_fifty_metre_radius(self):
        region = query_region([[139.75, 35.69]])

        self.assertLess(region[0], 35.69 - 50 / 111320)
        self.assertGreater(region[2], 35.69 + 50 / 111320)
        self.assertLess(region[1], 139.75 - 50 / (111320 * 0.812))
        self.assertGreater(region[3], 139.75 + 50 / (111320 * 0.812))
        self.assertIsNone(query_region([]))

    def test_position_keeps_the_exact_fifty_metre_boundary(self):
        selectable = predicate()

        self.assertTrue(selectable("node", 1, {"lon": 139.75, "lat": 35.6904490}, lambda: None))
        self.assertFalse(selectable("node", 1, {"lon": 139.75, "lat": 35.6908}, lambda: None))
        self.assertFalse(selectable("node", 1, {"lon": 139.75, "lat": 35.691}, lambda: None))

    def test_selected_id_is_kept_outside_both_regions(self):
        selectable = predicate(selected={("node", 7)})

        self.assertTrue(selectable("node", 7, {"lon": 0.0, "lat": 0.0}, self.fail))

    def test_wikidata_match_is_limited_to_the_chiyoda_bbox(self):
        selectable = predicate(qids={"Q1"})

        self.assertTrue(selectable("node", 1, {"lon": 139.75, "lat": 35.69}, lambda: "Q1"))
        self.assertFalse(selectable("node", 1, {"lon": 139.80, "lat": 35.72}, lambda: "Q1"))

    def test_nearby_and_selected_elements_do_not_read_wikidata(self):
        selectable = predicate(qids={"Q1"}, selected={("node", 7)})

        self.assertTrue(selectable("node", 7, {"lon": 0.0, "lat": 0.0}, self.fail))
        self.assertTrue(selectable("node", 1, {"lon": 139.75, "lat": 35.69}, self.fail))

    def test_way_center_uses_the_same_position_rules(self):
        selectable = predicate()

        self.assertTrue(selectable("way", 1, {"lon": 139.75, "lat": 35.6904}, lambda: None))
        self.assertFalse(selectable("way", 1, {"lon": 139.75, "lat": 35.6908}, lambda: None))
        self.assertFalse(selectable("way", 2, {"lon": 0.0, "lat": 0.0}, lambda: None))

    def test_missing_coordinates_leave_only_id_and_wikidata_rules(self):
        selectable = predicate(coordinates=(), qids={"Q1"}, selected={("node", 7)})

        self.assertTrue(selectable("node", 7, {"lon": 0.0, "lat": 0.0}, self.fail))
        self.assertTrue(selectable("node", 1, {"lon": 139.75, "lat": 35.69}, lambda: "Q1"))
        self.assertFalse(selectable("node", 2, {"lon": 139.75, "lat": 35.69}, lambda: None))


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
