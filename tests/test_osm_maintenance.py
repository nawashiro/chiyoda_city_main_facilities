import copy
import hashlib
import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.facility_data import (_distance_metres, _write_json, build_repository,
                               load_queries, normalize_osm_elements, validate_search_document)
from src.github_osm_review import (CONFIRM, GitHub, apply_confirmations, close_published,
                                   parse_issue, read_confirmations, render_issue)
from src.osm_maintenance import update, verified_snapshot
from src.resolve_osm_candidates import (MODEL, OSM, THRESHOLD, WIKIDATA, apply_decisions,
                                        decide, evidence_for, evidence_hash, request_choice,
                                        resolve, validate_choice)

ROOT = Path(__file__).resolve().parents[1]
A = '019c0000-0000-7000-8000-000000000001'
B = '019c0000-0000-7000-8000-000000000002'
COORD = [139.75, 35.69]
CONTEXT = {'@version': 1.1, 'schema': 'https://schema.org/', 'rdfs': 'http://www.w3.org/2000/01/rdf-schema#'}


def query(identifier=A, name='千代田相談支援センター', **kwargs):
    return {'id': identifier, 'name': name, 'coordinates': COORD[:], **kwargs}


def place(identifier=A, osm=None, qid=None):
    p = {'@id': f'urn:uuid:{identifier}', '@type': ['schema:Place'],
         'schema:geo': {'@type': 'schema:GeoCoordinates', 'schema:longitude': COORD[0], 'schema:latitude': COORD[1]}}
    if osm:
        p['rdfs:seeAlso'] = [OSM + osm] + ([WIKIDATA + qid] if qid else [])
    return p


def raw_element(number=1, name='千代田相談支援センター', **tags):
    return {'type': 'node', 'id': number, 'lon': COORD[0], 'lat': COORD[1], 'tags': {'name': name, **tags}}


def raw(*elements):
    return {'version': '20261027', 'elements': list(elements)}


def document(*places):
    return {'@context': CONTEXT, '@graph': list(places)}


def ledger():
    return {'version': 1, 'facilities': {}}


def judgement(choice='node/1', confidence=.95):
    return {'choice': choice, 'confidence': confidence, 'probabilities': {choice: .99, 'none' if choice != 'none' else 'node/1': .01}, 'usage': {'input_tokens': 100, 'output_tokens': 1}, 'model': MODEL}


def reviewed_entry():
    _, result = resolve(document(place()), [query()], raw(raw_element()), ledger(), lambda _: judgement(confidence=.5))
    entry = result['facilities'][A]
    entry['issue'] = 17
    entry['issueEvidenceHash'] = entry['evidenceHash']
    entry['issueBody'] = render_issue(A, entry)
    return entry


def checked(body, choice='node/1', confirm=True):
    body = body.replace(f'- [ ] `{choice}`', f'- [x] `{choice}`')
    return body.replace(f'- [ ] {CONFIRM}', f'- [x] {CONFIRM}') if confirm else body


class FakeGitHub:
    repository = 'owner/repo'

    def __init__(self, body, *, permission=True):
        self.body = body
        self.permission = permission
        self.comments = []
        self.calls = []
        self.state = 'OPEN'

    def issue(self, number):
        return {'body': self.body, 'state': self.state, 'lastEditedBy': {'login': 'maintainer'},
                'lastEditedAt': '2026-10-27T00:00:00Z', 'url': 'https://github.com/owner/repo/issues/17'}

    def may_write(self, login):
        return self.permission

    def corrective_comment(self, number, message):
        self.comments.append(message)

    def api(self, path, data=None, method=None):
        self.calls.append((path, data, method))
        return []


