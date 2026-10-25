"""Variant B (issue #9): fixed pact terms versus renegotiation, at saturation.

A transparent Powell-style ("War as a Commitment Problem", IO 2006) bargaining game built from the full solver's
saturation quantities. It is a reduced model, not an extension of `equilibrium_model.solve`; the full solver stays the
baseline, and the `fixed` regime below reproduces the baseline's saturation recursion exactly
(docking/powell.py `stop_year_fail`, which matches the solver's strike year 165 in the eroding-reserve world).

Players and timing (one period = one year, horizon T, AI at a fixed size A at or near the cap):
    humans  one aggregate actor (states are not separated here). Each year they set the AI's transfer x_t.
    AI      accepts (peace: it gets x_t on top of its own output) or strikes (absorbing).
All AI values are net of its own uncontested output A / (1 - delta), as in docking.md section 5.

    strike at t   AI      Phi_A(t) = (1 - p_f)(Pi(q_t) + Pi_h - cost)/(1 - delta) + p_f (x_fail/(1 - delta) - loss)
                  humans  Phi_H(t) = (1 - p_f) w_seized/(1 - delta_h) + p_f H/(1 - delta_h)
    peace at t    AI      x_t + delta V_A(t+1)
                  humans  B_H - x_t + delta_h V_H(t+1),    B_H = H (1 + gam): Earth's industry plus the trade surplus
    Pi(q) = (1 - c_w) H (1 - q den d): the prize after the denial reserve fires with probability q.

Regimes
    fixed       x_t = sigma gam H for ever (the baseline pact; AS-FIXEDTERMS).
    reneg       no commitment: each year humans offer the cheapest x in [x_lo, x_hi] the AI accepts, or let it strike
                if that is better for them. With x_lo < sigma gam H humans can squeeze the AI as they get stronger
                (relaxes AS-NOEXPLOIT); with x_hi > sigma gam H they can buy off a strike (relaxes AS-FIXEDTERMS).
    committed   humans choose one constant x in [x_lo, x_hi] at t = 0 and are bound by it (a commitment device);
                the AI best-responds as under fixed terms.

Diagnostics kept separate (the issue's distinction between existence and credible implementation)
    surplus(t)          B_H - (1 - delta) Phi_A(t) - (1 - delta_h) Phi_H(t). >= 0: a bargain exists at t (static).
    commitment_gap(t)   Phi_A(t) - delta max(Phi_A(t+1), x_lo/(1 - delta)) - x_max. > 0: an AI that humans can hold
                        to its reservation value next year cannot be paid enough this year, so without commitment the
                        bargain cannot be implemented (Powell's condition in this game's units). See diagnose().

Status: implemented; the fixed regime is verified against the baseline recursion (tests/test_variants.py). Not
human_validated, not empirical. Ties: the AI strikes only if its gross strike value exceeds its gross peace value by
the solver's relative tolerance em.TIE_TOL, as in the baseline.
"""
from __future__ import annotations

import numpy as np

try:
    from . import _common  # noqa: F401  (puts model/ on sys.path)
except ImportError:  # run as a script
    import _common  # noqa: F401
import equilibrium_model as em

A_NEAR_CAP = 0.999e9      # the docking erosion world's start, just below the cap (solver 165 = closed form 165)
T_H = 300


_QCACHE: dict = {}


def quantities(p: dict, A: float = A_NEAR_CAP) -> dict:
    """Size-dependent terms of the strike, exactly as docking/powell.stop_year_fail and em.cap_gap_fail use them."""
    key = (A, tuple(sorted(p.items())))
    if key not in _QCACHE:
        _QCACHE[key] = _quantities(p, A)
    return dict(_QCACHE[key])


def _quantities(p: dict, A: float) -> dict:
    p_f = (1 - p["p_s0"]) * (p["D"] / (p["D"] + A)) ** p["eps"]
    cost = p["c_A"] * p["D"] * A / (A + p["D"])
    loss = em.solo_value(p, A) - em.solo_value(p, A * (1 - p["L_f"]))
    Pi_h = p["f_E"] * (1 - p["c_grav"]) * p["Kmax"] * (A >= p["h_frac"] * p["Kmax"])
    return dict(A=A, p_f=p_f, cost=cost, loss=loss, Pi_h=Pi_h, delta=np.exp(-p["r"]), delta_h=np.exp(-p["r_h"]),
                B_H=p["H"] * (1 + p["gam"]), x_fix=p["sigma"] * p["gam"] * p["H"])


def war_values(p: dict, Q: dict, q_path: np.ndarray):
    """Phi_A(t) (net of A/(1-delta)) and Phi_H(t) for each year of the firing-probability path."""
    d, dh = Q["delta"], Q["delta_h"]
    Pi = (1 - p["c_w"]) * p["H"] * (1 - np.asarray(q_path) * p["den"] * p["d"])
    phiA = (1 - Q["p_f"]) * (Pi + Q["Pi_h"] - Q["cost"]) / (1 - d) + Q["p_f"] * (Q["x_fix"] / (1 - d) - Q["loss"])
    phiH = np.full_like(phiA, ((1 - Q["p_f"]) * p["w_seized"] + Q["p_f"] * p["H"]) / (1 - dh))
    return phiA, phiH


