"""Fast checks for the issue #9 variants (variants/). No network; about 20 s.

    python3 tests/test_variants.py

1. The fixed-terms regime of the bargaining game reproduces the baseline's saturation recursion (strike year 165 in the
   eroding-reserve world, docking/out/powell.json: closed form with failure branch and the full solver).
2. The bargaining example separates existence of a bargain from credible implementation.
3. The reduced bootstrap game's baseline limit reproduces the full solver's R6c brackets and the saturation closed form.
4. Switches that are off leave the reduced game unchanged (identity checks).
5. Re-running reproduces the committed results/variants/*.json.
6. Issue #51 (the R6c cell A_close 0.03, L_f 0.9): the grid-free path reference (variants/cap_approach.py) puts the
   needed q at 0.563, above both the committed solver bracket and the reduced game's default-grid bracket; the reduced
   game with near-cap grid points (cap_pts) converges to it.
"""
import json
import os
import sys
import unittest

MODEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(MODEL, "variants"))
sys.path.insert(0, MODEL)
os.environ.setdefault("OMP_NUM_THREADS", "1")

import bargaining as bg  # noqa: E402
import preventive as pv  # noqa: E402
import cap_approach as ca  # noqa: E402
import equilibrium_model as em  # noqa: E402

RES = os.path.join(MODEL, "results", "variants")



def _read_json(path):
    with open(path) as f:
        return json.load(f)


def close(a, b, rel=1e-9):
    if a is None or b is None:
        return a is b
    return abs(a - b) <= rel * max(1.0, abs(a), abs(b))


