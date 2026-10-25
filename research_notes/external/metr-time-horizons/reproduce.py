"""Reproduce METR's released TH1.1 time-horizon analysis and compare with METR's published numbers.

    bash fetch_sources.sh
    python reproduce.py [--cache .cache] [--bootstrap 1000] [--upstream results/upstream_th11.json]

Needs the cache (network) and pyyaml. Writes results/reproduction.json and results/reproduction.md.
The default run (point estimates, doubling times, revisions) takes seconds; --bootstrap 1000 takes about
two minutes. --upstream adds the output of run_upstream.py (METR's own code, run here).

Declared tolerances (set before comparing, except where the README says otherwise):
  point horizons (p50, p80)          relative |ours/published - 1| <= 1e-3  (scikit-learn's lbfgs stops at tol 1e-4)
  doubling times (from published p50) absolute <= 0.001 days (published values are rounded to 3 decimals)
  bootstrap CI endpoints              reported, not tested: see README "Discrepancies"
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import pathlib

import numpy as np
import yaml

import horizon_fit as hf

HERE = pathlib.Path(__file__).resolve().parent
TOL_REL = 1e-3
TOL_DT = 1e-3
OVERRIDES = {"flamingo_2": "gpt_5_3_codex"}


def _alias_keys(path: pathlib.Path) -> dict[str, str]:
    out = {}
    for line in path.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["alias"]] = OVERRIDES.get(r["model"], r["model"])
    return out


def compare_points(runs_path: pathlib.Path, published: dict, reg: float) -> list[dict]:
    runs = hf.load_runs(str(runs_path), exclude_agents=())
    keys = _alias_keys(runs_path)
    fits = hf.fit_agents(runs, reg, [a for a in set(runs.agent) if a != "human"])
    out = []
    for a, f in sorted(fits.items()):
        m = published[keys[a]]["metrics"]
        row = {"alias": a, "model_key": keys[a]}
        for p, name in ((0.5, "p50"), (0.8, "p80")):
            ours, pub = f.horizon(p), m[f"{name}_horizon_length"]["estimate"]
            row[name] = {"ours": ours, "published": pub, "rel_diff": ours / pub - 1}
        row["within_tolerance"] = bool(all(abs(row[n]["rel_diff"]) <= TOL_REL for n in ("p50", "p80")))
        out.append(row)
    return out


def doubling_times(published: dict, sat: float = 960.0) -> dict:
    """METR's published trend statistics, recomputed from the published p50 values: OLS of ln p50 on release
    date over frontier (SOTA) models, excluding p50 > 16 h (comment in benchmark_results_1_1.yaml)."""
    res = published["results"]

    def ols(pts):
        x = np.array([dt.date.fromisoformat(str(d)).toordinal() for d, _ in pts], float)
        return math.log(2) / np.polyfit(x, np.log([v for _, v in pts]), 1)[0]

    rows = sorted((str(v["release_date"]), v["metrics"]["p50_horizon_length"]["estimate"]) for v in res.values())
    best, sota = -math.inf, []
    for day in sorted({r[0] for r in rows if r[0] >= "2023-01-01"}):
        vals = [v for dd, v in rows if dd == day]
        best = max(best, max(vals))
        sota += [(day, v) for v in vals if v >= best]
    stitched = [(str(v["release_date"]), v["metrics"]["p50_horizon_length"]["estimate"])
                for v in res.values() if v["metrics"]["is_sota"]]
    pub = published["doubling_time_in_days"]
    out = {
        "from_2023_on": {"ours": ols([p for p in sota if p[1] <= sat]), "published": pub["from_2023_on"]["point_estimate"],
                         "ours_without_16h_exclusion": ols(sota)},
        "all_time_stitched": {"ours": ols([p for p in stitched if p[1] <= sat]),
                              "published": pub["all_time_stitched"]["point_estimate"],
                              "ours_without_16h_exclusion": ols(stitched)},
    }
    for v in out.values():
        v["abs_diff"] = v["ours"] - v["published"]
        v["within_tolerance"] = bool(abs(v["abs_diff"]) <= TOL_DT)
    return out


def bootstrap_cis(runs_path: pathlib.Path, published: dict, n: int) -> list[dict]:
    runs = hf.load_runs(str(runs_path), exclude_agents=())
    keys = _alias_keys(runs_path)
    bs = hf.bootstrap_horizons(runs, 1e-5, n)
    out = []
    for a in sorted(bs):
        if a == "human":
            continue
        m = published[keys[a]]["metrics"]
        row = {"alias": a}
        for j, name in enumerate(("p50", "p80")):
            lo, hi = np.nanquantile(bs[a][:, j], [0.025, 0.975])
            pl, ph = m[f"{name}_horizon_length"]["ci_low"], m[f"{name}_horizon_length"]["ci_high"]
            row[name] = {"ours": [float(lo), float(hi)], "published": [pl, ph],
                         "log_ratio": [math.log(lo / pl), math.log(hi / ph)]}
        out.append(row)
    return out


def revisions(obs_csv: pathlib.Path) -> list[dict]:
    """First-published (reconstructed, regularization 0.1) value against the latest published value, per model."""
    import csv
    rows = list(csv.DictReader(obs_csv.open(encoding="utf-8")))
    out = []
    for suite in ("TH1.0", "TH1.1"):
        by: dict[str, list[dict]] = {}
        for r in rows:
            if r["suite"] == suite:
                by.setdefault(r["model_key"], []).append(r)
        for k, rs in sorted(by.items()):
            rs.sort(key=lambda r: r["available"])
            if len(rs) > 1:
                f, l = rs[0], rs[-1]
                out.append({"suite": suite, "model_key": k, "first": {"available": f["available"], "p50": float(f["p50_min"]),
                                                                      "p80": float(f["p80_min"]), "source": f["value_source"]},
                            "latest": {"available": l["available"], "p50": float(l["p50_min"]), "p80": float(l["p80_min"]),
                                       "source": l["value_source"]},
                            "p50_ratio": float(l["p50_min"]) / float(f["p50_min"]),
                            "p80_ratio": float(l["p80_min"]) / float(f["p80_min"])})
    return out


def to_markdown(res: dict) -> str:
    L = ["# Reproduction of METR Time Horizon 1.1 (and 1.0) from public data", "",
         "Generated by `reproduce.py`. Source replication only: this checks that METR's published numbers follow",
         "from their released runs and method. It is not empirical validation of anything.", "",
         f"Pinned: eval-analysis-public `{res['upstream_commit']}`; published files sha256 in `sources.sha256`.", "",
         f"## TH1.1 headline point estimates (tolerance: relative {TOL_REL:g})", "",
         f"All within tolerance: **{res['th11_points_ok']}**. Max |relative difference|: {res['th11_points_maxrel']:.1e}.", "",
         "| agent (alias) | p50 ours | p50 published | rel. diff | p80 ours | p80 published | rel. diff |",
         "|---|---|---|---|---|---|---|"]
    for r in res["th11_points"]:
        L.append(f"| {r['alias']} | {r['p50']['ours']:.4f} | {r['p50']['published']:.4f} | {r['p50']['rel_diff']:+.1e} | "
                 f"{r['p80']['ours']:.4f} | {r['p80']['published']:.4f} | {r['p80']['rel_diff']:+.1e} |")
    L += ["", f"## TH1.0 point estimates, post-correction (same tolerance)", "",
          f"All within tolerance: **{res['th10_points_ok']}**. Max |relative difference|: {res['th10_points_maxrel']:.1e}"
          f" ({res['th10_points_worst']}).", ""]
    L += ["## Doubling times recomputed from the published p50 values (tolerance 0.001 days)", "",
          "| statistic | ours | published | difference | ours without the 16 h exclusion |", "|---|---|---|---|---|"]
    for k, v in res["doubling_times"].items():
        L.append(f"| {k} | {v['ours']:.3f} | {v['published']:.3f} | {v['abs_diff']:+.4f} | {v['ours_without_16h_exclusion']:.3f} |")
    if res.get("bootstrap"):
        b = res["bootstrap"]
        L += ["", f"## TH1.1 95% bootstrap intervals, independent implementation ({b['n']} replicates)", "",
              f"Median |log ratio| of endpoints to published: {b['median_abs_log_ratio']:.3f}; max {b['max_abs_log_ratio']:.3f}.", "",
              "| agent | p50 ours | p50 published | p80 ours | p80 published |", "|---|---|---|---|---|"]
        for r in b["rows"]:
            f = lambda v: f"[{v[0]:.2f}, {v[1]:.2f}]"
            L.append(f"| {r['alias']} | {f(r['p50']['ours'])} | {f(r['p50']['published'])} | {f(r['p80']['ours'])} | {f(r['p80']['published'])} |")
    if res.get("upstream"):
        u = res["upstream"]
        L += ["", f"## METR's own code run here ({u['versions']}, {u['n_bootstrap']} replicates)", "",
              f"Point estimates vs published, max |relative difference|: {u['max_rel_point']:.1e}. "
              f"CI endpoints vs published, max |log ratio|: {u['max_abs_log_ratio_ci']:.3f}.", ""]
        if "bootstrap_vs_upstream_max_abs_log_ratio" in res:
            L += [f"Independent bootstrap against METR's code run here (same draws), max |log ratio| of CI endpoints: "
                  f"{res['bootstrap_vs_upstream_max_abs_log_ratio']:.4f}. The published intervals are therefore not what "
                  "the public code gives on the public data; see README, Discrepancies.", ""]
    L += ["", "## Revisions: first public value (reconstructed) against latest published value", "",
          "| suite | model | first available | first p50 | latest available | latest p50 | p50 ratio | p80 ratio |",
          "|---|---|---|---|---|---|---|---|"]
    for r in res["revisions"]:
        L.append(f"| {r['suite']} | {r['model_key']} | {r['first']['available']} | {r['first']['p50']:.2f} | "
                 f"{r['latest']['available']} | {r['latest']['p50']:.2f} | {r['p50_ratio']:.3f} | {r['p80_ratio']:.3f} |")
    L.append("")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(HERE / ".cache"))
    ap.add_argument("--bootstrap", type=int, default=0)
    ap.add_argument("--upstream", default=None, help="JSON written by run_upstream.py")
    ap.add_argument("--outdir", default=str(HERE / "results"))
    a = ap.parse_args()
    cache = pathlib.Path(a.cache)
    pub11 = yaml.safe_load((cache / "metr.org/benchmark_results_1_1.yaml").read_text())
    pub10 = yaml.safe_load((cache / "metr.org/benchmark_results_1_0.yaml").read_text())
    p11 = compare_points(cache / "vintages/th11_2026-03-05.jsonl", pub11["results"], 1e-5)
    p10 = compare_points(cache / "vintages/th10_2026-03-05.jsonl", pub10["results"], 1e-5)
    rel = lambda rows: max(abs(r[n]["rel_diff"]) for r in rows for n in ("p50", "p80"))
    worst10 = max(p10, key=lambda r: max(abs(r[n]["rel_diff"]) for n in ("p50", "p80")))
    res: dict = {
        "upstream_commit": "52cb829c7a2efb2d659285c4b1768d191d97f8d2",
        "tolerances": {"point_rel": TOL_REL, "doubling_days_abs": TOL_DT},
        "th11_points": p11, "th11_points_ok": all(r["within_tolerance"] for r in p11), "th11_points_maxrel": rel(p11),
        "th10_points": p10, "th10_points_ok": all(r["within_tolerance"] for r in p10), "th10_points_maxrel": rel(p10),
        "th10_points_worst": worst10["alias"],
        "doubling_times": doubling_times(pub11),
        "revisions": revisions(HERE / "data/observations.csv"),
    }
    if a.bootstrap:
        rows = bootstrap_cis(cache / "vintages/th11_2026-03-05.jsonl", pub11["results"], a.bootstrap)
        lr = [abs(x) for r in rows for n in ("p50", "p80") for x in r[n]["log_ratio"]]
        res["bootstrap"] = {"n": a.bootstrap, "rows": rows, "median_abs_log_ratio": float(np.median(lr)),
                            "max_abs_log_ratio": float(max(lr))}
    if a.upstream:
        u = json.loads(pathlib.Path(a.upstream).read_text())
        keys = _alias_keys(cache / "vintages/th11_2026-03-05.jsonl")
        relp, lrs = [], []
        for alias, v in u["agents"].items():
            m = pub11["results"][keys[alias]]["metrics"]
            for n in ("p50", "p80"):
                relp.append(abs(v[n] / m[f"{n}_horizon_length"]["estimate"] - 1))
                if v.get(f"{n}q0.025") is not None:
                    lrs += [abs(math.log(v[f"{n}q0.025"] / m[f"{n}_horizon_length"]["ci_low"])),
                            abs(math.log(v[f"{n}q0.975"] / m[f"{n}_horizon_length"]["ci_high"]))]
        res["upstream"] = {"versions": u["versions"], "n_bootstrap": u["n_bootstrap"], "max_rel_point": max(relp),
                           "max_abs_log_ratio_ci": max(lrs) if lrs else float("nan"), "agents": u["agents"]}
    if a.bootstrap and a.upstream:
        u = res["upstream"]["agents"]
        res["bootstrap_vs_upstream_max_abs_log_ratio"] = max(
            abs(math.log(r[n]["ours"][i] / u[r["alias"]][f"{n}q{q}"]))
            for r in res["bootstrap"]["rows"] for n in ("p50", "p80") for i, q in ((0, "0.025"), (1, "0.975")))
    out = pathlib.Path(a.outdir)
    out.mkdir(exist_ok=True)
    (out / "reproduction.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    (out / "reproduction.md").write_text(to_markdown(res))
    print(f"TH1.1 points within {TOL_REL:g}: {res['th11_points_ok']} (max {res['th11_points_maxrel']:.1e}); "
          f"doubling times: {[v['within_tolerance'] for v in res['doubling_times'].values()]}")


if __name__ == "__main__":
    main()
