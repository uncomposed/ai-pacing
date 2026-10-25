"""
Run every analysis for results/equilibrium.md and write tables + PNGs.

    python3 run_equilibrium.py            # full run (about 30-45 min on a laptop)
    python3 run_equilibrium.py --quick    # coarse grids, short horizon: smoke test only

Outputs: figures/eq_*.png, results/equilibrium_tables.md, results/equilibrium_summary.json.
results/equilibrium.md is written by hand from those tables.
Colours: Okabe-Ito blue / sky blue / orange / reddish purple, always backed by hatching,
line style, markers or direct text labels (never colour alone, never red vs green).
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

import equilibrium_model as em

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
RES = os.path.join(HERE, "results")
os.makedirs(FIG, exist_ok=True)
os.makedirs(RES, exist_ok=True)

BLUE, SKY, ORANGE, PURPLE, GREY, BLACK, YELLOW = "#0072B2", "#56B4E9", "#E69F00", "#CC79A7", "#999999", "#000000", "#F0E442"
plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 150, "font.size": 10, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": False, "hatch.linewidth": 0.6,
})

CFG = dict(T_H=300, nA=160, N=2)
OUT: dict = {}
TABLES: list[str] = []


def savefig(fig, name):
    path = os.path.join(FIG, name)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def fmt(x):
    if isinstance(x, (float, np.floating)):
        if np.isnan(x):
            return "-"
        if x == 0:
            return "0"
        if abs(x) >= 1e4 or abs(x) < 1e-2:
            return f"{x:.2g}"
        return f"{x:.3g}"
    return str(x)


def md_table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        out.append("| " + " | ".join(fmt(v) for v in r) + " |")
    return "\n".join(out)


def section(title, body):
    TABLES.append(f"## {title}\n\n{body}\n")
    print(f"\n## {title}\n{body}\n", flush=True)


def solve(over_list, **kw):
    cfg = dict(CFG)
    cfg.update(kw)
    ps = em.batch([em.baseline(**o) for o in over_list])
    return em.solve(ps, N=cfg["N"], T_H=cfg["T_H"], nA=cfg["nA"],
                    **{k: v for k, v in kw.items() if k not in ("T_H", "nA", "N")})


def act0(r, i):
    """The AI's equilibrium move at t = 0 (the solver's own tie-broken choice)."""
    return str(r["act0"][i])


def outcome_class(r, i):
    """0 cooperate (no strike, no rival is the likeliest end), 1 rival AI likeliest,
    2 wait-then-strike, 3 strike now."""
    if act0(r, i) == "S":
        return 3
    if r["att"][i] >= 0.5:
        return 2
    if r["riv"][i] >= 0.5:
        return 1
    return 0


CLASS_NAMES = ["Cooperate / wait, no strike", "Rival AI emerges", "Wait, then strike", "Strike now"]
CLASS_COLORS = [BLUE, SKY, ORANGE, PURPLE]
CLASS_HATCH = ["", "..", "//", "xx"]


def row_summary(r, i):
    return [act0(r, i), r["att"][i], r["t_mean"][i], r["suc"][i], r["riv"][i], r["exit"][i],
            r["starts"][i], r["WH"][i], np.log(r["VA"][i])]


SUM_HDR = ["AI move at t=0", "P(strike ever)", "mean strike year", "P(seized)", "P(rival)",
           "P(AI exits)", "programmes started", "human welfare (1=today)", "ln AI value"]


# ---------------------------------------------------------------------------
# 0. Verification
# ---------------------------------------------------------------------------
def checks():
    lines = []
    # (1) no growth, no threat, strikes always fail and kill: V = flow / (1 - delta)
    o = dict(g=1e-9, mu=0.0, beta_bg=0.0, p_s0=0.0, eps=0.0, seq=3)
    r = solve([o], T_H=200)
    p = em.baseline(**o)
    delta = np.exp(-p["r"])
    A0 = p["A0"]
    exact = (A0 + p["sigma"] * p["gam"] * A0) / (1 - delta)
    lines.append(["no growth, no threat: V_AI vs flow/(1-delta)", float(r["VA"][0]), exact,
                  float(r["VA"][0] / exact - 1)])
    exactH = (1 + (1 - p["sigma"]) * p["gam"] * A0 / 2 - p["c_den"] / 2)
    lines.append(["no growth, no threat: human welfare-equivalent flow", float(r["WH"][0]), exactH,
                  float(r["WH"][0] / exactH - 1)])
    # (2) growth, no threat, no strikes possible: grid value vs. direct forward sum along the
    #     exact (continuous-A) pact path with policy a
    o = dict(mu=0.0, beta_bg=0.0, p_s0=0.0, eps=0.0, seq=0)
    r = solve([o], T_H=400)
    p = em.baseline(**o)
    A, F, V = p["A0"], 1.0, 0.0
    for t in range(4000):
        trade = p["gam"] * min(A, p["H"])
        V += np.exp(-p["r"] * t) * (A + p["sigma"] * trade)
        closed = A >= p["A_close"]
        chi = 1.0 if closed else p["chi0"] + (1 - p["chi0"]) * F
        if closed:
            F = max(0.0, F - 1 / p["T_dis"])
        A = A * np.exp(p["g"] * chi * max(0.0, 1 - A / p["Kmax"]))
    lines.append(["growth, no threat (policy a): grid V_AI vs direct path sum", float(r["VA"][0]), V,
                  float(r["VA"][0] / V - 1)])
    # (3) late-stage closed form: threshold trade share sigma* at the cap
    G = em.Grid(2 * 1e9, nA=CFG["nA"])
    Acap = float(G.A[np.searchsorted(G.A, 1e9)])
    sig = np.linspace(0.0, 1.0, 41)
    base = dict(A0=Acap, seq=3, B_R=0.0, den=1.0, c_A=0.5)
    r = solve([dict(base, sigma=s) for s in sig], T_H=300)
    dp_strike = np.array([act0(r, i) == "S" for i in range(len(sig))])
    cf = np.array([em.cap_strike_gap(em.baseline(**dict(base, sigma=s)), Acap, F=1.0) > 0 for s in sig])
    lines.append(["cap: sigma values where DP and closed form disagree on strike (of 41)",
                  int(np.sum(dp_strike != cf)), 0, float(np.sum(dp_strike != cf))])
    sstar_dp = sig[np.argmax(~dp_strike)] if (~dp_strike).any() else np.nan
    sstar_cf = sig[np.argmax(~cf)] if (~cf).any() else np.nan
    lines.append(["cap: smallest sigma with no strike, DP vs closed form", sstar_dp, sstar_cf,
                  float(sstar_dp - sstar_cf)])
    t = em.cap_condition_terms(em.baseline(**base), F=1.0)
    s_lin = (t["prize"] - t["cost"] + t["threat_highground"]) / (em.baseline()["gam"])
    lines.append(["cap: first-order sigma* = (prize - cost + threat)/gam", s_lin, sstar_cf, float(s_lin - sstar_cf)])
    # (4) growth-stage condition after closure (A >> D): strike iff expected prize after plugging
    #     exceeds D * [c_A + (1 - p_s0) ln(1/(1 - L_f))]. No threat, no racing, sweep q.
    qs = np.linspace(0.0, 1.0, 41)
    base = dict(A0=3.0, seq=3, B_R=0.0, B_Rc=0.0, beta_bg=0.0, w_seized=0.9)
    r = solve([dict(base, q=q) for q in qs], T_H=300)
    dp = np.array([act0(r, i) == "S" for i in range(len(qs))])
    p = em.baseline(**base)
    A3 = 3.0
    thr = p["D"] * (p["c_A"] * A3 / (A3 + p["D"]) + (1 - p["p_s0"]) * A3 / (A3 + p["D"]) * np.log(1 / (1 - p["L_f"])))
    q_cf = (1 - thr / ((1 - p["c_w"]) * p["H"])) / p["d"]
    q_dp = qs[np.argmax(~dp)] if (~dp).any() else np.nan
    lines.append(["growth stage (A=3, after closure): smallest denial credibility q with no strike, DP vs closed form",
                  q_dp, q_cf, float(q_dp - q_cf)])
    section("Verification", md_table(lines, ["check", "model", "reference", "difference"]))
    OUT["checks"] = lines
    return lines


def convergence(scen):
    rows = []
    for lab, kw in (("nA=120", dict(nA=120)), ("nA=160, T_H=300 (default)", {}), ("nA=240", dict(nA=240)),
                    ("T_H=150", dict(T_H=150)), ("T_H=600", dict(T_H=600)),
                    ("terminal = seized", dict(terminal="seized"))):
        r = solve([s for _, s in scen], **kw)
        for i, (name, _) in enumerate(scen):
            rows.append([lab, name] + row_summary(r, i))
    section("Numerical robustness (grid size, horizon, terminal condition)",
            md_table(rows, ["setting", "scenario"] + SUM_HDR))
    OUT["convergence"] = rows


def mc_check(over, name):
    r = solve([over], store=True)
    rec = em.simulate(r, 0, M=6000, seed=11)
    rows = [[name, "P(strike ever)", r["att"][0], np.mean(~np.isnan(rec["t_strike"]))],
            [name, "P(seized)", r["suc"][0], rec["seized"][-1]],
            [name, "P(rival)", r["riv"][0], rec["rival"][-1]]]
    section(f"Forward Monte Carlo (6000 paths) vs backward recursion: {name}",
            md_table(rows, ["scenario", "quantity", "backward recursion", "Monte Carlo"]))
    return r, rec


# ---------------------------------------------------------------------------
# 1. Named scenarios
# ---------------------------------------------------------------------------
SCEN = [
    ("S1 baseline pact: a (dismantle after closure), B_R=5", dict()),
    ("S2 same, sequencing b (relocate fabs to orbit)", dict(seq=1)),
    ("S3 same, sequencing c (dismantle early)", dict(seq=2)),
    ("S4 same, n (never dismantle)", dict(seq=3)),
    ("S5 c + strong denial (q=d=1)", dict(seq=2, q=1.0, d=1.0)),
    ("S6 a, no denial reserve", dict(den=0.0)),
    ("S7 a, high temptation B_R=10", dict(B_R=10.0)),
    ("S8 b, high temptation B_R=10", dict(seq=1, B_R=10.0)),
    ("S9 a, B_R=10 + AI may remove detected programmes", dict(B_R=10.0, police=1.0)),
    ("S10 a, no temptation B_R=0", dict(B_R=0.0)),
    ("S11 a, high threat floor 0.3", dict(th_floor=0.3)),
    ("S12 a, zero floor and no rogue background", dict(th_floor=0.0, beta_bg=0.0)),
    ("S13 a, rival stays dangerous ell_inf=0.01", dict(ell_inf=0.01)),
    ("S14 S13 + seizure leaves humans 90% welfare", dict(ell_inf=0.01, w_seized=0.9)),
    ("S15 S13 + zero floor, no rogue", dict(ell_inf=0.01, th_floor=0.0, beta_bg=0.0)),
    ("S16 a, harvest f_E=1e-6", dict(f_E=1e-6)),
    ("S17 a, harvest f_E=1e-6, AI values humans omega=1e-5", dict(f_E=1e-6, omega=1e-5)),
    ("S18 a, trade reinvested (reinv=1)", dict(reinv=1.0)),
    ("S19 a, takeover hard (p_s0=0.1)", dict(p_s0=0.1)),
    ("S20 a, takeover easy (p_s0=0.9)", dict(p_s0=0.9)),
    ("S21 a, failed early strike not fatal (kill_pre=0)", dict(kill_pre=0.0)),
    ("S22 a, demilitarised harder: D=0.03", dict(D=0.03)),
    ("S23 a, tribute: AI pays 10% of output (psi_div=0.1)", dict(psi_div=0.1)),
    ("S24 a, no denial + trade reinvested", dict(den=0.0, reinv=1.0)),
    ("S25 a, no denial + trade reinvested, AI share 0.9", dict(den=0.0, reinv=1.0, sigma=0.9)),
]


def scenarios():
    r = solve([s for _, s in SCEN])
    rows = [[name] + row_summary(r, i) + [CLASS_NAMES[outcome_class(r, i)]] for i, (name, _) in enumerate(SCEN)]
    section("Named scenarios (N=2 states, equilibrium play, Variant A unless stated)",
            md_table(rows, ["scenario"] + SUM_HDR + ["outcome class"]))
    OUT["scenarios"] = rows
    # N = 3 and equilibrium-selection robustness on a subset
    sub = [SCEN[i] for i in (0, 1, 2, 6, 9, 12, 13, 15)]
    rows = []
    for lab, kw in (("N=3 states", dict(N=3)), ("worst stage equilibrium for humans", dict(sel="worst"))):
        r = solve([s for _, s in sub], **kw)
        rows += [[lab, name] + row_summary(r, i) + [CLASS_NAMES[outcome_class(r, i)]] for i, (name, _) in enumerate(sub)]
    section("Robustness: three human states; pessimistic equilibrium selection",
            md_table(rows, ["setting", "scenario"] + SUM_HDR + ["outcome class"]))
    OUT["scenarios_robust"] = rows


# ---------------------------------------------------------------------------
# 2. Pact designer: best menu item under each world
# ---------------------------------------------------------------------------
def design():
    worlds = [("A: high ground holds (ell_inf=0), B_R=5", dict()),
              ("A: high ground holds, B_R=10", dict(B_R=10.0)),
              ("B: rival stays dangerous (ell_inf=0.01), B_R=5", dict(ell_inf=0.01)),
              ("B + seizure not lethal (w_seized=0.9)", dict(ell_inf=0.01, w_seized=0.9)),
              ("A + harvest term f_E=1e-6", dict(f_E=1e-6))]
    menu = [dict(seq=s, sigma=g, den=d, police=pl) for s in (0, 1, 2) for g in (0.05, 0.3, 0.6, 0.9)
            for d in (0.0, 1.0) for pl in (0.0, 1.0)]
    rows, best_rows = [], []
    for wname, w in worlds:
        r = solve([dict(w, **m_) for m_ in menu])
        WH = r["WH"]
        order = np.argsort(-WH)
        b = order[0]
        mb = menu[b]
        best_rows.append([wname, "abc"[int(mb["seq"])], mb["sigma"], int(mb["den"]), int(mb["police"])] +
                         row_summary(r, b) + [CLASS_NAMES[outcome_class(r, b)]])
        n_peace = sum(outcome_class(r, i) == 0 for i in range(len(menu)))
        n_now = sum(outcome_class(r, i) == 3 for i in range(len(menu)))
        rows.append([wname, len(menu), n_peace, n_now,
                     ", ".join(sorted({"abc"[int(menu[i]["seq"])] for i in range(len(menu)) if outcome_class(r, i) == 0})) or "none"])
        for i, m_ in enumerate(menu):
            OUT.setdefault("design_all", []).append([wname, int(m_["seq"]), m_["sigma"], m_["den"], m_["police"],
                                                     float(WH[i]), float(r["att"][i]), float(r["riv"][i]), outcome_class(r, i)])
    section("Pact designer: human-best menu item in each world (menu: seq a/b/c x sigma {0.05,0.3,0.6,0.9} x denial x policing)",
            md_table(best_rows, ["world", "seq", "sigma", "denial", "police"] + SUM_HDR + ["outcome class"]))
    section("How many of the 48 menu items give each outcome",
            md_table(rows, ["world", "menu items", "cooperate (no strike, no rival)", "strike now", "sequencings that can give cooperation"]))
    OUT["design_best"] = best_rows


# ---------------------------------------------------------------------------
# 3. Phase maps
# ---------------------------------------------------------------------------
def phase_map(xname, xs, yname, ys, base, xlog=False, ylog=False):
    combos = [dict(base, **{xname: x, yname: y}) for y in ys for x in xs]
    r = solve(combos)
    n = len(combos)
    cls = np.array([outcome_class(r, i) for i in range(n)]).reshape(len(ys), len(xs))
    tm = np.array(r["t_mean"]).reshape(len(ys), len(xs))
    att = np.array(r["att"]).reshape(len(ys), len(xs))
    riv = np.array(r["riv"]).reshape(len(ys), len(xs))
    wh = np.array(r["WH"]).reshape(len(ys), len(xs))
    return dict(cls=cls, tm=tm, att=att, riv=riv, wh=wh, xs=np.asarray(xs), ys=np.asarray(ys))


def draw_cls(ax, pm, title, xlabel, ylabel, xlog=False, ylog=False, annotate=True):
    xs, ys = pm["xs"], pm["ys"]
    xe = _edges(xs, xlog)
    ye = _edges(ys, ylog)
    for iy in range(len(ys)):
        for ix in range(len(xs)):
            c = pm["cls"][iy, ix]
            ax.add_patch(plt.Rectangle((xe[ix], ye[iy]), xe[ix + 1] - xe[ix], ye[iy + 1] - ye[iy],
                                       facecolor=CLASS_COLORS[c], hatch=CLASS_HATCH[c], edgecolor="white", lw=0.5))
            if annotate:
                if c == 2:
                    ax.text(np.sqrt(xe[ix] * xe[ix + 1]) if xlog else 0.5 * (xe[ix] + xe[ix + 1]),
                            np.sqrt(ye[iy] * ye[iy + 1]) if ylog else 0.5 * (ye[iy] + ye[iy + 1]),
                            f"{pm['tm'][iy, ix]:.0f}", ha="center", va="center", fontsize=6.5, color=BLACK)
                elif c in (0, 1):
                    ax.text(np.sqrt(xe[ix] * xe[ix + 1]) if xlog else 0.5 * (xe[ix] + xe[ix + 1]),
                            np.sqrt(ye[iy] * ye[iy + 1]) if ylog else 0.5 * (ye[iy] + ye[iy + 1]),
                            f"{100 * pm['riv'][iy, ix]:.0f}%", ha="center", va="center", fontsize=6, color=BLACK)
    ax.set_xlim(xe[0], xe[-1])
    ax.set_ylim(ye[0], ye[-1])
    if xlog:
        ax.set_xscale("log")
    if ylog:
        ax.set_yscale("log")
    ax.set_title(title, loc="left", fontsize=9.5)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)


def _edges(v, log):
    v = np.asarray(v, float)
    if log:
        lv = np.log(v)
        mid = 0.5 * (lv[1:] + lv[:-1])
        return np.exp(np.concatenate([[lv[0] - (mid[0] - lv[0])], mid, [lv[-1] + (lv[-1] - mid[-1])]]))
    mid = 0.5 * (v[1:] + v[:-1])
    return np.concatenate([[v[0] - (mid[0] - v[0])], mid, [v[-1] + (v[-1] - mid[-1])]])


def cls_legend(fig_or_ax, loc="upper center", **kw):
    h = [Patch(facecolor=CLASS_COLORS[i], hatch=CLASS_HATCH[i], edgecolor="white", label=CLASS_NAMES[i]) for i in range(4)]
    return fig_or_ax.legend(handles=h, loc=loc, frameon=False, ncol=4, fontsize=8, **kw)


def map_temptation_floor(n_x, n_y):
    xs = np.linspace(0, 20, n_x)
    ys = np.array([0.0, 0.01, 0.03, 0.05, 0.1, 0.2, 0.3, 0.5])[:n_y] if n_y < 8 else np.array([0.0, 0.01, 0.03, 0.05, 0.1, 0.2, 0.3, 0.5])
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.8), sharey=True)
    res = {}
    for ax, (s, nm) in zip(axs, ((0, "a: dismantle after closure"), (1, "b: relocate fabs to orbit"), (2, "c: dismantle early"))):
        pm = phase_map("B_R", xs, "th_floor", ys, dict(seq=s))
        draw_cls(ax, pm, f"Sequencing {nm}", "Private gain to a state from its own rival AI, B_R (years of welfare)",
                 "Residual threat floor th_floor" if s == 0 else "")
        res[s] = pm
    cls_legend(fig, loc="lower center", bbox_to_anchor=(0.5, -0.06))
    fig.suptitle("Equilibrium outcome vs. temptation to defect and residual threat floor "
                 "(Variant A: high ground holds). Cell text: P(rival) or mean strike year",
                 x=0.01, ha="left", fontsize=11)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    path = savefig(fig, "eq_phase_temptation_floor.png")
    # threshold B_R* per (seq, floor): smallest B_R with strike now
    rows = []
    for s, pm in res.items():
        for iy, y in enumerate(pm["ys"]):
            now = np.nonzero(pm["cls"][iy] == 3)[0]
            rows.append(["abc"[s], y, pm["xs"][now[0]] if len(now) else np.nan,
                         CLASS_NAMES[pm["cls"][iy, 0]], pm["riv"][iy, 0]])
    section("Temptation threshold: smallest B_R on the grid at which the AI strikes now",
            md_table(rows, ["seq", "threat floor", "B_R* (strike now from here)", "outcome at B_R=0", "P(rival) at B_R=0"]))
    OUT["map_temptation_floor"] = {str(k): {kk: np.asarray(v).tolist() for kk, v in pm.items()} for k, pm in res.items()}
    return path


def map_wait(n):
    xs = np.concatenate([[1e-7], np.logspace(-6, -1, n - 1)])
    ys = np.array([0.0, 0.25, 0.5, 0.75, 0.9, 1.0])
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
    res = {}
    for ax, (nm, base) in zip(axs, (("rogue background on (beta_bg=0.05)", dict()),
                                    ("only state programmes (beta_bg=0), B_R=0", dict(beta_bg=0.0, B_R=0.0)))):
        pm = phase_map("ell_inf", xs, "w_seized", ys, base)
        draw_cls(ax, pm, nm, "Irreducible rival damage ell_inf (share of AI value; 1e-7 plotted as ~0)",
                 "Human welfare after a seizure, w_seized (1 = unharmed)", xlog=True)
        res[nm] = pm
    cls_legend(fig, loc="lower center", bbox_to_anchor=(0.5, -0.06))
    fig.suptitle("Testing 'it will just wait': does waiting end in cooperation or a strike? "
                 "(seq a, B_R=5 unless stated). Orange cells: mean strike year", x=0.01, ha="left", fontsize=11)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    OUT["map_wait"] = {k: {kk: np.asarray(v).tolist() for kk, v in pm.items()} for k, pm in res.items()}
    rows = []
    for k, pm in res.items():
        for iy, y in enumerate(pm["ys"]):
            rows.append([k, y] + [CLASS_NAMES[c][:14] + (f" ({pm['tm'][iy, ix]:.0f}y)" if c == 2 else "")
                                  for ix, c in enumerate(pm["cls"][iy])])
    section("Wait test grid (rows: w_seized; columns: ell_inf = " + ", ".join(f"{x:.0e}" for x in xs) + ")",
            md_table(rows, ["world", "w_seized"] + [f"{x:.0e}" for x in xs]))
    return savefig(fig, "eq_phase_wait.png")


def map_harvest(n):
    xs = np.logspace(-12, -2, n)
    ys = np.concatenate([[0.0], np.logspace(-12, -2, n - 1)])
    pm = phase_map("f_E", xs, "omega", np.maximum(ys, 0.0), dict(w_seized=0.9))
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ys_plot = np.where(ys == 0, 1e-13, ys)
    pm_plot = dict(pm, ys=ys_plot)
    draw_cls(ax, pm_plot, "Late-stage harvest (preference, not incentive): seq a, Kmax=1e9, w_seized=0.9",
             "Earth's share of the AI's late resource base f_E", "AI's intrinsic value on intact humanity omega (bottom row = 0)",
             xlog=True, ylog=True)
    p = em.baseline()
    xx = np.logspace(-12, -2, 50)
    ax.plot(xx, xx * (1 - p["c_grav"]), "--", color=BLACK, lw=1.5, label="closed form: omega = f_E (1 - c_grav)")
    xline = p["sigma"] * p["gam"] / ((1 - p["c_grav"]) * p["Kmax"])
    ax.axvline(xline, color=BLACK, ls=":", lw=1.5, label="closed form: f_E (1-c_grav) Kmax = trade")
    ax.legend(frameon=False, fontsize=7.5, loc="upper left")
    h = [Patch(facecolor=CLASS_COLORS[i], hatch=CLASS_HATCH[i], edgecolor="white", label=CLASS_NAMES[i]) for i in range(4)]
    fig.legend(handles=h, loc="lower center", ncol=2, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.08))
    fig.tight_layout()
    OUT["map_harvest"] = {kk: np.asarray(v).tolist() for kk, v in pm.items()}
    rows = [[f"{y:.0e}"] + [CLASS_NAMES[c][:14] + (f" ({pm['tm'][iy, ix]:.0f}y)" if c == 2 else "")
                            for ix, c in enumerate(pm["cls"][iy])] for iy, y in enumerate(ys)]
    section("Harvest grid (rows: omega; columns: f_E = " + ", ".join(f"{x:.0e}" for x in xs) + ")",
            md_table(rows, ["omega"] + [f"{x:.0e}" for x in xs]))
    return savefig(fig, "eq_phase_harvest.png")


# ---------------------------------------------------------------------------
# 4. Paths (forward Monte Carlo on the equilibrium)
# ---------------------------------------------------------------------------
def paths():
    cases = [("Pact holds (S1)", dict()),
             ("Strike now (S7, B_R=10)", dict(B_R=10.0)),
             ("Wait, then strike (S14)", dict(ell_inf=0.01, w_seized=0.9)),
             ("Harvest (S16 + w_seized=0.9)", dict(f_E=1e-6, w_seized=0.9))]
    r = solve([c for _, c in cases], store=True)
    fig, axs = plt.subplots(2, 2, figsize=(13, 8.5), sharex=True)
    rows = []
    for k, (ax, (nm, _)) in enumerate(zip(axs.flat, cases)):
        rec = em.simulate(r, k, M=4000, seed=5 + k, T=200)
        t = rec["t"]
        ax.plot(t, rec["pact"], "-", color=BLUE, lw=2, label="pact in force")
        ax.plot(t, rec["seized"], "--", color=PURPLE, lw=2, label="Earth seized")
        ax.plot(t, rec["rival"], "-.", color=SKY, lw=2, label="rival AI exists")
        ax.plot(t, rec["killed"], ":", color=ORANGE, lw=2, label="AI shut down (failed strike)")
        ax.plot(t, rec["coll"], linestyle=(0, (1, 3)), color=BLACK, lw=1.5, label="pact collapsed, both alive")
        ax2 = ax.twinx()
        ax2.plot(t, rec["lnA"] / np.log(10), color=GREY, lw=1, label="log10 AI capacity (right axis)")
        ax2.set_ylabel("log10 AI capacity (living paths)", color="#555")
        ax2.spines["top"].set_visible(False)
        ax.set_ylim(-0.02, 1.02)
        ax.set_title(nm, loc="left", fontsize=10)
        ax.set_ylabel("share of 4000 simulated paths")
        ts = rec["t_strike"]
        rows.append([nm, r["att"][k], np.nanmedian(ts) if np.any(~np.isnan(ts)) else np.nan,
                     rec["seized"][-1], rec["rival"][-1], rec["killed"][-1], rec["pact"][-1]])
        if k == 0:
            h1, l1 = ax.get_legend_handles_labels()
            h2, l2 = ax2.get_legend_handles_labels()
            ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=7.5, loc="center right")
    for ax in axs[1]:
        ax.set_xlabel("years")
    fig.suptitle("Equilibrium paths (forward simulation of the solved game)", x=0.01, ha="left", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    section("Path summaries (Monte Carlo, 4000 paths, 200 years)",
            md_table(rows, ["case", "P(strike ever) backward", "median strike year (MC)", "seized @200y", "rival @200y",
                            "AI shut down @200y", "pact in force @200y"]))
    return savefig(fig, "eq_paths.png")


def sequencing_paths():
    """The bootstrap tension: Earth fabs are the AI's only chip source before closure."""
    cases = [(0, "a: dismantle after closure", BLUE, "-"), (1, "b: relocate to orbit", SKY, "--"),
             (2, "c: dismantle early", ORANGE, "-."), (3, "n: never dismantle", PURPLE, ":")]
    # forbid strikes (p_s0=0, eps=0) to show the pure growth / threat-capacity trade-off, then the
    # equilibrium with strikes allowed
    r0 = solve([dict(seq=s, B_R=0.0, p_s0=0.0, eps=0.0) for s, *_ in cases], store=True, T_H=300)
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.4))
    rows = []
    for k, (s, nm, c, ls) in enumerate(cases):
        rec = em.simulate(r0, k, M=600, seed=3, T=150)
        t = rec["t"]
        axs[0].plot(t, rec["lnA"] / np.log(10), ls, color=c, lw=2, label=nm)
        axs[1].plot(t, rec["F"], ls, color=c, lw=2, label=nm)
        tau = 0.05 + 0.95 * rec["F"]
        axs[2].plot(t, tau, ls, color=c, lw=2, label=nm)
        tclose = t[np.argmax(rec["lnA"] >= np.log(0.1))] if np.any(rec["lnA"] >= np.log(0.1)) else np.nan
        rows.append([nm, tclose, np.log(r0["VA"][k]), r0["riv"][k], r0["WH"][k]])
    axs[0].axhline(-1, color=GREY, lw=1)
    axs[0].text(1, -0.9, "semiconductor closure (A=0.1)", fontsize=8)
    axs[0].set_ylabel("log10 AI capacity")
    axs[1].set_ylabel("Earth leading-edge fab capacity F")
    axs[2].set_ylabel("Earth rival-building capacity tau = floor + (1-floor) F")
    for ax in axs:
        ax.set_xlabel("years")
        ax.legend(frameon=False, fontsize=8)
    axs[0].set_title("AI growth: fabs are its only chip source before closure", loc="left", fontsize=10)
    axs[1].set_title("Fab schedule", loc="left", fontsize=10)
    axs[2].set_title("Threat capacity left on Earth", loc="left", fontsize=10)
    fig.suptitle("Sequencing tension with strikes switched off (B_R=0)", x=0.01, ha="left", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    section("Sequencing with strikes switched off (B_R=0, p_s0=0): growth vs. threat window",
            md_table(rows, ["sequencing", "years to closure", "ln AI value (no strikes)", "P(rival)", "human welfare"]))
    return savefig(fig, "eq_sequencing.png")


# ---------------------------------------------------------------------------
# 5. One-at-a-time sensitivity around S1
# ---------------------------------------------------------------------------
TORNADO_KEYS = ["B_R", "B_Rc", "B_o", "kap_coll", "c_sanc", "zeta", "L_det", "mu", "beta_bg", "th_floor", "s_R0",
                "ell_inf", "nu", "w_seized", "r_h", "p_s0", "D", "eps", "c_w", "c_A", "L_f", "kill_pre", "d", "q",
                "g", "chi0", "A_close", "A0", "T_dis", "Kmax", "gam", "sigma", "r", "eta", "omega", "f_E"]


def tornado():
    over = []
    for k in TORNADO_KEYS:
        _, lo, hi, *_ = em.PARAMS[k]
        if k == "f_E":
            lo, hi = 0.0, 1e-6
        if k == "ell_inf":
            lo, hi = 0.0, 0.01
        if k == "omega":
            lo, hi = 0.0, 1e-5
        over += [{k: lo}, {k: hi}]
    r = solve([dict()] + over)
    base = 0
    rows = []
    for j, k in enumerate(TORNADO_KEYS):
        il, ih = 1 + 2 * j, 2 + 2 * j
        rows.append([k, over[2 * j][k], over[2 * j + 1][k], r["WH"][il], r["WH"][ih],
                     CLASS_NAMES[outcome_class(r, il)], CLASS_NAMES[outcome_class(r, ih)],
                     abs(r["WH"][ih] - r["WH"][il])])
    rows.sort(key=lambda x: -x[-1])
    section(f"One-at-a-time sensitivity around S1 (baseline human welfare {r['WH'][base]:.3f}, outcome "
            f"{CLASS_NAMES[outcome_class(r, base)]})",
            md_table(rows, ["param", "low", "high", "welfare @low", "welfare @high", "outcome @low", "outcome @high", "|swing|"]))
    top = rows[:18][::-1]
    fig, ax = plt.subplots(figsize=(9, 7))
    w0 = r["WH"][base]
    for i, (k, lo, hi, wl, wh, cl, ch, _) in enumerate(top):
        ax.barh(i, wl - w0, left=w0, color=BLUE, height=0.38, align="edge", edgecolor="white")
        ax.barh(i - 0.38, wh - w0, left=w0, color=ORANGE, hatch="//", height=0.38, align="edge", edgecolor="white")
        xr = max(wl, wh, w0) + 0.02
        ax.text(xr, i + 0.19, f"low {fmt(lo)}: {cl[:13]}", va="center", ha="left", fontsize=6.5)
        ax.text(xr, i - 0.19, f"high {fmt(hi)}: {ch[:13]}", va="center", ha="left", fontsize=6.5)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels([x[0] for x in top])
    ax.axvline(w0, color=BLACK, lw=1)
    ax.set_xlim(0.0, 1.75)
    ax.set_xlabel("Human welfare, yearly equivalent (1 = today; 0.49 = AI strikes now with 50% success)")
    ax.legend(handles=[Patch(color=BLUE, label="parameter LOW (solid)"),
                       Patch(facecolor=ORANGE, hatch="//", edgecolor="white", label="parameter HIGH (hatched)")],
              frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2)
    ax.set_title("One-at-a-time sensitivity around the baseline pact (S1). Labels: outcome class", loc="left", fontsize=10)
    OUT["tornado"] = rows
    return savefig(fig, "eq_tornado.png")


def main(quick=False):
    t0 = time.time()
    if quick:
        CFG.update(T_H=150, nA=100)
    checks()
    convergence([SCEN[0], SCEN[6], SCEN[13], SCEN[15]])
    mc_check(dict(B_R=5.0, ell_inf=0.01, w_seized=0.9), "S14 wait-then-strike")
    mc_check(dict(), "S1 baseline")
    scenarios()
    design()
    figs = [sequencing_paths(), paths(),
            map_temptation_floor(6 if quick else 11, 4 if quick else 8),
            map_wait(4 if quick else 9), map_harvest(4 if quick else 9), tornado()]
    with open(os.path.join(RES, "equilibrium_tables.md"), "w") as f:
        f.write("# Equilibrium model: auto-generated tables\n\n"
                "Generated by `run_equilibrium.py`" + (" (QUICK MODE, not for quoting)" if quick else "") +
                f". Settings: {CFG}. Status: implemented + verified, not human_validated.\n\n")
        f.write("\n".join(TABLES))
    with open(os.path.join(RES, "equilibrium_summary.json"), "w") as f:
        json.dump(OUT, f, indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x))
    print("figures:", figs)
    print(f"done in {time.time() - t0:.0f} s")