class Bargaining(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = bg.run_all()

    def test_fixed_terms_is_the_baseline_recursion(self):
        dock = _read_json((os.path.join(MODEL, "docking", "out", "powell.json")))["erosion"]["strike_year"][0]
        self.assertEqual(dock["A0"], bg.A_NEAR_CAP)
        self.assertEqual(self.out["eroding_reserve"]["fixed"]["strike_year"], dock["closed_form_with_fail"])
        self.assertAlmostEqual(self.out["eroding_reserve"]["fixed"]["strike_year"], dock["solver"], places=6)

    def test_existence_versus_credible_implementation(self):
        cw = self.out["closing_window"]
        self.assertTrue(cw["diagnostics"]["bargain_exists_every_year"])
        self.assertTrue(cw["diagnostics"]["commitment_problem"])
        self.assertIsNone(cw["fixed"]["strike_year"])          # fixed terms act as a commitment device
        self.assertIsNone(cw["committed"]["strike_year"])
        self.assertEqual(cw["reneg_two_sided"]["strike_year"], 19)   # preventive strike the year before the upgrade
        self.assertEqual(cw["reneg_down"]["strike_year"], 19)
        self.assertLess(cw["reneg_two_sided"]["V_H"], cw["fixed"]["V_H"])

    def test_renegotiation_buys_off_prize_only_strikes(self):
        for s in ("eroding_reserve", "no_reserve"):
            r = self.out[s]
            self.assertTrue(r["diagnostics"]["bargain_exists_every_year"])
            self.assertFalse(r["diagnostics"]["commitment_problem"])
            self.assertIsNotNone(r["fixed"]["strike_year"])
            self.assertIsNone(r["reneg_up"]["strike_year"])
            self.assertIsNone(r["reneg_two_sided"]["strike_year"])

    def test_no_bargain_when_harvest_dominates(self):
        r = self.out["harvest"]
        self.assertFalse(r["diagnostics"]["bargain_exists_t0"])
        for k, o in r.items():
            if k != "diagnostics":
                self.assertEqual(o["strike_year"], 0, k)

    def test_reproduces_committed_json(self):
        ref = _read_json((os.path.join(RES, "bargaining.json")))["raw"]
        for s, R in self.out.items():
            for k, o in R.items():
                for f, v in o.items():
                    w = ref[s][k][f]
                    if isinstance(v, float):
                        self.assertTrue(close(v, w), (s, k, f, v, w))
                    else:
                        self.assertEqual(v, w, (s, k, f))


class ReducedGame(unittest.TestCase):
    base = em.baseline(**pv.R6_CLEAN)

    def test_r6c_cell_matches_full_solver(self):
        ref = _read_json((os.path.join(MODEL, "results", "equilibrium_round3_summary.json")))["r6_solver"]
        brackets = {tuple(c): b for c, b in zip(ref["clean_cases"], ref["q_clean"])}
        lo, hi = brackets[(1.0, 0.5)]
        p = dict(self.base, A0=1.0, A_close=1.0, L_f=0.5, d=1.0, w_seized=0.9)
        self.assertGreaterEqual(pv.solve(dict(p, q=lo))["att"], 0.5)
        self.assertLess(pv.solve(dict(p, q=hi))["att"], 0.5)

    def test_saturated_start_matches_closed_form(self):
        p = dict(self.base, A0=1.5e9, d=1.0, w_seized=0.9)
        self.assertGreater(em.cap_gap_fail(dict(p, q=0.28), 1.5e9), 0)
        self.assertLess(em.cap_gap_fail(dict(p, q=0.29), 1.5e9), 0)
        self.assertGreaterEqual(pv.solve(dict(p, q=0.28), T=150)["att"], 0.5)
        self.assertLess(pv.solve(dict(p, q=0.29), T=150)["att"], 0.5)

    def test_switches_off_are_identities(self):
        p = dict(self.base, q=0.55, kill_pre=0.5)
        ref = pv.solve(p)
        for o in (dict(dq=0.2, dsh=0.2), dict(human_first=False, sh0=0.3, dsh=0.2)):
            r = pv.solve(p, o)
            for k in ("V_A", "V_H", "att", "suc", "fail", "hk"):
                self.assertTrue(close(r[k], ref[k], 1e-12), (o, k, r[k], ref[k]))

    def test_reproduces_committed_json(self):
        ref = _read_json((os.path.join(RES, "preventive.json")))["raw"]
        for s, pol in (("weak_survivable", "learn"), ("late_harvest", "shutdown_0.3")):
            r = pv.solve(dict(self.base, **pv.STRUCTURES[s]), pv.POLICIES[pol])
            for k, v in r.items():
                w = ref[s][pol][k]
                if isinstance(v, float):
                    self.assertTrue(close(v, w, 1e-7), (s, pol, k, v, w))
                else:
                    self.assertEqual(v, w, (s, pol, k))


class CapApproach(unittest.TestCase):
    """Issue #51. Under the logistic law the AI's path from below reaches within O(1) of Kmax (K - A shrinks by about
    1 - g a year). There a plugged landing (below K) regrows while an unplugged one (above K) is permanent, so the
    reserve deters less than in the static region above the cap. Neither grid resolves that region: the full solver
    interpolates across the cap into the static region (its R6c bracket is the static threshold 0.33), and the
    reduced game's default grid stops 1000 units below K (its bracket is the growth-phase threshold 0.19)."""
    p = ca.cell(0.03, 0.9)

    def test_grid_free_path_strikes_next_to_the_cap(self):
        s = ca.path_stop(dict(self.p, q=0.55))
        self.assertIsNotNone(s["strike_year"])
        self.assertGreater(s["strike_year"], 100)          # long after closure: not a growth-phase strike
        self.assertLess(s["gap_to_cap"], 1.0)              # within one Earth-industry unit of Kmax = 1e9
        self.assertIsNone(ca.path_stop(dict(self.p, q=0.58))["strike_year"])

    def test_committed_brackets_sit_below_the_stated_law(self):
        ref = _read_json(os.path.join(MODEL, "results", "equilibrium_round3_summary.json"))["r6_solver"]
        solver = {tuple(c): b for c, b in zip(ref["clean_cases"], ref["q_clean"])}[(0.03, 0.9)]
        self.assertEqual(solver, [0.33203125, 0.3359375])
        self.assertIsNotNone(ca.path_stop(dict(self.p, q=solver[1]))["strike_year"])   # the solver's "safe" q strikes
        # the reduced game's default grid reproduces its committed bracket (results/variants/tables.md H1)
        self.assertGreaterEqual(pv.solve(dict(self.p, q=0.19140625))["att"], 0.5)
        self.assertLess(pv.solve(dict(self.p, q=0.1953125))["att"], 0.5)

    def test_near_cap_grid_converges_to_the_path(self):
        self.assertGreaterEqual(pv.solve(dict(self.p, q=0.5625), cap_pts=20)["att"], 0.5)
        self.assertLess(pv.solve(dict(self.p, q=0.5664), cap_pts=20)["att"], 0.5)


class Selection(unittest.TestCase):
    def test_best_selection_reproduces_round1(self):
        """The committed selection run's 'best' column is the round-1 solver output (equilibrium_summary.json)."""
        sel = _read_json((os.path.join(RES, "selection.json")))
        ref = _read_json((os.path.join(MODEL, "results", "equilibrium_summary.json")))["scenarios"]
        self.assertEqual(sel["names"], [r[0] for r in ref])
        for i, r in enumerate(ref):
            self.assertEqual(sel["best"]["act0"][i], r[1])
            for k, j in (("att", 2), ("suc", 4), ("riv", 5), ("WH", 8)):
                self.assertTrue(close(sel["best"][k][i], r[j], 1e-9), (r[0], k, sel["best"][k][i], r[j]))


if __name__ == "__main__":
    unittest.main(verbosity=1)
