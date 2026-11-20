import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.facility_data import _write_json
from src.commons_retrieval import COMMONS_API, _artist_text, _query_files, collect_categories, collect_file_names, resolve_categories, run_commons_retrieval
from src.osm_maintenance import update

from tests.test_osm_maintenance import A, B, document, judgement, ledger, place, query, raw, raw_element

FIXTURES = Path(__file__).parent / 'fixtures'
CATEGORY_PAGE_IMAGES = {'Category:代表あり': '代表.jpg'}
CATEGORY_MEMBERS = {'Category:別施設': ['File:別施設.jpg'], 'Category:空': []}


def osm_mirror():
    return {'elements': [
        {'type': 'node', 'id': 1, 'lon': 139.74, 'lat': 35.68, 'tags': {'name': '千代田施設', 'wikimedia_commons': 'File:Chiyoda.jpg'}},
        {'type': 'node', 'id': 2, 'lon': 139.751, 'lat': 35.69, 'tags': {'name': '別施設', 'wikimedia_commons': 'Category:別施設'}},
        {'type': 'node', 'id': 3, 'lon': 139.752, 'lat': 35.69, 'tags': {'name': '代表施設', 'wikimedia_commons': 'Category:代表あり'}},
        {'type': 'node', 'id': 4, 'lon': 139.753, 'lat': 35.69, 'tags': {'name': '空施設', 'wikimedia_commons': 'Category:空'}},
        raw_element(5, 'タグのない要素'),
    ]}