class EvidenceTests(unittest.TestCase):
    def test_single_input_validation(self):
        q = query(publish=False, qid='Q1')
        self.assertEqual([], validate_search_document({'queries': [q]}))
        self.assertTrue(validate_search_document({'queries': [q, q]}))
        self.assertTrue(validate_search_document({'queries': [{'id': A, 'name': '不足'}]}))
        self.assertTrue(validate_search_document({'queries': [query(coordinates=[float('nan'), 1])]}))
        self.assertTrue(validate_search_document({'queries': [query(publish='false')]}))

    def test_migration_preserves_targets_and_public_geometry(self):
        queries = load_queries(ROOT)
        self.assertEqual(97, len(queries))
        self.assertEqual(97, len({q['id'] for q in queries}))
        published = json.loads((ROOT / 'data/places.jsonld').read_text())
        place_ids = [
            record['@id']
            for record in published['@graph']
            if 'schema:Place' in record.get('@type', [])
        ]
        self.assertEqual(len(place_ids), len(set(place_ids)))
        declared = {f'urn:uuid:{q["id"]}' for q in load_queries(ROOT)}
        self.assertEqual(
            [],
            sorted(set(place_ids) - declared),
            'canonical JSON-LD must only publish declared facilities',
        )
        self.assertFalse(any('schema:identifier' in p for p in published['@graph']))

    def test_hash_ignores_order_but_tracks_identity_fields(self):
        evidence = evidence_for(query(), normalize_osm_elements([raw_element(1), raw_element(2)]), {})
        reordered = copy.deepcopy(evidence)
        reordered['candidates'].reverse()
        self.assertEqual(evidence_hash(evidence), evidence_hash(reordered))
        for mutate in [lambda e: e['target'].update(name='別名'),
                       lambda e: e['target'].update(coordinates=[139.751, 35.69]),
                       lambda e: e['target'].update(qid='Q1'),
                       lambda e: e['candidates'][0].update(qid='Q2'),
                       lambda e: e['candidates'][0]['tags'].update(operator='別事業者')]:
            changed = copy.deepcopy(evidence)
            mutate(changed)
            self.assertNotEqual(evidence_hash(evidence), evidence_hash(changed))
        other = raw_element(fixme='changed', source='timestamp')
        self.assertEqual(evidence_for(query(), normalize_osm_elements([raw_element()]), {}), evidence_for(query(), normalize_osm_elements([other]), {}))

    def test_candidate_boundary_and_typed_ids(self):
        element = raw_element()
        element['lat'] += math.degrees(50 / 6371000)
        evidence = evidence_for(query(), normalize_osm_elements([element]), {})
        self.assertLessEqual(_distance_metres(COORD, [element['lon'], element['lat']]), 50.000001)
        element['lat'] += .00000001
        self.assertEqual([], evidence_for(query(), normalize_osm_elements([element]), {})['candidates'])
        target_place = place(osm='way/1')
        calls = []
        _, result = resolve(document(target_place), [query()], raw(raw_element()), ledger(), lambda e: calls.append(e) or judgement(confidence=.4))
        self.assertEqual(1, len(calls))
        self.assertEqual('needs_review', result['facilities'][A]['status'])


