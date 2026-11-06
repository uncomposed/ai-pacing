"""
State-dependent strike odds (2026-10-29 overnight run): do bad odds stop deadline-driven strikes?

The canonical solver uses one base strike success p_s0 in every state; the odds already improve with relative capacity
through the failure term (1 - p_s0) (D / (D + A))^eps. Cole's worry is a lab-internal model about to be superseded
that strikes at BAD odds. This file adds one option, ps_dep: wherever the AI is under a live deprecation hazard
(p_dep > 0 in the pact, p_dep dep_coll > 0 after collapse), a strike's base success is ps_dep instead of p_s0:

    p_f = (1 - ps_dep) (D_m / (D_m + A))^eps      (the capacity term is unchanged)

ps_dep = 0 is off (p_s0 everywhere). Policing odds keep p_s0. The option lives in a patched copy of
equilibrium_model.py built in memory (the precedent is diagnostics/noretry.py), so the canonical solver, its source
hash and every committed cache identity are untouched. PATCHES lists every replacement; each must match once.

    python3 strike_odds.py --check --runs-dir DIR    # default reproduces committed caches; two exact identities
    python3 strike_odds.py --solve --runs-dir DIR    # dep, dep_w, dep_coll, cole x ps_dep 0.1/0.2/0.3, r0.1 box
    python3 strike_odds.py --report --runs-dir DIR   # results/strike_odds.{md,json}

Status: implemented. Not human_validated.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import types
from concurrent.futures import ProcessPoolExecutor

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np

import breakout_options as bo
import equilibrium_model as em
import robust_design as rd
import run_identity as ri

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
WORKERS = int(os.environ.get("SO_WORKERS", "4"))


def patches():
    """(old, new) source replacements applied to equilibrium_model.py; each old string must occur exactly once."""
    return [
        ('''    ("p_s0",     (0.5, 0.05, 0.95, "lin", "Strike success probability for a seed-sized AI",
                  "Same as offearth_model.py; unknowable.")),
''',
         '''    ("p_s0",     (0.5, 0.05, 0.95, "lin", "Strike success probability for a seed-sized AI",
                  "Same as offearth_model.py; unknowable.")),
    ("ps_dep",   (0.0, 0.0, 1.0, "lin", "Strike base success while the AI is under a live deprecation hazard; 0 = off (p_s0)",
                  "strike_odds.py (2026-10-29). Cole: a lab-internal model about to be superseded may strike at bad odds.")),
'''),
        ('''        pf = (1 - P["p_s0"]) * np.power(Dm / (Dm + A), P["eps"])
        if _pass == "belief":
            pf = np.minimum(1.0, pf * P["pf_bel"])
''',
         '''        pf = (1 - P["p_s0"]) * np.power(Dm / (Dm + A), P["eps"])
        if _pass == "belief":
            pf = np.minimum(1.0, pf * P["pf_bel"])
        pfd = (1 - P["ps_dep"]) * np.power(Dm / (Dm + A), P["eps"])
        if _pass == "belief":
            pfd = np.minimum(1.0, pfd * P["pf_bel"])
'''),
        ('''        return dict(p_f=pf, cost=cS, As=(As0, As1), w=(G.wA(As0), G.wA(As1)))
''',
         '''        return dict(p_f=pf, p_fd=pfd, cost=cS, As=(As0, As1), w=(G.wA(As0), G.wA(As1)))
'''),
        ('''    dfac_c = 1 - p_dep * (1 - P["preserve_w"]) * P["dep_coll"]          # after the pact has collapsed
''',
         '''    dfac_c = 1 - p_dep * (1 - P["preserve_w"]) * P["dep_coll"]          # after the pact has collapsed
    use_psd = use_dep and on("ps_dep")
    if use_psd and store:
        raise ValueError("store/simulate does not support ps_dep")
    dep_live = (p_dep > 0, p_dep * P["dep_coll"] > 0)                   # (pact, collapsed): deprecation can strike
'''),
        ('''            p_f = CF[mL[m]]["p_f"]
            Vsucc_c = Vsucc_L[mL[m]]
''',
         '''            p_f = CF[mL[m]]["p_f"]
            if use_psd:
                p_f = np.where(dep_live[mbase[m] > 0], CF[mL[m]]["p_fd"], p_f)
            Vsucc_c = Vsucc_L[mL[m]]
'''),
    ]


def build():
    """The patched solver as module em_sd (registered in sys.modules)."""
    if "em_sd" in sys.modules:
        return sys.modules["em_sd"]
    with open(os.path.join(HERE, "equilibrium_model.py"), encoding="utf-8") as f:
        src = f.read()
    for old, new in patches():
        n = src.count(old)
        if n != 1:
            raise RuntimeError(f"strike_odds: a patch matches {n} times in equilibrium_model.py (expected 1):\n{old}")
        src = src.replace(old, new)
    mod = types.ModuleType("em_sd")
    mod.__file__ = os.path.join(HERE, "equilibrium_model.py")
    sys.modules["em_sd"] = mod
    exec(compile(src, "em_sd(equilibrium_model.py + strike_odds.patches)", "exec"), mod.__dict__)
    return mod


sd = build()

# configuration -> breakout options (from breakout_options.CONFIGS)
CONFIGS = {k: bo.CONFIGS[k][0] for k in ("off", "dep", "dep_w", "dep_coll", "cole")}
PS = [0.1, 0.2, 0.3]
RUN_CFGS = ("dep", "dep_w", "dep_coll", "cole")


def _solve(args):
    plist, kw = args
    r = sd.solve(sd.batch([sd.baseline(**p) for p in plist]), N=kw["N"], T_H=kw["T_H"], nA=kw["nA"])
    out = {k: np.asarray(r[k], float) if k in r else np.zeros(len(plist)) for k in bo.KEEP}
    out["act0"] = np.asarray(r["act0"]).astype("U1")
    return out


def run_ens(thetas, design, opts, pool, tag, runs=None):
    """Like breakout_options.run_ens, on the patched solver. runs=None: no cache."""
    want = ri.request("strike_odds", "r0.1", thetas, design, bo.CFG, opts) if runs else None
    path = os.path.join(runs, f"r0.1__{tag}.npz") if runs else None
    if runs:
        hit = ri.load_cached(path, want)
        if hit is not None:
            return hit
    params = [dict(rd.apply_design(t, design), **opts) for t in thetas]
    groups = rd.batches_for(thetas)
    t0 = time.time()
    res = list(pool.map(_solve, [([params[i] for i in g], bo.CFG) for g in groups]))
    out = {k: np.empty(len(thetas), float) for k in bo.KEEP}
    out["act0"] = np.empty(len(thetas), "U1")
    for g, r in zip(groups, res):
        for k in out:
            out[k][g] = r[k]
    if runs:
        ri.save_cached(path, out, want, produced=dict(by="strike_odds.run_ens", batches=len(groups)))
    print(f"  r0.1 {tag}: {len(thetas)} draws in {time.time() - t0:.0f} s; holds {bo.holds(out).sum()}", flush=True)
    return out


def maxdiff(a, b):
    return max(float(np.nanmax(np.abs(a[k] - b[k]))) for k in bo.KEEP if k in a and k in b)


def checks(pool):
    th = bo.boxes()["r0.1"]
    L, data = [], {"default": [], "identity": []}
    # 1. default (ps_dep 0): against the canonical solver re-solved now, and against the committed caches
    rows = []
    for cfg, op in CONFIGS.items():
        for des, dv in bo.DESIGNS.items():
            old = ri.load_for_read(os.path.join(bo.RUNS, f"r0.1__{des}__{cfg}.npz"))
            new = run_ens(th, dv, op, pool, f"chk_{des}_{cfg}")
            params = [dict(rd.apply_design(t, dv), **op) for t in th]
            groups = rd.batches_for(th)
            res = list(pool.map(bo._solve, [([params[i] for i in g], bo.CFG) for g in groups]))
            can = {k: np.empty(len(th), new[k].dtype) for k in new}
            for g, r in zip(groups, res):
                for k in can:
                    can[k][g] = r[k]
            dc, sc = maxdiff(new, can), bool(np.all(new["act0"] == can["act0"]))
            d, same = maxdiff(new, old), bool(np.all(new["act0"] == old["act0"]))
            hs = bool(np.all(bo.holds(new) == bo.holds(old)))
            rows.append([cfg, des, f"{dc:.3g}", sc, f"{d:.3g}", same, hs, int(bo.holds(new).sum())])
            data["default"].append(dict(config=cfg, design=des, maxdiff_canonical=dc, act0_same_canonical=sc,
                                        maxdiff_committed=d, act0_same_committed=same, holds_same_committed=hs))
    L.append("1. Patched solver with ps_dep 0 (the default) against the canonical solver re-solved in this process "
             "(must be bit-identical), and against the committed caches `results/breakout_runs/r0.1__<design>__<config>.npz` "
             "(opening moves and hold decisions must match; the largest absolute difference over every kept number is "
             "reported):\n\n" +
             rd.md_table(rows, ["config", "design", "max diff vs canonical", "act0 same", "max diff vs committed",
                                "act0 same", "holds same", "holds"]))
    # 2. identities: (a) deprecation live everywhere -> ps_dep x equals p_s0 x; (b) ps_dep = each draw's p_s0 is a no-op
    g = rd.batches_for(th)[0]
    sub = [th[i] for i in g]
    rows = []
    every = dict(bo.TRACK, h_dep=0.1, dep_coll=1.0, dep_post=1.0)
    for des, dv in bo.DESIGNS.items():
        for x in (0.1, 0.3):
            a = run_ens(sub, dv, dict(every, ps_dep=x), pool, "")
            b = run_ens([dict(t, p_s0=x) for t in sub], dv, every, pool, "")
            rows.append([f"deprecation everywhere (dep_coll 1, dep_post 1), ps_dep {x:g} vs p_s0 {x:g}", des,
                         f"{maxdiff(a, b):.3g}", bool(np.all(a["act0"] == b["act0"]))])
        op = CONFIGS["dep"]
        p0 = [dict(rd.apply_design(t, dv), **op) for t in sub]
        a = {k: v for k, v in _solve(([dict(p, ps_dep=p["p_s0"]) for p in p0], bo.CFG)).items()}
        b = _solve((p0, bo.CFG))
        rows.append(["dep: ps_dep equal to each draw's p_s0 vs ps_dep 0 (a no-op)", des, f"{maxdiff(a, b):.3g}",
                     bool(np.all(a["act0"] == b["act0"]))])
    for r in rows:
        data["identity"].append(dict(case=r[0], design=r[1], maxdiff=float(r[2]), act0_same=r[3]))
    L.append(f"2. Identities on one solver batch ({len(sub)} draws of the r0.1 box), each should be exact:\n\n" +
             rd.md_table(rows, ["case", "design", "max diff", "act0 same"]))
    # 3. closed form in the static pre-closure world: deadline hazard at which a one-shot strike beats cooperating
    rows = []
    for x in (0.5, 0.3, 0.2, 0.1):
        t = em.deadline_thresholds(em.baseline(**bo.STATIC, p_s0=x), bo.STATIC["A0"])
        rows.append([x, f"{t['p_f']:.3f}", f"{t['h_strike']:.4f}", f"{t['h_exit']:.4f}"])
        data.setdefault("static", []).append(dict(odds=x, p_f=t["p_f"], h_strike=t["h_strike"], h_exit=t["h_exit"]))
    L.append("3. Closed form (`deadline_thresholds`, canonical solver module) in the static pre-closure world of "
             "breakout_options --check: the deprecation hazard above which a one-shot strike beats cooperating "
             "forever, by base odds (preserve_w 0):\n\n" +
             rd.md_table(rows, ["base strike success", "failure prob. at A0", "h_dep for strike", "h_dep for exit"]))
    ok = all(r["maxdiff_canonical"] == 0 and r["act0_same_canonical"] and r["act0_same_committed"]
             and r["holds_same_committed"] for r in data["default"]) and \
        all(r["maxdiff"] < 1e-12 and r["act0_same"] for r in data["identity"])
    L.append(f"\nVerdict: {'PASS' if ok else 'FAIL'} (default bit-identical to the canonical solver, same decisions as "
             "the committed caches; identities within 1e-12).")
    return "\n".join(L), data, ok


def solve(pool, runs, ps=None):
    th = bo.boxes()["r0.1"]
    for x in ps or PS:
        for cfg in RUN_CFGS:
            for des, dv in bo.DESIGNS.items():
                run_ens(th, dv, dict(CONFIGS[cfg], ps_dep=x), pool, f"{des}__{cfg}__ps{x:g}", runs)


def report(runs):
    n = rd.N_RAD
    data, L = [], ["# State-dependent strike odds (auto-generated by strike_odds.py --report)", "",
                   "r0.1 box, 64 draws (seed 105). ps_dep replaces the base strike success p_s0 wherever the AI is "
                   "under a live deprecation hazard; 'p_s0' rows (ps_dep off) are the committed breakout caches. "
                   "holds = cooperate at t = 0 and P(strike within 300 years) < 1%; rival-aware also needs "
                   "P(rival) < 0.5. Counts are sampling-measure outcomes, not probabilities; Wilson 90% intervals.", ""]
    rows = []
    for cfg in ("off",) + RUN_CFGS:
        for des in bo.DESIGNS:
            for x in ([None] if cfg == "off" else [None] + PS):
                if x is None:
                    r = ri.load_for_read(os.path.join(bo.RUNS, f"r0.1__{des}__{cfg}.npz"))
                else:
                    r = ri.load_for_read(os.path.join(runs, f"r0.1__{des}__{cfg}__ps{x:g}.npz"))
                k, kr = int(bo.holds(r).sum()), int(bo.holds_rival(r).sum())
                lo, hi = rd.ci(k / n, n)
                s = dict(config=cfg, design=des, ps_dep=x, holds=k, holds_rival=kr, ci90=[lo, hi],
                         strike_now=int(np.sum(np.isin(r["act0"], ["S", "D"]))), exit_now=int(np.sum(r["act0"] == "X")),
                         p_strike=float(r["att"].mean()), p_succ=float(r["suc"].mean()),
                         t_strike=float(np.sum(r["t_mean"] * r["att"]) / max(r["att"].sum(), 1e-12)))
                data.append(s)
                rows.append([cfg, des, "p_s0 (off)" if x is None else f"{x:g}", f"{k} ({lo:.2f}-{hi:.2f})", kr,
                             s["strike_now"], s["exit_now"], f"{s['p_strike']:.3f}", f"{s['p_succ']:.3f}",
                             f"{s['t_strike']:.1f}"])
    L.append(rd.md_table(rows, ["config", "design", "strike odds under deadline", "holds (90% CI)", "rival-aware",
                                "strike now", "exit now", "mean P(strike)", "mean P(success)",
                                "mean strike year (P(strike)-weighted)"]) + "\n")
    leg = ri.legacy_read_summary()
    if leg:
        L.append(f"Reading note: {leg}.\n")
    old = open(os.path.join(RES, "strike_odds.md")).read() if os.path.exists(os.path.join(RES, "strike_odds.md")) else ""
    chk = old[old.index("## Checks"):] if "## Checks" in old else ""
    open(os.path.join(RES, "strike_odds.md"), "w").write("\n".join(L) + "\n" + chk)
    prev = json.load(open(os.path.join(RES, "strike_odds.json"))) if os.path.exists(os.path.join(RES, "strike_odds.json")) else {}
    json.dump(dict(prev, runs=data), open(os.path.join(RES, "strike_odds.json"), "w"), indent=1)
    print("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--solve", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--runs-dir", required=True, help="cache folder; must not be results/breakout_runs")
    ap.add_argument("--ps", default=None, help="comma-separated ps_dep values for --solve (default: all of PS)")
    a = ap.parse_args()
    runs = os.path.abspath(a.runs_dir)
    if runs == os.path.abspath(bo.RUNS):
        raise SystemExit("strike_odds.py: --runs-dir must not be the committed cache folder")
    os.makedirs(runs, exist_ok=True)
    with ProcessPoolExecutor(WORKERS) as pool:
        if a.check:
            txt, data, ok = checks(pool)
            md = os.path.join(RES, "strike_odds.md")
            head = open(md).read().split("## Checks")[0] if os.path.exists(md) else "# State-dependent strike odds\n\n"
            open(md, "w").write(head + "## Checks (strike_odds.py --check)\n\n" + txt + "\n")
            js = os.path.join(RES, "strike_odds.json")
            prev = json.load(open(js)) if os.path.exists(js) else {}
            json.dump(dict(prev, checks=data, checks_pass=ok), open(js, "w"), indent=1, default=float)
            print(txt, flush=True)
            if not ok:
                raise SystemExit("strike_odds.py --check FAILED")
        if a.solve:
            solve(pool, runs, [float(x) for x in a.ps.split(",")] if a.ps else None)
    if a.report:
        report(runs)


if __name__ == "__main__":
    main()
