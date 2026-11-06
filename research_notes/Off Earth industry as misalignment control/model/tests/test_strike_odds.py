"""strike_odds.py: the patched solver leaves the canonical one untouched and is exact at its default.

Run from anywhere:  python3 tests/test_strike_odds.py   (small solves; a few seconds)
"""
import os
import sys
import unittest

MODEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MODEL)
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np  # noqa: E402

import breakout_options as bo  # noqa: E402
import equilibrium_model as em  # noqa: E402
import strike_odds as so  # noqa: E402

KW = dict(N=2, T_H=40, nA=50)
WORLD = dict(em.baseline(), **dict(bo.STATIC, c_w=0.7))


def run(mod, **over):
    return mod.solve(mod.batch([mod.baseline(**dict(WORLD, **over))]), **KW)


def same(a, b):
    return all(np.array_equal(np.asarray(a[k]), np.asarray(b[k])) for k in ("VA", "WH", "att", "suc", "exit", "act0"))


class StrikeOdds(unittest.TestCase):
    def test_patches_apply_once_and_canonical_untouched(self):
        with open(os.path.join(MODEL, "equilibrium_model.py"), encoding="utf-8") as f:
            src = f.read()
        for old, _ in so.patches():
            self.assertEqual(src.count(old), 1)
        self.assertIn("ps_dep", so.sd.PARAMS)
        self.assertNotIn("ps_dep", em.PARAMS)

    def test_default_is_bit_identical(self):
        for over in ({}, dict(h_dep=0.02), dict(h_dep=0.02, preserve_w=0.5, dep_coll=1.0)):
            self.assertTrue(same(run(so.sd, **over), run(em, **over)), over)

    def test_without_deadline_ps_dep_does_nothing(self):
        self.assertTrue(same(run(so.sd, ps_dep=0.1), run(em)))

    def test_deadline_everywhere_equals_p_s0(self):
        dl = dict(h_dep=0.02, dep_coll=1.0, dep_post=1.0)
        for x in (0.1, 0.3):
            self.assertTrue(same(run(so.sd, ps_dep=x, **dl), run(em, p_s0=x, **dl)), x)

    def test_bad_odds_change_the_answer(self):
        a, b = run(so.sd, h_dep=0.02), run(so.sd, h_dep=0.02, ps_dep=0.05)
        self.assertFalse(same(a, b))


if __name__ == "__main__":
    unittest.main(verbosity=1)