class MatchingTests(unittest.TestCase):
    def test_existing_id_and_unique_qid_skip_jev(self):
        for p, q, element, method in [(place(osm='node/1'), query(), raw_element(name='改名'), 'source_record'),
                                      (place(), query(qid='Q1'), raw_element(wikidata='Q1'), 'qid')]:
            result, decisions = resolve(document(p), [q], raw(element), ledger(), lambda _: self.fail('Jev should not run'))
            self.assertEqual(method, decisions['facilities'][A]['method'])
            self.assertEqual(OSM+'node/1', result['@graph'][0]['rdfs:seeAlso'][0])

    def test_qid_contradiction_and_name_proximity_do_not_bypass_jev(self):
        for p, q, e in [(place(osm='node/1'), query(qid='Q1'), raw_element(wikidata='Q2')),
                        (place(), query(), raw_element())]:
            calls = []
            _, decisions = resolve(document(p), [q], raw(e), ledger(), lambda ev: calls.append(ev) or judgement(confidence=.5))
            self.assertEqual(1, len(calls))
            self.assertEqual('needs_review', decisions['facilities'][A]['status'])

    def test_real_legacy_name_coordinate_links_are_rejudged(self):
        cases = json.loads((ROOT/'tests/fixtures/legacy-name-coordinate-links.json').read_text())
        self.assertEqual(2, len(cases))
        calls = []
        for case in cases:
            identifier = case['query']['id']
            saved = {'version': 1, 'facilities': {identifier: {'reassess': True}}}
            _, result = resolve(document(case['place']), [case['query']], case['raw'], saved,
                                lambda ev: calls.append(ev) or judgement('none', .5))
            self.assertEqual('needs_review', result['facilities'][identifier]['status'])
        self.assertEqual(2, len(calls))

    def test_human_none_wins_over_existing_and_qid_on_same_evidence(self):
        original = document(place(osm='node/1', qid='Q1'))
        q = query(qid='Q1')
        evidence = evidence_for(q, normalize_osm_elements([raw_element(wikidata='Q1')]), original['@graph'][0])
        saved = {'version': 1, 'facilities': {A: {'method': 'human', 'choice': 'none', 'human': {'editor': 'owner'}, 'evidenceHash': evidence_hash(evidence)}}}
        result, decisions = resolve(original, [q], raw(raw_element(wikidata='Q1')), saved, lambda _: self.fail('human choice must win'))
        self.assertNotIn('rdfs:seeAlso', result['@graph'][0])
        self.assertEqual(original['@graph'][0]['schema:geo'], result['@graph'][0]['schema:geo'])
        self.assertEqual('human', decisions['facilities'][A]['method'])

    def test_partial_progress_none_and_missing_candidates_differ(self):
        q2 = query(B, '別施設', coordinates=[139.751, 35.69])
        original = document(place(), place(B))
        result, decisions = resolve(original, [query(), q2], raw(raw_element()), ledger(), lambda _: judgement())
        self.assertIn('rdfs:seeAlso', result['@graph'][0])
        self.assertEqual('no_candidates', decisions['facilities'][B]['status'])
        _, unresolved = resolve(document(place(osm='node/8')), [query()], raw(), ledger(), lambda _: self.fail('no candidates'))
        self.assertEqual('needs_review', unresolved['facilities'][A]['status'])
        result, none = resolve(document(place()), [query()], raw(raw_element()), ledger(), lambda _: judgement('none'))
        self.assertEqual('decided', none['facilities'][A]['status'])
        self.assertEqual('none', none['facilities'][A]['choice'])

    def test_existing_reference_removal_or_replacement_requires_human(self):
        for choice in ['none', 'node/1']:
            original = document(place(osm='node/9', qid='Q9'))
            result, decisions = resolve(original, [query()], raw(raw_element()), ledger(), lambda _: judgement(choice))
            self.assertEqual(original, result)
            self.assertEqual('needs_review', decisions['facilities'][A]['status'])

    def test_conflicting_allocations_are_reviewed_and_direct_apply_rejects(self):
        q2 = query(B, '同一建物内の別施設')
        result, decisions = resolve(document(place(), place(B)), [query(), q2], raw(raw_element()), ledger(), lambda _: judgement())
        self.assertTrue(all(e['status'] == 'needs_review' for e in decisions['facilities'].values()))
        for e in decisions['facilities'].values(): e['status'] = 'decided'
        with self.assertRaisesRegex(ValueError, 'duplicate OSM'):
            apply_decisions(result, [query(), q2], decisions['facilities'])

    def test_replacement_removes_old_wikidata_but_keeps_uuid(self):
        original = document(place(osm='node/9', qid='Q9'))
        _, decisions = resolve(original, [query()], raw(raw_element(wikidata='Q1')), ledger(), lambda _: judgement())
        entry = decisions['facilities'][A]
        entry.update(method='human', status='decided', choice='node/1')
        result = apply_decisions(original, [query()], decisions['facilities'])
        self.assertEqual([OSM+'node/1', WIKIDATA+'Q1'], result['@graph'][0]['rdfs:seeAlso'])
        self.assertEqual(original['@graph'][0]['@id'], result['@graph'][0]['@id'])


