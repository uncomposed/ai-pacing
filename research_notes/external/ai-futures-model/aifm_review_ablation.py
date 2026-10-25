"""Issue #49: review/integration throughput cap. An EXTENSION by this project, not AIFM behaviour.

Runs the pinned upstream with review_cap.py applied at run time (nothing on disk is
patched) and writes small summaries next to the replication results. Needs the same
upstream checkout and environment as aifm_runner.py; not run by `make check`.

    python aifm_review_ablation.py sweep     --src .upstream     # default parameters, kappa sweep
    python aifm_review_ablation.py rollouts  --src .upstream --preset published-daniel-08-16-26 -n 400

`sweep` writes results/review_cap_sweep.json; `rollouts` writes
results/review_cap_rollouts_<preset>_n<N>.json. Both carry a provenance block that records
the runtime patch.
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import aifm_runner as R  # noqa: E402
import aifm_summary as S  # noqa: E402
import review_cap as C  # noqa: E402

# Scenario values, not estimates: no measurement gives kappa in these units (see README, issue #49).
# inf is the upstream. 1 is a limit check: validated flow never exceeds a no-AI lab's, so the
# research stock follows the human-only path and dates should match the feedback-off run.
SWEEP_KAPPAS = (math.inf, 100.0, 30.0, 10.0, 5.0, 3.0, 2.0, 1.5, 1.25, 1.0)
ROLLOUT_KAPPAS = (math.inf, 30.0, 10.0, 3.0)
PROGRESS_MILESTONES = ("AC", "SAR-level-experiment-selection-skill", "TED-AI",
                       "SIAR-level-experiment-selection-skill", "ASI")
TIME_RANGE = [2017.0, 2200.0]


def _k(kappa: float) -> str:
    return "inf" if math.isinf(kappa) else f"{kappa:g}"


def _patch_provenance(mechanism: str) -> dict:
    return {"extension": C.EXTENSION_LABEL, "runtime_patch_target": C.PATCH_TARGET, "mechanism": mechanism,
            "upstream_files_modified": False}


def cmd_sweep(args):
    R._import_upstream(args.src)
    import numpy as np

    base = R._default_model(TIME_RANGE)
    r0 = base.results
    t0, p0 = np.asarray(r0["times"], dtype=float), np.asarray(r0["progress"], dtype=float)
    levels = {m: R._progress_at(t0, p0, r0["milestones"][m]["time"]) for m in PROGRESS_MILESTONES}
    ec_thresholds = {m: r0["milestones"][m]["effective_compute_ooms"] for m in PROGRESS_MILESTONES}
    present_day = float(base.params.present_day)

    # Feedback-off reference in the same process: the upstream's human-only run, same calibration.
    r_cal = float(r0["r_software"])
    base.params.r_software = r_cal
    base.compute_human_only_trajectory(TIME_RANGE, initial_progress=0.0)
    ho = base.human_only_results
    th, ph = np.asarray(ho["times"], dtype=float), np.asarray(ho["progress"], dtype=float)
    off = {m: S.crossing_time(th, ph, lvl) for m, lvl in levels.items()}

    s0 = C.cap_series(base, math.inf)
    ratio = s0["demand"] / s0["re_human"]
    uplift_path = {str(y): float(np.interp(y, s0["times"], ratio))
                   for y in (2024.0, 2025.0, 2026.0, present_day, 2027.0, 2027.5, r0["milestones"]["AC"]["time"], 2028.0)}

    rows = {}
    for kappa in SWEEP_KAPPAS:
        with C.review_cap(kappa):
            model = R._default_model(TIME_RANGE)
        r = model.results
        t, p = np.asarray(r["times"], dtype=float), np.asarray(r["progress"], dtype=float)
        ms = {m: S._finite_or_none(r["milestones"].get(m, {}).get("time")) for m in PROGRESS_MILESTONES}
        # Same thresholds as the uncapped run: they are functions of progress fixed before integration.
        ec_shift = max(abs(r["milestones"][m]["effective_compute_ooms"] - ec_thresholds[m]) for m in PROGRESS_MILESTONES if ms[m] is not None)
        # The upstream dates taste milestones by interpolating the taste SD exponentially in time on a 0.1-year
        # grid; crossing the uncapped run's progress level linearly is the method used for feedback-off.
        by_level = {m: S.crossing_time(t, p, levels[m]) for m in PROGRESS_MILESTONES}
        series = C.cap_series(model, kappa)
        asi = ms["ASI"]
        diag = C.cap_diagnostics(series, t_end_check=asi + 1.0 if asi else None)
        ac = ms["AC"]
        gap = (asi - ac) if (asi is not None and ac is not None) else None

        def at(y, key):
            return None if y is None else float(np.interp(y, series["times"], series[key]))

        rows[_k(kappa)] = {
            "kappa": None if math.isinf(kappa) else kappa,
            "milestones": ms,
            "ac_to_asi_years": gap,
            "ac_to_ted_ai_years": (ms["TED-AI"] - ac) if (ms["TED-AI"] and ac) else None,
            "ac_to_asi_years_by_progress_level": (by_level["ASI"] - by_level["AC"]) if by_level["ASI"] and by_level["AC"] else None,
            # Both gaps by the same method (progress-level crossing), so the ratio has no date-method mix.
            "compression_vs_feedback_off": ((off["ASI"] - off["AC"]) / (by_level["ASI"] - by_level["AC"])
                                            if by_level["ASI"] and by_level["AC"] else None),
            "first_binding_year": diag["first_binding_year"],
            "binds_before_present_day": diag["first_binding_year"] is not None and diag["first_binding_year"] < present_day,
            "validated_share_of_demand": {"at_AC": at(ac, "expected_flow") / at(ac, "demand") if ac else None,
                                          "at_ASI": at(asi, "expected_flow") / at(asi, "demand") if asi else None},
            "progress_at_present_day_ooms": float(np.interp(present_day, t, p)),
            "milestones_by_progress_level": by_level,
            "date_method_max_difference_years": max(abs(ms[m] - by_level[m]) for m in PROGRESS_MILESTONES if ms[m] is not None and by_level[m] is not None),
            "milestone_threshold_ec_max_shift_ooms": ec_shift,
            "r_software": float(r["r_software"]),
            "flow_self_check": diag["flow_self_check"],
        }

    payload = {
        "what": "Review/integration throughput cap, default parameters over [2017, 2200]. Research stock grows at "
                "min(RE, kappa * RE_human) instead of RE; RE_human is the upstream's human-only research effort at the "
                "same date. kappa = inf is the upstream. Calibration (r_software), the uplift reconstruction and the "
                "automation-schedule anchoring are the upstream's and do not see the cap. Milestones are the progress-"
                "defined ones (AC, SAR, TED-AI, SIAR, ASI); multiplier-defined milestones (AIR-*x, AI2027-SC) are "
                "computed by the upstream from uncapped demand and are not reported.",
        "status": "EXTENSION by this project (issue #49), not AIFM behaviour; scenario sweep inside the source model "
                  "with kappa values chosen as scenarios, not estimated; not empirical validation; no date here is a forecast",
        "kappas": [None if math.isinf(k) else k for k in SWEEP_KAPPAS],
        "kappa_basis": "scenario sweep: no measurement gives the throughput of review and integration relative to a "
                       "no-AI lab in these units. EV-METR-ALGO-2025 shows review overhead exists for agent code but its "
                       "not_for excludes use as a conversion factor. kappa = 1 is a limit check, not a scenario.",
        "present_day": present_day,
        "uncapped_demand_over_human_only_effort": uplift_path,
        "milestone_progress_levels_ooms": levels,
        "feedback_off_same_calibration": {"milestones": off, "ac_to_asi_years": off["ASI"] - off["AC"]},
        "rows": rows,
        "provenance": dict(R.provenance(args.src, "aifm_review_ablation.py sweep"),
                           **_patch_provenance("context manager in-process (review_cap.review_cap)")),
    }
    R._write("review_cap_sweep", payload)
    return 0


def _run_batch(src: Path, preset: dict, n: int, workers: int, kappa: float, out: Path) -> Path:
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(filter(None, [str(HERE / "review_cap_hook"), os.environ.get("PYTHONPATH")])),
               AIFM_REVIEW_CAP_KAPPA=repr(kappa), AIFM_REVIEW_CAP_SRC=str(src), AIFM_REVIEW_CAP_HERE=str(HERE))
    cmd = [sys.executable, "-c", R.FORK_SHIM, "scripts/pipelines/batch_rollout.py",
           "--config", preset["config"], "--input-data", preset["input_data"],
           "--time-range", str(preset["time_range"][0]), str(preset["time_range"][1]),
           "--num-samples", str(n), "--seed", str(preset["seed"]),
           "--num-workers", str(workers), "--skip-summary", "--output-dir", str(out)]
    print(f"kappa={_k(kappa)}: " + " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=src, check=True, env=env)
    runs = sorted(d for d in out.iterdir() if (d / "rollouts.jsonl").exists())
    return runs[-1]


def cmd_rollouts(args):
    src = args.src.resolve()
    preset = R.PRESETS[args.preset]
    base_out = Path(args.out or tempfile.mkdtemp(prefix="aifm-reviewcap-")).resolve()
    kappas = [math.inf if k == "inf" else float(k) for k in args.kappas]
    per = {}
    records_by_k = {}
    for kappa in kappas:
        out = base_out / f"kappa_{_k(kappa)}"
        out.mkdir(parents=True, exist_ok=True)
        run_dir = _run_batch(src, preset, args.num_samples, args.workers, kappa, out)
        recs = list(S.iter_rollout_records(run_dir / "rollouts.jsonl"))
        records_by_k[_k(kappa)] = recs
        per[_k(kappa)] = {
            "kappa": None if math.isinf(kappa) else kappa,
            "successful_rollouts": len(recs),
            "failures_by_reason": S.failure_reasons(run_dir / "rollouts.jsonl"),
            "milestones": {m: S.milestone_stats(recs, m) for m in ("AC", "TED-AI", "ASI")},
            "after_ac": {"ASI": C.gap_stats(recs, "ASI", thresholds=(1.0, 2.0, 5.0, 10.0)),
                         "TED-AI": C.gap_stats(recs, "TED-AI", thresholds=(0.75,))},
        }

    # Patch-active check: same seed, so sample i has the same parameters under every kappa.
    ref = {r["sample_id"]: r for r in records_by_k.get("inf", [])}
    for key, recs in records_by_k.items():
        if key == "inf" or not ref:
            continue
        pairs = [(ref[r["sample_id"]], r) for r in recs if r["sample_id"] in ref]
        later = [b["milestones"]["ASI"] is None or (a["milestones"]["ASI"] is not None and b["milestones"]["ASI"] > a["milestones"]["ASI"] + 1e-6)
                 for a, b in pairs if a["milestones"]["ASI"] is not None]
        earlier = [b["milestones"]["ASI"] is not None and b["milestones"]["ASI"] < a["milestones"]["ASI"] - 1e-3
                   for a, b in pairs if a["milestones"]["ASI"] is not None]
        ac_moved = [b["milestones"]["AC"] is None or b["milestones"]["AC"] > a["milestones"]["AC"] + 0.01
                    for a, b in pairs if a["milestones"]["AC"] is not None]
        per[key]["paired_with_uncapped"] = {"pairs": len(pairs), "share_asi_later": float(sum(later) / len(later)) if later else None,
                                            "share_ac_later_by_over_0.01_years": float(sum(ac_moved) / len(ac_moved)) if ac_moved else None,
                                            "share_asi_earlier_by_over_1e-3_years": float(sum(earlier) / len(earlier)) if earlier else None}

    published = None
    if preset["published_dir"]:
        pub = src / preset["published_dir"]
        published = {"source": f"{preset['published_dir']}/ac_unconditional_time_until_cdf.csv and _statistics.csv",
                     "after_ac": _read_published_after_ac(pub)}
    payload = {
        "what": f"Review/integration throughput cap in the seeded Monte Carlo, preset {args.preset} (config "
                f"{preset['config']}, inputs {preset['input_data']}, seed {preset['seed']}), {args.num_samples} samples "
                "per kappa, same seed for every kappa so sample i has the same parameters. Cap as in review_cap.py, "
                "relative to each sample's own human-only research effort. 'after_ac' follows the upstream's "
                "generate_conditional_timing.py: rollouts that reached AC; a milestone never reached counts as not "
                "reached at any finite time (1e6 in quantiles).",
        "status": "EXTENSION by this project (issue #49), not AIFM behaviour; shares are draws under Daniel's elicited "
                  "sampling measure, not calibrated probabilities; not empirical validation; no date here is a forecast",
        "preset": dict(preset, num_samples=args.num_samples),
        "kappas": [None if math.isinf(k) else k for k in kappas],
        "rows": per,
        "published_uncapped": published,
        "provenance": dict(R.provenance(src, f"aifm_review_ablation.py rollouts --preset {args.preset} -n {args.num_samples}"),
                           **_patch_provenance("review_cap_hook/sitecustomize.py on PYTHONPATH, so every spawned rollout "
                                               "process applies review_cap at start-up")),
    }
    R._write(f"review_cap_rollouts_{args.preset}_n{args.num_samples}", payload)
    return 0


def _read_published_after_ac(pub: Path) -> dict:
    import csv

    import numpy as np

    with open(pub / "ac_unconditional_time_until_cdf.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    x = np.array([float(r["time_decimal_year"]) for r in rows])
    out = {}
    for m, thresholds in (("ASI", (1.0, 2.0, 5.0, 10.0)), ("TED-AI", (0.75,))):
        y = np.array([float(r[m]) for r in rows])
        out[m] = {"share_le": {str(t): float(np.interp(t, x, y)) for t in thresholds}}
    with open(pub / "ac_unconditional_time_until_statistics.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["milestone_name"] in out:
                out[r["milestone_name"]].update({k: float(r[k]) for k in ("p10", "p50", "p90")},
                                                n_with_ac=int(r["total_rollouts"]), num_reached=int(r["num_achieved"]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=HERE / ".upstream", help="upstream checkout from fetch_upstream.sh")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sweep")
    ro = sub.add_parser("rollouts")
    ro.add_argument("--preset", choices=sorted(R.PRESETS), required=True)
    ro.add_argument("-n", "--num-samples", type=int, default=400)
    ro.add_argument("--kappas", nargs="+", default=[_k(k) for k in ROLLOUT_KAPPAS])
    ro.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    ro.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    args.src = args.src.resolve()
    return {"sweep": cmd_sweep, "rollouts": cmd_rollouts}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
