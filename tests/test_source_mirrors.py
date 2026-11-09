import json
import tempfile
import unittest
from pathlib import Path

from src.facility_data import _write_json, build_repository

ROOT = Path(__file__).resolve().parents[1]
A = '019c0000-0000-7000-8000-000000000001'
B = '019c0000-0000-7000-8000-000000000002'
CONTEXT = {'@version': 1.1, 'schema': 'https://schema.org/', 'rdfs': 'http://www.w3.org/2000/01/rdf-schema#'}
OSM = 'https://www.openstreetmap.org/'
WIKIDATA = 'https://www.wikidata.org/entity/'
COORD = [139.75, 35.69]


def place(identifier=A, osm=None, qid=None):
    p = {'@id': f'urn:uuid:{identifier}', '@type': ['schema:Place'],
         'schema:geo': {'@type': 'schema:GeoCoordinates', 'schema:longitude': COORD[0], 'schema:latitude': COORD[1]}}
    if osm:
        p['rdfs:seeAlso'] = [OSM + osm] + ([WIKIDATA + qid] if qid else [])
    return p


def raw_element(number, name, lon, lat, **tags):
    return {'type': 'node', 'id': number, 'lon': lon, 'lat': lat, 'tags': {'name': name, **tags}}


class SourceMirrorTests(unittest.TestCase):
    def setup_root(self, directory):
        root = Path(directory)
        _write_json(root / 'data/places.jsonld', {
            '@context': CONTEXT,
            '@graph': [
                place(A, osm='node/1', qid='Q1'),
                place(B, osm='node/2', qid='Q2'),
            ],
        })
        _write_json(root / 'imports/openstreetmap/raw.json', {
            'version': '20261109',
            'elements': [
                raw_element(1, '千代田相談支援センター', *COORD, wikidata='Q1'),
                raw_element(2, '別施設', *[139.751, 35.69]),
                raw_element(3, '近隣のレストラン', *COORD),
            ],
        })
        _write_json(root / 'imports/wikidata/raw.json', {
            'sourceId': 'wikidata', 'retrievedAt': '2026-11-09T00:00:00Z',
            'entities': {
                'Q1': {'id': 'Q1', 'claims': {}},
                'Q2': {'id': 'Q2', 'claims': {}},
                'Q499071': {'id': 'Q499071', 'claims': {}},
            },
        })
        return root

    def test_mirrors_hold_only_associated_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            build_repository(root)
            osm = json.loads((root / 'site/mirrors/osm.json').read_text())
            self.assertEqual(['node/1', 'node/2'], [f"{e['type']}/{e['id']}" for e in osm['elements']])
            self.assertIn('tags', osm['elements'][0])
            wikidata = json.loads((root / 'site/mirrors/wikidata.json').read_text())
            self.assertEqual({'Q1', 'Q2'}, set(wikidata['entities']))
            raw = json.loads((root / 'imports/openstreetmap/raw.json').read_text())
            self.assertEqual(3, len(raw['elements']))
            raw_wikidata = json.loads((root / 'imports/wikidata/raw.json').read_text())
            self.assertEqual({'Q1', 'Q2', 'Q499071'}, set(raw_wikidata['entities']))

    def test_new_association_appears_in_next_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            build_repository(root)
            document = json.loads((root / 'data/places.jsonld').read_text())
            document['@graph'].append(place('019c0000-0000-7000-8000-000000000003', osm='node/3', qid='Q3'))
            document['@graph'].pop(0)
            _write_json(root / 'data/places.jsonld', document)
            build_repository(root)
            osm = json.loads((root / 'site/mirrors/osm.json').read_text())
            self.assertEqual(['node/2', 'node/3'], [f"{e['type']}/{e['id']}" for e in osm['elements']])
            wikidata = json.loads((root / 'site/mirrors/wikidata.json').read_text())
            self.assertEqual({'Q2'}, set(wikidata['entities']))  # Q3 is not in the imports pool until a Wikidata refresh fetches it

    def test_wikidata_mirror_pages_are_preserved_without_source_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            imports_raw = (root / 'imports/wikidata/raw.json').read_bytes()
            build_repository(root)
            self.assertEqual({'sourceId', 'retrievedAt', 'entities'}, set(json.loads(imports_raw)))
            self.assertNotEqual((root / 'site/mirrors/wikidata.json').read_bytes(), imports_raw)


if __name__ == '__main__':
    unittest.main()
