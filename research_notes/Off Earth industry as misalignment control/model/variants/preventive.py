"""Variant H (issue #9): human preventive action and improving human control, during the bootstrap.

A reduced stochastic game ("RBG") with one AI and one aggregate human actor, solved by backward induction on a log
grid in the AI's capacity A, like the full solver but without states, rival programmes or the fab schedule. It reuses
the full solver's parameters (em.baseline) and strike terms read-only. It is NOT an extension of
`equilibrium_model.solve`; the full solver stays the baseline. With every new switch off, the RBG is a stripped-down
copy of the baseline game in its no-rival limit (R6_CLEAN: mu = 0, B_R = 0), and tests/test_variants.py checks that
it reproduces the full solver's R6c brackets (needed q at d = 1) and the saturation closed form em.q_star_cap.

State: A (log grid), mode m (0 pact, 1 collapsed), human control level c in 0..Lc.
Per year, in this order:
  1. Humans (only if `human_first`) may attempt a preventive shutdown of the AI, cooperating or not. It succeeds with
     probability sh_c * D_s / (D_s + A): the AI is eliminated; humans keep Earth (H a year) and lose the trade. On
     failure the pact collapses (m = 1: no more trade or chips) and the AI moves in collapsed mode this year. Optional
     cost c_K. So the option always includes ending the pact; with sh0 = 0 it is only that (policy end_pact_only),
     which separates "cut the AI off" from "try to destroy it".
  2. The AI cooperates/waits or strikes. A strike succeeds with probability 1 - p_f(A) (baseline odds); the reserve
     fires with probability q_c, plugging share d. On success the AI grows alone from its landing size (with chips if
     unplugged; without chips below closure if plugged), humans get w_seized. On failure the AI dies with probability
     kill_pre before closure; otherwise it falls to A (1 - L_f) in collapsed mode (it may strike again: AS-FREERETRY,
     as in the baseline). With `learn`, humans learn from the failed strike: c -> c + 1.
  3. Flows and growth (pact: chips supplied, chi = 1; collapsed: chi0 below A_close). Exogenous tightening: with
     probability 1 - exp(-h_tight) per year, c -> c + 1 ("each caught excursion, including one by a weaker model,
     tightens surveillance", spec node D18; others' excursions are not modelled as players).
Control level c raises the reserve's firing probability, q_c = min(1, q + dq c), and the shutdown odds,
sh_c = min(1, sh0 + dsh c). Neither sign is assumed: the runs report what each does to every outcome.

Ties: the AI strikes only above em.TIE_TOL (relative); humans attempt a shutdown only if strictly better for them.
Indicators are probabilities from t = 0 along the equilibrium (backward recursions, as the solver's IND).
Status: implemented; baseline limit verified against the full solver's R6c brackets and em.q_star_cap (tests).
Scope (issue #51): with the default grid it reproduces the solver's discretisation, which never brings the AI within
O(1) of Kmax; it does not resolve the stated law there. cap_pts > 0 does (variants/cap_approach.py).
Not human_validated, not empirical.
"""
from __future__ import annotations

import numpy as np

try:
    from . import _common  # noqa: F401
except ImportError:
    import _common  # noqa: F401
import equilibrium_model as em

R6_CLEAN = dict(mu=0.0, beta_bg=0.0, B_R=0.0, B_Rc=0.0)
DEFAULT_OPTS = dict(human_first=False, sh0=0.0, dsh=0.0, D_s=1.0, c_K=0.0,
                    learn=False, dq=0.0, h_tight=0.0, Lc=2)
IND = ["att", "suc", "fail", "hk", "hks", "dead", "tatt", "thk", "pre"]


