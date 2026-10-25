"""Run METR's own fitting code (pinned eval-analysis-public) on the TH1.1 headline data, without DVC.

    python run_upstream.py --cache .cache --n-bootstrap 1000 --out results/upstream_th11.json

Needs the upstream dependencies at the versions in upstream uv.lock (numpy 2.4.1, scikit-learn 1.8.0,
pandas 2.3.3, joblib 1.5.3, scipy, pyyaml); see .github/workflows/metr-repro.yml. It calls
horizon.wrangle.bootstrap.compute_bootstrap_regressions and horizon.wrangle.logistic.run_logistic_regressions
with the parameters of figs.wrangle_logistic.headline in reports/time-horizon-1-1/fig_params/figs.yaml.
DVC is only used upstream to read those parameters, so an empty stub package stands in for it and the
parameters are read from the YAML directly. Run without `python -I`, so joblib's workers see PYTHONPATH.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import os
import sys


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(pathlib.Path(__file__).with_name(".cache")))
    ap.add_argument("--n-bootstrap", type=int, default=1000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cache = pathlib.Path(a.cache)
    up = cache / "eval-analysis-public"
    # Stub package for dvc (upstream imports dvc.api only to read parameters). Put on PYTHONPATH too, so
    # joblib's worker processes can import the upstream modules.
    stub = cache / "_stubs"
    (stub / "dvc").mkdir(parents=True, exist_ok=True)
    (stub / "dvc/__init__.py").write_text("")
    (stub / "dvc/api.py").write_text("")
    paths = [str(up / "src"), str(stub)]
    sys.path[:0] = paths
    os.environ["PYTHONPATH"] = os.pathsep.join(paths + [os.environ.get("PYTHONPATH", "")])

    import numpy as np
    import pandas as pd
    import sklearn
    import yaml
    from horizon.wrangle.bootstrap import compute_bootstrap_regressions
    from horizon.wrangle.logistic import run_logistic_regressions

    report = up / "reports/time-horizon-1-1"
    params = yaml.safe_load((report / "fig_params/figs.yaml").read_text())["figs"]["wrangle_logistic"]["headline"]
    runs_file = report / "data/raw/runs.jsonl"
    data = pd.read_json(runs_file, lines=True, orient="records")
    boot = None
    if a.n_bootstrap > 0:
        bdata = data.rename(columns={"alias": "agent"})
        boot = compute_bootstrap_regressions(
            data=bdata, categories=["task_family", "task_id", "run_id"], n_bootstrap=a.n_bootstrap,
            regularization=params["regularization"], weights_col=params["weighting"],
            success_percents=params["success_percents"], score_col=params.get("score_col", "score_binarized"))
        bfile = cache / "upstream_bootstrap_th11.csv"
        boot.to_csv(bfile, index=False)
    runs = pd.read_json(runs_file, lines=True, orient="records", convert_dates=False)
    bpath = (cache / "upstream_bootstrap_th11.csv") if boot is not None else None
    fits = run_logistic_regressions(runs, up / "data/external/release_dates.yaml", params, bpath)
    out = {
        "upstream_commit": "52cb829c7a2efb2d659285c4b1768d191d97f8d2",
        "versions": {"numpy": np.__version__, "pandas": pd.__version__, "scikit-learn": sklearn.__version__},
        "params": {k: params[k] for k in ("weighting", "regularization", "success_percents", "confidence_level")},
        "n_bootstrap": a.n_bootstrap,
        "agents": {
            row["agent"]: {k: (None if pd.isna(row[k]) else float(row[k]))
                           for k in ("p50", "p50q0.025", "p50q0.975", "p80", "p80q0.025", "p80q0.975", "average")}
            for _, row in fits.iterrows() if row["agent"] != "human"
        },
    }
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
