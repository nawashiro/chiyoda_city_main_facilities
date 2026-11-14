import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.facility_data import _write_json
from src.commons_retrieval import COMMONS_API, collect_file_names, run_commons_retrieval
from src.osm_maintenance import update

from tests.test_osm_maintenance import A, B, document, judgement, ledger, place, query, raw, raw_element


def osm_raw():
    return raw(
        {**raw_element(1, '千代田施設'), 'tags': {'name': '千代田施設', 'wikimedia_commons': 'File:Chiyoda.jpg'}},
        {**raw_element(2, '別施設'), 'tags': {'name': '別施設', 'wikimedia_commons': 'Category:別施設'}},
        {**raw_element(3, '紐付けのないカフェ'), 'tags': {'name': '紐付けのないカフェ', 'wikimedia_commons': 'File:Cafe.jpg'}},
        raw_element(4, 'タグのない要素'),
    )


def wikidata_raw():
    return {'sourceId': 'wikidata', 'retrievedAt': 'at', 'entities': {
        'Q1': {'id': 'Q1', 'claims': {'P18': [
            {'mainsnak': {'datavalue': {'value': 'Chiyoda-first.jpg'}}},
            {'mainsnak': {'datavalue': {'value': 'Chiyoda-second.jpg'}}},
        ]}},
        'Q2': {'id': 'Q2', 'claims': {'P18': [{'mainsnak': {'datavalue': {'value': 'File:別施設.jpg'}}}]}},
        'Q999': {'id': 'Q999', 'claims': {'P18': [{'mainsnak': {'datavalue': {'value': 'Unlinked.jpg'}}}]}},
    }}


def canonical():
    return document(place(A, osm='node/1', qid='Q1'), place(B, osm='node/2', qid='Q2'))


def commons_response(titles):
    pages = {}
    for title in titles:
        if title == 'File:Chiyoda.jpg':
            pages[1] = {'title': title, 'imageinfo': [{'url': 'https://upload.wikimedia.org/wikipedia/commons/a/Chiyoda.jpg?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original',
                'extmetadata': {'LicenseShortName': {'value': 'CC BY-SA 4.0'},
                                'LicenseUrl': {'value': 'https://creativecommons.org/licenses/by-sa/4.0/'},
                                'Artist': {'value': '<a href="https://commons.wikimedia.org/" title="foo">作者 &amp; 共同</a>'}}}]}
        elif title == 'File:別施設.jpg':
            pages[2] = {'title': title, 'imageinfo': [{'url': 'https://upload.wikimedia.org/wikipedia/commons/b/other.jpg',
                'extmetadata': {'LicenseShortName': {'value': 'Attribution'}}}]}
        elif title == 'File:Gone.jpg':
            pages[3] = {'title': title, 'missing': ''}
    return json.dumps({'query': {'pages': pages}}).encode()


class CollectFileNamesTests(unittest.TestCase):
    def test_collects_associated_p18_and_file_tags_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_json(root / 'data/places.jsonld', canonical())
            _write_json(root / 'imports/openstreetmap/raw.json', osm_raw())
            _write_json(root / 'imports/wikidata/raw.json', wikidata_raw())
            self.assertEqual(['File:Chiyoda-first.jpg', 'File:Chiyoda-second.jpg', 'File:Chiyoda.jpg', 'File:別施設.jpg'], collect_file_names(root))

    def test_missing_imports_yield_no_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_json(root / 'data/places.jsonld', canonical())
            self.assertEqual([], collect_file_names(root))


