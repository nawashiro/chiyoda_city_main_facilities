import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from src.commons_files import commons_file_page
from src.fac_cli import main as fac_main
from src.facility_data import _write_json

A = '019c0000-0000-7000-8000-000000000001'
COORD = [139.75, 35.69]
CONTEXT = {'@version': 1.1, 'schema': 'https://schema.org/', 'rdfs': 'http://www.w3.org/2000/01/rdf-schema#'}


def setup_root(directory):
    root = Path(directory)
    _write_json(root / 'data/places.jsonld', {'@context': CONTEXT, '@graph': [{
        '@id': f'urn:uuid:{A}', '@type': ['schema:Place'],
        'schema:geo': {'@type': 'schema:GeoCoordinates', 'schema:longitude': COORD[0], 'schema:latitude': COORD[1]},
    }]})
    _write_json(root / 'inputs/facilities.json', {'queries': [{
        'id': A, 'name': '千代田施設', 'coordinates': COORD,
    }]})
    _write_json(root / 'imports/commons/raw.json', {'files': {
        'File:Manual.jpg': {'url': 'https://upload.wikimedia.org/wikipedia/commons/m/manual.jpg',
                            'license': 'CC0', 'licenseUrl': None, 'artist': '手動作者'},
    }})
    (root / 'site').mkdir()
    (root / 'site/dataset.jsonld').write_bytes(b'previous publication')
    return root


def run_fac(*argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = fac_main(list(argv))
    return code, stdout.getvalue(), stderr.getvalue()


def recorded_image(root):
    document = json.loads((root / 'data/places.jsonld').read_text())
    return document['@graph'][0].get('schema:image')


class ImageCommandTests(unittest.TestCase):
    def test_set_writes_the_canonical_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = setup_root(directory)
            code, stdout, _ = run_fac('image', 'set', str(root), A, 'File:Manual.jpg')
            self.assertEqual(0, code)
            self.assertIn(f'image={commons_file_page("File:Manual.jpg")}', stdout)
            self.assertEqual({'@id': commons_file_page('File:Manual.jpg')}, recorded_image(root))
            self.assertEqual(b'previous publication', (root / 'site/dataset.jsonld').read_bytes())

    def test_set_accepts_and_normalizes_a_page_url(self):
        with tempfile.TemporaryDirectory() as directory:
            root = setup_root(directory)
            code, _, _ = run_fac('image', 'set', str(root), A,
                                 'https://commons.wikimedia.org/wiki/File:Manual.jpg?uselang=ja')
            self.assertEqual(0, code)
            self.assertEqual({'@id': commons_file_page('File:Manual.jpg')}, recorded_image(root))

    def test_set_replaces_an_existing_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = setup_root(directory)
            self.assertEqual(0, run_fac('image', 'set', str(root), A, 'File:First.jpg')[0])
            self.assertEqual(0, run_fac('image', 'set', str(root), A, 'File:Second.jpg')[0])
            self.assertEqual({'@id': commons_file_page('File:Second.jpg')}, recorded_image(root))

    def test_set_rejects_unknown_place_and_non_file_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = setup_root(directory)
            for arguments in (
                ('image', 'set', str(root), '019c0000-0000-7000-8000-000000000099', 'File:Manual.jpg'),
                ('image', 'set', str(root), A, 'Category:千代田区'),
                ('image', 'set', str(root), A, 'https://upload.wikimedia.org/wikipedia/commons/m/manual.jpg'),
            ):
                with self.subTest(arguments=arguments):
                    code, stdout, _ = run_fac(*arguments)
                    self.assertEqual(1, code)
                    self.assertIn('ERROR', stdout)

    def test_clear_removes_the_reference_and_keeps_the_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = setup_root(directory)
            run_fac('image', 'set', str(root), A, 'File:Manual.jpg')
            code, _, _ = run_fac('image', 'clear', str(root), A)
            self.assertEqual(0, code)
            self.assertIsNone(recorded_image(root))
            self.assertEqual(b'previous publication', (root / 'site/dataset.jsonld').read_bytes())
            code, stdout, _ = run_fac('image', 'clear', str(root), A)
            self.assertEqual(1, code)
            self.assertIn('ERROR', stdout)

    def test_review_shows_resolved_and_unresolved_references(self):
        with tempfile.TemporaryDirectory() as directory:
            root = setup_root(directory)
            run_fac('image', 'set', str(root), A, 'File:Manual.jpg')
            code, stdout, _ = run_fac('image', 'review', str(root))
            self.assertEqual(0, code)
            self.assertIn('resolved 千代田施設', stdout)
            self.assertIn('file=File:Manual.jpg', stdout)
            self.assertIn('license=CC0', stdout)
            self.assertIn('artist=手動作者', stdout)

            commons = json.loads((root / 'imports/commons/raw.json').read_text())
            commons['files'].pop('File:Manual.jpg')
            _write_json(root / 'imports/commons/raw.json', commons)
            code, stdout, _ = run_fac('image', 'review', str(root))
            self.assertEqual(0, code)
            self.assertIn('unresolved 千代田施設', stdout)
            self.assertIn('file=File:Manual.jpg', stdout)


if __name__ == '__main__':
    unittest.main()
