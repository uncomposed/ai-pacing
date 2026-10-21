"""
Continuous-integration driver for robust_design.py ensemble runs (2026-10-21). It splits a stage into
GitHub Actions matrix jobs, merges the pieces, and compares re-solved runs with the committed cache.

    python3 ci_sims.py plan  --args "--stage oat_r" [--shards 4] [--force]   # matrix JSON on stdout
    python3 ci_sims.py solve --args "--stage oat_r" --unit TAG --shard 0 --of 4 --out parts/
    python3 ci_sims.py merge --args "--stage oat_r" --parts parts/ [--force]  # new runs into results/robust_runs/
    python3 ci_sims.py repro --args "--stage pilot"                           # re-solve cached runs here, compare
    python3 ci_sims.py compare-checks                                         # --check output against git HEAD
    python3 ci_sims.py collect-outputs --out out/                             # new or changed files, for review
    python3 ci_sims.py provenance --out prov.json                             # commit, numpy, OS of this machine

--args is handed to robust_design.main() with run_design() intercepted, so ensembles, seeds and designs
come from robust_design itself and are never copied here. Only the ensemble stages can be split: pilot,
oat, oat_r, box, radius, factorial, ensemble. A unit is one cached (ensemble, design) run; a shard is a
subset of its solver batches (batches_for). Each batch is solved exactly as run_design solves it, so a
merged run equals an unsplit run on the same machine.

A run that is already in the cache is never overwritten. With --force it is re-solved and compared with
the cache instead: identical, float noise (|a - b| <= ATOL + RTOL |b|, no outcome changes) or differs.
Any changed outcome (act0 or holds) is listed draw by draw and makes the command exit 1.
Every output carries provenance: commit, Python, numpy, OS and runner.
Status: implemented + verified locally (see HANDOFF.md, CI section). Not human_validated.
"""
from __future__ import annotations

import argparse
import contextlib
import glob
import json
import os
import platform
import shlex
import subprocess
import sys
import time
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np

import robust_design as rd

SPLITTABLE = ("pilot", "oat", "oat_r", "box", "radius", "factorial", "ensemble")
MAX_JOBS = 256          # GitHub's limit on jobs in one matrix
ATOL, RTOL = 1e-12, 1e-9
CHECK_FILES = ("results/robust_design_checks.md", "results/robust_design_checks.json")


