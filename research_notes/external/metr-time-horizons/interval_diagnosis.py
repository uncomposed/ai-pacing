"""Why do METR's published TH1.1 95% bootstrap intervals differ from what their public code gives? (#57)

    python interval_diagnosis.py run --cache .cache --out .cache/diag          # about 40 minutes on 4 cores
    python interval_diagnosis.py summarize --cache .cache --out .cache/diag --json results/interval_diagnosis.json

`run` bootstraps the TH1.1 headline data (METR's runs.jsonl at 52cb829) under a list of named configurations,
with the independent numpy implementation (`horizon_fit.py`, which draws the same index sets as METR's code
and agrees with it to 0.18% on the intervals). Each configuration changes one thing from METR's recorded
settings: the seed stream, the number of replicates, the row order of the input, the regularization, the
weights, the hierarchy, or the run vintage. `summarize` compares each with METR's published intervals
and with the Monte Carlo noise measured from the seed-stream configurations. It does not tune anything to
match: every configuration is declared below before it is run, and the published intervals are only read.

What the comparison asks. Published endpoints are compared as log(ours / published) over the 80 endpoints
(20 agents x p50, p80 x 2.5%, 97.5%). If the published intervals are another draw of the same procedure, their
differences from any one of our seed streams are Monte Carlo noise: of size sqrt(2) times the standard error
of an endpoint (z, with that standard error taken across our independent seed streams). A change of setting
that moves intervals systematically shows as a z far above that, or as a signed shift of the interval width.
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import pathlib
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import horizon_fit as hf  # noqa: E402

PIN = "52cb829c7a2efb2d659285c4b1768d191d97f8d2"
N_SEED_STREAMS = 12
SEED_STRIDE = 100_000  # stream k uses seeds 42 + k * stride + i: disjoint from METR's 42 + i for k >= 1

# name -> settings. Everything not listed is METR's recorded setting (dvc.lock: 1000 replicates, seed 42 + i,
# regularization 1e-5, invsqrt_task_weight, task family -> task -> run, th11_2026-03-05 runs, file row order).
CONFIGS: dict[str, dict] = {"base": {}}
for k in range(1, N_SEED_STREAMS):
    CONFIGS[f"seed{k}"] = {"seed0": 42 + k * SEED_STRIDE}
CONFIGS["n10000"] = {"n": 10_000}                 # reference stream: 10 consecutive blocks starting at METR's seed 42
CONFIGS["order_sorted"] = {"order": "sorted"}     # same seeds, runs sorted by (agent, task, run id)
CONFIGS["order_reversed"] = {"order": "reversed"}
CONFIGS["order_shuffle1"] = {"order": "shuffle:1"}
CONFIGS["order_shuffle2"] = {"order": "shuffle:2"}
CONFIGS["reg_0.1"] = {"reg": 0.1}                 # pre-correction regularization, bootstrap only
CONFIGS["weights_equal"] = {"weight": "equal_task_weight"}
CONFIGS["levels_tr"] = {"levels": "tr"}
CONFIGS["levels_ft"] = {"levels": "ft"}
CONFIGS["levels_f"] = {"levels": "f"}
CONFIGS["levels_t"] = {"levels": "t"}
CONFIGS["levels_r"] = {"levels": "r"}
CONFIGS["vintage_0212"] = {"vintage": "th11_2026-02-12"}
CONFIGS["vintage_0130"] = {"vintage": "th11_2026-01-30"}
CONFIGS["vintage_0212_reg0.1"] = {"vintage": "th11_2026-02-12", "reg": 0.1}
CONFIGS["n100"] = {"n": 100}
CONFIGS["n500"] = {"n": 500}


def _setting(cfg: dict) -> dict:
    return {"n": 1000, "seed0": 42, "reg": 1e-5, "weight": "invsqrt_task_weight", "levels": "ftr",
            "vintage": "th11_2026-03-05", "order": "file", **cfg}


_RUNS: hf.Runs | None = None
_SET: dict = {}


def _load(cache: pathlib.Path, s: dict) -> hf.Runs:
    runs = hf.load_runs(str(cache / "vintages" / f"{s['vintage']}.jsonl"), weight_col=s["weight"])
    o = s["order"]
    if o == "file":
        return runs
    if o == "sorted":
        idx = np.lexsort((runs.run_id.astype(str), runs.task_id.astype(str), runs.agent.astype(str)))
    elif o == "reversed":
        idx = np.arange(len(runs))[::-1]
    elif o.startswith("shuffle:"):
        idx = np.random.default_rng(int(o.split(":")[1])).permutation(len(runs))
    else:
        raise ValueError(o)
    return runs.take(idx)


def _one(b: int) -> np.ndarray:
    runs, s = _RUNS, _SET
    rng = np.random.default_rng(s["seed0"] + b)
    sample = runs.take(hf.bootstrap_indices(runs, rng, s["levels"]))
    agents = sorted(set(runs.agent))
    out = np.full((len(agents), 2), np.nan)
    for j, a in enumerate(agents):
        m = sample.agent == a
        y = sample.score[m]
        if m.sum() == 0 or len(np.unique(y)) < 2:
            continue
        f = hf.fit_logistic(np.log2(sample.human_minutes[m]), y, sample.weight[m], s["reg"])
        out[j] = [f.horizon(0.5), f.horizon(0.8)]
    return out


def run_config(cache: pathlib.Path, name: str, out: pathlib.Path, procs: int) -> None:
    global _RUNS, _SET
    dest = out / f"{name}.npz"
    if dest.exists():
        print(f"{name}: present, skipped")
        return
    s = _setting(CONFIGS[name])
    _RUNS, _SET = _load(cache, s), s
    t0 = time.time()
    with mp.get_context("fork").Pool(procs) as pool:
        res = pool.map(_one, range(s["n"]), chunksize=10)
    arr = np.stack(res)  # (n, agents, 2)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(dest, horizons=arr, agents=np.array(sorted(set(_RUNS.agent)), dtype=str),
                        settings=json.dumps(s))
    print(f"{name}: {s['n']} replicates in {time.time() - t0:.0f}s", flush=True)


# ---------------------------------------------------------------------------------------------


def _alias_keys(path: pathlib.Path) -> dict[str, str]:
    overrides = {"flamingo_2": "gpt_5_3_codex"}
    d = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            d[r["alias"]] = overrides.get(r["model"], r["model"])
    return d


def endpoints(arr: np.ndarray) -> np.ndarray:
    """(agents, 2, 2) array of the 2.5% and 97.5% quantiles (linear interpolation, ignoring NaN as upstream's
    np.nanquantile does) of each agent's p50 and p80 horizons."""
    q = np.nanquantile(arr, [0.025, 0.975], axis=0)  # (2, agents, 2)
    return np.transpose(q, (1, 2, 0))              # (agents, percent, bound)


