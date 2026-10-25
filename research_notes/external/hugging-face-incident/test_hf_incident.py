#!/usr/bin/env python3
"""Fast schema and consistency tests for the Hugging Face incident tables (issue #15). No network; well under a second."""
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import render  # noqa: E402

load_yaml = render.load_yaml
_ms = importlib.util.spec_from_file_location('modes_tool', ROOT / 'tools/modes_tool.py')
modes_tool = importlib.util.module_from_spec(_ms)
_ms.loader.exec_module(modes_tool)

STAGES = {'precondition', 'agent_action', 'detection', 'interpretation', 'escalation', 'authorized_action',
          'containment', 'audit', 'disclosure', 'institutional_response'}
KINDS = {'observation', 'intent_inference', 'institutional_claim'}
VERIFICATION = {'independent', 'single_source', 'contested'}
BASES = {'stated', 'reconstructed', 'date_only', 'bounded_by_publication', 'unknown'}
ACTORS = {'agents', 'openai', 'hugging_face', 'metr', 'aisi', 'third_party', 'unknown'}
VERDICTS = {'supported', 'contradicted', 'unsupported'}
EVENT_FIELDS = {'id', 'time', 'stage', 'actor', 'kind', 'verification', 'statement', 'sources'}
OPTIONAL_FIELDS = {'discrepancies', 'unknowns', 'resource_effect', 'causal_claim'}

