"""Fast checks for the AI Futures Model replication (no network, no upstream checkout).

They check that the committed summaries are internally consistent, pinned to one upstream
commit, and that their pass/fail flags follow from the recorded numbers and the declared
tolerances. They do not re-run the model; the workflow aifm.yml does that.
"""

import json
import math
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import aifm_summary as S  # noqa: E402

RESULTS = HERE / "results"
TOL = json.loads((HERE / "tolerances.json").read_text())


def load_yaml(path):
    try:
        import yaml

        return yaml.safe_load(path.read_text())
    except ImportError:
        out = subprocess.run(["ruby", "-ryaml", "-rjson", "-e", "puts JSON.dump(YAML.safe_load(File.read(ARGV[0])))", str(path)],
                             capture_output=True, text=True, check=True)
        return json.loads(out.stdout)


def result(name):
    return json.loads((RESULTS / name).read_text())


def pinned_commit():
    return load_yaml(HERE / "SOURCES.yaml")["upstream"]["commit"]


class TestPins(unittest.TestCase):
    def test_fetch_script_matches_sources(self):
        script = (HERE / "fetch_upstream.sh").read_text()
        m = re.search(r'^AIFM_COMMIT="([0-9a-f]{40})"', script, re.M)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), pinned_commit())

    def test_every_result_is_from_the_pinned_clean_commit(self):
        files = sorted(RESULTS.glob("*.json"))
        self.assertTrue(files)
        for f in files:
            prov = json.loads(f.read_text())["provenance"]
            self.assertEqual(prov["upstream_commit"], pinned_commit(), f.name)
            self.assertFalse(prov["upstream_tracked_files_modified"], f.name)

    def test_upstream_is_not_vendored(self):
        tracked = subprocess.run(["git", "ls-files", ".upstream"], capture_output=True, text=True, cwd=HERE)
        self.assertEqual(tracked.stdout.strip(), "", "upstream code is tracked; it must be fetched, not vendored")


class TestReference(unittest.TestCase):
    def setUp(self):
        self.r = result("reference_trajectory.json")

    def test_declared_tolerance_is_the_committed_one(self):
        self.assertEqual(self.r["tolerance"], TOL["reference_trajectory"])

    def test_flags_follow_from_numbers(self):
        for k, v in self.r["scalars"].items():
            self.assertEqual(v["pass"], abs(v["ours"] - v["golden"]) <= v["tolerance"], k)
            self.assertAlmostEqual(v["abs_diff"], abs(v["ours"] - v["golden"]), places=12)
        tol = self.r["tolerance"]
        for k, v in self.r["series"].items():
            if not v.get("compared", True):
                continue
            # allclose implies max_abs_diff <= atol + rtol * max|expected|; a fail with tiny diffs would be inconsistent
            if v["max_rel_diff"] <= tol["series_rtol"]:
                self.assertTrue(v["pass"], k)
        overall = all(v.get("pass", True) for v in self.r["series"].values()) and all(v["pass"] for v in self.r["scalars"].values())
        self.assertEqual(self.r["pass"], overall)

    def test_reference_reproduces(self):
        self.assertTrue(self.r["pass"], "the committed reference run did not reproduce the golden files")

    def test_milestone_order_on_progress(self):
        ms = self.r["milestones"]
        self.assertLess(ms["AC"]["time"], ms["SAR-level-experiment-selection-skill"]["time"])
        self.assertLess(ms["TED-AI"]["time"], ms["ASI"]["time"])


class TestFeedbackOff(unittest.TestCase):
    def setUp(self):
        self.r = result("feedback_off.json")

    def test_refit_hits_target_rate(self):
        rate = self.r["software_progress_rate_2024"]
        self.assertAlmostEqual(rate["off_refit"], rate["target"], places=9)

    def test_feedback_off_is_never_earlier(self):
        # AI feedback only adds research effort, so switching it off cannot bring a capability level earlier.
        for name, row in self.r["milestone_dates"].items():
            if row["feedback_on"] is None:
                continue
            for key in ("off_same_calibration", "off_refit"):
                if row[key] is not None:
                    self.assertGreaterEqual(row[key], row["feedback_on"] - 1e-6, f"{name} {key}")

    def test_paths_agree_before_ai_matters(self):
        p = self.r["progress_path"]
        i = p["year"].index(2020.0)
        self.assertAlmostEqual(p["feedback_on"][i], p["off_same_calibration"][i], delta=0.05)


