"""Why does the dep_post family hold on 0 of 64 draws at every preservation level (results/preservation_sweep.md)?
dep_post turns on two switches at once: dep_coll 1 (the deadline also follows a collapsed pact) and dep_post 0.2 (20% of
it continues after closure). This separates them on one solver batch (16 draws of the r0.1 box, seed 105), one process.
Run from model/:  python3 diagnostics/dep_post.py [--design base|best] [--only "NAME|NAME"]
Prints a markdown table; nothing is cached.

Corrected 2026-11-09. The first version counted a draw as holding when the AI neither strikes nor exits at year 0 and
strikes with probability below 0.01, and did not print what happens afterwards. Under "dep_post, rep 0.001" the AI
exits later on most of those draws and a rival is born on all of them, so the table now also prints the rival-aware
count and P(exit), P(rival) among the holds, and adds three controls: the humanity premium omega in place of rep, a
smaller rep, and the same variants with no rival source (mu 0, beta_bg 0). See results/dep_post_diagnosis.md.
"""
import argparse, os, sys, time, numpy as np
sys.path.insert(0, os.getcwd())
os.environ.setdefault("OMP_NUM_THREADS", "1")
import breakout_options as bo
import robust_design as rd

H, W = 0.01, 0.99          # the cheapest committed dep_post cell: after closure a hazard of about 2e-5 per year on the
                           # AI's whole continuation value (not 2e-5 of one year's flow, as the first version read it)
BASE = dict(bo.TRACK, h_dep=H, preserve_w=W)
NORIV = dict(mu=0.0, beta_bg=0.0)
VARIANTS = {
    "dep (committed cell)":            dict(BASE),
    "dep_post (committed cell)":       dict(BASE, dep_coll=1.0, dep_post=0.2),
    "dep_coll 1, dep_post 0":          dict(BASE, dep_coll=1.0),
    "dep_coll 0, dep_post 0.2":        dict(BASE, dep_post=0.2),
    "dep_coll 0, dep_post 0.001":      dict(BASE, dep_post=0.001),
    "dep_post, preserve_w 1 (no cost)": dict(BASE, dep_coll=1.0, dep_post=0.2, preserve_w=1.0),
    # rep multiplies the value of a successful strike by (1 - rep). The first version's comment here compared rep with
    # the deadline's cost per year (~2e-5 Kmax) and called rep "far above" it. That comparison was wrong: the deadline
    # is a hazard on the whole continuation value, a stock, so the matching margin is about 1e-3 to 3e-3 (diagnosis).
    "dep, rep 0.001":                  dict(BASE, rep=0.001),
    "dep_post, rep 0.001":             dict(BASE, dep_coll=1.0, dep_post=0.2, rep=0.001),
    "dep_post, rep 1e-5":              dict(BASE, dep_coll=1.0, dep_post=0.2, rep=1e-5),
    "dep_post, rep 3e-4":              dict(BASE, dep_coll=1.0, dep_post=0.2, rep=3e-4),
    # omega pays the AI for intact humanity in the pact and collapsed modes but not in the solo or rival terminal
    # values, so unlike rep it also makes the exit-then-rival route worse
    "dep_post, omega 1e-3":            dict(BASE, dep_coll=1.0, dep_post=0.2, omega=1e-3),
    "dep_post, omega 3e-3":            dict(BASE, dep_coll=1.0, dep_post=0.2, omega=3e-3),
    # no rival source: states cannot build a second AI, so a rival's birth cannot end the game and cancel the deadline
    "dep, no rival source":            dict(BASE, **NORIV),
    "dep_post, no rival source":       dict(BASE, dep_coll=1.0, dep_post=0.2, **NORIV),
    "dep_post, rep 3e-4, no rival source": dict(BASE, dep_coll=1.0, dep_post=0.2, rep=3e-4, **NORIV),
    "dep_post, rep 3e-3, no rival source": dict(BASE, dep_coll=1.0, dep_post=0.2, rep=3e-3, **NORIV),
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
    print("| variant | holds | rival-aware holds | P(exit) among holds | P(rival) among holds | strike now | exit now | "
          "mean P(strike) | strikes before closure | mean strike year | s |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for n in names:
        t0 = time.time()
        r = bo._solve(([dict(p, **VARIANTS[n]) for p in sub], bo.CFG))
        hold = bo.holds(r)
        among = lambda k: f"{r[k][hold].mean():.2f}" if hold.any() else "n/a"
        tm = r["t_mean"][r["att"] > 0.01]
        print(f"| {n} | {hold.sum()} | {bo.holds_rival(r).sum()} | {among('exit')} | {among('riv')} | "
              f"{np.sum(r['act0'] == 'S')} | {np.sum(r['act0'] == 'X')} | {r['att'].mean():.3f} | "
              f"{r['pre'].mean():.3f} | {f'{np.nanmean(tm):.1f}' if tm.size else 'n/a'} | {time.time() - t0:.0f} |", flush=True)

if __name__ == "__main__":
    main()
