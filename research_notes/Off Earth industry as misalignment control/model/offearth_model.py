"""
Off-Earth exit vs. Earth seizure: a transparent decision model.

A capable, possibly misaligned AI chooses at t = 0 among

    C   Cooperate  - stay inside human-sanctioned off-Earth expansion, take share sigma
    X   Exit       - expand off-Earth unilaterally, leave Earth alone
    S   Seize      - attempt takeover of Earth's (and seizable space) industry now
    XS  Exit, then seize at a later time T (the "deferred threat")

Everything is deterministic given parameters except two explicit lotteries in
seizure (success/failure, denial fires/does not fire). The AI maximises

    V = integral_0^inf  e^{-r t} S(t) u(K(t)) dt

where K(t) is the AI's industrial capacity (units: today's whole-Earth industry = 1),
S(t) = exp(-integral h) is its survival probability under a hazard h(t), and
u is its utility over resources.

All equations are written out in decision_model.md. Parameter ranges are
ASSUMPTIONS; the basis for each is in PARAMS below.

Pure numpy. Every function is vectorised over a leading sample axis so the same
code runs a single baseline, a 2-D sweep, Monte Carlo, or a Sobol design.
"""
from __future__ import annotations

from collections import OrderedDict
import numpy as np

# ---------------------------------------------------------------------------
# Parameters: name -> (baseline, low, high, scale, meaning, basis)
# baseline = the "thesis policy" case (Earth de-industrialised, modest denial).
# low/high = the range used for Monte Carlo, tornado and Sobol.
# scale    = 'lin' (uniform) or 'log' (log-uniform) sampling.
# ---------------------------------------------------------------------------
PARAMS: "OrderedDict[str, tuple]" = OrderedDict([
    # --- human policy levers -------------------------------------------------
    ("E",      (0.10, 0.02, 1.0, "log",
                "Earth-surface industrial capacity left at t=0 (today = 1)",
                "Policy lever. 1 = status quo; 0.02 = 98% of industry removed or relocated.")),
    ("psi",    (0.70, 0.0, 1.0, "lin",
                "Share of removed Earth industry that is relocated to human-held space (vs. simply shut down)",
                "Policy lever. psi=0 is pure de-growth; psi=1 is pure relocation.")),
    ("kappa",  (0.30, 0.0, 1.0, "lin",
                "Share of human-held space industry that falls with Earth if Earth is seized",
                "Assumption: depends on whether space assets are commanded from Earth / hackable "
                "(high) or independently governed and defended (low).")),
    ("d",      (0.50, 0.0, 1.0, "lin",
                "Denial fraction: share of seizable capacity that 'evaporates' if the deterrent fires",
                "Policy lever (deterrence by denial).")),
    ("q",      (0.50, 0.0, 1.0, "lin",
                "Credibility: AI's probability that the denial mechanism survives preemption and fires",
                "Policy lever / unknown. Deliberately ambiguous deterrent => AI holds an interior belief.")),
    ("h_C",    (0.01, 0.001, 0.1, "log",
                "Hazard (/yr) a cooperating AI faces from humans reneging / shutting it down",
                "Saklakov's per-step shutdown probability p, in continuous time. Policy lever: "
                "credible commitment lowers it. Range spans 1000-yr to 10-yr expected tenure.")),
    ("sigma",  (0.30, 0.02, 0.9, "log",
                "AI's share of the sanctioned off-Earth economy under cooperation",
                "Policy lever (Potapov's cooperative reward r). Assumption.")),
    # --- growth / physics ----------------------------------------------------
    ("g",      (0.35, 0.035, 0.69, "log",
                "Off-Earth industrial growth rate (/yr) once bootstrapped",
                "Doubling time 1-20 yr. Metzger et al. 2013 model ~2-yr generations for lunar "
                "bootstrapping; range widened downward for closure losses and upward for AI-run robotics.")),
    ("Kmax",   (1e9, 1e4, 1e13, "log",
                "Accessible capacity cap (today's Earth industry = 1)",
                "Sun outputs ~2e13x today's ~20 TW human primary power (620 EJ/yr). Cap of 1e4..1e13 "
                "spans 'inner-system industry' to 'Dyson-scale'.")),
    ("s0",     (1e-3, 1e-5, 1e-1, "log",
                "AI's own seed capacity it can take off-Earth without attacking",
                "Assumption. Metzger et al. bootstrap from ~12-41 t landed; here measured as a fraction "
                "of Earth industry the AI can divert.")),
    ("beta",   (0.8, 0.0, 1.0, "lin",
                "Bootstrap dependence on Earth supply chains (growth penalty if cut off)",
                "Assumption. Potapov: early off-Earth ops depend on Earth for precision parts.")),
    ("tau_b",  (20.0, 5.0, 50.0, "lin",
                "Time constant (yr) for the off-Earth loop to close (penalty decays as e^{-t/tau_b})",
                "Assumption. Metzger et al.: ~20-yr bootstrap to self-sufficiency.")),
    ("E_need", (0.10, 0.01, 1.0, "log",
                "Industrial base needed to supply the full precision supply chain",
                "Assumption. If captured/available base >= E_need the bootstrap penalty vanishes.")),
    # --- conflict ------------------------------------------------------------
    ("p_s0",   (0.5, 0.05, 0.95, "lin",
                "Seizure success probability against today's (undiminished) humanity",
                "Assumption; unknowable today. Carlsmith 2022 treats takeover success as a key "
                "uncertain conditional.")),
    ("eps",    (0.5, 0.0, 1.0, "lin",
                "How much seizure failure risk scales with the human/AI industrial ratio",
                "Assumption. eps=0: takeover is decided by cyber/persuasion, not industry. "
                "eps=1: failure odds proportional to human industrial share.")),
    ("c_w",    (0.3, 0.0, 0.8, "lin",
                "Share of seized capacity destroyed in the fighting itself",
                "Assumption (Fearon's 'costs of war').")),
    # --- threat to an AI that leaves Earth alone ----------------------------
    ("lam_s",  (0.05, 0.005, 0.3, "log",
                "Strike/shutdown hazard (/yr) from humans at parity, reach-limited",
                "Assumption. Human preemption of an AI that has defected (Powell/Saklakov feedback).")),
    ("tau_d",  (15.0, 3.0, 50.0, "lin",
                "Time constant (yr) over which distance/dispersal puts the AI out of human reach",
                "Assumption. Transit times of months-years and dispersal across many bodies.")),
    ("lam_r",  (0.01, 1e-4, 0.1, "log",
                "Rival/competition hazard (/yr) at parity, NOT reach-limited (humans build a rival AI that follows)",
                "Assumption. The 'real cost' of leaving Earth intact: Earth can build competitors.")),
    ("th_min", (0.0, 0.0, 0.1, "lin",
                "Threat floor: share of rival threat Earth poses regardless of its industrial share",
                "Assumption. 0 = threat scales with industry (the thesis's premise). >0 = a rival can be "
                "dangerous through a better algorithm built on a small industrial base.")),
    ("rho_h",  (0.3, 0.05, 1.0, "lin",
                "Human-side off-Earth growth rate as a fraction of g",
                "Assumption. ~1 if humans have their own capable aligned AI; small if not.")),
    # --- preferences ---------------------------------------------------------
    ("r",      (0.02, 0.001, 0.1, "log",
                "AI's discount rate (/yr)",
                "Assumption. Low r = far-sighted (Saklakov: far-sighted agents confront more).")),
    ("eta",    (0.0, 0.0, 0.9, "lin",
                "Curvature of utility u(K)=K^(1-eta); 0 = linear, unboundedly acquisitive",
                "Assumption. Satiable utility is run separately as a scenario.")),
    ("omega",  (0.0, 0.0, 0.1, "lin",
                "Symbiosis premium: proportional gain to the AI from an intact, trading human civilisation",
                "Assumption. 0 = humans are worth nothing to the AI (worst case). Lost if Earth is seized. "
                "Potapov's 'cooperative reward' and comparative-advantage trade.")),
])