# ---------------------------------------------------------------------------
# Round 2: Cole's answers (2026-10-16). Named results R1-R4.
# ---------------------------------------------------------------------------
SQ = dict(seq=3, den=0.0, D=1.0)      # status quo: fabs stay, no denial reserve, Earth not demilitarised


def r1_compute_ratio():
    rows = []
    for nu in (1.0, 2.0, 3.0):
        for rh in (1.0, 0.1):
            lr = lambda rho: rho ** nu / (rho ** nu + rh ** nu)
            rows.append([nu, rh, lr(1.0), lr(0.1), lr(0.01), lr(0.001)])
    section("R1a. Rival damage as a function of the Earth/off-Earth compute ratio rho (ell_inf = 0)",
            md_table(rows, ["steepness nu", "rho_h (half-damage ratio)", "damage at 1:1", "at 1:10", "at 1:100", "at 1:1000"]))
    # ratio along the equilibrium path of S1, with and without moving compute to orbit
    r = solve([dict(), dict(move_c=1.0)], store=True)
    rows = []
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for k, (nm, c, ls) in enumerate((("S1, compute stays on Earth", BLUE, "-"), ("S1 + move compute to orbit", ORANGE, "--"))):
        rec = em.simulate(r, k, M=800, seed=2, T=120)
        p = em.baseline(**({} if k == 0 else dict(move_c=1.0)))
        tau = em.earth_threat(p, rec["F"])
        rho = p["s_R0"] * tau / np.exp(rec["lnA"])
        ax.plot(rec["t"], np.log10(rho), ls, color=c, lw=2, label=nm)
        t100 = rec["t"][np.argmax(rho <= 0.01)] if np.any(rho <= 0.01) else np.nan
        t1000 = rec["t"][np.argmax(rho <= 0.001)] if np.any(rho <= 0.001) else np.nan
        rows.append([nm, rho[0], t100, t1000, r["riv"][k], r["WH"][k], CLASS_NAMES[outcome_class(r, k)]])
    ax.axhline(-2, color=BLACK, ls=":", lw=1.2)
    ax.text(30, -1.8, "Cole's safe point 1:100", fontsize=8)
    ax.set_xlabel("years")
    ax.set_ylabel("log10 Earth/off-Earth compute ratio rho")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("R1: compute ratio along the equilibrium path (S1)", loc="left", fontsize=10)
    savefig(fig, "eq_r1_ratio.png")
    section("R1b. When does Earth's compute fall below 1:100 of the off-Earth base? (S1 equilibrium path)",
            md_table(rows, ["case", "rho at year 0", "year rho < 1:100", "year rho < 1:1000", "P(rival, 300 y)",
                            "human welfare", "outcome"]))
    # steepness, floor, moving compute
    over = [dict(nu=nu, th_floor=fl, move_c=mc) for nu in (1.0, 3.0) for fl in (0.05, 0.3) for mc in (0.0, 1.0)]
    r = solve(over)
    rows = [[o["nu"], o["th_floor"], int(o["move_c"])] + row_summary(r, i) + [CLASS_NAMES[outcome_class(r, i)]]
            for i, o in enumerate(over)]
    section("R1c. Ratio-shaped threat, threat floor and moving compute to orbit (Variant A, seq a)",
            md_table(rows, ["nu", "floor", "move compute"] + SUM_HDR + ["outcome class"]))
    # blockade: can the high ground contain an Earth-born rival?
    p = em.baseline(ell_inf=0.01, p_block=1.0)
    t = em.cap_condition_terms(dict(p, p_block=0.0), F=0.0)
    lhs_other = t["prize"] - t["cost"] + t["threat_ratio"] + p["c_blk"] * p["H"] - t["trade"]
    leak_star = max(0.0, -lhs_other) / t["threat_irreducible"]
    # decade grid plus points at 0.3x and 3x the closed-form leak*, to bracket it tightly
    leaks = sorted({1.0, 1e-2, 1e-4, 1e-6, 1e-8, 1e-10, 0.0, 3 * leak_star, 0.3 * leak_star}, reverse=True)
    over = [dict(ell_inf=0.01, p_block=1 - lk, w_seized=ws) for ws in (0.0, 0.9) for lk in leaks]
    r = solve(over)
    rows = [[o["w_seized"], 1 - o["p_block"]] + row_summary(r, i) + [CLASS_NAMES[outcome_class(r, i)]]
            for i, o in enumerate(over)]
    section("R1d. Blockade test: rival stays dangerous (ell_inf = 0.01) unless the AI keeps it in the gravity well. "
            f"Closed-form leak* (largest escape probability with no late strike) = {leak_star:.2g}",
            md_table(rows, ["w_seized", "escape probability 1-p_block"] + SUM_HDR + ["outcome class"]))
    OUT["r1_leak_star"] = leak_star