def _strikes(Q, S, W):
    """The baseline's strike test on gross values (own output added back), with the solver's tie tolerance."""
    G = Q["A"] / (1 - Q["delta"])
    return (S + G) > (W + G) * (1 + em.TIE_TOL)


def _min_accept(Q, S, VA_next):
    """Cheapest transfer the AI accepts this year: the x at which the strike test above just fails."""
    G = Q["A"] / (1 - Q["delta"])
    return (S + G) / (1 + em.TIE_TOL) - G - Q["delta"] * VA_next


def solve_fixed(p: dict, q_path, x: float | None = None, A: float = A_NEAR_CAP) -> dict:
    """Fixed terms x (default sigma gam H). Backward induction over t = T-1..0 with a 'peace' terminal value, the same
    recursion as docking/powell.stop_year_fail written net of A/(1-delta). Returns the policy and the path outcome."""
    Q = quantities(p, A)
    x = Q["x_fix"] if x is None else float(x)
    q_path = np.asarray(q_path, float)
    T = len(q_path) - 1
    phiA, phiH = war_values(p, Q, q_path)
    d, dh = Q["delta"], Q["delta_h"]
    VA, VH = x / (1 - d), (Q["B_H"] - x) / (1 - dh)
    strike = np.zeros(T, bool)
    VA0 = np.empty(T); VH0 = np.empty(T)
    for t in range(T - 1, -1, -1):
        W = x + d * VA
        if _strikes(Q, phiA[t], W):
            strike[t] = True
            VA, VH = phiA[t], phiH[t]
        else:
            VA, VH = W, Q["B_H"] - x + dh * VH
        VA0[t], VH0[t] = VA, VH
    return _outcome(Q, "fixed", strike, np.full(T, x), VA0, VH0, human_war=np.zeros(T, bool), x_lo=x, x_hi=x)


def solve_reneg(p: dict, q_path, x_lo: float = 0.0, x_hi: float | None = None, A: float = A_NEAR_CAP) -> dict:
    """Renegotiation without commitment. Terminal: the stationary equilibrium with q frozen at q_path[T]."""
    Q = quantities(p, A)
    x_hi = Q["B_H"] if x_hi is None else float(x_hi)
    q_path = np.asarray(q_path, float)
    T = len(q_path) - 1
    phiA, phiH = war_values(p, Q, q_path)
    d, dh = Q["delta"], Q["delta_h"]
    # stationary terminal: cheapest constant transfer that holds the AI, or war
    xs = max(x_lo, (1 - d) * _min_accept(Q, phiA[T], 0.0))
    if xs <= x_hi and (Q["B_H"] - xs) / (1 - dh) >= phiH[T]:
        VA, VH = xs / (1 - d), (Q["B_H"] - xs) / (1 - dh)
    else:
        VA, VH = phiA[T], phiH[T]
    strike = np.zeros(T, bool); human_war = np.zeros(T, bool)
    xpath = np.full(T, np.nan)
    VA0 = np.empty(T); VH0 = np.empty(T)
    for t in range(T - 1, -1, -1):
        xstar = max(x_lo, _min_accept(Q, phiA[t], VA))
        peaceH = Q["B_H"] - xstar + dh * VH
        if xstar > x_hi:
            strike[t] = True
        elif peaceH < phiH[t]:
            strike[t] = True; human_war[t] = True
        if strike[t]:
            VA, VH = phiA[t], phiH[t]
        else:
            xpath[t] = xstar
            VA, VH = xstar + d * VA, peaceH
        VA0[t], VH0[t] = VA, VH
    return _outcome(Q, "reneg", strike, xpath, VA0, VH0, human_war=human_war, x_lo=x_lo, x_hi=x_hi)


def solve_committed(p: dict, q_path, x_lo: float = 0.0, x_hi: float | None = None, A: float = A_NEAR_CAP,
                    n_grid: int = 301) -> dict:
    """Humans pick the constant transfer that maximises their t = 0 welfare, bound for the horizon."""
    Q = quantities(p, A)
    x_hi = Q["B_H"] if x_hi is None else float(x_hi)
    grid = np.unique(np.concatenate([np.linspace(x_lo, x_hi, n_grid), [Q["x_fix"]] if x_lo <= Q["x_fix"] <= x_hi else []]))
    best = None
    for x in grid:
        o = solve_fixed(p, q_path, x=x, A=A)
        if best is None or o["V_H"] > best["V_H"] + 1e-12:
            best = o
    best["regime"] = "committed"
    best["x_committed"] = best["x_lo"]
    return best