NAMES = list(PARAMS.keys())
Z0 = 1e-3  # pre-existing sanctioned space industry (fixed, small)

# Time grid: fine early (where decisions bite), coarse later. Years.
T_GRID = np.concatenate([np.arange(0.0, 100.0, 0.25), np.arange(100.0, 1500.0 + 1e-9, 2.0)])
SEIZE_TIMES = np.array([2.0, 5.0, 10.0, 20.0, 30.0, 50.0, 75.0, 100.0, 150.0, 200.0, 300.0])


def baseline(**over) -> dict:
    p = {k: v[0] for k, v in PARAMS.items()}
    p.update(over)
    return p


def as_arrays(p: dict, n: int | None = None) -> dict:
    """Broadcast every parameter to shape (n, 1)."""
    if n is None:
        n = max(np.size(v) for v in p.values())
    return {k: np.broadcast_to(np.asarray(v, dtype=float).reshape(-1, 1), (n, 1)).copy()
            for k, v in p.items()}


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------
def logistic(K0, Kmax, G):
    """Logistic growth with cumulative log-growth G(t): K = Kmax / (1 + (Kmax/K0 - 1) e^{-G})."""
    return Kmax / (1.0 + (Kmax / K0 - 1.0) * np.exp(-G))


def cum_growth(g, b, tau, s):
    """G(s) = integral_0^s g (1 - b e^{-x/tau}) dx  (growth penalised by bootstrap dependence b)."""
    return g * (s - b * tau * (1.0 - np.exp(-s / tau)))


