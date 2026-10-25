"""Reweighting identities behind measure_sensitivity.py, and that its committed report is current.

Run from anywhere:  python3 tests/test_measure_sensitivity.py   (no solving; a few seconds)
"""
import json
import math
import os
import sys
import unittest

MODEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MODEL)
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np  # noqa: E402

import measure_sensitivity as ms  # noqa: E402
import robust_design as rd  # noqa: E402


def big_sample(n=40000, seed=3):
    U = rd.lhs(n, len(rd.UNCERTAIN), seed)
    th = rd.u_to_params(U, "full")
    return U, {p: np.array([t[p] for t in th]) for p in rd.UNAMES}


class Reweighting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.U, cls.v = big_sample()

    def test_base_measure_has_unit_weights(self):
        w = ms.weights(self.U, self.v, [])
        self.assertTrue(np.all(w == 1.0))
        self.assertEqual(ms.ess(w), len(w))

    def test_density_ratios_integrate_to_one(self):
        # E_sampled[new/sampled] = 1 for every admissible measure.
        for mid, _, comps in ms.MEASURES:
            with self.subTest(measure=mid):
                self.assertAlmostEqual(ms.weights(self.U, self.v, comps).mean(), 1.0, delta=0.05)

    def test_linear_reweighting_recovers_the_uniform_mean(self):
        lo, hi = 0.02, 1.0   # mu
        w = ms.component_weight(self.U, self.v, ("linear", "mu"))
        self.assertAlmostEqual(ms.weighted_share(w, self.v["mu"]), (lo + hi) / 2, delta=0.01)

    def test_point_mass_reweighting_hits_the_new_share(self):
        w = ms.component_weight(self.U, self.v, ("pointmass", "ell_inf", 0.1))
        self.assertAlmostEqual(ms.weighted_share(w, (self.v["ell_inf"] == 0).astype(float)), 0.1, places=2)

    def test_point_mass_without_support_is_refused(self):
        with self.assertRaises(ValueError):
            ms.component_weight(self.U, self.v, ("pointmass", "kill_pre", 0.5))

    def test_copula_induces_the_rank_correlation(self):
        w = ms.component_weight(self.U, self.v, ("copula", "q", "D", 0.5))
        a, b = self.U[:, ms.COL["q"]], self.U[:, ms.COL["D"]]
        ma, mb = np.average(a, weights=w), np.average(b, weights=w)
        cov = np.average((a - ma) * (b - mb), weights=w)
        sd = math.sqrt(np.average((a - ma) ** 2, weights=w) * np.average((b - mb) ** 2, weights=w))
        spearman = 6 / math.pi * math.asin(0.5 / 2)     # Gaussian copula: rho_S = (6/pi) asin(rho/2)
        self.assertAlmostEqual(cov / sd, spearman, delta=0.03)

    def test_wilson_interval(self):
        lo, hi = ms.wilson(15, 192)
        self.assertAlmostEqual(lo, 0.0479, places=3)
        self.assertAlmostEqual(hi, 0.1249, places=4)

    def test_design_keys_parse(self):
        self.assertEqual({"D_mult": "3", "T_reloc": "4", "d": "0.99", "q_red": "2", "seq": "1"},
                         ms.design_levers("D_mult=3_T_reloc=4_d=0.99_q_red=2_seq=1"))
        self.assertFalse(set(ms.design_levers("D_mult=3_pf_bel=2")) <= ms.DESIGN_KEYS)


class CommittedReport(unittest.TestCase):
    def test_report_is_current_and_labelled(self):
        md, js = ms.build()
        with open(ms.OUT_JSON) as f:
            committed = json.load(f)
        self.assertEqual(committed["label"]["interpretation"], ms.INTERPRETATION)
        self.assertEqual(committed["designs"], js["designs"])
        for a, b in zip(committed["rows"], js["rows"]):
            self.assertEqual(a["id"], b["id"])
            self.assertEqual(a["top"], b["top"])
            self.assertEqual(a["best_stack_rank"], b["best_stack_rank"])
            for d, s in a["shares"].items():
                self.assertAlmostEqual(s, b["shares"][d], places=6)
        with open(ms.OUT_MD) as f:
            self.assertEqual(f.read(), md)


if __name__ == "__main__":
    unittest.main()
