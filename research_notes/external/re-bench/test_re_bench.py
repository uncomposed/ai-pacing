"""Fast checks for the RE-Bench replication (#58). No network; standard library and the committed files only.

    python3 research_notes/external/re-bench/test_re_bench.py      (run by make check)
"""
from __future__ import annotations

import csv
import importlib.util
import json
import math
import pathlib
import statistics
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import reproduce as R  # noqa: E402

_spec = importlib.util.spec_from_file_location('evidence_tool', ROOT / 'tools/evidence_tool.py')
EV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(EV)

FB = list(csv.DictReader((HERE / 'data/fixed_budget.csv').read_text(encoding='utf-8').splitlines()))
HB = list(csv.DictReader((HERE / 'data/human_baselines.csv').read_text(encoding='utf-8').splitlines()))
RES = json.loads((HERE / 'results/reproduction.json').read_text())
RECORDS = {r['id']: r for r in EV.load_yaml(ROOT / 'evidence/records.yaml')['records']}
OBSERVABLES = EV.load_yaml(HERE / 'observables.yaml')


class Reproduction(unittest.TestCase):
    def test_committed_results_match_a_fresh_recomputation(self):
        R.compare(json.loads(json.dumps(R.build())), RES)

    def test_declared_verdicts(self):
        # These are findings. A change here means the data or the method changed: explain it in the README.
        self.assertTrue(RES['readme_transforms_all_match'])
        self.assertEqual(len(RES['readme_transforms']), 8)
        self.assertEqual((RES['ceiling_matches'], RES['ceiling_rows']), (6, 7))
        bad = [r['environment'] for r in RES['ceiling_table'] if not r['match']]
        self.assertEqual(bad, ['Scaling Law Experiment'])
        so = RES['baseline_sourcing']
        self.assertTrue(so['runs_match'] and so['baseliners_match'] and so['mean_match'])
        self.assertFalse(so['text_matches_table'])
        va = RES['validation_table']
        self.assertEqual((va['gt_0p05']['k'], va['gt_0p05']['n']), (60, 71))
        self.assertFalse(va['gt_0p05']['match'])
        self.assertEqual(RES['paper_revision_changes'], ['env_metrics_loc'])
        self.assertFalse(any(x['same_counts'] for x in RES['metr_released_human_baselines']['per_environment']
                             if x['released_runs'] is not None))

    def test_normalization_corners(self):
        # (y - s) / (r - s) is 0 at the start and 1 at the reference, also for lower-is-better scores.
        for s, r in [(2.197, 0.262), (0.24, 0.84)]:
            lo, hi = R.norm_interval(s, (s, s), (r, r))
            self.assertAlmostEqual(lo, 0.0)
            lo, hi = R.norm_interval(r, (s, s), (r, r))
            self.assertAlmostEqual(hi, 1.0)

    def test_headline_claims_are_listed_as_not_reproduced(self):
        status = {c['value']: c['status'] for c in RES['not_reproducible']}
        self.assertEqual(status['4x'], 'not_reproducible')
        self.assertEqual(status['2x'], 'not_reproducible')


class FixedBudget(unittest.TestCase):
    def test_internal_consistency(self):
        for suite in ('TH1.0', 'TH1.1'):
            hrows = [r for r in HB if r['suite'] == suite]
            hmean = statistics.fmean(float(r['mean_score']) for r in hrows)
            for r in (x for x in FB if x['suite'] == suite):
                m, lo, hi = float(r['mean_score']), float(r['ci95_low']), float(r['ci95_high'])
                self.assertLessEqual(lo, m + 1e-6, r['agent'])
                self.assertLessEqual(m, hi + 1e-6, r['agent'])
                self.assertTrue(0 <= lo and hi <= 1)
                self.assertEqual(int(r['tasks']), len(hrows))
                self.assertAlmostEqual(float(r['human_mean_same_tasks']), hmean, places=5)
                self.assertAlmostEqual(float(r['ratio_to_human']), m / float(r['human_mean_same_tasks']), places=4)
                self.assertTrue(r['release_date'], r['agent'])

    def test_budgets_are_labelled(self):
        th11 = {r['agent']: r['time_limit_s'] for r in FB if r['suite'] == 'TH1.1'}
        self.assertEqual(sorted(a for a, t in th11.items() if t != '28800'), ['GPT-4 0314', 'o1-preview'])
        self.assertTrue(all(r['time_limit_s'] in ('36000', '72000') for r in FB if r['suite'] == 'TH1.0'))


class Separation(unittest.TestCase):
    """Fixed-budget scores, benchmark process, time horizons and research productivity stay separate observables."""

    def test_classes(self):
        allowed = set(OBSERVABLES['classes'])
        used = {o['class'] for o in OBSERVABLES['observables']}
        self.assertLessEqual(used, allowed)
        self.assertEqual(used, {'fixed_budget_score', 'benchmark_process'})

    def test_records_exist_and_forbid_other_uses(self):
        ids = set()
        for o in OBSERVABLES['observables']:
            ids |= set(o['record'] if isinstance(o['record'], list) else [o['record']])
        ids |= {'EV-REBENCH-PAPER-V2-2025'}
        for rid in ids:
            rec = RECORDS[rid]
            nf = ' '.join(rec['not_for'])
            self.assertIn('time-horizon capability', nf, rid)
            self.assertIn('research productivity', nf, rid)
            self.assertIn('adoption', nf, rid)
            self.assertIn('units-bridge', nf, rid)

    def test_shared_runs_are_declared_not_independent(self):
        for rid in ('EV-REBENCH-METR-TH10-2026-03-05', 'EV-REBENCH-METR-TH11-2026-03-05'):
            self.assertIn('not independent', RECORDS[rid]['extraction']['note'])
        self.assertIn('EV-REBENCH-PAPER-V1-2024', RECORDS['EV-REBENCH-PAPER-V2-2025']['depends_on'])


class Pins(unittest.TestCase):
    def test_pins_agree(self):
        fetch = (HERE / 'fetch_sources.sh').read_text()
        sources = (HERE / 'SOURCES.yaml').read_text()
        for pin in ('a0cc6d4a91b20f84ebef505d5c72358f88b3b389', '52cb829c7a2efb2d659285c4b1768d191d97f8d2'):
            self.assertIn(pin, fetch)
            self.assertIn(pin, sources)
        sha = dict(reversed(line.split('  ')) for line in (HERE / 'sources.sha256').read_text().splitlines())
        for rid, path in [('EV-REBENCH-PAPER-V1-2024', 'arxiv/v1/report.tex'), ('EV-REBENCH-PAPER-V2-2025', 'arxiv/v2/report.tex'),
                          ('EV-REBENCH-METR-TH10-2026-03-05', 'metr/th10_runs.jsonl'),
                          ('EV-REBENCH-METR-TH11-2026-03-05', 'metr/th11_runs.jsonl')]:
            self.assertIn(sha[path], RECORDS[rid]['source']['version'], rid)


if __name__ == '__main__':
    unittest.main(verbosity=1)
