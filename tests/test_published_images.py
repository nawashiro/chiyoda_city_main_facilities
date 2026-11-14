import json
import tempfile
import unittest
from pathlib import Path

from src.fac_cli import main as fac_main
from src.facility_data import _write_json, build_repository, validate_jsonld_document, validate_published_document

ROOT = Path(__file__).resolve().parents[1]
A = '019c0000-0000-7000-8000-000000000001'
B = '019c0000-0000-7000-8000-000000000002'
C = '019c0000-0000-7000-8000-000000000003'
D = '019c0000-0000-7000-8000-000000000004'
E = '019c0000-0000-7000-8000-000000000005'
COORD = [139.75, 35.69]
CONTEXT = {'@version': 1.1, 'schema': 'https://schema.org/', 'rdfs': 'http://www.w3.org/2000/01/rdf-schema#'}
OSM = 'https://www.openstreetmap.org/'
WIKIDATA = 'https://www.wikidata.org/entity/'


def place(identifier, osm=None, qid=None):
    p = {'@id': f'urn:uuid:{identifier}', '@type': ['schema:Place'],
         'schema:geo': {'@type': 'schema:GeoCoordinates', 'schema:longitude': COORD[0], 'schema:latitude': COORD[1]}}
    if osm:
        p['rdfs:seeAlso'] = [OSM + osm] + ([WIKIDATA + qid] if qid else [])
    return p


def setup_root(directory):
    root = Path(directory)
    _write_json(root / 'data/places.jsonld', {'@context': CONTEXT, '@graph': [
        place(A, osm='node/1', qid='Q1'),
        place(B, osm='node/2', qid='Q2'),
        place(C, osm='node/3'),
        place(D, osm='node/4', qid='Q4'),
        place(E, osm='node/5', qid='Q5'),
    ]})
    _write_json(root / 'imports/openstreetmap/raw.json', {'version': '1', 'elements': [
        {'type': 'node', 'id': number, 'lon': COORD[0], 'lat': COORD[1], 'tags': {'name': f'n{number}', **tags}}
        for number, tags in (
            (1, {'wikidata': 'Q1', 'wikimedia_commons': 'File:Chiyoda.jpg'}),
            (2, {'wikidata': 'Q2', 'wikimedia_commons': 'File:別施設.jpg'}),
            (3, {'wikimedia_commons': 'Category:分類のみ'}),
            (4, {}),
            (5, {}),
        )]})
    _write_json(root / 'imports/wikidata/raw.json', {'sourceId': 'wikidata', 'retrievedAt': 'at', 'entities': {
        'Q1': {'id': 'Q1', 'claims': {'P18': [
            {'mainsnak': {'datavalue': {'value': 'first.jpg'}}},
            {'mainsnak': {'datavalue': {'value': 'second.jpg'}}}]}},
        'Q2': {'id': 'Q2', 'claims': {}},
        'Q4': {'id': 'Q4', 'claims': {'P18': [{'mainsnak': {'datavalue': {'value': 'artistless.jpg'}}}]}},
        'Q5': {'id': 'Q5', 'claims': {'P18': [{'mainsnak': {'datavalue': {'value': 'nameless-license.jpg'}}}]}},
        'Q999': {'id': 'Q999', 'claims': {'P18': [{'mainsnak': {'datavalue': {'value': 'Unlinked.jpg'}}}]}},
    }})
    _write_json(root / 'imports/commons/raw.json', {'sourceId': 'commons', 'retrievedAt': 'at', 'files': {
        'File:first.jpg': {'url': 'https://upload.wikimedia.org/wikipedia/commons/a/first.jpg',
                           'license': 'CC BY-SA 4.0', 'licenseUrl': 'https://creativecommons.org/licenses/by-sa/4.0/',
                           'artist': '作者'},
        'File:second.jpg': {'url': 'https://upload.wikimedia.org/wikipedia/commons/b/second.jpg',
                            'license': 'CC BY 4.0', 'licenseUrl': 'https://creativecommons.org/licenses/by/4.0/', 'artist': '誰か'},
        'File:別施設.jpg': {'url': 'https://upload.wikimedia.org/wikipedia/commons/c/other.jpg',
                          'license': 'Attribution', 'licenseUrl': None, 'artist': '作者'},
        'File:artistless.jpg': {'url': 'https://upload.wikimedia.org/wikipedia/commons/d/none.jpg',
                                'license': 'CC BY-SA 3.0', 'licenseUrl': 'https://creativecommons.org/licenses/by-sa/3.0/', 'artist': None},
        'File:nameless-license.jpg': {'url': 'https://upload.wikimedia.org/wikipedia/commons/e/only-name.jpg',
                                      'license': 'Public domain', 'licenseUrl': None, 'artist': '作者'},
        'File:Unlinked.jpg': {'url': 'https://upload.wikimedia.org/wikipedia/commons/f/unlinked.jpg',
                              'license': 'CC0', 'licenseUrl': None, 'artist': '誰か'},
    }})
    return root


