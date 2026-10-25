"""Follow-up 2026-10-21, item 2: baseline world, kill_pre sweep, with and without d = 1. Run from model/ (about 4 min)."""
import os, sys, time, numpy as np
sys.path.insert(0, os.getcwd())
import equilibrium_model as em
kps = [1.0, 0.95, 0.9, 0.7, 0.5, 0.3, 0.0]
variants = {"retry on (d .9)": dict(), "control d 1": dict(d=1.0), "no retry (d 1, k_rat 1)": dict(d=1.0, k_rat=1.0)}
worlds = {"baseline": dict(), "no temptation B_R 0": dict(B_R=0.0, B_Rc=0.0)}
sets, labels = [], []
for wn, w in worlds.items():
    for vn, v in variants.items():
        for kp in kps:
            sets.append(dict(w, **v, kill_pre=kp)); labels.append((wn, vn, kp))
t0 = time.time()
r = em.solve(em.batch([em.baseline(**s) for s in sets]), N=2, T_H=300, nA=160)
print(f"solved {len(sets)} in {time.time()-t0:.0f}s")
for i, (wn, vn, kp) in enumerate(labels):
    print(f"{wn:22s} {vn:26s} kill_pre {kp:4.2f}  act0 {r['act0'][i]}  P(strike) {r['att'][i]:.2f}  P(succ) {r['suc'][i]:.2f}  P(fail) {r['fail'][i]:.2f}  yr {r['tatt'][i]:5.1f}  WH {r['WH'][i]:.3f}")
