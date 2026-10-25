"""Declared TH1.0 -> TH1.1 horizon mapping with uncertainty (issue #57). See suite_mapping.yaml first.

    python suite_mapping.py            # writes results/suite_mapping.json and results/suite_mapping.md
    python suite_mapping.py --check    # recompute and compare with the committed results (used by the tests)

Needs only data/observations.csv (published post-correction values and intervals) and numpy; no network.
A descriptive calibration across 16 agents METR measured on both suites. It is not empirical validation of
anything and not a conversion rule for other models; the criteria in the YAML are adequacy checks.
"""
from __future__ import annotations

import argparse
import csv
import functools
import json
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import holdout as H  # noqa: E402  (t quantile, YAML loader, comparison helper)

DECL = H.ET.load_yaml(HERE / "suite_mapping.yaml")
REF_H10 = (5.0, 15.0, 30.0, 60.0, 120.0, 250.0)   # reference TH1.0 horizons (minutes) for the prediction table


@functools.lru_cache(maxsize=None)
def tq(p: float, df: int) -> float:
    return H.t_ppf(p, df)


def load_pairs() -> list[dict]:
    with (HERE / "data/observations.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    by = {(r["record_id"], r["model_key"]): r for r in rows}
    out = []
    for p in DECL["pairs"]:
        a, b = by[(DECL["rows"]["th10"], p["th10"])], by[(DECL["rows"]["th11"], p["th11"])]
        rec = {"th10": p["th10"], "th11": p["th11"], "alias10": a["alias"], "alias11": b["alias"],
               "scaffold_change": bool(p["scaffold_change"])}
        for m in DECL["metrics"]:
            for tag, r in (("10", a), ("11", b)):
                rec[f"{m}_{tag}"] = float(r[f"{m}_min"])
                for bound in ("low", "high"):
                    v = r[f"{m}_ci_{bound}"]
                    rec[f"{m}_{tag}_{bound}"] = float(v) if v else None
        out.append(rec)
    return out


def ols(x: np.ndarray, y: np.ndarray) -> dict:
    n = len(x)
    xb, yb = x.mean(), y.mean()
    sxx = float(np.sum((x - xb) ** 2))
    b = float(np.sum((x - xb) * (y - yb)) / sxx)
    a = float(yb - b * xb)
    res = y - (a + b * x)
    s = math.sqrt(float(np.sum(res ** 2)) / (n - 2))
    return {"a": a, "b": b, "s": s, "n": n, "df": n - 2, "xbar": float(xb), "sxx": sxx, "se_b": s / math.sqrt(sxx),
            "se_a": s * math.sqrt(1 / n + xb ** 2 / sxx), "r2": 1 - float(np.sum(res ** 2)) / float(np.sum((y - yb) ** 2))}


def predict(f: dict, x: float, level: float) -> dict:
    """Point prediction of ln h11 at ln h10 = x, with the t-based prediction interval for one new agent and the
    confidence interval of the mean line."""
    t = tq(0.5 + level / 2, f["df"])
    mean = f["a"] + f["b"] * x
    lev = 1 / f["n"] + (x - f["xbar"]) ** 2 / f["sxx"]
    pi = t * f["s"] * math.sqrt(1 + lev)
    ci = t * f["s"] * math.sqrt(lev)
    return {"ln": mean, "pi": [mean - pi, mean + pi], "ci": [mean - ci, mean + ci]}


def fit_metric(pairs: list[dict], m: str, level: float) -> dict:
    fit = [p for p in pairs if p["scaffold_change"]]
    held = [p for p in pairs if not p["scaffold_change"]]
    x = np.log([p[f"{m}_10"] for p in fit])
    y = np.log([p[f"{m}_11"] for p in fit])
    f = ols(x, y)
    res: dict = {"fit": f, "support_h10": [float(math.exp(x.min())), float(math.exp(x.max()))],
                 "slope_equals_1_t": (f["b"] - 1) / f["se_b"]}

    # Baselines and leave-one-out.
    loo = []
    for i, p in enumerate(fit):
        k = np.arange(len(fit)) != i
        fi = ols(x[k], y[k])
        pr = predict(fi, x[i], level)
        ratio_pred = x[i] + float(np.mean(y[k] - x[k]))
        loo.append({"model": p["th10"], "ln_h11": float(y[i]), "mapping": pr["ln"], "pi": pr["pi"],
                    "err_mapping": float(y[i] - pr["ln"]), "err_identity": float(y[i] - x[i]),
                    "err_const_ratio": float(y[i] - ratio_pred), "covered": bool(pr["pi"][0] <= y[i] <= pr["pi"][1])})
    mae = {k: float(np.mean([abs(r[f"err_{k}"]) for r in loo])) for k in ("mapping", "identity", "const_ratio")}
    res["loo"] = {"rows": loo, "mean_abs_error_ln": mae, "covered": sum(r["covered"] for r in loo), "n": len(loo)}

    # Held out (same scaffold): not used in the fit.
    ho = []
    for p in held:
        xi, yi = math.log(p[f"{m}_10"]), math.log(p[f"{m}_11"])
        pr = predict(f, xi, level)
        ho.append({"model": p["th10"], "ln_h11": yi, "mapping": pr["ln"], "pi": pr["pi"], "resid": yi - pr["ln"],
                   "resid_over_s": (yi - pr["ln"]) / f["s"], "inside": bool(pr["pi"][0] <= yi <= pr["pi"][1]),
                   "h10_in_support": bool(res["support_h10"][0] <= p[f"{m}_10"] <= res["support_h10"][1])})
    res["held_out"] = ho

    # Bootstrap over the fit-set agents (they are the unit of replication; METR chose which to re-run).
    spec = DECL["bootstrap"]
    rng = np.random.default_rng(spec["seed"])
    n = len(fit)
    ab = np.empty((spec["n"], 2))
    for i in range(spec["n"]):
        idx = rng.integers(0, n, n)
        if np.ptp(x[idx]) == 0:
            ab[i] = np.nan
            continue
        fb = ols(x[idx], y[idx])
        ab[i] = (fb["a"], fb["b"])
    ab = ab[np.isfinite(ab[:, 0])]
    q = lambda v: [float(u) for u in np.quantile(v, [0.025, 0.975])]
    res["bootstrap"] = {"n_valid": int(len(ab)), "a_ci95": q(ab[:, 0]), "b_ci95": q(ab[:, 1]),
                        "slope_excludes_1": bool(not (q(ab[:, 1])[0] <= 1.0 <= q(ab[:, 1])[1]))}

    # Prediction table at reference TH1.0 horizons.
    table = []
    for h in REF_H10:
        pr = predict(f, math.log(h), level)
        table.append({"h10": h, "in_support": bool(res["support_h10"][0] <= h <= res["support_h10"][1]),
                      "h11": math.exp(pr["ln"]), "pi": [math.exp(v) for v in pr["pi"]], "ci": [math.exp(v) for v in pr["ci"]]})
    res["table"] = table

    # Sensitivity: all 16 agents in the fit.
    xa = np.log([p[f"{m}_10"] for p in pairs])
    ya = np.log([p[f"{m}_11"] for p in pairs])
    fa = ols(xa, ya)
    res["fit_all16"] = {k: fa[k] for k in ("a", "b", "s", "n", "r2")}

    # Context for the residual scatter: the published intervals of each side, as log standard errors
    # (interval width / 3.92). They overstate the noise of the difference if the two suites' errors are
    # positively correlated (shared tasks), which the published files cannot show.
    se = []
    for p in fit:
        s10 = (math.log(p[f"{m}_10_high"]) - math.log(p[f"{m}_10_low"])) / 3.92
        s11 = (math.log(p[f"{m}_11_high"]) - math.log(p[f"{m}_11_low"])) / 3.92
        se.append((s10, s11))
    res["published_interval_se_ln"] = {
        "median_th10": float(np.median([s[0] for s in se])), "median_th11": float(np.median([s[1] for s in se])),
        "rms_of_independent_difference": float(math.sqrt(np.mean([a * a + b * b for a, b in se])))}

    c = {"C1": bool(mae["mapping"] < mae["identity"] and mae["mapping"] < mae["const_ratio"]),
         "C2": bool(res["loo"]["covered"] >= 12), "C3": bool(all(r["inside"] for r in ho)),
         "C4": res["bootstrap"]["slope_excludes_1"]}
    res["criteria_met"] = c
    return res


def compute() -> dict:
    pairs = load_pairs()
    level = DECL["interval_level"]
    out = {"id": DECL["id"], "interval_level": level, "n_pairs": len(pairs),
           "n_fit": sum(p["scaffold_change"] for p in pairs), "pairs": pairs,
           "metrics": {m: fit_metric(pairs, m, level) for m in DECL["metrics"]}}
    # Lab context for the residuals (informational): sign of the fit-set residuals by lab.
    for m, r in out["metrics"].items():
        f = r["fit"]
        lab = {}
        for p in pairs:
            if not p["scaffold_change"]:
                continue
            e = math.log(p[f"{m}_11"]) - (f["a"] + f["b"] * math.log(p[f"{m}_10"]))
            lab.setdefault("anthropic" if p["th10"].startswith("claude") else "openai", []).append(e)
        r["residual_by_lab"] = {k: {"n": len(v), "mean": float(np.mean(v))} for k, v in sorted(lab.items())}
    return out


def to_markdown(res: dict) -> str:
    L = ["# TH1.0 to TH1.1 horizon mapping (generated by `suite_mapping.py`)", "",
         f"Declared in `suite_mapping.yaml` (`{res['id']}`). A descriptive calibration over {res['n_pairs']} agents with published "
         f"post-correction values on both suites ({res['n_fit']} fit, {res['n_pairs'] - res['n_fit']} held out). ln(h11) = a + b ln(h10), "
         f"minutes of human time, one fit per metric. {int(res['interval_level'] * 100)}% prediction intervals are Student t. "
         "Not empirical validation; the criteria were fixed after an exploratory look at the same pairs.", ""]
    for m, r in res["metrics"].items():
        f, bs = r["fit"], r["bootstrap"]
        L += [f"## {m.upper()}", "",
              f"- Fit ({f['n']} agents): a = {f['a']:.3f}, b = {f['b']:.3f} (se {f['se_b']:.3f}; bootstrap 95% interval "
              f"{bs['b_ci95'][0]:.2f} to {bs['b_ci95'][1]:.2f}), residual sd {f['s']:.3f} in ln units (a factor of {math.exp(f['s']):.2f}), R^2 {f['r2']:.3f}.",
              f"- All 16 in the fit (sensitivity): a = {r['fit_all16']['a']:.3f}, b = {r['fit_all16']['b']:.3f}, residual sd {r['fit_all16']['s']:.3f}.",
              f"- Support (fit-set TH1.0 horizons): {r['support_h10'][0]:.1f} to {r['support_h10'][1]:.1f} minutes. The mapping is not applied outside it.",
              f"- Published intervals as ln standard errors: median {r['published_interval_se_ln']['median_th10']:.2f} (TH1.0) and "
              f"{r['published_interval_se_ln']['median_th11']:.2f} (TH1.1); if the two errors were independent the difference would scatter by "
              f"{r['published_interval_se_ln']['rms_of_independent_difference']:.2f}, against a residual sd of {f['s']:.2f} about the line. "
              "Independent errors could not give a scatter that small, so the two suites' sampling errors are positively correlated (shared tasks and families); "
              "the published files cannot say by how much, and a paired bootstrap was not run.",
              f"- Residual by lab (mean ln, informational): " + ", ".join(f"{k} {v['mean']:+.2f} (n={v['n']})" for k, v in r["residual_by_lab"].items()) + ".", "",
              "| criterion | result |", "|---|---|"]
        lo = r["loo"]
        L += [f"| C1 leave-one-out mean abs error (ln): mapping {lo['mean_abs_error_ln']['mapping']:.3f}, identity {lo['mean_abs_error_ln']['identity']:.3f}, "
              f"constant ratio {lo['mean_abs_error_ln']['const_ratio']:.3f} | {'met' if r['criteria_met']['C1'] else 'NOT met'} |",
              f"| C2 leave-one-out coverage of the {int(res['interval_level'] * 100)}% prediction interval: {lo['covered']} of {lo['n']} (need 12) | {'met' if r['criteria_met']['C2'] else 'NOT met'} |",
              f"| C3 held-out agents inside the interval: " + "; ".join(
                  f"{h['model']} residual {h['resid']:+.2f} ({h['resid_over_s']:+.1f} s), {'inside' if h['inside'] else 'outside'}" for h in r["held_out"]) +
              f" | {'met' if r['criteria_met']['C3'] else 'NOT met'} |",
              f"| C4 slope bootstrap interval excludes 1 | {'met' if r['criteria_met']['C4'] else 'NOT met'} |", "",
              "| TH1.0 horizon (min) | in support | predicted TH1.1 (min) | 90% prediction interval | 90% interval of the mean |", "|---|---|---|---|---|"]
        for t in r["table"]:
            L.append(f"| {t['h10']:g} | {'yes' if t['in_support'] else 'no'} | {t['h11']:.1f} | {t['pi'][0]:.1f} to {t['pi'][1]:.1f} | {t['ci'][0]:.1f} to {t['ci'][1]:.1f} |")
        L += ["", "| agent | TH1.0 | TH1.1 | mapped (fit without this agent) | leave-one-out error (ln) | identity error | constant-ratio error |", "|---|---|---|---|---|---|---|"]
        pm = {p["th10"]: p for p in res["pairs"]}
        for row in lo["rows"]:
            p = pm[row["model"]]
            L.append(f"| {p['alias10']} | {p[m + '_10']:.2f} | {p[m + '_11']:.2f} | {math.exp(row['mapping']):.2f} | {row['err_mapping']:+.2f} | "
                     f"{row['err_identity']:+.2f} | {row['err_const_ratio']:+.2f} |")
        L.append("")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    res = compute()
    jp, mp = HERE / "results/suite_mapping.json", HERE / "results/suite_mapping.md"
    if a.check:
        ok = H.close(json.loads(jp.read_text()), res) and mp.read_text() == to_markdown(res)
        print("suite_mapping: committed results reproduce" if ok else "suite_mapping: MISMATCH with committed results")
        sys.exit(0 if ok else 1)
    jp.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    mp.write_text(to_markdown(res))
    print(to_markdown(res))


if __name__ == "__main__":
    main()