# ---------------------------------------------------------------------------
# provenance and reporting
# ---------------------------------------------------------------------------
def _git(*cmd):
    try:
        return subprocess.run(["git", *cmd], cwd=rd.HERE, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def provenance() -> dict:
    env = ("RUNNER_OS", "RUNNER_ARCH", "ImageOS", "ImageVersion", "GITHUB_SHA", "GITHUB_REF", "GITHUB_RUN_ID",
           "GITHUB_RUN_ATTEMPT", "GITHUB_WORKFLOW", "GITHUB_JOB")
    return dict(commit=_git("rev-parse", "HEAD"), dirty_tracked_files=bool(_git("status", "--porcelain", "-uno")),
                python=platform.python_version(), numpy=np.__version__, os=platform.platform(),
                machine=platform.machine(), workers=rd.WORKERS, cfg=rd.CFG, n_full=rd.N_FULL, n_near=rd.N_NEAR,
                runner={k: os.environ[k] for k in env if k in os.environ},
                utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


def summary(md: str):
    """Print markdown to stderr and, on GitHub, to the job summary page."""
    print(md, file=sys.stderr)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as f:
            f.write(md + "\n")


# ---------------------------------------------------------------------------
# units: the run_design calls a robust_design stage would make
# ---------------------------------------------------------------------------
def collect(args: str) -> "OrderedDict[str, dict]":
    argv = shlex.split(args)
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--stage")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--report", action="store_true")
    known, _ = ap.parse_known_args(argv)
    if known.stage not in SPLITTABLE or known.check or known.report:
        sys.exit(f"ci_sims: --args must name one of --stage {', '.join(SPLITTABLE)} and no --check/--report "
                 f"(got {args!r}). Run other stages whole, as the sims workflow does.")
    units: "OrderedDict[str, dict]" = OrderedDict()
    real = rd.run_design

    def record(ens_name, thetas, design, pool=None, **kw):
        tag = rd.run_tag(ens_name, design, **kw)
        units.setdefault(tag, dict(tag=tag, thetas=thetas, design=dict(design), kw=kw))
        n = len(thetas)
        out = {k: np.zeros(n) for k in rd.KEEP}
        out["act0"], out["holds"] = np.full(n, "C"), np.zeros(n)
        return out

    rd.run_design, saved = record, sys.argv
    sys.argv = ["robust_design.py"] + argv
    try:
        with contextlib.redirect_stdout(sys.stderr):
            rd.main()
    finally:
        rd.run_design, sys.argv = real, saved
    return units


def cache_path(tag: str) -> str:
    return os.path.join(rd.RUNS, tag + ".npz")


def load(path: str) -> dict:
    z = np.load(path)
    return {k: z[k] for k in z.files}


def cached(u: dict) -> bool:
    """True if the unit is in the cache. The cache name does not record the ensemble size, so a cached
    run of another size (RD_NFULL / RD_NNEAR changed) is an error, never silently reused."""
    p = cache_path(u["tag"])
    if not os.path.exists(p):
        return False
    n = len(load(p)["holds"])
    if n != len(u["thetas"]):
        sys.exit(f"ci_sims: cached {u['tag']} has {n} draws but this ensemble has {len(u['thetas'])}. "
                 "Use another --runs-dir for non-default ensemble sizes.")
    return True


def solve_groups(u: dict, groups: list) -> dict:
    params = [rd.apply_design(t, u["design"]) for t in u["thetas"]]
    cfg = dict(rd.CFG, **u["kw"])
    jobs = [([params[i] for i in g], cfg) for g in groups]
    with ProcessPoolExecutor(rd.WORKERS) as pool:
        res = list(pool.map(rd._solve_batch, jobs))
    out = {k: np.concatenate([r[k] for r in res]) for k in res[0]}
    out["idx"] = np.concatenate(groups)
    return out


def assemble(n: int, parts: list[dict], tag: str) -> dict:
    out = {k: np.full(n, np.nan) for k in rd.KEEP}
    out["act0"] = np.full(n, "", "U1")
    seen = np.zeros(n, int)
    for z in parts:
        idx = z["idx"]
        seen[idx] += 1
        for k in out:
            out[k][idx] = z[k]
    if not (seen == 1).all():
        sys.exit(f"ci_sims: {tag}: draws {np.nonzero(seen != 1)[0].tolist()} missing or solved twice")
    out["holds"] = rd.holds(out).astype(float)
    return out


# ---------------------------------------------------------------------------
# comparison with the cache
# ---------------------------------------------------------------------------
def compare(ref: dict, new: dict) -> dict:
    flips_act = np.nonzero(ref["act0"] != new["act0"])[0]
    flips_hold = np.nonzero(ref["holds"] != new["holds"])[0]
    max_abs, beyond, exact = 0.0, [], True
    for k in [k for k in rd.KEEP if k in ref and k in new]:   # runs cached before 2026-10-21 have no "fail"
        a, b = np.asarray(ref[k], float), np.asarray(new[k], float)
        nan_a, nan_b = np.isnan(a), np.isnan(b)
        both = nan_a & nan_b
        d = np.where(both, 0.0, np.abs(a - b))
        d = np.where(nan_a ^ nan_b, np.inf, d)
        if (d > 0).any():
            exact = False
        max_abs = max(max_abs, float(d.max(initial=0.0)))
        bad = d > ATOL + RTOL * np.where(nan_a, 0.0, np.abs(a))
        if bad.any():
            beyond.append(f"{k} ({int(bad.sum())} draws)")
    verdict = ("identical" if exact and not len(flips_act) and not len(flips_hold) else
               "float noise" if not beyond and not len(flips_act) and not len(flips_hold) else "differs")
    return dict(n=len(ref["holds"]), verdict=verdict, max_abs_diff=max_abs, beyond_tolerance=beyond,
                fields_not_compared=sorted(set(rd.KEEP) ^ (set(rd.KEEP) & set(ref) & set(new))),
                act0_changed=[dict(draw=int(i), cache=str(ref["act0"][i]), here=str(new["act0"][i]))
                              for i in flips_act],
                holds_changed=[dict(draw=int(i), cache=bool(ref["holds"][i]), here=bool(new["holds"][i]),
                                    att_cache=float(ref["att"][i]), att_here=float(new["att"][i]))
                               for i in flips_hold])


def compare_table(rows: dict) -> str:
    out = ["| run | draws | verdict | largest abs. difference | outcome changes |", "|---|---|---|---|---|"]
    for tag, c in rows.items():
        ch = [f"draw {x['draw']} act0 {x['cache']}->{x['here']}" for x in c["act0_changed"]]
        ch += [f"draw {x['draw']} holds {x['cache']}->{x['here']} (att {x['att_cache']:.3g}->{x['att_here']:.3g})"
               for x in c["holds_changed"]]
        out.append(f"| `{tag}` | {c['n']} | {c['verdict']} | {c['max_abs_diff']:.3g} | {'; '.join(ch) or 'none'} |")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------
def cmd_plan(a):
    units = collect(a.args)
    jobs, skipped = [], []
    for u in units.values():
        if cached(u) and not a.force:
            skipped.append(u["tag"])
            continue
        k = max(1, min(a.shards, len(rd.batches_for(u["thetas"]))))
        jobs += [dict(unit=u["tag"], shard=j, of=k) for j in range(k)]
    if len(jobs) > MAX_JOBS:
        sys.exit(f"ci_sims: {len(jobs)} jobs exceed GitHub's matrix limit of {MAX_JOBS}; use fewer shards or designs")
    summary(f"### Plan for `{a.args}`\n\n{len(units)} runs: {len(jobs)} matrix jobs"
            f"{' (re-solving cached runs to compare)' if a.force else ''}; {len(skipped)} already cached and skipped"
            + "".join(f"\n- skipped `{t}`" for t in skipped))
    print(json.dumps(dict(include=jobs)))


def cmd_solve(a):
    u = collect(a.args)[a.unit]
    t0 = time.time()
    groups = rd.batches_for(u["thetas"])[a.shard::a.of]
    out = solve_groups(u, groups)
    os.makedirs(a.out, exist_ok=True)
    base = os.path.join(a.out, f"{a.unit}__s{a.shard}of{a.of}")
    np.savez(base + ".npz", **out)
    meta = dict(provenance(), unit=a.unit, design=u["design"], shard=a.shard, of=a.of, draws=len(out["idx"]),
                seconds=round(time.time() - t0, 1))
    json.dump(meta, open(base + ".json", "w"), indent=1)
    summary(f"Solved `{a.unit}` shard {a.shard + 1} of {a.of}: {len(out['idx'])} draws in {meta['seconds']:.0f} s "
            f"(numpy {meta['numpy']}, {meta['os']}, commit {str(meta['commit'])[:12]})")


def cmd_merge(a):
    units = collect(a.args)
    files: dict[str, list[str]] = {}
    for p in sorted(glob.glob(os.path.join(a.parts, "**", "*__s*of*.npz"), recursive=True)):
        files.setdefault(os.path.basename(p).rsplit("__s", 1)[0], []).append(p)
    unknown = sorted(set(files) - set(units))
    if unknown:
        sys.exit(f"ci_sims: parts for runs this stage does not make: {unknown}")
    expected = [t for t, u in units.items() if a.force or not cached(u)]
    missing = [t for t in expected if t not in files]
    if missing:
        sys.exit(f"ci_sims: no parts for {missing}")
    manifest = dict(merge=provenance(), args=a.args, force=a.force, parts=[], new=[], compared={})
    for tag in expected:
        parts = [load(p) for p in files[tag]]
        for p in files[tag]:
            j = p[:-4] + ".json"
            if os.path.exists(j):
                manifest["parts"].append(json.load(open(j)))
        out = assemble(len(units[tag]["thetas"]), parts, tag)
        if os.path.exists(cache_path(tag)):
            manifest["compared"][tag] = compare(load(cache_path(tag)), out)
            if a.resolved:
                os.makedirs(a.resolved, exist_ok=True)
                np.savez(os.path.join(a.resolved, tag + ".npz"), **out)
        else:
            np.savez(cache_path(tag), **out)
            manifest["new"].append(tag)
            print(f"  merged {tag}: {len(out['holds'])} draws; holds {out['holds'].mean():.3f}", file=sys.stderr)
    json.dump(manifest, open(a.manifest, "w"), indent=1, default=str)
    md = [f"### Merge for `{a.args}`", "", f"{len(manifest['new'])} new runs added to results/robust_runs/"]
    md += [f"- `{t}`" for t in manifest["new"]]
    if manifest["compared"]:
        md += ["", "Re-solved runs against the committed cache:", "", compare_table(manifest["compared"])]
    summary("\n".join(md))
    sys.exit(1 if any(c["verdict"] == "differs" for c in manifest["compared"].values()) else 0)


def cmd_repro(a):
    units = collect(a.args)
    tags = a.units.split(",") if a.units else [t for t, u in units.items() if cached(u)]
    rows, t0 = OrderedDict(), time.time()
    for tag in tags:
        u = units[tag]
        if not cached(u):
            sys.exit(f"ci_sims: {tag} is not in the cache; nothing to compare")
        out = solve_groups(u, rd.batches_for(u["thetas"]))
        new = assemble(len(u["thetas"]), [out], tag)
        rows[tag] = compare(load(cache_path(tag)), new)
    meta = dict(provenance(), args=a.args, compared=rows, seconds=round(time.time() - t0, 1))
    if a.manifest:
        json.dump(meta, open(a.manifest, "w"), indent=1, default=str)
    summary(f"### Cache reproducibility for `{a.args}`\n\nRe-solved here (numpy {meta['numpy']}, {meta['os']}, "
            f"commit {str(meta['commit'])[:12]}) in {meta['seconds']:.0f} s and compared with the committed cache.\n\n"
            + compare_table(rows))
    sys.exit(1 if any(c["verdict"] == "differs" for c in rows.values()) else 0)


def _json_diff(a, b, path="$"):
    """Differences between two JSON values: strings, ints and structure exactly, floats to RTOL."""
    if isinstance(a, float) or isinstance(b, float):
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            return [f"{path}: {a!r} != {b!r}"]
        if a == b:
            return []
        return [f"{path}: {a!r} vs {b!r} ({'within' if abs(a - b) <= ATOL + RTOL * abs(a) else 'beyond'} tolerance)"]
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return [f"{path}: keys {sorted(set(a) ^ set(b))} differ"]
        return [d for k in a for d in _json_diff(a[k], b[k], f"{path}.{k}")]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: length {len(a)} != {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in _json_diff(x, y, f"{path}[{i}]")]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


def cmd_compare_checks(a):
    """--check output against the committed copy. The markdown must match exactly apart from its run-time
    line; the JSON must match exactly apart from floats within tolerance, which are still listed."""
    problems, notes = [], []
    for rel in CHECK_FILES:
        ref = _git("show", f"{a.ref}:./{rel}")
        if ref is None:
            sys.exit(f"ci_sims: {rel} is not committed at {a.ref}")
        here = open(os.path.join(rd.HERE, rel)).read()
        if rel.endswith(".md"):
            strip = lambda s: [ln for ln in s.splitlines() if not ln.startswith("(checks took")]
            if strip(ref) != strip(here):
                import difflib
                problems.append(f"{rel} differs:\n```diff\n" + "\n".join(difflib.unified_diff(
                    strip(ref), strip(here), "committed", "this run", lineterm="")) + "\n```")
        else:
            for d in _json_diff(json.loads(ref), json.loads(here)):
                (problems if "within tolerance" not in d else notes).append(f"{rel} {d}")
    md = ["### `robust_design.py --check` against the committed reference", ""]
    md += ["Matches the committed output." if not problems else "**Differs from the committed output.**"]
    md += [f"- {p}" for p in problems] + [f"- float noise, not a failure: {n}" for n in notes]
    summary("\n".join(md))
    sys.exit(1 if problems else 0)


def cmd_collect_outputs(a):
    """Copy every file under the model folder that git sees as new or modified into a.out (same paths),
    so a person can review and commit them. Nothing is committed here."""
    st = subprocess.run(["git", "status", "--porcelain", "-z", "--untracked-files=all", "--no-renames", "."],
                        cwd=rd.HERE, capture_output=True, text=True, check=True).stdout   # not stripped: " M path"
    root = _git("rev-parse", "--show-toplevel")
    copied = []
    for entry in filter(None, st.split("\0")):
        code, path = entry[:2], entry[3:]
        if "D" in code:
            continue
        src = os.path.join(root, path)
        dst = os.path.join(a.out, os.path.relpath(src, rd.HERE))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(src, "rb") as f, open(dst, "wb") as g:
            g.write(f.read())
        copied.append(os.path.relpath(src, rd.HERE))
    summary(f"{len(copied)} new or changed files kept for review (paths relative to the model folder):"
            + "".join(f"\n- `{c}`" for c in copied))


def cmd_provenance(a):
    json.dump(dict(provenance(), note=a.note), open(a.out, "w"), indent=1, default=str)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-dir", default=None, help="cache folder instead of results/robust_runs/")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--args", required=True)
    p.add_argument("--shards", type=int, default=1)
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("solve")
    p.add_argument("--args", required=True)
    p.add_argument("--unit", required=True)
    p.add_argument("--shard", type=int, default=0)
    p.add_argument("--of", type=int, default=1)
    p.add_argument("--out", required=True)
    p = sub.add_parser("merge")
    p.add_argument("--args", required=True)
    p.add_argument("--parts", required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--resolved", default=None, help="folder for re-solved copies of cached runs (with --force)")
    p.add_argument("--manifest", default="ci_manifest.json")
    p = sub.add_parser("repro")
    p.add_argument("--args", required=True)
    p.add_argument("--units", default=None, help="comma-separated run names; default every cached run of the stage")
    p.add_argument("--manifest", default=None)
    p = sub.add_parser("compare-checks")
    p.add_argument("--ref", default="HEAD")
    p = sub.add_parser("collect-outputs", help="copy new or changed model files to a folder for upload")
    p.add_argument("--out", required=True)
    p = sub.add_parser("provenance", help="write provenance JSON for a run made outside this script")
    p.add_argument("--out", required=True)
    p.add_argument("--note", default="")
    a = ap.parse_args()
    if a.runs_dir:
        rd.RUNS = os.path.abspath(a.runs_dir)
        os.makedirs(rd.RUNS, exist_ok=True)
    dict(plan=cmd_plan, solve=cmd_solve, merge=cmd_merge, repro=cmd_repro,
         provenance=cmd_provenance,
         **{"compare-checks": cmd_compare_checks, "collect-outputs": cmd_collect_outputs})[a.cmd](a)


if __name__ == "__main__":
    main()
