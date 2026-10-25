"""Issue #51: a grid-free reference for the AI's approach to the capacity cap Kmax in the no-rival limit.

    python3 variants/cap_approach.py        # about 1 minute; prints the comparison table in results/variants.md 1a

With mu = 0 and no rival source (R6_CLEAN) and the pact holding, the AI's size follows a deterministic path:
A_{t+1} = A_t exp(g (1 - A_t / Kmax)) (chips supplied, chi = 1). Its only decision is when, if ever, to strike, an
optimal-stopping problem along that path. This module solves it by backward induction over the path itself, with no
capacity grid: strike values use the full solver's strike terms (as variants/preventive.py) and exact solo path sums
for every landing point. So it resolves sizes within O(1) of Kmax = 1e9, which neither the full solver's 160-point log
grid nor the reduced game's default grid represents.

One simplification: after a failed strike the AI is put on its solo path from A (1 - L_f) without a second strike
(no retry). That lowers the strike value, so thresholds here are lower bounds for the stated law. Near the cap the
failure branch carries probability p_f = 1.5e-10 (p_f A = 0.15), so the retry option is worth about 1e-9 there.

Status: implemented and checked (tests/test_variants.py: the reduced game with near-cap grid points, cap_pts > 0,
converges to it). It is a numerical reference for the model's stated growth law, not a new model and not empirical.
"""
from __future__ import annotations

import numpy as np

try:
    from . import _common as C
except ImportError:
    import _common as C
import equilibrium_model as em

try:
    from . import preventive as pv
except ImportError:
    import preventive as pv


def path_stop(p: dict, T: int = 300, near_cap: float = 0.0) -> dict:
    """Optimal stopping along the exact pact path from p['A0'] (T years, then the solver's 'peace' terminal).
    near_cap > 0 allows strikes only once A >= near_cap * Kmax. Returns the first strike year on the equilibrium path
    (None: never), the AI's gain over never striking, and Kmax - A in that year."""
    K, H, delta = p["Kmax"], p["H"], np.exp(-p["r"])
    a = np.empty(T + 1)
    a[0] = p["A0"]
    for t in range(T):
        a[t + 1] = a[t] * np.exp(p["g"] * max(0.0, 1.0 - a[t] / K))
    tr = p["sigma"] * p["gam"] * np.minimum(a, H)
    p_f = (1 - p["p_s0"]) * (p["D"] / (p["D"] + a)) ** p["eps"]
    cost = p["c_A"] * p["D"] * a / (a + p["D"])
    Pi0 = (1 - p["c_w"]) * H
    Pi_h = p["f_E"] * (1 - p["c_grav"]) * K * (a >= p["h_frac"] * K)
    q = min(1.0, p["q"] * p["den"])
    V_unpl = pv.path_value(p, a - cost + Pi0 + Pi_h, True)
    V_pl = pv.path_value(p, np.maximum(a - cost + Pi0 * (1 - p["d"]) + Pi_h, 1e-300), False)
    A_fail = a * (1 - p["L_f"])
    A_fail_next = A_fail * np.exp(p["g"] * np.where(A_fail >= p["A_close"], 1.0, p["chi0"])
                                  * np.maximum(0.0, 1.0 - A_fail / K))
    V_fail = a + delta * pv.path_value(p, A_fail_next, False)        # this year's flow at A, then solo, no retry
    z = p["kill_pre"] * (a < p["A_close"])
    S = (1 - p_f) * ((1 - q) * V_unpl + q * V_pl) + p_f * (1 - z) * V_fail
    W = peace = pv.path_value(p, a[T:], True)[0] + tr[T] / (1 - delta)
    first = None
    for t in range(T - 1, -1, -1):
        cont = a[t] + tr[t] + delta * W
        peace = a[t] + tr[t] + delta * peace
        if a[t] >= near_cap * K and S[t] - cont > em.TIE_TOL * cont:
            W, first = S[t], t
        else:
            W = cont
    return dict(strike_year=first, gain=float(W - peace), gap_to_cap=None if first is None else float(K - a[first]))