class JevTests(unittest.TestCase):
    def response(self, confidence=.9, choice='candidate_0'):
        return {'model': MODEL, 'answers': {'association': {'type': 'choice', 'choice': choice, 'confidence': confidence,
                'probabilities': {'candidate_0': .95, 'none': .05}}}, 'usage': {'input_tokens': 100, 'output_tokens': 1}}

    def test_response_validation_and_threshold(self):
        self.assertEqual('node/1', validate_choice(self.response(), {'candidate_0': 'node/1'})['choice'])
        for confidence, expected in [(.8999, 'needs_review'), (.9, 'decided')]:
            _, result = resolve(document(place()), [query()], raw(raw_element()), ledger(), lambda _: judgement(confidence=confidence))
            self.assertEqual(expected, result['facilities'][A]['status'])
        for mutate in [lambda r: r['answers']['association'].update(choice='unknown'),
                       lambda r: r['answers']['association'].update(confidence=float('nan')),
                       lambda r: r['answers']['association'].update(probabilities={'candidate_0': 1}),
                       lambda r: r['usage'].update(input_tokens=-1)]:
            response = self.response()
            mutate(response)
            with self.assertRaises(ValueError): validate_choice(response, {'candidate_0': 'node/1'})

    def test_request_is_single_direct_system_one_call(self):
        evidence = evidence_for(query(), normalize_osm_elements([raw_element()]), {})
        class Response:
            headers = {}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, n): return json.dumps(JevTests().response()).encode()
        with patch('src.resolve_osm_candidates.urlopen', return_value=Response()) as send:
            result = request_choice(evidence, 'test-secret')
        self.assertEqual(1, send.call_count)
        request = send.call_args.args[0]
        self.assertEqual('https://api.typesafe.ai/v1/systemone', request.full_url)
        payload = json.loads(request.data)
        self.assertEqual(MODEL, payload['model'])
        self.assertEqual('choice', payload['questions']['association']['type'])
        self.assertEqual({'input_tokens': 100, 'output_tokens': 1}, result['usage'])
        self.assertEqual({'node/1': .95, 'none': .05}, result['probabilities'])
        with patch('src.resolve_osm_candidates.urlopen', side_effect=OSError('offline')):
            with self.assertRaises(OSError): request_choice(evidence, 'test-secret')

    def test_input_limits_fail_before_api(self):
        evidence = evidence_for(query(), normalize_osm_elements([raw_element()]), {})
        evidence['candidates'] *= 255
        with self.assertRaisesRegex(ValueError, '255'): request_choice(evidence, 'test')
        evidence['candidates'] = evidence['candidates'][:1]
        evidence['target']['name'] = 'あ' * 20000
        with self.assertRaisesRegex(ValueError, 'input budget'): request_choice(evidence, 'test')

    def test_japanese_identity_regression_cases(self):
        cases = [('神田教会', '神田教会', 'node/1', .98, 'decided'),
                 ('相談支援センターＡｋｉｂａ', '秋葉原駅', 'none', .98, 'decided'),
                 ('千代田クリニック', '千代田クリニック別館', 'none', .65, 'needs_review'),
                 ('東京福祉相談室', '東京福祉会館', 'none', .96, 'decided'),
                 ('区役所相談支援', 'コンビニ千代田店', 'none', .99, 'decided')]
        for target, candidate, choice, confidence, status in cases:
            with self.subTest(target=target):
                _, result = resolve(document(place()), [query(name=target)], raw(raw_element(name=candidate)), ledger(), lambda _: judgement(choice, confidence))
                self.assertEqual(choice, result['facilities'][A]['jev']['choice'])
                self.assertEqual(status, result['facilities'][A]['status'])


