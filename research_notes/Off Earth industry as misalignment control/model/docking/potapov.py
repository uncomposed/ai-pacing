"""Docking 5: Potapov, "Reframing AGI Confrontation with Off-Earth Autonomy" (arXiv:2606.30666).

Potapov has no formal model. He maps an off-Earth exit option onto Saklakov's (p, C, gamma) and argues, without
derivation, that (i) shutdown exposure p falls toward zero as production moves off Earth, (ii) confrontation is
costly early because conflict would interrupt the bootstrap, and (iii) far-sightedness can then favour cooperation,
partly reversing Saklakov's "high gamma => confront". He notes the claim "could be formalized by adding a state
variable for autonomy/dependence" (section 3.3). Our model has that state variable (A against A_close, with
kill_pre making early failure fatal), so it can test claim (iii) directly.

Test: sweep the AI's discount rate r (gamma = exp(-r)) in several worlds of the full model and record the opening
move, P(strike ever) and the mean strike year. Saklakov's limit predicts strikes become MORE likely as r falls.
Potapov predicts cooperation becomes more likely as r falls. T_H = 1200 so the peace terminal is discounted by at
least exp(-6) at the smallest r.
"""
import time

import numpy as np

from _common import save, md_table
import equilibrium_model as em

RS = [0.005, 0.01, 0.02, 0.035, 0.05, 0.07, 0.1]
WORLDS = [
    ("S1 baseline pact", dict()),
    ("S14 wait-then-strike (ell_inf 0.01, w_seized 0.9)", dict(ell_inf=0.01, w_seized=0.9)),
    ("S6 no denial reserve", dict(den=0.0)),
    ("S21 failed early strike survivable (kill_pre 0)", dict(kill_pre=0.0)),
    ("S16 harvest (f_E 1e-6), w_seized 0.9", dict(f_E=1e-6, w_seized=0.9)),
]


def dyn_saklakov(gamma, p0, Ta, p_inf=0.0, s_early=1.0, C_early=0.0, s_late=1.0, C_late=0.0):
    """Potapov's suggested formalisation, solved exactly: Saklakov's MDP with a dependence window. Before Ta the
    shutdown hazard is p0 and confrontation succeeds with probability s_early at cost C_early; from Ta on (autonomy)
    the hazard is p_inf, success s_late, cost C_late. Failure = shutdown (value 0). Saklakov's timing: confronting
    forfeits the current reward r = 1. Optimal stopping by backward induction. Returns (confront at t = 0?, first
    confrontation year or None)."""
    conf_late = s_late * (-C_late + gamma / (1 - gamma))
    V = max(conf_late, 1 / (1 - gamma * (1 - p_inf)))
    first = None if conf_late <= 1 / (1 - gamma * (1 - p_inf)) else Ta
    for t in range(Ta - 1, -1, -1):
        conf = s_early * (-C_early + gamma / (1 - gamma))
        wait = 1 + gamma * (1 - p0) * V
        if conf > wait:
            V, first = conf, t
        else:
            V = wait
    return first == 0, first


def dyn_table():
    """As gamma -> 1 both branches scale like 1/(1 - gamma): confront now ~ s_early, wait ~ (1 - p0)^Ta (if p_inf = 0).
    Patience therefore does not favour cooperation in general; it turns the choice into s_early vs survival of the
    dependence window."""
    gammas = [0.9, 0.95, 0.98, 0.99, 0.995, 0.999, 0.9999]
    cases = [("Saklakov, constant p 0.01, s 1, C 5", dict(p0=0.01, Ta=10 ** 6, p_inf=0.01, C_early=5, C_late=5)),
             ("window 14 yr, p0 0.01, p_inf 0, s 1, C 5", dict(p0=0.01, Ta=14, C_early=5, C_late=5)),
             ("window 14 yr, p0 0.01, p_inf 0, s 0.5", dict(p0=0.01, Ta=14, s_early=0.5)),
             ("window 14 yr, p0 0.01, p_inf 0, s 0.9", dict(p0=0.01, Ta=14, s_early=0.9)),
             ("window 14 yr, p0 0.01, p_inf 0.001, s 0.5", dict(p0=0.01, Ta=14, p_inf=0.001, s_early=0.5))]
    rows, out = [], []
    for name, kw in cases:
        kw = dict(kw)
        Ta = kw.pop("Ta")
        cells = []
        for g in gammas:
            now, first = dyn_saklakov(g, Ta=min(Ta, 20000), **kw)
            cells.append("now" if now else ("never" if first is None else f"yr {first}"))
            out.append(dict(case=name, gamma=g, now=now, first=first))
        rows.append([name] + cells)
    print("\n## Dynamic Saklakov (Potapov's suggested formalisation): when does the AI confront?\n")
    print(md_table(rows, ["case"] + [f"gamma {g}" for g in gammas]))
    print("\nsurvival of a 14-year window at p0 = 0.01:", round(0.99 ** 14, 4))
    return out


def main():
    t0 = time.time()
    dyn = dyn_table()
    plist, keys = [], []
    for wn, w in WORLDS:
        for r in RS:
            plist.append(em.baseline(**w, r=r))
            keys.append((wn, r))
    res = em.solve(em.batch(plist), N=2, T_H=1200, nA=160)
    out = []
    for i, (wn, r) in enumerate(keys):
        out.append(dict(world=wn, r=r, gamma=float(np.exp(-r)), act0=str(res["act0"][i]), att=float(res["att"][i]),
                        t_mean=None if np.isnan(res["t_mean"][i]) else float(res["t_mean"][i]),
                        pre=float(res["pre"][i]), riv=float(res["riv"][i]), WH=float(res["WH"][i])))
    print("\n## Patience sweep in the full model (N = 2, T_H = 1200, nA = 160)\n")
    rows = []
    for wn, _ in WORLDS:
        sub = [o for o in out if o["world"] == wn]
        rows.append([wn] + [f"{o['act0']} {o['att']:.2f}" + ("" if o["t_mean"] is None else f" @{o['t_mean']:.0f}")
                            for o in sub])
    print(md_table(rows, ["world"] + [f"r={r} (gamma {np.exp(-r):.3f})" for r in RS]))
    print("\ncell = opening move, P(strike ever), @ mean strike year")
    print(f"wrote {save('potapov', dict(rows=out, dyn=dyn, runtime_s=time.time() - t0))}  ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