def _grid(p, A0, nA, cap_pts=0):
    K = p["Kmax"]
    g = np.logspace(np.log10(min(1e-5, A0 / 10)), np.log10(2.0 * K), nA)
    # K itself is left out. At exactly K a strike's unplugged landing (above K) stays put while a plugged landing
    # (below K) regrows. The default grid's last point below K is K (1 - 1e-6), 1000 units below the cap, and the AI's
    # next-year size from there is interpolated back onto it, so the default grid never lets the AI within O(1) of K.
    # Under the logistic law the path from below does get there (K - A shrinks by a factor of about 1 - g a year),
    # and there a plugged landing regrows while an unplugged one above K is permanent: issue #51,
    # variants/cap_approach.py. cap_pts > 0 adds cap_pts points a decade at K (1 - 10^-k), k = 1..13, which resolves
    # that region; the default (0) keeps the grid that reproduces the full solver's R6c brackets and the committed
    # results/variants/*.json.
    extra = [A0, K * (1 - 1e-6), p["A_close"], p["H"]]
    if cap_pts:
        extra += list(K * (1 - 10.0 ** -np.arange(1.0, 13.0 + 1e-9, 1.0 / cap_pts)))
    return np.unique(np.concatenate([g, extra]))


class _Interp:
    """Linear interpolation, weights linear in log A (the grid is log-spaced). Applied only to excess values (see
    solve), never to the AI's absolute value, whose saturation-stage gaps are 1e-10 of its size."""

    def __init__(self, grid, x):
        lg = np.log(grid)
        lx = np.log(np.clip(x, grid[0], grid[-1]))
        i = np.clip(np.searchsorted(lg, lx) - 1, 0, len(grid) - 2)
        self.i, self.w = i, (lx - lg[i]) / (lg[i + 1] - lg[i])

    def __call__(self, V):
        return V[..., self.i] * (1 - self.w) + V[..., self.i + 1] * self.w


def path_value(p: dict, x, chips: bool, n: int = 3000):
    """Exact discounted capacity along the deterministic solo path from x (dt = 1), as em._path_sums: with chips
    (chi = 1), or without (chi0 below A_close, 1 above). Vectorised; no interpolation."""
    a = np.array(x, float, copy=True)
    K, g, delta = p["Kmax"], p["g"], np.exp(-p["r"])
    tot = np.zeros_like(a)
    disc = 1.0
    for _ in range(n):
        tot += disc * a
        chi = 1.0 if chips else np.where(a >= p["A_close"], 1.0, p["chi0"])
        a = a * np.exp(g * chi * np.maximum(0.0, 1.0 - a / K))
        disc *= delta
    return tot