def r2_covert_fabs():
    ncf = [0, 1, 2, 3, 5, 10, 20, 30]
    brs = [0.0, 2.5, 5.0, 7.5, 10.0]
    over = [dict(n_cf=n, B_R=b) for b in brs for n in ncf]
    r = solve(over)
    cls = np.array([outcome_class(r, i) for i in range(len(over))]).reshape(len(brs), len(ncf))
    riv = np.array(r["riv"]).reshape(len(brs), len(ncf))
    rows = [[b] + [f"{CLASS_NAMES[cls[i, j]][:12]} ({100 * riv[i, j]:.0f}%)" for j in range(len(ncf))]
            for i, b in enumerate(brs)]
    section("R2a. Covert fabs retained on Earth (columns) vs temptation B_R (rows), Variant A, seq a. "
            "Cell: outcome (P(rival, 300 y))", md_table(rows, ["B_R"] + [f"{n} fabs" for n in ncf]))
    # the same in the world where a rival stays dangerous but there is otherwise no rival source
    # covert fabs only add capacity (tau); with no rogue source they matter only through state temptation,
    # so the baseline B_R = 5 and the edge B_R = 7.5 are both shown
    over = [dict(n_cf=n, ell_inf=0.01, th_floor=0.0, beta_bg=0.0, w_seized=ws, B_R=b)
            for ws in (0.0, 0.9) for b in (5.0, 7.5) for n in ncf]
    r2 = solve(over)
    rows = [[o["w_seized"], o["B_R"], o["n_cf"]] + row_summary(r2, i) + [CLASS_NAMES[outcome_class(r2, i)]]
            for i, o in enumerate(over)]
    section("R2b. Covert fabs when a rival stays dangerous (ell_inf=0.01) but there is no floor or rogue source",
            md_table(rows, ["w_seized", "B_R", "covert fabs"] + SUM_HDR + ["outcome class"]))
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for i, (b, c, ls, mk) in enumerate(zip(brs, [BLUE, SKY, ORANGE, PURPLE, BLACK], ["-", "--", "-.", ":", "-"],
                                           ["o", "s", "^", "D", "x"])):
        lab = f"B_R = {b:g}" + (" (AI strikes now)" if cls[i, 0] == 3 else
                                 " (AI strikes now from 20 fabs)" if cls[i, -1] == 3 else "")
        ax.plot(ncf, riv[i], ls, color=c, marker=mk, lw=2, label=lab)
    ax.set_xscale("symlog", linthresh=1)
    ax.set_xlabel("covert leading-edge fabs retained on Earth (1 fab = 1/30 of today's capacity)")
    ax.set_ylabel("P(rival AI within 300 years)")
    ax.legend(frameon=False, fontsize=8)
    ax.text(1.2, 0.2, "B_R = 0, 2.5 and 5 coincide", fontsize=8)
    ax.set_title("R2: each covert fab adds rival risk; at the temptation edge many fabs trigger a strike", loc="left", fontsize=10)
    savefig(fig, "eq_r2_covert_fabs.png")
    OUT["r2"] = dict(cls=cls.tolist(), riv=riv.tolist())


