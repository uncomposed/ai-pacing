"""Fast checks for the GATE replication (issue #13). No network, no solving, stdlib only.

Run: python3 research_notes/external/epoch-gate/tests/test_epoch_gate.py
(wired into `make test`). The official solver itself is rerun by the
`epoch-gate` workflow (workflow_dispatch), not here.
"""
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / 'official'))
import gate_core as g  # noqa: E402
import diagnostics  # noqa: E402

TARGET = json.loads((HERE / 'data' / 'baseline_target.json').read_text())
JOBS = {j['name']: j for j in TARGET['jobs']}
PRESETS = ['default', 'conservative', 'aggressive']
PINNED_BUNDLE = 'c2104290dc486c27e07b6614dd306604bd98a095d660369d3ce356f481e72731'
EXACT = 1e-12


def load_yaml(path):
    try:
        import yaml
        return yaml.safe_load(path.read_text())
    except ImportError:  # make check already needs Ruby, whose standard library parses YAML
        out = subprocess.run(['ruby', '-ryaml', '-rjson', '-e', 'puts JSON.dump(YAML.safe_load(File.read(ARGV[0])))', str(path)],
                             check=True, capture_output=True, text=True)
        return json.loads(out.stdout)


def states(job):
    s = dict(job['trajectory'])
    s['steps'] = job['steps']
    return s


class TargetProvenance(unittest.TestCase):
    def test_bundle_pin_consistent(self):
        self.assertEqual(TARGET['bundle_sha256'], PINNED_BUNDLE)
        self.assertIn(PINNED_BUNDLE, (HERE / 'official' / 'fetch_bundle.sh').read_text())
        sources = load_yaml(HERE / 'SOURCES.yaml')
        self.assertIn(PINNED_BUNDLE, json.dumps(sources))

    def test_presets_rerun_equals_playground_cache(self):
        for name in PRESETS:
            c = JOBS[name]['cached_vs_rerun']
            self.assertEqual(c['max_rel_diff'], 0.0, name)
            self.assertTrue(c['objective_path_identical'] and c['check_flags_identical'] and c['same_number_of_steps'], name)
            self.assertGreater(c['values_compared'], 10000, name)

    def test_jobs_match_committed_job_list(self):
        jobs = json.loads((HERE / 'official' / 'jobs.json').read_text())
        self.assertEqual([j['name'] for j in jobs], [j['name'] for j in TARGET['jobs']])

    def test_solver_sanity_checks_pass_and_objective_decreases(self):
        for j in TARGET['jobs']:
            d = j['diagnostics']
            self.assertTrue(d['check'] and d['simple_policy_check'] and d['spliced_utility_check'], j['name'])
            # The solver minimizes `objective`; the cheaper policy class and spliced utility score worse.
            self.assertLess(d['objective'], d['simple_objective'], j['name'])
            self.assertLess(d['objective'], d['spliced_objective'], j['name'])
            self.assertLessEqual(d['objective_path'][-1], d['objective_path'][0], j['name'])
            # Every run stops at maxiter, not at a tolerance: recorded, not hidden.
            self.assertTrue(d['stopped_at_maxiter'], j['name'])


class ExactIdentities(unittest.TestCase):
    """Equations that hold on the solver output to rounding (EQUATIONS.md status 'exact')."""

    def test_identities(self):
        for name in PRESETS:
            j = JOBS[name]
            r = g.check_states(states(j), j['args']['modelParams'])
            r.pop('E14_implied_tfp')
            for k, v in r.items():
                if k.endswith('violations') or k.endswith('decreases'):
                    self.assertEqual(v, 0, f'{name} {k}')
                else:
                    self.assertLess(v, EXACT, f'{name} {k}')

    def test_capital_law_exponential_step(self):
        for name in PRESETS:
            j = JOBS[name]
            res = g.capital_law_residuals(states(j), j['args']['modelParams'], 'exponential')
            self.assertEqual(len(res), 20)
            self.assertLess(max(map(abs, res)), EXACT, name)
            # The naive forward-Euler reading of the same law is off by about 0.2% a step.
            euler = g.capital_law_residuals(states(j), j['args']['modelParams'], 'euler')
            self.assertGreater(max(map(abs, euler)), 1e-3, name)

    def test_compute_stock_law(self):
        for name in PRESETS:
            j = JOBS[name]
            res = g.compute_stock_law_residuals(states(j), j['args']['modelParams'])
            self.assertEqual(len(res), 20)
            self.assertLess(max(map(abs, res)), EXACT, name)

    def test_tfp_constant_before_automation_moves(self):
        # While f is at f_init (steps 0-2 in every preset), implied A is constant
        # to 0.05%; once f rises it drifts, which EQUATIONS.md records as unresolved (E14).
        for name in PRESETS:
            j = JOBS[name]
            tfp = g.check_states(states(j), j['args']['modelParams'])['E14_implied_tfp']
            self.assertLess(abs(tfp[2] / tfp[0] - 1), 5e-4, name)


