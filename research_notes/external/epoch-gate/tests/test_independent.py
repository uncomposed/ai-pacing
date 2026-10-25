"""Fast checks for the independent GATE re-implementation (issue #34). No network, no solving.

[[ai gen]] Run: python3 research_notes/external/epoch-gate/tests/test_independent.py (wired into
`make test`; needs numpy, which CI pins). The independent model is checked against the official
solver's own output: every law separately, then a full replay of the official decisions. The
re-solve itself (scipy + autograd, minutes) is run by the epoch-gate-resolve workflow; here only its
committed result is checked against the targets of issue #34.
"""
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / 'independent'))
import gate_indep as gi  # noqa: E402

TARGET = json.loads((HERE / 'data' / 'baseline_target.json').read_text())
JOBS = {j['name']: j for j in TARGET['jobs']}
FULL = json.loads((HERE / 'independent' / 'data' / 'official_full.json').read_text())['presets']
IDENT = json.loads((HERE / 'independent' / 'data' / 'identification.json').read_text())
RESOLVE_PATH = HERE / 'independent' / 'results' / 'resolve_default.json'
PRESETS = ['default', 'conservative', 'aggressive']
EXACT = 1e-12
REPLAY = 1e-9


def rel(a, b):
    return 0.0 if a == b else abs(a - b) / max(abs(a), abs(b))


def model(name):
    return gi.Model(JOBS[name]['args']['modelParams'])


def start(rows, key, t, init):
    return rows[key][t - 1] if t > 0 else init


class TableDerivations(unittest.TestCase):
    """E6: the R&D constants follow from the parameter table, not from a fit (D4)."""

    def test_paper_constants_reproduced(self):
        rd = model('default').rd
        # Paper appendix: phi_H = 0.4/5.2 = 0.0769, phi_S = 0.4/1.25 = 0.32, theta_H = 0.192, theta_S = 0.0307,
        # with lambda = 0.4 x 0.35 = 0.14 (researcher elasticity 0.35).
        self.assertAlmostEqual(rd['hardware']['phi'], 0.0769, 4)
        self.assertAlmostEqual(rd['software']['phi'], 0.32, 12)
        self.assertAlmostEqual(rd['hardware']['theta'], 0.192, 3)
        self.assertAlmostEqual(rd['software']['theta'], 0.0307, 4)
        self.assertEqual(rd['hardware']['lam'], 0.14)

    def test_flop_gap_constant_explained(self):
        # D3: schedule_x = log10 T - Delta - 5 with Delta = flop_gap_frac (log10 T - log10 C_T(0)), so the
        # empirical constant 16.608061 is log10(5e25) - 5/0.55.
        for j in TARGET['jobs']:
            M = gi.Model(j['args']['modelParams']) if j['name'] not in ('default_max_frac_0.8', 'default_rnd_wedge_8',
                                                                         'default_no_labor_reallocation') else None
            a = j['args']['modelParams']['automation']
            delta = a['flop_gap_frac'] * (a['train_reqs'] - math.log10(j['args']['modelParams']['main']['best_training_run']))
            self.assertLess(abs(j['automation_schedule_x'][0] - (a['train_reqs'] - delta - 5)), EXACT, j['name'])
            if M:
                self.assertLess(abs(M.schedule_x - j['automation_schedule_x'][0]), EXACT, j['name'])
        self.assertAlmostEqual(math.log10(5e25) - 5 / 0.55, 16.608060913, 9)


class Laws(unittest.TestCase):
    """Each law on its own, fed the official start-of-year state and decisions (all 80 rows)."""

    def test_rnd_law(self):
        for name in PRESETS:
            M, r = model(name), FULL[name]['rows']
            for kind in ('hardware', 'software'):
                X = M.rd[kind]['X0']
                for t in range(80):
                    I = r['q_%s_rnd' % kind][t] * r['gwp'][t]
                    self.assertLess(rel(M.rd_step(kind, X, I), r[kind][t]), EXACT, f'{name} {kind} {t}')
                    X = r[kind][t]

    def test_compute_adjustment_cost(self):
        for name in PRESETS:
            M, r = model(name), FULL[name]['rows']
            for t in range(80):
                Q, H = start(r, 'compute', t, M.Q0), start(r, 'hardware', t, M.rd['hardware']['X0'])
                Iq = M.effective_compute_investment(r['q_compute'][t] * r['gwp'][t], Q, H)
                self.assertLess(rel(Iq, r['effective_compute_investment'][t]), 1e-10, f'{name} {t}')

    def test_usable_compute_and_training_run(self):
        for name in PRESETS:
            M, r = model(name), FULL[name]['rows']
            for t in range(80):
                Q = start(r, 'compute', t, M.Q0)
                S = start(r, 'software', t, 1.0)
                self.assertLess(rel(r['training_compute'][t] + r['runtime_compute'][t], M.usable(Q)), 1e-10, f'{name} {t}')
                CT = start(r, 'best_training_run', t, M.ct0)
                self.assertLess(rel(CT + r['training_compute'][t] * S, r['best_training_run'][t]), 1e-10, f'{name} {t}')

    def test_frontier(self):
        for name in PRESETS:
            M, r = model(name), FULL[name]['rows']
            for t in range(80):
                CT = start(r, 'best_training_run', t, M.ct0)
                self.assertLess(abs(M.f_max(math.log10(CT)) - r['frac_automated'][t]), 1e-10, f'{name} {t}')

    def test_task_composite_and_output(self):
        for name in PRESETS:
            M, r = model(name), FULL[name]['rows']
            for t in range(80):
                CI = r['runtime_compute'][t - 1] * r['software'][t - 1] if t > 0 else M.CI0
                CT = start(r, 'best_training_run', t, M.ct0)
                L = M.L0 * math.exp(M.gL * t)
                T, _ = M.composite(CI, math.log10(CT), L, r['frac_automated'][t])
                self.assertLess(rel(T, r['cognitive_ces_term'][t]), REPLAY, f'{name} {t}')
                K = start(r, 'capital', t, M.K0)
                Y = M.A * r['cognitive_ces_term'][t] ** (1 - M.alpha) * K ** M.alpha
                self.assertLess(rel(Y, r['gwp'][t]), 1e-10, f'{name} {t}')

    def test_objective_scale(self):
        for j in TARGET['jobs']:
            d = j['diagnostics']
            eta = j['args']['modelParams']['objective']['eta']
            self.assertLess(rel(d['objective'] / d['utility'], -gi.OBJECTIVE_REF_C ** (eta - 1)), EXACT, j['name'])


