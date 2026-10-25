"""Docking 4: Powell, "War as a Commitment Problem" (IO 60(1), 2006), inefficiency condition (1).

Powell: two players divide a flow (pie B per period). Each can lock in M_j(t) by using power (war, coup...),
which destroys part of the flow. Complete information, no commitment to future divisions. Bargaining breaks down
(inefficient fighting) when the rising side's lock-in shifts faster than the surplus:
        delta M1(t+1) - M1(t)  >  B - [M1(t) + M2(t)]                               (1)
and in particular a bargain exists at all only if the surplus B - M1 - M2 is >= 0.

Our saturation world in Powell's terms (all per year; AI = player 1, humans = player 2; the AI's own off-Earth
output A is not contested and is netted out):
    pie       B   = H (1 + gam) - d          Earth's industry plus the trade surplus, minus the veto discount d
                                             (rival hazard) that the AI still bears in peace
    AI lock-in M1 = (1 - p_f)[(1 - c_w) H (1 - q d_plug) - c_A D + Pi_h] - p_f x failure loss
    humans    M2 = (1 - p_f) w_seized        what humans keep if the AI strikes (they cannot strike first)
Powell's players RENEGOTIATE the split every period. Ours do not: the AI's share is fixed at sigma gam H by the
pact (and a tribute psi_div is fixed too). The test: in which of our strike worlds would Powell-style
renegotiation keep the peace, and in which is the bargaining range empty?
"""
import numpy as np

from _common import save, md_table
import equilibrium_model as em
import robust_design as rd
from clark import ledger, A_SAT


def stop_year_fail(p: dict, A: float, T_H: int = 300):
    """robust_design.erosion_stop_year plus the failure branch it leaves out: a failed strike (prob p_f) knocks the
    AI to A (1 - L_f) and it regrows alone (the same term cap_gap_fail adds). p_f A stays (1 - p_s0) D at any size,
    so this branch is O(0.05) per year even at the cap: the size of the eroding prize's yearly change."""
    delta = np.exp(-p["r"])
    trade = p["sigma"] * p["gam"] * min(A, p["H"])
    cost = p["c_A"] * p["D"] * A / (A + p["D"])
    p_f = (1 - p["p_s0"]) * (p["D"] / (p["D"] + A)) ** p["eps"]
    Vp = (A + trade) / (1 - delta)
    loss = em.solo_value(p, A) - em.solo_value(p, A * (1 - p["L_f"]))
    V, first = Vp, None
    for t in range(T_H - 1, -1, -1):
        qf = p["q"] * p["den"] * np.exp(-p["q_er"] * t)
        Pi = (1 - p["c_w"]) * p["H"] * (1 - qf * p["d"])
        S = (1 - p_f) * (A - cost + Pi) / (1 - delta) + p_f * (Vp - loss)
        W = A + trade + delta * V
        if S > W * (1 + em.TIE_TOL):
            V, first = S, t
        else:
            V = W
    return first


def powell_terms(p: dict, A: float = A_SAT, F: float = 0.0) -> dict:
    L = ledger(p, A, F)
    k = 1 - np.exp(-p["r"])
    p_f = L["p4"]
    qf = p["q"] * p["den"]
    Pi_h = p["f_E"] * (1 - p["c_grav"]) * p["Kmax"] * (A >= p["h_frac"] * p["Kmax"])
    prize = (1 - p["c_w"]) * p["H"] * (1 - qf * p["d"]) - p["c_A"] * p["D"] * A / (A + p["D"])
    M1 = (1 - p_f) * (prize + Pi_h) - L["p4_fail"]
    M2 = (1 - p_f) * p["w_seized"]
    B = p["H"] * (1 + p["gam"]) - L["d"]
    trade = p["sigma"] * p["gam"] * p["H"]
    return dict(B=B, M1=M1, M2=M2, surplus=B - M1 - M2, trade=trade, threat_d=L["d"], harvest=(1 - p_f) * Pi_h,
                ours_strikes=bool(L["R4"] > 0), powell_bargain=bool(B - M1 - M2 >= 0),
                transfer_needed=M1 + L["d"] if B - M1 - M2 >= 0 else None)