class PublishedImageTests(unittest.TestCase):
    def test_build_enriches_the_published_distribution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = setup_root(directory)
            artifact = build_repository(root)
            published = json.loads(artifact.read_text())
            images = {p['@id'].rsplit(':', 1)[1]: p.get('schema:image') for p in published['@graph']}
            self.assertEqual('https://upload.wikimedia.org/wikipedia/commons/a/first.jpg', images[A]['schema:contentUrl'])
            self.assertEqual(['schema:Person'], images[A]['schema:creator']['@type'])
            self.assertEqual('作者', images[A]['schema:creator']['schema:name'])
            self.assertEqual('Attribution', images[B]['schema:license'])
            self.assertIsNone(images[C])
            self.assertIsNone(images[D])
            self.assertEqual('Public domain', images[E]['schema:license'])

    def test_canonical_source_stays_image_free(self):
        with tempfile.TemporaryDirectory() as directory:
            root = setup_root(directory)
            build_repository(root)
            canonical = json.loads((root / 'data/places.jsonld').read_text())
            self.assertTrue(all('schema:image' not in p for p in canonical['@graph']))

    def test_publish_failure_without_commons_metadata_keeps_canonical_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = setup_root(directory)
            (root / 'imports/commons/raw.json').unlink()
            artifact = build_repository(root)
            published = json.loads(artifact.read_text())
            self.assertTrue(all('schema:image' not in p for p in published['@graph']))
            self.assertEqual((root / 'data/places.jsonld').read_bytes(), artifact.read_bytes())


class ImageValidationTests(unittest.TestCase):
    def valid_document(self, image):
        return {'@context': CONTEXT, '@graph': [{**place(A), 'schema:image': image}]}

    def test_canonical_document_rejects_schema_image(self):
        with self.assertRaises(ValueError):
            validate_jsonld_document(self.valid_document({'@type': ['schema:ImageObject'], 'schema:contentUrl': 'https://x/y.jpg',
                'schema:license': 'CC0', 'schema:creator': {'@type': ['schema:Person'], 'schema:name': '作者'}}))

    def test_published_document_accepts_a_valid_image(self):
        validate_published_document(self.valid_document({'@type': ['schema:ImageObject'], 'schema:contentUrl': 'https://x/y.jpg',
            'schema:license': 'CC0', 'schema:creator': {'@type': ['schema:Person'], 'schema:name': '作者'}}))

    def test_published_document_rejects_incomplete_images(self):
        cases = [
            {'schema:contentUrl': 'https://x/y.jpg', 'schema:license': 'CC0', 'schema:creator': {'@type': ['schema:Person'], 'schema:name': '作者'}},
            {'@type': ['schema:ImageObject'], 'schema:contentUrl': 'http://x/y.jpg', 'schema:license': 'CC0', 'schema:creator': {'@type': ['schema:Person'], 'schema:name': '作者'}},
            {'@type': ['schema:ImageObject'], 'schema:contentUrl': 'https://x/y.jpg', 'schema:license': ' ', 'schema:creator': {'@type': ['schema:Person'], 'schema:name': '作者'}},
            {'@type': ['schema:ImageObject'], 'schema:contentUrl': 'https://x/y.jpg', 'schema:license': 'CC0', 'schema:creator': {'@type': ['schema:Person'], 'schema:name': '  '}},
            {'@type': ['schema:ImageObject'], 'schema:contentUrl': 'https://x/y.jpg', 'schema:license': 'CC0'},
        ]
        for image in cases:
            with self.subTest(image=image):
                with self.assertRaises(ValueError):
                    validate_published_document(self.valid_document(image))


class FacValidationTests(unittest.TestCase):
    def test_published_flag_accepts_images_and_default_stays_canonical(self):
        with tempfile.TemporaryDirectory() as directory:
            root = setup_root(directory)
            build_repository(root)
            enriched = json.loads((root / 'site/places.jsonld').read_text())
            self.assertTrue(any('schema:image' in p for p in enriched['@graph']))
            self.assertEqual(0, fac_main(['jsonld-validate', '--published', str(root / 'site/places.jsonld')]))
            self.assertNotEqual(0, fac_main(['jsonld-validate', str(root / 'site/places.jsonld')]))
            self.assertEqual(0, fac_main(['jsonld-validate', str(root / 'data/places.jsonld')]))


if __name__ == '__main__':
    unittest.main()