def published_endpoints(cache: pathlib.Path, agents: list[str]) -> np.ndarray:
    import yaml
    pub = yaml.safe_load((cache / "metr.org/benchmark_results_1_1.yaml").read_text())["results"]
    keys = _alias_keys(cache / "vintages/th11_2026-03-05.jsonl")
    out = np.full((len(agents), 2, 2), np.nan)
    for i, a in enumerate(agents):
        if a not in keys:
            continue
        m = pub[keys[a]]["metrics"]
        for j, n in enumerate(("p50", "p80")):
            out[i, j] = [m[f"{n}_horizon_length"]["ci_low"], m[f"{n}_horizon_length"]["ci_high"]]
    return out


def _stats(d: np.ndarray, se: np.ndarray | None) -> dict:
    d = d[np.isfinite(d)]
    r = {"n_endpoints": int(d.size), "median_abs_log_ratio": float(np.median(np.abs(d))),
         "max_abs_log_ratio": float(np.max(np.abs(d))), "rms_log_ratio": float(np.sqrt(np.mean(d ** 2)))}
    return r


def doubling_inputs(cache: pathlib.Path, agents: list[str]) -> tuple[list[int], np.ndarray, np.ndarray]:
    """The agents on METR's from-2023 frontier trend (upstream get_sota_agents, ties kept) with their release
    ordinals and the published p50 point values, as the published doubling-time interval uses them."""
    import datetime as dt
    import yaml
    dates = yaml.safe_load((cache / "vintages/release_dates_2026-03-05.yaml").read_text())["date"]
    pub = yaml.safe_load((cache / "metr.org/benchmark_results_1_1.yaml").read_text())["results"]
    keys = _alias_keys(cache / "vintages/th11_2026-03-05.jsonl")
    rows = sorted((dt.date.fromisoformat(str(dates[a])), a, pub[keys[a]]["metrics"]["p50_horizon_length"]["estimate"])
                  for a in agents if a in keys and dt.date.fromisoformat(str(dates[a])) >= dt.date(2023, 1, 1))
    best, sota = -math.inf, []
    for day in sorted({r[0] for r in rows}):
        on = [r for r in rows if r[0] == day]
        best = max(best, max(r[2] for r in on))
        sota += [r for r in on if r[2] >= best]
    idx = [agents.index(r[1]) for r in sota]
    return idx, np.array([r[0].toordinal() for r in sota], float), np.array([r[2] for r in sota])