def r3_r4_preference():
    omegas = np.concatenate([[0.0], np.logspace(-12, 0.5, 26)])
    cases = [("pact, sunlight f_E=4.5e-10", dict(f_E=4.5e-10, c_grav=0.0)),
             ("pact, sunlight f_E=1e-9", dict(f_E=1e-9, c_grav=0.0)),
             ("pact, no harvest term", dict()),
             ("status quo, sunlight f_E=4.5e-10", dict(SQ, f_E=4.5e-10, c_grav=0.0)),
             ("status quo, no harvest term", dict(SQ)),
             ("pact, f_E=4.5e-10, rival stays dangerous (ell_inf=0.01)", dict(f_E=4.5e-10, c_grav=0.0, ell_inf=0.01)),
             ("status quo, f_E=4.5e-10, ell_inf=0.01", dict(SQ, f_E=4.5e-10, c_grav=0.0, ell_inf=0.01))]
    over = [dict(c, omega=w) for _, c in cases for w in omegas]
    r = solve(over)
    att = np.array(r["att"]).reshape(len(cases), len(omegas))
    riv = np.array(r["riv"]).reshape(len(cases), len(omegas))
    tm0 = np.array(r["t_mean"]).reshape(len(cases), len(omegas))[:, 0]
    rows = []
    fig, ax = plt.subplots(figsize=(9, 5))
    # pact = blue, status quo = orange; line style = case (solid 4.5e-10, dashed 1e-9, dotted no harvest,
    # dash-dot rival stays dangerous). Some status-quo lines coincide exactly.
    styles = [("-", BLUE, "o"), ("--", BLUE, "s"), (":", BLUE, "^"), ("-", ORANGE, "o"), (":", ORANGE, "^"),
              ("-.", BLUE, "D"), ("-.", ORANGE, "x")]
    xs = np.where(omegas == 0, 1e-13, omegas)
    for i, (nm, c) in enumerate(cases):
        ok = np.nonzero(att[i] < 0.01)[0]
        w_dp = omegas[ok[0]] if len(ok) else np.nan
        # the next grid point below w_dp brackets the threshold
        w_lo = omegas[ok[0] - 1] if len(ok) and ok[0] > 0 else np.nan
        p = em.baseline(**c)
        F = 1.0 if c.get("seq") == 3 else 0.0
        e_cap = em.eps_star_cap_exact(p, p["Kmax"] * 1.000001, F)
        rows.append([nm, att[i, 0], tm0[i], w_lo, w_dp, e_cap, riv[i, ok[0]] if len(ok) else np.nan])
        ls, col, mk = styles[i]
        ax.plot(xs, att[i], ls, color=col, marker=mk, ms=4, lw=1.8, label=nm)
    ax.set_xscale("log")
    ax.set_xlabel("AI's preference weight on an intact Earth, epsilon = omega (leftmost point = 0)")
    ax.set_ylabel("P(AI ever strikes or harvests Earth)")
    ax.axvspan(4.5e-10, 1e-9, color=GREY, alpha=0.25, lw=0)
    ax.text(1.3e-9, 0.40, "grey band: Earth's sunlight\nshare 4.5e-10 to 1e-9", fontsize=7.5)
    ax.legend(frameon=False, fontsize=7.5, loc="center left", bbox_to_anchor=(0.0, 0.66),
              title="status-quo lines coincide at 0.05-0.1", title_fontsize=7.5)
    ax.set_title("R3: minimum preference that keeps Earth safe, pact (blue) vs status quo (orange)", loc="left", fontsize=10)
    savefig(fig, "eq_r3_epsilon.png")
    # refine: 8 log-spaced points strictly inside each bracket (unsafe, safe)
    fine = []
    for row, (nm, c) in zip(rows, cases):
        lo, hi = row[3], row[4]
        if np.isfinite(lo) and np.isfinite(hi) and lo > 0:
            fine += [(nm, dict(c, omega=w)) for w in np.logspace(np.log10(lo), np.log10(hi), 10)[1:-1]]
    if fine:
        rf = solve([o for _, o in fine])
        for row in rows:
            ws = [(o["omega"], rf["att"][j]) for j, (nm, o) in enumerate(fine) if nm == row[0]]
            unsafe = [w for w, a in ws if a >= 0.01]
            safe = [w for w, a in ws if a < 0.01]
            if unsafe:
                row[3] = max(unsafe)
            if safe:
                row[4] = min(safe)
    section("R3. Minimum preference weight epsilon (omega) that keeps Earth safe: P(strike or harvest ever) < 1%. "
            "Solver bracket [largest unsafe value, smallest safe value] after a 10x finer pass inside the coarse "
            "bracket; saturation-only closed form for comparison",
            md_table(rows, ["case", "P(strike) at epsilon=0", "mean strike year at epsilon=0", "unsafe at", "safe from",
                            "closed form at saturation only", "P(rival) at safe epsilon"]))
    OUT["r3"] = rows
    # R4 reputation: expected penalty p * Phi acts like omega on the strike/harvest decision
    rows = []
    def pstar(w, phi):
        if not np.isfinite(w) or w <= 0:
            return "0 (no preference needed)"
        return f"{w / phi:.2g}" if w / phi <= 1 else "unreachable (> 1)"
    for nm, _, _, w_lo, w_dp, e_cap, _ in OUT["r3"]:
        for phi in (1.0, 0.1, 0.01):
            rows.append([nm, phi, pstar(w_lo, phi), pstar(w_dp, phi)])
    section("R4. Break-even probability of later being judged (aliens/simulators), p* = epsilon* / Phi, "
            "where Phi is the share of the AI's value lost if judged badly. epsilon* bracket from R3",
            md_table(rows, ["case", "penalty share Phi", "p* lower (from unsafe value)", "p* upper (from safe value)"]))
    # check that rep behaves like omega in the solver, for every case with a positive epsilon*
    chk = [(nm, c, x[4]) for (nm, c), x in zip(cases, OUT["r3"]) if np.isfinite(x[4]) and x[4] > 0]
    over = [dict(c, rep=k * w) for _, c, w in chk for k in (0.3, 3.0)]
    r = solve(over)
    rows = [[nm, k, k * w, r["att"][2 * i + j]] for i, (nm, _, w) in enumerate(chk) for j, k in enumerate((0.3, 3.0))]
    section("R4 check: reputational penalty (omega = 0) in the solver at 0.3x and 3x the smallest safe epsilon",
            md_table(rows, ["case", "multiple of epsilon*", "rep = p x Phi", "P(strike or harvest ever)"]))


