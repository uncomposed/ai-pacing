"""Per-model holdout of METR time horizons against B-FLAT, B-LOGLINEAR and B-COMPUTE (issue #56).

    python permodel.py              # writes results/permodel.json and results/permodel.md
    python permodel.py --check      # recompute and compare with the committed results (used by the tests)
    python permodel.py --registry   # print the FC-METR-PM-* entries for evidence/protocol.yaml

Implements permodel_protocol.yaml, which was committed on its own (DECLARED_COMMIT) before this file existed;
read that first. Offline: needs only data/observations.csv and numpy. Every forecast here is RETROSPECTIVE.
"""
from __future__ import annotations

import argparse
import datetime as dt
import functools
import hashlib
import json
import math
import pathlib
import sys

import numpy as np

import holdout as H

HERE = pathlib.Path(__file__).resolve().parent
ET = H.ET
PROTOCOL = HERE / "permodel_protocol.yaml"
# The commit that added permodel_protocol.yaml, before any scoring code or score existed, and the file's sha256.
DECLARED_COMMIT = "6cea9d0edf0c796995e61398be5ef4fc715c0902"
PROTOCOL_SHA256 = "608f966f9c578f2326bc8d7142c28fa5adc32c64f7331b5321edb43fbc9e9470"
CORRECTION = dt.date(2026, 3, 3)
METRICS = ("p50_min", "p80_min")
RESOLUTIONS = ("V-FIRST", "V-LATEST", "V-POSTFIX")
BASELINES = ("B-FLAT", "B-LOGLINEAR", "B-COMPUTE")
RULE_RESOLUTIONS = ("V-FIRST", "V-POSTFIX")
COMPUTE_RECORD = "EV-EPOCH-COMPUTE-TREND-2024"
t_ppf = functools.lru_cache(maxsize=None)(H.t_ppf)  # same values, computed once per df


def load_protocol() -> dict:
    return ET.load_yaml(PROTOCOL)


def is_postfix(row: dict) -> bool:
    return float(row["regularization"]) < 1e-3


def suite_rows(rows: list[dict], suite: str, nosat: bool) -> list[dict]:
    return [r for r in rows if r["suite"] == suite and not (nosat and r["p50_min"] > H.SAT_MIN)]


def targets(srows: list[dict]) -> list[dict]:
    """Models released on or after the suite's first publication date, in release order."""
    first = min(r["_avail"] for r in srows)
    by_model: dict[str, list[dict]] = {}
    for r in srows:
        by_model.setdefault(r["model_key"], []).append(r)
    out = []
    for k, rs in by_model.items():
        rs = sorted(rs, key=lambda r: r["_avail"])
        if rs[0]["_rel"] >= first:
            post = [r for r in rs if is_postfix(r)]
            out.append({"model_key": k, "alias": rs[0]["alias"] or k, "release": rs[0]["_rel"], "rows": rs,
                        "first": rs[0], "latest": rs[-1], "postfix": post[-1] if post else None})
    return sorted(out, key=lambda t: (t["release"], t["model_key"]))


def information_set(srows: list[dict], c: dt.date, exclude: str, res: str) -> dict[str, dict]:
    info: dict[str, dict] = {}
    for r in srows:
        if r["model_key"] != exclude and r["_avail"] <= c:
            cur = info.get(r["model_key"])
            if cur is None or r["_avail"] > cur["_avail"]:
                info[r["model_key"]] = r
    if res == "V-POSTFIX":
        post: dict[str, dict] = {}
        for r in srows:
            if r["model_key"] in info and is_postfix(r):
                cur = post.get(r["model_key"])
                if cur is None or r["_avail"] > cur["_avail"]:
                    post[r["model_key"]] = r
        info = post
    return info


# ------------------------------------------------------------------------------------------ baselines (points)


def flat(info: dict, metric: str) -> dict:
    return {"point": max(r[metric] for r in info.values())}


