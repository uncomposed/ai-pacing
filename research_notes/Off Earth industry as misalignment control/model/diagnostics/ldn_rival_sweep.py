"""Follow-up 2026-10-21, item 3: draws 51 and 56 of the r0.1 box, sweeping detection speed L_dn and the rival hazard mu. Pads each solve with its original batch's largest draw so the A grid matches the cache. Run from model/ (about 3 min)."""
import os, sys, time, numpy as np
sys.path.insert(0, os.getcwd())
import equilibrium_model as em, robust_design as rd
_, th = rd.ensemble("r0.1", rd.N_RAD, seed=105)
groups = rd.batches_for(th)
for i in (51, 56):
    g = [gg for gg in groups if i in gg][0]
    top = lambda k: th[k]["Kmax"] * (1 + th[k]["f_E"])
    pad = max(g, key=top)
    print(f"draw {i}: batch {list(g)}  pad draw {pad}  own top {top(i):.3g}  batch top {top(pad):.3g}")
    sets, lab = [], []
    for ldn in (0.0, 0.01, 0.03, 0.1):
        for mm in (0.0, 0.25, 0.5, 1.0, 2.0):
            p = rd.apply_design(th[i], {}); p["L_dn"] = ldn; p["mu"] = p["mu"] * mm
            if mm == 0: p["beta_bg"] = 0.0
            sets.append(p); lab.append((ldn, mm))
    sets.append(rd.apply_design(th[pad], {}))
    t0 = time.time()
    r = em.solve(em.batch([em.baseline(**p) for p in sets]), N=2, T_H=300, nA=160)
    for j, (ldn, mm) in enumerate(lab):
        print(f"  L_dn {ldn:4.2f} mu x{mm:4.2f}  act0 {r['act0'][j]} P(strike) {r['att'][j]:.3f} P(succ) {r['suc'][j]:.3f} P(rival) {r['riv'][j]:.3f} yr {r['tatt'][j]:5.1f} WH {r['WH'][j]:.3f}")
    print(f"  ({time.time()-t0:.0f}s)")