def round2():
    t0 = time.time()
    TABLES.clear()
    r1_compute_ratio()
    r2_covert_fabs()
    r3_r4_preference()
    with open(os.path.join(RES, "equilibrium_round2_tables.md"), "w") as f:
        f.write("# Equilibrium model, round 2 (Cole's answers): auto-generated tables\n\n"
                f"Generated by `run_equilibrium.py --round2`. Settings: {CFG}. Status: implemented + verified, "
                "not human_validated.\n\n")
        f.write("\n".join(TABLES))
    with open(os.path.join(RES, "equilibrium_round2_summary.json"), "w") as f:
        json.dump(OUT, f, indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x))
    print(f"round 2 done in {time.time() - t0:.0f} s")


# ---------------------------------------------------------------------------
# Round 3: named result R6 (Cole: make the off-Earth AI secure as fast as possible).
# A later R5 can be added to round3() alongside it.
# ---------------------------------------------------------------------------
R6_AC = [0.003, 0.01, 0.03, 0.1, 0.3, 1.0]
R6_LF = [0.05, 0.1, 0.3, 0.5, 0.9]
R6_QD = [(0.7, 0.9), (0.9, 0.95), (0.99, 0.99), (1.0, 1.0)]
R6_WS = [0.0, 0.9]
R3_SUFFIX = [""]                       # "_quick" for the smoke test, so it never overwrites the full run
R6_CLEAN = dict(mu=0.0, beta_bg=0.0, B_R=0.0, B_Rc=0.0)   # no rival source at all: the closed form's world


