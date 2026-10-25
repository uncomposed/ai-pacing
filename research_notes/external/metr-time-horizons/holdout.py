"""Retrospective rolling-origin holdout of METR frontier time horizons against B-FLAT and B-LOGLINEAR.

    python holdout.py            # writes results/holdout.json and results/holdout.md
    python holdout.py --check    # recompute and compare with the committed results (used by the tests)

Implements holdout_protocol.yaml exactly; read that first. Needs only the committed data/observations.csv
(no network) and numpy. Scoring helpers come from tools/evidence_tool.py (the shared protocol, #8).
Everything here is RETROSPECTIVE: the outcomes were public before the protocol was written.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import importlib.util
import json
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SAT_MIN = 960.0


def _evidence_tool():
    spec = importlib.util.spec_from_file_location("evidence_tool", ROOT / "tools/evidence_tool.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ET = _evidence_tool()


def load_protocol() -> dict:
    return ET.load_yaml(HERE / "holdout_protocol.yaml")


def d(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def load_observations(path: pathlib.Path = HERE / "data/observations.csv") -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k in ("p50_min", "p80_min"):
            r[k] = float(r[k])
        r["_avail"] = d(r["available"])
        r["_rel"] = d(r["model_release_date"])
    return rows


# ------------------------------------------------------------------------------------------ information sets


def info_set(rows: list[dict], suite: str, t: dt.date, nosat: bool = False) -> dict[str, dict]:
    """model_key -> its latest row available on or before t (the value public at t)."""
    out: dict[str, dict] = {}
    for r in rows:
        if r["suite"] == suite and r["_avail"] <= t:
            cur = out.get(r["model_key"])
            if cur is None or r["_avail"] > cur["_avail"]:
                out[r["model_key"]] = r
    if nosat:
        out = {k: v for k, v in out.items() if v["p50_min"] <= SAT_MIN}
    return out


def latest_values(rows: list[dict], suite: str) -> dict[str, dict]:
    return info_set(rows, suite, dt.date.max)


def first_available(rows: list[dict], suite: str) -> dict[str, dt.date]:
    out: dict[str, dt.date] = {}
    for r in rows:
        if r["suite"] == suite:
            out[r["model_key"]] = min(out.get(r["model_key"], dt.date.max), r["_avail"])
    return out


def frontier(info: dict[str, dict], metric: str) -> float:
    return max(r[metric] for r in info.values())


def month_ends(start: dt.date, end: dt.date) -> list[dt.date]:
    out, y, m = [], start.year, start.month
    while True:
        nxt = dt.date(y + (m == 12), m % 12 + 1, 1)
        me = nxt - dt.timedelta(days=1)
        if me > end:
            return out
        if me >= start:
            out.append(me)
        y, m = nxt.year, nxt.month


# ------------------------------------------------------------------------------------------ t quantile


def t_ppf(p: float, df: int) -> float:
    """Student t quantile by bisection on a Simpson-integrated density (no scipy)."""
    c = math.exp(math.lgamma((df + 1) / 2) - math.lgamma(df / 2)) / math.sqrt(df * math.pi)

    def cdf(x: float) -> float:
        n = 2000
        h = x / n
        s = sum((1 if i in (0, n) else (4 if i % 2 else 2)) * c * (1 + (i * h) ** 2 / df) ** (-(df + 1) / 2)
                for i in range(n + 1))
        return 0.5 + s * h / 3

    lo, hi = 0.0, 50.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if cdf(mid) < p else (lo, mid)
    return (lo + hi) / 2


# ------------------------------------------------------------------------------------------ baselines


def sota_points(info: dict[str, dict], metric: str, from_date: dt.date | None = None) -> list[tuple[dt.date, float]]:
    """Frontier-advancing models by release date, as METR's get_sota_agents (ties kept). The ranking is by
    p50 in METR's code; we rank by the series' own metric so the p80 series uses its own frontier."""
    pts = sorted((r["_rel"], r[metric]) for r in info.values() if from_date is None or r["_rel"] >= from_date)
    out, best = [], -math.inf
    for day in sorted({p[0] for p in pts}):
        vals = [v for dd, v in pts if dd == day]
        best = max(best, max(vals))
        out += [(day, v) for v in vals if v >= best]
    return out


def b_flat(rows, suite, metric, c, target, nosat, first_date):
    f_c = frontier(info_set(rows, suite, c, nosat), metric)
    h = (target - c).days
    changes = []
    for s in month_ends(first_date, c):
        if s + dt.timedelta(days=h) <= c and info_set(rows, suite, s, nosat):
            changes.append(math.log(frontier(info_set(rows, suite, s + dt.timedelta(days=h), nosat), metric))
                           - math.log(frontier(info_set(rows, suite, s, nosat), metric)))
    interval = None
    if len(changes) >= 3:
        q10, q90 = np.quantile(changes, [0.1, 0.9])
        interval = [f_c * math.exp(q10), f_c * math.exp(q90)]
    return {"point": f_c, "interval80": interval, "n_changes": len(changes)}


def b_loglinear(rows, suite, metric, c, target, nosat, from_date=None, lag_zero=False):
    info = info_set(rows, suite, c, nosat)
    fa = first_available(rows, suite)
    # Declared rule: median publication lag over the information set. POSTHOC-LAG0 sets it to 0 (see README).
    lag = 0.0 if lag_zero else float(np.median([(fa[k] - r["_rel"]).days for k, r in info.items()]))
    x0 = (target - dt.timedelta(days=lag)).toordinal()
    pts = sota_points(info, metric, from_date)
    x = np.array([p[0].toordinal() for p in pts], float)
    y = np.log([p[1] for p in pts])
    n = len(pts)
    if n < 2 or np.ptp(x) == 0:
        return {"point": None, "interval80": None, "n": n, "lag_days": lag}
    slope, icpt = np.polyfit(x, y, 1)
    pred = icpt + slope * x0
    interval = None
    if n >= 3:
        resid = y - (icpt + slope * x)
        s = math.sqrt(float(resid @ resid) / (n - 2))
        se = s * math.sqrt(1 + 1 / n + (x0 - x.mean()) ** 2 / float(((x - x.mean()) ** 2).sum()))
        tq = t_ppf(0.9, n - 2)
        interval = [math.exp(pred - tq * se), math.exp(pred + tq * se)]
    return {"point": math.exp(pred), "interval80": interval, "n": n, "lag_days": lag,
            "doubling_days": math.log(2) / slope if slope > 0 else None, "at_date": dt.date.fromordinal(int(round(x0))).isoformat()}


def score(fc: dict, y: float) -> dict:
    if fc["point"] is None:
        return {"abslogerr": None, "interval80": None, "covered80": None}
    out = {"abslogerr": ET.abs_log_error(fc["point"], y), "interval80": None, "covered80": None}
    if fc["interval80"]:
        lo, hi = fc["interval80"]
        out["interval80"] = ET.interval_score(math.log(lo), math.log(hi), math.log(y), 0.2)
        out["covered80"] = bool(lo <= y <= hi)
    return out


# ------------------------------------------------------------------------------------------ run


def run(protocol: dict, rows: list[dict], horizon: int, nosat: bool = False, from2023: bool = False,
        lag_zero: bool = False) -> list[dict]:
    out = []
    for ser in protocol["series"]:
        suite, metric = ser["suite"], ser["metric"]
        first_date = min(r["_avail"] for r in rows if r["suite"] == suite)
        last = d(protocol["last_date"][suite])
        latest = latest_values(rows, suite)
        for cs in protocol["cutoffs"][suite]:
            c = d(cs)
            target = c + dt.timedelta(days=horizon)
            if target > last:
                continue
            fl = b_flat(rows, suite, metric, c, target, nosat, first_date)
            ll = b_loglinear(rows, suite, metric, c, target, nosat, dt.date(2023, 1, 1) if from2023 else None, lag_zero)
            known = info_set(rows, suite, target, nosat)
            y_first = frontier(known, metric)
            y_latest = max(latest[k][metric] for k in known if not (nosat and latest[k]["p50_min"] > SAT_MIN))
            recs = sorted({r["record_id"] for r in rows if r["suite"] == suite and r["_avail"] <= c})
            out.append({
                "suite": suite, "metric": metric, "cutoff": cs, "target_date": target.isoformat(),
                "inputs": recs, "observed_first_published": y_first, "observed_latest_vintage": y_latest,
                "B-FLAT": fl, "B-LOGLINEAR": ll,
                "scores": {res: {b: score(fc, y) for b, fc in (("B-FLAT", fl), ("B-LOGLINEAR", ll))}
                           for res, y in (("first_published", y_first), ("latest_vintage", y_latest))},
            })
    return out


def summarize(fcs: list[dict]) -> dict:
    out: dict = {}
    for f in fcs:
        for res, by in f["scores"].items():
            for b, s in by.items():
                key = f"{f['suite']}|{f['metric']}|{res}|{b}"
                a = out.setdefault(key, {"n": 0, "abslogerr": [], "interval80": [], "covered80": []})
                a["n"] += 1
                for k in ("abslogerr", "interval80", "covered80"):
                    if s[k] is not None:
                        a[k].append(float(s[k]))
    return {k: {"n": v["n"],
                "mean_abslogerr": (float(np.mean(v["abslogerr"])) if v["abslogerr"] else None),
                "n_intervals": len(v["interval80"]),
                "mean_interval80": (float(np.mean(v["interval80"])) if v["interval80"] else None),
                "coverage80": (float(np.mean(v["covered80"])) if v["covered80"] else None)}
            for k, v in sorted(out.items())}


def verdict(summ: dict, summ182: dict) -> dict:
    checks = {}
    for name, s in (("H91", summ), ("H182", summ182)):
        for suite in ("TH1.0", "TH1.1"):
            fl = s.get(f"{suite}|p50_min|first_published|B-FLAT", {}).get("mean_abslogerr")
            ll = s.get(f"{suite}|p50_min|first_published|B-LOGLINEAR", {}).get("mean_abslogerr")
            checks[f"{name} {suite}"] = None if fl is None or ll is None else bool(ll < fl)
    ok = all(v is True for v in checks.values())
    return {"checks": checks, "statement": "B-LOGLINEAR beats B-FLAT" if ok else "not established"}


def compute() -> dict:
    protocol = load_protocol()
    rows = load_observations()
    h = int(protocol["horizon_days"])
    main_fc = run(protocol, rows, h)
    sens = {"H182": run(protocol, rows, 182), "NOSAT": run(protocol, rows, h, nosat=True),
            "FROM2023": run(protocol, rows, h, from2023=True)}
    # Added AFTER seeing the declared results (not part of the declared protocol): the declared lag rule
    # measures the lag over the whole information set, which is dominated by old models first scored long
    # after release, so it evaluates the trend more than a year in the past. Kept separate; never in the verdict.
    posthoc = {"POSTHOC-LAG0": run(protocol, rows, h, lag_zero=True),
               "POSTHOC-LAG0-H182": run(protocol, rows, 182, lag_zero=True)}
    summ = summarize(main_fc)
    sens_summ = {k: summarize(v) for k, v in sens.items()}
    post_summ = {k: summarize(v) for k, v in posthoc.items()}
    return {"label": "retrospective", "protocol": "holdout_protocol.yaml", "horizon_days": h,
            "forecasts": main_fc, "summary": summ,
            "sensitivity_summaries": sens_summ,
            "verdict": verdict(summ, sens_summ["H182"]),
            "posthoc_forecasts": posthoc["POSTHOC-LAG0"], "posthoc_summaries": post_summ,
            "posthoc_verdict_not_preregistered": verdict(post_summ["POSTHOC-LAG0"], post_summ["POSTHOC-LAG0-H182"])}


def _fmt(x, nd=3):
    return "n/a" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def to_markdown(res: dict) -> str:
    L = ["# METR frontier time horizon: retrospective rolling-origin holdout", "",
         "Generated by `holdout.py` from `data/observations.csv` under `holdout_protocol.yaml`. **Retrospective**: every",
         "outcome was public before the protocol was written. Not a forecast and not empirical validation of any model;",
         "it measures how two simple baselines would have done with the information then public.", "",
         f"Pre-declared verdict (p50, both suites, horizons 91 and 182 days, first-published resolution): "
         f"**{res['verdict']['statement']}**.", ""]
    L += ["| check | B-LOGLINEAR lower mean abs log error? |", "|---|---|"]
    L += [f"| {k} | {_fmt(v)} |" for k, v in res["verdict"]["checks"].items()]
    L += ["", "## Summary (horizon 91 days)", "",
          "Mean absolute natural-log error (0.69 = a factor of 2), mean 80% interval score on the log scale, and 80% coverage.",
          "", "| suite | metric | resolution | baseline | origins | mean abs log err | intervals | mean IS80 | coverage80 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for k, v in res["summary"].items():
        L.append("| " + " | ".join(k.split("|")) + f" | {v['n']} | {_fmt(v['mean_abslogerr'])} | {v['n_intervals']} | "
                 f"{_fmt(v['mean_interval80'])} | {_fmt(v['coverage80'], 2)} |")
    blocks = [(f"Sensitivity {k}", v) for k, v in res["sensitivity_summaries"].items()]
    blocks += [(f"Post hoc {k} (not pre-registered)", v) for k, v in res["posthoc_summaries"].items()]
    for name, summ in blocks:
        L += ["", f"## {name} (first-published resolution)", "",
              "| suite | metric | baseline | origins | mean abs log err | coverage80 |", "|---|---|---|---|---|---|"]
        for k, v in summ.items():
            s, m, r, b = k.split("|")
            if r == "first_published":
                L.append(f"| {s} | {m} | {b} | {v['n']} | {_fmt(v['mean_abslogerr'])} | {_fmt(v['coverage80'], 2)} |")
    L += ["", "## Every forecast (horizon 91 days)", "",
          "| suite | metric | cutoff | target date | observed (first pub.) | observed (latest) | flat | flat 80% | loglinear | loglinear 80% | trend pts |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for f in res["forecasts"]:
        fl, ll = f["B-FLAT"], f["B-LOGLINEAR"]
        iv = lambda i: "n/a" if not i else f"[{i[0]:.1f}, {i[1]:.1f}]"
        L.append(f"| {f['suite']} | {f['metric']} | {f['cutoff']} | {f['target_date']} | {f['observed_first_published']:.1f} | "
                 f"{f['observed_latest_vintage']:.1f} | {fl['point']:.1f} | {iv(fl['interval80'])} | "
                 f"{_fmt(ll['point'], 1)} | {iv(ll['interval80'])} | {ll['n']} |")
    pv = res["posthoc_verdict_not_preregistered"]
    L += ["", "## Post hoc: B-LOGLINEAR evaluated at the target date (lag 0)", "",
          "Added after the declared results were seen. The declared rule set the lag to the median, over the whole",
          "information set, of first availability minus release date. That set is dominated by old models first scored",
          "long after release (TH1.0 paper models, TH1.1 re-runs), so the trend was read off more than a year in the",
          "past. This variant reads it at the target date, as METR's own extrapolations do. It is a diagnosis of the",
          "declared design, not a test: same rule applied post hoc gives "
          f"**{pv['statement']}** ({', '.join(f'{k}: {_fmt(v)}' for k, v in pv['checks'].items())}).", "",
          "| suite | metric | cutoff | observed (first pub.) | flat | loglinear (lag 0) | loglinear 80% |",
          "|---|---|---|---|---|---|---|"]
    for f in res["posthoc_forecasts"]:
        ll = f["B-LOGLINEAR"]
        iv = "n/a" if not ll["interval80"] else f"[{ll['interval80'][0]:.1f}, {ll['interval80'][1]:.1f}]"
        L.append(f"| {f['suite']} | {f['metric']} | {f['cutoff']} | {f['observed_first_published']:.1f} | "
                 f"{f['B-FLAT']['point']:.1f} | {_fmt(ll['point'], 1)} | {iv} |")
    L += ["", "Units: minutes of human expert time on the suite's tasks (source-native). Origins overlap, so the",
          "scores are serially dependent; with 5 to 7 origins per series they are descriptive, not a significance test.", ""]
    return "\n".join(L)


def _plain(x):
    return json.loads(json.dumps(x, sort_keys=True, default=str))


def close(a, b, rel: float = 1e-9) -> bool:
    """Structural equality with floats compared to a relative tolerance (platform float noise only)."""
    a, b = _plain(a), _plain(b)

    def eq(x, y):
        if isinstance(x, dict):
            return isinstance(y, dict) and x.keys() == y.keys() and all(eq(x[k], y[k]) for k in x)
        if isinstance(x, list):
            return isinstance(y, list) and len(x) == len(y) and all(eq(u, v) for u, v in zip(x, y))
        if isinstance(x, float) or isinstance(y, float):
            return isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) \
                and abs(x - y) <= rel * max(1.0, abs(x), abs(y))
        return x == y
    return eq(a, b)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="compare with the committed results instead of writing")
    a = ap.parse_args()
    res = compute()
    jpath, mpath = HERE / "results/holdout.json", HERE / "results/holdout.md"
    if a.check:
        committed = json.loads(jpath.read_text())
        if not close(committed, res) or mpath.read_text() != to_markdown(res):
            sys.exit("holdout: recomputed results differ from the committed results/holdout.{json,md}")
        print(f"holdout: {len(res['forecasts'])} retrospective forecasts reproduce the committed results; "
              f"verdict: {res['verdict']['statement']}")
        return
    jpath.parent.mkdir(exist_ok=True)
    jpath.write_text(json.dumps(res, indent=1, sort_keys=True, default=str) + "\n")
    mpath.write_text(to_markdown(res))
    print(f"wrote {jpath} and {mpath}; verdict: {res['verdict']['statement']}")


if __name__ == "__main__":
    main()
