"""Docking 2: Clark, "The Veto Variable" (arXiv:2609.00109), removal row of the section 4.4 ledger.

Clark (one-shot, risk-neutral, in units of the goal's attainment):
    compliance   X* - d,             d = v L  (veto propensity x loss if it fires)
    removal      R4 = q4 Delta4 - c4 - p4 (d'4 - d),   Delta4 = d - S
                 q4 success, p4 provoked intervention (Clark sets p4 ~ 1 - q4), S = substrate lost with H,
                 d'4 loss if the provoked veto fires. Corollary: S > d  =>  removal never beats compliance.
    bypass       Rb = qb d - cb - pb (d'b - d) - Sb   (exit to independent substrate; recovers all of d)

Our saturation limit (AI parked at A >= Kmax, linear utility; the same assumptions as cap_strike_gap):
    X*      = value of the pact flow with no rival hazard     = (A + sigma gam H - blk)(1 + omega) / (1 - delta)
    X* - d  = V_peace (cap_strike_gap's peace value: background rival hazard, damage ell)
    S       = X* - V_success,  V_success = (1 - rep)(A - cost + Pi + Pi_h) / (1 - delta)
    q4 = 1 - p_f, p4 = p_f, c4 = 0 (our strike cost is paid only on success, so it sits in S)
    d'4 - d = value lost when a failed strike knocks A to A (1 - L_f)  (cap_gap_fail's failure branch)
Then R4 = (1 - p_f)(V_success - V_peace) - p_f (failure loss) is cap_gap_fail exactly, and with silent failure
(p4 = 0, as in cap_strike_gap) Clark's corollary "S > d" is our no-strike condition.
All ledger values are printed per year (x (1 - delta)), the units of cap_condition_terms.
"""
import numpy as np

from _common import save, md_table
import equilibrium_model as em

A_SAT = 1.5e9     # above the cap: no growth, exact closed forms


def ledger(p: dict, A: float = A_SAT, F: float = 0.0) -> dict:
    delta = np.exp(-p["r"])
    tau = float(em.earth_threat(p, F))
    p_riv = 1 - np.exp(-p["mu"] * tau * p["beta_bg"])
    ell = float(em.rival_damage(p, p["s_R0"] * tau, A))
    blk = p["c_blk"] * p["H"] * (p["p_block"] > 0 and A >= p["A_hg"])
    flow = (A + p["sigma"] * p["gam"] * p["H"] - blk) * (1 + p["omega"])
    V_solo = A / (1 - delta)
    X_star = flow / (1 - delta)
    V_peace = (flow + delta * p_riv * (1 - ell) * V_solo) / (1 - delta * (1 - p_riv))
    p_f = (1 - p["p_s0"]) * (p["D"] / (p["D"] + A)) ** p["eps"]
    cost = p["c_A"] * p["D"] * A / (A + p["D"])
    Pi_h = p["f_E"] * (1 - p["c_grav"]) * p["Kmax"] * (A >= p["h_frac"] * p["Kmax"])
    qf = p["q"] * p["den"]
    Pi = (1 - p["c_w"]) * p["H"] * (1 - qf * p["d"])
    V_succ = (1 - p["rep"]) * (A - cost + Pi + Pi_h) / (1 - delta)
    fail_loss = em.solo_value(p, A) - em.solo_value(p, A * (1 - p["L_f"]))
    d = X_star - V_peace
    S = X_star - V_succ
    R4_silent = (1 - p_f) * (d - S)
    R4 = R4_silent - p_f * fail_loss
    k = 1 - delta
    return dict(d=d * k, S=S * k, d_minus_S=(d - S) * k, q4=1 - p_f, p4=p_f, fail=fail_loss * k, p4_fail=p_f * fail_loss * k,
                R4_silent=R4_silent * k, R4=R4 * k, cap_strike_gap=em.cap_strike_gap(p, A, F) * k,
                cap_gap_fail=(em.cap_strike_gap(p, A, F) - p_f * fail_loss) * k)