class Replay(unittest.TestCase):
    """The official decisions through the independent model reproduce the official run."""

    def test_full_replay(self):
        for name in PRESETS:
            M, r = model(name), FULL[name]['rows']
            q = np.array([r[k] for k in ('q_consumption', 'q_capital', 'q_compute', 'q_hardware_rnd',
                                         'q_software_rnd', 'q_training_compute')]).T
            out = M.simulate(np.vstack([q, np.tile(q[-1], (80, 1))]))   # years 80-159 are not reported
            for k in ('gwp', 'consumption', 'capital', 'frac_automated', 'compute', 'training_compute', 'runtime_compute',
                      'best_training_run', 'hardware', 'software', 'effective_compute_investment', 'cognitive_ces_term'):
                worst = max(rel(a, b) for a, b in zip(out[k][:80], r[k]))
                self.assertLess(worst, REPLAY, f'{name} {k}')
            self.assertLess(rel(out['objective'], FULL[name]['objective']), 1e-6, name)
            ms = gi.milestones(list(out['gwp'][:80]), list(out['frac_automated'][:80]))
            for k, v in ms.items():
                self.assertEqual(v, JOBS[name]['milestones'][k], f'{name} {k}')

    def test_probe_record(self):
        """identification.json: black-box probes of the official solver (independent/identify.py)."""
        runs = {x['name']: x for x in IDENT['runs']}
        self.assertEqual(len(runs), 13)
        for x in runs.values():
            self.assertLess(rel(x['quadrature_solver_over_exact'], x['quadrature_left1000_over_exact']), 1e-9, x['name'])
            self.assertLess(rel(x['lattice']['spacing'], x['lattice']['spacing_predicted']), 1e-8, x['name'])
            self.assertLess(x['lattice']['anchor_offset_in_spacings'], 1e-6, x['name'])
            self.assertLess(abs(x['schedule_x'] - x['schedule_x_predicted']), EXACT, x['name'])
        self.assertLess(IDENT['K_max'] / IDENT['K_min'] - 1, 2e-6)
        self.assertTrue(IDENT['K_min'] <= gi.OBJECTIVE_K * (1 + 1e-6) and gi.OBJECTIVE_K <= IDENT['K_max'] * (1 + 1e-6))
        exact = [n for n, x in runs.items() if x['replay']['max_rel_diff'] < REPLAY]
        self.assertEqual(sorted(exact), sorted(['default', 'conservative', 'aggressive', 'rho_m2', 'flopgap_0.4',
                                                'm_1', 'ct0_1e26', 'T_37']))
        # Open (RECONSTRUCTION.md, D11): years where the human/digital boundary sits at the frontier.
        for n in set(runs) - set(exact):
            self.assertLess(runs[n]['replay']['max_rel_diff'], 1e-2, n)
            self.assertLess(abs(runs[n]['replay']['objective_rel_diff']), 1e-4, n)


@unittest.skipUnless(RESOLVE_PATH.exists(), 'no committed re-solve result')
class Resolve(unittest.TestCase):
    """Issue #34 targets for the committed independent re-solve of the Default preset."""

    R = json.loads(RESOLVE_PATH.read_text()) if RESOLVE_PATH.exists() else None

    def test_milestones_exact(self):
        c = self.R['comparison']
        self.assertEqual(c['milestones_resolve'], c['milestones_official'])

    def test_objective_within_1e3(self):
        self.assertLess(abs(self.R['comparison']['objective_rel_diff']), 1e-3)

    def test_result_is_reproducible_from_its_decisions(self):
        # The committed trajectory is what the independent model gives for the committed decisions.
        M = model('default')
        tr = self.R['trajectory']
        q = np.array([tr[k] for k in ('q_consumption', 'q_capital', 'q_compute', 'q_hardware_rnd',
                                      'q_software_rnd', 'q_training_compute')]).T
        out = M.simulate(q)
        for k in ('gwp', 'compute', 'best_training_run', 'cognitive_ces_term'):
            self.assertLess(max(rel(a, b) for a, b in zip(out[k], tr[k])), 1e-9, k)


if __name__ == '__main__':
    unittest.main(verbosity=1)