def solve(p: dict, opts: dict | None = None, A0: float | None = None, T: int = 300, nA: int = 200,
          cap_pts: int = 0) -> dict:
    """AI values are carried as EXCESS over an exact solo value, E_m(A) = V_m(A) - Base_m(A) with Base_0 the solo
    value with chips (pact) and Base_1 the solo value without chips below closure (collapsed), both from path_value.
    Only E is interpolated, so the saturation-stage comparison (gaps of O(1) on values of 5e10) is not swamped by
    interpolation error. Human values are O(10) and are interpolated directly. cap_pts: see _grid (default 0)."""
    o = dict(DEFAULT_OPTS, **(opts or {}))
    A0 = p["A0"] if A0 is None else A0
    A = _grid(p, A0, nA, cap_pts)
    i0 = int(np.searchsorted(A, A0))
    K, H = p["Kmax"], p["H"]
    delta, dh = np.exp(-p["r"]), np.exp(-p["r_h"])
    C = int(o["Lc"]) + 1
    cs = np.arange(C)
    q_c = np.minimum(1.0, p["q"] * p["den"] + o["dq"] * cs)[:, None]           # (C,1)
    sh_c = (np.minimum(1.0, o["sh0"] + o["dsh"] * cs)[:, None] * o["D_s"] / (o["D_s"] + A)[None, :])  # (C,nA)
    if not o["human_first"]:
        sh_c = np.zeros_like(sh_c)
    p_t = 1 - np.exp(-o["h_tight"])
    up = np.minimum(cs + 1, C - 1)                                              # c after one tightening step

    def grow(x, chi):
        return x * np.exp(p["g"] * chi * np.maximum(0.0, 1.0 - x / K))

    chi_coll = np.where(A >= p["A_close"], 1.0, p["chi0"])
    Base = [path_value(p, A, True), path_value(p, A, False)]
    # strike terms (baseline formulas); landing values exact
    p_f = (1 - p["p_s0"]) * (p["D"] / (p["D"] + A)) ** p["eps"]
    cost = p["c_A"] * p["D"] * A / (A + p["D"])
    Pi_h = p["f_E"] * (1 - p["c_grav"]) * K * (A >= p["h_frac"] * K)
    Pi0 = (1 - p["c_w"]) * H
    V_unpl = path_value(p, A - cost + Pi0 + Pi_h, True)                         # captures fabs
    V_pl = path_value(p, np.maximum(A - cost + Pi0 * (1 - p["d"]) + Pi_h, 1e-300), False)   # plugged
    A_fail = A * (1 - p["L_f"])
    V_fail0 = A - A_fail + path_value(p, A_fail, False)     # this year's collapsed flow at A, then solo from A_fail
    Afn = grow(A_fail, np.where(A_fail >= p["A_close"], 1.0, p["chi0"]))
    z = p["kill_pre"] * (A < p["A_close"])
    tr = p["sigma"] * p["gam"] * np.minimum(A, H)
    fH = [H + (p["gam"] * np.minimum(A, H) - tr), H + 0 * A]
    W_noAI, W_seized = H / (1 - dh), p["w_seized"] / (1 - dh)
    In = [_Interp(A, grow(A, 1.0)), _Interp(A, grow(A, chi_coll))]
    Ifail = _Interp(A, Afn)

    # terminal ('peace', as the solver): pact keeps its trade stream; collapsed grows alone
    EA = np.stack([np.broadcast_to(tr / (1 - delta), (C, len(A))), np.zeros((C, len(A)))]).copy()
    VH = np.stack([np.broadcast_to(fH[0] / (1 - dh), (C, len(A))), np.broadcast_to(fH[1] / (1 - dh), (C, len(A)))]).copy()
    I = {k: np.zeros_like(EA) for k in IND}
    actA = np.zeros((2, C, len(A)), bool); actH = np.zeros((2, C, len(A)), bool)

    def tight(X):          # expectation over the exogenous tightening draw, X shape (..., C, nA)
        return (1 - p_t) * X + p_t * X[..., up, :]

    cf = up if o["learn"] else cs                           # control level after a failed strike
    for t in range(T - 1, -1, -1):
        nEA, nVH = np.empty_like(EA), np.empty_like(VH)
        nI = {k: np.empty_like(EA) for k in IND}
        cE = [tight(In[m](EA[m])) for m in (0, 1)]
        cH = [tight(In[m](VH[m])) for m in (0, 1)]
        cI = [{k: tight(In[m](I[k][m])) for k in IND} for m in (0, 1)]
        fE_ = tight(Ifail(EA[1]))[cf]
        fH_ = tight(Ifail(VH[1]))[cf]
        fI = {k: tight(Ifail(I[k][1]))[cf] for k in IND}
        aiE, aiH, aiI = [], [], []
        for m in (0, 1):
            CE = (tr if m == 0 else 0.0) + delta * cE[m]                       # excess over Base_m(A)
            CH = fH[m] + dh * cH[m]
            SE = ((1 - p_f) * ((1 - q_c) * (V_unpl - Base[m]) + q_c * (V_pl - Base[m]))
                  + p_f * (1 - z) * (V_fail0 - Base[m] + delta * fE_) - p_f * z * Base[m])
            SH = (1 - p_f) * W_seized + p_f * (z * W_noAI + (1 - z) * (fH[1] + dh * fH_))
            s = (SE - CE) > em.TIE_TOL * (Base[m] + CE)
            actA[m] = s
            cont = p_f * (1 - z)
            SI = {k: cont * fI[k] for k in IND}
            SI["att"] = np.ones_like(SE); SI["tatt"] = np.full_like(SE, float(t))
            SI["suc"] = (1 - p_f) + cont * fI["suc"]
            SI["fail"] = p_f + 0 * SE
            SI["dead"] = p_f * z + cont * fI["dead"]
            SI["pre"] = np.broadcast_to((A < p["A_close"]).astype(float), SE.shape).copy()
            aiE.append(np.where(s, SE, CE)); aiH.append(np.where(s, SH, CH))
            aiI.append({k: np.where(s, SI[k], cI[m][k]) for k in IND})
        for m in (0, 1):
            # humans' preventive shutdown (success: AI eliminated; failure: collapse, the AI then moves in mode 1)
            KE = (1 - sh_c) * (aiE[1] + Base[1]) - Base[m]
            KH = sh_c * W_noAI + (1 - sh_c) * aiH[1] - o["c_K"]
            k = o["human_first"] & (KH > aiH[m] + 1e-12 * np.abs(aiH[m]))
            actH[m] = k
            nEA[m] = np.where(k, KE, aiE[m]); nVH[m] = np.where(k, KH, aiH[m])
            KI = {kk: (1 - sh_c) * aiI[1][kk] for kk in IND}
            KI["hk"] = np.ones_like(KE); KI["thk"] = np.full_like(KE, float(t))
            KI["hks"] = sh_c + (1 - sh_c) * aiI[1]["hks"]
            KI["dead"] = sh_c + (1 - sh_c) * aiI[1]["dead"]
            for kk in IND:
                nI[kk][m] = np.where(k, KI[kk], aiI[m][kk])
        EA, VH, I = nEA, nVH, nI
        if t == 0:
            act0 = dict(human_shutdown=bool(actH[0, 0, i0]), ai_strike=bool(actA[0, 0, i0]))
    out = dict(V_A=float(Base[0][i0] + EA[0, 0, i0]), E_A=float(EA[0, 0, i0]), V_H=float(VH[0, 0, i0]), **act0)
    for k in IND:
        out[k] = float(I[k][0, 0, i0])
    out["strike_year"] = out["tatt"] / out["att"] if out["att"] > 1e-12 else None
    out["shutdown_year"] = out["thk"] / out["hk"] if out["hk"] > 1e-12 else None
    out["control_retained"] = 1.0 - out["suc"]
    out["P_seizure"] = out["suc"]
    return out