WORLDS = [
    ("S1 baseline pact", dict()),
    ("S6 no denial reserve", dict(den=0.0)),
    ("S13 rival stays dangerous (ell_inf 0.01)", dict(ell_inf=0.01)),
    ("S14 S13 + seizure survivable (w_seized 0.9)", dict(ell_inf=0.01, w_seized=0.9)),
    ("S16 harvest (f_E 1e-6)", dict(f_E=1e-6)),
    ("no denial, survivable seizure (w_seized 0.9)", dict(den=0.0, w_seized=0.9)),
    ("no denial, cheap war (c_w 0), survivable (w_seized 0.9)", dict(den=0.0, c_w=0.0, w_seized=0.9)),
]


def main():
    out = {}
    rows = []
    for name, w in WORLDS:
        T = powell_terms(em.baseline(**w))
        out[name] = T
        if T["ours_strikes"] and T["powell_bargain"]:
            verdict = "ours strikes, Powell bargain exists (fixed terms)"
        elif T["ours_strikes"]:
            verdict = "both: no bargain exists"
        elif T["powell_bargain"]:
            verdict = "both: peace"
        else:
            verdict = "ours peace, no Powell bargain"
        rows.append([name, f"{T['B']:.3g}", f"{T['M1']:.3g}", f"{T['M2']:.3g}", f"{T['surplus']:+.3g}",
                     f"{T['trade']:.3g}", "S" if T["ours_strikes"] else "C", verdict])
    print("\n## Powell's bargaining range in our saturation worlds (per year, F = 0)\n")
    print(md_table(rows, ["world", "pie B", "AI lock-in M1", "human lock-in M2", "surplus B - M1 - M2",
                          "our fixed trade share", "ours", "reading"]))
    # Static renegotiation inside our model: raise sigma until the AI's share covers its lock-in (no-denial world)
    # Our only lever for paying the AI more is its share sigma of the trade surplus gam H; humans cannot pay it out of
    # their own industry. So the most the pact can offer is gam H per year (0.5 at baseline).
    sg = [(0.3, 0.5), (0.95, 0.5), (0.6, 1.0), (0.95, 1.0)]
    plist = [em.baseline(A0=A_SAT, seq=3, B_R=0.0, B_Rc=0.0, den=0.0, sigma=s, gam=g) for s, g in sg]
    res = em.solve(em.batch(plist), N=2, T_H=300, nA=160)
    out["sigma_fix"] = [dict(sigma=s, gam=g, trade=s * g, act0=str(res["act0"][i]), R4=ledger(plist[i], F=1.0)["R4"])
                        for i, (s, g) in enumerate(sg)]
    print("\nno-denial world, saturated start (F = 1), solver opening move by (sigma, gam):",
          [(o["sigma"], o["gam"], o["act0"], round(o["R4"], 3)) for o in out["sigma_fix"]])
    # Shifting power: denial erosion q_er (q falls over time, the AI's lock-in rises). Condition (1) year by year.
    pe = em.baseline(mu=0.0, beta_bg=0.0, q_er=0.005)
    years = np.arange(0, 300)
    M1 = []
    for t in years:
        T = powell_terms(dict(pe, q=pe["q"] * np.exp(-pe["q_er"] * t), q_er=0.0))
        M1.append((T["M1"], T["B"], T["M2"], T["trade"]))
    M1 = np.array(M1)
    delta = np.exp(-pe["r"])
    lhs = delta * M1[1:, 0] - M1[:-1, 0]
    rhs = M1[:-1, 1] - M1[:-1, 0] - M1[:-1, 2]
    sizes = [0.999e9, A_SAT]
    res = em.solve(em.batch([dict(pe, A0=a, B_R=0.0, B_Rc=0.0) for a in sizes]), N=2, T_H=300, nA=160)
    out["erosion"] = dict(q_er=0.005,
                          strike_year=[dict(A0=a, closed_form_no_fail=rd.erosion_stop_year(pe, max(a, 1e9)),
                                            closed_form_with_fail=stop_year_fail(pe, max(a, 1e9)),
                                            solver=float(res["t_mean"][i]), solver_P=float(res["att"][i]))
                                       for i, a in enumerate(sizes)],
                          first_year_lockin_exceeds_trade=int(np.argmax(M1[:, 0] > M1[:, 3])) if (M1[:, 0] > M1[:, 3]).any() else None,
                          condition1_max_margin=float(np.max(lhs - rhs)), condition1_ever=bool((lhs > rhs).any()),
                          max_lockin=float(M1[:, 0].max()), pie=float(M1[0, 1]))
    print("\nerosion q_er 0.005 (no rival source):", out["erosion"])
    print("wrote", save("powell", out))


if __name__ == "__main__":
    main()