def loglinear(info: dict, metric: str, t: dt.date) -> dict:
    pts = H.sota_points(info, metric)
    n = len(pts)
    x = np.array([p[0].toordinal() for p in pts], float)
    y = np.log([p[1] for p in pts])
    if n < 2 or np.ptp(x) == 0:
        return {"point": None, "interval80": None, "n": n}
    slope, icpt = np.polyfit(x, y, 1)
    pred = icpt + slope * t.toordinal()
    interval = None
    if n >= 3:
        resid = y - (icpt + slope * x)
        s = math.sqrt(float(resid @ resid) / (n - 2))
        se = s * math.sqrt(1 + 1 / n + (t.toordinal() - x.mean()) ** 2 / float(((x - x.mean()) ** 2).sum()))
        tq = t_ppf(0.9, n - 2)
        interval = [math.exp(pred - tq * se), math.exp(pred + tq * se)]
    return {"point": math.exp(pred), "interval80": interval, "n": n,
            "doubling_days": math.log(2) / slope if slope > 0 else None}


def compute(info: dict, metric: str, t: dt.date, g: float) -> dict:
    f = max(r[metric] for r in info.values())
    t_f = max(r["_rel"] for r in info.values() if r[metric] == f)
    return {"point": f * g ** ((t - t_f).days / 365.25), "anchor_value": f, "anchor_release": t_f.isoformat(), "g": g}


def score(point, interval, y) -> dict:
    if point is None or y is None:
        return {"abslogerr": None, "interval80": None, "covered80": None}
    out = {"abslogerr": ET.abs_log_error(point, y), "interval80": None, "covered80": None}
    if interval:
        lo, hi = interval
        out["interval80"] = ET.interval_score(math.log(lo), math.log(hi), math.log(y), 0.2)
        out["covered80"] = bool(lo <= y <= hi)
    return out


# ------------------------------------------------------------------------------------------ run


def run(rows: list[dict], g: float, nosat: bool = False, min_info: int = 3) -> dict:
    forecasts, skipped = [], []
    for suite in ("TH1.0", "TH1.1"):
        srows = suite_rows(rows, suite, nosat)
        tg = targets(srows)
        for t in tg:
            c = t["release"]
            base = information_set(srows, c, t["model_key"], "V-FIRST")
            if len(base) < min_info:
                skipped.append({"suite": suite, "model_key": t["model_key"], "information_set": len(base)})
                continue
            outcomes = {"V-FIRST": t["first"], "V-LATEST": t["latest"], "V-POSTFIX": t["postfix"]}
            for metric in METRICS:
                fc = {"suite": suite, "metric": metric, "model_key": t["model_key"], "alias": t["alias"],
                      "cutoff": c.isoformat(), "first_available": t["first"]["available"],
                      "first_published_before_correction": t["first"]["_avail"] < CORRECTION,
                      "inputs": sorted({r["record_id"] for r in srows if r["_avail"] <= c and r["model_key"] != t["model_key"]}),
                      "resolution_record": t["first"]["record_id"], "by_resolution": {}}
                for res in RESOLUTIONS:
                    info = information_set(srows, c, t["model_key"], res)
                    out_row = outcomes[res]
                    y = None if out_row is None else out_row[metric]
                    if not info:
                        fc["by_resolution"][res] = {"observed": y, "n_info": 0}
                        continue
                    fc["by_resolution"][res] = {
                        "observed": y, "n_info": len(info),
                        "B-FLAT": flat(info, metric), "B-LOGLINEAR": loglinear(info, metric, c),
                        "B-COMPUTE": compute(info, metric, c, g)}
                forecasts.append(fc)
    _residual_intervals(forecasts)
    for f in forecasts:
        for res, r in f["by_resolution"].items():
            r["scores"] = {b: score(r[b]["point"], r[b].get("interval80"), r["observed"]) for b in BASELINES if b in r}
    return {"forecasts": forecasts, "skipped": skipped}


def _residual_intervals(forecasts: list[dict]) -> None:
    """B-FLAT and B-COMPUTE intervals: empirical 10/90% log residuals of earlier targets whose first-published
    outcome was public by the cutoff (same suite, metric, resolution, baseline); none with fewer than 3."""
    for f in forecasts:
        c = dt.date.fromisoformat(f["cutoff"])
        earlier = [j for j in forecasts if j is not f and j["suite"] == f["suite"] and j["metric"] == f["metric"]
                   and dt.date.fromisoformat(j["cutoff"]) <= c and dt.date.fromisoformat(j["first_available"]) <= c]
        for res, r in f["by_resolution"].items():
            for b in ("B-FLAT", "B-COMPUTE"):
                if b not in r:
                    continue
                logs = [math.log(j["by_resolution"][res]["observed"] / j["by_resolution"][res][b]["point"])
                        for j in earlier if b in j["by_resolution"].get(res, {})
                        and j["by_resolution"][res]["observed"] is not None]
                r[b]["n_residuals"] = len(logs)
                r[b]["interval80"] = None
                if len(logs) >= 3:
                    q10, q90 = np.quantile(logs, [0.1, 0.9])
                    p = r[b]["point"]
                    r[b]["interval80"] = [p * math.exp(q10), p * math.exp(q90)]


