"""Why does the dep_post family hold on 0 of 64 draws at every preservation level (results/preservation_sweep.md)?
dep_post turns on two switches at once: dep_coll 1 (the deadline also follows a collapsed pact) and dep_post 0.2 (20% of
it continues after closure). This separates them on one solver batch (16 draws of the r0.1 box, seed 105), one process.
Run from model/:  python3 diagnostics/dep_post.py [--design base|best] [--only "NAME|NAME"]
Prints a markdown table; nothing is cached.
"""
import argparse, os, sys, time, numpy as np
sys.path.insert(0, os.getcwd())
os.environ.setdefault("OMP_NUM_THREADS", "1")
import breakout_options as bo
import robust_design as rd

H, W = 0.01, 0.99          # the cheapest committed dep_post cell: retirement cost about 2e-5 per year after closure
BASE = dict(bo.TRACK, h_dep=H, preserve_w=W)
VARIANTS = {
    "dep (committed cell)":            dict(BASE),
    "dep_post (committed cell)":       dict(BASE, dep_coll=1.0, dep_post=0.2),
    "dep_coll 1, dep_post 0":          dict(BASE, dep_coll=1.0),
    "dep_coll 0, dep_post 0.2":        dict(BASE, dep_post=0.2),
    "dep_coll 0, dep_post 0.001":      dict(BASE, dep_post=0.001),
    "dep_post, preserve_w 1 (no cost)": dict(BASE, dep_coll=1.0, dep_post=0.2, preserve_w=1.0),
    # at the cap the strike/peace gap is O(1) capacity unit against values O(Kmax/r); rep puts a margin of rep * Kmax
    # per year on peace, far above the post-closure deadline cost p_dep * dep_post * (1 - preserve_w) * Kmax ~ 2e-5 Kmax
    "dep, rep 0.001":                  dict(BASE, rep=0.001),
    "dep_post, rep 0.001":             dict(BASE, dep_coll=1.0, dep_post=0.2, rep=0.001),
    "dep_post, rep 1e-5":              dict(BASE, dep_coll=1.0, dep_post=0.2, rep=1e-5),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", default="base", choices=list(bo.DESIGNS))
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    _, th = rd.ensemble("r0.1", 64, seed=105)
    g = rd.batches_for(th)[0]
    sub = [rd.apply_design(th[i], bo.DESIGNS[a.design]) for i in g]
    names = [n for n in VARIANTS if not a.only or n in a.only.split("|")]
    print(f"{a.design} design, {len(sub)} draws (batch 0 of r0.1, seed 105), h_dep {H}, preserve_w {W} unless stated\n")
    print("| variant | holds | strike now | exit now | mean P(strike) | strikes before closure | mean strike year | s |")
    print("|---|---|---|---|---|---|---|---|")
    for n in names:
        t0 = time.time()
        r = bo._solve(([dict(p, **VARIANTS[n]) for p in sub], bo.CFG))
        hold = np.isin(r["act0"], ["C", "P"]) & (r["att"] < 0.01)
        tm = r["t_mean"][r["att"] > 0.01]
        print(f"| {n} | {hold.sum()} | {np.sum(r['act0'] == 'S')} | {np.sum(r['act0'] == 'X')} | {r['att'].mean():.3f} | "
              f"{r['pre'].mean():.3f} | {np.nanmean(tm) if tm.size else float('nan'):.1f} | {time.time() - t0:.0f} |", flush=True)


if __name__ == "__main__":
    main()
