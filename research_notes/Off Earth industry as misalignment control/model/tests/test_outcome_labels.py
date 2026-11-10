"""Outcome definitions and share labels (issues #10, #26).

    python3 tests/test_outcome_labels.py      # reads the committed caches; no solving; about a minute

Unit tests for outcomes.py (the predicate agrees with robust_design.holds, the criteria nest, the label states
horizon, terminal rule, exit and rival treatment) and one report test: robust_report.report() run into a temporary
results folder labels every table, refuses an unlabelled one, and changes no number against the committed summary.
Regression only: this does not validate the model, and it does not show that the definition is the right one.
"""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

MODEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MODEL)
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np  # noqa: E402

import outcomes as oc  # noqa: E402
import robust_design as rd  # noqa: E402


def draws():
    # act0, att, riv: every combination the predicate distinguishes
    return dict(act0=np.array(["C", "P", "X", "S", "C", "C", "P", "C"]),
                att=np.array([0.0, 0.005, 0.0, 0.9, 0.5, 0.0099, 0.0, 0.0]),
                riv=np.array([0.0, 0.2, 0.0, 0.0, 0.1, 0.6, 0.005, 0.5]))


class Predicate(unittest.TestCase):
    def test_default_criterion_is_robust_design_holds(self):
        r = draws()
        np.testing.assert_array_equal(oc.criterion("holds", r), rd.holds(r))
        self.assertEqual(oc.DEFAULT_CRITERION, "holds")

    def test_holds_values(self):
        h = oc.criterion("holds", draws())
        self.assertEqual(h.tolist(), [True, True, False, False, False, True, True, True])

    def test_exit_after_year_zero_is_not_excluded(self):
        # holds looks only at the opening move and the strike probability; the exit probability plays no part
        r = dict(draws(), exit=np.ones(8))
        np.testing.assert_array_equal(oc.criterion("holds", r), oc.criterion("holds", draws()))

    def test_criteria_nest_and_differ(self):
        r = draws()
        h, u, a = (oc.criterion(k, r) for k in ("holds", "rival_unlikely", "rival_adverse"))
        self.assertTrue(np.all(~u | h) and np.all(~a | u))
        self.assertEqual(u.tolist(), [True, True, False, False, False, False, True, False])     # P(rival) < 0.5
        self.assertEqual(a.tolist(), [True, False, False, False, False, False, True, False])    # P(rival) < strike_tol
        self.assertEqual(oc.RANGE_CRITERIA, ("rival_adverse", "holds"))

    def test_thresholds(self):
        self.assertEqual(oc.strike_tol(), rd.STRIKE_TOL)
        self.assertEqual(oc.RIVAL_LIKELY, 0.5)

    def test_decompose_classes_are_disjoint_and_cover(self):
        d = oc.decompose(draws())
        total = d["strike_now"].astype(int) + d["later_strike"] + d["holds"] + d["other"]
        self.assertTrue(np.all(total == 1))
        self.assertEqual(d["strike_now"].tolist(), [False, False, False, True, False, False, False, False])
        self.assertEqual(d["later_strike"].tolist(), [False, False, False, False, True, False, False, False])
        self.assertTrue(np.all((d["unresolved"] >= 0) & (d["unresolved"] <= 1)))

    def test_wilson(self):
        lo, hi = oc.wilson95(0, 192)
        self.assertEqual(lo, 0.0)
        self.assertTrue(0 < hi < 0.03)
        lo, hi = oc.wilson95(96, 192)
        self.assertAlmostEqual((lo + hi) / 2, 0.5, places=3)


class Words(unittest.TestCase):
    """The label must say, in words, what a reader needs; a rewording that drops one fails here."""

    def check(self, text):
        for needle in ("cooperate or police", "P(strike or harvest within 300 years) < 0.01",
                       "does not exclude the AI exiting after year 0", "T_H = 300 years", "'peace'",
                       "not a calibrated probability", "P(rival) < 0.5", "indefinite stability"):
            self.assertIn(needle, text)
        self.assertIn("count as holding whatever P(rival) is", text)

    def test_label_line(self):
        line = oc.label_line("A", oc.box_sampling("full"))
        self.check(line)
        self.assertTrue(line.startswith(oc.LABEL_LINE_PREFIX + " A."))
        self.assertIn("Rival AI: a rival born before any strike ends the game and is not a strike", line)

    def test_definition_section(self):
        sec = oc.definition_section()
        self.check(sec)
        for k in oc.CRITERIA:
            self.assertIn(f"`{k}`", sec)
        self.assertIn("not modelled", sec)           # rival continuation
        self.assertIn("never 'stable indefinitely'", sec)

    def test_metadata(self):
        m = oc.outcome_metadata(dict(T_H=300))
        self.assertEqual(m["horizon_years"], 300)
        self.assertEqual(m["terminal_rule"]["name"], oc.solver_default_terminal())
        self.assertEqual(m["thresholds"], dict(strike_tol=rd.STRIKE_TOL, rival_likely=0.5))
        self.assertEqual(set(m["alternative_criteria"]), {"rival_unlikely", "rival_adverse"})
        json.dumps(m)

    def test_share_label_shape(self):
        lab = oc.share_label(oc.box_sampling("r0.1"), [("x: holds", 3, 64)])
        for k in ("interpretation", "sampling_measure", "structural_assumptions", "horizon", "predicate",
                  "numerical_uncertainty", "uncertainty_types"):
            self.assertIn(k, lab)
        self.assertEqual(set(lab["uncertainty_types"]), {"random_outcome", "parameter", "model_form", "normative"})
        self.assertEqual(lab["numerical_uncertainty"][0]["interval"], oc.wilson95(3, 64))
        self.assertIn("radius box r0.1", oc.box_sampling("r0.1"))
        with self.assertRaises(KeyError):
            oc.box_sampling("nonsense")

    def test_missing_labels_detects_an_unlabelled_table(self):
        good = "# t\n\n## Outcome definition\n\ntext\n\n## A. x\n\n" + oc.label_line("A", "s") + "\n\n| a |\n"
        self.assertEqual(oc.missing_labels(good), [])
        bad = good + "\n## B. y\n\n| b |\n"
        self.assertEqual(oc.missing_labels(bad), ["B. y"])