class TestAnchors(unittest.TestCase):
    def test_all_modes_present(self):
        a = result("anchors.json")["anchors"]
        self.assertEqual(set(a), {"uplift-solved", "time-horizon", "revenue", "eci"})
        for mode, v in a.items():
            self.assertIsNotNone(v["milestone_times"]["AC"], mode)


class TestSeeded(unittest.TestCase):
    def setUp(self):
        self.files = sorted(RESULTS.glob("seeded_*.json"))

    def test_present(self):
        self.assertTrue(self.files, "no seeded milestone distribution committed")

    def test_quantiles_ordered_and_counts_consistent(self):
        for f in self.files:
            r = json.loads(f.read_text())
            n = r["preset"]["num_samples"]
            for name, s in r["summary"]["overall"].items():
                self.assertLessEqual(s["p10"], s["p50"], f"{f.name} {name}")
                self.assertLessEqual(s["p50"], s["p90"], f"{f.name} {name}")
                self.assertEqual(s["num_achieved"] + s["num_not_achieved"], s["total_rollouts"])
                self.assertEqual(s["total_rollouts"] + r["failed_rollouts"], n)

    def test_comparison_flags_follow_from_numbers(self):
        for f in self.files:
            r = json.loads(f.read_text())
            if "comparison" not in r:
                continue
            c = r["comparison"]
            self.assertEqual(c["tolerance"], TOL["seeded_distribution"])
            for row in c["rows"]:
                self.assertEqual(row["pass"], abs(row["diff"]) <= row["tolerance"], row)
                self.assertAlmostEqual(row["diff"], row["ours"] - row["published"], places=9)
            self.assertEqual(c["n_fail"], sum(not row["pass"] for row in c["rows"]))
            self.assertEqual(c["pass"], c["n_fail"] == 0)


class TestSummaryFunctions(unittest.TestCase):
    def rec(self, mode, **times):
        ms = {m: None for m in S.OVERLAY_MILESTONES}
        ms.update({k.replace("_", "-"): v for k, v in times.items()})
        return {"sample_id": 0, "ac_anchor_mode": mode, "sim_end": 2200.0, "milestones": ms}

    def test_unachieved_are_placed_at_sim_end(self):
        recs = [self.rec("revenue", AC=2027.0), self.rec("revenue", AC=2029.0), self.rec("revenue")]
        s = S.milestone_stats(recs, "AC")
        self.assertEqual((s["num_achieved"], s["num_not_achieved"]), (2, 1))
        self.assertAlmostEqual(s["p50"], 2029.0)
        self.assertAlmostEqual(s["p90"], 2029.0 + 0.8 * (2200.0 - 2029.0))
        self.assertAlmostEqual(s["achievement_rate_pct"], 200.0 / 3)

    def test_crossing_time(self):
        self.assertAlmostEqual(S.crossing_time([0, 1, 2], [0.0, 1.0, 3.0], 2.0), 1.5)
        self.assertIsNone(S.crossing_time([0, 1], [0.0, 1.0], 5.0))
        self.assertEqual(S.crossing_time([0, 1], [2.0, 3.0], 1.0), 0.0)

    def test_compare_rejects_shift_beyond_sampling_noise(self):
        ours = {"AC": {"total_rollouts": 1000, "achievement_rate_pct": 99.0, "p10": 2027.0, "p50": 2028.0, "p90": 2031.0,
                       "bootstrap_se": {"p10": 0.02, "p50": 0.03, "p90": 0.2}}}
        pub = {"AC": {"total_rollouts": 10000, "achievement_rate_pct": 99.2, "p10": 2027.0, "p50": 2028.5, "p90": 2031.1}}
        rows = {r["stat"]: r for r in S.compare_to_published(ours, pub, z=3.0)}
        self.assertTrue(rows["p10"]["pass"])
        self.assertFalse(rows["p50"]["pass"])
        self.assertTrue(rows["p90"]["pass"])
        self.assertTrue(rows["achievement_rate_pct"]["pass"])
        self.assertAlmostEqual(rows["p50"]["tolerance"], 3 * math.sqrt(0.03 ** 2 * (1 + 0.1)))

    def test_max_rel_diff(self):
        self.assertEqual(S.max_rel_diff([1.0, 2.0], [1.0, 2.0]), 0.0)
        self.assertEqual(S.max_rel_diff([1.0, float("nan")], [1.0, 2.0]), float("inf"))
        self.assertAlmostEqual(S.max_rel_diff([1.1], [1.0]), 0.1)