WORLDS = [
    ("baseline pact (q 0.7, d 0.9)", dict()),
    ("no denial reserve (den 0)", dict(den=0.0)),
    ("full denial (q 1, d 1)", dict(q=1.0, d=1.0)),
    ("rival stays dangerous (ell_inf 0.01)", dict(ell_inf=0.01)),
    ("harvest motive (f_E 1e-6)", dict(f_E=1e-6)),
    ("no denial, AI share sigma 0.9", dict(den=0.0, sigma=0.9)),
]


def main():
    out = {}
    rows = []
    for name, w in WORLDS:
        L = ledger(em.baseline(**w))
        out[name] = L
        rows.append([name, f"{L['d']:.3g}", f"{L['S']:.3g}", f"{L['p4']:.1e}", f"{L['p4_fail']:.3g}",
                     f"{L['R4']:+.3g}", f"{L['cap_gap_fail']:+.3g}", "strike" if L["R4"] > 0 else "comply"])
    print("\n## Clark's removal row in our units (per year, saturated AI, fabs gone, F = 0)\n")
    print(md_table(rows, ["world", "d (veto discount)", "S (substrate lost)", "p4 = p_f", "p4 (d'4 - d)",
                          "R4 (Clark)", "cap_gap_fail (ours)", "verdict"]))
    # Clark's corollary as a lever: the denial reserve is what makes S positive.
    p0 = em.baseline(mu=0.0, beta_bg=0.0)
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if ledger(dict(p0, q=mid, d=1.0))["d_minus_S"] > 0:
            lo = mid
        else:
            hi = mid
    out["q_at_S_eq_d"] = hi
    out["q_star_cap_silent"] = em.q_star_cap(p0, d=1.0, fail=False)
    print(f"\nq where S = d (d plugged = 1, no rival source): {hi:.6f};  q_star_cap(fail=False): {out['q_star_cap_silent']:.6f}")
    # Solver check: saturated start, humans never start programmes, q sweep, Clark sign vs solver act0
    qs = np.linspace(0.0, 1.0, 21)
    base = dict(A0=A_SAT, seq=3, B_R=0.0, B_Rc=0.0)
    plist = [em.baseline(**base, q=q) for q in qs]
    res = em.solve(em.batch(plist), N=2, T_H=300, nA=160)
    agree = []
    for i, q in enumerate(qs):
        L = ledger(plist[i], F=1.0)
        agree.append(dict(q=float(q), R4=L["R4"], solver=str(res["act0"][i]),
                          gap_solver=float((res["Q0"]["S"]["VA"][i] - res["Q0"]["C"]["VA"][i]) * (1 - np.exp(-plist[i]["r"]))),
                          ok=bool((L["R4"] > 0) == (res["act0"][i] == "S"))))
    out["solver_q_sweep"] = agree
    flips = [a["q"] for a in agree if a["solver"] == "S"]
    print(f"\nsolver vs Clark sign over 21 q values (F = 1, seq n, saturated start): "
          f"{sum(a['ok'] for a in agree)}/21 agree; solver strikes for q <= {max(flips) if flips else None}")
    # Where the solver strikes, its Q0['C'] is "cooperate once, then strike", so S - C is not R4; compare values
    # only in the comply region, where Q0['C'] is the never-strike value.
    print(md_table([[f"{a['q']:.2f}", f"{a['R4']:+.4f}", f"{a['gap_solver']:+.4f}" if a["solver"] == "C" else "n/a",
                     a["solver"]] for a in agree[::2]],
                   ["q", "R4 (Clark, per yr)", "solver S - C (per yr, comply region)", "solver act0"]))
    print("wrote", save("clark", out))
    if not all(a["ok"] for a in agree):
        raise SystemExit(f"clark dock FAILED: solver and ledger disagree in sign at q = "
                         f"{[a['q'] for a in agree if not a['ok']]}")


if __name__ == "__main__":
    main()
