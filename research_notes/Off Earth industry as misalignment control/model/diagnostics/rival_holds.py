"""Follow-up 2026-10-21, item 1: rescore every cached run with a rival-aware 'holds' (also require P(rival) < 0.5, or < 0.1). Reads the cache only. Run from model/."""
import os, sys, glob, numpy as np
sys.path.insert(0, os.getcwd())
R = "results/robust_runs"
def load(p):
    z = np.load(p); return {k: z[k] for k in z.files}
def h_old(r): return np.isin(r["act0"], ["C","P"]) & (r["att"] < 0.01)
def h_new(r, th): return h_old(r) & (r["riv"] < th)
best = "D_mult=3_T_reloc=4_d=0.99_q_red=2_seq=1"
for ens in ["r0.1", "near", "full"]:
    print(f"\n=== {ens} ===  holds: old | rival<0.5 | rival<0.1   (n)   mean P(rival) among old-holds")
    rows = []
    for p in sorted(glob.glob(f"{R}/{ens}__*.npz")):
        k = os.path.basename(p)[len(ens)+2:-4]
        r = load(p); n = len(r["att"])
        o = h_old(r); a = h_new(r, .5); b = h_new(r, .1)
        rows.append((k, o.sum(), a.sum(), b.sum(), n, r["riv"][o].mean() if o.any() else np.nan))
    for k,o,a,b,n,mr in sorted(rows, key=lambda x: -x[2]):
        print(f"{k[:70]:70s} {o:4d} {a:4d} {b:4d}  ({n})  {mr:.2f}")
