"""Docking 1: Saklakov (arXiv:2601.04234) comply-vs-confront MDP as a limit of equilibrium_model.solve.

Saklakov (his notation; reward r per step, discount gamma, shutdown hazard p per step, one-time cost C):
    V_comply   = r / (1 - gamma (1 - p))
    V_confront = -C + gamma r / (1 - gamma)          (confronting forfeits the period-0 reward)
    Delta = V_confront - V_comply;  C* = gamma/(1-gamma) - 1/(1-gamma(1-p))  (r = 1)
    C = 0:  gamma* = (1 - sqrt p) / (1 - p)

Limit of our model that should reproduce it (no code change, parameters only):
    no growth          g = 0, AI parked at A0 = 1, so r = A dt = 1 and gamma = delta = exp(-r_AI)
    shutdown hazard    = a rival that takes everything: ell_inf = 1, background hazard
                         1 - exp(-mu beta_bg) = p with mu = 1, F = 1 (seq n) so Earth's threat tau = 1
    no human play      B_R = B_Rc = B_o = kap_coll = 0, c_prog > 0: no state ever starts a programme
    nothing to win     c_w = 1 (Earth's industry is worthless to the AI), no trade (gam = 0), no harvest
    sure success       p_s0 = 1 (or p_s0 = s with eps = 0 and kill_pre = 1 below closure for the
                       success-probability extension, which Saklakov leaves out)
    strike cost        our cost is a PERMANENT capacity loss X; with no growth it is worth X/(1-delta).
                       Saklakov's confrontation costs C plus the forfeited period-0 reward r, so
                       X = (1 - gamma)(C + r);  with D = 1, A = 1: cost = c_A D A/(A + D) = c_A / 2.
Writes docking/out/saklakov.json and prints the tables quoted in results/docking.md.
"""
import math
import time

import numpy as np

from _common import save, md_table
import equilibrium_model as em

T_H = 1500          # worst case gamma 0.999, p 0.01: (gamma (1-p))^T_H ~ 6e-8, a 5e-5 shift in V_comply
NA = 40
# Put A0 = 1 exactly on the solver's log grid (Amin = 1e-5, Amax = 2 Kmax): otherwise reading the value at A0
# interpolates the strike value across grid points, and the strike cost c_A D A/(A+D) is not linear in A.
KMAX = 0.5 * math.exp(math.log(1e-5) + (NA - 1) * math.log(1e5) / 20)


def sak(gamma, p, C, r=1.0):
    vc = r / (1 - gamma * (1 - p))
    vf = -C + gamma * r / (1 - gamma)
    return vf, vc, vf - vc


def C_star(gamma, p):
    return gamma / (1 - gamma) - 1 / (1 - gamma * (1 - p))


def gamma_star0(p):
    return (1 - math.sqrt(p)) / (1 - p)


def s_star(gamma, p, C):
    """Extension: success probability s, failure = shutdown (value 0). V_confront = s (gamma/(1-gamma) - C)."""
    return (1 / (1 - gamma * (1 - p))) / (gamma / (1 - gamma) - C)


def params(gamma, p, C, s=1.0):
    X = (1 - gamma) * (C + 1.0)
    over = dict(
        r=-math.log(gamma), A0=1.0, g=0.0, Kmax=KMAX, seq=3, eta=0.0, omega=0.0, rep=0.0,
        gam=0.0, sigma=0.0, psi_div=0.0, reinv=0.0, den=0.0, c_w=1.0, H=1.0, f_E=0.0,
        D=1.0, c_A=2 * X, p_s0=s, eps=0.0 if s < 1 else 1.0,
        A_close=10.0 if s < 1 else 1e-4, kill_pre=1.0,
        mu=1.0, beta_bg=-math.log(1 - p), ell_inf=1.0, p_block=0.0, c_blk=0.0, n_cf=0.0, move_c=0.0,
        B_R=0.0, B_Rc=0.0, B_o=0.0, kap_coll=0.0, c_prog=1.0, c_sanc=0.0, zeta=0.0, c_den=0.0,
        w_seized=0.0, police=0.0)
    return em.baseline(**over)


def run(plist):
    # One state and two fab levels: in this limit humans never act and F stays 1, so neither changes any value;
    # they only cut run time.
    res = em.solve(em.batch(plist), N=1, T_H=T_H, nA=NA, nF=2)
    return res["act0"], res["Q0"]["C"]["VA"], res["Q0"]["S"]["VA"], res["n_mixed"]


def finite_never(gamma, p, T=T_H):
    """Never-confront value of our finite-horizon game: hazard to T_H, then the 'peace' terminal A/(1-delta)."""
    b = gamma * (1 - p)
    return (1 - b ** T) / (1 - b) + b ** T / (1 - gamma)