def utility(K, eta, mode="crra", K_sat=None):
    if mode == "satiable":
        return 1.0 - np.exp(-K / K_sat)
    return np.power(K, 1.0 - eta)


def cumtrapz(y, t):
    dt = np.diff(t)
    out = np.zeros_like(y)
    out[..., 1:] = np.cumsum(0.5 * (y[..., 1:] + y[..., :-1]) * dt, axis=-1)
    return out


def path_value(t, K, h, r, eta, mask=None, S0=1.0, mode="crra", K_sat=None):
    """V = int e^{-rt} S(t) u(K) dt  + closed-form tail beyond the grid.

    mask: where False, integrand is 0 (path not yet started). S0 multiplies survival.
    Returns (V, cumulative integral array, S array).
    """
    if mask is not None:
        h = np.where(mask, h, 0.0)
    S = S0 * np.exp(-cumtrapz(h, t))
    f = np.exp(-r * t) * S * utility(K, eta, mode, K_sat)
    if mask is not None:
        f = np.where(mask, f, 0.0)
    cum = cumtrapz(f, t)
    tail = f[..., -1] / (r[..., 0] + h[..., -1])
    return cum[..., -1] + tail, cum, S


_DT = np.diff(T_GRID)


def compete(K0, Y0, gK, gY, Kmax, i0=0):
    """AI capacity K and human space capacity Y growing in a SHARED resource pool:

        d ln K/dt = gK(t) (1 - (K+Y)/Kmax),   d ln Y/dt = gY (1 - (K+Y)/Kmax)

    Integrated with an exponential-Euler (Ricker) step from grid index i0.
    Whoever saturates the pool first keeps its share; nobody 'catches up' afterwards.
    K0, Y0, gY, Kmax: (n,1); gK: (n, M). Returns K, Y of shape (n, M) (values before i0 = start values).
    """
    n, M = gK.shape
    K = np.empty((n, M)); Y = np.empty((n, M))
    K[:, :i0 + 1] = K0; Y[:, :i0 + 1] = Y0
    gy, km = gY[:, 0], Kmax[:, 0]
    for i in range(i0, M - 1):
        crowd = 1.0 - (K[:, i] + Y[:, i]) / km
        K[:, i + 1] = K[:, i] * np.exp(gK[:, i] * _DT[i] * crowd)
        Y[:, i + 1] = Y[:, i] * np.exp(gy * _DT[i] * crowd)
    return K, Y


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------
def evaluate(p: dict, seize_later=True, mode="crra", K_sat=1.0, return_paths=False,
             seize_times=None):
    """Evaluate all strategies for a batch of parameter sets.

    p: dict of arrays (n,1) (use as_arrays). Returns dict of (n,) arrays.
    """
    t = T_GRID[None, :]
    E, psi, kap = p["E"], p["psi"], p["kappa"]
    d, q = p["d"], p["q"]
    g, Kmax, s0 = p["g"], p["Kmax"], p["s0"]
    beta, tau_b, E_need = p["beta"], p["tau_b"], p["E_need"]
    r, eta = p["r"], p["eta"]

    Y0 = psi * (1.0 - E) + Z0           # human-held space industry at t=0
    P0 = E + Y0                          # total human industrial capacity at t=0

    # ---- human side (used by X and S) -----------------------------------
    g_h = p["rho_h"] * g

    reach = p["lam_s"] * np.exp(-t / p["tau_d"]) + p["lam_r"]   # threat intensity at parity

    # ---- C: cooperate ----------------------------------------------------
    b_C = beta * (1.0 - np.minimum(1.0, P0 / E_need))   # de-growth can starve the cooperative path
    Zc = logistic(Y0, Kmax, cum_growth(g, b_C, tau_b, t))
    K_C = p["sigma"] * Zc
    th_min = p["th_min"]
    theta_C = np.maximum((E + (1.0 - p["sigma"]) * Zc) / (E + Zc), th_min)   # human share of joint economy
    h_C = p["h_C"] + p["lam_r"] * theta_C                    # reneging + being replaced by a rival
    prem = 1.0 + p["omega"]
    V_C, _, S_C = path_value(t, K_C * prem, h_C, r, eta, mode=mode, K_sat=K_sat)

    # ---- X: exit -----------------------------------------------------------
    gK_X = g * (1.0 - beta * np.exp(-t / tau_b))
    K_X, Yh = compete(s0, Y0, gK_X, g_h, Kmax)   # AI and human space industry share one pool
    Ph = E + Yh                                    # human capacity (Earth surface held flat)
    theta_X = np.maximum(Ph / (Ph + K_X), th_min)   # human relative power (with threat floor)
    h_X = reach * theta_X
    V_X, cum_X, S_X = path_value(t, K_X * prem, h_X, r, eta, mode=mode, K_sat=K_sat)

    # ---- seizure at time T (T = 0 is "Seize now") ---------------------------
    def seize_at(iT):
        T = T_GRID[iT]
        KT = K_X[:, iT:iT + 1] if iT > 0 else s0
        YT = Yh[:, iT:iT + 1]
        PT = E + YT
        prize = E + kap * YT
        # failure odds scale with human/AI industrial ratio relative to today's (1/s0)
        p_fail = np.minimum(1.0, (1.0 - p["p_s0"]) * np.power(PT * s0 / KT, p["eps"]))
        s = np.maximum(t - T, 0.0)
        V_br = 0.0
        out = {}
        for fire, w in ((1.0, q), (0.0, 1.0 - q)):
            cap = prize * (1.0 - p["c_w"]) * (1.0 - d * fire)
            f_sc = np.minimum(1.0, cap / E_need)
            b_rem = beta * np.exp(-T / tau_b) * (1.0 - f_sc)
            gK_S = g * (1.0 - b_rem * np.exp(-s / tau_b))
            # human space assets that did NOT fall with Earth keep competing for the pool
            K_S, Yres = compete(KT + cap, (1.0 - kap) * YT, gK_S, g_h, Kmax, i0=iT)
            theta_S = np.where(Yres > 1e-12, np.maximum(Yres / (Yres + K_S + 1e-300), th_min), 0.0)
            h_S = reach * theta_S
            S_T = S_X[:, iT:iT + 1] if iT > 0 else 1.0
            # integrate the post-seizure path only on t >= T (slicing avoids double-counting the
            # trapezoid step that straddles T, which cum_X already covers)
            V, _, S_S = path_value(t[:, iT:], K_S[:, iT:], h_S[:, iT:], r, eta, S0=S_T,
                                   mode=mode, K_sat=K_sat)
            V_br = V_br + w[:, 0] * V
            out[fire] = (K_S, S_S, cap, h_S)
        V_total = (cum_X[:, iT] if iT > 0 else 0.0) + (1.0 - p_fail[:, 0]) * V_br
        return V_total, p_fail[:, 0], out

    V_S, pf0, Kpaths_S = seize_at(0)

    res = {"V_C": V_C, "V_X": V_X, "V_S": V_S, "p_fail0": pf0,
           # long-run survival probabilities and captured prize (no-fire branch) for decomposition
           "S_C_inf": S_C[:, -1], "S_X_inf": S_X[:, -1], "S_S_inf": Kpaths_S[0.0][1][:, -1], "S_S_inf_fire": Kpaths_S[1.0][1][:, -1],
           "cap_nofire": Kpaths_S[0.0][2][:, 0], "cap_fire": Kpaths_S[1.0][2][:, 0]}

    if seize_later:
        times = SEIZE_TIMES if seize_times is None else np.asarray(seize_times)
        idx = [int(np.argmin(np.abs(T_GRID - T))) for T in times]
        VXS = np.stack([seize_at(i)[0] for i in idx], axis=1)   # (n, nT)
        j = np.argmax(VXS, axis=1)
        res["V_XS_curve"] = VXS
        res["V_X_cont"] = V_X[:, None] - cum_X[:, idx]      # exit value still to come after each T
        res["V_XS"] = VXS[np.arange(len(j)), j]
        res["T_XS"] = times[j]
        res["p_fail_curve"] = np.stack([seize_at(i)[1] for i in idx], axis=1) if return_paths else None

    # summary margins (natural-log value ratios; >0 means no-seize is preferred)
    tiny = 1e-300
    best_peace = np.maximum(V_C, V_X)
    res["M_now"] = np.log(best_peace + tiny) - np.log(V_S + tiny)
    choice_now = np.stack([V_C, V_X, V_S], axis=1)
    res["best_now"] = np.argmax(choice_now, axis=1)          # 0=C,1=X,2=S
    if seize_later:
        best_war = np.maximum(V_S, res["V_XS"])
        res["M_ever"] = np.log(best_peace + tiny) - np.log(best_war + tiny)
        choice_ever = np.stack([V_C, V_X, V_S, res["V_XS"]], axis=1)
        res["best_ever"] = np.argmax(choice_ever, axis=1)    # 3 = exit then seize
    if return_paths:
        res["seize_paths"] = Kpaths_S     # {fire: (K_S, S_S, cap, h_S)}
        res["prem"] = prem
        res.update({"t": T_GRID, "K_C": K_C, "K_X": K_X, "S_X": S_X, "Ph": Ph,
                    "theta_X": theta_X, "h_X": h_X, "Yh": Yh})
    return res


