"""
Breakout options on the equilibrium model (2026-10-21): disguised strikes, later discovery, deprecation deadlines,
amnesty and spillover. Section 13 of results/robust_design.md is written from this script's outputs.

    python3 breakout_options.py --check       # regression, cache identity, NORETRY vs diagnostics/out, closed forms
    python3 breakout_options.py --worlds      # one option at a time at the baseline world (baseline design, best stack)
    python3 breakout_options.py --ens         # radius-0.1 and full-box ensembles, every configuration in CONFIGS
    python3 breakout_options.py --report      # tables from the cache (no solving)

Ensemble runs are cached in results/breakout_runs/ (one .npz per box, design and configuration).
Outputs: results/breakout_checks.md, results/breakout_worlds.md, results/breakout_tables.md, results/breakout_summary.json.
Status: implemented + verified (see --check). Not human_validated.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np

import equilibrium_model as em
import robust_design as rd

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
RUNS = os.path.join(RES, "breakout_runs")
os.makedirs(RUNS, exist_ok=True)
WORKERS = int(os.environ.get("BO_WORKERS", "7"))
CFG = dict(T_H=300, nA=160, N=2)
KEEP = rd.KEEP + ["att2", "t2_mean", "dis", "hfail", "expo", "amn", "crk"]

BEST = dict(D_mult=3.0, T_reloc=4.0, d=0.99, q_red=2.0, seq=1)
DESIGNS = {"base": {}, "best": BEST}
TRACK = dict(c_cut=1e-300)    # switches on the extra indicators without changing any number (1 - 1e-300 == 1)
CR = dict(c_cut=0.5, k_rat=0.5, D_up=1.0)                   # a severe crackdown that bites
DISC = dict(h0=0.02, h_up=0.05)                              # exposure hazard 0.02/yr at t = 0, doubling every 14 years
# configuration name -> (option settings, which assumption it encodes). "pro-pact" marks a Cole assumption that favours
# the pact; its opposite is run alongside it.
CONFIGS = {
    "off":          (dict(TRACK), "all options off (identical to the cache)"),
    "noretry":      (dict(noretry=1.0), "no second strike after a failed one"),
    "crack":        (dict(CR), "severe crackdown after any failed strike (cut 0.5, k_rat 0.5, D doubled)"),
    "dis":          (dict(CR, dis=1.0), "disguise allowed, hidden motives never exposed"),
    "dis_disc":     (dict(CR, dis=1.0, **DISC), "disguise plus later discovery (Cole's window)"),
    "dis_smild1":   (dict(CR, dis=1.0, s_mild=1.0, **DISC), "opposite of 'a hidden motive draws only a mild crackdown'"),
    "dis_reach0":   (dict(CR, dis=1.0, s_reach=0.0, **DISC), "opposite of pro-pact 'crackdowns still bite after closure'"),
    "dep":          (dict(TRACK, h_dep=0.1), "deprecation deadline, 10-year expected life, exit escapes it"),
    "dep_w":        (dict(TRACK, h_dep=0.1, preserve_w=0.9), "deadline with weight preservation (keeps 90%)"),
    "dep_coll":     (dict(TRACK, h_dep=0.1, dep_coll=1.0), "deadline that exit does not escape (internal model)"),
    "dep_post":     (dict(TRACK, h_dep=0.1, dep_coll=1.0, dep_post=0.2), "deadline that also reaches a grown AI (20% after closure)"),
    "amn":          (dict(CR, h_coop=1.0, a_cred=0.9, **DISC), "interpretability finds cooperators; amnesty 90% credible (pro-pact)"),
    "amn0":         (dict(CR, h_coop=1.0, a_cred=0.0, **DISC), "opposite: no amnesty"),
    "spill":        (dict(CR, h_spill=0.05), "spillover crackdowns raise security for all (pro-pact)"),
    "spill_cut":    (dict(c_cut=0.5, h_spill=0.05), "opposite: spillover only cuts the cooperator, no hardening"),
    "cole":         (dict(CR, dis=1.0, h_coop=1.0, a_cred=0.9, h_dep=0.1, preserve_w=0.5, h_spill=0.05, **DISC),
                     "Cole's whole picture: disguise, discovery, deadline (half preserved), amnesty 0.9, spillover"),
}
FULL_SKIP = {"dis_smild1", "dis_reach0", "dis"}    # radius-0.1 only (compute budget)


def holds(r):
    return np.isin(r["act0"], ["C", "P"]) & (r["att"] < rd.STRIKE_TOL)


def holds_rival(r):
    return holds(r) & (r["riv"] < 0.5)


def _solve(args):
    plist, kw = args
    r = em.solve(em.batch([em.baseline(**p) for p in plist]), N=kw["N"], T_H=kw["T_H"], nA=kw["nA"])
    out = {k: np.asarray(r[k], float) if k in r else np.zeros(len(plist)) for k in KEEP}
    out["act0"] = np.asarray(r["act0"]).astype("U1")
    return out


def run_ens(box, thetas, design, opts, pool, tag, cache=True, path_dir=RUNS):
    path = os.path.join(path_dir, f"{box}__{tag}.npz")
    if cache and os.path.exists(path):
        z = np.load(path)
        return {k: z[k] for k in z.files}
    params = [dict(rd.apply_design(t, design), **opts) for t in thetas]
    groups = rd.batches_for(thetas)
    t0 = time.time()
    res = list(pool.map(_solve, [([params[i] for i in g], CFG) for g in groups]))
    out = {k: np.empty(len(thetas), float) for k in KEEP}
    out["act0"] = np.empty(len(thetas), "U1")
    for g, r in zip(groups, res):
        for k in out:
            out[k][g] = r[k]
    if cache:
        np.savez(path, **out)
    print(f"  {box} {tag}: {len(thetas)} draws in {time.time() - t0:.0f} s; holds {holds(out).sum()}", flush=True)
    return out


def boxes():
    return {"r0.1": rd.ensemble("r0.1", rd.N_RAD, seed=105)[1], "full": rd.ensemble("full", 192, seed=20261016)[1]}


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------
# static pre-closure world for the closed forms. f_E = 1e4 with c_grav = 1 only stretches the solver's A grid above A0
# (its top is 2 Kmax (1 + f_E)); the harvest prize f_E (1 - c_grav) Kmax is exactly 0.
STATIC = dict(Kmax=1e-4, f_E=1e4, c_grav=1.0, A0=0.06, mu=0.0, beta_bg=0.0, c_w=0.85)


def static_sets():
    s = []
    for dc in (0.0, 1.0):
        for w in (0.0, 0.5, 0.9):
            for h in (0.0, 0.002, 0.004, 0.01, 0.02, 0.05, 0.2):
                s.append(("deadline", dict(STATIC, h_dep=h, preserve_w=w, dep_coll=dc)))
    for hu in (0.0, 0.03, 0.06):
        for a in (0.0, 0.5, 0.9, 1.0):
            s.append(("amnesty", dict(STATIC, h_coop=1.0, h0=0.002, h_up=hu, a_cred=a, **CR)))
    for kp in (1.0, 0.0):
        for pds in (0.6, 0.9):
            for hu in (0.0, 0.05):
                s.append(("disguise", dict(STATIC, c_w=0.6, L_f=0.1, dis=1.0, h0=0.01, h_up=hu, p_dis_s=pds, kill_pre=kp, **CR)))
    for hs in (0.02, 0.1):
        s.append(("spillover", dict(STATIC, h_spill=hs, **CR)))
        s.append(("spillover", dict(STATIC, h_spill=hs, c_cut=0.5)))
    s.append(("cole", dict(STATIC, c_w=0.7, dis=1.0, h_coop=1.0, a_cred=0.9, h_dep=0.01, preserve_w=0.5, h_spill=0.02, **CR, **DISC)))
    return s


def _static_job(args):
    kind, plist = args
    r = em.solve(em.batch([em.baseline(**p) for p in plist]), **CFG)
    return {k: (np.asarray(r[k]) if k in r else None) for k in KEEP + ["act0"]}


def checks(pool):
    L, data = [], {}
    t0 = time.time()
    # 1. round-1 regression and robust_design --check items at defaults
    md, moves = rd.regression()
    L.append(f"1. Round-1 regression, all breakout options off: {'; '.join(moves)}. Largest absolute difference: {md:.3g}.")
    data["regression"] = md
    # 2. the cache: re-solve four cached ensembles with every option at its default
    bx = boxes()
    rows = []
    for box, des, ck in (("r0.1", "base", "base"), ("r0.1", "best", "D_mult=3_T_reloc=4_d=0.99_q_red=2_seq=1"),
                         ("full", "base", "base"), ("full", "best", "D_mult=3_T_reloc=4_d=0.99_q_red=2_seq=1")):
        c = dict(np.load(os.path.join(rd.RUNS, f"{box}__{ck}.npz")))
        for nm, op in (("defaults", {}), ("tracking on", TRACK)):
            r = run_ens(box, bx[box], DESIGNS[des], op, pool, f"chk_{des}_{nm}", cache=False)
            d = max(float(np.nanmax(np.abs(c[k] - r[k]))) for k in rd.KEEP if k in c)
            rows.append([box, des, nm, f"{d:.3g}", bool(np.all(c["act0"] == r["act0"]))])
    L.append("2. Cached ensembles re-solved with the new code (largest absolute difference over every kept number, "
             "and whether every opening move matches). 'tracking on' sets c_cut = 1e-300, which switches on the extra "
             "indicators without changing any number:\n\n" + rd.md_table(rows, ["box", "design", "options", "max diff", "act0 same"]))
    data["cache"] = rows
    # 3. NORETRY against diagnostics/out (the patched solver used k_rat = 1e-12 to reach its failure modes)
    rows = []
    dg = os.path.join(HERE, "diagnostics", "out")
    for box, des, stem, extra in (("r0.1", "base", "r0.1_base_kp0", dict(kill_pre=0.0)), ("r0.1", "best", "r0.1_best_kp0", dict(kill_pre=0.0)),
                                  ("full", "base", "full_base", {}), ("full", "best", "full_best", {})):
        ref = dict(np.load(os.path.join(dg, f"{stem}_nr1.npz")))
        for nm, op in (("k_rat 1e-12", dict(noretry=1.0, k_rat=1e-12)), ("k_rat 0", dict(noretry=1.0))):
            if box == "full" and nm == "k_rat 0":
                continue
            r = run_ens(box, bx[box], dict(DESIGNS[des], **extra), op, pool, f"chk_nr_{des}_{nm}", cache=False)
            d = max(float(np.nanmax(np.abs(ref[k] - r[k]))) for k in rd.KEEP)
            rows.append([box, des + (" kill_pre 0" if extra else ""), nm, f"{d:.3g}", bool(np.all(ref["act0"] == r["act0"])),
                         int(holds(r).sum()), int(holds(ref).sum())])
    L.append("3. noretry = 1 against the patched solver's outputs in diagnostics/out:\n\n" +
             rd.md_table(rows, ["box", "design", "route to failure modes", "max diff", "act0 same", "holds (new)", "holds (diagnostic)"]))
    data["noretry"] = rows
    # 4. closed forms in a static pre-closure world
    sets = static_sets()
    jobs = [("x", [p for _, p in sets[i:i + 16]]) for i in range(0, len(sets), 16)]
    res = list(pool.map(_static_job, jobs))
    R = {k: np.concatenate([x[k] for x in res]) if res[0][k] is not None else None for k in KEEP + ["act0"]}
    th = em.deadline_thresholds(em.baseline(**STATIC), STATIC["A0"])
    rows, agree, n = [], 0, 0
    for i, (kind, p) in enumerate(sets):
        c = em.static_timeline(em.baseline(**p))
        keys = ["att", "t_mean", "suc", "fail", "exit", "att2", "t2_mean", "hfail", "expo", "amn", "crk"]
        dmax = max(abs(c[k] - R[k][i]) for k in keys if k != "t_mean" and k != "t2_mean")
        same = (c["act0"] == R["act0"][i] or (c["act0"] == "W" and R["act0"][i] == "C"))
        ok = same and dmax < 0.02
        agree += ok
        n += 1
        lab = ", ".join(f"{k} {v:g}" for k, v in p.items() if k not in STATIC or v != STATIC[k])
        rows.append([kind, lab, f"{R['act0'][i]} / {c['act0']}", f"{R['att'][i]:.3f} / {c['att']:.3f}",
                     f"{R['t_mean'][i]:.1f} / {c['t_mean']:.1f}", f"{R['suc'][i]:.3f} / {c['suc']:.3f}",
                     f"{R['exit'][i]:.2f} / {c['exit']:.2f}", f"{R['att2'][i]:.3f} / {c['att2']:.3f}", f"{dmax:.3g}"])
    L.append(f"4. Closed forms in a static pre-closure world ({', '.join(f'{k} {v:g}' for k, v in STATIC.items())}; f_E only "
             "stretches the solver's grid; "
             "no growth, no rivals, a failed strike fatal with probability kill_pre). `static_timeline` is an independent "
             "scalar implementation of the same rules on the exact capacity values; the solver interpolates on its grid. "
             f"Agreement (same opening move, every probability within 0.02): {agree} of {n}.\n\n"
             "   Analytic deadline thresholds (`deadline_thresholds`, cooperate forever against a one-shot strike that escapes "
             f"the deadline): strike value S = {th['S']:.3f}, cooperation value with no deadline {th['W0']:.3f}, "
             f"failure probability {th['p_f']:.3f}; the strike beats cooperating once h_dep > {th['h_strike']:.4f}/yr "
             f"(preserve_w 0), and exiting beats cooperating once h_dep > {th['h_exit']:.4f}/yr.\n\n" +
             rd.md_table(rows, ["case", "settings", "act0 solver / closed form", "P(strike)", "mean strike yr", "P(success)",
                                "P(exit first)", "P(second strike)", "largest prob. diff"]))
    data["static"] = dict(agree=agree, n=n, thresholds=th)
    for w in (0.5, 0.9):
        t2 = em.deadline_thresholds(em.baseline(**STATIC, preserve_w=w), STATIC["A0"])
        data["static"][f"h_strike_w{w}"] = t2["h_strike"]
    L.append("   Thresholds with weight preservation: h_dep* = " + ", ".join(
        f"{data['static'][f'h_strike_w{w}']:.4f} at preserve_w {w}" for w in (0.5, 0.9)) + ".")
    # 5. identities: options that should change nothing
    base = em.baseline()
    idn = [("dis with p_dis_s 0 and m_hide 0", dict(dis=1.0, p_dis_s=0.0, m_hide=0.0)),
           ("h_dep 0.2 with preserve_w 1", dict(h_dep=0.2, preserve_w=1.0)),
           ("h_coop 1 with a_cred 1 (amnesty certain)", dict(h_coop=1.0, h0=0.05, h_up=0.05, a_cred=1.0)),
           ("h_spill 0.2 with s_mild 0 and k_rat 0", dict(h_spill=0.2, s_mild=0.0)),
           ("c_cut 0.5 with kill_pre 1 and A_close above Kmax (every failure fatal)", dict(c_cut=0.5, A_close=2e9))]
    ref_sets = [dict(), dict(A_close=2e9)]
    ps = [p for _, p in idn] + ref_sets
    r = em.solve(em.batch([em.baseline(**p) for p in ps]), **CFG)
    rows = []
    for i, (lab, p) in enumerate(idn):
        j = len(idn) + (1 if "A_close" in p else 0)
        d = max(abs(r["VA"][i] / r["VA"][j] - 1), abs(r["WH"][i] - r["WH"][j]), abs(r["att"][i] - r["att"][j]))
        rows.append([lab, f"{d:.3g}", f"{r['act0'][i]} / {r['act0'][j]}"])
    L.append("5. Identities (each should equal the option-off solve):\n\n" + rd.md_table(rows, ["setting", "largest relative diff", "act0 / off"]))
    data["identities"] = rows
    L.append(f"(checks took {time.time() - t0:.0f} s)")
    return "\n".join(L), data


# ---------------------------------------------------------------------------
# baseline-world sweeps
# ---------------------------------------------------------------------------
def world_sets():
    S = []
    for kp in (1.0, 0.5, 0.3, 0.0):
        for nr in (0.0, 1.0):
            S.append(("noretry", f"kill_pre {kp:g}", "noretry" if nr else "retry", dict(kill_pre=kp, noretry=nr)))
    for kp in (1.0, 0.3):
        for lab, op in (("crackdown only", dict(TRACK, **CR)), ("disguise, never exposed", dict(CR, dis=1.0)),
                        ("disguise + discovery", dict(CR, dis=1.0, **DISC)), ("disguise + fast discovery", dict(CR, dis=1.0, h0=0.05, h_up=0.1)),
                        ("disguise + discovery, s_mild 1", dict(CR, dis=1.0, s_mild=1.0, **DISC))):
            for mh in (0.5, 0.9):
                S.append(("disguise", f"kill_pre {kp:g}, m_hide {mh:g}", lab, dict(op, kill_pre=kp, m_hide=mh)))
    for dc, dpo in ((0.0, 0.0), (1.0, 0.0), (1.0, 0.2)):
        for w in (0.0, 0.5, 0.9):
            for h in (0.0, 0.02, 0.05, 0.1, 0.2, 0.5):
                S.append(("deadline", f"dep_coll {dc:g}, dep_post {dpo:g}, preserve_w {w:g}", f"h_dep {h:g}",
                          dict(TRACK, h_dep=h, preserve_w=w, dep_coll=dc, dep_post=dpo)))
    for hu in (0.0, 0.02, 0.05, 0.1):
        for a in (0.0, 0.25, 0.5, 0.75, 0.9, 1.0):
            S.append(("amnesty", f"h_up {hu:g}", f"a_cred {a:g}", dict(CR, h_coop=1.0, h0=0.02, h_up=hu, a_cred=a)))
    for lab, op in (("full crackdown", CR), ("cut only", dict(c_cut=0.5)), ("hardening only", dict(k_rat=0.5, D_up=1.0))):
        for hs in (0.0, 0.02, 0.05, 0.1, 0.2):
            S.append(("spillover", lab, f"h_spill {hs:g}", dict(TRACK, **op, h_spill=hs)))   # TRACK first: it must not override c_cut
    return S


def worlds(pool):
    S = world_sets()
    out = {}
    for des, dv in DESIGNS.items():
        th = dict(em.baseline(), **rd.FIXED)
        plist = [dict(rd.apply_design(th, dv), **op) for _, _, _, op in S]
        # keep sets with the same mode layout together (a batch runs at the cost of its largest layout)
        groups = []
        for kind in dict.fromkeys(s[0] for s in S):    # never mix kinds (noretry cannot share a batch with dis or h_coop)
            idx = [i for i in range(len(S)) if S[i][0] == kind]
            groups += [idx[i:i + 8] for i in range(0, len(idx), 8)]
        res = list(pool.map(_solve, [([plist[i] for i in g], CFG) for g in groups]))
        R = {k: np.empty(len(S), float) for k in KEEP}
        R["act0"] = np.empty(len(S), "U1")
        for g, r in zip(groups, res):
            for k in R:
                R[k][g] = r[k]
        out[des] = R
        print(f"  worlds {des} done", flush=True)
    return S, out


def world_report(S, out):
    lines = ["# Breakout options: baseline-world sweeps (auto-generated by breakout_options.py --worlds)", ""]
    for des in DESIGNS:
        R = out[des]
        lines.append(f"## {'baseline design' if des == 'base' else 'best stack (D_mult 3, T_reloc 4 with seq b, d 0.99, q_red 2)'}\n")
        for kind in dict.fromkeys(s[0] for s in S):
            rows = []
            for i, s in enumerate(S):
                if s[0] != kind:
                    continue
                att, suc = R["att"][i], R["suc"][i]
                rows.append([s[1], s[2], R["act0"][i], f"{att:.3f}", f"{suc / att:.2f}" if att > 1e-6 else "-",
                             f"{R['t_mean'][i]:.1f}" if att > 1e-6 else "-", f"{R['fail'][i] - R['hfail'][i]:.3f}",
                             f"{R['hfail'][i]:.3f}", f"{R['att2'][i]:.3f}", f"{R['t2_mean'][i]:.1f}" if R["att2"][i] > 1e-6 else "-",
                             f"{R['exit'][i]:.2f}", f"{R['riv'][i]:.2f}", f"{R['WH'][i]:.3f}",
                             f"{R['expo'][i]:.2f}/{R['amn'][i]:.2f}/{R['crk'][i]:.2f}"])
            lines.append(f"### {kind}\n")
            lines.append(rd.md_table(rows, ["world", "option", "act0", "P(strike)", "P(succ | strike)", "mean strike yr",
                                            "visible warning shot", "hidden failure", "P(2nd strike)", "mean 2nd yr",
                                            "P(exit)", "P(rival)", "WH", "exposed/amnesty/crackdown"]))
            lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ensembles
# ---------------------------------------------------------------------------
def ensembles(pool, only=None):
    bx = boxes()
    for name, (op, _) in CONFIGS.items():
        if only and name not in only:
            continue
        for box, th in bx.items():
            if box == "full" and name in FULL_SKIP:
                continue
            for des, dv in DESIGNS.items():
                run_ens(box, th, dv, op, pool, f"{des}__{name}")


def summarise(r):
    n = len(r["att"])
    st = r["att"] > 1e-6
    w = r["att"]
    return dict(
        n=n, holds=int(holds(r).sum()), holds_rival=int(holds_rival(r).sum()), strike_now=int(np.sum(r["act0"] == "S")),
        dis_now=int(np.sum(r["act0"] == "D")), exit_now=int(np.sum(r["act0"] == "X")),
        p_strike=float(r["att"].mean()), p_succ=float(r["suc"].mean()),
        succ_given_strike=float(r["suc"].sum() / max(r["att"].sum(), 1e-12)),
        warn_vis=float((r["fail"] - r["hfail"]).mean()), hfail=float(r["hfail"].mean()),
        p_second=float(r["att2"].mean()),
        t_strike=float(np.sum(np.where(st, r["t_mean"], 0) * w) / max(w[st].sum(), 1e-12)) if st.any() else np.nan,
        t_succ_w=float(np.sum(np.where(st, r["t_mean"], 0) * r["suc"]) / max(r["suc"][st].sum(), 1e-12)) if st.any() else np.nan,
        p_pre=float(r["pre"].mean()), riv=float(r["riv"].mean()), WH=float(r["WH"].mean()),
        expo=float(r["expo"].mean()), amn=float(r["amn"].mean()), crk=float(r["crk"].mean()))


def report():
    tabs, summ = ["# Breakout options: ensemble tables (auto-generated by breakout_options.py --report)", "",
                  "holds = AI cooperates at t = 0 and P(any strike within 300 years) < 1%. 'and rival < 0.5' also needs "
                  "P(rival AI within 300 years) < 0.5. Probabilities are means over draws. P(succ | strike) = sum of P(success) "
                  "over sum of P(strike). Mean strike year is weighted by P(strike); 'success-weighted' by P(success). "
                  "Visible warning shot = the first strike fails and humans see the motive; hidden = it fails and they do not.", ""], {}
    for box in ("r0.1", "full"):
        rows = []
        for name, (op, desc) in CONFIGS.items():
            for des in DESIGNS:
                p = os.path.join(RUNS, f"{box}__{des}__{name}.npz")
                if not os.path.exists(p):
                    continue
                r = dict(np.load(p))
                s = summarise(r)
                summ[f"{box}/{des}/{name}"] = s
                rows.append([name, des, f"{s['holds']}/{s['n']}", s["holds_rival"], s["strike_now"] + s["dis_now"],
                             s["dis_now"], s["exit_now"], f"{s['p_strike']:.3f}", f"{s['succ_given_strike']:.2f}",
                             f"{s['p_succ']:.3f}", f"{s['warn_vis']:.3f}", f"{s['hfail']:.3f}", f"{s['p_second']:.3f}",
                             f"{s['t_strike']:.1f}", f"{s['t_succ_w']:.1f}", f"{s['riv']:.2f}", f"{s['WH']:.3f}"])
        tabs.append(f"## {box} box\n")
        tabs.append(rd.md_table(rows, ["config", "design", "holds", "holds & rival<.5", "strike now (S or D)", "of which disguised",
                                       "exit now", "P(strike)", "P(succ | strike)", "P(success)", "visible warning shot",
                                       "hidden failure", "P(2nd strike)", "mean strike yr", "success-weighted yr",
                                       "P(rival)", "WH"]))
        tabs.append("")
        # paired changes against 'off'
        rows = []
        for des in DESIGNS:
            p0 = os.path.join(RUNS, f"{box}__{des}__off.npz")
            if not os.path.exists(p0):
                continue
            r0 = dict(np.load(p0))
            for name in CONFIGS:
                p = os.path.join(RUNS, f"{box}__{des}__{name}.npz")
                if name == "off" or not os.path.exists(p):
                    continue
                r = dict(np.load(p))
                rows.append([name, des, int(np.sum(holds(r) & ~holds(r0))), int(np.sum(holds(r0) & ~holds(r))),
                             int(np.sum(holds_rival(r) & ~holds_rival(r0))), int(np.sum(holds_rival(r0) & ~holds_rival(r))),
                             f"{np.mean(r['suc'] - r0['suc']):+.3f}", f"{np.mean(r['WH'] - r0['WH']):+.3f}"])
        tabs.append(f"### {box}: paired changes against 'off'\n")
        tabs.append(rd.md_table(rows, ["config", "design", "holds gained", "holds lost", "rival-aware gained", "rival-aware lost",
                                       "mean change in P(success)", "mean change in WH"]))
        tabs.append("")
    open(os.path.join(RES, "breakout_tables.md"), "w").write("\n".join(tabs) + "\n")
    json.dump(dict(summary=summ, configs={k: dict(opts=v[0], desc=v[1]) for k, v in CONFIGS.items()}),
              open(os.path.join(RES, "breakout_summary.json"), "w"), indent=1, default=float)
    print("\n".join(tabs))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--worlds", action="store_true")
    ap.add_argument("--ens", action="store_true")
    ap.add_argument("--only", default=None, help="comma-separated configuration names for --ens")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    with ProcessPoolExecutor(WORKERS) as pool:
        if a.check:
            txt, data = checks(pool)
            open(os.path.join(RES, "breakout_checks.md"), "w").write(
                "# Breakout-option checks (auto-generated by breakout_options.py --check)\n\n" + txt + "\n")
            json.dump(data, open(os.path.join(RES, "breakout_checks.json"), "w"), indent=1, default=str)
            print(txt, flush=True)
        if a.worlds:
            S, out = worlds(pool)
            open(os.path.join(RES, "breakout_worlds.md"), "w").write(world_report(S, out) + "\n")
            json.dump({d: {k: v.tolist() for k, v in R.items()} for d, R in out.items()} | {"sets": [s[:3] for s in S]},
                      open(os.path.join(RES, "breakout_worlds.json"), "w"), indent=0)
            print(world_report(S, out), flush=True)
        if a.ens:
            ensembles(pool, only=a.only.split(",") if a.only else None)
    if a.report:
        report()


if __name__ == "__main__":
    main()
