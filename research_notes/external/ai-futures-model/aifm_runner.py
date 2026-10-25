"""Run the pinned AI Futures Model and write small, reviewable summaries.

Needs an upstream checkout made by fetch_upstream.sh and the upstream's own Python
environment (see README: Python 3.14, numpy 2.4.1, scipy 1.17.0, pyyaml). Not run by
`make check`; the fast tests only read what this writes.

    python aifm_runner.py reference    --src .upstream   # golden trajectory replication
    python aifm_runner.py feedback-off --src .upstream   # human-only counterfactual, two calibrations
    python aifm_runner.py anchors      --src .upstream   # AC anchor modes at default parameters
    python aifm_runner.py horizon-identifiability --src .upstream   # feedback on vs off at METR dates (#45)
    python aifm_runner.py rollouts     --src .upstream --preset published-daniel-08-16-26 -n 1000
    python aifm_runner.py summarize-rollouts --run-dir RUN --preset published-daniel-08-16-26

Every subcommand writes results/<name>.json with a provenance block. Nothing here edits
the upstream checkout; the rollout run directory goes under --out (default: a temp dir).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
sys.path.insert(0, str(HERE))
import aifm_summary as S  # noqa: E402

TOL = json.loads((HERE / "tolerances.json").read_text())

# Rollout presets: which config, input series, seed and time range, and what to compare with.
PRESETS = {
    # Reproduce the published Daniel 08-16-26 forecast's setup: the flattened config the
    # upstream exported next to it, the input series it names (inputs/2200.csv) and its seed.
    "published-daniel-08-16-26": {
        "config": "app/forecast/data/simulations/daniel-08-16-26/sampling_config.yaml",
        "input_data": "inputs/2200.csv",
        "seed": 20260810,
        "time_range": [2017.0, 2200.0],
        "published_dir": "app/forecast/data/simulations/daniel-08-16-26",
    },
    # The same forecaster's config as it stands at the pinned commit, with the default inputs.
    "pinned-q2-daniel": {
        "config": "config/sampling_config_q2_daniel.yaml",
        "input_data": "inputs/input_data.csv",
        "seed": 20260810,
        "time_range": [2017.0, 2200.0],
        "published_dir": None,
    },
}


def provenance(src: Path, command: str) -> dict:
    import numpy
    import scipy

    commit = subprocess.run(["git", "-C", str(src), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(src), "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True, check=True).stdout.strip()
    return {
        "upstream": "https://github.com/AI-Futures-Project/aifm-public",
        "upstream_commit": commit,
        "upstream_tracked_files_modified": bool(dirty),
        "command": command,
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _import_upstream(src: Path):
    src = src.resolve()
    for p in (str(src), str(src / "tests")):
        if p not in sys.path:
            sys.path.insert(0, p)
    os.chdir(src)
    import logging

    logging.disable(logging.WARNING)
    import warnings

    warnings.filterwarnings("ignore")


def _write(name: str, payload: dict) -> Path:
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"{name}.json"
    path.write_text(json.dumps(payload, indent=1, sort_keys=False, default=float) + "\n")
    print(f"wrote {path.relative_to(HERE)}")
    return path


def _milestone_table(results) -> dict:
    out = {}
    for name, m in (results.get("milestones") or {}).items():
        out[name] = {
            "metric": m.get("metric"),
            "target": m.get("target"),
            "time": S._finite_or_none(m.get("time")),
            "effective_compute_ooms": S._finite_or_none(m.get("effective_compute_ooms")),
        }
    return out


def _progress_at(times, progress, t):
    import numpy as np

    if t is None:
        return None
    return float(np.interp(t, times, progress))


# ---------------------------------------------------------------------------------------
# reference: the upstream's default-parameter golden trajectory
# ---------------------------------------------------------------------------------------

GOLDEN_SERIES = {  # golden key -> results key
    "times": "times", "progress": "progress", "research_stock": "research_stock",
    "progress_rates": "progress_rates", "etsp_rates": "etsp_rates", "research_efforts": "research_efforts",
    "automation_fractions": "automation_fraction", "ai_research_tastes": "ai_research_taste",
    "ai_research_taste_sds": "ai_research_taste_sd", "aggregate_research_tastes": "aggregate_research_taste",
    "coding_labors": "coding_labors", "serial_coding_labors": "serial_coding_labors",
    "software_progress_rates": "software_progress_rates", "software_efficiency": "software_efficiency",
    "effective_compute": "effective_compute", "training_compute": "training_compute",
    "horizon_lengths": "horizon_lengths", "experiment_capacity": "experiment_capacity",
    "human_only_progress_rates": "human_only_progress_rates",
    "ai_coding_labor_multipliers": "ai_coding_labor_multipliers",
    "ai_sw_progress_mult_ref_present_day": "ai_sw_progress_mult_ref_present_day",
}


def cmd_reference(args):
    _import_upstream(args.src)
    import numpy as np
    from progress_model import ProgressModel
    from utils import load_time_series_data, parameters_from_dict, DEFAULT_TIME_RANGE

    gdir = Path("tests/golden_data")
    golden = json.loads((gdir / "default_trajectory.json").read_text())
    gm = json.loads((gdir / "default_milestones.json").read_text())
    tol = TOL["reference_trajectory"]

    t0 = time.time()
    model = ProgressModel(parameters_from_dict(golden["_generation_parameters"]), load_time_series_data())
    model.compute_progress_trajectory(DEFAULT_TIME_RANGE, initial_progress=0.0)
    wall = time.time() - t0
    r = model.results

    series = {}
    for gk, rk in GOLDEN_SERIES.items():
        exp = np.asarray(golden[gk], dtype=float)
        act = np.asarray(r[rk], dtype=float)
        if exp.size == 0:
            series[gk] = {"compared": False, "reason": "empty in golden file"}
            continue
        absd = np.abs(act - exp) if act.shape == exp.shape else np.array([np.inf])
        ok = bool(act.shape == exp.shape and np.allclose(act, exp, rtol=tol["series_rtol"], atol=tol["series_atol"]))
        series[gk] = {"n": int(exp.size), "max_abs_diff": float(np.max(absd)),
                      "max_rel_diff": S.max_rel_diff(act, exp, floor=1e-12), "pass": ok}

    scalars = {}
    for key, actual, atol in (
        ("aa_time", r.get("aa_time"), tol["milestone_time_atol_years"]),
        ("ai2027_sc_time", r.get("ai2027_sc_time"), tol["milestone_time_atol_years"]),
        ("progress_at_aa", model.params.progress_at_aa, tol["progress_atol_ooms"]),
        ("final_progress", float(r["progress"][-1]), tol["progress_atol_ooms"]),
        ("sc_sw_multiplier", r.get("sc_sw_multiplier"), tol["multiplier_rtol"] * abs(gm["sc_sw_multiplier"])),
    ):
        d = abs(float(actual) - float(gm[key]))
        scalars[key] = {"ours": float(actual), "golden": float(gm[key]), "abs_diff": d, "tolerance": atol, "pass": d <= atol}

    times, prog = np.asarray(r["times"]), np.asarray(r["progress"])
    yearly = [float(y) for y in range(2016, 2051, 2)]
    pick = lambda key: [float(np.interp(y, times, np.asarray(r[key], dtype=float))) for y in yearly]  # noqa: E731
    payload = {
        "what": "Upstream default parameters (tests/golden_data/default_trajectory.json _generation_parameters), "
                "time range [2015, 2050], initial_progress 0.0, compared with the upstream golden files.",
        "status": "source-model replication of the upstream's own golden output; not empirical validation",
        "tolerance": tol,
        "pass": all(v.get("pass", True) for v in series.values()) and all(v["pass"] for v in scalars.values()),
        "series": series,
        "scalars": scalars,
        "r_software_calibrated": float(r["r_software"]),
        "milestones": _milestone_table(r),
        "milestone_progress_ooms": {k: _progress_at(times, prog, v["time"]) for k, v in _milestone_table(r).items()},
        "sampled_path": {
            "year": yearly,
            "progress_ooms": pick("progress"),
            "software_efficiency_ooms": pick("software_efficiency"),
            "training_compute_ooms": pick("training_compute"),
            "research_stock": pick("research_stock"),
            "automation_fraction": pick("automation_fraction"),
            "ai_research_taste_sd": pick("ai_research_taste_sd"),
            "aggregate_research_taste": pick("aggregate_research_taste"),
            "serial_coding_labor": pick("serial_coding_labors"),
            "ai_sw_progress_mult_ref_present_day": pick("ai_sw_progress_mult_ref_present_day"),
        },
        "wall_seconds": round(wall, 2),
        "provenance": provenance(args.src, "aifm_runner.py reference"),
    }
    _write("reference_trajectory", payload)
    return 0 if payload["pass"] else 1


# ---------------------------------------------------------------------------------------
# feedback-off: the upstream's human-only counterfactual, against the full run
# ---------------------------------------------------------------------------------------

def _default_model(time_range, overrides=None):
    from progress_model import ProgressModel
    from utils import load_time_series_data, parameters_from_dict

    golden = json.loads(Path("tests/golden_data/default_trajectory.json").read_text())
    params = dict(golden["_generation_parameters"])
    params.update(overrides or {})
    model = ProgressModel(parameters_from_dict(params), load_time_series_data())
    model.compute_progress_trajectory(time_range, initial_progress=0.0)
    return model


def cmd_feedback_off(args):
    _import_upstream(args.src)
    import numpy as np
    from progress_model import config as cfg

    tr = [2017.0, 2200.0]
    model = _default_model(tr)
    r = model.results
    times, prog = np.asarray(r["times"], dtype=float), np.asarray(r["progress"], dtype=float)
    ms = _milestone_table(r)
    levels = {k: _progress_at(times, prog, v["time"]) for k, v in ms.items()}

    def human_only(r_software):
        model.params.r_software = r_software
        model.compute_human_only_trajectory(tr, initial_progress=0.0)
        ho = model.human_only_results
        t, p = np.asarray(ho["times"], dtype=float), np.asarray(ho["progress"], dtype=float)
        rate_2024 = float(np.interp(cfg.SOFTWARE_PROGRESS_SCALE_REFERENCE_YEAR, t, np.asarray(ho["sw_progress_rates"], dtype=float)))
        return t, p, rate_2024

    r_cal = float(r["r_software"])
    t_a, p_a, rate_a = human_only(r_cal)
    # Refit: human-only software rate is linear in r_software (effort and stock do not depend on it),
    # so scale r_software to hit the same elicited 2024 software-progress rate without any AI uplift.
    target = float(model.params.software_progress_rate_at_reference_year)
    r_refit = r_cal * target / rate_a
    t_b, p_b, rate_b = human_only(r_refit)
    model.params.r_software = r_cal

    rows = {}
    for k, lvl in levels.items():
        if lvl is None:
            rows[k] = {"feedback_on": None, "off_same_calibration": None, "off_refit": None, "progress_level_ooms": None}
            continue
        rows[k] = {
            "progress_level_ooms": lvl,
            "feedback_on": ms[k]["time"],
            "off_same_calibration": S.crossing_time(t_a, p_a, lvl),
            "off_refit": S.crossing_time(t_b, p_b, lvl),
        }
    pick_years = [2020.0, 2024.0, 2026.578082, 2030.0, 2035.0, 2040.0, 2050.0, 2075.0, 2100.0]
    payload = {
        "what": "Feedback-off baseline. Upstream default parameters over [2017, 2200]. 'feedback_on' is the full model; "
                "the two off runs are the upstream's own human-only counterfactual (automation fraction 0, aggregate taste 1, "
                "coding labor = human labor; compute and labor paths unchanged). 'off_same_calibration' keeps the r_software "
                "calibrated with AI uplift in the history; 'off_refit' rescales r_software so the human-only run hits the same "
                "elicited 2024 software-progress rate. Milestone columns give the date each run first reaches the progress "
                "level (log10 cumulative effective compute) at which the full run crosses that milestone; capability schedules "
                "are functions of progress, so this is the date the same capability level would be reached.",
        "status": "counterfactual inside the source model; not empirical validation",
        "r_software": {"calibrated_with_uplift": r_cal, "refit_human_only": r_refit},
        "software_progress_rate_2024": {"target": target, "off_same_calibration": rate_a, "off_refit": rate_b},
        "milestone_dates": rows,
        "progress_path": {
            "year": pick_years,
            "feedback_on": [float(np.interp(y, times, prog)) for y in pick_years],
            "off_same_calibration": [float(np.interp(y, t_a, p_a)) for y in pick_years],
            "off_refit": [float(np.interp(y, t_b, p_b)) for y in pick_years],
        },
        "provenance": provenance(args.src, "aifm_runner.py feedback-off"),
    }
    _write("feedback_off", payload)
    return 0


# ---------------------------------------------------------------------------------------
# anchors: alternative AC calibration anchors at default parameters
# ---------------------------------------------------------------------------------------

def cmd_anchors(args):
    _import_upstream(args.src)
    import numpy as np

    out = {}
    for mode in ("uplift-solved", "time-horizon", "revenue", "eci"):
        model = _default_model([2017.0, 2200.0], {"ac_anchor_mode": mode})
        r = model.results
        ms = _milestone_table(r)
        td = r.get("td_correction") or {}
        out[mode] = {
            "progress_at_ac_ooms": float(model.params.progress_at_aa),
            "r_software": float(r["r_software"]),
            "milestone_times": {k: v["time"] for k, v in ms.items()},
            "td_correction": {k: td.get(k) for k in ("mode", "applied", "reason", "believed", "measured", "mismatch") if k in td},
            "progress_2026_578": float(np.interp(2026.578082, r["times"], r["progress"])),
        }
    payload = {
        "what": "Default parameters over [2017, 2200], varying only ac_anchor_mode. Each mode sets the AC progress "
                "threshold from a different belief (uplift schedule, METR p80 time horizon, revenue, Epoch Capabilities "
                "Index); the anchor beliefs are the upstream defaults (ac_time_horizon_minutes 120000, revenue_required_for_ac "
                "1e12 USD, eci_required_for_ac 250).",
        "status": "alternative calibration anchors inside the source model; not empirical validation",
        "anchors": out,
        "provenance": provenance(args.src, "aifm_runner.py anchors"),
    }
    _write("anchors", payload)
    return 0


# ---------------------------------------------------------------------------------------
# rollouts: seeded Monte Carlo with the upstream batch runner, then a compact summary
# ---------------------------------------------------------------------------------------

FORK_SHIM = (
    "import multiprocessing as mp, runpy, sys; mp.set_start_method('fork', force=True); "
    "sys.argv = sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')"
)


def cmd_rollouts(args):
    src = args.src.resolve()
    p = PRESETS[args.preset]
    out = Path(args.out or tempfile.mkdtemp(prefix="aifm-rollouts-")).resolve()
    cmd = [sys.executable, "-c", FORK_SHIM, "scripts/pipelines/batch_rollout.py",
           "--config", p["config"], "--input-data", p["input_data"],
           "--time-range", str(p["time_range"][0]), str(p["time_range"][1]),
           "--num-samples", str(args.num_samples), "--seed", str(p["seed"]),
           "--num-workers", str(args.workers), "--skip-summary", "--output-dir", str(out)]
    print(" ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=src, check=True)
    runs = sorted(d for d in out.iterdir() if (d / "rollouts.jsonl").exists())
    args.run_dir = runs[-1]
    return cmd_summarize(args)


def cmd_summarize(args):
    src = args.src.resolve()
    p = PRESETS[args.preset]
    run_dir = Path(args.run_dir).resolve()
    meta = json.loads((run_dir / "metadata.json").read_text())
    records = list(S.iter_rollout_records(run_dir / "rollouts.jsonl"))
    summary = S.summarize(records)
    n_samples = int(meta["num_samples"])
    tol = TOL["seeded_distribution"]
    payload = {
        "what": f"Seeded Monte Carlo, preset {args.preset}: config {p['config']}, inputs {p['input_data']}, "
                f"seed {p['seed']}, time range {p['time_range']}, {n_samples} samples.",
        "status": "source-model replication of a sampling-measure output; shares are draws under the sampled "
                  "parameter measure, not calibrated probabilities; not empirical validation",
        "preset": dict(p, num_samples=n_samples),
        "failed_rollouts": n_samples - len(records),
        "failures_by_reason": S.failure_reasons(run_dir / "rollouts.jsonl"),
        "failure_note": "Timeouts come from the upstream's 30 s per-sample limit and depend on machine load; "
                        "infeasible uplift beliefs are the model's own rejections (uplift-solved mode).",
        "summary": summary,
    }
    if p["published_dir"]:
        pub_dir = src / p["published_dir"]
        published = S.read_published_overlay(pub_dir / "milestone_pdfs_overlay_statistics.csv")
        rows = S.compare_to_published(summary["overall"], published, z=tol["z"])
        payload["published"] = {
            "source": f"{p['published_dir']}/milestone_pdfs_overlay_statistics.csv",
            "metadata": json.loads((pub_dir / "metadata.json").read_text()),
            "overall": published,
        }
        payload["comparison"] = {"tolerance": tol, "rows": rows,
                                 "pass": all(r["pass"] for r in rows),
                                 "n_fail": sum(not r["pass"] for r in rows)}
    payload["provenance"] = provenance(src, f"aifm_runner.py rollouts --preset {args.preset} -n {n_samples}")
    payload["provenance"]["run_metadata"] = {k: meta.get(k) for k in ("num_samples", "seed", "time_range", "per_sample_timeout")}
    _write(f"seeded_{args.preset}_n{n_samples}", payload)
    return 0


# ---------------------------------------------------------------------------------------
# horizon-identifiability: feedback on vs off, in horizon units, at METR's observation dates (#45)
# ---------------------------------------------------------------------------------------

def _decimal_year(d) -> float:
    # The upstream's own convention (progress_model/ac_anchor.py, _impl.py compute_metr_mse).
    return d.year + (d.timetuple().tm_yday - 1) / 365.25


def cmd_horizon_identifiability(args):
    """In-sample diagnostic, not a held-out test: every METR value used here is in AIFM's own input file."""
    _import_upstream(args.src)
    import hashlib

    import numpy as np
    from progress_model.ac_anchor import _load_benchmark_data

    bundled = Path("inputs/metr/benchmark_results_1_1.yaml")
    tr = [2017.0, 2200.0]
    model = _default_model(tr)
    r = model.results
    times, prog = np.asarray(r["times"], dtype=float), np.asarray(r["progress"], dtype=float)
    upstream_mse = model.compute_metr_mse()
    # The progress coordinates the horizon curve was fitted in (what compute_metr_mse uses for "on").
    m_times, m_prog = (np.asarray(x, dtype=float) for x in model._anchor_mapping)

    r_cal = float(r["r_software"])
    paths = {}
    for name, r_soft in (("off_same_calibration", r_cal), ("off_refit", None)):
        if r_soft is None:  # same refit rule as cmd_feedback_off
            model.params.r_software = r_cal
            model.compute_human_only_trajectory(tr, initial_progress=0.0)
            ho = model.human_only_results
            from progress_model import config as cfg
            rate = float(np.interp(cfg.SOFTWARE_PROGRESS_SCALE_REFERENCE_YEAR, ho["times"], ho["sw_progress_rates"]))
            r_soft = r_cal * float(model.params.software_progress_rate_at_reference_year) / rate
        model.params.r_software = r_soft
        model.compute_human_only_trajectory(tr, initial_progress=0.0)
        ho = model.human_only_results
        paths[name] = (np.asarray(ho["times"], dtype=float), np.asarray(ho["progress"], dtype=float))
    model.params.r_software = r_cal

    def prog_at(t_arr, p_arr, t):
        return float(np.interp(t, t_arr, p_arr)) if t_arr.min() <= t <= t_arr.max() else float(p_arr[0] if t < t_arr.min() else p_arr[-1])

    rows = []
    for key, info in _load_benchmark_data()["results"].items():
        rel = info["release_date"]
        rel = datetime.strptime(rel, "%Y-%m-%d").date() if isinstance(rel, str) else rel
        y = _decimal_year(rel)
        p80 = info["metrics"]["p80_horizon_length"]
        row = {"model_key": key, "release_date": rel.isoformat(), "decimal_year": y,
               "observed_p80": float(p80["estimate"]), "p80_ci95": [float(p80["ci_low"]), float(p80["ci_high"])],
               "progress_on": prog_at(m_times, m_prog, y), "progress_on_full_run": prog_at(times, prog, y)}
        row["horizon_on"] = float(model.horizon_trajectory(row["progress_on"]))
        for name, (t_arr, p_arr) in paths.items():
            row[f"progress_{name}"] = prog_at(t_arr, p_arr, y)
            row[f"horizon_{name}"] = float(model.horizon_trajectory(row[f"progress_{name}"]))
        rows.append(row)
    rows.sort(key=lambda x: (x["decimal_year"], x["model_key"]))

    def summary(series):
        e = np.array([np.log(x[series]) - np.log(x["observed_p80"]) for x in rows])
        return {"n": int(e.size), "mean_squared_log_error": float(np.mean(e ** 2)), "mean_abs_log_error": float(np.mean(np.abs(e)))}

    sep = {name: float(max(abs(np.log(x["horizon_on"]) - np.log(x[f"horizon_{name}"])) for x in rows)) for name in paths}
    # Where the paths separate: the source model's own curves at later dates (the dates of the METR suite's
    # locked forecast, and later). Statements about the source model, not forecasts by this project.
    later = []
    for y in (2026.75, 2027.3274, 2027.8301, 2028.0):
        row = {"decimal_year": y, "horizon_on": float(model.horizon_trajectory(prog_at(times, prog, y)))}
        for name, (t_arr, p_arr) in paths.items():
            row[f"horizon_{name}"] = float(model.horizon_trajectory(prog_at(t_arr, p_arr, y)))
        later.append(row)
    ci_half = [0.5 * (np.log(x["p80_ci95"][1]) - np.log(x["p80_ci95"][0])) for x in rows]
    payload = {
        "what": "AIFM's p80 time horizon at the release date of every model in its bundled METR file, with feedback on "
                "(the full model, in the progress coordinates the horizon curve was fitted in, as compute_metr_mse) and off "
                "(the upstream's human-only counterfactual, same calibration and r_software refit, mapped through the same "
                "horizon curve). Default parameters over [2017, 2200]; dates use the upstream's decimal-year convention.",
        "status": "IN-SAMPLE diagnostic of identifiability inside the source model. Every observation here is in AIFM's own "
                  "input file (fitted_to), so this is not a held-out test, not a score under evidence/protocol.yaml and not "
                  "empirical validation.",
        "bundled_metr_file_sha256": hashlib.sha256(bundled.read_bytes()).hexdigest(),
        "horizon_reference": {"present_horizon": float(model.params.present_horizon),
                              "horizon_reference_date": float(model.params.horizon_reference_date),
                              "present_doubling_time_years": float(model.params.present_doubling_time)},
        "upstream_compute_metr_mse": None if upstream_mse is None else float(upstream_mse),
        "in_sample_fit_p80": {"feedback_on": summary("horizon_on"),
                              **{name: summary(f"horizon_{name}") for name in paths}},
        "max_abs_log_separation_on_vs_off": sep,
        "median_half_width_ln_p80_ci95": float(np.median(ci_half)),
        "later_dates_source_model_only": later,
        "observations": rows,
        "provenance": provenance(args.src, "aifm_runner.py horizon-identifiability"),
    }
    _write("horizon_identifiability", payload)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=HERE / ".upstream", help="upstream checkout from fetch_upstream.sh")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("reference")
    sub.add_parser("feedback-off")
    sub.add_parser("anchors")
    sub.add_parser("horizon-identifiability")
    ro = sub.add_parser("rollouts")
    ro.add_argument("--preset", choices=sorted(PRESETS), required=True)
    ro.add_argument("-n", "--num-samples", type=int, default=1000)
    ro.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    ro.add_argument("--out", default=None)
    sm = sub.add_parser("summarize-rollouts")
    sm.add_argument("--preset", choices=sorted(PRESETS), required=True)
    sm.add_argument("--run-dir", required=True)
    args = ap.parse_args(argv)
    args.src = args.src.resolve()
    return {"reference": cmd_reference, "feedback-off": cmd_feedback_off, "anchors": cmd_anchors,
            "horizon-identifiability": cmd_horizon_identifiability, "rollouts": cmd_rollouts, "summarize-rollouts": cmd_summarize}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