class IssueTests(unittest.TestCase):
    def test_body_has_actionable_context_and_exactly_one_confirmed_choice(self):
        entry = reviewed_entry()
        body = entry['issueBody']
        for field in ['[bot]', A, '現在の参照', '確認理由', 'Jev:', 'confidence', '0.0 m', '[OSM]', '[地図]', '`none`', CONFIRM]:
            self.assertIn(field, body)
        self.assertIsNone(parse_issue(checked(body, confirm=False), A, entry))
        self.assertIsNone(parse_issue(body + '\n候補を採用します', A, entry))
        self.assertEqual('node/1', parse_issue(checked(body), A, entry))
        self.assertEqual('none', parse_issue(checked(body, 'none'), A, entry))
        for invalid in [checked(checked(body, 'none')), body.replace(f'- [ ] {CONFIRM}', f'- [x] {CONFIRM}'),
                        checked(body).replace('node/1', 'node/99'), checked(body).replace(entry['evidenceHash'], '0'*64)]:
            with self.assertRaises(ValueError): parse_issue(invalid, A, entry)

    def test_permission_and_invalid_confirmation_receive_correction(self):
        entry = reviewed_entry()
        saved = {'version': 1, 'facilities': {A: entry}}
        github = FakeGitHub(checked(entry['issueBody']), permission=False)
        self.assertEqual({}, read_confirmations(saved, github))
        self.assertIn('書き込み権限', github.comments[0])
        github = FakeGitHub(checked(checked(entry['issueBody'], 'none')))
        self.assertEqual({}, read_confirmations(saved, github))
        self.assertIn('一つだけ', github.comments[0])

    def test_reads_all_confirmed_issues_independent_of_event(self):
        entry = reviewed_entry()
        second = copy.deepcopy(entry)
        second['evidence']['target']['id'] = B
        second['evidenceHash'] = evidence_hash(second['evidence'])
        second['issueBody'] = render_issue(B, second)
        second['issue'] = 18
        saved = {'version': 1, 'facilities': {A: entry, B: second}}
        github = FakeGitHub('')
        github.issue = lambda n: {'body': checked(entry['issueBody'] if n == 17 else second['issueBody'], 'none'), 'state': 'OPEN',
                                 'lastEditedBy': {'login': 'maintainer'}, 'lastEditedAt': 'now', 'url': f'issue/{n}'}
        self.assertEqual({A, B}, set(read_confirmations(saved, github)))

    def test_same_evidence_preserves_partial_body_changed_evidence_resets(self):
        entry = reviewed_entry()
        github = GitHub.__new__(GitHub)
        github.repository = 'owner/repo'
        github.issue = lambda n: {'body': checked(entry['issueBody'], confirm=False), 'state': 'OPEN'}
        calls = []
        github.api = lambda *args: calls.append(args)
        github.save_issue(A, entry)
        self.assertEqual([], calls)
        entry['evidence']['target']['name'] = '名称更新'
        entry['evidenceHash'] = evidence_hash(entry['evidence'])
        github.save_issue(A, entry)
        self.assertEqual(1, len(calls))
        self.assertIn('- [ ] `node/1`', calls[0][1]['body'])
        self.assertNotIn('- [x]', calls[0][1]['body'])
        with self.assertRaises(ValueError):
            parse_issue(checked(reviewed_entry()['issueBody']), A, entry)

    def test_tampered_body_never_becomes_saved_canonical_body(self):
        entry = reviewed_entry()
        original = entry['issueBody']
        github = GitHub.__new__(GitHub)
        github.repository = 'owner/repo'
        github.issue = lambda n: {'body': original.replace('千代田相談支援センター', '偽の対象'), 'state': 'OPEN'}
        github.api = lambda *args: self.fail('partial body should not be rewritten')
        github.save_issue(A, entry)
        self.assertEqual(original, entry['issueBody'])
        with self.assertRaises(ValueError):
            parse_issue(checked(github.issue(17)['body']), A, entry)

    def test_recover_orphan_issue_after_commit_failure_without_duplicate(self):
        entry = reviewed_entry()
        entry.pop('issue')
        entry.pop('issueEvidenceHash')
        github = GitHub.__new__(GitHub)
        github.repository = 'owner/repo'
        github.find_issue = lambda q: 17
        github.issue = lambda n: {'body': checked(entry['issueBody'], confirm=False), 'state': 'OPEN'}
        github.api = lambda *args: self.fail('same Issue must be reused')
        github.save_issue(A, entry)
        self.assertEqual(17, entry['issue'])

    def test_human_decision_closes_only_in_post_publication_step(self):
        entry = reviewed_entry()
        saved = {'version': 1, 'facilities': {A: entry}}
        github = FakeGitHub(checked(entry['issueBody'], 'none'))
        confirmations = read_confirmations(saved, github)
        apply_confirmations(saved, confirmations)
        self.assertEqual([], github.calls)
        updated = apply_decisions(document(place(osm='node/8', qid='Q8')), [query()], saved['facilities'])
        self.assertNotIn('rdfs:seeAlso', updated['@graph'][0])
        close_published(saved, github)
        self.assertEqual({'state': 'closed', 'state_reason': 'completed'}, github.calls[0][1])
        github.state = 'CLOSED'
        close_published(saved, github)
        self.assertEqual(1, len(github.calls))