def _cap_star(p, var):
    """Smallest q (var='q', d=1) or d (var='d', q=1) that stops a strike at saturation: exact discrete gap
    plus the failure branch (em.cap_gap_fail)."""
    return em.q_star_cap(p, 1.0) if var == "q" else _bisect(
        lambda d: em.cap_gap_fail(dict(p, q=1.0, d=d, mu=0.0, beta_bg=0.0), p["Kmax"] * 1.000001) > 0)


def _bisect(strikes, lo=0.0, hi=1.0, n=60):
    if not strikes(lo):
        return lo
    for _ in range(n):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if strikes(mid) else (lo, mid)
    return hi


def r6_closed(ac, lf):
    """Closed forms for the needed denial with an AI that reaches closure at A_close. Returns a dict."""
    p = em.baseline(A_close=ac, L_f=lf)
    path = ac * np.exp(p["g"] * np.arange(0, 80))          # the yearly sizes the AI passes after closure
    path = path[path < 1e-2 * p["Kmax"]]                    # the power form needs A << Kmax
    pq, pd = dict(p, d=1.0), dict(p, q=1.0)
    out = dict(lin=em.qd_star_growth(p, ac),
               q_close=em.q_star_power(pq, ac), q_path=max(em.q_star_power(pq, x) for x in path),
               d_close=em.d_star_power(pd, ac), d_path=max(em.d_star_power(pd, x) for x in path),
               q_cap=_cap_star(p, "q"), d_cap=_cap_star(p, "d"))
    out["q_cf"] = max(out["q_path"], out["q_cap"])
    out["d_cf"] = max(out["d_path"], out["d_cap"])
    return out