class CommonsRetrievalTests(unittest.TestCase):
    def setup_root(self, directory):
        root = Path(directory)
        _write_json(root / 'data/places.jsonld', canonical())
        _write_json(root / 'imports/openstreetmap/raw.json', osm_raw())
        _write_json(root / 'imports/wikidata/raw.json', wikidata_raw())
        return root

    def test_retrieval_writes_files_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)

            def fetch(url):
                titles = parse_qs(urlparse(url).query)['titles'][0].split('|')
                return commons_response(titles)

            raw_path = run_commons_retrieval(root, '2026-11-14T00:00:00+00:00', fetch)
            document = json.loads(raw_path.read_text())
            self.assertEqual(['File:Chiyoda.jpg', 'File:別施設.jpg'], sorted(document['files']))
            chiyoda = document['files']['File:Chiyoda.jpg']
            self.assertEqual('https://upload.wikimedia.org/wikipedia/commons/a/Chiyoda.jpg', chiyoda['url'])
            self.assertEqual('https://creativecommons.org/licenses/by-sa/4.0/', chiyoda['licenseUrl'])
            self.assertEqual('作者 & 共同', chiyoda['artist'])
            other = document['files']['File:別施設.jpg']
            self.assertIsNone(other['licenseUrl'])
            self.assertIsNone(other['artist'])
            metadata = json.loads((root / 'imports/commons/retrieval.json').read_text())
            self.assertEqual({'sourceId': 'commons', 'retrievedAt': '2026-11-14T00:00:00+00:00',
                              'endpoint': COMMONS_API, 'fileCount': 4, 'pages': 1,
                              'rawSha256': hashlib.sha256(raw_path.read_bytes()).hexdigest()}, metadata)

    def test_paging_over_fifty_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            wikidata = {'sourceId': 'wikidata', 'retrievedAt': 'at', 'entities': {
                f'Q{i}': {'id': f'Q{i}', 'claims': {'P18': [{'mainsnak': {'datavalue': {'value': f'p{i}.jpg'}}}]}} for i in range(1, 56)}}
            _write_json(root / 'imports/wikidata/raw.json', wikidata)
            place_a, place_b = place(A, osm='node/1'), place(B, osm='node/2')
            place_a['rdfs:seeAlso'] += [f'https://www.wikidata.org/entity/Q{i}' for i in range(1, 28)]
            place_b['rdfs:seeAlso'] += [f'https://www.wikidata.org/entity/Q{i}' for i in range(28, 56)]
            _write_json(root / 'data/places.jsonld', document(place_a, place_b))
            calls = []

            def fetch(url):
                calls.append(url)
                titles = parse_qs(urlparse(url).query)['titles'][0].split('|')
                return commons_response(titles)

            run_commons_retrieval(root, 'at', fetch)
            self.assertEqual(2, len(calls))
            self.assertNotIn('File:p55.jpg', calls[0])

    def test_no_files_makes_no_request(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_json(root / 'data/places.jsonld', canonical())
            raw_path = run_commons_retrieval(root, 'at', lambda url: (_ for _ in ()).throw(AssertionError('unexpected fetch')))
            self.assertEqual({'sourceId': 'commons', 'retrievedAt': 'at', 'files': {}}, json.loads(raw_path.read_text()))


class UpdateCommonsTests(unittest.TestCase):
    def setup_root(self, directory):
        root = Path(directory)
        _write_json(root / 'inputs/facilities.json', {'queries': [query(), query(B, '別施設', coordinates=[139.751, 35.69])]})
        _write_json(root / 'data/places.jsonld', document(place(), place(B)))
        _write_json(root / 'data/osm-decisions.json', ledger())
        _write_json(root / 'imports/openstreetmap/raw.json', raw(raw_element(), {**raw_element(2, '別施設'), 'lon': 139.751}))
        payload = (root / 'imports/openstreetmap/raw.json').read_bytes()
        _write_json(root / 'imports/openstreetmap/retrieval.json', {'rawSha256': hashlib.sha256(payload).hexdigest(), 'rawVersion': '20261027'})
        return root

    def test_failed_commons_retrieval_does_not_block_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            before = (root / 'data/places.jsonld').read_bytes()
            saved = update(root, refresh=True, retrieve=lambda *args, **kwargs: None, wikidata=None,
                           commons=lambda *a, **k: (_ for _ in ()).throw(OSError('Commons down')),
                           judge=lambda ev: judgement('node/1') if ev['target']['id'] == A else judgement('node/2'))
            self.assertNotEqual(before, (root / 'data/places.jsonld').read_bytes())
            self.assertIn(A, saved['facilities'])

    def test_refresh_retrieves_commons_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            calls = []
            update(root, refresh=True, retrieve=lambda *args, **kwargs: None, wikidata=None,
                   commons=lambda r, at: calls.append(r),
                   judge=lambda ev: judgement('node/1') if ev['target']['id'] == A else judgement('node/2'))
            self.assertEqual([root], calls)


if __name__ == '__main__':
    unittest.main()