def _outcome(Q, regime, strike, xpath, VA0, VH0, human_war, x_lo, x_hi) -> dict:
    """Outcome measures, kept separate: timing, successful harm, control retention, welfare, distribution."""
    T = len(strike)
    d, dh = Q["delta"], Q["delta_h"]
    sy = int(np.argmax(strike)) if strike.any() else None
    horizon = sy if sy is not None else T
    xs = np.nan_to_num(np.asarray(xpath, float)[:horizon])
    seize = (1 - Q["p_f"]) if sy is not None else 0.0
    return dict(
        regime=regime, strike_year=sy, human_chose_war=bool(sy is not None and human_war[sy]),
        P_seizure=float(seize),                       # successful harm (a seizure; lethal when w_seized = 0)
        P_strike_fails=float(Q["p_f"]) if sy is not None else 0.0,
        control_retained=float(1 - seize),            # P(no successful seizure within the horizon)
        V_A=float(VA0[0]), V_H=float(VH0[0]),         # AI value net of own output; human welfare (discount r_h)
        pv_transfer_H=float(np.sum(xs * dh ** np.arange(horizon))),   # what humans pay, at their discount rate
        x_first=float(xs[0]) if horizon else None, x_last=float(xs[-1]) if horizon else None,
        x_lo=float(x_lo), x_hi=float(x_hi), T=T,
    )


def diagnose(p: dict, q_path, x_lo: float = 0.0, x_max: float | None = None, A: float = A_NEAR_CAP) -> dict:
    """World-level bargaining diagnostics, independent of the regime played.

    exists      surplus(t) = B_H - (1 - delta) Phi_A(t) - (1 - delta_h) Phi_H(t) >= 0 (a static bargain exists at t).
    credible    without commitment humans can hold the AI next year to V_min(t+1) = max(Phi_A(t+1), x_lo/(1 - delta)),
                so this year they must pay Phi_A(t) - delta V_min(t+1). gap(t) = that minus x_max. gap > 0 in some year
                means no renegotiation-proof bargain exists although a static bargain may (Powell's commitment problem).
    """
    Q = quantities(p, A)
    x_max = Q["B_H"] if x_max is None else float(x_max)
    q_path = np.asarray(q_path, float)
    phiA, phiH = war_values(p, Q, q_path)
    d, dh = Q["delta"], Q["delta_h"]
    surplus = Q["B_H"] - (1 - d) * phiA - (1 - dh) * phiH
    vmin = np.maximum(phiA[1:], x_lo / (1 - d))
    gap = phiA[:-1] - d * vmin - x_max
    return dict(surplus_t0=float(surplus[0]), min_surplus=float(surplus.min()),
                bargain_exists_every_year=bool((surplus >= 0).all()), bargain_exists_t0=bool(surplus[0] >= 0),
                gap_max=float(gap.max()), commitment_problem=bool((gap > 0).any()),
                first_gap_year=int(np.argmax(gap > 0)) if (gap > 0).any() else None,
                lockin_t0=float((1 - d) * phiA[0]), lockin_max=float((1 - d) * phiA.max()),
                x_fix=Q["x_fix"], x_max=x_max, x_lo=x_lo, p_f=Q["p_f"])


# ---------------------------------------------------------------------------------------------------------------
# Scenarios. Each starts from em.baseline() with no rival source (mu = 0), so only the strike motive is at stake.
# ---------------------------------------------------------------------------------------------------------------
def scenario(name: str):
    t = np.arange(T_H + 1)
    if name == "eroding_reserve":          # humans weaken: q decays 0.5 %/yr (docking.md 5, robust_design.md 4)
        p = em.baseline(mu=0.0, beta_bg=0.0, q_er=0.005)
        return p, p["q"] * np.exp(-p["q_er"] * t)
    if name == "closing_window":           # humans strengthen: the reserve upgrades from q 0.45 to 0.9 in year 20
        p = em.baseline(mu=0.0, beta_bg=0.0)
        return p, np.where(t < 20, 0.45, 0.9)
    if name == "no_reserve":               # S6: no denial reserve (den 0), constant
        p = em.baseline(mu=0.0, beta_bg=0.0, den=0.0)
        return p, np.full(T_H + 1, p["q"])
    if name == "harvest":                  # S16: harvest motive f_E 1e-6, constant
        p = em.baseline(mu=0.0, beta_bg=0.0, f_E=1e-6)
        return p, np.full(T_H + 1, p["q"])
    if name == "baseline":
        p = em.baseline(mu=0.0, beta_bg=0.0)
        return p, np.full(T_H + 1, p["q"])
    raise KeyError(name)


SCENARIOS = ["baseline", "eroding_reserve", "closing_window", "no_reserve", "harvest"]
REGIMES = {
    "fixed": lambda p, q: solve_fixed(p, q),
    "reneg_up": lambda p, q: solve_reneg(p, q, x_lo=quantities(p)["x_fix"]),        # buy-offs only
    "reneg_down": lambda p, q: solve_reneg(p, q, x_lo=0.0, x_hi=quantities(p)["x_fix"]),  # squeeze only
    "reneg_two_sided": lambda p, q: solve_reneg(p, q, x_lo=0.0),
    "committed": lambda p, q: solve_committed(p, q, x_lo=0.0),
}


def run_all() -> dict:
    out = {}
    for s in SCENARIOS:
        p, q = scenario(s)
        out[s] = {r: f(p, q) for r, f in REGIMES.items()}
        out[s]["diagnostics"] = diagnose(p, q)
    return out
