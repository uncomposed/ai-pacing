"""
Tables, regret, scenario discovery and figures for the robust-design run. Reads only the cache in
results/robust_runs/ (written by robust_design.py); never solves. Writes
results/robust_design_tables.md, results/robust_design_summary.json and figures/rd_*.png.
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import robust_design as rd

BLUE, ORANGE, SKY, BLACK, GREY = rd.BLUE, rd.ORANGE, rd.SKY, rd.BLACK, rd.GREY
plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 150, "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "hatch.linewidth": 0.6})
TABLES: list[str] = []
OUT: dict = {}


def section(title, body):
    TABLES.append(f"## {title}\n\n{body}\n")


def load(ens, key):
    p = os.path.join(rd.RUNS, f"{ens}__{key}.npz")
    if not os.path.exists(p):
        return None
    z = np.load(p)
    return {k: z[k] for k in z.files}


def savefig(fig, name):
    fig.savefig(os.path.join(rd.FIG, name), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def label(design):
    if not design:
        return "baseline design (a, denial, d 0.9)"
    names = {"seq": {1: "seq b (fabs to orbit)", 2: "seq c (dismantle early)", 3: "seq n (never dismantle)"},
             "den": {0: "no denial reserve"}}
    parts = []
    for k, v in design.items():
        if k in names and v in names[k]:
            parts.append(names[k][v])
        elif k == "seq" and v == 0:
            parts.append("seq a")
        else:
            parts.append(f"{k} {v:g}")
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# PRIM (patient rule induction), on the unit-cube sample
# ---------------------------------------------------------------------------
def prim(U, y, alpha=0.05, min_support=0.05, dims=None):
    """Peel a box in u-space that concentrates y = 1. Returns the peeling trajectory:
    list of (box lo, box hi, coverage, density, support)."""
    n, d = U.shape
    dims = range(d) if dims is None else dims
    lo, hi = np.zeros(d), np.ones(d)
    inside = np.ones(n, bool)
    tot = y.sum()
    traj = [(lo.copy(), hi.copy(), 1.0, y.mean(), 1.0)]
    while inside.mean() > min_support:
        best = None
        for j in dims:
            x = U[inside, j]
            for side in (0, 1):
                cut = np.quantile(x, alpha if side == 0 else 1 - alpha)
                keep = inside & ((U[:, j] >= cut) if side == 0 else (U[:, j] <= cut))
                if keep.sum() in (0, inside.sum()):
                    continue
                dens = y[keep].mean()
                if best is None or dens > best[0]:
                    best = (dens, j, side, cut, keep)
        if best is None:
            break
        dens, j, side, cut, keep = best
        if dens <= y[inside].mean():
            break
        inside = keep
        if side == 0:
            lo[j] = cut
        else:
            hi[j] = cut
        traj.append((lo.copy(), hi.copy(), y[inside].sum() / max(tot, 1), dens, inside.mean()))
    return traj


def box_text(lo, hi, ens="full"):
    """Restricted dimensions of a u-space box, in parameter units."""
    out = []
    for j, (nm, a, b, sc, p0) in enumerate(rd.UNCERTAIN):
        if lo[j] <= 1e-12 and hi[j] >= 1 - 1e-12:
            continue

        def val(u):
            if ens != "full":
                return rd.u_to_params(np.full((1, len(rd.UNAMES)), u), ens)[0][nm]
            if sc == "bin":
                return float(u >= 0.5)
            if p0 > 0 and u < p0:
                return 0.0
            x = (u - p0) / (1 - p0) if p0 > 0 else u
            return float(rd._scale_map(x, a, b, sc))
        s = []
        if lo[j] > 1e-12:
            s.append(f">= {rd.fmt(val(lo[j]))}")
        if hi[j] < 1 - 1e-12:
            s.append(f"<= {rd.fmt(val(hi[j]))}")
        out.append(f"{nm} " + " and ".join(s))
    return "; ".join(out)


def ndims(t):
    return int(((t[0] > 1e-12) | (t[1] < 1 - 1e-12)).sum())


def pick_box(traj, min_cov=0.5, max_dims=3):
    """Densest box on the trajectory that still covers at least min_cov of the target cases and restricts
    at most max_dims uncertainties (small samples: more dimensions would mostly fit noise)."""
    ok = [t for t in traj if t[2] >= min_cov and ndims(t) <= max_dims]
    return max(ok, key=lambda t: (t[3], t[2]))


# ---------------------------------------------------------------------------
def report():
    bp = os.path.join(rd.RES, "robust_best.json")
    if os.path.exists(bp):
        OUT["best_lv"] = json.load(open(bp))
    U_f, th_f = rd.ensemble("full", rd.N_FULL)
    U_n, th_n = rd.ensemble("near", rd.N_NEAR, seed=20261017)
    nf, nn = rd.N_FULL, rd.N_NEAR
    # ---- one lever at a time -------------------------------------------------------------
    oat = rd.oat_designs()
    base_f, base_n = load("full", "base"), load("near", "base")
    rows, oat_out = [], []
    for d in oat:
        k = rd.design_key(d)
        rf, rn = load("full", k), load("near", k)
        if rf is None or rn is None:
            continue
        hf, hn = rf["holds"].mean(), rn["holds"].mean()
        gain_f = int(((rf["holds"] == 1) & (base_f["holds"] == 0)).sum())
        lost_f = int(((rf["holds"] == 0) & (base_f["holds"] == 1)).sum())
        gain_n = int(((rn["holds"] == 1) & (base_n["holds"] == 0)).sum())
        lost_n = int(((rn["holds"] == 0) & (base_n["holds"] == 1)).sum())
        fkf = rd.fail_kind(rf)
        lo, hi = rd.ci(hf, nf)
        r1, b1 = load("r0.1", k), load("r0.1", "base")
        if r1 is not None and b1 is not None:
            h1 = r1["holds"].mean()
            g1, l1 = int(((r1["holds"] == 1) & (b1["holds"] == 0)).sum()), int(((r1["holds"] == 0) & (b1["holds"] == 1)).sum())
            t1 = f"{100 * h1:.0f}% (+{g1} / -{l1})"
        else:
            h1, t1 = np.nan, "-"
        rows.append([label(d), t1, f"{100 * hf:.1f}% ({100 * lo:.0f}-{100 * hi:.0f})", f"+{gain_f} / -{lost_f}",
                     f"{100 * hn:.1f}%", f"+{gain_n} / -{lost_n}", f"{100 * (fkf == 1).mean():.0f}%",
                     f"{100 * (fkf == 2).mean():.0f}%", f"{100 * rf['riv'].mean():.0f}%", rf["WH"].mean(), rn["WH"].mean()])
        oat_out.append(dict(design=d, key=k, label=label(d), hold_full=hf, hold_near=hn, gain_full=gain_f,
                            lost_full=lost_f, gain_near=gain_n, lost_near=lost_n, hold_r01=float(h1), WH_full=float(rf["WH"].mean()),
                            WH_near=float(rn["WH"].mean())))
    section(f"A. One lever at a time ({nf} full-box draws, {nn} near-box draws; common random numbers)",
            "Pact holds = AI cooperates at t = 0 and P(strike or harvest within 300 years) < 1%. "
            "'+g / -l' = draws gained / lost against the baseline design on the same draws. "
            "Brackets: Wilson 90% interval.\n\n" +
            md_table(rows, ["design", "holds, r0.1 box (vs baseline)", "holds, full box", "vs baseline (full)", "holds, near box", "vs baseline (near)",
                            "strike now (full)", "later strike/harvest (full)", "mean P(rival) (full)",
                            "mean human welfare (full)", "mean human welfare (near)"]))
    OUT["oat"] = oat_out
    if oat_out:
        fig_oat(oat_out)
    # ---- all designs on the full box: regret --------------------------------------------
    keys = sorted({os.path.basename(p)[len("full__"):-4] for p in glob.glob(os.path.join(rd.RUNS, "full__*.npz"))
                   if "__nA" not in p and "__T_H" not in p})
    R = {k: load("full", k) for k in keys}
    R = {k: v for k, v in R.items() if v is not None and len(v["holds"]) == nf}
    test_tables(R, "full")
    R = {k: v for k, v in R.items() if not is_test(k)}
    if R:
        regret_tables(R, "full")
    Rn = {k: load("near", k) for k in keys}
    Rn = {k: v for k, v in Rn.items() if v is not None and len(v["holds"]) == nn and not is_test(k)}
    if Rn:
        regret_tables(Rn, "near")
    radius_table()
    R1 = {k: load("r0.1", k) for k in {os.path.basename(p)[len("r0.1__"):-4] for p in glob.glob(os.path.join(rd.RUNS, "r0.1__*.npz"))}}
    R1 = {k: v for k, v in R1.items() if v is not None and len(v["holds"]) == rd.N_RAD}
    test_tables(R1, "r0.1")
    R1 = {k: v for k, v in R1.items() if not is_test(k)}
    if len(R1) > 1:
        regret_tables(R1, "r0.1")
    # ---- scenario discovery -----------------------------------------------------------------
    best = OUT["best_full"] = max(R, key=lambda k: (R[k]["holds"].mean(), R[k]["WH"].mean())) if R else "base"
    R1d = {k: v for k, v in R1.items() if "q_er" not in k and "q_ea" not in k}   # erosion runs are scenarios, not designs
    best1 = OUT["best_r0.1"] = max(R1d, key=lambda k: (R1d[k]["holds"].mean(), R1d[k]["WH"].mean())) if len(R1d) > 1 else "base"
    for ens, n, seed in (("r0.1", rd.N_RAD, 105), ("r0.25", rd.N_RAD, 255)):
        U, th = rd.ensemble(ens, n, seed=seed)
        for k in dict.fromkeys(["base", best1, best]):
            z = load(ens, k)
            if z is not None:
                discovery(U, z, k, ens, th, "fails")
    for k in dict.fromkeys(["base", best]):
        if load("full", k) is not None:
            discovery(U_f, load("full", k), k, "full", th_f, "holds")
        if load("near", k) is not None:
            discovery(U_n, load("near", k), k, "near", th_n, "holds")
    # ---- erosion ------------------------------------------------------------------------
    erosion_report(OUT.get("best_lv"))
    with open(os.path.join(rd.RES, "robust_design_tables.md"), "w") as f:
        f.write("# Robust-design tables (auto-generated by robust_report.py from results/robust_runs/)\n\n"
                + "\n".join(TABLES))
    json.dump(OUT, open(os.path.join(rd.RES, "robust_design_summary.json"), "w"), indent=1, default=float)
    print("\n".join(TABLES))


md_table = rd.md_table

# Overnight tests of 2026-10-21 solve extra "designs" that are really model variants (state temptation BR_mult,
# closing window q_up / L_dn, ratchet k_rat, misjudged odds pf_bel, and the failure-penalty controls L_f / kill_pre).
# They stay out of the lever regret pool and the best-design pick, so the earlier tables do not move, and get their
# own table T: hold share and paired draws gained / lost against the baseline design and the best lever stack.
TEST_PARAMS = ("BR_mult", "q_up", "L_dn", "k_rat", "pf_bel", "L_f", "kill_pre", "w_seized")
BEST_STACK = "D_mult=3_T_reloc=4_d=0.99_q_red=2_seq=1"


def is_test(key):
    # fractional q_red (correlated reserves, test 5) is a model variant too
    if any(f"q_red={v}" in key for v in ("1.25", "1.5", "1.75")):
        return True
    return any(f"{t}=" in key for t in TEST_PARAMS)


def test_tables(R, ens):
    keys = sorted(k for k in R if is_test(k))
    if not keys:
        return
    rows = []
    for k in keys:
        r = R[k]
        h = r["holds"] > 0.5
        row = [k, f"{h.sum()}/{len(h)} ({100 * h.mean():.1f}%)"]
        for ref in ("base", BEST_STACK):
            if ref in R:
                hr = R[ref]["holds"] > 0.5
                row.append(f"+{int((h & ~hr).sum())} / -{int((hr & ~h).sum())}")
            else:
                row.append("-")
        row += [r["WH"].mean(), r["att"].mean(), r["suc"].mean()]
        rows.append(row)
    section(f"T ({ens} box). Model-variant tests (overnight 2026-10-21), kept out of the regret pool",
            "Paired against the baseline design and the best lever stack on the same draws: draws gained / lost. "
            "att = mean P(strike within 300 y); suc = mean P(a strike succeeds).\n\n" +
            md_table(rows, ["variant", "holds", "vs baseline design", "vs best stack", "mean human welfare", "mean att", "mean suc"]))
    OUT[f"tests_{ens}"] = [dict(zip(["key", "holds", "vs_base", "vs_best", "WH", "att", "suc"], [str(x) if i < 4 else float(x) for i, x in enumerate(r)])) for r in rows]


def regret_tables(R, ens):
    # erosion runs are scenarios, not designs; a tribute (psi_div) pays humans a share of an AI economy up to
    # Kmax = 1e13, so its welfare is on another scale and would swamp every regret number. Both are left out.
    keys = [k for k in R if not any(x in k for x in ("q_er", "q_ea", "psi_div"))]
    WH = np.array([R[k]["WH"] for k in keys])           # (designs, draws)
    H = np.array([R[k]["holds"] for k in keys])
    reg = WH.max(axis=0)[None, :] - WH
    order = np.argsort(reg.max(axis=1))
    rows = []
    for i in order:
        rows.append([keys[i], f"{100 * H[i].mean():.1f}%", WH[i].mean(), reg[i].mean(), np.quantile(reg[i], 0.9),
                     reg[i].max(), int((reg[i] < 1e-9).sum())])
    section(f"B ({ens} box). Every design solved on this box: hold share and regret in human welfare",
            "Regret on a draw = best welfare any listed design achieves on that draw minus this design's welfare "
            "(yearly equivalent, 1 = today). Sorted by maximum regret (minimax regret first). 'best on' = draws "
            "where this design is the best (ties count for each). Excluded: erosion scenarios, and the tribute design "
            "(its welfare scales with the AI's size; see table A).\n\n" +
            md_table(rows, ["design", "holds", "mean welfare", "mean regret", "90th pct regret", "max regret", "best on"]))
    OUT[f"regret_{ens}"] = [dict(key=keys[i], hold=float(H[i].mean()), WH=float(WH[i].mean()), reg_mean=float(reg[i].mean()),
                                  reg_p90=float(np.quantile(reg[i], 0.9)), reg_max=float(reg[i].max())) for i in order]


def discovery(U, r, key, ens, thetas, target="fails"):
    y = 1 - r["holds"] if target == "fails" else r["holds"].copy()
    tname = "the pact fails" if target == "fails" else "the pact holds"
    # single-uncertainty failure rates: the strongest one-dimensional splits
    one = []
    for j, nm in enumerate(rd.UNAMES):
        for cut in (0.25, 0.5, 0.75):
            lo = U[:, j] < cut
            if lo.sum() < 8 or (~lo).sum() < 8:
                continue
            one.append((abs(y[lo].mean() - y[~lo].mean()), nm, cut, y[lo].mean(), y[~lo].mean()))
    one.sort(reverse=True)
    seen, top = set(), []
    for s in one:
        if s[1] in seen:
            continue
        seen.add(s[1])
        top.append(s)
        if len(top) == 10:
            break

    traj = prim(U, y, alpha=0.1, min_support=0.1, dims=[rd.UNAMES.index(t[1]) for t in top[:6]])
    rows = []
    for t in [t for t in traj if ndims(t) <= 4]:
        rows.append([f"{100 * t[4]:.0f}%", f"{100 * t[2]:.0f}%", f"{100 * t[3]:.0f}%", box_text(t[0], t[1], ens) or "(whole box)"])
    b = pick_box(traj, 0.5)
    def uval(nm, u):
        j = rd.UNAMES.index(nm)
        _, a, bb, sc, p0 = rd.UNCERTAIN[j]
        if sc == "bin":
            return "0/1"
        if p0 > 0 and u <= p0:
            return "0"
        x = (u - p0) / (1 - p0) if p0 > 0 else u
        if ens != "full":
            th = rd.u_to_params(np.full((1, len(rd.UNAMES)), u), ens)[0]
            return rd.fmt(th[nm])
        return rd.fmt(float(rd._scale_map(x, a, bb, sc)))
    rows1 = [[nm, f"u < {cut:g} (value < {uval(nm, cut)})", f"{100 * fl:.0f}%", f"{100 * fh:.0f}%"] for _, nm, cut, fl, fh in top]
    tree_txt = ""
    try:
        from sklearn.tree import DecisionTreeClassifier, export_text
        X = np.array([[t[n] for n in rd.UNAMES] for t in thetas])
        X = np.where(np.array([sc == "log" for _, _, _, sc, _ in rd.UNCERTAIN])[None, :], np.log10(np.maximum(X, 1e-300)), X)
        clf = DecisionTreeClassifier(max_depth=3, min_samples_leaf=8, random_state=0).fit(X, y)
        tree_txt = ("\n\nDecision tree (depth 3, at least 8 draws per leaf; log-scale parameters are log10; "
                    f"class 1 = {tname}; training accuracy "
                    f"{100 * clf.score(X, y):.0f}%):\n\n```\n" + export_text(clf, feature_names=[
                        ("log10 " + n) if sc == "log" else n for n, _, _, sc, _ in rd.UNCERTAIN]) + "```")
    except Exception as e:     # noqa: BLE001
        tree_txt = f"\n\n(decision tree skipped: {e})"
    section(f"C ({ens} box, design {key}, target: {tname}). Scenario discovery",
            f"Target: draws where {tname} ({100 * y.mean():.0f}% of {len(y)}). PRIM peeling trajectory, restricted to the six "
            "uncertainties with the strongest single splits (below), to limit fitting noise "
            "(support = share of draws in the box; coverage = share of all target draws inside; density = target share inside):\n\n"
            + md_table(rows, ["support", "coverage", "density", "box"]) +
            f"\n\nChosen box (densest with coverage >= 50% and at most 3 restricted uncertainties): support {100 * b[4]:.0f}%, coverage {100 * b[2]:.0f}%, "
            f"density {100 * b[3]:.0f}%: {box_text(b[0], b[1], ens)}.\n\n"
            "Strongest single-uncertainty splits (target share below and above the cut, in sample quantiles):\n\n"
            + md_table(rows1, ["uncertainty", "split", "target below", "target above"]) + tree_txt)
    OUT[f"prim_{ens}_{key}_{target}"] = dict(box=box_text(b[0], b[1], ens), support=b[4], coverage=b[2], density=b[3],
                                    top_splits=[(nm, cut, fl, fh) for _, nm, cut, fl, fh in top])


def radius_table():
    keys = sorted({os.path.basename(p).split("__", 1)[1][:-4] for p in glob.glob(os.path.join(rd.RUNS, "r0.02__*.npz"))})
    rows, data = [], {}
    for k in keys:
        hs = []
        for rad in rd.RADII:
            z = load(f"r{rad:g}", k)
            hs.append(np.nan if z is None else z["holds"].mean())
        zf = load("full", k)
        hs.append(np.nan if zf is None else zf["holds"].mean())
        rad = rd.RADII + [1.0]
        # radius where the hold share falls through 50%, interpolated in log radius
        r50 = np.nan
        for i in range(len(hs) - 1):
            if hs[i] >= 0.5 > hs[i + 1]:
                f = (hs[i] - 0.5) / (hs[i] - hs[i + 1])
                r50 = float(np.exp(np.log(rad[i]) + f * (np.log(rad[i + 1]) - np.log(rad[i]))))
        rows.append([k] + [f"{100 * h:.0f}%" if not np.isnan(h) else "-" for h in hs] + [r50])
        data[k] = dict(radii=rad, holds=hs, r50=r50)
    section("D. How wide is the band? Hold share in boxes of growing radius around the baseline",
            "Radius = half-width of the box as a share of each uncertainty's range, in its own scale (64 draws per box; "
            "the full box is 192 draws). In these radius boxes the three structural parameters (ell_inf, omega, f_E) are "
            "held at their baseline of 0, and reinv at 0. 'r50' = radius where the hold share falls through 50%, "
            "interpolated in log radius.\n\n" + md_table(rows, ["design"] + [f"r {r:g}" for r in rd.RADII] + ["full box", "r50"]))
    OUT["radius"] = data
    if data:
        fig, ax = plt.subplots(figsize=(7, 4))
        styles = [(BLUE, "-", "o"), (ORANGE, "--", "s"), (BLACK, ":", "^"), (SKY, "-.", "D")]
        for (k, v), (c, ls, mk) in zip(data.items(), styles):
            ax.plot(v["radii"], 100 * np.array(v["holds"]), color=c, ls=ls, marker=mk, label=k)
            ax.annotate(k, (v["radii"][-1], 100 * v["holds"][-1]), textcoords="offset points", xytext=(4, 0), fontsize=7, color=c)
        ax.set_xscale("log")
        ax.set_xlabel("Box radius (share of each uncertainty's range; 1 = full box)")
        ax.set_ylabel("Draws where the pact holds (%)")
        ax.axhline(50, color=GREY, lw=0.8, ls=":")
        ax.legend(frameon=False, fontsize=8)
        ax.set_title("How fast the pact's band closes as uncertainty grows", loc="left", fontsize=10)
        savefig(fig, "rd_radius.png")


def fig_oat(oat_out):
    base = [o for o in oat_out if o["key"] == "base"][0]
    rows = [o for o in oat_out if o["key"] != "base"]
    use1 = not np.isnan(base.get("hold_r01", np.nan))
    k1, n1 = ("hold_r01", "radius-0.1 box") if use1 else ("hold_near", "near box")
    rows.sort(key=lambda o: (o[k1] - base[k1], o["hold_full"] - base["hold_full"]))
    fig, ax = plt.subplots(figsize=(9, 0.34 * len(rows) + 1.5))
    y = np.arange(len(rows))
    d1 = [100 * (o[k1] - base[k1]) for o in rows]
    df = [100 * (o["hold_full"] - base["hold_full"]) for o in rows]
    ax.barh(y + 0.2, d1, height=0.38, color=BLUE, label=f"{n1}, solid (baseline design holds {100 * base[k1]:.0f}%)")
    ax.barh(y - 0.2, df, height=0.38, color=ORANGE, hatch="//", edgecolor="white",
            label=f"full box, hatched (baseline design holds {100 * base['hold_full']:.0f}%)")
    for i in range(len(rows)):
        for v, off in ((d1[i], 0.2), (df[i], -0.2)):
            ax.text(v + (0.6 if v >= 0 else -0.6), i + off, f"{v:+.0f}", va="center", ha="left" if v >= 0 else "right", fontsize=7)
    ax.set_yticks(y)
    ax.set_yticklabels([o["label"] for o in rows], fontsize=8)
    ax.axvline(0, color=BLACK, lw=1)
    lim = max(5, max(abs(v) for v in d1 + df) * 1.25)
    ax.set_xlim(-lim, lim)
    ax.set_xlabel("Change in the share of draws where the pact holds, against the baseline design (percentage points)")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.set_title("One lever at a time: which settings widen the band?", loc="left", fontsize=10)
    savefig(fig, "rd_levers.png")


def erosion_report(best_lv=None):
    path = os.path.join(rd.RES, "robust_erosion.json")
    if not os.path.exists(path):
        return
    E = json.load(open(path))
    for title, body in E.get("tables", []):
        section(title, body)
    OUT["erosion"] = E.get("data", {})
    # ensemble: hold share on the radius-0.1 box against erosion rate
    designs = {"baseline design": {}}
    if best_lv:
        designs["best design"] = best_lv
    rows, curves = [], {}
    for lab, lv in designs.items():
        b = load("r0.1", rd.design_key(lv))
        for kind, vals, rots in (("q_er", [0.001, 0.003, 0.01, 0.03], [0.0, 10.0]), ("q_ea", [0.03, 0.1], [0.0])):
            for rot in rots:
                hs = [b["holds"].mean() if b is not None else np.nan]
                for v in vals:
                    d = dict(lv, **{kind: v})
                    if rot:
                        d["T_rot"] = rot
                    z = load("r0.1", rd.design_key(d))
                    hs.append(np.nan if z is None else z["holds"].mean())
                curves[(lab, kind, rot)] = ([0.0] + vals, hs)
                rows.append([lab, kind, "every 10 y" if rot else "never"] +
                            [f"{100 * h:.0f}%" if not np.isnan(h) else "-" for h in hs])
    hdr = ["design", "erosion", "key rotation", "rate 0"] + [f"{v:g}" for v in [0.001, 0.003, 0.01, 0.03]]
    rows_er = [r for r in rows if r[1] == "q_er"]
    rows_ea = [r for r in rows if r[1] == "q_ea"]
    section("E-ens. Denial erosion over the radius-0.1 box: share of draws where the pact holds",
            "Time erosion q_er (per-year rate). 64 draws, common random numbers.\n\n" + md_table(rows_er, hdr) +
            "\n\nSize erosion q_ea (share of firing probability lost per tenfold growth above Earth's industry).\n\n" +
            md_table(rows_ea, ["design", "erosion", "key rotation", "rate 0", "0.03", "0.1"]))
    OUT["erosion_ens"] = {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in curves.items()}
    fig, ax = plt.subplots(figsize=(7, 4))
    sty = {("baseline design", 0.0): (ORANGE, "--", "s"), ("baseline design", 10.0): (ORANGE, ":", "x"),
           ("best design", 0.0): (BLUE, "-", "o"), ("best design", 10.0): (BLUE, "-.", "D")}
    for (lab, kind, rot), (xs, hs) in curves.items():
        if kind != "q_er":
            continue
        c, ls, mk = sty[(lab, rot)]
        x = [1e-4] + xs[1:]
        nm = f"{lab}, {'rotate keys every 10 y' if rot else 'no rotation'}"
        ax.plot(x, 100 * np.array(hs), color=c, ls=ls, marker=mk, label=nm)
    ax.set_xscale("log")
    ax.set_xticks([1e-4, 1e-3, 3e-3, 1e-2, 3e-2])
    ax.set_xticklabels(["0", "0.001", "0.003", "0.01", "0.03"])
    ax.set_xlabel("Denial erosion rate q_er (share of firing probability lost per year)")
    ax.set_ylabel("Draws where the pact holds (%)")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Gradual capture of the denial keys (radius-0.1 box)", loc="left", fontsize=10)
    savefig(fig, "rd_erosion.png")


if __name__ == "__main__":
    report()