def summarize(forecasts: list[dict], group: str | None = None) -> dict:
    """Means per suite|metric|resolution|baseline. group: None, 'pre' or 'post' (first published before or on/after
    the 2026-03-03 correction)."""
    acc: dict = {}
    for f in forecasts:
        if group == "pre" and not f["first_published_before_correction"]:
            continue
        if group == "post" and f["first_published_before_correction"]:
            continue
        for res, r in f["by_resolution"].items():
            for b, s in r.get("scores", {}).items():
                a = acc.setdefault(f"{f['suite']}|{f['metric']}|{res}|{b}", {"n": 0, "abslogerr": [], "interval80": [], "covered80": []})
                if s["abslogerr"] is None:
                    continue
                a["n"] += 1
                for k in ("abslogerr", "interval80", "covered80"):
                    if s[k] is not None:
                        a[k].append(float(s[k]))
    return {k: {"n": v["n"],
                "mean_abslogerr": float(np.mean(v["abslogerr"])) if v["abslogerr"] else None,
                "n_intervals": len(v["interval80"]),
                "mean_interval80": float(np.mean(v["interval80"])) if v["interval80"] else None,
                "coverage80": float(np.mean(v["covered80"])) if v["covered80"] else None}
            for k, v in sorted(acc.items())}


def beats(summ: dict, x: str, y: str, summ_x: dict | None = None) -> dict:
    """x beats y only if x's mean abs log error is lower in every cell of the declared rule."""
    sx = summ_x or summ
    cells = {}
    for suite in ("TH1.0", "TH1.1"):
        for metric in METRICS:
            for res in RULE_RESOLUTIONS:
                ex = sx.get(f"{suite}|{metric}|{res}|{x}", {}).get("mean_abslogerr")
                ey = summ.get(f"{suite}|{metric}|{res}|{y}", {}).get("mean_abslogerr")
                cells[f"{suite} {metric} {res}"] = None if ex is None or ey is None else bool(ex < ey)
    return {"cells": cells, "beats": all(v is True for v in cells.values())}


def compute_all() -> dict:
    proto = load_protocol()
    rows = H.load_observations()
    g = float(proto["baselines"]["B-COMPUTE"]["g"])
    main = run(rows, g, min_info=int(proto["min_information_set"]))
    sens_runs = {"G36": run(rows, 3.6), "G49": run(rows, 4.9), "NOSAT": run(rows, g, nosat=True)}
    summ = summarize(main["forecasts"])
    sens = {k: summarize(v["forecasts"]) for k, v in sens_runs.items()}
    pairs = {f"{x} vs {y}": beats(summ, x, y) for x in BASELINES for y in BASELINES if x != y}
    compute_robust = {f"B-COMPUTE (g={gg}) vs {y}": beats(summ, "B-COMPUTE", y, s)
                      for gg, s in ((g, summ), (3.6, sens["G36"]), (4.9, sens["G49"])) for y in ("B-FLAT", "B-LOGLINEAR")}
    promoted = all(v["beats"] for v in compute_robust.values())
    loglin = pairs["B-LOGLINEAR vs B-FLAT"]["beats"]
    return {
        "label": "retrospective", "protocol": "permodel_protocol.yaml", "declared_commit": DECLARED_COMMIT,
        "protocol_sha256": PROTOCOL_SHA256, "g": g,
        "forecasts": main["forecasts"], "skipped": main["skipped"],
        "summary": summ, "summary_first_published_before_correction": summarize(main["forecasts"], "pre"),
        "summary_first_published_after_correction": summarize(main["forecasts"], "post"),
        "sensitivity_summaries": sens, "pairwise": pairs, "compute_rule": compute_robust,
        "verdict": {
            "B-COMPUTE": "promoted: beats B-FLAT and B-LOGLINEAR" if promoted else "not established",
            "B-LOGLINEAR vs B-FLAT": "B-LOGLINEAR beats B-FLAT" if loglin else "not established",
            "B-FLAT vs B-LOGLINEAR": "B-FLAT beats B-LOGLINEAR" if pairs["B-FLAT vs B-LOGLINEAR"]["beats"] else "not established",
        },
    }