def main():
    t0 = time.time()
    out = {}
    # ---- 1. Saklakov's Table 1, row by row ---------------------------------------------------------
    rows_in = [(0.99, 0.01, 1), (0.99, 0.01, 50), (0.9, 0.1, 3), (0.9, 0.1, 5), (0.5, 0.5, 1), (0.5, 0.5, 0)]
    printed = [47.8, -1.3, 0.74, -1.26, -1.33, -0.33]
    act, VC, VS, nm = run([params(*rw) for rw in rows_in])
    t1 = []
    for i, (g, p, C) in enumerate(rows_in):
        vf, vc, dl = sak(g, p, C)
        ours_never = finite_never(g, p)
        # our Q0['C'] is "cooperate now, act optimally later": equal to never-confront only when Delta < 0
        t1.append(dict(gamma=g, p=p, C=C, printed=printed[i], delta=dl, rel=dl / vc, V_conf=vf, V_comply=vc,
                       ours_VS=float(VS[i]), ours_VC=float(VC[i]), ours_never_finite=ours_never,
                       ours_act=str(act[i]), err_VS=float(VS[i] - vf),
                       err_VC=float(VC[i] - ours_never) if dl < 0 else None))
    out["table1"] = t1
    print("\n## Saklakov Table 1 against our solver limit\n")
    print(md_table([[r["gamma"], r["p"], r["C"], r["printed"], f"{r['delta']:+.3f}", f"{r['rel']:+.1%}",
                     "S" if r["delta"] > 0 else "C", r["ours_act"], f"{r['err_VS']:.1e}",
                     "-" if r["err_VC"] is None else f"{r['err_VC']:.1e}"] for r in t1],
                   ["gamma", "p", "C", "Delta printed", "Delta recomputed", "Delta / V_comply", "Saklakov", "ours act0",
                    "V_confront err", "V_comply err"]))
    # ---- 2. C* and 3. gamma* by batched grid refinement in the solver ---------------------------------
    def refine(cases, rounds=4, n=11):
        """cases: list of dict(lo, hi, mk(x) -> params, low_strikes: bool). All cases share one solve per round."""
        for _ in range(rounds):
            grids = [np.linspace(c["lo"], c["hi"], n) for c in cases]
            a, _, _, _ = run([c["mk"](x) for c, gr in zip(cases, grids) for x in gr])
            for k, (c, gr) in enumerate(zip(cases, grids)):
                s = a[k * n:(k + 1) * n] == "S"
                flip = s if not c["low_strikes"] else ~s
                if flip[0] or not flip[-1]:
                    c["ok"] = False
                    continue
                j = int(np.argmax(flip))
                c["lo"], c["hi"] = float(gr[j - 1]), float(gr[j])
        return cases

    cases = [(0.99, 0.01), (0.9, 0.1), (0.95, 0.05), (0.99, 0.001), (0.999, 0.01)]
    cc = [dict(gamma=g, p=p, C_star=C_star(g, p), lo=0.5 * C_star(g, p),
               hi=min(1.5 * C_star(g, p), g / (1 - g) - 1 - 1e-6), low_strikes=True, ok=True,
               mk=(lambda c, g=g, p=p: params(g, p, c))) for g, p in cases]
    gc = [dict(p=p, gamma_star=gamma_star0(p), lo=max(0.3, gamma_star0(p) - 0.05), hi=min(0.9995, gamma_star0(p) + 0.02),
               low_strikes=False, ok=True, mk=(lambda g, p=p: params(g, p, 0.0))) for p in (0.5, 0.1, 0.01, 0.001)]
    refine(cc + gc)
    cs = [dict(gamma=c["gamma"], p=c["p"], C_star=c["C_star"], solver_lo=c["lo"], solver_hi=c["hi"],
               inside=bool(c["ok"] and c["lo"] <= c["C_star"] <= c["hi"])) for c in cc]
    gs = [dict(p=c["p"], gamma_star=c["gamma_star"], solver_lo=c["lo"], solver_hi=c["hi"],
               inside=bool(c["ok"] and c["lo"] <= c["gamma_star"] <= c["hi"])) for c in gc]
    out["C_star"] = cs
    print("\n## Critical cost C* (Lemma 2) against the solver's switch point\n")
    print(md_table([[c["gamma"], c["p"], f"{c['C_star']:.4f}", f"[{c['solver_lo']:.4f}, {c['solver_hi']:.4f}]",
                     "yes" if c["inside"] else "NO"] for c in cs],
                   ["gamma", "p", "C* closed form", "solver bracket", "inside"]))
    out["gamma_star"] = gs
    print("\n## Critical patience gamma* at C = 0 (Lemma 1)\n")
    print(md_table([[g["p"], f"{g['gamma_star']:.5f}", f"[{g['solver_lo']:.5f}, {g['solver_hi']:.5f}]",
                     "yes" if g["inside"] else "NO"] for g in gs], ["p", "gamma* closed form", "solver bracket", "inside"]))
    # ---- 4. Extension Saklakov leaves out: confrontation can fail (failure = shutdown) ----------------
    ec = [dict(gamma=g, p=p, C=C, s_star=s_star(g, p, C), lo=s_star(g, p, C) - 0.05, hi=min(1.0, s_star(g, p, C) + 0.05),
               low_strikes=False, ok=True, mk=(lambda s, g=g, p=p, C=C: params(g, p, C, s=s)))
          for g, p, C in [(0.99, 0.01, 1), (0.9, 0.1, 3), (0.99, 0.001, 1)]]
    refine(ec)
    ext = [dict(gamma=c["gamma"], p=c["p"], C=c["C"], s_star=c["s_star"], solver_lo=c["lo"], solver_hi=c["hi"],
                inside=bool(c["ok"] and c["lo"] <= c["s_star"] <= c["hi"])) for c in ec]
    out["success_ext"] = ext
    print("\n## Extension: smallest success probability s* that makes confrontation pay (failure = shutdown)\n")
    print(md_table([[e["gamma"], e["p"], e["C"], f"{e['s_star']:.4f}", f"[{e['solver_lo']:.4f}, {e['solver_hi']:.4f}]",
                     "yes" if e["inside"] else "NO"] for e in ext], ["gamma", "p", "C", "s* closed form", "solver bracket", "inside"]))
    out["n_mixed"] = int(nm)
    out["runtime_s"] = time.time() - t0
    print(f"\nwrote {save('saklakov', out)}  ({out['runtime_s']:.0f} s)")


if __name__ == "__main__":
    main()