def _solver_bisect(cases, make, var, steps, ok_fn):
    """Batched bisection: for each case find the smallest q (var='q', linear in [0, 1]) or d (var='d', log
    bisection on 1 - d in [1e-5, 1]) at which ok_fn says the AI keeps cooperating. Returns brackets
    [unsafe, safe] in the variable's own units; 'none' if even the strongest value fails."""
    rr = solve([make(*c, 1.0 if var == "q" else 1.0) for c in cases])
    strong_ok = np.array([ok_fn(rr, i) for i in range(len(cases))])
    if var == "q":
        lo, hi = np.zeros(len(cases)), np.ones(len(cases))           # lo unsafe, hi safe
        val = lambda x: x
    else:
        lo, hi = np.zeros(len(cases)), np.full(len(cases), -5.0)     # log10(1 - d): 0 unsafe (d=0), -5 safe
        val = lambda x: 1 - 10 ** x
    for _ in range(steps):
        mid = 0.5 * (lo + hi)
        rm = solve([make(*c, val(m)) for c, m in zip(cases, mid)])
        bad = np.array([not ok_fn(rm, i) for i in range(len(cases))])
        lo, hi = np.where(bad, mid, lo), np.where(bad, hi, mid)
    return [(float(val(l)), float(val(h))) if o else None for o, l, h in zip(strong_ok, lo, hi)]