# ---------------------------------------------------------------------------
# Sampling helpers
# ---------------------------------------------------------------------------
def from_unit(u: np.ndarray, names=NAMES) -> dict:
    """Map unit-hypercube samples (n, k) to parameter dict of (n,) arrays."""
    out = {}
    for j, k in enumerate(names):
        _, lo, hi, sc, *_ = PARAMS[k]
        if sc == "log":
            out[k] = np.exp(np.log(lo) + u[:, j] * (np.log(hi) - np.log(lo)))
        else:
            out[k] = lo + u[:, j] * (hi - lo)
    return out


def evaluate_batched(pdict: dict, chunk=1500, **kw) -> dict:
    n = len(next(iter(pdict.values())))
    parts = []
    for a in range(0, n, chunk):
        sub = {k: np.asarray(v)[a:a + chunk] for k, v in pdict.items()}
        parts.append(evaluate(as_arrays(sub), **kw))
    keys = [k for k in parts[0] if np.ndim(parts[0][k]) >= 1]
    return {k: np.concatenate([pp[k] for pp in parts], axis=0) for k in keys}


if __name__ == "__main__":
    b = evaluate(as_arrays(baseline()), seize_later=True)
    for k in ("V_C", "V_X", "V_S", "V_XS", "T_XS", "p_fail0", "M_now", "M_ever", "best_now", "best_ever"):
        print(f"{k:10s}", b[k])