def path_threshold(p: dict, n: int = 30, **kw) -> tuple | None:
    """Bracket [strikes, does not strike] on q (d as given). None if the AI strikes even at q = 1."""
    if path_stop(dict(p, q=1.0), **kw)["strike_year"] is not None:
        return None
    lo, hi = 0.0, 1.0
    for _ in range(n):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if path_stop(dict(p, q=mid), **kw)["strike_year"] is not None else (lo, mid)
    return lo, hi


def cell(ac: float, lf: float) -> dict:
    """The R6c cell's parameters (mu = 0, AI starting at closure, d = 1), as run_variants.baseline_checks."""
    return dict(em.baseline(**pv.R6_CLEAN), A0=ac, A_close=ac, L_f=lf, d=1.0, w_seized=0.9)


def compare(cells=((0.003, 0.5), (0.1, 0.1), (0.1, 0.5), (1.0, 0.5), (0.03, 0.9)), cap_pts: int = 20) -> list[dict]:
    import json
    import os
    with open(os.path.join(C.MODEL, "results", "equilibrium_round3_summary.json")) as f:
        ref = json.load(f)["r6_solver"]
    solver = {tuple(c): tuple(b) for c, b in zip(ref["clean_cases"], ref["q_clean"])}
    rows = []
    for ac, lf in cells:
        p = cell(ac, lf)
        rows.append(dict(A_close=ac, L_f=lf, solver=solver[(ac, lf)], rbg=pv.needed_q(p),
                         rbg_cap=pv.needed_q(p, cap_pts=cap_pts), path=path_threshold(p),
                         path_near_cap=path_threshold(p, near_cap=0.5)))
    return rows


SENS_KEYS = ("ai_strike", "human_shutdown", "att", "suc", "strike_year", "shutdown_year", "V_H")


def structure_sensitivity(cap_pts: int = 20) -> list[list]:
    """Re-solve the issue #9 structure x policy runs (preventive.run_all) with near-cap grid points and list every run
    whose headline measures move against the committed results/variants/preventive.json. Nothing is written."""
    import json
    import os
    with open(os.path.join(C.OUT, "preventive.json")) as f:
        ref = json.load(f)["raw"]
    base = em.baseline(**pv.R6_CLEAN)
    rows = []
    for s, w in pv.STRUCTURES.items():
        for pol, o in pv.POLICIES.items():
            r, c = pv.solve(dict(base, **w), o, cap_pts=cap_pts), ref[s][pol]
            moved = any((r[k] is None) != (c[k] is None) or (r[k] is not None and abs(float(r[k]) - float(c[k]))
                                                              > 1e-3 * max(1.0, abs(float(c[k])))) for k in SENS_KEYS)
            if moved:
                rows.append([s, pol] + [f"{C.fmt(c[k])} -> {C.fmt(r[k])}" for k in SENS_KEYS])
    return rows


if __name__ == "__main__":
    b = lambda x: "none" if x is None else f"[{x[0]:.4f}, {x[1]:.4f}]"
    rows = compare()
    print(C.md_table([[r["A_close"], r["L_f"], b(r["solver"]), b(r["rbg"]), b(r["rbg_cap"]), b(r["path"]),
                       b(r["path_near_cap"])] for r in rows],
                     ["A_close", "L_f", "full solver (R6c, committed)", "reduced game, default grid",
                      "reduced game, cap_pts 20", "grid-free path", "grid-free, strikes only above Kmax/2"]))
    p = cell(0.03, 0.9)
    for q in (0.19, 0.3, 0.45, 0.55):
        r = path_stop(dict(p, q=q))
        print(f"q {q}: strike year {r['strike_year']}, Kmax - A then {r['gap_to_cap']:.3g}, gain {r['gain']:.3g}")
    for n in (20, 40):
        print(f"\nissue #9 runs that move with cap_pts {n} (committed -> near-cap grid):")
        print(C.md_table(structure_sensitivity(n), ["structure", "policy"] + list(SENS_KEYS)))
