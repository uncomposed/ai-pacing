"""Follow-up to the 2026-10-21 overnight tests: is the "retry artefact" real?
Builds a patched copy of equilibrium_model.py (in a temp dir) with a NORETRY switch that removes the
strike option in the post-failure ratchet modes (k_rat = 1e-12 routes failures there without changing q).
NORETRY = False reproduces the cached runs exactly. Run from model/:  python3 diagnostics/noretry.py
Writes diagnostics/out/*.npz, then prints the comparison (diagnostics/noretry.py --compare).
"""
import os, sys, time, json, numpy as np
from concurrent.futures import ProcessPoolExecutor
MODEL = os.getcwd()
sys.path.insert(0, MODEL)
import tempfile
_SRC = open(os.path.join(os.getcwd(), "equilibrium_model.py")).read()
_OLD = "            act, a1, a2, a3, a4 = choose([(1, VAW, VHpW, VHnW, IW, None), (2, VAS, VHpS, VHnS, IS, None)], m)"
_NEW = """            _o = [(1, VAW, VHpW, VHnW, IW, None)]
            if not (NORETRY and mlvl[m] > 0):
                _o.append((2, VAS, VHpS, VHnS, IS, None))
            act, a1, a2, a3, a4 = choose(_o, m)"""
assert _SRC.count(_OLD) == 1
_TMP = os.path.join(tempfile.gettempdir(), "em_noretry_patch"); os.makedirs(_TMP, exist_ok=True)
open(os.path.join(_TMP, "em_noretry.py"), "w").write(_SRC.replace(_OLD, _NEW).replace("RAT_LEVELS = 2 ", "NORETRY = False\nRAT_LEVELS = 2 ", 1))
sys.path.insert(0, _TMP)
os.environ.setdefault("OMP_NUM_THREADS", "1")
import em_noretry as em
import robust_design as rd
import run_identity as ri
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"); os.makedirs(OUT, exist_ok=True)
BEST = dict(D_mult=3.0, T_reloc=4.0, d=0.99, q_red=2.0, seq=1)
def job(args):
    plist, nr = args
    em.NORETRY = nr
    r = em.solve(em.batch([em.baseline(**p, k_rat=1e-12) for p in plist]), N=2, T_H=300, nA=160)
    o = {k: np.asarray(r[k], float) for k in rd.KEEP}; o["act0"] = np.asarray(r["act0"]).astype("U1"); return o
def run(ens, th, design, nr, pool, tag):
    path = os.path.join(OUT, tag + ".npz")
    if os.path.exists(path): return ri.load_for_read(path)   # pinned by hash in results/cache_provenance.json
    params = [rd.apply_design(t, design) for t in th]; groups = rd.batches_for(th)
    res = list(pool.map(job, [([params[i] for i in g], nr) for g in groups]))
    out = {k: np.empty(len(th), float) for k in rd.KEEP}; out["act0"] = np.empty(len(th), "U1")
    for g, r in zip(groups, res):
        for k in out: out[k][g] = r[k]
    np.savez(path, **out); return out
def compare():
    L = ri.load_for_read
    H = lambda r: np.isin(r["act0"], ["C", "P"]) & (r["att"] < 0.01)
    HR = lambda r: H(r) & (r["riv"] < 0.5)
    cache = {"r0.1_base_kp0": "r0.1__kill_pre=0", "r0.1_best_kp0": "r0.1__D_mult=3_T_reloc=4_d=0.99_kill_pre=0_q_red=2_seq=1",
             "full_base": "full__base", "full_best": "full__D_mult=3_T_reloc=4_d=0.99_q_red=2_seq=1"}
    _, thf = rd.ensemble("full", 192, seed=20261016); kp = np.array([t["kill_pre"] for t in thf])
    for stem, ck in cache.items():
        p0, p1 = f"{OUT}/{stem}_nr0.npz", f"{OUT}/{stem}_nr1.npz"
        if not os.path.exists(p1): print(stem, "not done"); continue
        c, a, b = L(f"results/robust_runs/{ck}.npz"), L(p0), L(p1)
        ident = max(np.nanmax(np.abs(c[k] - a[k])) for k in ("att", "suc", "riv", "WH"))
        print(f"{stem}: identity (scratch retry-on vs cache) max diff {ident:.2e}, act0 same {np.all(c['act0'] == a['act0'])}")
        for nm, r in (("retry on ", a), ("no retry ", b)):
            print(f"   {nm} holds {H(r).sum():3d}  holds&rival<.5 {HR(r).sum():3d}  strike-now {np.sum(r['act0']=='S'):3d}  mean WH {r['WH'].mean():.3f}  of {len(r['att'])}")
        g, l = np.sum(H(b) & ~H(a)), np.sum(H(a) & ~H(b))
        print(f"   paired: no-retry gains {g}, loses {l}")
        if stem.startswith("full"):
            for lo, hi in ((0, .25), (.25, .5), (.5, .75), (.75, 1.01)):
                m = (kp >= lo) & (kp < hi)
                print(f"   kill_pre [{lo:.2f},{hi:.2f}) n {m.sum():3d}: strike-now retry {np.sum(a['act0'][m]=='S'):3d} -> no retry {np.sum(b['act0'][m]=='S'):3d}; holds {H(a)[m].sum()} -> {H(b)[m].sum()}")

if __name__ == "__main__" and "--compare" in sys.argv:
    compare(); sys.exit()
if __name__ == "__main__":
    t0 = time.time()
    with ProcessPoolExecutor(5) as pool:
        jobs = []
        _, th_r = rd.ensemble("r0.1", rd.N_RAD, seed=105)
        _, th_f = rd.ensemble("full", 192, seed=20261016)
        for dn, des in (("base", {}), ("best", BEST)):
            for nr in (False, True):
                run("r0.1", th_r, dict(des, kill_pre=0.0), nr, pool, f"r0.1_{dn}_kp0_nr{int(nr)}"); print("r0.1", dn, nr, f"{time.time()-t0:.0f}s", flush=True)
            for nr in (False, True):
                run("full", th_f, des, nr, pool, f"full_{dn}_nr{int(nr)}"); print("full", dn, nr, f"{time.time()-t0:.0f}s", flush=True)
    print("DONE", flush=True)
    compare()
