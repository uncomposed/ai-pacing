"""Fast checks for the GATE variant sweep and the bundle watch (issue #33). No network, no solving.

Run: python3 research_notes/external/epoch-gate/tests/test_variants.py (wired into `make test`).
The sweep itself is rerun by the `epoch-gate` workflow with the `variants` input.
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / 'variants'))
sys.path.insert(0, str(HERE / 'official'))
import bundle_watch  # noqa: E402
import make_jobs  # noqa: E402
import summarize  # noqa: E402

PINNED_BUNDLE = 'c2104290dc486c27e07b6614dd306604bd98a095d660369d3ce356f481e72731'
SPEC = json.loads((HERE / 'variants' / 'spec.json').read_text())
SUMMARY = json.loads((HERE / 'variants' / 'summary.json').read_text())
TARGET = {j['name']: j for j in json.loads((HERE / 'data' / 'baseline_target.json').read_text())['jobs']}
PIN = json.loads((HERE / 'data' / 'bundle_pin.json').read_text())


class Jobs(unittest.TestCase):
    def test_jobs_file_is_expansion_of_spec(self):
        self.assertEqual((HERE / 'variants' / 'jobs.json').read_text(), make_jobs.dump(make_jobs.expand(SPEC)))

    def test_issue_variant_set_present(self):
        mp = {v['name']: v.get('modelParams', {}) for v in SPEC['variants']}
        fracs = sorted(m['beliefs.max_frac_beliefs'][0]['max_frac'] for m in mp.values() if 'beliefs.max_frac_beliefs' in m)
        self.assertEqual(fracs, [0.5, 0.8, 0.9])
        for key in ('main.labor_reallocation_friction', 'rnd.rnd_wedge', 'main.ces_term_rho', 'objective.eta',
                    'automation.train_reqs', 'automation.flop_gap_frac'):
            self.assertTrue(any(key in m for m in mp.values()), key)
        self.assertGreaterEqual(len(SPEC['caps']), 3)

    def test_every_variant_param_is_a_preset_argument(self):
        # The table names the partial-automation add-on `automation.max_fracs`; the solver's
        # argument is `beliefs.max_frac_beliefs`. Every override must be a real argument.
        args = bundle_watch.flatten(PIN['presets'][0]['modelParams'])
        table = {r['Variable in code'] for r in PIN['parameter_table']}
        for v in SPEC['variants']:
            for k in v.get('modelParams', {}):
                self.assertIn(k, args, v['name'])
                self.assertTrue(k in table or k == 'beliefs.max_frac_beliefs', k)

    def test_shards_cover_jobs_once(self):
        jobs = make_jobs.expand(SPEC)
        parts = make_jobs.shards(jobs, 4)
        self.assertEqual(sorted(j['name'] for p in parts for j in p), sorted(j['name'] for j in jobs))


class Summary(unittest.TestCase):
    def test_provenance(self):
        self.assertEqual(SUMMARY['bundle_sha256'], PINNED_BUNDLE)
        self.assertEqual([j['name'] for j in SUMMARY['jobs']], [j['name'] for j in make_jobs.expand(SPEC)])

    def test_results_md_rendered_from_summary(self):
        self.assertEqual((HERE / 'variants' / 'RESULTS.md').read_text(), summarize.render(SUMMARY))

    def test_overlap_with_baseline_target_is_bit_identical(self):
        # Jobs that #13 already ran must give the same full trajectory: same solver, same arguments.
        pairs = {'default@40': 'default', 'default@80': 'default_maxiter_80',
                 'conservative@40': 'conservative', 'aggressive@40': 'aggressive',
                 'train_reqs_36.4@40': 'default_train_reqs_36.4', 'train_reqs_36.6@40': 'default_train_reqs_36.6',
                 'labor_friction@40': 'default_no_labor_reallocation', 'rnd_wedge_8@40': 'default_rnd_wedge_8',
                 'max_frac_0.8@40': 'default_max_frac_0.8'}
        jobs = {j['name']: j for j in SUMMARY['jobs']}
        for v, t in pairs.items():
            self.assertEqual(jobs[v]['full_world_path_sha256'], TARGET[t]['full_world_path_sha256'], v)

    def test_measures_consistent_with_stored_trajectories(self):
        for j in SUMMARY['jobs']:
            m, tr = j['measures'], j['trajectory_steps_0_20']
            self.assertEqual(m['q_compute_0'], tr['q_compute'][0])
            self.assertEqual(m['q_compute_20'], tr['q_compute'][20])
            self.assertEqual(m['q_compute_peak_0_20'], max(tr['q_compute']))
            self.assertLessEqual(max(tr['frac_automated']), m['max_frac'] * (1 + 1e-9), j['name'])
            if m['first_step_f_at_max'] is not None and m['first_step_f_at_max'] <= 20:
                self.assertGreaterEqual(tr['frac_automated'][m['first_step_f_at_max']], m['max_frac'] * (1 - 1e-9))

    def test_every_run_stops_at_its_cap(self):
        # Recorded, not hidden: the optimizer never meets its tolerance at any cap tried.
        for j in SUMMARY['jobs']:
            self.assertEqual(j['diagnostics']['iterations'], j['cap'], j['name'])
            self.assertTrue(j['diagnostics']['checks_pass'], j['name'])

    def test_objective_improves_with_cap_except_one(self):
        # The solver minimizes `objective`. More iterations lower it in every variant but one:
        # flop_gap_0.4 ends worse at cap 80 than at cap 40 (learning-rate schedule depends on
        # the cap). Recorded as a finding in README.md; this pins it.
        worse = []
        for v, jobs in summarize.by_variant(SUMMARY).items():
            obj = [jobs[c]['diagnostics']['objective'] for c in sorted(jobs)]
            if obj != sorted(obj, reverse=True):
                worse.append(v)
            self.assertEqual(obj[-1], min(obj), v)
        self.assertEqual(worse, ['flop_gap_0.4'])


class Verdicts(unittest.TestCase):
    def test_rule(self):
        self.assertEqual(summarize.judge([True, True, True], [True, True, True]), 'survives')
        self.assertEqual(summarize.judge([False, False, False], [True, True, True]), 'flips')
        self.assertEqual(summarize.judge([True, False, True], [True, True, True]), 'not robust')
        self.assertEqual(summarize.judge([True, True, True], [True, False, True]), 'not robust (baseline)')

    def test_default_conclusions_hold_at_every_cap(self):
        _, table = summarize.verdicts(SUMMARY)
        for cid, _, _ in summarize.CONCLUSIONS:
            self.assertEqual(table[('default', cid)]['verdict'], 'holds', cid)

    def test_partial_automation_caps_peak_growth(self):
        # The headline of the sweep, pinned so a rerun that changes it fails loudly.
        _, table = summarize.verdicts(SUMMARY)
        for v in ('max_frac_0.5', 'max_frac_0.8', 'max_frac_0.9'):
            self.assertEqual(table[(v, 'C2')]['verdict'], 'flips', v)

    def test_no_verdict_flips_within_the_noise_band(self):
        # Every predicate agrees across caps 40/80/160 in every variant. If a rerun changes
        # this, the stopping rule applies: report "not robust", do not pick a side.
        _, table = summarize.verdicts(SUMMARY)
        self.assertEqual([k for k, r in table.items() if r['verdict'].startswith('not robust')], [])


class BundleWatch(unittest.TestCase):
    def test_pin_matches_fetch_script_and_presets(self):
        self.assertEqual(PIN['sha256'], PINNED_BUNDLE)
        self.assertEqual(PIN['errors'], [])
        for k, name in enumerate(('default', 'conservative', 'aggressive')):
            self.assertEqual(PIN['presets'][k], TARGET[name]['args'], name)

    def test_unchanged_bundle_passes(self):
        changed, report = bundle_watch.compare(PIN, PIN)
        self.assertFalse(changed)
        self.assertIn('unchanged', report)

    def test_redeploy_reports_hash_table_and_preset_diff(self):
        fresh = json.loads(json.dumps(PIN))
        fresh['sha256'] = 'f' * 64
        fresh['parameter_table'][0]['Default'] = '36.6'
        fresh['presets'][1]['modelParams']['rnd']['rnd_wedge'] = 3
        changed, report = bundle_watch.compare(PIN, fresh)
        self.assertTrue(changed)
        self.assertIn('f' * 64, report)
        self.assertIn("`automation.train_reqs` Default: '36.5' -> '36.6'", report)
        self.assertIn('preset 1 `modelParams.rnd.rnd_wedge`: 1 -> 3', report)


if __name__ == '__main__':
    unittest.main(verbosity=1)
