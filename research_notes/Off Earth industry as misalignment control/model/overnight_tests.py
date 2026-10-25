"""
Overnight model tests of 2026-10-21 (tests 2-5 of the brief in HANDOFF.md section 7c).

    python3 overnight_tests.py test2 [--quick]   # closing window: q rises (q_up) and/or hiding time shrinks (L_dn)
    python3 overnight_tests.py test4 [--quick]   # misjudged strike odds (pf_bel), two-pass solve
    python3 overnight_tests.py test3 [--quick]   # ratchet after a failed strike (k_rat), with L_f / kill_pre controls
    python3 overnight_tests.py test5             # correlated denial reserves on the best stack: q_red = 2 - rho

Each test writes results/overnight_<test>.json and results/overnight_<test>_tables.md. Ensemble runs go
through robust_design.run_design, so they are cached in results/robust_runs/ like every other design.
--quick writes *_quick files only (smoke test). Status: implemented. Checks are listed in each table file.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np

import equilibrium_model as em
import robust_design as rd

BEST = {"d": 0.99, "q_red": 2.0, "D_mult": 3.0, "seq": 1, "T_reloc": 4.0}
DESIGNS = {"baseline design": {}, "best stack": BEST}
WORLDS = {
    "baseline world": {},
    "lasting rival (ell_inf 0.01)": dict(ell_inf=0.01),
    "weak reserve (q 0.35)": dict(q=0.35),
    "early failure survivable (kill_pre 0.3)": dict(kill_pre=0.3),
}
# test 2 also needs worlds where the AI strikes LATER than year 0, otherwise a timing shift cannot show
WORLDS_LATE = {
    "eroding keys (q_er 0.005)": dict(q_er=0.005),
    "harvest motive (f_E 1e-6)": dict(f_E=1e-6),
    "weak reserve, no state temptation (q 0.35, B_R 0)": dict(q=0.35, B_R=0.0),
}
SEIZE = {"seizure lethal (w_seized 0)": dict(w_seized=0.0), "seizure survivable (w_seized 0.9)": dict(w_seized=0.9)}
STAT = ["act0", "att", "suc", "fail", "t_mean", "WH", "riv"]


def sweep(pool, plist):
    """Solve a list of full parameter dicts in batches of rd.BATCH (deterministic worlds share Kmax)."""
    jobs = [(plist[i:i + rd.BATCH], rd.CFG) for i in range(0, len(plist), rd.BATCH)]
    res = list(pool.map(rd._solve_batch, jobs))
    return {k: np.concatenate([r[k] for r in res]) for k in res[0]}


def world_params(design, world, seize, extra):
    th = dict(em.baseline(), **rd.FIXED)
    p = rd.apply_design(th, design)
    p.update(world)
    if "q" in world:                       # a world's q is the single-reserve value; the design's redundancy applies on top
        p["q"] = 1 - (1 - world["q"]) ** dict(rd.LEVER_BASE, **design)["q_red"]
    p.update(seize)
    p.update(extra)
    return p


def row_stats(r, i):
    att, suc = float(r["att"][i]), float(r["suc"][i])
    return dict(act0=str(r["act0"][i]), att=att, suc=suc, fail=float(r["fail"][i]),
                t_mean=float(r["t_mean"][i]) if att > 1e-9 else None, WH=float(r["WH"][i]), riv=float(r["riv"][i]),
                p_suc_given_strike=(suc / att) if att > 1e-6 else None)


def fmt_cell(s):
    if s["att"] < 0.01:
        return f"holds (WH {s['WH']:.3f})"
    t = "now" if s["act0"] == "S" else f"yr {s['t_mean']:.0f}"
    return (f"att {s['att']:.2f}, suc {s['suc']:.2f}, {t}, P(suc|strike) {s['p_suc_given_strike']:.2f}, "
            f"WH {s['WH']:.3f}")


def ens_summary(r, base=None):
    """Hold share and strike statistics over an ensemble; paired timing changes against base."""
    h = r["holds"] > 0.5
    att, suc = r["att"], r["suc"]
    st = att > 0.01
    out = dict(holds=int(h.sum()), n=int(len(h)), mean_att=float(att.mean()), mean_suc=float(suc.mean()),
               p_suc_given_strike=float(suc.sum() / max(att.sum(), 1e-12)), mean_WH=float(r["WH"].mean()),
               mean_t_strikers=float(np.nanmean(np.where(st, r["t_mean"], np.nan))) if st.any() else None,
               n_strike_now=int((r["act0"] == "S").sum()))
    if "fail" in r:
        out["mean_fail"] = float(r["fail"].mean())
    if base is not None:
        sb = base["att"] > 0.01
        both = st & sb
        dt = r["t_mean"][both] - base["t_mean"][both]
        out.update(paired_both=int(both.sum()), earlier=int((dt < -0.5).sum()), later=int((dt > 0.5).sum()),
                   mean_dt_both=float(dt.mean()) if both.any() else None,
                   new_strikers=int((st & ~sb).sum()), stopped=int((sb & ~st).sum()),
                   gained=int((h & ~(base["holds"] > 0.5)).sum()), lost=int(((base["holds"] > 0.5) & ~h).sum()),
                   dWH=float((r["WH"] - base["WH"]).mean()),
                   dsuc=float((r["suc"] - base["suc"]).mean()), datt=float((r["att"] - base["att"]).mean()))
        if "fail" in r and "fail" in base:
            out["dfail"] = float((r["fail"] - base["fail"]).mean())
    return out


def ens_table(rows):
    hdr = ["design", "variant", "holds", "mean att", "mean suc", "P(suc|strike)", "mean strike yr (strikers)",
           "mean WH", "vs off: gained/lost", "earlier/later (both strike)", "new/stopped strikers", "mean dWH"]
    body = []
    for lab, var, s in rows:
        body.append([lab, var, f"{s['holds']}/{s['n']}", s["mean_att"], s["mean_suc"], s["p_suc_given_strike"],
                     "-" if s["mean_t_strikers"] is None else f"{s['mean_t_strikers']:.1f}", s["mean_WH"],
                     f"+{s.get('gained', 0)} / -{s.get('lost', 0)}" if "gained" in s else "-",
                     f"{s['earlier']} / {s['later']} of {s['paired_both']}" if "earlier" in s else "-",
                     f"{s['new_strikers']} / {s['stopped']}" if "new_strikers" in s else "-",
                     s.get("dWH", float("nan"))])
    return rd.md_table(body, hdr)


def r01():
    return rd.ensemble("r0.1", rd.N_RAD, seed=105)[1]


def write(name, quick, tables, data):
    suf = "_quick" if quick else ""
    with open(os.path.join(rd.RES, f"overnight_{name}{suf}_tables.md"), "w") as f:
        f.write(f"# Overnight {name} (auto-generated by overnight_tests.py; [[ai gen]])\n\n" + "\n\n".join(tables) + "\n")
    json.dump(data, open(os.path.join(rd.RES, f"overnight_{name}{suf}.json"), "w"), indent=1, default=str)
    print("\n\n".join(tables), flush=True)


# ---------------------------------------------------------------------------
# test 2: closing window
# ---------------------------------------------------------------------------
def test2(pool, quick=False):
    variants = [("off", {}), ("q_up 0.005", dict(q_up=0.005)), ("q_up 0.01", dict(q_up=0.01)), ("q_up 0.02", dict(q_up=0.02)),
                ("q_up 0.05", dict(q_up=0.05)), ("q_up 0.1", dict(q_up=0.1)), ("L_dn 0.03", dict(L_dn=0.03)),
                ("L_dn 0.1", dict(L_dn=0.1)), ("q_up 0.02 + L_dn 0.03", dict(q_up=0.02, L_dn=0.03))]
    if quick:
        variants = variants[:3]
    plist, meta = [], []
    worlds = dict(WORLDS, **WORLDS_LATE)
    for dl, dv in DESIGNS.items():
        for wl, w in worlds.items():
            for sl, s in SEIZE.items():
                for vl, v in variants:
                    plist.append(world_params(dv, w, s, v))
                    meta.append((dl, wl, sl, vl))
    t0 = time.time()
    r = sweep(pool, plist)
    print(f"test2 deterministic: {len(plist)} sets in {time.time() - t0:.0f} s", flush=True)
    det = [dict(design=m[0], world=m[1], seizure=m[2], variant=m[3], **row_stats(r, i)) for i, m in enumerate(meta)]
    tables = []
    for dl in DESIGNS:
        body = []
        for wl in worlds:
            for sl in SEIZE:
                cells = [fmt_cell(d) for d in det if d["design"] == dl and d["world"] == wl and d["seizure"] == sl]
                body.append([wl, sl] + cells)
        tables.append(f"## T2-det ({dl}). Closing window at fixed worlds\n\nEach cell: att = P(strike within 300 y), "
                      "suc = P(a strike succeeds), strike timing (now = opening move; else mean strike year), "
                      "P(suc|strike) = suc/att, WH = human welfare (yearly equivalent).\n\n" +
                      rd.md_table(body, ["world", "seizure"] + [v[0] for v in variants]))
    # ensembles
    th = r01()
    ens_vars = [("q_up 0.01", dict(q_up=0.01)), ("q_up 0.03", dict(q_up=0.03)), ("q_up 0.1", dict(q_up=0.1)),
                ("L_dn 0.03", dict(L_dn=0.03)), ("L_dn 0.1", dict(L_dn=0.1)), ("q_up 0.03 + L_dn 0.03", dict(q_up=0.03, L_dn=0.03))]
    if quick:
        ens_vars = ens_vars[:1]
    rows, ens = [], {}
    for dl, dv in DESIGNS.items():
        base = rd.run_design("r0.1", th, dv, pool)
        rows.append((dl, "off", ens_summary(base)))
        for vl, v in ens_vars:
            z = rd.run_design("r0.1", th, dict(dv, **v), pool)
            s = ens_summary(z, base)
            rows.append((dl, vl, s))
            ens[f"{dl}|{vl}"] = s
    tables.append("## T2-ens. Closing window over the radius-0.1 box (64 draws, paired against the same design with the window off)\n\n"
                  "Note: cached runs made before 2026-10-21 lack the `fail` indicator, so the 'off' rows show no warning-shot rate.\n\n"
                  + ens_table(rows))
    write("test2", quick, tables, dict(det=det, ens=ens))


# ---------------------------------------------------------------------------
# test 4: misjudged odds
# ---------------------------------------------------------------------------
def test4(pool, quick=False):
    bels = [0.25, 0.5, 0.8, 1.0, 1.25, 2.0, 4.0] if not quick else [0.5, 1.0, 2.0]
    worlds = dict(WORLDS, **{"early failure harmless (kill_pre 0)": dict(kill_pre=0.0)})
    plist, meta = [], []
    for dl, dv in DESIGNS.items():
        for wl, w in worlds.items():
            for sl, s in SEIZE.items():
                for b in bels:
                    plist.append(world_params(dv, w, s, dict(pf_bel=b)))
                    meta.append((dl, wl, sl, b))
    t0 = time.time()
    # pf_bel = 1 rows run through the one-pass solver; the identity check below compares them with forced two-pass
    r = sweep(pool, plist)
    print(f"test4 deterministic: {len(plist)} sets in {time.time() - t0:.0f} s", flush=True)
    det = [dict(design=m[0], world=m[1], seizure=m[2], pf_bel=m[3], **row_stats(r, i)) for i, m in enumerate(meta)]
    # identity: forced two-pass at pf_bel = 1 equals the one-pass solve
    ident = [world_params(dv, w, s, {}) for dv in DESIGNS.values() for w in worlds.values() for s in SEIZE.values()]
    a = em.solve(em.batch([em.baseline(**p) for p in ident]), N=rd.CFG["N"], T_H=rd.CFG["T_H"], nA=rd.CFG["nA"])
    b = em.solve(em.batch([em.baseline(**p) for p in ident]), N=rd.CFG["N"], T_H=rd.CFG["T_H"], nA=rd.CFG["nA"], two_pass=True)
    idd = max(float(np.nanmax(np.abs(np.asarray(a[k], float) - np.asarray(b[k], float)))) for k in ("VA", "WH", "att", "suc", "fail", "riv"))
    same = bool(np.all(a["act0"] == b["act0"]))
    tables = [f"Identity check: forced two-pass solve with belief = truth against the one-pass solve, {len(ident)} worlds: "
              f"largest absolute difference {idd:.3g}; opening moves identical: {same}."]
    for dl in DESIGNS:
        body = []
        for wl in worlds:
            for sl in SEIZE:
                ds = [d for d in det if d["design"] == dl and d["world"] == wl and d["seizure"] == sl]
                truth = [d for d in ds if d["pf_bel"] == 1.0][0]
                cells = []
                for d in ds:
                    if d["att"] < 0.01:
                        cells.append(f"holds (WH {d['WH']:.3f})")
                    else:
                        t = "now" if d["act0"] == "S" else f"yr {d['t_mean']:.0f}"
                        cells.append(f"warn {d['fail']:.2f}, suc {d['suc']:.2f}, {t}, WH {d['WH']:.3f} (d {d['WH'] - truth['WH']:+.3f})")
                body.append([wl, sl] + cells)
        tables.append(f"## T4-det ({dl}). Misjudged strike odds at fixed worlds\n\nColumns: the AI believes a strike fails with "
                      "probability pf_bel x the true one (below 1 = overconfident). warn = P(a chosen strike fails) (warning shot), "
                      "suc = P(a strike succeeds), timing, WH = human welfare and (d) its change against belief = truth.\n\n" +
                      rd.md_table(body, ["world", "seizure"] + [f"pf_bel {b:g}" for b in bels]))
    th = r01()
    ens_b = [0.25, 0.5, 2.0, 4.0] if not quick else [0.5]
    rows, ens = [], {}
    for dl, dv in DESIGNS.items():
        base = rd.run_design("r0.1", th, dv, pool)
        rows.append((dl, "truth", ens_summary(base)))
        for bv in ens_b:
            z = rd.run_design("r0.1", th, dict(dv, pf_bel=bv), pool)
            s = ens_summary(z, base)
            rows.append((dl, f"pf_bel {bv:g}", s))
            ens[f"{dl}|{bv}"] = s
    tables.append("## T4-ens. Misjudged odds over the radius-0.1 box (64 draws, paired against belief = truth)\n\n"
                  + ens_table(rows) + "\n\nWarning-shot rate (mean P a chosen strike fails): " +
                  "; ".join(f"{k}: {v.get('mean_fail', float('nan')):.3f}" for k, v in ens.items()))
    write("test4", quick, tables, dict(det=det, ens=ens, identity=dict(maxdiff=idd, act0_same=same)))


# ---------------------------------------------------------------------------
# test 3: ratchet
# ---------------------------------------------------------------------------
def test3(pool, quick=False):
    LF = [0.999, 0.99, 0.9, 0.7, 0.5, 0.3, 0.1] if not quick else [0.999, 0.5]
    KP = [1.0, 0.3, 0.0] if not quick else [1.0, 0.0]
    KR = [0.0, 0.5, 0.9] if not quick else [0.0, 0.9]
    worlds = {k: v for k, v in WORLDS.items() if "kill_pre" not in k}
    plist, meta = [], []
    for dl, dv in DESIGNS.items():
        for wl, w in worlds.items():
            for sl, s in SEIZE.items():
                for kp in KP:
                    for lf in LF:
                        for kr in KR:
                            plist.append(world_params(dv, w, s, dict(L_f=lf, kill_pre=kp, k_rat=kr)))
                            meta.append((dl, wl, sl, kp, lf, kr))
    t0 = time.time()
    r = sweep(pool, plist)
    print(f"test3 deterministic: {len(plist)} sets in {time.time() - t0:.0f} s", flush=True)
    det = [dict(design=m[0], world=m[1], seizure=m[2], kill_pre=m[3], L_f=m[4], k_rat=m[5], **row_stats(r, i))
           for i, m in enumerate(meta)]
    tables = []
    for dl in DESIGNS:
        body = []
        for wl in worlds:
            for sl in SEIZE:
                for kp in KP:
                    for kr in KR[1:]:
                        cells = []
                        for lf in LF:
                            on = [d for d in det if (d["design"], d["world"], d["seizure"], d["kill_pre"], d["L_f"], d["k_rat"]) == (dl, wl, sl, kp, lf, kr)][0]
                            off = [d for d in det if (d["design"], d["world"], d["seizure"], d["kill_pre"], d["L_f"], d["k_rat"]) == (dl, wl, sl, kp, lf, 0.0)][0]
                            def sh(d):
                                if d["att"] < 0.01:
                                    return "holds"
                                return ("now" if d["act0"] == "S" else f"yr {d['t_mean']:.0f}") + f" att {d['att']:.2f}"
                            cells.append(f"off: {sh(off)}; on: {sh(on)}; dWH {on['WH'] - off['WH']:+.4f}, datt {on['att'] - off['att']:+.3f}")
                        body.append([wl, sl, f"{kp:g}", f"{kr:g}"] + cells)
        tables.append(f"## T3-det ({dl}). Ratchet on against off, sweeping the failure loss L_f\n\nEach cell: strike behaviour with the "
                      "ratchet off and on (same world), and the on-minus-off change in human welfare and P(strike). Only the "
                      "on-minus-off difference is the ratchet's effect; changes along a row with the ratchet off come from "
                      "softening the failure penalty itself.\n\n" +
                      rd.md_table(body, ["world", "seizure", "kill_pre", "k_rat"] + [f"L_f {lf:g}" for lf in LF]))
    # continuity: L_f 0.999 must reproduce L_f 0.999 with ratchet off (failure near total)
    cont = []
    for d in det:
        if d["L_f"] == 0.999 and d["k_rat"] > 0 and d["kill_pre"] == 1.0:
            off = [e for e in det if (e["design"], e["world"], e["seizure"], e["kill_pre"], e["L_f"], e["k_rat"]) ==
                   (d["design"], d["world"], d["seizure"], 1.0, 0.999, 0.0)][0]
            cont.append(max(abs(d[k] - off[k]) for k in ("att", "suc", "WH", "fail")))
    tables.insert(0, f"Continuity check (kill_pre 1, L_f 0.999, ratchet on vs off, {len(cont)} cases): largest absolute "
                     f"difference in att, suc, fail, WH = {max(cont) if cont else float('nan'):.3g}.")
    th = r01()
    rows, ens = [], {}
    evs = [("k_rat 0.5", dict(k_rat=0.5)), ("k_rat 0.9", dict(k_rat=0.9))] if not quick else [("k_rat 0.9", dict(k_rat=0.9))]
    for dl, dv in DESIGNS.items():
        for kpl, kpd in (("sampled kill_pre", {}), ("kill_pre 0", dict(kill_pre=0.0))):
            base = rd.run_design("r0.1", th, dict(dv, **kpd), pool)
            rows.append((dl, f"{kpl}, off", ens_summary(base)))
            for vl, v in evs:
                z = rd.run_design("r0.1", th, dict(dv, **kpd, **v), pool)
                s = ens_summary(z, base)
                rows.append((dl, f"{kpl}, {vl}", s))
                ens[f"{dl}|{kpl}|{vl}"] = s
    tables.append("## T3-ens. Ratchet over the radius-0.1 box (64 draws, paired against the ratchet off with the same kill_pre)\n\n"
                  + ens_table(rows))
    write("test3", quick, tables, dict(det=det, ens=ens, continuity=cont))


# ---------------------------------------------------------------------------
# test 5: correlated reserves on the best stack
# ---------------------------------------------------------------------------
def test5(pool, quick=False):
    rows, out = [], {}
    for box, th in (("r0.1", r01()), ("full", rd.ensemble("full", rd.N_FULL)[1])):
        no_red = rd.run_design(box, th, dict(BEST, q_red=1.0), pool)
        best = rd.run_design(box, th, BEST, pool)
        for rho in (0.0, 0.25, 0.5, 0.75, 1.0):
            d = dict(BEST, q_red=2.0 - rho)
            z = rd.run_design(box, th, d, pool)
            s = ens_summary(z, best)
            s["vs_no_redundancy"] = f"+{int(((z['holds'] > 0.5) & (no_red['holds'] < 0.5)).sum())} / -{int(((z['holds'] < 0.5) & (no_red['holds'] > 0.5)).sum())}"
            rows.append((box, f"rho {rho:g} (q_red {2 - rho:g})", s))
            out[f"{box}|{rho}"] = s
    body = [[b, v, f"{s['holds']}/{s['n']}", s["vs_no_redundancy"], f"+{s['gained']} / -{s['lost']}", s["mean_WH"], s["mean_att"]]
            for b, v, s in rows]
    tables = ["## T5. Correlated denial reserves on the best stack: q -> 1 - (1 - q)^(2 - rho)\n\n"
              "rho 0 = independent (the best stack as run before), rho 1 = fully correlated (same as one reserve). "
              "Paired draw counts against one reserve (q_red 1) and against independent reserves (q_red 2).\n\n" +
              rd.md_table(body, ["box", "correlation", "holds", "vs one reserve", "vs independent", "mean WH", "mean att"])]
    write("test5", quick, tables, out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("test", choices=["test2", "test3", "test4", "test5"])
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    with ProcessPoolExecutor(rd.WORKERS) as pool:
        globals()[a.test](pool, quick=a.quick)
    print(f"{a.test} done in {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
