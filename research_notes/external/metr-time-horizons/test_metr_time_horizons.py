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
import subprocess
import sys
import unittest

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import holdout as H  # noqa: E402
import horizon_fit as hf  # noqa: E402
import lock_forecast as LF  # noqa: E402
import permodel as PM  # noqa: E402

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


class PerModel(unittest.TestCase):
    """#56: the per-model holdout and its pre-declared B-COMPUTE."""

    @classmethod
    def setUpClass(cls):
        cls.rows = H.load_observations()
        cls.res = PM.compute_all()

    def test_protocol_is_the_declared_version(self):
        self.assertEqual(hashlib.sha256(PM.PROTOCOL.read_bytes()).hexdigest(), PM.PROTOCOL_SHA256)

    def test_protocol_was_committed_before_the_scoring_code(self):
        def git(*a):
            return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True)
        if git("cat-file", "-e", f"{PM.DECLARED_COMMIT}^{{commit}}").returncode != 0:
            self.skipTest("declaration commit not in this clone (shallow or squashed); the sha256 check still applies")
        rel = PM.PROTOCOL.relative_to(ROOT).as_posix()
        self.assertEqual(git("show", f"{PM.DECLARED_COMMIT}:{rel}").stdout.encode(), PM.PROTOCOL.read_bytes())
        for later in ("permodel.py", "results/permodel.json"):
            path = (HERE / later).relative_to(ROOT).as_posix()
            self.assertNotEqual(git("cat-file", "-e", f"{PM.DECLARED_COMMIT}:{path}").returncode, 0, later)

    def test_information_sets_exclude_target_and_later_values(self):
        for f in self.res["forecasts"]:
            c = dt.date.fromisoformat(f["cutoff"])
            srows = PM.suite_rows(self.rows, f["suite"], False)
            info = PM.information_set(srows, c, f["model_key"], "V-FIRST")
            self.assertNotIn(f["model_key"], info)
            self.assertTrue(all(r["_avail"] <= c for r in info.values()))
            self.assertEqual(f["by_resolution"]["V-FIRST"]["B-FLAT"]["point"], max(r[f["metric"]] for r in info.values()))
            self.assertTrue(all(i in {r["record_id"] for r in srows if r["_avail"] <= c} for i in f["inputs"]))

    def test_targets_follow_the_declared_rule(self):
        got = {(f["suite"], f["model_key"]) for f in self.res["forecasts"]}
        self.assertEqual(len([g for g in got if g[0] == "TH1.0"]), 15)
        self.assertEqual({k for s, k in got if s == "TH1.1"},
                         {"claude_opus_4_6_inspect", "gpt_5_3_codex", "gemini_3_1_pro", "gpt_5_4",
                          "claude_mythos_preview_early_inspect"})
        self.assertEqual(self.res["skipped"], [])

    def test_compute_baseline_definition(self):
        info = {"a": {"p50_min": 10.0, "_rel": dt.date(2025, 1, 1)}, "b": {"p50_min": 20.0, "_rel": dt.date(2025, 7, 1)}}
        self.assertAlmostEqual(PM.compute(info, "p50_min", dt.date(2025, 7, 1), 4.2)["point"], 20.0)
        one_year = PM.compute(info, "p50_min", dt.date(2025, 7, 1) + dt.timedelta(days=365.25), 4.2)["point"]
        self.assertAlmostEqual(one_year, 20.0 * 4.2 ** (365 / 365.25))
        self.assertEqual(float(PM.load_protocol()["baselines"]["B-COMPUTE"]["g"]), 4.2)

    def test_committed_results_reproduce(self):
        self.assertTrue(H.close(json.loads((HERE / "results/permodel.json").read_text()), self.res))
        self.assertEqual((HERE / "results/permodel.md").read_text(), PM.to_markdown(self.res))

    def test_declared_verdicts_are_preserved(self):
        self.assertEqual(self.res["verdict"]["B-COMPUTE"], "not established")
        self.assertEqual(self.res["verdict"]["B-LOGLINEAR vs B-FLAT"], "not established")

    def test_registry_matches(self):
        reg = {f["id"]: f for f in H.ET.load_yaml(ROOT / "evidence/protocol.yaml")["forecasts"] if f["id"].startswith("FC-METR-PM-")}
        want = {}
        for f in self.res["forecasts"]:
            want[f"FC-METR-PM-{f['suite'].replace('.', '')}-{f['model_key'].upper().replace('_', '-')}"] = f
        self.assertEqual(set(reg), set(want))
        for k, f in want.items():
            self.assertEqual(reg[k]["information_cutoff"], f["cutoff"])
            self.assertEqual(reg[k]["inputs"], f["inputs"] + [PM.COMPUTE_RECORD])
            self.assertEqual(reg[k]["resolution"]["record"], f["resolution_record"])
            self.assertIn("B-COMPUTE", reg[k]["baselines"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