TREE = re.compile(r"^\|(---|   )")


def rows(md):
    """Table rows of a tables file, as a multiset, without decision-tree text and label lines."""
    out = []
    for ln in md.splitlines():
        if ln.startswith("|") and not (TREE.match(ln) and set(ln) - set("|-")):
            out.append(ln)
    return sorted(out)


class ReportLabels(unittest.TestCase):
    """report() into a temporary results folder: every table labelled, no number changed."""

    @classmethod
    def setUpClass(cls):
        import matplotlib
        matplotlib.use("Agg")
        import robust_report as rr
        cls.rr, cls.tmp = rr, tempfile.mkdtemp()
        cls.keep = (rd.RES, rr.savefig, list(rr.TABLES), dict(rr.OUT))
        for name in ("robust_erosion.json", "robust_best.json"):          # the report's other inputs
            if os.path.exists(os.path.join(rd.RES, name)):
                shutil.copy(os.path.join(rd.RES, name), cls.tmp)
        rd.RES = cls.tmp
        rr.savefig = lambda fig, name: rr.plt.close(fig)
        rr.TABLES.clear()
        rr.OUT.clear()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rr.report()
        with open(os.path.join(cls.tmp, "robust_design_tables.md"), encoding="utf-8") as f:
            cls.md = f.read()
        with open(os.path.join(cls.tmp, "robust_design_summary.json"), encoding="utf-8") as f:
            cls.out = json.load(f)

    @classmethod
    def tearDownClass(cls):
        rd.RES, cls.rr.savefig = cls.keep[0], cls.keep[1]
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_every_table_is_labelled(self):
        self.assertEqual(oc.missing_labels(self.md), [])
        sections = [s for s in self.md.split("\n## ")[1:] if not s.startswith("Outcome definition")]
        self.assertGreater(len(sections), 10)
        for s in sections:
            self.assertEqual(s.count(oc.LABEL_LINE_PREFIX), 1, s.splitlines()[0])
        ids = re.findall(r"\*\*Outcome label (.+?)\.\*\*", self.md)
        self.assertEqual(sorted(ids), sorted(self.out["outcome_labels"]))

    def test_label_text_on_the_page(self):
        for ln in (l for l in self.md.splitlines() if l.startswith(oc.LABEL_LINE_PREFIX)):
            for needle in ("calibrated probability", "does not exclude the AI exiting after year 0", "T_H = 300",
                           "'peace'", "P(rival) < 0.5", "indefinite stability"):
                self.assertIn(needle, ln)

    def test_summary_label_fields(self):
        for k, lab in self.out["outcome_labels"].items():
            self.assertIn("calibrated", lab["interpretation"], k)
            self.assertTrue(lab["numerical_uncertainty"], k)
            for u in lab["numerical_uncertainty"]:
                self.assertLessEqual(u["interval"][0], u["k"] / u["n"] + 1e-9, k)
                self.assertGreaterEqual(u["interval"][1], u["k"] / u["n"] - 1e-9, k)
        self.assertEqual(self.out["outcome_definition"]["horizon_years"], 300)

    def test_report_refuses_an_unlabelled_table(self):
        rr = self.rr
        saved = list(rr.TABLES)
        try:
            rr.TABLES.append("## Z. unlabelled\n\n| a |\n")
            text = "# x\n\n" + oc.definition_section() + "\n" + "\n".join(rr.TABLES)
            self.assertEqual(oc.missing_labels(text), ["Z. unlabelled"])
        finally:
            rr.TABLES[:] = saved

    def test_no_number_changed_against_the_committed_summary(self):
        path = os.path.join(MODEL, "results", "robust_design_summary.json")
        with open(path, encoding="utf-8") as f:
            ref = json.load(f)
        skip = {"outcome_labels", "outcome_definition"}
        for k, v in ref.items():
            if k in skip:
                continue
            self.assertIn(k, self.out)
            norm = (lambda x: sorted(json.dumps(i, sort_keys=True) for i in x)) if isinstance(v, list) else \
                   (lambda x: json.dumps(x, sort_keys=True))
            self.assertEqual(norm(self.out[k]), norm(v), f"{k}: a number changed (row order may differ for ties)")

    def test_committed_table_rows_are_unchanged(self):
        with open(os.path.join(MODEL, "results", "robust_design_tables.md"), encoding="utf-8") as f:
            ref = f.read()
        self.assertEqual(rows(self.md), rows(ref))


if __name__ == "__main__":
    unittest.main(verbosity=1)