# ------------------------------------------------------------------------------------------ report


def _f(x, nd=3):
    return "n/a" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def _iv(i):
    return "n/a" if not i else f"[{i[0]:.1f}, {i[1]:.1f}]"


def to_markdown(res: dict) -> str:
    v = res["verdict"]
    L = ["# METR per-model holdout: each new model forecast at its release date (#56)", "",
         "Generated by `permodel.py` from `data/observations.csv` under `permodel_protocol.yaml`, which was committed on",
         f"its own in `{res['declared_commit']}` (sha256 `{res['protocol_sha256'][:16]}...`) before this code or any score",
         "existed. **Retrospective**: every outcome was public, and had been read, before the protocol was written.",
         "Not a forecast and not empirical validation of any model.", "",
         f"- B-COMPUTE (g = {res['g']}x/year, elasticity 1), pre-declared rule: **{v['B-COMPUTE']}**.",
         f"- B-LOGLINEAR against B-FLAT under the same rule: **{v['B-LOGLINEAR vs B-FLAT']}**; "
         f"B-FLAT against B-LOGLINEAR: **{v['B-FLAT vs B-LOGLINEAR']}**.", "",
         "Rule: lower mean absolute log error in all 8 cells (TH1.0 and TH1.1, p50 and p80, V-FIRST and V-POSTFIX);",
         "for B-COMPUTE also at g = 3.6 and 4.9.", "",
         "| comparison | " + " | ".join(next(iter(res["compute_rule"].values()))["cells"]) + " | beats |",
         "|---|" + "---|" * 9]
    for name, b in list(res["compute_rule"].items()) + [(k, res["pairwise"][k]) for k in
                                                         ("B-LOGLINEAR vs B-FLAT", "B-FLAT vs B-LOGLINEAR")]:
        L.append(f"| {name} | " + " | ".join(_f(c) for c in b["cells"].values()) + f" | {b['beats']} |")
    L += ["", "## Summary by resolution", "",
          "Mean absolute natural-log error (0.69 = a factor of 2), mean 80% interval score on the log scale, 80% coverage.",
          "V-FIRST: inputs as public at the release date, outcome as first published (primary). V-LATEST: same inputs,",
          "outcome at its latest value. V-POSTFIX: inputs and outcome all at post-correction (regularization 1e-5) values;",
          "uses revisions not public at the cutoff.", "",
          "| suite | metric | resolution | baseline | targets | mean abs log err | intervals | mean IS80 | coverage80 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for k, s in res["summary"].items():
        L.append("| " + " | ".join(k.split("|")) + f" | {s['n']} | {_f(s['mean_abslogerr'])} | {s['n_intervals']} | "
                 f"{_f(s['mean_interval80'])} | {_f(s['coverage80'], 2)} |")
    for title, key in (("first published before the 2026-03-03 correction", "summary_first_published_before_correction"),
                       ("first published on or after the 2026-03-03 correction", "summary_first_published_after_correction")):
        L += ["", f"## Targets {title}", "", "| suite | metric | resolution | baseline | targets | mean abs log err |",
              "|---|---|---|---|---|---|"]
        for k, s in res[key].items():
            L.append("| " + " | ".join(k.split("|")) + f" | {s['n']} | {_f(s['mean_abslogerr'])} |")
    for name, summ in res["sensitivity_summaries"].items():
        L += ["", f"## Sensitivity {name} (V-FIRST and V-POSTFIX)", "",
              "| suite | metric | resolution | baseline | targets | mean abs log err | coverage80 |", "|---|---|---|---|---|---|---|"]
        for k, s in summ.items():
            if k.split("|")[2] in RULE_RESOLUTIONS:
                L.append("| " + " | ".join(k.split("|")) + f" | {s['n']} | {_f(s['mean_abslogerr'])} | {_f(s['coverage80'], 2)} |")
    L += ["", "## Every forecast (V-FIRST)", "",
          "| suite | metric | model | release (cutoff) | first published | info set | observed | flat | flat 80% | loglinear | loglinear 80% | compute | compute 80% |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for f in res["forecasts"]:
        r = f["by_resolution"]["V-FIRST"]
        L.append(f"| {f['suite']} | {f['metric']} | {f['alias']} | {f['cutoff']} | {f['first_available']} | {r['n_info']} | "
                 f"{r['observed']:.1f} | {r['B-FLAT']['point']:.1f} | {_iv(r['B-FLAT']['interval80'])} | "
                 f"{_f(r['B-LOGLINEAR']['point'], 1)} | {_iv(r['B-LOGLINEAR']['interval80'])} | "
                 f"{r['B-COMPUTE']['point']:.1f} | {_iv(r['B-COMPUTE']['interval80'])} |")
    L += ["", "## Every forecast (V-POSTFIX)", "",
          "| suite | metric | model | observed | flat | loglinear | compute |", "|---|---|---|---|---|---|---|"]
    for f in res["forecasts"]:
        r = f["by_resolution"]["V-POSTFIX"]
        if "B-FLAT" in r and r["observed"] is not None:
            L.append(f"| {f['suite']} | {f['metric']} | {f['alias']} | {r['observed']:.1f} | {r['B-FLAT']['point']:.1f} | "
                     f"{_f(r['B-LOGLINEAR']['point'], 1)} | {r['B-COMPUTE']['point']:.1f} |")
    L += ["", f"Skipped targets (information set below 3 models): {res['skipped'] or 'none'}.", "",
          "Units: minutes of human expert time on the suite's tasks (source-native). Targets are not independent:",
          "same-lab models share scaffolds and failure modes, and consecutive targets share most of their information",
          "sets. With 15 TH1.0 and 5 TH1.1 targets these are descriptions, not a significance test.", ""]
    return "\n".join(L)


def registry() -> str:
    res = compute_all()
    seen, out = set(), []
    for f in res["forecasts"]:
        key = (f["suite"], f["model_key"])
        if key in seen:
            continue
        seen.add(key)
        sid = f["suite"].replace(".", "")
        out.append(
            f"  - id: FC-METR-PM-{sid}-{f['model_key'].upper().replace('_', '-')}\n"
            f"    model: \"B-FLAT, B-LOGLINEAR and B-COMPUTE as declared in research_notes/external/metr-time-horizons/permodel_protocol.yaml (declared in {DECLARED_COMMIT[:7]})\"\n"
            f"    target: \"p50 and p80 time horizon of {f['alias']} on METR {f['suite']}, forecast at its release date (minutes of human expert time)\"\n"
            f"    information_cutoff: \"{f['cutoff']}\"\n"
            f"    issued: \"2026-10-25\"\n"
            f"    label: retrospective\n"
            f"    inputs: {json.dumps(f['inputs'] + [COMPUTE_RECORD])}\n"
            f"    horizon: \"0 days (the model's own release date)\"\n"
            f"    baselines: [B-FLAT, B-LOGLINEAR, B-COMPUTE]\n"
            f"    scoring: [S-ABSLOGERR, S-INTERVAL80, S-COVERAGE80]\n"
            f"    resolution: {{record: {f['resolution_record']}, vintage: \"first published (available {f['first_available']}); latest and post-correction vintages scored separately\"}}")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--registry", action="store_true")
    a = ap.parse_args()
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != PROTOCOL_SHA256:
        sys.exit("permodel: permodel_protocol.yaml differs from the declared version")
    if a.registry:
        print(registry())
        return
    res = compute_all()
    jpath, mpath = HERE / "results/permodel.json", HERE / "results/permodel.md"
    if a.check:
        if not H.close(json.loads(jpath.read_text()), res) or mpath.read_text() != to_markdown(res):
            sys.exit("permodel: recomputed results differ from the committed results/permodel.{json,md}")
        print(f"permodel: {len(res['forecasts'])} retrospective per-model forecasts reproduce the committed results; "
              f"B-COMPUTE: {res['verdict']['B-COMPUTE']}")
        return
    jpath.write_text(json.dumps(res, indent=1, sort_keys=True, default=str) + "\n")
    mpath.write_text(to_markdown(res))
    print(f"wrote {jpath} and {mpath}; verdict: {res['verdict']}")


if __name__ == "__main__":
    main()
