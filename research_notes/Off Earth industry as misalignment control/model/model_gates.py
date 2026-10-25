"""
Model CI gates, one command per evidence category (issue #7, 2026-10-25). Run from model/.

    python3 model_gates.py numerics      # numerical identities and approximations against justified thresholds
    python3 model_gates.py software      # software/schema regression: unit tests, cache provenance, and drift
                                         #   against committed outputs (run numerics first: it makes the outputs)
    python3 model_gates.py replication   # pinned external-model replication (Saklakov, Clark) + gate self-test
    python3 model_gates.py empirical     # empirical validation: reports NOT ESTABLISHED; there is no such gate
    python3 model_gates.py report        # one table of every category's status in this job

Each command writes gate_status/<category>.json and a line in the GitHub job summary. Statuses are `pass`,
`fail` or `not_established`. They are separate on purpose:

- numerics: the solver satisfies identities and closed forms to stated tolerances. It says nothing about
  whether the model describes the world.
- software: code and committed outputs have not drifted (golden-file comparison, cache reproducibility,
  run identity). A green status here does not mean the numbers are right, only that they are unchanged.
- replication: the solver, set to a published model's limit, reproduces that model's own results. It does
  not mean the source's assumptions are true.
- empirical: nothing in this repository compares model outputs with observations, so this is always
  `not_established`. CI success must never be read as empirical validation.

Convergence (results stable as nA, T_H and the ensemble size grow) is not gated yet; see HANDOFF.md 8c.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GATE_DIR = os.environ.get("GATE_DIR", os.path.join(HERE, "gate_status"))
PY = sys.executable

CATEGORIES = {
    "numerics": "numerical identities and approximations",
    "software": "software and schema regression",
    "replication": "external-model replication",
    "empirical": "empirical validation",
}
REPRO_ARGS = "--stage oat_r --designs '[{}]'"


def _summary(md: str):
    print(md, flush=True)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as f:
            f.write(md + "\n")


def _run(steps: list[tuple[str, list[str]]]) -> list[dict]:
    out = []
    for name, cmd in steps:
        print(f"\n::group::{name}" if os.environ.get("GITHUB_ACTIONS") else f"\n== {name}", flush=True)
        t0 = time.time()
        rc = subprocess.run(cmd, cwd=HERE).returncode
        if os.environ.get("GITHUB_ACTIONS"):
            print("::endgroup::", flush=True)
        out.append(dict(step=name, command=" ".join(cmd), exit=rc, seconds=round(time.time() - t0, 1)))
    return out


def _write(category: str, status: str, steps: list[dict], note: str = "") -> int:
    os.makedirs(GATE_DIR, exist_ok=True)
    sys.path.insert(0, HERE)
    import run_identity as ri
    rec = dict(category=category, title=CATEGORIES[category], status=status, steps=steps, note=note,
               environment=ri.environment())
    with open(os.path.join(GATE_DIR, f"{category}.json"), "w") as f:
        json.dump(rec, f, indent=1)
    lines = [f"### {CATEGORIES[category]}: **{status}**", ""]
    lines += [f"- {'ok' if s['exit'] == 0 else 'FAILED'}: {s['step']} (`{s['command']}`, {s['seconds']:.0f} s)" for s in steps]
    if note:
        lines += ["", note]
    _summary("\n".join(lines) + "\n")
    return 0 if status in ("pass", "not_established") else 1


def _status(steps):
    return "pass" if all(s["exit"] == 0 for s in steps) else "fail"


def cmd_numerics(a):
    steps = _run([("robust_design.py --check: CHECK_TOL thresholds and closed-form invariants",
                   [PY, "robust_design.py", "--check"])])
    return _write("numerics", _status(steps), steps,
                  "Fails on any error measure above its threshold or a broken closed-form invariant, whatever the "
                  "committed reference files say.")


def cmd_software(a):
    if not os.path.exists(os.path.join(GATE_DIR, "numerics.json")):
        sys.exit("model_gates: run `model_gates.py numerics` first; it writes the --check outputs compared here")
    steps = [("unit tests: run identity", [PY, "tests/test_run_identity.py"]),
             ("unit tests: check comparison", [PY, "tests/test_check_tolerances.py"]),
             ("unit tests: gate categories", [PY, "tests/test_gates.py"]),
             ("cache provenance: every cache has a manifest or an inventory entry", [PY, "run_identity.py", "inventory", "--check"]),
             ("--check output against the committed reference (drift)", [PY, "ci_sims.py", "compare-checks"])]
    if not a.no_repro:
        steps.append(("re-solve a cached ensemble and compare with the cache (r0.1 box, base design)",
                      [PY, "ci_sims.py", "repro", "--args", REPRO_ARGS, "--manifest", "repro_r0.1_base.json"]))
    res = _run(steps)
    return _write("software", _status(res), res,
                  "Regression only: unchanged is not the same as correct." +
                  (" Cache re-solve skipped (--no-repro)." if a.no_repro else ""))


def cmd_replication(a):
    res = _run([("pinned Saklakov and Clark replication checks",
                 [PY, "docking/replication.py", "--out", os.path.join(GATE_DIR, "replication_checks.json")]),
                ("gate self-test: a deliberately broken solver must fail the Clark checks",
                 [PY, "docking/replication.py", "--self-test"])])
    return _write("replication", _status(res), res,
                  "Powell, Potapov and Metzger are comparisons, not replications; they run in the slow `docking` "
                  "workflow and never count here. A pass shows reproduction, not that the sources' assumptions hold.")


def cmd_empirical(a):
    return _write("empirical", "not_established", [],
                  "No model output is compared with observations anywhere in this repository. This status is "
                  "never `pass`, and no CI result should be cited as empirical validation.")


def cmd_report(a):
    rows = ["| category | status | steps |", "|---|---|---|"]
    worst = 0
    for c, title in CATEGORIES.items():
        p = os.path.join(GATE_DIR, f"{c}.json")
        if not os.path.exists(p):
            rows.append(f"| {title} | not run in this job | - |")
            continue
        with open(p) as f:
            r = json.load(f)
        rows.append(f"| {title} | {r['status']} | {len(r['steps'])} |")
        worst |= r["status"] == "fail"
    _summary("### Model gate status (this job)\n\n" + "\n".join(rows) + "\n")
    return 1 if worst else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("numerics", "replication", "empirical", "report"):
        sub.add_parser(c)
    p = sub.add_parser("software")
    p.add_argument("--no-repro", action="store_true", help="skip the cache re-solve (about 2 minutes)")
    a = ap.parse_args(argv)
    return dict(numerics=cmd_numerics, software=cmd_software, replication=cmd_replication,
                empirical=cmd_empirical, report=cmd_report)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
