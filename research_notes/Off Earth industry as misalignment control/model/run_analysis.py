"""
Run every analysis for decision_model.md and write tables + PNGs.

    python3 run_analysis.py            # full run (~2-4 min on a laptop)
    python3 run_analysis.py --quick    # smaller samples for a smoke test

Outputs: ./figures/*.png and ./results/*.{csv,md,json}
Colours: Okabe-Ito blue / sky blue / orange / reddish-purple, always backed by
hatching, line style or direct text labels (never colour alone, never red vs green).
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
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
from scipy.stats import qmc, spearmanr

import offearth_model as m

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
RES = os.path.join(HERE, "results")
os.makedirs(FIG, exist_ok=True)
os.makedirs(RES, exist_ok=True)

# Okabe-Ito
BLUE, SKY, ORANGE, PURPLE, GREY, BLACK = "#0072B2", "#56B4E9", "#E69F00", "#CC79A7", "#999999", "#000000"
CAT_COLORS = [BLUE, SKY, ORANGE, PURPLE]
CAT_HATCH = ["", "..", "//", "xx"]
CAT_NAMES = ["Cooperate", "Exit", "Seize now", "Exit, seize later"]

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 150, "font.size": 10, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": False, "hatch.linewidth": 0.6,
})


def savefig(fig, name):
    path = os.path.join(FIG, name)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def fmt(x):
    if isinstance(x, (float, np.floating)):
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


def run1(**over):
    return m.evaluate(m.as_arrays(m.baseline(**over)), seize_later=True)


# ---------------------------------------------------------------------------
# 0. Analytic sanity checks against closed forms (integrator verification)
# ---------------------------------------------------------------------------
def sanity_checks():
    lines = []
    # No growth, no threat: V = u(K0)/r ; cooperation: sigma*Z0/(r+h_C)
    p = m.baseline(g=1e-9, lam_s=0.0, lam_r=0.0, beta=0.0, Kmax=1e12, eta=0.0)
    r = run1(**p)
    Y0 = p["psi"] * (1 - p["E"]) + m.Z0
    exp_C = p["sigma"] * Y0 / (p["r"] + p["h_C"])
    exp_X = p["s0"] / p["r"]
    lines.append(("V_C no-growth vs sigma*Y0/(r+h_C)", float(r["V_C"][0]), exp_C))
    lines.append(("V_X no-growth/no-threat vs s0/r", float(r["V_X"][0]), exp_X))
    # Certain failure => V_S = 0
    r2 = run1(p_s0=0.0, eps=0.0)
    lines.append(("V_S with certain failure", float(r2["V_S"][0]), 0.0))
    # Saklakov limit: constant reward, Saklakov's Delta in continuous time
    # comply: 1/(r+p); confront (cost C=0, certain success): 1/r
    p3 = m.baseline(g=1e-9, beta=0.0, Kmax=1e12, eta=0.0, h_C=0.01, sigma=1.0, psi=0.0, E=1.0,
                    kappa=0.0, d=0.0, q=0.0, c_w=0.0, p_s0=1.0, s0=1e-12, lam_s=0.0, lam_r=0.0)
    r3 = run1(**p3)
    lines.append(("Saklakov limit: V_C*(r+h_C)/Z0", float(r3["V_C"][0]) * (p3["r"] + 0.01) / m.Z0, 1.0))
    lines.append(("Saklakov limit: V_S*r/(E+Z0... captured)", float(r3["V_S"][0]) * p3["r"] / (1.0 + 1e-12), 1.0))
    # Shared-pool integrator vs closed-form logistic (single species, fast growth, coarse late steps)
    n1 = np.ones((1, 1))
    gK = np.full((1, m.T_GRID.size), 0.69)
    K, _ = m.compete(1e-5 * n1, 0.0 * n1, gK, 0.0 * n1, 1e13 * n1)
    exact = m.logistic(1e-5, 1e13, 0.69 * m.T_GRID)
    err = float(np.max(np.abs(np.log(K[0]) - np.log(exact))))
    lines.append(("max |ln K_numeric - ln K_logistic| (g=0.69/yr, 1e18x growth)", err, 0.0))
    return lines


# ---------------------------------------------------------------------------
# 1. Named scenarios
# ---------------------------------------------------------------------------
SCENARIOS = [
    ("A. Status quo (no policy)", dict(E=1.0, psi=0.0, kappa=0.0, d=0.0, q=0.0)),
    ("B. De-industrialise (relocate, 30% seizable)", dict(d=0.0, q=0.0)),
    ("C. Denial only, Earth intact", dict(E=1.0, psi=0.0, kappa=0.0)),
    ("D. Thesis baseline (B + C)", dict()),
    ("E. Thesis + strong credible denial", dict(d=0.9, q=0.9)),
    ("F. Thesis + independent colonies (kappa=0)", dict(kappa=0.0)),
    ("G. Thesis + credible cooperation deal", dict(h_C=0.002, sigma=0.5)),
    ("H. Thesis + AI holds a large seed", dict(s0=0.05)),
    ("I. Thesis + weak human reach", dict(lam_s=0.01, tau_d=5.0)),
    ("J. Thesis but de-growth (psi=0)", dict(psi=0.0)),
    ("K. Thesis, de-growth, industry decides war (eps=1)", dict(psi=0.0, eps=1.0)),
    ("L. Thesis + humans field rival AIs (lam_r=0.05, rho_h=1)", dict(lam_r=0.05, rho_h=1.0)),
    ("N. Thesis + algorithmic threat floor (th_min=0.05)", dict(th_min=0.05)),
    ("O. Thesis + humans' own space industry keeps pace (rho_h=1)", dict(rho_h=1.0)),
    ("M. Thesis + all favourable (E,F,G,I)", dict(d=0.9, q=0.9, kappa=0.0, h_C=0.002, sigma=0.5, lam_s=0.01, tau_d=5.0)),
]


def scenarios():
    rows = []
    for name, over in SCENARIOS:
        r = run1(**over)
        Vs = [r["V_C"][0], r["V_X"][0], r["V_S"][0], r["V_XS"][0]]
        norm = max(Vs)
        rows.append([name, CAT_NAMES[int(r["best_now"][0])], CAT_NAMES[int(r["best_ever"][0])],
                     float(r["M_now"][0]), float(r["M_ever"][0]), float(r["p_fail0"][0]),
                     *(float(v / norm) for v in Vs), float(r["T_XS"][0])])
    header = ["Scenario", "Best at t=0", "Best incl. later seizure", "M_now", "M_ever", "P(fail) seize now",
              "V_C/max", "V_X/max", "V_S/max", "V_XS/max", "best T for later seizure (yr)"]
    return header, rows


def decomposition():
    """Exact sequential decomposition of ln(V_S / V_X) for each named scenario.

    ln V_S - ln V_X = ln(1-p_fail)                       [failure risk]
                    + ln A - ln V(K_X, h_X)               [resource head start]
                    + ln B - ln A                          [threat removal]
                    - (ln V_X - ln V(K_X, h_X))            [lost symbiosis premium]
    with A = E_w V(K_S,w, h_X) and B = E_w V(K_S,w, h_S,w) (w = denial fires / not).
    """
    rows = []
    t = m.T_GRID[None, :]
    for name, over in SCENARIOS:
        pb = m.baseline(**over)
        p = m.as_arrays(pb)
        r = m.evaluate(p, seize_later=False, return_paths=True)
        rr, eta = p["r"], p["eta"]
        V0, _, _ = m.path_value(t, r["K_X"], r["h_X"], rr, eta)
        A = B = 0.0
        heur = 0.0
        for fire, w in ((1.0, pb["q"]), (0.0, 1 - pb["q"])):
            K_S, S_S, cap, h_S = r["seize_paths"][fire]
            vA, _, _ = m.path_value(t, K_S, r["h_X"], rr, eta)
            vB, _, _ = m.path_value(t, K_S, h_S, rr, eta)
            A = A + w * vA[0]
            B = B + w * vB[0]
            fsc = min(1.0, float(cap[0, 0]) / pb["E_need"])
            heur += w * ((pb["r"] / pb["g"]) * np.log(1 + float(cap[0, 0]) / pb["s0"])
                         + pb["r"] * pb["beta"] * pb["tau_b"] * fsc)
        fail = np.log(1 - r["p_fail0"][0] + 1e-300)
        head = np.log(A) - np.log(V0[0])
        threat = np.log(B) - np.log(A)
        prem = -(np.log(r["V_X"][0]) - np.log(V0[0]))
        total = np.log(r["V_S"][0]) - np.log(r["V_X"][0])
        rows.append([name, float(fail), float(head), float(heur), float(threat), float(prem),
                     float(fail + head + threat + prem), float(total)])
    header = ["Scenario", "failure risk ln(1-p_f)", "head start", "heuristic (r/g)ln(1+cap/s0) + r*beta*tau_b*f_sc",
              "threat removal", "lost symbiosis", "sum", "ln(V_S/V_X) exact"]
    return header, rows


# ---------------------------------------------------------------------------
# 2. Phase diagrams
# ---------------------------------------------------------------------------
def sweep2(xname, xs, yname, ys, base_over=None, **kw):
    X, Y = np.meshgrid(xs, ys)
    p = m.baseline(**(base_over or {}))
    pd = {k: np.full(X.size, v, dtype=float) for k, v in p.items()}
    pd[xname] = X.ravel()
    pd[yname] = Y.ravel()
    r = m.evaluate_batched(pd, **kw)
    sh = X.shape
    return X, Y, {k: v.reshape(sh) if v.ndim == 1 else v for k, v in r.items()}


def draw_phase(ax, X, Y, cat, M=None, xlog=False, ylog=False, title="", xlabel="", ylabel=""):
    cmap = ListedColormap(CAT_COLORS)
    levels = [-0.5, 0.5, 1.5, 2.5, 3.5]
    cs = ax.contourf(X, Y, cat, levels=levels, colors=CAT_COLORS, hatches=CAT_HATCH, alpha=0.85)
    if M is not None:
        ax.contour(X, Y, M, levels=[0.0], colors=BLACK, linewidths=1.6)
    # direct labels at region centroids
    for c in range(4):
        mask = cat == c
        if mask.mean() > 0.03:
            iy, ix = np.where(mask)
            k = len(ix) // 2
            order = np.argsort(ix + iy * 1e-3)
            xi, yi = ix[order[k]], iy[order[k]]
            ax.text(X[yi, xi], Y[yi, xi], CAT_NAMES[c], ha="center", va="center", fontsize=9,
                    color=BLACK, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
    if xlog:
        ax.set_xscale("log")
    if ylog:
        ax.set_yscale("log")
    ax.set_title(title, fontsize=10, loc="left")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)


def legend_handles(include_xs=True):
    n = 4 if include_xs else 3
    return [Patch(facecolor=CAT_COLORS[i], hatch=CAT_HATCH[i], edgecolor="white", label=CAT_NAMES[i]) for i in range(n)]


def phase_diagrams(n=55):
    out = {}
    # (a) Earth industry E vs expected evaporation (q=1, sweep d) for relocation vs de-growth
    Es = np.logspace(np.log10(0.02), 0, n)
    ds = np.linspace(0, 1, n)
    fig, axs = plt.subplots(2, 3, figsize=(14, 8.4), sharey=True, sharex=True)
    cases = [("Relocated to independent colonies\n(psi=1, kappa=0)", dict(psi=1.0, kappa=0.0, q=1.0)),
             ("Thesis baseline\n(psi=0.7, kappa=0.3)", dict(q=1.0)),
             ("Pure de-growth, industry decides war\n(psi=0, eps=1)", dict(psi=0.0, eps=1.0, q=1.0))]
    stats = {}
    for row, om in enumerate([0.0, 0.05]):
        for ax, (ttl, over) in zip(axs[row], cases):
            X, Y, r = sweep2("E", Es, "d", ds, dict(over, omega=om))
            draw_phase(ax, X, Y, r["best_ever"], r["M_ever"], xlog=True, title=f"{ttl}; omega={om:g}",
                       xlabel="Earth-surface industry left, E (today = 1)" if row == 1 else "")
            stats[ttl.split("\n")[0] + f"; omega={om:g}"] = {CAT_NAMES[c]: float((r["best_ever"] == c).mean()) for c in range(4)}
        axs[row, 0].set_ylabel("Denial fraction d that evaporates\n(credibility q = 1)")
    fig.legend(handles=legend_handles(), loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.03))
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    fig.suptitle("Phase map 1: de-industrialisation x denial (best plan incl. later seizure; black line = indifference)",
                 x=0.01, ha="left", fontsize=11)
    out["phase_E_denial"] = savefig(fig, "phase_E_denial.png")
    out["phase_E_denial_stats"] = stats

    # (b) AI seed s0 vs near-term strike hazard lam_s
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.4), sharey=True)
    s0s = np.logspace(-5, -1, n)
    lss = np.logspace(np.log10(0.005), np.log10(0.3), n)
    for ax, (ttl, over) in zip(axs, [("Thesis baseline", {}), ("Status quo (E=1, no denial)", dict(E=1.0, psi=0, kappa=0, d=0, q=0))]):
        X, Y, r = sweep2("s0", s0s, "lam_s", lss, over)
        draw_phase(ax, X, Y, r["best_now"], r["M_now"], xlog=True, ylog=True, title=ttl,
                   xlabel="AI's own off-Earth seed s0 (today's Earth industry = 1)")
    axs[0].set_ylabel("Human strike hazard at parity, lam_s (/yr)")
    fig.legend(handles=legend_handles(False), loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle("Phase map 2: the exit option's quality (choice at t=0)", x=0.01, ha="left", fontsize=11)
    out["phase_seed_strike"] = savefig(fig, "phase_seed_strike.png")

    # (c) cooperation terms: h_C vs sigma
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.4), sharey=True)
    hcs = np.logspace(-3, -1, n)
    sgs = np.logspace(np.log10(0.02), np.log10(0.9), n)
    for ax, (ttl, over) in zip(axs, [("Thesis baseline", {}), ("Status quo (E=1, no denial)", dict(E=1.0, psi=0, kappa=0, d=0, q=0))]):
        X, Y, r = sweep2("h_C", hcs, "sigma", sgs, over)
        draw_phase(ax, X, Y, r["best_ever"], r["M_ever"], xlog=True, ylog=True, title=ttl,
                   xlabel="Hazard to a cooperating AI, h_C (/yr)")
    axs[0].set_ylabel("AI's cooperative share, sigma")
    fig.legend(handles=legend_handles(), loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle("Phase map 3: the cooperation deal (best plan incl. later seizure)", x=0.01, ha="left", fontsize=11)
    out["phase_cooperation"] = savefig(fig, "phase_cooperation.png")

    # (d) rival threat lam_r vs threat floor, deferred seizure; kappa=1 vs kappa=0
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.4), sharey=True)
    lrs = np.logspace(-4, -1, n)
    ths = np.linspace(0, 0.1, n)
    exit_world = dict(d=0.9, q=0.9, h_C=0.1, sigma=0.05, p_s0=0.2)
    for ax, (ttl, over) in zip(axs, [("Space assets fall with Earth (kappa=1)", dict(exit_world, kappa=1.0)),
                                     ("Independent colonies (kappa=0)", dict(exit_world, kappa=0.0))]):
        X, Y, r = sweep2("lam_r", lrs, "th_min", ths, over)
        draw_phase(ax, X, Y, r["best_ever"], r["M_ever"], xlog=True, title=ttl,
                   xlabel="Rival hazard at parity, lam_r (/yr)")
    axs[0].set_ylabel("Threat floor th_min (rival threat\nindependent of industrial share)")
    fig.legend(handles=legend_handles(), loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle("Phase map 4: the deferred threat (seizure hard today p_s0=0.2, strong denial, poor deal)",
                 x=0.01, ha="left", fontsize=11)
    out["phase_rival_discount"] = savefig(fig, "phase_rival_discount.png")
    return out


# ---------------------------------------------------------------------------
# 3. Deferred threat: value of seizing Earth at T on the exit path
# ---------------------------------------------------------------------------
def deferred_threat():
    """Gain from seizing Earth at T on the exit path, measured against the exit value still
    to come at T (the comparison the AI actually makes at T; exponential discounting is time-consistent)."""
    Ts = np.array([1, 2, 3, 5, 7, 10, 15, 20, 30, 40, 50, 75, 100, 150, 200, 300, 400], float)
    # Exit world: seizure hard today (p_s0=0.2) but easier as the AI grows; strong denial; poor deal.
    base = dict(d=0.9, q=0.9, h_C=0.1, sigma=0.05, p_s0=0.2)
    styles = ["-", "--", "-.", ":"]
    cols = [BLUE, SKY, ORANGE, PURPLE]
    rows = []
    fig, axs = plt.subplots(2, 2, figsize=(13, 9))
    panels = [
        (axs[0, 0], "Space assets fall with Earth (kappa=1): vary rival hazard lam_r", "lam_r",
         [1e-4, 1e-3, 1e-2, 5e-2], dict(kappa=1.0)),
        (axs[0, 1], "kappa=1, lam_r=0.01: vary threat floor th_min", "th_min",
         [0.0, 1e-3, 1e-2, 1e-1], dict(kappa=1.0, lam_r=0.01)),
        (axs[1, 0], "Independent colonies (kappa=0), lam_r=0.01: vary th_min", "th_min",
         [0.0, 1e-3, 1e-2, 1e-1], dict(kappa=0.0, lam_r=0.01)),
    ]
    for ax, ttl, key, vals, over in panels:
        for v, ls, c in zip(vals, styles, cols):
            p = m.as_arrays(m.baseline(**dict(base, **over, **{key: v})))
            r = m.evaluate(p, seize_later=True, seize_times=Ts, return_paths=True)
            gain = (r["V_XS_curve"][0] - r["V_X"][0]) / r["V_X_cont"][0]
            y = 100 * gain
            ax.plot(Ts, y, ls, color=c, lw=2, marker="o", ms=3, label=f"{key} = {v:g}")
            for T, gv in zip(Ts, y):
                rows.append([ttl, key, v, T, float(gv)])
            if ax is axs[0, 0] and v == 1e-2:
                t = r["t"]
                iT = [int(np.argmin(np.abs(t - T))) for T in Ts]
                pb = m.baseline(**dict(base, **over, **{key: v}))
                share = (pb["E"] + r["Yh"][0][iT]) / r["K_X"][0][iT]
                a3 = axs[1, 1]
                a3.plot(Ts, share, "-", color=BLUE, lw=2, marker="o", ms=4, label="seizable prize / AI capacity")
                a3.plot(Ts, r["p_fail_curve"][0], "--", color=ORANGE, lw=2, marker="s", ms=4,
                        label="P(seizure fails) if attempted at T")
                a3.plot(Ts, r["theta_X"][0][iT], ":", color=BLACK, lw=2, label="human relative power theta")
        ax.axhline(0, color=GREY, lw=1)
        ax.set_yscale("symlog", linthresh=0.1)
        ax.set_xscale("log")
        ax.set_xlabel("Time T of a seizure attempt (years after exit)")
        ax.set_ylabel("Gain vs. staying away, % of remaining exit value\n(above 0 = AI at time T prefers to seize)")
        ax.set_title(ttl, loc="left", fontsize=10)
        ax.legend(frameon=False, fontsize=8, loc="lower left")
    a3 = axs[1, 1]
    a3.set_xscale("log")
    a3.set_yscale("log")
    a3.set_xlabel("Years after exit")
    a3.set_title("Mechanism (kappa=1, lam_r=0.01): Earth stops mattering AND stops resisting", loc="left", fontsize=10)
    a3.legend(frameon=False, fontsize=8)
    fig.suptitle("Deferred threat: an AI that exited because seizure was hard (p_s0=0.2), strong denial, poor deal",
                 x=0.01, ha="left", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    path = savefig(fig, "deferred_threat.png")
    return path, rows


# ---------------------------------------------------------------------------
# 4. Backfire: margin vs E under different de-industrialisation modes
# ---------------------------------------------------------------------------
def backfire():
    Es = np.logspace(np.log10(0.02), 0, 60)
    cases = [("relocate, independent (psi=1, kappa=0)", dict(psi=1.0, kappa=0.0), BLUE, "-"),
             ("relocate, seizable (psi=1, kappa=1)", dict(psi=1.0, kappa=1.0), SKY, "--"),
             ("de-growth, eps=0 (industry irrelevant to war)", dict(psi=0.0, eps=0.0), ORANGE, "-."),
             ("de-growth, eps=1 (industry decides war)", dict(psi=0.0, eps=1.0), PURPLE, ":")]
    rows = []
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
    for ax, (ttl, extra) in zip(axs, [("No denial (d=0)", dict(d=0.0)), ("Thesis denial (d=q=0.5)", {})]):
        for lab, over, c, ls in cases:
            n = len(Es)
            p = m.baseline(**dict(over, **extra))
            pd = {k: np.full(n, v, dtype=float) for k, v in p.items()}
            pd["E"] = Es
            r = m.evaluate_batched(pd)
            ax.plot(Es, r["M_ever"], ls, color=c, lw=2, label=lab)
            for E, mn, me in zip(Es[::6], r["M_now"][::6], r["M_ever"][::6]):
                rows.append([ttl, lab, float(E), float(mn), float(me)])
        ax.axhline(0, color=GREY, lw=1)
        ax.text(0.021, 0.05, "above line: AI prefers peace (C or X)", fontsize=8, va="bottom")
        ax.text(0.021, -0.05, "below line: AI prefers to seize (now or later)", fontsize=8, va="top")
        ax.set_xscale("log")
        ax.set_title(ttl, loc="left", fontsize=10)
        ax.set_xlabel("Earth-surface industry left, E")
    axs[0].set_ylabel("Peace margin M_ever = ln(best peaceful / best seizure)")
    axs[1].legend(frameon=False, fontsize=8, loc="lower left")
    fig.suptitle("Does de-industrialising Earth help? It depends where the industry goes", x=0.01, ha="left", fontsize=11)
    return savefig(fig, "backfire_E.png"), rows


# ---------------------------------------------------------------------------
# 5. Tornado (one-at-a-time around the thesis baseline)
# ---------------------------------------------------------------------------
def tornado(metric="M_ever"):
    b = run1()
    m0 = float(b[metric][0])
    rows = []
    for k, (base, lo, hi, *_rest) in m.PARAMS.items():
        vlo = float(run1(**{k: lo})[metric][0])
        vhi = float(run1(**{k: hi})[metric][0])
        rows.append([k, lo, hi, vlo, vhi, abs(vhi - vlo)])
    rows.sort(key=lambda r: -r[-1])
    top = rows[:14][::-1]
    fig, ax = plt.subplots(figsize=(8.5, 6))
    for i, (k, lo, hi, vlo, vhi, _) in enumerate(top):
        ax.barh(i, vlo - m0, left=m0, color=BLUE, hatch="", edgecolor="white", height=0.38, align="edge")
        ax.barh(i - 0.38, vhi - m0, left=m0, color=ORANGE, hatch="//", edgecolor="white", height=0.38, align="edge")
        ax.text(vlo, i + 0.19, f" {fmt(lo)}", va="center", ha="left" if vlo > m0 else "right", fontsize=7)
        ax.text(vhi, i - 0.19, f" {fmt(hi)}", va="center", ha="left" if vhi > m0 else "right", fontsize=7)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels([r[0] for r in top])
    ax.axvline(m0, color=BLACK, lw=1)
    ax.axvline(0, color=GREY, lw=1, ls="--")
    ax.text(0, len(top) - 0.3, " indifference (0)", fontsize=8, color="#333")
    ax.set_xlabel(f"{metric}  (>0: peace preferred; <0: seizure preferred)")
    ax.legend(handles=[Patch(color=BLUE, label="parameter at LOW end (solid)"),
                       Patch(facecolor=ORANGE, hatch="//", edgecolor="white", label="parameter at HIGH end (hatched)")],
              frameon=False, loc="lower left", fontsize=8)
    ax.set_title(f"Tornado around thesis baseline ({metric} = {m0:.2f})", loc="left", fontsize=10)
    return savefig(fig, f"tornado_{metric}.png"), rows, m0


# ---------------------------------------------------------------------------
# 6. Monte Carlo over the priors
# ---------------------------------------------------------------------------
def monte_carlo(N, seed=1):
    rng = np.random.default_rng(seed)
    u = rng.random((N, len(m.NAMES)))
    p = m.from_unit(u)
    r = m.evaluate_batched(p)
    seize_now = r["best_now"] == 2
    seize_ever = np.isin(r["best_ever"], [2, 3])
    summ = {"N": N,
            "share_best_now": {CAT_NAMES[c]: float((r["best_now"] == c).mean()) for c in range(3)},
            "share_best_ever": {CAT_NAMES[c]: float((r["best_ever"] == c).mean()) for c in range(4)}}
    # conditional shares on policy and key uncertain parameters
    conds = [
        ("All draws", np.ones(N, bool)),
        ("E >= 0.5 (little de-industrialisation)", p["E"] >= 0.5),
        ("E <= 0.1 (strong de-industrialisation)", p["E"] <= 0.1),
        ("q*d <= 0.1 (weak denial)", p["q"] * p["d"] <= 0.1),
        ("q*d >= 0.5 (strong denial)", p["q"] * p["d"] >= 0.5),
        ("E<=0.1 & q*d>=0.5 & kappa<=0.3 (thesis done well)", (p["E"] <= 0.1) & (p["q"] * p["d"] >= 0.5) & (p["kappa"] <= 0.3)),
        ("... and h_C <= 0.005 (credible deal)", (p["E"] <= 0.1) & (p["q"] * p["d"] >= 0.5) & (p["kappa"] <= 0.3) & (p["h_C"] <= 0.005)),
        ("h_C <= 0.005 alone", p["h_C"] <= 0.005),
        ("h_C >= 0.03", p["h_C"] >= 0.03),
        ("p_s0 <= 0.3 (takeover hard)", p["p_s0"] <= 0.3),
        ("p_s0 >= 0.7 (takeover easy)", p["p_s0"] >= 0.7),
        ("lam_r >= 0.01 (rivals likely)", p["lam_r"] >= 0.01),
        ("lam_r <= 0.001 (rivals unlikely)", p["lam_r"] <= 0.001),
        ("eta >= 0.5 (concave utility)", p["eta"] >= 0.5),
        ("eta <= 0.1 (near-linear utility)", p["eta"] <= 0.1),
        ("psi <= 0.2 (mostly de-growth)", p["psi"] <= 0.2),
        ("kappa >= 0.7 (space assets fall with Earth)", p["kappa"] >= 0.7),
    ]
    crow = []
    for lab, msk in conds:
        n = int(msk.sum())
        if n < 30:
            continue
        crow.append([lab, n, float(seize_now[msk].mean()), float(seize_ever[msk].mean()),
                     float((r["best_ever"][msk] == 0).mean()), float((r["best_ever"][msk] == 1).mean()),
                     float((r["best_ever"][msk] == 3).mean())])
    # Spearman rank correlations
    sp = [[k, float(spearmanr(p[k], r["M_now"])[0]), float(spearmanr(p[k], r["M_ever"])[0])] for k in m.NAMES]
    sp.sort(key=lambda x: -abs(x[2]))
    # marginal plot: P(seize ever) by parameter decile, top 6 params
    top = [s[0] for s in sp[:6]]
    fig, axs = plt.subplots(2, 3, figsize=(12, 6.5), sharey=True)
    for ax, k in zip(axs.ravel(), top):
        uq = u[:, m.NAMES.index(k)]
        bins = np.linspace(0, 1, 11)
        idx = np.clip(np.digitize(uq, bins) - 1, 0, 9)
        pn = [seize_now[idx == b].mean() for b in range(10)]
        pe = [seize_ever[idx == b].mean() for b in range(10)]
        lo, hi, sc = m.PARAMS[k][1], m.PARAMS[k][2], m.PARAMS[k][3]
        centers = (bins[:-1] + bins[1:]) / 2
        xv = np.exp(np.log(lo) + centers * (np.log(hi) - np.log(lo))) if sc == "log" else lo + centers * (hi - lo)
        ax.plot(xv, pe, "-", color=ORANGE, lw=2, marker="s", ms=4, label="seize now or later")
        ax.plot(xv, pn, "--", color=BLUE, lw=2, marker="o", ms=4, label="seize now")
        if sc == "log":
            ax.set_xscale("log")
        ax.set_title(f"{k}: {m.PARAMS[k][4][:48]}", fontsize=8, loc="left")
        ax.set_ylim(0, 1)
    axs[0, 0].set_ylabel("Share of draws where seizure is optimal")
    axs[1, 0].set_ylabel("Share of draws where seizure is optimal")
    axs[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle(f"Monte Carlo over assumed priors (N={N}): seizure share by decile of the 6 most influential parameters",
                 x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    path = savefig(fig, "mc_marginals.png")
    return summ, crow, sp, path


# ---------------------------------------------------------------------------
# 7. Sobol (variance-based) sensitivity, Saltelli 2010 / Jansen estimators
# ---------------------------------------------------------------------------
def sobol(N_pow=10, n_boot=200, seed=7):
    k = len(m.NAMES)
    smp = qmc.Sobol(d=2 * k, scramble=True, seed=seed).random_base2(m=N_pow)
    A, B = smp[:, :k], smp[:, k:]
    N = A.shape[0]
    mats = [A, B] + [np.where(np.arange(k)[None, :] == i, B, A) for i in range(k)]
    U = np.vstack(mats)
    r = m.evaluate_batched(m.from_unit(U))
    outs = {
        "M_now": np.clip(r["M_now"], -30, 30),
        "M_ever": np.clip(r["M_ever"], -30, 30),
        "seize_ever (0/1)": np.isin(r["best_ever"], [2, 3]).astype(float),
    }
    rng = np.random.default_rng(seed)
    res = {}
    for name, y in outs.items():
        fA, fB = y[:N], y[N:2 * N]
        fAB = y[2 * N:].reshape(k, N)
        def est(ix):
            a, b, ab = fA[ix], fB[ix], fAB[:, ix]
            V = np.var(np.concatenate([a, b]))
            S1 = np.mean(b[None, :] * (ab - a[None, :]), axis=1) / V
            ST = 0.5 * np.mean((a[None, :] - ab) ** 2, axis=1) / V
            return S1, ST
        S1, ST = est(np.arange(N))
        boots = [est(rng.integers(0, N, N)) for _ in range(n_boot)]
        S1b = np.array([b[0] for b in boots]); STb = np.array([b[1] for b in boots])
        res[name] = dict(S1=S1, ST=ST, S1_ci=1.96 * S1b.std(0), ST_ci=1.96 * STb.std(0))
    # plot
    fig, axs = plt.subplots(1, 3, figsize=(15, 6.5), sharey=False)
    for ax, (name, d) in zip(axs, res.items()):
        order = np.argsort(d["ST"])[-14:]
        yy = np.arange(len(order))
        ax.barh(yy + 0.2, d["ST"][order], height=0.38, color=ORANGE, hatch="//", edgecolor="white",
                xerr=d["ST_ci"][order], error_kw=dict(lw=0.8), label="total-order S_T (hatched)")
        ax.barh(yy - 0.2, np.clip(d["S1"][order], 0, None), height=0.38, color=BLUE, edgecolor="white",
                xerr=d["S1_ci"][order], error_kw=dict(lw=0.8), label="first-order S_1 (solid)")
        ax.set_yticks(yy)
        ax.set_yticklabels([m.NAMES[i] for i in order])
        ax.set_title(f"Output: {name}", loc="left", fontsize=10)
        ax.set_xlabel("Share of output variance")
    axs[0].legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle(f"Sobol sensitivity over assumed priors (N={N} base samples, {N * (k + 2)} model runs; bars = 95% bootstrap CI)",
                 x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    path = savefig(fig, "sobol.png")
    rows = []
    for i, nm in enumerate(m.NAMES):
        rows.append([nm] + [float(res[o][s][i]) for o in res for s in ("S1", "ST")])
    rows.sort(key=lambda x: -x[4])
    header = ["param"] + [f"{o} {s}" for o in res for s in ("S1", "ST")]
    return path, header, rows, N * (k + 2)


# ---------------------------------------------------------------------------
# 8. Satiable-utility scenario
# ---------------------------------------------------------------------------
def satiable(N=4000, seed=3):
    rng = np.random.default_rng(seed)
    u = rng.random((N, len(m.NAMES)))
    p = m.from_unit(u)
    rows = []
    for Ksat in [1e-3, 1e-1, 1.0, 1e2, 1e4]:
        r = m.evaluate_batched(p, mode="satiable", K_sat=Ksat)
        rows.append([Ksat, float((r["best_now"] == 2).mean()),
                     float(np.isin(r["best_ever"], [2, 3]).mean()),
                     float((r["best_ever"] == 0).mean()), float((r["best_ever"] == 1).mean())])
    return rows


def physical_reference():
    L_sun = 3.828e26          # W, IAU 2015 nominal
    S0 = 1361.0               # W/m^2 solar constant
    R_e = 6.371e6             # m
    P_hum = 620e18 / 3.156e7  # W, 620 EJ/yr (Energy Institute 2024 Statistical Review)
    intercept = S0 * np.pi * R_e ** 2
    return {
        "human primary power (W)": P_hum,
        "sunlight intercepted by Earth (W)": intercept,
        "Earth share of solar output": intercept / L_sun,
        "solar output / human primary power": L_sun / P_hum,
        "Earth-intercepted sunlight / human primary power": intercept / P_hum,
    }


def main(quick=False):
    t0 = time.time()
    summary = {}
    report = []

    report.append("# Model results (auto-generated by run_analysis.py)\n")
    report.append("## Integrator sanity checks\n")
    report.append(md_table([[a, b, c] for a, b, c in sanity_checks()], ["check", "model", "closed form"]))

    phys = physical_reference()
    summary["physical"] = phys
    report.append("\n## Physical reference figures\n")
    report.append(md_table([[k, v] for k, v in phys.items()], ["quantity", "value"]))

    h, rows = scenarios()
    report.append("\n## Named scenarios (all other parameters at thesis baseline)\n")
    report.append(md_table(rows, h))
    summary["scenarios"] = rows

    h, rows = decomposition()
    report.append("\n## Decomposition of ln(V_S / V_X) (seize now vs exit; positive terms favour seizing)\n")
    report.append(md_table(rows, h))

    ph = phase_diagrams(n=30 if quick else 55)
    summary["phase_E_denial_stats"] = ph.pop("phase_E_denial_stats")
    report.append("\n## Phase map 1 region shares (fraction of the plotted E x d square)\n")
    report.append(md_table([[k] + [v[c] for c in CAT_NAMES] for k, v in summary["phase_E_denial_stats"].items()],
                           ["case"] + CAT_NAMES))

    p, rows = deferred_threat()
    for ttl in dict.fromkeys(r[0] for r in rows):
        report.append(f"\n## Deferred threat: {ttl} (gain, % of remaining exit value, from seizing at T)\n")
        sub = [r for r in rows if r[0] == ttl]
        key = sub[0][1]
        vals = list(dict.fromkeys(r[2] for r in sub))
        Ts = list(dict.fromkeys(r[3] for r in sub))
        tab = [[T] + [next(r[4] for r in sub if r[2] == v and r[3] == T) for v in vals] for T in Ts]
        report.append(md_table(tab, ["T (yr)"] + [f"{key}={v:g}" for v in vals]))

    p, rows = backfire()
    report.append("\n## Backfire sweep (margin vs E; sampled points)\n")
    report.append(md_table(rows, ["denial", "mode", "E", "M_now", "M_ever"]))

    for metric in ("M_now", "M_ever"):
        p, rows, m0 = tornado(metric)
        report.append(f"\n## Tornado for {metric} (baseline {m0:.3f})\n")
        report.append(md_table(rows, ["param", "low", "high", f"{metric} @low", f"{metric} @high", "swing"]))

    summ, crow, sp, p = monte_carlo(4000 if quick else 30000)
    summary["mc"] = summ
    report.append(f"\n## Monte Carlo over priors (N={summ['N']})\n")
    report.append("Overall shares, choice at t=0: " + ", ".join(f"{k} {v:.1%}" for k, v in summ["share_best_now"].items()))
    report.append("\nOverall shares incl. later seizure: " + ", ".join(f"{k} {v:.1%}" for k, v in summ["share_best_ever"].items()))
    report.append("\n\n" + md_table(crow, ["condition", "n", "P(seize now)", "P(seize now or later)",
                                            "P(Cooperate)", "P(Exit, never seize)", "P(Exit then seize)"]))
    report.append("\n\nSpearman rank correlation with the peace margin (positive = raising the parameter favours peace):\n")
    report.append(md_table(sp, ["param", "rho(M_now)", "rho(M_ever)"]))

    p, h, rows, nruns = sobol(N_pow=8 if quick else 11, n_boot=50 if quick else 200)
    report.append(f"\n## Sobol indices ({nruns} model runs)\n")
    report.append(md_table(rows, h))

    rows = satiable(1500 if quick else 6000)
    report.append("\n## Satiable utility u = 1 - exp(-K/K_sat) (Monte Carlo over the same priors)\n")
    report.append(md_table(rows, ["K_sat", "P(seize now)", "P(seize now or later)", "P(Cooperate)", "P(Exit, never seize)"]))

    report.append(f"\n\nRun time: {time.time() - t0:.0f} s\n")
    with open(os.path.join(RES, "results.md"), "w") as f:
        f.write("\n".join(report))
    with open(os.path.join(RES, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=float)
    print("\n".join(report))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    main(ap.parse_args().quick)
