"""Gates fail on a broken invariant or a broken dock, whatever the committed reference files say (issue #7).

    python3 tests/test_gates.py        # no ensemble solving; a few seconds
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

MODEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MODEL)
sys.path.insert(0, os.path.join(MODEL, "docking"))
os.environ.setdefault("OMP_NUM_THREADS", "1")

import ci_sims  # noqa: E402
import equilibrium_model as em  # noqa: E402
import robust_design as rd  # noqa: E402

CHECKS_JSON = os.path.join(MODEL, "results", "robust_design_checks.json")
CHECKS_MD = os.path.join(MODEL, "results", "robust_design_checks.md")


class ClosedFormInvariants(unittest.TestCase):
    def setUp(self):
        # the committed copy: robust_design.py --check overwrites the working-tree files
        self.ref = json.loads(ci_sims._git("show", "HEAD:./results/robust_design_checks.json") or open(CHECKS_JSON).read())
        self.md = ci_sims._git("show", "HEAD:./results/robust_design_checks.md") or open(CHECKS_MD).read()

    def test_committed_output_satisfies_invariants(self):
        self.assertEqual(rd.invariant_failures(self.ref["rows"], self.ref["q_star_cap"]), [])

    def test_broken_invariant_fails_even_when_reference_is_regenerated(self):
        # A regression that makes the solver strike later than the closed form allows (q_er = 0.005: 165 -> 175),
        # and the reference files regenerated to match it, so golden-file equality passes.
        bad = json.loads(json.dumps(self.ref))
        bad["rows"][1][1] = 175
        md = self.md.replace("| q_er = 0.005 | 160 |", "| q_er = 0.005 | 175 |")
        self.assertNotEqual(md, self.md)
        problems, _ = ci_sims.compare_check_outputs(md, md, json.dumps(bad), json.dumps(bad))
        self.assertEqual(problems, [], "golden comparison alone accepts the regenerated reference")
        self.assertTrue(rd.invariant_failures(bad["rows"], bad["q_star_cap"]))

    def test_each_invariant(self):
        rows, qs = self.ref["rows"], self.ref["q_star_cap"]
        r = [list(x) for x in rows]
        r[5][2], r[5][3] = "12.0", "0.900"          # q_ea 0.04: solver strikes, closed form does not
        self.assertTrue(any("closed form says none" in x for x in rd.invariant_failures(r, qs)))
        self.assertTrue(any("threshold" in x for x in rd.invariant_failures(rows, 0.2)))   # threshold moves to 0.067
        self.assertTrue(any("q* =" in x for x in rd.invariant_failures(rows, 0.8)))


class ReplicationGate(unittest.TestCase):
    def setUp(self):
        import replication
        self.rep = replication
        replication.RESULTS.clear()

    def test_clark_identity_passes_and_breaks(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.rep.clark_checks(solver=False)
        self.assertTrue(all(r["ok"] for r in self.rep.RESULTS), [r for r in self.rep.RESULTS if not r["ok"]])
        self.rep.RESULTS.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.rep.self_test(), 0, "the self-test must see the broken dock fail")
        self.assertTrue(any(not r["ok"] for r in self.rep.RESULTS))
        self.assertTrue(abs(em.cap_strike_gap(em.baseline(), 1.5e9)) > 0)   # the real function is restored

    def test_printed_table_check_uses_pinned_values(self):
        # expectations live in replication.py, not docking/out: an altered expected value fails
        g, p, C, printed, dec = self.rep.SAK_TABLE1[2]
        import saklakov
        self.assertLessEqual(abs(saklakov.sak(g, p, C)[2] - printed), 0.5 * 10 ** -dec)
        self.assertGreater(abs(saklakov.sak(g, p, C)[2] - (printed + 0.1)), 0.5 * 10 ** -dec)

    def test_comparison_docks_are_not_labelled_replication(self):
        for k in ("powell", "potapov", "metzger"):
            self.assertIn("not a replication", self.rep.SOURCES[k]["kind"])


class Categories(unittest.TestCase):
    def test_empirical_is_never_pass(self):
        import model_gates as mg
        with tempfile.TemporaryDirectory() as d:
            mg.GATE_DIR = d
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(mg.main(["empirical"]), 0)
                with open(os.path.join(d, "empirical.json")) as f:
                    self.assertEqual(json.load(f)["status"], "not_established")
                self.assertEqual(mg.main(["report"]), 0)
            with self.assertRaises(SystemExit):        # software needs numerics' fresh outputs
                mg.main(["software"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
