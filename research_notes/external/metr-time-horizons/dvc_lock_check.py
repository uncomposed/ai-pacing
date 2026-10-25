"""Are the public inputs the ones METR's recorded pipeline run used? (issue #57)

    python dvc_lock_check.py --cache .cache --out results/dvc_lock_check.json      # stdlib only; needs the cache

METR's repository records, in reports/time-horizon-1-1/dvc.lock (DVC), the md5 and size of every input
(code files, runs.jsonl, release_dates.yaml) and output of the stage that produced the headline bootstrap and
the headline fits, and the parameters of the run (n_bootstrap 1000, regularization 1e-5, invsqrt_task_weight,
success percents, confidence level). This script recomputes the md5 of each input from the pinned checkout
and compares. A match means the public inputs are byte-identical to what that stage consumed. Outputs are
not in the repository (DVC remote), so their md5 and size can only be reported, not checked; for the bootstrap
output, the size of the file METR's code writes here is reported next to the recorded size.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re

STAGES = ("wrangle_bootstrap_logistic@headline", "wrangle_logistic_regression@headline")


def parse_lock(text: str) -> dict:
    """Minimal parser for the part of dvc.lock needed here: per stage, deps and outs as (path, md5, size)."""
    stages: dict = {}
    cur = sect = None
    item: dict | None = None
    for line in text.splitlines():
        m = re.match(r"^  (\S.*):$", line)
        if m and not line.startswith("    "):
            cur = stages.setdefault(m.group(1), {"deps": [], "outs": [], "params": [], "cmd": ""})
            sect, item = None, None
            continue
        if cur is None:
            continue
        m = re.match(r"^    cmd: (.*)$", line)
        if m:
            sect, item = "cmd", None
            cur["cmd"] = m.group(1)
            continue
        m = re.match(r"^    (deps|outs|params):", line)
        if m:
            sect, item = m.group(1), None
            continue
        if sect == "cmd":  # the command wraps onto indented continuation lines
            cur["cmd"] += " " + line.strip()
            continue
        if sect in ("deps", "outs"):
            m = re.match(r"^    - path: (.+)$", line)
            if m:
                item = {"path": m.group(1)}
                cur[sect].append(item)
                continue
            m = re.match(r"^      (md5|size): (\S+)$", line)
            if m and item is not None:
                item[m.group(1)] = int(m.group(2)) if m.group(1) == "size" else m.group(2)
        elif sect == "params":
            cur["params"].append(line.strip())
    return stages


def md5_of(path: pathlib.Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(pathlib.Path(__file__).with_name(".cache")))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cache = pathlib.Path(a.cache)
    up = cache / "eval-analysis-public"
    report = up / "reports/time-horizon-1-1"
    stages = parse_lock((report / "dvc.lock").read_text())
    out: dict = {"upstream_commit": "52cb829c7a2efb2d659285c4b1768d191d97f8d2", "stages": {}}
    for name in STAGES:
        st = stages[name]
        checks = []
        for d in st["deps"]:
            p = (report / d["path"]).resolve()
            if "wrangled" in d["path"]:  # an intermediate output of the other stage: not in the repository
                checks.append({"path": d["path"], "recorded_md5": d["md5"], "recorded_size": d["size"], "status": "output, not public"})
                continue
            got = md5_of(p)
            checks.append({"path": d["path"].replace("../../", ""), "recorded_md5": d["md5"], "computed_md5": got,
                           "recorded_size": d["size"], "computed_size": p.stat().st_size,
                           "match": bool(got == d["md5"] and p.stat().st_size == d["size"])})
        out["stages"][name] = {"cmd": " ".join(st["cmd"].split()) if st["cmd"] else None, "inputs": checks,
                               "outputs_recorded": [{k: o[k] for k in ("path", "md5", "size")} for o in st["outs"]],
                               "params": st["params"]}
    own = cache / "upstream_bootstrap_th11.csv"
    if own.exists():
        rec = out["stages"][STAGES[0]]["outputs_recorded"][0]
        out["bootstrap_output_here_vs_recorded"] = {"recorded_size": rec["size"], "recorded_md5": rec["md5"],
                                                    "size_here": own.stat().st_size, "md5_here": md5_of(own),
                                                    "note": "written by METR's code at the lockfile versions (run_upstream.py); floats of an lbfgs fit are not byte-reproducible across machines, so neither value is evidence of different draws"}
    out["all_inputs_match"] = all(c.get("match") for s in out["stages"].values() for c in s["inputs"] if "match" in c)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print("all inputs match dvc.lock:", out["all_inputs_match"])


if __name__ == "__main__":
    main()
