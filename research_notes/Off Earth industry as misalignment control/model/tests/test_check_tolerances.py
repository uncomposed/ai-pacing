"""compare-checks judges --check's error measures by threshold, not by equality with the committed copy.

Run from anywhere:  python3 tests/test_check_tolerances.py   (no solving; under a second)
"""
import json
import os
import sys
import unittest

MODEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MODEL)
os.environ.setdefault("OMP_NUM_THREADS", "1")

import ci_sims  # noqa: E402
import robust_design as rd  # noqa: E402

MD = open(os.path.join(MODEL, "results", "robust_design_checks.md")).read()
JS = open(os.path.join(MODEL, "results", "robust_design_checks.json")).read()
REG = "Largest absolute difference over every reported number: 0."


def with_reg(md, js, value, printed):
    j = json.loads(js)
    j["reg_maxdiff"] = value
    return md.replace(REG, f"Largest absolute difference over every reported number: {printed}."), json.dumps(j)


class CompareChecks(unittest.TestCase):
    def test_reference_matches_itself(self):
        problems, _ = ci_sims.compare_check_outputs(MD, MD, JS, JS)
        self.assertEqual(problems, [])

    def test_rounding_noise_in_error_measure_passes(self):
        # run 40215844769: 1.1226575225009583e-12 on the runner against 0.0 committed
        md, js = with_reg(MD, JS, 1.1226575225009583e-12, "1.12e-12")
        problems, notes = ci_sims.compare_check_outputs(MD, md, JS, js)
        self.assertEqual(problems, [])
        self.assertTrue(any("reg_maxdiff" in n for n in notes))

    def test_regression_error_above_threshold_fails(self):
        md, js = with_reg(MD, JS, 2e-6, "2e-06")
        problems, _ = ci_sims.compare_check_outputs(MD, md, JS, js)
        self.assertTrue(any("reg_maxdiff" in p and "exceeds" in p for p in problems), problems)

    def test_broken_invariant_fails_even_if_reference_regenerated(self):
        md, js = with_reg(MD, JS, 2e-6, "2e-06")
        problems, _ = ci_sims.compare_check_outputs(md, md, js, js)
        self.assertTrue(any("exceeds" in p for p in problems), problems)

    def test_identity_error_above_threshold_fails(self):
        md = MD.replace("(largest relative difference 0)", "(largest relative difference 0.003)")
        self.assertNotEqual(md, MD)
        problems, _ = ci_sims.compare_check_outputs(md, md, JS, JS)
        self.assertTrue(any("identity_rotation" in p for p in problems), problems)
        md = MD.replace("changes nothing (0)", "changes nothing (1e-15)")
        self.assertNotEqual(md, MD)
        self.assertEqual(ci_sims.compare_check_outputs(MD, md, JS, JS)[0], [])

    def test_other_numbers_still_compared_with_reference(self):
        md = MD.replace("q* = 0.389", "q* = 0.390")
        self.assertNotEqual(md, MD)
        self.assertTrue(ci_sims.compare_check_outputs(MD, md, JS, JS)[0])
        j = json.loads(JS)
        j["q_star_cap"] += 1e-6
        self.assertTrue(ci_sims.compare_check_outputs(MD, MD, JS, json.dumps(j))[0])

    def test_missing_diagnostic_line_fails(self):
        md = MD.replace(REG, "")
        self.assertTrue(ci_sims.compare_check_outputs(MD, md, JS, JS)[0])


class CheckFailures(unittest.TestCase):
    def test_thresholds(self):
        self.assertEqual(rd.check_failures(dict(reg_maxdiff=1.1e-12, identity_rotation=0.0)), [])
        self.assertEqual(len(rd.check_failures(dict(reg_maxdiff=1e-8))), 1)
        self.assertEqual(len(rd.check_failures(dict(identity_size_erosion=float("nan")))), 1)


if __name__ == "__main__":
    unittest.main(verbosity=1)
