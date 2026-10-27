import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.osm_mirror import coordinate_matcher, relation_out_center


class OsmRetrievalTests(unittest.TestCase):
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
