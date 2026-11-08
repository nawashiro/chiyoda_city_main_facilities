import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.facility_data import _write_json
from src.osm_maintenance import update
from src.wikidata_retrieval import collect_qids, run_wikidata_retrieval, WIKIDATA_API

from tests.test_osm_maintenance import A, B, judgement, query, ledger, document, place, raw, raw_element


def raw_osm(*names, prefix='Q'):
    elements = [{'type': 'node', 'id': index, 'lon': 139.74, 'lat': 35.68,
                 'tags': {'name': name, 'wikidata': f'{prefix}{index}'}}
                for index, name in enumerate(names, start=1)]
    return {'version': '1', 'elements': elements}


class WikidataRetrievalTests(unittest.TestCase):
    def test_collect_qids_deduplicates_sorts_and_takes_both_tag_keys(self):
        raw = raw_osm('a', 'b', 'c')
        raw['elements'][1]['tags'] = {'name': 'b', 'operator:wikidata': 'Q2'}
        self.assertEqual(['Q1', 'Q2', 'Q3'], collect_qids(raw))
        raw['elements'][1]['tags'] = {'name': 'b', 'wikidata': 'Q1'}
        self.assertEqual(['Q1', 'Q3'], collect_qids(raw))

    def test_retrieval_pages_writes_raw_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_json(root / 'imports/openstreetmap/raw.json', raw_osm(*[f'n{i}' for i in range(1, 56)]))
            calls = []

            def fetch(url):
                calls.append(url)
                ids = url.rsplit('ids=', 1)[1].split('&')[0].replace('%7C', '|').split('|')
                return json.dumps({'entities': {identifier: {'id': identifier} for identifier in ids}}).encode()

            raw_path = run_wikidata_retrieval(root, '2026-11-08T00:00:00+00:00', fetch)
            self.assertEqual(2, len(calls))  # 55 QIDs over a 50-QID page size
            self.assertNotIn('Q55', calls[0])
            document = json.loads(raw_path.read_text())
            self.assertEqual(55, len(document['entities']))
            self.assertEqual('2026-11-08T00:00:00+00:00', document['retrievedAt'])
            metadata = json.loads((root / 'imports/wikidata/retrieval.json').read_text())
            self.assertEqual({'sourceId': 'wikidata', 'retrievedAt': '2026-11-08T00:00:00+00:00',
                              'endpoint': WIKIDATA_API, 'qidCount': 55, 'pages': 2,
                              'rawSha256': hashlib.sha256(raw_path.read_bytes()).hexdigest()}, metadata)

    def test_retrieval_without_qids_writes_empty_mirror(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            osm = raw_osm('x')
            osm['elements'][0]['tags'] = {'name': 'x'}
            _write_json(root / 'imports/openstreetmap/raw.json', osm)
            raw_path = run_wikidata_retrieval(root, 'at', lambda url: (_ for _ in ()).throw(AssertionError('unexpected fetch')))
            self.assertEqual({'sourceId': 'wikidata', 'retrievedAt': 'at', 'entities': {}}, json.loads(raw_path.read_text()))


class UpdateWikidataTests(unittest.TestCase):
    def setup_root(self, directory):
        root = Path(directory)
        _write_json(root / 'inputs/facilities.json', {'queries': [query(), query(B, '別施設', coordinates=[139.751, 35.69])]})
        _write_json(root / 'data/places.jsonld', document(place(), place(B)))
        _write_json(root / 'data/osm-decisions.json', ledger())
        _write_json(root / 'imports/openstreetmap/raw.json', raw(raw_element(), {**raw_element(2, '別施設'), 'lon': 139.751}))
        payload = (root / 'imports/openstreetmap/raw.json').read_bytes()
        _write_json(root / 'imports/openstreetmap/retrieval.json', {'rawSha256': hashlib.sha256(payload).hexdigest(), 'rawVersion': '20261027'})
        return root

    def _update(self, root, wikidata):
        return update(root, refresh=True, retrieve=lambda *args, **kwargs: None, wikidata=wikidata,
                      judge=lambda ev: judgement('node/1') if ev['target']['id'] == A else judgement('node/2', .5))

    def test_failed_wikidata_retrieval_does_not_block_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            before = (root / 'data/places.jsonld').read_bytes()
            saved = self._update(root, lambda *a, **k: (_ for _ in ()).throw(OSError('Wikidata down')))
            self.assertNotEqual(before, (root / 'data/places.jsonld').read_bytes())
            self.assertIn(A, saved['facilities'])

    def test_refresh_retrieves_wikidata_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            calls = []
            self._update(root, lambda r, at: calls.append(r))
            self.assertEqual([root], calls)


if __name__ == '__main__':
    unittest.main()
