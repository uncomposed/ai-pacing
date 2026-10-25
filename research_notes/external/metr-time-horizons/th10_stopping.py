"""Why four TH1.0 agents exceed the declared 1e-3 tolerance (issue #57): scikit-learn's stopping point.

    python th10_stopping.py --cache .cache --out results/th10_stopping.json      # needs scikit-learn 1.8.0

For each of the 33 TH1.0 agents (post-correction runs, regularization 1e-5, as published) this fits the
same weighted logistic regression three ways and compares the horizons with METR's published values:

  ours      horizon_fit.fit_logistic: damped Newton to a tight gradient tolerance (the independent fit);
  default   scikit-learn LogisticRegression(C=1e5) with its defaults (lbfgs, tol 1e-4, max_iter 100), the call in
            METR's src/horizon/utils/logistic.py;
  tight     the same objective with tol 1e-12 and a large max_iter, lbfgs and newton-cholesky.

If the published value is scikit-learn's stopping point, `default` reproduces it, `ours` and `tight` agree with
each other, and the objective at `default` is above the objective at `ours`. The tolerance in reproduce.py
(relative 1e-3) is not touched. The committed results/th10_stopping.json is read by the fast tests; this script
needs scikit-learn and the cache (network, fetch_sources.sh), so it is run by hand or by the metr-repro workflow.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
import warnings

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import horizon_fit as hf  # noqa: E402
import reproduce as rp  # noqa: E402

REG = 1e-5
LEVELS = {"p50": 0.5, "p80": 0.8}


def sk_fit(x, y, w, **kw):
    from sklearn.linear_model import LogisticRegression
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        m = LogisticRegression(C=1 / REG, **kw).fit(x.reshape(-1, 1), y, sample_weight=w)
    a, b = float(m.intercept_[0]), float(m.coef_[0][0])
    return a, b, int(np.max(m.n_iter_)), [str(c.category.__name__) for c in caught]


def objective(a: float, b: float, x, y, w) -> float:
    return hf._objective(np.array([a, b]), x, y, w, 1 / REG)


def grad_norm(a: float, b: float, x, y, w) -> float:
    """hf's scaled gradient norm (comparable to scikit-learn's tol, weights sum to 1 here)."""
    c = 1 / REG
    p = hf._sigmoid(a + b * x)
    r = c * w * (p - y)
    return float(max(abs(r.sum()), abs(np.dot(r, x) + b)) / max(1.0, c * w.sum()))


def horizons(a: float, b: float) -> dict:
    return {n: float(2.0 ** ((math.log(p / (1 - p)) - a) / b)) for n, p in LEVELS.items()}


def main() -> None:
    import sklearn
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(HERE / ".cache"))
    ap.add_argument("--out", required=True)
    a_ = ap.parse_args()
    cache = pathlib.Path(a_.cache)
    path = cache / "vintages/th10_2026-03-05.jsonl"
    pub = yaml.safe_load((cache / "metr.org/benchmark_results_1_0.yaml").read_text())["results"]
    keys = rp._alias_keys(path)
    runs = hf.load_runs(str(path), exclude_agents=("human",))
    out: dict = {"upstream_commit": "52cb829c7a2efb2d659285c4b1768d191d97f8d2",
                 "versions": {"numpy": np.__version__, "scikit-learn": sklearn.__version__},
                 "tolerance_rel": rp.TOL_REL, "regularization": REG, "agents": {}}
    for alias in sorted(set(runs.agent)):
        m = runs.agent == alias
        x, y, w = np.log2(runs.human_minutes[m]), runs.score[m], runs.weight[m]
        if not np.any(y > 0):
            continue
        ours = hf.fit_logistic(x, y, w, REG)
        d_a, d_b, d_it, d_warn = sk_fit(x, y, w)
        t_a, t_b, t_it, t_warn = sk_fit(x, y, w, tol=1e-12, max_iter=100_000)
        n_a, n_b, n_it, n_warn = sk_fit(x, y, w, solver="newton-cholesky", tol=1e-12, max_iter=1000)
        pm = pub[keys[alias]]["metrics"]
        row = {"model_key": keys[alias], "n_runs": int(m.sum()),
               "published": {n: pm[f"{n}_horizon_length"]["estimate"] for n in LEVELS},
               "ours": {n: ours.horizon(p) for n, p in LEVELS.items()},
               "sklearn_default": horizons(d_a, d_b), "sklearn_tight_lbfgs": horizons(t_a, t_b),
               "sklearn_tight_newton_cholesky": horizons(n_a, n_b),
               "sklearn_default_n_iter": d_it, "sklearn_default_warnings": d_warn,
               "objective": {"ours": objective(ours.intercept, ours.slope, x, y, w),
                             "sklearn_default": objective(d_a, d_b, x, y, w),
                             "sklearn_tight_lbfgs": objective(t_a, t_b, x, y, w),
                             "sklearn_tight_newton_cholesky": objective(n_a, n_b, x, y, w)},
               "grad_norm": {"ours": ours.grad_norm, "sklearn_default": grad_norm(d_a, d_b, x, y, w)}}
        rel = lambda k, n: row[k][n] / row["published"][n] - 1
        row["rel_diff_to_published"] = {k: {n: rel(k, n) for n in LEVELS} for k in
                                        ("ours", "sklearn_default", "sklearn_tight_lbfgs", "sklearn_tight_newton_cholesky")}
        row["max_abs_rel_to_published"] = {k: max(abs(v) for v in d.values()) for k, d in row["rel_diff_to_published"].items()}
        row["exceeds_tolerance_ours"] = bool(row["max_abs_rel_to_published"]["ours"] > rp.TOL_REL)
        out["agents"][alias] = row
    out["exceeding"] = sorted(a for a, r in out["agents"].items() if r["exceeds_tolerance_ours"])
    pathlib.Path(a_.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    for a in out["exceeding"]:
        r = out["agents"][a]
        print(a, {k: f"{v:.1e}" for k, v in r["max_abs_rel_to_published"].items()}, "objective gap",
              r["objective"]["sklearn_default"] - r["objective"]["ours"])


if __name__ == "__main__":
    main()
