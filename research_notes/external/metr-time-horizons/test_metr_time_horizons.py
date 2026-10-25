"""Fast checks for the METR time-horizon suite (#12). No network; numpy and the committed files only.

    python3 research_notes/external/metr-time-horizons/test_metr_time_horizons.py      (run by make check)
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import pathlib
import sys
import unittest

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import holdout as H  # noqa: E402
import horizon_fit as hf  # noqa: E402
import lock_forecast as LF  # noqa: E402
import suite_mapping as SM  # noqa: E402

ROOT = HERE.parents[2]
OBS = list(csv.DictReader((HERE / "data/observations.csv").open(encoding="utf-8")))


class Fitter(unittest.TestCase):
    def test_recovers_parameters_on_large_synthetic_sample(self):
        rng = np.random.default_rng(0)
        x = rng.uniform(-2, 10, 200_000)
        a, b = 3.0, -0.6
        y = (rng.random(x.size) < 1 / (1 + np.exp(-(a + b * x)))).astype(float)
        f = hf.fit_logistic(x, y, np.full(x.size, 1 / x.size), 1e-9)
        self.assertAlmostEqual(f.intercept, a, delta=0.03)
        self.assertAlmostEqual(f.slope, b, delta=0.01)
        self.assertAlmostEqual(f.horizon(0.5), 2 ** (-a / b), delta=0.05 * 2 ** (-a / b))

    def test_horizon_formula_and_ordering(self):
        f = hf.Fit(intercept=2.0, slope=-0.5, iterations=1, grad_norm=0.0)
        self.assertAlmostEqual(f.horizon(0.5), 2 ** 4)
        self.assertAlmostEqual(math.log2(f.horizon(0.8)), (math.log(4) - 2.0) / -0.5)
        self.assertLess(f.horizon(0.8), f.horizon(0.5))  # higher reliability, shorter horizon

    def test_gradient_zero_at_solution_with_regularization(self):
        rng = np.random.default_rng(1)
        x = rng.uniform(0, 8, 300)
        y = (rng.random(300) < 1 / (1 + np.exp(-(2 - 0.5 * x)))).astype(float)
        w = rng.uniform(0.5, 1.5, 300)
        w /= w.sum()
        c = 1 / 0.1
        f = hf.fit_logistic(x, y, w, 0.1)
        p = 1 / (1 + np.exp(-(f.intercept + f.slope * x)))
        g0 = c * np.sum(w * (p - y))
        g1 = c * np.sum(w * (p - y) * x) + f.slope  # slope is penalized, intercept is not
        self.assertLess(abs(g0), 1e-6)
        self.assertLess(abs(g1), 1e-6)

    def test_fractional_scores_equal_weighted_split(self):
        x = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        y = np.array([1.0, 0.7, 0.5, 0.2, 0.0])
        w = np.full(5, 0.2)
        f1 = hf.fit_logistic(x, y, w, 1e-3)
        xs = np.concatenate([x, x])
        ys = np.concatenate([np.ones(5), np.zeros(5)])
        ws = np.concatenate([w * y, w * (1 - y)])
        f2 = hf.fit_logistic(xs, ys, ws, 1e-3)
        self.assertAlmostEqual(f1.slope, f2.slope, places=6)
        self.assertAlmostEqual(f1.intercept, f2.intercept, places=6)

    def test_bootstrap_is_seeded_and_hierarchical(self):
        runs = hf.Runs(agent=np.array(["A"] * 8 + ["B"] * 8, dtype=object),
                       task_family=np.array(["f1", "f1", "f2", "f2"] * 4, dtype=object),
                       task_id=np.array(["t1", "t2", "t3", "t4"] * 4, dtype=object),
                       run_id=np.array([f"r{i}" for i in range(16)], dtype=object),
                       human_minutes=np.array([1, 4, 16, 64] * 4, float),
                       score=np.array([1, 1, 0, 0, 1, 0, 1, 0] * 2, float),
                       weight=np.full(16, 1 / 8))
        i1 = hf.bootstrap_indices(runs, np.random.default_rng(42))
        i2 = hf.bootstrap_indices(runs, np.random.default_rng(42))
        self.assertTrue(np.array_equal(i1, i2))
        # Families are drawn first: every drawn index belongs to a drawn family, and both agents share the draw.
        fams = set(runs.task_family[i1])
        for a in ("A", "B"):
            self.assertEqual(set(runs.task_family[i1][runs.agent[i1] == a]), fams)


class ObservationTable(unittest.TestCase):
    def test_dates_are_kept_apart_and_never_leak(self):
        for r in OBS:
            # METR published GPT-5's TH1.0 value on 2025-08-06, a day before the release date it lists
            # (pre-release access; dates are not time-zoned). Allow that, nothing more.
            lag = (dt.date.fromisoformat(r["available"]) - dt.date.fromisoformat(r["model_release_date"])).days
            self.assertGreaterEqual(lag, -1, r)
            if r["runs_end"]:
                self.assertLessEqual(r["runs_start"], r["runs_end"], r)
                # A value can't be public before the runs that produced it.
                self.assertLessEqual(r["runs_end"], r["available"], r)

    def test_units_and_flags(self):
        for r in OBS:
            p50, p80 = float(r["p50_min"]), float(r["p80_min"])
            self.assertGreater(p50, 0)
            self.assertLess(p80, p50, r)  # 80% horizon below 50% horizon for a decreasing curve
            self.assertEqual(int(r["saturated"]), int(p50 > 960), r)
            self.assertIn(r["suite"], ("TH1.0", "TH1.1"))

    def test_every_row_has_an_evidence_record_with_consistent_dates(self):
        recs = {x["id"]: x for x in H.ET.load_records()["records"]}
        for rid in {r["record_id"] for r in OBS}:
            self.assertIn(rid, recs)
            rec = recs[rid]
            rows = [r for r in OBS if r["record_id"] == rid]
            self.assertTrue(all(r["available"] == rec["availability_date"] for r in rows), rid)
            ends = [r["runs_end"] for r in rows if r["runs_end"]]
            if ends:
                self.assertEqual(max(ends), rec["observation_date"]["end"], rid)

    def test_th11_published_values_match_metr_file_extract(self):
        # Spot values copied from metr.org/assets/benchmark_results_1_1.yaml (sha256 in sources.sha256).
        want = {"claude_opus_4_6_inspect": 718.80683, "gpt_5_2": 352.249302, "claude_mythos_preview_early_inspect": 1044.780145}
        got = {r["model_key"]: float(r["p50_min"]) for r in OBS if r["record_id"].startswith("EV-METR-TH11") and
               r["value_source"].startswith("published")}
        for k, v in want.items():
            self.assertEqual(got[k], v)


class Holdout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = H.load_observations()
        cls.res = H.compute()

    def test_information_sets_use_only_available_values(self):
        for f in self.res["forecasts"]:
            c = dt.date.fromisoformat(f["cutoff"])
            info = H.info_set(self.rows, f["suite"], c)
            self.assertTrue(all(r["_avail"] <= c for r in info.values()))
            self.assertEqual(f["B-FLAT"]["point"], H.frontier(info, f["metric"]))

    def test_revision_replaces_value_only_after_its_date(self):
        before = H.info_set(self.rows, "TH1.1", dt.date(2026, 3, 2))
        after = H.info_set(self.rows, "TH1.1", dt.date(2026, 3, 3))
        self.assertEqual(before["gpt_5_2"]["value_source"], "refit:th11_2026-02-12")
        self.assertTrue(after["gpt_5_2"]["value_source"].startswith("published"))
        self.assertNotIn("claude_opus_4_6_inspect", before)

    def test_committed_results_reproduce(self):
        committed = json.loads((HERE / "results/holdout.json").read_text())
        self.assertTrue(H.close(committed, self.res))
        self.assertEqual((HERE / "results/holdout.md").read_text(), H.to_markdown(self.res))

    def test_declared_verdict_is_preserved(self):
        self.assertEqual(self.res["verdict"]["statement"], "not established")
        self.assertEqual(self.res["label"], "retrospective")

    def test_registry_matches_holdout(self):
        reg = {f["id"]: f for f in H.ET.load_yaml(ROOT / "evidence/protocol.yaml")["forecasts"]}
        for f in self.res["forecasts"]:
            m = "P50" if f["metric"] == "p50_min" else "P80"
            e = reg[f"FC-METR-{f['suite'].replace('.', '')}-{m}-{f['cutoff']}"]
            self.assertEqual(e["label"], "retrospective")
            self.assertEqual(e["information_cutoff"], f["cutoff"])
            self.assertEqual(sorted(e["inputs"]), f["inputs"])

    def test_t_quantile(self):
        self.assertAlmostEqual(H.t_ppf(0.9, 1), 3.0777, places=3)
        self.assertAlmostEqual(H.t_ppf(0.9, 10), 1.3722, places=3)


class LockedForecast(unittest.TestCase):
    def test_hash_and_reproducibility(self):
        text = LF.OUT.read_text()
        digest = hashlib.sha256(text.encode()).hexdigest()
        self.assertIn(f"{digest}  {LF.OUT.name}", (HERE / "forecasts/SHA256SUMS").read_text())
        self.assertTrue(H.close(json.loads(text), LF.build()))

    def test_registered_as_locked_with_commit(self):
        reg = [f for f in H.ET.load_yaml(ROOT / "evidence/protocol.yaml")["forecasts"] if "LOCK" in f["id"]]
        self.assertEqual(len(reg), 4)
        for f in reg:
            self.assertEqual(f["label"], "locked")
            self.assertRegex(f["lock_commit"], r"^[0-9a-f]{40}$")
            self.assertIsNone(f["resolution"])


class SuiteMapping(unittest.TestCase):
    """TH1.0 -> TH1.1 mapping (#57): declared in suite_mapping.yaml, computed by suite_mapping.py."""

    @classmethod
    def setUpClass(cls):
        cls.res = SM.compute()
        cls.committed = json.loads((HERE / "results/suite_mapping.json").read_text())

    def test_committed_results_reproduce(self):
        self.assertTrue(H.close(self.committed, self.res))
        self.assertEqual((HERE / "results/suite_mapping.md").read_text(), SM.to_markdown(self.res))

    def test_declaration_is_what_was_run(self):
        d = SM.DECL
        self.assertEqual(d["interval_level"], 0.9)
        self.assertEqual(d["bootstrap"], {"over": "models", "n": 10000, "seed": 57})
        self.assertEqual([c["id"] for c in d["criteria"]], ["C1", "C2", "C3", "C4"])
        self.assertEqual(len(d["pairs"]), 16)
        self.assertEqual(sum(p["scaffold_change"] for p in d["pairs"]), 14)
        self.assertEqual(self.res["n_fit"], 14)

    def test_pairs_are_published_post_correction_values_on_both_suites(self):
        by = {(r["record_id"], r["model_key"]): r for r in OBS}
        for p in SM.DECL["pairs"]:
            a, b = by[(SM.DECL["rows"]["th10"], p["th10"])], by[(SM.DECL["rows"]["th11"], p["th11"])]
            self.assertEqual((a["suite"], b["suite"]), ("TH1.0", "TH1.1"))
            self.assertTrue(a["value_source"].startswith("published") and b["value_source"].startswith("published"))
            self.assertEqual((a["regularization"], b["regularization"]), ("1e-05", "1e-05"))
            self.assertTrue(a["p50_ci_low"] and b["p50_ci_low"])
        # Agents the TH1.1 file only repeats from TH1.0 (identical estimates and intervals on both sides, checked
        # against the two published files) are not pairs.
        self.assertFalse(set(SM.DECL["excluded_stitched"]) & {p["th10"] for p in SM.DECL["pairs"]})

    def test_ols_and_prediction_interval_on_exact_and_known_data(self):
        x = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        f = SM.ols(x, 2.0 + 0.5 * x)
        self.assertAlmostEqual(f["a"], 2.0)
        self.assertAlmostEqual(f["b"], 0.5)
        self.assertAlmostEqual(f["s"], 0.0, places=12)
        # Hand-computed: y = (1, 3, 2, 5, 4): Sxy 8, Sxx 10, b = 0.8, a = 1.4, residual sum of squares 3.6, s = sqrt(1.2)
        g = SM.ols(x, np.array([1.0, 3.0, 2.0, 5.0, 4.0]))
        self.assertAlmostEqual(g["b"], 0.8)
        self.assertAlmostEqual(g["a"], 1.4)
        self.assertAlmostEqual(g["s"], math.sqrt(1.2))
        pr = SM.predict(g, 2.0, 0.9)  # at the mean of x the leverage is 1/n
        half = SM.tq(0.95, 3) * g["s"] * math.sqrt(1 + 1 / 5)
        self.assertAlmostEqual(pr["pi"][1] - pr["ln"], half)
        self.assertAlmostEqual(SM.tq(0.95, 12), 1.7823, places=3)

    def test_declared_criteria_outcomes_are_preserved(self):
        # Recorded as found, including the failure: p80 C3 (GPT-4 0314 lies above its interval).
        met = {m: r["criteria_met"] for m, r in self.res["metrics"].items()}
        self.assertEqual(met["p50"], {"C1": True, "C2": True, "C3": True, "C4": True})
        self.assertEqual(met["p80"], {"C1": True, "C2": True, "C3": False, "C4": True})
        ho = {h["model"]: h for h in self.res["metrics"]["p80"]["held_out"]}
        self.assertFalse(ho["gpt_4"]["inside"])
        self.assertTrue(ho["o1_preview"]["inside"])

    def test_mapping_is_not_a_constant_ratio_and_beats_baselines(self):
        for m, r in self.res["metrics"].items():
            self.assertGreater(r["fit"]["b"], 1.2, m)
            self.assertLess(r["fit"]["b"], 1.5, m)
            self.assertGreater(r["bootstrap"]["b_ci95"][0], 1.0, m)
            mae = r["loo"]["mean_abs_error_ln"]
            self.assertLess(mae["mapping"], 0.6 * mae["identity"], m)
            self.assertLess(mae["mapping"], 0.6 * mae["const_ratio"], m)

    def test_support_limits_are_flagged(self):
        for m, r in self.res["metrics"].items():
            lo, hi = r["support_h10"]
            for t in r["table"]:
                self.assertEqual(t["in_support"], lo <= t["h10"] <= hi, (m, t["h10"]))
        self.assertFalse(any(t["in_support"] for t in self.res["metrics"]["p50"]["table"] if t["h10"] in (5.0, 250.0)))
        # prediction intervals are wider than the interval of the mean line, everywhere
        for r in self.res["metrics"].values():
            for t in r["table"]:
                self.assertLess(t["pi"][0], t["ci"][0])
                self.assertGreater(t["pi"][1], t["ci"][1])

    def test_residual_scatter_is_below_independent_published_error(self):
        # The published intervals, taken as independent errors on each side, would scatter the difference by far
        # more than the residual about the line: so the two suites' errors are positively correlated.
        for m, r in self.res["metrics"].items():
            self.assertLess(r["fit"]["s"], 0.6 * r["published_interval_se_ln"]["rms_of_independent_difference"], m)

    def test_leave_one_out_coverage_counts_match_rows(self):
        for r in self.res["metrics"].values():
            self.assertEqual(r["loo"]["covered"], sum(x["covered"] for x in r["loo"]["rows"]))
            self.assertEqual(r["loo"]["n"], 14)


class Th10Stopping(unittest.TestCase):
    """The four TH1.0 agents above the 1e-3 tolerance are scikit-learn's stopping point (#57)."""

    @classmethod
    def setUpClass(cls):
        cls.d = json.loads((HERE / "results/th10_stopping.json").read_text())
        cls.rep = json.loads((HERE / "results/reproduction.json").read_text())

    def test_tolerance_not_widened(self):
        self.assertIn("TOL_REL = 1e-3", (HERE / "reproduce.py").read_text())
        self.assertEqual(self.d["tolerance_rel"], 1e-3)

    def test_the_same_four_agents_exceed_in_both_files(self):
        four = ["Claude 4 Opus", "Claude 4 Sonnet", "GPT-2", "gpt-3.5-turbo-instruct"]
        self.assertEqual(self.d["exceeding"], four)
        self.assertEqual(len(self.d["agents"]), 33)
        over = sorted(r["alias"] for r in self.rep["th10_points"]
                      if max(abs(r[n]["rel_diff"]) for n in ("p50", "p80")) > 1e-3)
        self.assertEqual(over, four)
        worst = max(max(abs(r[n]["rel_diff"]) for n in ("p50", "p80")) for r in self.rep["th10_points"])
        self.assertAlmostEqual(worst, 1.7e-3, delta=0.05e-3)

    def test_published_values_are_sklearn_default_stopping_points(self):
        for a, r in self.d["agents"].items():
            self.assertLess(r["max_abs_rel_to_published"]["sklearn_default"], 1e-5, a)  # published = default lbfgs (6 decimals)
            # a tightly converged scikit-learn fit agrees with the independent Newton fit, not with the published value
            for k in ("sklearn_tight_lbfgs", "sklearn_tight_newton_cholesky"):
                self.assertLess(abs(r[k]["p50"] / r["ours"]["p50"] - 1), 2e-6, (a, k))
                self.assertLess(abs(r[k]["p80"] / r["ours"]["p80"] - 1), 2e-6, (a, k))

    def test_independent_fit_has_the_lower_objective_for_the_four(self):
        for a in self.d["exceeding"]:
            o = self.d["agents"][a]["objective"]
            self.assertGreater(o["sklearn_default"] - o["ours"], 1e-3, a)
            self.assertLess(abs(o["sklearn_tight_lbfgs"] - o["ours"]), 1e-8 * o["ours"], a)
            g = self.d["agents"][a]["grad_norm"]
            self.assertLess(g["sklearn_default"], 1e-4, a)       # stopped at its tolerance
            self.assertLess(g["ours"], 1e-8, a)                  # at the optimum
            self.assertEqual(self.d["agents"][a]["sklearn_default_warnings"], [], a)  # no convergence warning

    def test_no_agent_is_above_tolerance_except_the_four(self):
        for a, r in self.d["agents"].items():
            self.assertEqual(r["exceeds_tolerance_ours"], a in self.d["exceeding"], a)


class UpstreamProvenance(unittest.TestCase):
    """What the public repository says about the run behind the published intervals (#57)."""

    @classmethod
    def setUpClass(cls):
        cls.d = json.loads((HERE / "results/dvc_lock_check.json").read_text())

    def test_every_public_input_matches_the_md5_in_dvc_lock(self):
        self.assertTrue(self.d["all_inputs_match"])
        n = 0
        for st in self.d["stages"].values():
            for c in st["inputs"]:
                if "match" in c:
                    self.assertTrue(c["match"], c["path"])
                    n += 1
        self.assertEqual(n, 11)

    def test_recorded_run_parameters(self):
        text = " ".join(self.d["stages"]["wrangle_bootstrap_logistic@headline"]["params"])
        for want in ("n_bootstrap: 1000", "weighting: invsqrt_task_weight", "regularization: 1e-05", "categories: ftr", "confidence_level: 0.95"):
            self.assertIn(want, text)
        self.assertIn("--n-bootstrap 1000", self.d["stages"]["wrangle_bootstrap_logistic@headline"]["cmd"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