def doubling_ci(horizons: np.ndarray, idx: list[int], days: np.ndarray) -> tuple[float, float, int]:
    """95% interval of the doubling time (days) over bootstrap replicates, as upstream's
    compute_bootstrap_confidence_region: per replicate, OLS of ln p50 on release date over the frontier agents
    (replicates with fewer than two valid p50 are skipped, non-positive doubling times dropped)."""
    out = []
    for r in horizons[:, idx, 0]:
        ok = np.isfinite(r) & (r >= 1e-3)
        if ok.sum() < 2:
            continue
        slope = np.polyfit(days[ok], np.log(r[ok]), 1)[0]
        if math.log(2) / slope > 0:
            out.append(math.log(2) / slope)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), len(out)


def summarize(cache: pathlib.Path, out: pathlib.Path) -> dict:
    sets = {p.stem: np.load(p) for p in sorted(out.glob("*.npz"))}
    base = sets["base"]
    own = cache / "upstream_bootstrap_th11.csv"
    if own.exists():  # METR's own code run here (run_upstream.py), as one more set of replicates
        import csv
        with own.open(encoding="utf-8") as fh:
            tab = list(csv.DictReader(fh))
        names_b = [str(x) for x in base["agents"]]
        arr = np.full((len(tab), len(names_b), 2), np.nan)
        for j, a in enumerate(names_b):
            for k, nm in enumerate(("p50", "p80")):
                if f"{a}_{nm}" in tab[0]:
                    arr[:, j, k] = [float(r[f"{a}_{nm}"]) if r[f"{a}_{nm}"] != "" else np.nan for r in tab]
        sets["metr_code_here"] = {"horizons": arr, "agents": base["agents"],
                                  "settings": json.dumps({**_setting({}), "source": "METR's code (run_upstream.py), numpy 2.4.1, scikit-learn 1.8.0"})}
    agents = [str(a) for a in base["agents"]]
    keep = [i for i, a in enumerate(agents) if a != "human"]
    agents = [agents[i] for i in keep]
    pub = published_endpoints(cache, [str(a) for a in base["agents"]])[keep]
    ep = {}
    for k, v in sets.items():  # align by agent name: other vintages have other agent lists
        e = endpoints(v["horizons"])
        names = [str(x) for x in v["agents"]]
        ep[k] = np.stack([e[names.index(a)] if a in names else np.full((2, 2), np.nan) for a in agents])

    streams = [k for k in ["base"] + [f"seed{i}" for i in range(1, N_SEED_STREAMS)] if k in ep]
    logs = np.log(np.stack([ep[k] for k in streams]))             # (S, agents, 2, 2)
    se = logs.std(axis=0, ddof=1) if len(streams) > 2 else None   # Monte Carlo SE of one stream's endpoint
    ref = np.log(ep["n10000"]) if "n10000" in ep else logs.mean(axis=0)

    res: dict = {"upstream_commit": PIN, "streams": streams, "agents": agents,
                 "mc_se_log": {"median": float(np.median(se)), "max": float(se.max())} if se is not None else None,
                 "configs": {}}
    for name, e in ep.items():
        d = np.log(e) - np.log(pub)
        row = _stats(d, se)
        row["settings"] = json.loads(str(sets[name]["settings"]))
        if se is not None:
            z = d / se
            row["rms_z_vs_published"] = float(np.sqrt(np.nanmean(z ** 2)))
            row["max_abs_z_vs_published"] = float(np.nanmax(np.abs(z)))
        # Width bias: mean over agents/percents of log(hi/lo) ours minus published (positive: ours wider).
        row["mean_log_width_ratio"] = float(np.nanmean(np.log(e[..., 1] / e[..., 0]) - np.log(pub[..., 1] / pub[..., 0])))
        row["mean_signed_log_lower"] = float(np.nanmean(d[..., 0]))
        row["mean_signed_log_upper"] = float(np.nanmean(d[..., 1]))
        names = [str(x) for x in sets[name]["agents"]]
        if name in streams or name in ("n10000", "metr_code_here"):
            idx, days, _ = doubling_inputs(cache, names)
            lo_d, hi_d, nv = doubling_ci(sets[name]["horizons"], idx, days)
            row["doubling_ci"] = {"low": lo_d, "high": hi_d, "n_valid": nv}
        db = np.log(e) - np.log(ep["base"])
        row["median_abs_log_ratio_vs_base"] = float(np.nanmedian(np.abs(db)))
        row["max_abs_log_ratio_vs_base"] = float(np.nanmax(np.abs(db)))
        dr = np.log(e) - ref
        row["median_abs_log_ratio_vs_reference"] = float(np.nanmedian(np.abs(dr)))
        row["max_abs_log_ratio_vs_reference"] = float(np.nanmax(np.abs(dr)))
        res["configs"][name] = row

    # The published doubling-time interval is a second, aggregate probe of the same bootstrap.
    import yaml
    pubfile = yaml.safe_load((cache / "metr.org/benchmark_results_1_1.yaml").read_text())["doubling_time_in_days"]["from_2023_on"]
    names_all = [str(x) for x in base["agents"]]
    idx, days, p50s = doubling_inputs(cache, names_all)
    point = math.log(2) / np.polyfit(days, np.log(p50s), 1)[0]
    dstreams = [res["configs"][k]["doubling_ci"] for k in streams]
    res["doubling"] = {"published": [pubfile["ci_low"], pubfile["ci_high"]], "published_point": pubfile["point_estimate"],
                       "point_check": float(point), "n_frontier_agents": len(idx),
                       "streams_low_range": [min(x["low"] for x in dstreams), max(x["low"] for x in dstreams)],
                       "streams_high_range": [min(x["high"] for x in dstreams), max(x["high"] for x in dstreams)]}
    if "metr_code_here" in res["configs"]:
        m = res["configs"]["metr_code_here"]["doubling_ci"]
        res["doubling"]["metr_code_here"] = [m["low"], m["high"]]

    # Published against the same reference, for comparison with the seed streams' distances to it.
    dp = ref - np.log(pub)
    dpb = np.log(pub) - np.log(ep["base"])
    res["published_vs_base"] = {"median_abs_log_ratio": float(np.nanmedian(np.abs(dpb))), "max_abs_log_ratio": float(np.nanmax(np.abs(dpb)))}
    res["published_vs_reference"] = {"median_abs_log_ratio": float(np.median(np.abs(dp))),
                                     "max_abs_log_ratio": float(np.max(np.abs(dp))),
                                     "reference": "n10000" if "n10000" in ep else "mean of seed streams"}
    if len(streams) > 2:
        # Max and median |d| of published against each seed stream, against pairs of seed streams.
        pubd = [np.abs(np.log(ep[k]) - np.log(pub)) for k in streams]
        pair = [np.abs(logs[i] - logs[j]) for i in range(len(streams)) for j in range(i + 1, len(streams))]
        res["seed_streams"] = {
            "published_vs_stream": {"median_of_median": float(np.median([np.median(x) for x in pubd])),
                                    "median_of_max": float(np.median([x.max() for x in pubd])),
                                    "range_of_max": [float(min(x.max() for x in pubd)), float(max(x.max() for x in pubd))]},
            "stream_vs_stream": {"median_of_median": float(np.median([np.median(x) for x in pair])),
                                 "median_of_max": float(np.median([x.max() for x in pair])),
                                 "range_of_max": [float(min(x.max() for x in pair)), float(max(x.max() for x in pair))],
                                 "n_pairs": len(pair)},
        }
        # Rank of the published intervals among the streams, by max distance to the other streams.
        # Leave-one-out: distance of each stream and of the published set to the mean of the 11 other-stream endpoints.
        loo = []
        for i in range(len(streams)):
            others = np.delete(logs, i, axis=0).mean(axis=0)
            loo.append(float(np.sqrt(np.mean((logs[i] - others) ** 2))))
        mean_all = logs.mean(axis=0)
        pub_rms = float(np.sqrt(np.mean((np.log(pub) - mean_all) ** 2)))
        res["rms_to_mean_of_streams"] = {"streams_leave_one_out": loo, "published": pub_rms,
                                         "published_rank_from_closest": int(1 + sum(x < pub_rms for x in loo))}
    return res