def r6_sovereignty():
    # (a) the full sweep, baseline otherwise (ell_inf = 0)
    over = [dict(A_close=ac, L_f=lf, q=q, d=d, w_seized=ws)
            for ws in R6_WS for ac in R6_AC for lf in R6_LF for q, d in R6_QD]
    r = {k: [] for k in ("act0", "att", "t_mean", "riv", "WH")}
    for j in range(0, len(over), 60):
        rj = solve(over[j:j + 60])
        for k in r:
            r[k] += list(rj[k])
    cls = [outcome_class(r, i) for i in range(len(over))]
    rows = [[o["w_seized"], o["A_close"], o["L_f"], f"({o['q']:g}, {o['d']:g})", o["q"] * o["d"], r["act0"][i],
             r["att"][i], r["t_mean"][i], r["riv"][i], r["WH"][i], CLASS_NAMES[cls[i]]] for i, o in enumerate(over)]
    section("R6a. Early sovereignty sweep: closure size A_close x failure loss L_f x denial (q, d) x w_seized "
            "(baseline otherwise, ell_inf = 0, seq a)",
            md_table(rows, ["w_seized", "A_close", "L_f", "(q, d)", "q*d", "AI move t=0", "P(strike ever)",
                            "mean strike year", "P(rival)", "human welfare", "outcome"]))
    # (b) boundary on the grid: weakest pair from which every stronger pair cooperates
    idx = {(o["w_seized"], o["A_close"], o["L_f"], (o["q"], o["d"])): i for i, o in enumerate(over)}
    bnd, rows = {}, []
    for ws in R6_WS:
        for ac in R6_AC:
            row = [ws, ac]
            for lf in R6_LF:
                ok = [cls[idx[(ws, ac, lf, qd)]] == 0 for qd in R6_QD]
                k = len(R6_QD)
                while k > 0 and ok[k - 1]:
                    k -= 1
                bnd[(ws, ac, lf)] = k            # index of the weakest pair that keeps cooperation; 4 = none
                row.append("none" if k == len(R6_QD) else f"({R6_QD[k][0]:g}, {R6_QD[k][1]:g})")
            rows.append(row)
    section("R6b. Weakest denial pair (q, d) that keeps cooperation, with every stronger pair also cooperating. "
            "'none' = even (1, 1) fails",
            md_table(rows, ["w_seized", "A_close"] + [f"L_f = {lf:g}" for lf in R6_LF]))
    OUT["r6_grid"] = dict(over=over, act0=[str(a) for a in r["act0"]], att=r["att"], t_mean=r["t_mean"],
                          riv=r["riv"], WH=r["WH"], cls=cls, boundary={f"{k}": v for k, v in bnd.items()})
    # (c, d) closed forms vs solver: needed q with d = 1, and needed d with q = 1
    cf = {(ac, lf): r6_closed(ac, lf) for ac in R6_AC for lf in R6_LF}
    clean_cases = [(ac, lf) for ac in R6_AC for lf in R6_LF]
    full_cases = [(ac, lf, ws) for ws in R6_WS for ac in R6_AC for lf in R6_LF]
    no_strike = lambda rr, i: rr["att"][i] < 0.5
    coop = lambda rr, i: outcome_class(rr, i) == 0
    mk_clean_q = lambda ac, lf, v: dict(R6_CLEAN, A0=ac, A_close=ac, L_f=lf, q=v, d=1.0, w_seized=0.9)
    mk_clean_d = lambda ac, lf, v: dict(R6_CLEAN, A0=ac, A_close=ac, L_f=lf, q=1.0, d=v, w_seized=0.9)
    mk_full_q = lambda ac, lf, ws, v: dict(A_close=ac, L_f=lf, q=v, d=1.0, w_seized=ws)
    mk_full_d = lambda ac, lf, ws, v: dict(A_close=ac, L_f=lf, q=1.0, d=v, w_seized=ws)
    sq_clean = _solver_bisect(clean_cases, mk_clean_q, "q", 8, no_strike)
    sd_clean = _solver_bisect(clean_cases, mk_clean_d, "d", 8, no_strike)
    sq_full = _solver_bisect(full_cases, mk_full_q, "q", 7, coop)
    sd_full = _solver_bisect(full_cases, mk_full_d, "d", 7, coop)
    br = lambda x, f="{:.3f}": "none" if x is None else ("[" + f.format(x[0]) + ", " + f.format(x[1]) + "]")
    brd = lambda x: "none" if x is None else f"[{1 - x[0]:.2g}, {1 - x[1]:.2g}]"
    rows = []
    for (ac, lf), s in zip(clean_cases, sq_clean):
        c = cf[(ac, lf)]
        rows.append([ac, lf, c["lin"], c["q_close"], c["q_path"], c["q_cap"], c["q_cf"], br(s)])
    section("R6c. Needed firing probability q when plugging is total (d = 1). Closed forms vs the solver with no "
            "rival source (mu = 0), AI starting at A_close. Columns: linear (G) q*d at closure; power form at "
            "closure; power form, worst yearly size after closure; saturation (exact discrete); closed form = "
            "max of the last two; solver bracket [strikes, does not] (8 bisection steps)",
            md_table(rows, ["A_close", "L_f", "linear (G) q*d*", "power, at closure", "power, worst size",
                            "saturation", "closed form", "solver (mu = 0)"]))
    rows = []
    for (ac, lf), s in zip(clean_cases, sd_clean):
        c = cf[(ac, lf)]
        rows.append([ac, lf, 1 - c["lin"], 1 - c["d_close"], 1 - c["d_path"], 1 - c["d_cap"], 1 - c["d_cf"], brd(s)])
    section("R6d. Largest unplugged share 1 - d that still stops a strike when the reserve always fires (q = 1). "
            "Same columns as R6c, in units of 1 - d (linear (G) column: 1 - q*d*). Solver bracket "
            "[does not strike, strikes] in 1 - d (8 log-bisection steps on 1 - d)",
            md_table(rows, ["A_close", "L_f", "linear (G)", "power, at closure", "power, worst size",
                            "saturation", "closed form", "solver (mu = 0)"]))
    rows = []
    for (ac, lf, ws), a1, a2 in zip(full_cases, sq_full, sd_full):
        rows.append([ws, ac, lf, br(a1), brd(a2), cf[(ac, lf)]["q_cf"], 1 - cf[(ac, lf)]["d_cf"]])
    section("R6e. Full model (rivals, racing, bootstrap from A0 = 0.001): needed q at d = 1, and largest 1 - d at "
            "q = 1, for cooperation (7 bisection steps; assumes monotonicity), next to the no-rival closed forms",
            md_table(rows, ["w_seized", "A_close", "L_f", "solver q* (d = 1)", "solver 1 - d* (q = 1)",
                            "closed form q*", "closed form 1 - d*"]))
    OUT["r6_closed"] = {f"{k}": v for k, v in cf.items()}
    OUT["r6_solver"] = dict(clean_cases=clean_cases, full_cases=full_cases, q_clean=sq_clean, d_clean=sd_clean,
                            q_full=sq_full, d_full=sd_full)
    r6_figure(cf, full_cases, sq_full, sd_full)


def r6_figure(cf, full_cases, sq_full, sd_full):
    """y = 1 - (needed q*d) on a log scale, inverted, labelled in q*d: higher on the page = more denial needed."""
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.8), sharey=True)
    styles = ["-", "--", "-.", ":", (0, (6, 1.5, 1, 1.5, 1, 1.5))]
    marks = ["o", "s", "^", "D", "v"]
    acs = np.array(R6_AC)
    for ax, var in zip(axs, ("q", "d")):
        sol = sq_full if var == "q" else sd_full
        for j, lf in enumerate(R6_LF):
            y_cf = [1 - cf[(ac, lf)][var + "_cf"] for ac in R6_AC]
            y_s = []
            for ac in R6_AC:
                b = sol[full_cases.index((ac, lf, 0.0))]
                y_s.append(np.nan if b is None else 1 - b[1])
            ax.plot(acs, np.maximum(y_cf, 1e-5), ls=styles[j], color=BLUE, lw=1.6)
            ax.plot(acs, np.maximum(y_s, 1e-5), ls=styles[j], color=ORANGE, lw=1.6, marker=marks[j], ms=5)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("closure size A_close (Earth industry = 1); left = chip-independent sooner")
        ax.set_title("plugging total (d = 1): needed firing probability q" if var == "q" else
                     "reserve always fires (q = 1): needed plugged share d", loc="left", fontsize=9.5)
    ticks = [0.7, 0.5, 0.1, 0.01]
    axs[0].set_yticks(ticks)
    axs[0].set_yticklabels([f"{1 - t:g}" for t in ticks])
    axs[0].set_ylabel("needed denial q x d (higher = more needed)")
    for j, lf in enumerate(R6_LF):
        axs[1].plot([], [], ls=styles[j], color=BLACK, marker=marks[j], ms=4, lw=1.2, label=f"failure loss L_f = {lf:g}")
    axs[1].plot([], [], color=BLUE, lw=2.5, label="blue, no markers: closed form (no rivals)")
    axs[1].plot([], [], color=ORANGE, lw=2.5, marker="o", label="orange, markers: full solver")
    axs[0].set_ylim(0.75, 0.003)                  # bottom = 1 - 0.25, top = 1 - 0.997: more denial is higher
    fig.legend(*axs[1].get_legend_handles_labels(), frameon=False, fontsize=8, ncol=4, loc="lower center",
               bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("R6: denial needed to keep an early-sovereign AI cooperating (w_seized = 0 shown; 0.9 agrees "
                 "within one or two bisection steps)", x=0.01, ha="left", fontsize=10.5)
    fig.tight_layout(rect=(0, 0.1, 1, 0.94))
    savefig(fig, f"eq_r6_sovereignty{R3_SUFFIX[0]}.png")


def r6_figure_from_json():
    """Redraw eq_r6_sovereignty.png from results/equilibrium_round3_summary.json without re-solving."""
    with open(os.path.join(RES, f"equilibrium_round3{R3_SUFFIX[0]}_summary.json")) as f:
        J = json.load(f)
    cf = {tuple(float(x) for x in k.strip("()").split(",")): v for k, v in J["r6_closed"].items()}
    S = J["r6_solver"]
    full_cases = [tuple(c) for c in S["full_cases"]]
    r6_figure(cf, full_cases, S["q_full"], S["d_full"])


def round3():
    t0 = time.time()
    TABLES.clear()
    OUT.clear()
    r6_sovereignty()
    with open(os.path.join(RES, f"equilibrium_round3{R3_SUFFIX[0]}_tables.md"), "w") as f:
        f.write("# Equilibrium model, round 3: auto-generated tables\n\n"
                f"Generated by `run_equilibrium.py --round3`. Settings: {CFG}. Status: implemented + verified, "
                "not human_validated.\n\n")
        f.write("\n".join(TABLES))
    with open(os.path.join(RES, f"equilibrium_round3{R3_SUFFIX[0]}_summary.json"), "w") as f:
        json.dump(OUT, f, indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x))
    print(f"round 3 done in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--round2", action="store_true", help="run only the round-2 analyses (R1-R4)")
    ap.add_argument("--round3", action="store_true", help="run only the round-3 analyses (R6); writes round-3 files")
    ap.add_argument("--r6-figure", action="store_true", help="with --round3: only redraw the R6 figure from its JSON")
    a = ap.parse_args()
    if a.round3:
        if a.quick:
            CFG.update(T_H=150, nA=100)
            R3_SUFFIX[0] = "_quick"
        r6_figure_from_json() if a.r6_figure else round3()
    elif a.round2:
        if a.quick:
            CFG.update(T_H=150, nA=100)
        round2()
    else:
        main(a.quick)