def needed_q(p: dict, opts=None, steps: int = 8, **kw):
    """Bisection bracket [strikes, does not strike] on q (d as given) for P(strike) < 0.5, as run_equilibrium's
    _solver_bisect does for R6c."""
    if solve(dict(p, q=1.0), opts, **kw)["att"] >= 0.5:
        return None
    lo, hi = 0.0, 1.0
    for _ in range(steps):
        mid = 0.5 * (lo + hi)
        if solve(dict(p, q=mid), opts, **kw)["att"] >= 0.5:
            lo = mid
        else:
            hi = mid
    return (lo, hi)


# ---------------------------------------------------------------------------------------------------------------
# Runs for issue #9. Structures are worlds (what the AI would do absent the new options); policies are human options.
# All start from the no-rival limit R6_CLEAN (mu = 0, B_R = 0), A0 = 1e-3, A_close = 0.1, seq a.
# ---------------------------------------------------------------------------------------------------------------
STRUCTURES = {
    "holds": dict(),                                      # baseline reserve q 0.7, d 0.9: the pact holds
    "weak_reserve": dict(q=0.45),                         # the AI strikes at closure
    "weak_survivable": dict(q=0.55, kill_pre=0.5),        # strikes at closure; an early failure is survivable
    "retry_now": dict(q=0.55, kill_pre=0.2),              # strikes at year 0 (the retry artefact, AS-FREERETRY)
    "late_harvest": dict(f_E=1e-8),                       # strikes late, near saturation, to harvest Earth
    "survivable_seizure": dict(q=0.45, w_seized=0.9),     # as weak_reserve, but a seizure leaves humans 90 %
}
CTRL = dict(dq=0.2, dsh=0.2)
POLICIES = {
    "none": dict(),
    "learn": dict(learn=True, **CTRL),                    # D18 check 1: humans learn after a failed strike
    "tighten": dict(h_tight=0.05, **CTRL),                # improving control from others' caught excursions
    "end_pact_only": dict(human_first=True, sh0=0.0),     # humans may end the pact (cut chips) but cannot shut down
    "shutdown_0.1": dict(human_first=True, sh0=0.1),      # D18 check 2: humans may strike first (weak capability)
    "shutdown_0.3": dict(human_first=True, sh0=0.3),
    "shutdown_0.3+tighten": dict(human_first=True, sh0=0.3, h_tight=0.05, **CTRL),
}


def run_all(T: int = 300) -> dict:
    base = em.baseline(**R6_CLEAN)
    return {s: {pn: solve(dict(base, **w), o, T=T) for pn, o in POLICIES.items()} for s, w in STRUCTURES.items()}