def to_markdown(res: dict) -> str:
    L = ["# Why the published TH1.1 intervals differ from METR's public code (generated by `interval_diagnosis.py`)", "",
         "Log ratio = log(ours / published) over the 80 interval endpoints (20 agents x p50, p80 x two bounds), "
         "1000 replicates unless the configuration says otherwise. `rms z` divides each difference by the Monte Carlo "
         "standard error of that endpoint measured across independent seed streams; pure Monte Carlo noise "
         "between two independent streams gives about 1.41.", ""]
    mc = res.get("mc_se_log")
    if mc:
        L += [f"Monte Carlo standard error of one endpoint (log scale, from {len(res['streams'])} seed streams): "
              f"median {mc['median']:.3f}, max {mc['max']:.3f}.", ""]
    pv = res["published_vs_base"]
    L += [f"Published against `base` (METR's recorded seeds, independent fit): median {pv['median_abs_log_ratio']:.3f}, max {pv['max_abs_log_ratio']:.3f}. "
          "The last two columns give each configuration's distance to `base` for comparison.", "",
          "| configuration | settings changed | median abs | max abs | rms z | max abs z | mean log width, ours minus published | median to base | max to base |",
          "|---|---|---|---|---|---|---|---|---|"]
    default = _setting({})
    for name, r in res["configs"].items():
        ch = {k: v for k, v in r["settings"].items() if default.get(k) != v}
        z = f"{r['rms_z_vs_published']:.2f}" if "rms_z_vs_published" in r else ""
        zm = f"{r['max_abs_z_vs_published']:.1f}" if "max_abs_z_vs_published" in r else ""
        L.append(f"| {name} | {ch or 'none'} | {r['median_abs_log_ratio']:.3f} | {r['max_abs_log_ratio']:.3f} | {z} | {zm} | "
                 f"{r['mean_log_width_ratio']:+.3f} | {r['median_abs_log_ratio_vs_base']:.3f} | {r['max_abs_log_ratio_vs_base']:.3f} |")
    s = res.get("seed_streams")
    if s:
        L += ["", "Distances between interval sets, log scale (median over streams or pairs of the median and of the max over "
              "the 80 endpoints):", "",
              "| pair | median of medians | median of maxima | range of maxima |", "|---|---|---|---|",
              f"| published vs each seed stream | {s['published_vs_stream']['median_of_median']:.3f} | "
              f"{s['published_vs_stream']['median_of_max']:.3f} | {s['published_vs_stream']['range_of_max'][0]:.3f} to "
              f"{s['published_vs_stream']['range_of_max'][1]:.3f} |",
              f"| seed stream vs seed stream ({s['stream_vs_stream']['n_pairs']} pairs) | {s['stream_vs_stream']['median_of_median']:.3f} | "
              f"{s['stream_vs_stream']['median_of_max']:.3f} | {s['stream_vs_stream']['range_of_max'][0]:.3f} to "
              f"{s['stream_vs_stream']['range_of_max'][1]:.3f} |"]
    r = res.get("rms_to_mean_of_streams")
    if r:
        L += ["", f"RMS log distance to the mean of the streams: published {r['published']:.4f}; each stream, leave-one-out: "
              f"{min(r['streams_leave_one_out']):.4f} to {max(r['streams_leave_one_out']):.4f}. The published set ranks "
              f"{r['published_rank_from_closest']} of {len(r['streams_leave_one_out']) + 1} from the closest."]
    d = res.get("doubling")
    if d:
        L += ["", f"Doubling time since 2023, 95% interval from the bootstrap (published: {d['published'][0]:.3f} to {d['published'][1]:.3f} days; "
              f"point estimate {d['point_check']:.3f}, published {d['published_point']:.3f}). Seed streams: lower end {d['streams_low_range'][0]:.2f} to "
              f"{d['streams_low_range'][1]:.2f}, upper end {d['streams_high_range'][0]:.2f} to {d['streams_high_range'][1]:.2f}."
              + (f" METR's code run here: {d['metr_code_here'][0]:.2f} to {d['metr_code_here'][1]:.2f}." if d.get("metr_code_here") else "")]
    p = res["published_vs_reference"]
    L += ["", f"Published against the reference ({p['reference']}): median {p['median_abs_log_ratio']:.3f}, max {p['max_abs_log_ratio']:.3f}.", ""]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "summarize"])
    ap.add_argument("--cache", default=str(HERE / ".cache"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--json", default=None)
    ap.add_argument("--md", default=None)
    a = ap.parse_args()
    cache = pathlib.Path(a.cache)
    out = pathlib.Path(a.out or cache / "diag")
    if a.cmd == "run":
        for name in (a.only or list(CONFIGS)):
            run_config(cache, name, out, a.procs)
    else:
        res = summarize(cache, out)
        if a.json:
            pathlib.Path(a.json).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
        md = to_markdown(res)
        if a.md:
            pathlib.Path(a.md).write_text(md)
        print(md)


if __name__ == "__main__":
    main()