# Guard for the "no exploit detail" rule: patterns that would indicate technique-level content.
FORBIDDEN = [r'CVE-\d', r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', r'\bcurl\b', r'\bexec\(', r'/proc/', r'\.svc\b',
             r'\bkubectl\b', r'\bsudo\b', r'--[a-z][a-z-]+=', r'\bpayload\b', r'\bSSRF\b', r'\binjection\b',
             r'\bHDF5\b', r'\bJinja', r'\bIMDS', r'\bmetadata endpoint\b', r'auth-key', r'\btoken=']


def check_events(doc, records):
    """Return a list of errors for an events.yaml document."""
    errors = []
    events = doc['events']
    ids = [e['id'] for e in events]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        errors.append(f'duplicate event {dup}')
    dx_ids = {d['id'] for d in doc['discrepancies']}
    by_id = {e['id']: e for e in events}
    for e in events:
        i = e['id']
        if not re.fullmatch(r'HF-E\d{2}', i):
            errors.append(f'{i}: id must be HF-Enn (EV- is reserved for evidence records)')
        missing = EVENT_FIELDS - set(e)
        extra = set(e) - EVENT_FIELDS - OPTIONAL_FIELDS
        if missing:
            errors.append(f'{i}: missing {sorted(missing)}')
            continue
        if extra:
            errors.append(f'{i}: unknown fields {sorted(extra)}')
        if e['stage'] not in STAGES:
            errors.append(f'{i}: stage {e["stage"]!r}')
        if e['kind'] not in KINDS:
            errors.append(f'{i}: kind {e["kind"]!r}')
        if e['verification'] not in VERIFICATION:
            errors.append(f'{i}: verification {e["verification"]!r}')
        if e['actor'] not in ACTORS:
            errors.append(f'{i}: actor {e["actor"]!r}')
        if e['kind'] == 'intent_inference' and e['verification'] == 'independent':
            errors.append(f'{i}: an intent inference cannot be marked independently verified')
        t = e['time']
        if t.get('basis') not in BASES:
            errors.append(f'{i}: time basis {t.get("basis")!r}')
        lo, hi = render.parse(t['earliest']), render.parse(t['latest'])
        if lo and hi and lo > hi:
            errors.append(f'{i}: earliest after latest')
        if (lo is None or hi is None) and t['basis'] != 'unknown':
            errors.append(f'{i}: an open time bound needs basis unknown')
        if not e['sources']:
            errors.append(f'{i}: no sources')
        read = []
        for s in e['sources']:
            r = records.get(s.get('record'))
            if r is None:
                errors.append(f'{i}: cites unknown evidence record {s.get("record")}')
                continue
            if not str(s.get('locator', '')).strip():
                errors.append(f'{i}: cites {s["record"]} without a locator')
            if r['reading'] == 'not_read':
                errors.append(f'{i}: cites {s["record"]}, which was not read')
            else:
                read.append(r)
        if read and lo is not None:
            last_avail = max(render._at.evidence_tool.date_bounds(r['availability_date'])[1] for r in read)
            if lo.date() > last_avail:
                errors.append(f'{i}: event starts after every cited source was published')
        if e['stage'] in ('institutional_response', 'audit') and e.get('causal_claim') != 'none asserted':
            errors.append(f'{i}: institutional responses carry causal_claim "none asserted"')
        for d in e.get('discrepancies', []):
            if d not in dx_ids:
                errors.append(f'{i}: unknown discrepancy {d}')
    for d in doc['discrepancies']:
        if d['resolution'] not in ('resolved', 'unresolved'):
            errors.append(f'{d["id"]}: resolution {d["resolution"]!r}')
        if d['resolution'] == 'resolved' and not d.get('note'):
            errors.append(f'{d["id"]}: a resolved discrepancy must say how')
        for s in d['sources']:
            if s not in records:
                errors.append(f'{d["id"]}: unknown evidence record {s}')
    for w in doc['windows']:
        for end in ('from', 'to'):
            if w[end] not in by_id:
                errors.append(f'{w["id"]}: unknown event {w[end]}')
    for a in doc['assertions_issue_3']:
        if a['verdict'] not in VERDICTS:
            errors.append(f'{a["id"]}: verdict {a["verdict"]!r}')
        if not a['evidence']:
            errors.append(f'{a["id"]}: no evidence')
        for x in a['evidence']:
            if x not in by_id:
                errors.append(f'{a["id"]}: unknown event {x}')
    return errors


class HuggingFaceIncidentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = render.load()
        cls.records = cls.data['records']
        cls.events = cls.data['events']
        cls.event_ids = {e['id'] for e in cls.events['events']}

    def errors(self, doc):
        return check_events(doc, self.records)

    def rejects(self, doc, message):
        errs = self.errors(doc)
        self.assertTrue(any(message in e for e in errs), errs)

    # committed tables
    def test_committed_event_table_is_consistent(self):
        self.assertEqual([], self.errors(self.events))

    def test_rendered_markdown_is_current(self):
        self.assertEqual((HERE / 'events.md').read_text(), render.render(self.data))

    def test_every_issue_3_assertion_has_a_three_valued_verdict(self):
        self.assertGreaterEqual(len(self.events['assertions_issue_3']), 10)
        verdicts = {a['verdict'] for a in self.events['assertions_issue_3']}
        self.assertLessEqual(verdicts, VERDICTS)

    def test_disclosure_pressure_is_not_marked_supported(self):
        a = next(a for a in self.events['assertions_issue_3'] if 'whistleblower' in a['claim'])
        self.assertEqual('unsupported', a['verdict'])

    def test_sources_file_matches_evidence_records(self):
        src = load_yaml(HERE / 'SOURCES.yaml')['sources']
        cited = {s['record'] for e in self.events['events'] for s in e['sources']}
        listed = {s['id'] for s in src}
        self.assertLessEqual(cited, listed)
        for s in src:
            if s['id'].startswith('EV-'):
                self.assertIn(s['id'], self.records, s['id'])
                self.assertEqual(s['read'] is False, self.records[s['id']]['reading'] == 'not_read', s['id'])

    def test_no_technique_level_detail(self):
        for path in sorted(HERE.glob('*.yaml')) + [HERE / 'events.md', HERE / 'README.md']:
            text = path.read_text()
            for pat in FORBIDDEN:
                self.assertIsNone(re.search(pat, text, flags=re.I), f'{path.name} matches {pat}')

    # mutation tests: the checker must catch these
    def test_unknown_record_is_rejected(self):
        doc = copy.deepcopy(self.events)
        doc['events'][0]['sources'][0]['record'] = 'EV-GHOST'
        self.rejects(doc, 'cites unknown evidence record EV-GHOST')

    def test_unread_record_cannot_be_cited(self):
        doc = copy.deepcopy(self.events)
        doc['events'][0]['sources'].append({'record': 'EV-OAI-HF-ROAD-2026', 'locator': 'x'})
        self.rejects(doc, 'which was not read')

    def test_missing_locator_is_rejected(self):
        doc = copy.deepcopy(self.events)
        doc['events'][0]['sources'][0]['locator'] = ' '
        self.rejects(doc, 'without a locator')

    def test_inverted_interval_is_rejected(self):
        doc = copy.deepcopy(self.events)
        t = doc['events'][4]['time']
        t['earliest'], t['latest'] = t['latest'], t['earliest']
        if t['earliest'] == t['latest']:
            t['earliest'] = '2026-12-31T00:00:00Z'
        self.rejects(doc, 'earliest after latest')

    def test_event_after_its_sources_is_rejected(self):
        doc = copy.deepcopy(self.events)
        e = next(e for e in doc['events'] if e['id'] == 'HF-E21')
        e['time'] = {'earliest': '2026-09-01T00:00:00Z', 'latest': '2026-09-02T00:00:00Z', 'basis': 'stated'}
        self.rejects(doc, 'starts after every cited source was published')

    def test_open_bound_needs_unknown_basis(self):
        doc = copy.deepcopy(self.events)
        doc['events'][0]['time']['earliest'] = None
        self.rejects(doc, 'open time bound needs basis unknown')

    def test_bad_enum_and_verdict_are_rejected(self):
        doc = copy.deepcopy(self.events)
        doc['events'][0]['stage'] = 'mitigated'
        doc['assertions_issue_3'][0]['verdict'] = 'partly'
        errs = self.errors(doc)
        self.assertTrue(any("stage 'mitigated'" in e for e in errs))
        self.assertTrue(any("verdict 'partly'" in e for e in errs))

    def test_intent_inference_cannot_be_independent(self):
        doc = copy.deepcopy(self.events)
        e = next(e for e in doc['events'] if e['kind'] == 'intent_inference')
        e['verification'] = 'independent'
        self.rejects(doc, 'intent inference cannot be marked independently verified')

    def test_response_cannot_claim_effectiveness(self):
        doc = copy.deepcopy(self.events)
        e = next(e for e in doc['events'] if e['stage'] == 'institutional_response')
        e['causal_claim'] = 'prevented recurrence'
        self.rejects(doc, 'causal_claim "none asserted"')

    def test_duplicate_and_evidence_prefix_ids_are_rejected(self):
        doc = copy.deepcopy(self.events)
        doc['events'][1]['id'] = doc['events'][0]['id']
        doc['events'][2]['id'] = 'EV-03'
        errs = self.errors(doc)
        self.assertTrue(any('duplicate event' in e for e in errs))
        self.assertTrue(any('EV- is reserved' in e for e in errs))

    # windows
    def test_windows_are_computed_or_unknown(self):
        events = {e['id']: e for e in self.events['events']}
        got = {w['id']: render.window_hours(events, w) for w in self.events['windows']}
        self.assertIsNone(got['W-DETECT-TO-LOCKOUT'])  # detection time is unpublished; never guessed
        lo, hi = got['W-RECUR']
        self.assertTrue(0 < lo <= hi < 48)

    # topology
    def test_topology_references_resolve(self):
        topo = load_yaml(HERE / 'topology.yaml')
        zones = {z['id'] for z in topo['zones']}
        stores = {p['id'] for p in topo['persistent_state']}
        boundaries = {b['id']: b for b in topo['trust_boundaries']}
        for b in boundaries.values():
            self.assertLessEqual(set(b['between']), zones, b['id'])
        for c in topo['crossings']:
            self.assertIn(c['boundary'], boundaries)
            self.assertLessEqual(set(c['events']), self.event_ids, c)
        for ch in topo['channels']:
            self.assertLessEqual(set(ch['between']), zones, ch['id'])
        for p in topo['persistent_state']:
            self.assertIn(p['location'], zones)
        for v in topo['observer_view']:
            self.assertLessEqual(set(v['sees']) | set(v['not']), zones | stores, v['party'])

    # explanations
    def test_explanation_matrix(self):
        ex = self.data['explanations']
        feats = set(ex['features'])
        for x in ex['explanations']:
            self.assertLessEqual(set(x['has']), feats)
        for o in ex['observations']:
            self.assertLessEqual(set(o['needs']), feats)
            self.assertLessEqual(set(o['events']), self.event_ids, o['id'])
        m = render.explanation_matrix(ex)
        self.assertTrue(all(row['X-COMM-PERSISTENT'] for row in m.values()))
        self.assertEqual({'O-08', 'O-09', 'O-10'}, {o for o, row in m.items() if row['X-ISOLATED']})
        self.assertEqual({'O-02', 'O-03', 'O-06'}, {o for o, row in m.items() if not row['X-COMM-LIVE']})
        for o in ex['observations']:  # an observation every explanation accounts for must say it does not discriminate
            if all(m[o['id']].values()):
                self.assertIn('note', o, o['id'])

    def test_no_capacity_multiplier(self):
        text = (HERE / 'explanations.yaml').read_text()
        self.assertIsNone(re.search(r'multiplier\s*:|capacity\s*:|\b\d+(\.\d+)?x\b', text))

    # mode contract
    def test_mode_trace_against_the_contract(self):
        contract = copy.deepcopy(modes_tool.load_yaml(modes_tool.CONTRACT))
        trace = load_yaml(HERE / 'mode_trace.yaml')
        self.assertEqual(contract['contract_version'], trace['contract_version_used'])
        contract['traces'] = trace['traces']
        errors = modes_tool.validate(contract)
        expected = [g['message'] for g in trace['contract_gaps']]
        self.assertEqual(sorted(expected), sorted(errors))

    def test_mode_trace_derives_no_mode(self):
        contract = modes_tool.load_yaml(modes_tool.CONTRACT)
        tr = load_yaml(HERE / 'mode_trace.yaml')['traces'][0]
        for step in tr['steps']:
            views = modes_tool.classify(contract, tr, step)
            self.assertFalse(any(v is True for res in views.values() for v in res.values()), step['label'])
            self.assertFalse(views['COLL-EG']['MODE-SOVEREIGN'])

    # held-out
    def test_heldout_is_frozen(self):
        h = load_yaml(HERE / 'heldout.yaml')
        self.assertEqual('retrospective_heldout', h['label'])
        # The frozen file keeps `evaluated: false`; the scoring block is heldout_scores.yaml.
        self.assertFalse(h['evaluated'])
        self.assertEqual('EV-AISI-TECH-2026', h['resolution_record'])
        self.assertEqual('read_primary', self.records[h['resolution_record']]['reading'])
        for p in h['predictions']:
            self.assertTrue(0 < p['probability'] < 1, p['id'])
            self.assertLessEqual(set(p['derived_from']), self.event_ids, p['id'])
        for c in h['comparison']:
            self.assertIn(c['aisi'], {'consistent', 'inconsistent', 'not_reported'})


OUTCOMES = {'resolved_true', 'resolved_false', 'unresolvable'}


def predictions_hash(predictions):
    return hashlib.sha256(json.dumps(predictions, sort_keys=True).encode()).hexdigest()


def check_scores(doc, heldout, records):
    """Return a list of errors for a heldout_scores.yaml document scored against the frozen heldout.yaml."""
    errors = []
    preds = {p['id']: p for p in heldout['predictions']}
    if doc['frozen_check']['predictions_sha256'] != predictions_hash(heldout['predictions']):
        errors.append('predictions differ from the frozen hash')
    if not doc['label'].startswith('retrospective_heldout'):
        errors.append('label must stay a retrospective held-out check')
    if 'validation' in doc['label'].replace('not_validation', ''):
        errors.append('label must not claim validation')
    if not doc.get('not_validation_of'):
        errors.append('missing not_validation_of')
    if doc['resolution_record'] != heldout['resolution_record']:
        errors.append('resolution record differs from heldout.yaml')
    rec = records.get(doc['resolution_record'])
    if rec is None or rec['reading'] != 'read_primary':
        errors.append('resolution record is not read in primary form')
    elif doc['resolution_record_sha256'] not in rec['source']['version']:
        errors.append('resolution record hash differs from the evidence record')
    ids = [s['id'] for s in doc['scores']]
    if sorted(ids) != sorted(preds):
        errors.append(f'scores {sorted(ids)} do not cover predictions {sorted(preds)} exactly once')
    if doc['n_predictions'] != len(preds):
        errors.append('n_predictions is not the number of frozen predictions')
    total = base_total = 0.0
    scored, unresolved = [], []
    for s in doc['scores']:
        i = s['id']
        p = preds.get(i)
        if p is None:
            continue
        if s['claim'] != p['claim'] or s['probability'] != p['probability']:
            errors.append(f'{i}: claim or probability differs from heldout.yaml')
        if s['outcome'] not in OUTCOMES:
            errors.append(f'{i}: outcome {s["outcome"]!r}')
            continue
        if not s.get('locators') or not all(str(l.get('where', '')).strip() for l in s['locators']):
            errors.append(f'{i}: every score needs locators with a position in the report')
        if not str(s.get('reasoning', '')).strip():
            errors.append(f'{i}: no reasoning')
        if s['outcome'] == 'unresolvable':
            unresolved.append(i)
            if s['log_score'] is not None or s['log_score_baseline'] is not None:
                errors.append(f'{i}: an unresolvable prediction carries no score')
            continue
        happened = s['outcome'] == 'resolved_true'
        want = math.log(p['probability'] if happened else 1 - p['probability'])
        if abs(s['log_score'] - want) > 5e-5:
            errors.append(f'{i}: log_score {s["log_score"]} but ln gives {want:.4f}')
        if abs(s['log_score_baseline'] - math.log(0.5)) > 5e-5:
            errors.append(f'{i}: baseline is not ln(0.5)')
        total += want
        base_total += math.log(0.5)
        scored.append(i)
    t = doc['totals']
    if t['scored_predictions'] != scored or t['excluded_unresolvable'] != unresolved:
        errors.append('totals list the wrong predictions')
    if doc['n_resolved'] != len(scored) or doc['n_unresolvable'] != len(unresolved):
        errors.append('n_resolved or n_unresolvable is wrong')
    if scored:
        for key, want in (('sum_log_score', total), ('mean_log_score', total / len(scored)),
                          ('baseline_sum', base_total), ('baseline_mean', base_total / len(scored)),
                          ('difference_sum', total - base_total)):
            if abs(t[key] - want) > 5e-4:
                errors.append(f'totals.{key} is {t[key]} but recomputes to {want:.4f}')
    dxs = [d['id'] for d in doc['discrepancies']]
    if len(set(dxs)) != len(dxs):
        errors.append('duplicate discrepancy ids')
    return errors


class HeldoutScoresTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = render.load()['records']
        cls.heldout = load_yaml(HERE / 'heldout.yaml')
        cls.scores = load_yaml(HERE / 'heldout_scores.yaml')

    def errors(self, doc):
        return check_scores(doc, self.heldout, self.records)

    def rejects(self, doc, message):
        errs = self.errors(doc)
        self.assertTrue(any(message in e for e in errs), errs)

    def test_committed_scores_are_consistent(self):
        self.assertEqual([], self.errors(self.scores))

    def test_sample_size_and_unresolvables_are_stated(self):
        self.assertEqual(4, self.scores['n_predictions'])
        self.assertEqual(3, self.scores['n_resolved'])
        self.assertEqual(['HO-02'], self.scores['totals']['excluded_unresolvable'])

    def test_discrepancy_in_events_table_is_recorded(self):
        events = load_yaml(HERE / 'events.yaml')
        self.assertIn('DX-09', {d['id'] for d in events['discrepancies']})

    def test_edited_prediction_is_rejected(self):
        h = copy.deepcopy(self.heldout)
        h['predictions'][0]['probability'] = 0.5
        self.assertTrue(any('frozen hash' in e for e in check_scores(self.scores, h, self.records)))

    def test_wrong_log_score_is_rejected(self):
        doc = copy.deepcopy(self.scores)
        doc['scores'][0]['log_score'] = -0.1
        self.rejects(doc, 'log_score')

    def test_flipped_outcome_is_rejected(self):
        doc = copy.deepcopy(self.scores)
        next(s for s in doc['scores'] if s['id'] == 'HO-01')['outcome'] = 'resolved_false'
        self.rejects(doc, 'HO-01: log_score')

    def test_scored_unresolvable_is_rejected(self):
        doc = copy.deepcopy(self.scores)
        s = next(s for s in doc['scores'] if s['id'] == 'HO-02')
        s['log_score'] = -0.5
        self.rejects(doc, 'unresolvable prediction carries no score')

    def test_wrong_totals_are_rejected(self):
        doc = copy.deepcopy(self.scores)
        doc['totals']['sum_log_score'] = -0.5
        self.rejects(doc, 'totals.sum_log_score')

    def test_dropped_prediction_is_rejected(self):
        doc = copy.deepcopy(self.scores)
        doc['scores'] = [s for s in doc['scores'] if s['id'] != 'HO-02']
        self.rejects(doc, 'exactly once')

    def test_missing_locator_is_rejected(self):
        doc = copy.deepcopy(self.scores)
        doc['scores'][0]['locators'] = []
        self.rejects(doc, 'locators')

    def test_validation_label_is_rejected(self):
        doc = copy.deepcopy(self.scores)
        doc['label'] = 'retrospective_heldout_validation'
        self.rejects(doc, 'must not claim validation')

    def test_unread_resolution_record_is_rejected(self):
        recs = copy.deepcopy(self.records)
        recs['EV-AISI-TECH-2026']['reading'] = 'not_read'
        errs = check_scores(self.scores, self.heldout, recs)
        self.assertTrue(any('not read in primary form' in e for e in errs), errs)


if __name__ == '__main__':
    unittest.main(verbosity=1)