class IntegrationTests(unittest.TestCase):
    def setup_root(self, directory):
        root = Path(directory)
        _write_json(root/'inputs/facilities.json', {'queries': [query(), query(B, '別施設', coordinates=[139.751, 35.69])]})
        _write_json(root/'data/places.jsonld', document(place(), place(B)))
        _write_json(root/'data/osm-decisions.json', ledger())
        _write_json(root/'imports/openstreetmap/raw.json', raw(raw_element(), {**raw_element(2, '別施設'), 'lon':139.751}))
        payload = (root/'imports/openstreetmap/raw.json').read_bytes()
        _write_json(root/'imports/openstreetmap/retrieval.json', {'rawSha256': hashlib.sha256(payload).hexdigest(), 'rawVersion': '20261027'})
        return root

    def test_operational_failures_leave_canonical_and_ledger_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            before = [(root/p).read_bytes() for p in ['data/places.jsonld', 'data/osm-decisions.json']]
            for error_at in ['retrieve', 'hash', 'jev']:
                def retrieve(*args):
                    if error_at == 'retrieve': raise OSError('download failed')
                    if error_at == 'hash': (root/'imports/openstreetmap/raw.json').write_text('{}')
                with self.subTest(error_at=error_at):
                    self.setup_root(directory)
                    with self.assertRaises((OSError, ValueError)):
                        update(root, refresh=True, retrieve=retrieve, judge=lambda _: (_ for _ in ()).throw(OSError('API failed')))
                    self.assertEqual(before, [(root/p).read_bytes() for p in ['data/places.jsonld', 'data/osm-decisions.json']])

    def test_resolved_progress_and_pending_issue_survive_without_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            saved = update(root, refresh=True, retrieve=lambda *args: None, judge=lambda ev: judgement('node/1') if ev['target']['id'] == A else judgement('node/2', .5))
            entry = saved['facilities'][B]
            entry.update(issue=17, issueEvidenceHash=entry['evidenceHash'])
            entry['issueBody'] = render_issue(B, entry)
            _write_json(root/'data/osm-decisions.json', saved)
            public = json.loads(build_repository(root).read_text())
            self.assertIn('rdfs:seeAlso', public['@graph'][0])
            self.assertNotIn('rdfs:seeAlso', public['@graph'][1])
            self.assertNotIn('facilities', public)
            self.assertEqual(['places.jsonld'], [p.name for p in (root/'site').iterdir()])
            # Human application uses only the newly confirmed facility in latest data.
            public['@graph'][0]['schema:geo']['schema:longitude'] = 139.749
            _write_json(root/'data/places.jsonld', public)
            github = FakeGitHub(checked(entry['issueBody'], 'none'))
            update(root, github=github)
            after = (root/'data/places.jsonld').read_bytes()
            self.assertEqual(139.749, json.loads(after)['@graph'][0]['schema:geo']['schema:longitude'])
            self.assertNotIn('rdfs:seeAlso', json.loads(after)['@graph'][1])
            self.assertEqual([], github.calls)  # no close before successful Pages
            update(root, github=github)
            self.assertEqual(after, (root/'data/places.jsonld').read_bytes())

    def test_changed_input_rejects_old_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            saved = update(root, refresh=True, retrieve=lambda *args: None, judge=lambda ev: judgement('node/1' if ev['target']['id'] == A else 'node/2', .5))
            entry = saved['facilities'][A]
            entry.update(issue=17, issueEvidenceHash=entry['evidenceHash'])
            entry['issueBody'] = render_issue(A, entry)
            _write_json(root/'data/osm-decisions.json', saved)
            queries = load_queries(root)
            queries[0]['name'] = '変更後の対象'
            _write_json(root/'inputs/facilities.json', {'queries': queries})
            github = FakeGitHub(checked(entry['issueBody']))
            github.save_issue = lambda *args: None
            before = (root/'data/places.jsonld').read_bytes()
            update(root, github=github)
            self.assertEqual(before, (root/'data/places.jsonld').read_bytes())
            self.assertIn('再実行', github.comments[0])

    def test_conflicting_confirmation_does_not_block_other_valid_answer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            queries = [query(), query(B, '別施設')]
            _write_json(root/'inputs/facilities.json', {'queries': queries})
            entry = reviewed_entry()
            second = copy.deepcopy(entry)
            second['issue'] = 18
            second['evidence']['target'] = queries[1]
            second['evidenceHash'] = evidence_hash(second['evidence'])
            second['issueBody'] = render_issue(B, second)
            saved = {'version': 1, 'facilities': {A: entry, B: second}}
            _write_json(root/'data/osm-decisions.json', saved)
            _write_json(root/'data/places.jsonld', document(place(), place(B, osm='node/1')))
            _write_json(root/'imports/openstreetmap/raw.json', raw(raw_element()))
            payload = (root/'imports/openstreetmap/raw.json').read_bytes()
            _write_json(root/'imports/openstreetmap/retrieval.json', {'rawSha256': hashlib.sha256(payload).hexdigest(), 'rawVersion': '20261027'})
            github = FakeGitHub('')
            github.issue = lambda n: {'body': checked(entry['issueBody'] if n == 17 else second['issueBody'], 'node/1'), 'state': 'OPEN', 'lastEditedBy': {'login': 'owner'}, 'lastEditedAt': 'now', 'url': str(n)}
            github.save_issue = lambda *args: None
            result = update(root, github=github)
            self.assertEqual('needs_review', result['facilities'][A]['status'])
            self.assertEqual('decided', result['facilities'][B]['status'])
            self.assertIn('別の施設', github.comments[0])

    def test_publish_false_does_not_remove_search_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            queries = load_queries(root)
            queries[0]['publish'] = False
            _write_json(root/'inputs/facilities.json', {'queries': queries})
            published = json.loads(build_repository(root).read_text())
            self.assertEqual([f'urn:uuid:{B}'], [p['@id'] for p in published['@graph']])
            self.assertEqual(2, len(load_queries(root)))


if __name__ == '__main__':
    unittest.main()