def wikidata_mirror():
    return {'sourceId': 'wikidata', 'retrievedAt': 'at', 'entities': {
        'Q1': {'id': 'Q1', 'claims': {'P18': [
            {'mainsnak': {'datavalue': {'value': 'Chiyoda-first.jpg'}}},
            {'mainsnak': {'datavalue': {'value': 'Chiyoda-second.jpg'}}},
        ]}},
        'Q2': {'id': 'Q2', 'claims': {'P18': [{'mainsnak': {'datavalue': {'value': 'File:別施設.jpg'}}}]}},
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
        elif title == 'File:代表.jpg':
            pages[4] = {'title': title, 'imageinfo': [{'url': 'https://upload.wikimedia.org/wikipedia/commons/e/代表.jpg',
                'extmetadata': {'LicenseShortName': {'value': 'CC0'}, 'Artist': {'value': '代表作者'}}}]}
        elif title == 'File:Gone.jpg':
            pages[3] = {'title': title, 'missing': ''}
    return json.dumps({'query': {'pages': pages}}).encode()


class FakeCommons:
    def __init__(self):
        self.calls = []

    def __call__(self, url):
        query = parse_qs(urlparse(url).query)
        self.calls.append(query)
        if query.get('prop') == ['pageimages']:
            pages = {}
            for index, title in enumerate(query['titles'][0].split('|')):
                page = {'title': title}
                if title in CATEGORY_PAGE_IMAGES:
                    page['pageimage'] = CATEGORY_PAGE_IMAGES[title]
                pages[str(index)] = page
            return json.dumps({'query': {'pages': pages}}).encode()
        if query.get('list') == ['categorymembers']:
            members = CATEGORY_MEMBERS.get(query['cmtitle'][0], [])
            return json.dumps({'query': {'categorymembers': [{'ns': 6, 'title': title} for title in members]}}).encode()
        return commons_response(query['titles'][0].split('|'))


class CollectFileNamesTests(unittest.TestCase):
    def test_collects_mirrored_p18_and_file_tags(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_json(root / 'site/mirrors/osm.json', osm_mirror())
            _write_json(root / 'site/mirrors/wikidata.json', wikidata_mirror())
            self.assertEqual(['File:Chiyoda-first.jpg', 'File:Chiyoda-second.jpg', 'File:Chiyoda.jpg', 'File:別施設.jpg'], collect_file_names(root))

    def test_collects_category_tags(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_json(root / 'site/mirrors/osm.json', osm_mirror())
            self.assertEqual(['Category:代表あり', 'Category:別施設', 'Category:空'], collect_categories(root))

    def test_missing_mirrors_yield_no_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_json(root / 'data/places.jsonld', canonical())
            self.assertEqual([], collect_file_names(root))
            self.assertEqual([], collect_categories(root))


class ResolveCategoriesTests(unittest.TestCase):
    def test_page_images_are_requested_fifty_at_a_time_and_mapped_back(self):
        categories = [f'Category:分類{index:02d}' for index in range(51)]
        calls = []

        def fetch(url):
            requested = parse_qs(urlparse(url).query)
            calls.append(requested)
            titles = requested['titles'][0].split('|')
            normalized = [{'from': title, 'to': title + ' 正規化'} for title in titles]
            redirects = [{'from': item['to'], 'to': item['from'] + ' 転送'} for item in normalized]
            pages = {str(index): {'title': title + ' 転送', 'pageimage': title + ' 画像.jpg'} for index, title in enumerate(titles)}
            return json.dumps({'query': {'normalized': normalized, 'redirects': redirects, 'pages': pages}}).encode()

        resolved = resolve_categories(categories, fetch)

        self.assertEqual(2, len(calls))
        self.assertTrue(all(len(call['titles'][0].split('|')) <= 50 for call in calls))
        self.assertTrue(all('list' not in call for call in calls))
        self.assertEqual({category: f'File:{category} 画像.jpg' for category in categories}, resolved)

    def test_category_members_fallback_selects_the_name_match(self):
        members = json.loads((FIXTURES / 'commons-category-members.json').read_text())

        def fetch(url):
            requested = parse_qs(urlparse(url).query)
            if requested.get('prop') == ['pageimages']:
                return json.dumps({'query': {'pages': {}}}).encode()
            self.assertEqual(['Category:MAAch ecute Kanda-Manseibashi'], requested['cmtitle'])
            return json.dumps({'query': {'categorymembers': [{'ns': 6, 'title': title} for title in members]}}).encode()

        category = 'Category:MAAch ecute Kanda-Manseibashi'
        self.assertEqual({category: 'File:MAAch ecute Kanda Manseibashi.jpg'}, resolve_categories([category], fetch))

    def test_category_without_a_name_match_uses_the_first_member(self):
        def fetch(url):
            requested = parse_qs(urlparse(url).query)
            if requested.get('prop') == ['pageimages']:
                return json.dumps({'query': {'pages': {}}}).encode()
            return json.dumps({'query': {'categorymembers': [{'title': 'File:Alpha.jpg'}, {'title': 'File:Beta.jpg'}]}}).encode()

        self.assertEqual({'Category:関係なし': 'File:Alpha.jpg'}, resolve_categories(['Category:関係なし'], fetch))

    def test_category_without_images_is_not_recorded(self):
        calls = []

        def fetch(url):
            requested = parse_qs(urlparse(url).query)
            calls.append(requested)
            if requested.get('prop') == ['pageimages']:
                return json.dumps({'query': {
                    'normalized': [{'from': 'Category:代表', 'to': 'Category:代表あり'}],
                    'pages': {'1': {'title': 'Category:代表あり', 'pageimage': '代表.jpg'}}}}).encode()
            return json.dumps({'query': {'categorymembers': []}}).encode()

        resolved = resolve_categories(['Category:代表', 'Category:空'], fetch)

        self.assertEqual({'Category:代表': 'File:代表.jpg'}, resolved)
        self.assertEqual(1, sum(1 for requested in calls if requested.get('list') == ['categorymembers']))


class CommonsRetrievalTests(unittest.TestCase):
    def setup_root(self, directory):
        root = Path(directory)
        _write_json(root / 'data/places.jsonld', canonical())
        _write_json(root / 'site/mirrors/osm.json', osm_mirror())
        _write_json(root / 'site/mirrors/wikidata.json', wikidata_mirror())
        return root

    def test_retrieval_writes_files_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            fake = FakeCommons()

            raw_path = run_commons_retrieval(root, '2026-11-14T00:00:00+00:00', fake)
            document = json.loads(raw_path.read_text())
            self.assertEqual(['File:Chiyoda.jpg', 'File:代表.jpg', 'File:別施設.jpg'], sorted(document['files']))
            chiyoda = document['files']['File:Chiyoda.jpg']
            self.assertEqual('https://upload.wikimedia.org/wikipedia/commons/a/Chiyoda.jpg', chiyoda['url'])
            self.assertEqual('https://creativecommons.org/licenses/by-sa/4.0/', chiyoda['licenseUrl'])
            self.assertEqual('作者 & 共同', chiyoda['artist'])
            other = document['files']['File:別施設.jpg']
            self.assertIsNone(other['licenseUrl'])
            self.assertIsNone(other['artist'])
            self.assertEqual('代表作者', document['files']['File:代表.jpg']['artist'])
            self.assertEqual({'Category:別施設': 'File:別施設.jpg', 'Category:代表あり': 'File:代表.jpg'}, document['categories'])
            metadata = json.loads((root / 'imports/commons/retrieval.json').read_text())
            self.assertEqual({'sourceId': 'commons', 'retrievedAt': '2026-11-14T00:00:00+00:00',
                              'endpoint': COMMONS_API, 'fileCount': 5, 'pages': 1,
                              'rawSha256': hashlib.sha256(raw_path.read_bytes()).hexdigest()}, metadata)

    def test_paging_over_fifty_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            _write_json(root / 'site/mirrors/wikidata.json', {'sourceId': 'wikidata', 'retrievedAt': 'at', 'entities': {
                f'Q{i}': {'id': f'Q{i}', 'claims': {'P18': [{'mainsnak': {'datavalue': {'value': f'p{i}.jpg'}}}]}} for i in range(1, 56)}})
            fake = FakeCommons()

            run_commons_retrieval(root, 'at', fake)
            image_calls = [requested for requested in fake.calls if requested.get('prop') == ['imageinfo']]
            self.assertEqual(2, len(image_calls))
            self.assertNotIn('File:p55.jpg', image_calls[0]['titles'][0])

    def test_no_files_makes_no_request(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_json(root / 'data/places.jsonld', canonical())
            raw_path = run_commons_retrieval(root, 'at', lambda url: (_ for _ in ()).throw(AssertionError('unexpected fetch')))
            self.assertEqual({'sourceId': 'commons', 'retrievedAt': 'at', 'files': {}, 'categories': {}}, json.loads(raw_path.read_text()))


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


class QueryFilesTests(unittest.TestCase):
    def test_file_metadata_is_keyed_by_the_page_title(self):
        def fetch(url):
            return json.dumps({'query': {
                'normalized': [{'from': 'File:Chiyoda_写真.jpg', 'to': 'File:Chiyoda 写真.jpg'}],
                'pages': {'1': {'title': 'File:Chiyoda 写真.jpg', 'imageinfo': [{
                    'url': 'https://upload.wikimedia.org/wikipedia/commons/a/Chiyoda.jpg',
                    'extmetadata': {'LicenseShortName': {'value': 'CC0'}, 'Artist': {'value': '作者'}}}]}}}}).encode()

        files = _query_files(['File:Chiyoda_写真.jpg'], fetch)

        self.assertEqual(['File:Chiyoda 写真.jpg'], list(files))
        self.assertEqual('作者', files['File:Chiyoda 写真.jpg']['artist'])


class ArtistTextTests(unittest.TestCase):
    def test_hidden_author_text_is_ignored(self):
        extmetadata = {'Artist': {'value': '作者<span style="display: none;">作者</span>'}}
        self.assertEqual('作者', _artist_text(extmetadata))

    def test_unknown_author_placeholder_means_no_author(self):
        for value in ('Unknown author', 'Unknown artist'):
            with self.subTest(value=value):
                self.assertIsNone(_artist_text({'Artist': {'value': value}}))


if __name__ == '__main__':
    unittest.main()