class TestEvidenceRecords(unittest.TestCase):
    def test_outputs_are_never_observations_and_declare_fitting(self):
        all_recs = load_yaml(HERE.parents[2] / "evidence" / "records.yaml")["records"]
        ids = {r["id"] for r in all_recs}
        recs = [r for r in all_recs if r["id"].startswith("EV-AIFM-")]
        self.assertEqual(len(recs), 4)
        for r in recs:
            if r["id"].startswith("EV-AIFM-") and r["source"]["citation"].startswith("AI Futures Project"):
                self.assertEqual(r["kind"], "source_model_output", r["id"])
                self.assertTrue(r["fitted_to"], r["id"])
            for dep in r["depends_on"] + r["fitted_to"]:
                self.assertIn(dep, ids)
            if r["kind"] in ("observation", "observation_report") and r["reading"] != "read_primary":
                self.assertTrue(any("empirical support" in x for x in r["not_for"]), r["id"])


class TestHeldOut(unittest.TestCase):
    """#45: no METR observation is held out from AIFM yet; feedback on and off are not identifiable."""

    def test_no_metr_record_is_held_out(self):
        import heldout_audit as A

        rows = A.audit()
        self.assertEqual(len(rows), 15)
        self.assertEqual([x for x in rows if x["held_out"]], [])
        self.assertTrue(all(not x["available_after_aifm_cutoff"] for x in rows))
        self.assertTrue(all(not x["independent_of_aifm_outputs"] for x in rows if x["suite"] == "TH1.1"))
        self.assertEqual(A.AIFM_CUTOFF, load_yaml(HERE / "SOURCES.yaml")["upstream"]["commit_date"])

    def test_outputs_cite_primary_metr_records(self):
        recs = {r["id"]: r for r in load_yaml(HERE.parents[2] / "evidence" / "records.yaml")["records"]}
        primary = {"EV-METR-TH11-2026-03-03", "EV-METR-TH11-2026-04-10", "EV-METR-TH11-2026-04-15", "EV-METR-TH11-2026-05-08"}
        for rid in ("EV-AIFM-REFERENCE-TRAJECTORY", "EV-AIFM-DANIEL-08-16-26"):
            self.assertTrue(primary <= set(recs[rid]["fitted_to"]), rid)
            self.assertIn("EV-METR-TH10-2026-03-03", recs[rid]["depends_on"])
            self.assertNotIn("EV-AIFM-METR-HORIZON-V1-1", recs[rid]["depends_on"] + recs[rid]["fitted_to"])
            for dep in recs[rid]["depends_on"] + recs[rid]["fitted_to"]:
                self.assertIn(dep, recs)

    def test_bundled_metr_file_is_metr_published_file(self):
        h = result("horizon_identifiability.json")["bundled_metr_file_sha256"]
        sums = (HERE.parent / "metr-time-horizons" / "sources.sha256").read_text()
        self.assertIn(f"{h}  metr.org/benchmark_results_1_1.yaml", sums)

    def test_identifiability_diagnostic(self):
        d = result("horizon_identifiability.json")
        self.assertIn("IN-SAMPLE", d["status"])
        self.assertIn("not a held-out test", d["status"])
        fit = d["in_sample_fit_p80"]
        # The "on" curve is evaluated exactly as the upstream's own compute_metr_mse.
        self.assertAlmostEqual(fit["feedback_on"]["mean_squared_log_error"], d["upstream_compute_metr_mse"], places=9)
        self.assertEqual(fit["feedback_on"]["n"], len(d["observations"]))
        # On and off are separated by far less than METR's own measurement uncertainty at every observed date.
        sep = max(d["max_abs_log_separation_on_vs_off"].values())
        self.assertLess(sep, 0.1)
        self.assertLess(sep, d["median_half_width_ln_p80_ci95"] / 5)
        mses = [v["mean_squared_log_error"] for v in fit.values()]
        self.assertLess(max(mses) - min(mses), 0.05)


if __name__ == "__main__":
    unittest.main(verbosity=1)