class ComputeSplit(unittest.TestCase):
    """#35: E7 resolved. D + R = g(Q at the start of the step); the physical training run accumulates D."""

    def test_split_exhausts_usable_compute(self):
        import coupling_example as cx
        for name in PRESETS:
            r = cx.split_identities(JOBS[name])
            self.assertGreaterEqual(r['consecutive_pairs'], 20, name)
            self.assertLess(r['step0_rel_err'], EXACT, name)
            self.assertLess(r['budget_max_rel_err'], EXACT, name)
            self.assertLess(r['training_run_max_rel_err'], EXACT, name)

    def test_heat_limit_explains_the_falling_share(self):
        # The share (D + R) / Q falls to ~0 because g(Q) saturates at C_L, not because compute goes unused by the split.
        t = JOBS['aggressive']['trajectory']
        c_l = JOBS['aggressive']['args']['modelParams']['main']['physical_compute_limit']
        i = JOBS['aggressive']['steps'].index(25)
        self.assertLess((t['training_compute'][i] + t['runtime_compute'][i]) / t['compute'][i], 1e-4)
        self.assertAlmostEqual((t['training_compute'][i] + t['runtime_compute'][i]) / c_l, 1.0, places=3)

    def test_committed_example_is_current(self):
        import coupling_example as cx
        self.assertEqual(json.loads((HERE / 'coupling_example.json').read_text()), json.loads(json.dumps(cx.build())))


class Automation(unittest.TestCase):
    def test_function_shape(self):
        f = g.automation_fraction
        self.assertEqual(f(20.0, 36.5, 10.0, 0.1), 0.1)
        self.assertEqual(f(26.5, 36.5, 10.0, 0.1), 0.1)
        self.assertAlmostEqual(f(31.5, 36.5, 10.0, 0.1), 0.55)
        self.assertEqual(f(36.5, 36.5, 10.0, 0.1), 1.0)
        self.assertEqual(f(40.0, 36.5, 10.0, 0.1), 1.0)
        # Paper footnote: C_T = 1e30, iota_max = 100 (2 OOM), m = 2 -> C_{T+iota} = 1e31.
        self.assertAlmostEqual(g.log10_capability(30.0, 2.0, 2.0), 31.0)

    def test_deployed_share_within_frontier(self):
        for j in TARGET['jobs']:
            if 'frac_automated' not in j['trajectory'] or 'best_training_run' not in j['trajectory']:
                continue
            a = g.check_automation(states(j), j['args']['modelParams'], j['automation_schedule_x'][0])
            self.assertEqual(a['violations'], 0, j['name'])

    def test_flop_gap_mapping_found_empirically(self):
        # Delta_FLOP = flop_gap_frac * (train_reqs - X0) with one X0 across all ten runs;
        # the paper does not state X0 (README, discrepancy D3).
        x0 = set()
        for j in TARGET['jobs']:
            a = j['args']['modelParams']['automation']
            delta = a['train_reqs'] - j['automation_schedule_x'][0]
            x0.add(round(a['train_reqs'] - delta / a['flop_gap_frac'], 9))
        self.assertEqual(x0, {16.608060913})


class Milestones(unittest.TestCase):
    def test_default_baseline_target(self):
        m = JOBS['default']['milestones']
        self.assertEqual((m['first_step_frac_automated_ge_0.5'], m['first_step_frac_automated_ge_0.9'],
                          m['first_step_frac_automated_eq_1'], m['first_step_gwp_growth_ge_30pct']), (4, 8, 9, 5))

    def test_milestones_stable_under_optimizer_budget(self):
        base = JOBS['default']['milestones']
        for name in ('default_maxiter_20', 'default_maxiter_80'):
            m = JOBS[name]['milestones']
            for k, v in base.items():
                if 'step' in k:
                    self.assertEqual(m[k], v, f'{name} {k}')

    def test_diagnostics_report_runs(self):
        text = diagnostics.report(TARGET)
        self.assertIn('default_maxiter_80', text)


class Records(unittest.TestCase):
    def test_sources(self):
        s = load_yaml(HERE / 'SOURCES.yaml')
        for src in s['sources']:
            for k in ('id', 'url', 'version', 'accessed', 'license', 'used_for', 'status'):
                self.assertIn(k, src, src.get('id'))

    def test_evidence_records(self):
        # Shape and dates are checked by tools/evidence_tool.py in `make check`; here only
        # that the GATE records exist, carry the pin, and are never observations (#8).
        recs = {r['id']: r for r in load_yaml(ROOT / 'evidence' / 'records.yaml')['records']}
        paper, runs = recs['EV-GATE-PAPER-2025'], recs['EV-GATE-PLAYGROUND-2026']
        self.assertEqual(paper['kind'], 'source_model_assumption')
        self.assertEqual(runs['kind'], 'source_model_output')
        self.assertIn(PINNED_BUNDLE, runs['source']['version'])
        self.assertEqual(runs['depends_on'], ['EV-GATE-PAPER-2025'])

    def test_contract_adapter_points_here(self):
        modes = load_yaml(ROOT / 'systems' / 'modes.yaml')
        ad = next(a for a in modes['adapters'] if a['id'] == 'AD-GATE')
        self.assertIn('c2104290', ad['source'])
        self.assertEqual({m: e['coverage'] for m, e in ad['modes'].items()},
                         {'MODE-HUMAN-LAB': 'partial', 'MODE-SOVEREIGN-CAPABLE': 'unsupported', 'MODE-SOVEREIGN': 'unsupported'})


if __name__ == '__main__':
    unittest.main(verbosity=1)
