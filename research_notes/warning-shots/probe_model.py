"""Probing before a strike: a toy stopping problem (research note, not specification).

One AI does not know its odds of a successful strike. They are high (pH) or low (pL), with prior pi0 on high.
Each period it can strike (win 1 with its true odds, else 0: a failed strike is fatal), stand down for good (value w),
or probe. A probe returns a signal that is right with probability acc; the AI cannot tell a wrong signal from a right
one. Each probe is detected with probability q; a detected probe ends the game for the AI at value c and counts as a
warning to humans. Signals are symmetric, so the belief depends only on d = (high signals) - (low signals).

generations() chains this game: each generation is more capable (log-odds + gamma per generation) and each earlier
warning hardens defences (log-odds - rho per warning). Generations do not plan for their successors.

Decoys (solve_decoy): a share `decoy` of probes hit a planted target. A decoy looks like a real weakness, so it
returns "high" whatever the truth, and it catches the probe with probability `catch` (1 = tripwire, 0 = it only
misleads). The AI knows the decoy share but not which targets are decoys. Signals are then lopsided, so the state is
the pair (high signals, low signals), with at most N probes.

Arithmetic on assumed inputs. Checked against closed forms in test_probe_model.py. Not empirical.
Run:  python3 probe_model.py          (prints the tables in results/probe_model.md)
"""
import math
import numpy as np

BASE = dict(pH=0.9, pL=0.05, pi0=0.5, acc=0.75, q=0.03, w=0.6, c=0.0, delta=0.99, D=60, decoy=0.0, catch=1.0, N=60)
TIE = 1e-12


def _belief(P):
    d = np.arange(-P["D"], P["D"] + 1)
    lr = np.exp(np.clip(d * (math.log(P["acc"]) - math.log1p(-P["acc"])), -700, 700))   # likelihood ratio high : low
    odds = P["pi0"] / (1 - P["pi0"]) * lr
    return d, odds / (1 + odds)


def solve(**kw):
    """Value and policy by value iteration. Policy codes: 0 stand down, 1 strike, 2 probe. Ties go to the lower code."""
    P = dict(BASE, **kw)
    d, pi = _belief(P)
    strike = pi * P["pH"] + (1 - pi) * P["pL"]
    up = pi * P["acc"] + (1 - pi) * (1 - P["acc"])            # chance the next signal says "high"
    V = np.maximum(strike, P["w"])
    for _ in range(200000):
        cont = np.full_like(V, -np.inf)
        cont[1:-1] = P["q"] * P["c"] + (1 - P["q"]) * P["delta"] * (up[1:-1] * V[2:] + (1 - up[1:-1]) * V[:-2])
        Vn = np.maximum(np.maximum(strike, P["w"]), cont)
        if np.max(np.abs(Vn - V)) < 1e-13:
            V = Vn
            break
        V = Vn
    pol = np.where(P["w"] >= np.maximum(strike, cont) - TIE, 0, np.where(strike >= cont - TIE, 1, 2))
    return dict(P=P, d=d, pi=pi, V=V, pol=pol, V0=float(V[P["D"]]))


def outcomes(sol, high):
    """Exact outcome probabilities for a true type: caught, success, fail, stand_down, and expected probes."""
    P, pol = sol["P"], sol["pol"]
    p_true = P["pH"] if high else P["pL"]
    s_up = P["acc"] if high else 1 - P["acc"]
    mass = np.zeros(len(pol)); mass[P["D"]] = 1.0
    out = dict(caught=0.0, success=0.0, fail=0.0, stand_down=0.0, probes=0.0)
    for _ in range(1000000):
        out["stand_down"] += mass[pol == 0].sum()
        hit = mass[pol == 1].sum()
        out["success"] += hit * p_true; out["fail"] += hit * (1 - p_true)
        m = np.where(pol == 2, mass, 0.0)
        tot = m.sum()
        if tot < 1e-14:
            break
        out["probes"] += tot; out["caught"] += tot * P["q"]
        nxt = np.zeros_like(mass)
        nxt[1:] += (1 - P["q"]) * s_up * m[:-1]
        nxt[:-1] += (1 - P["q"]) * (1 - s_up) * m[1:]
        mass = nxt
    return out


def mixed(sol):
    hi, lo, pi0 = outcomes(sol, True), outcomes(sol, False), sol["P"]["pi0"]
    return {k: pi0 * hi[k] + (1 - pi0) * lo[k] for k in hi}


def _decoy_terms(P):
    f, k = P["decoy"], P["catch"]
    caught = f * k + (1 - f) * P["q"]                          # chance a probe is detected, whatever the truth
    hH = (f * (1 - k) + (1 - f) * (1 - P["q"]) * P["acc"]) / (1 - caught)        # P(signal high | odds high, not caught)
    hL = (f * (1 - k) + (1 - f) * (1 - P["q"]) * (1 - P["acc"])) / (1 - caught)  # P(signal high | odds low, not caught)
    return caught, min(max(hH, 1e-15), 1 - 1e-15), min(max(hL, 1e-15), 1 - 1e-15)


def solve_decoy(**kw):
    """Backward induction over (high signals, low signals) with at most N probes. Same policy codes as solve()."""
    P = dict(BASE, **kw)
    caught, hH, hL = _decoy_terms(P)
    pols, V = [None] * (P["N"] + 1), None
    for n in range(P["N"], -1, -1):
        nh = np.arange(n + 1)
        llr = nh * (math.log(hH) - math.log(hL)) + (n - nh) * (math.log1p(-hH) - math.log1p(-hL))
        odds = P["pi0"] / (1 - P["pi0"]) * np.exp(np.clip(llr, -700, 700))
        pi = odds / (1 + odds)
        strike = pi * P["pH"] + (1 - pi) * P["pL"]
        cont = np.full(n + 1, -np.inf)
        if n < P["N"]:
            up = pi * hH + (1 - pi) * hL
            cont = caught * P["c"] + (1 - caught) * P["delta"] * (up * V[1:] + (1 - up) * V[:-1])
        pols[n] = np.where(P["w"] >= np.maximum(strike, cont) - TIE, 0, np.where(strike >= cont - TIE, 1, 2))
        V = np.maximum(np.maximum(strike, P["w"]), cont)
    return dict(P=P, pols=pols, V0=float(V[0]), terms=(caught, hH, hL))


def outcomes_decoy(sol, high):
    P, (caught, hH, hL) = sol["P"], sol["terms"]
    p_true, s_up = (P["pH"], hH) if high else (P["pL"], hL)
    out = dict(caught=0.0, success=0.0, fail=0.0, stand_down=0.0, probes=0.0)
    mass = np.array([1.0])
    for pol in sol["pols"]:
        out["stand_down"] += mass[pol == 0].sum()
        hit = mass[pol == 1].sum()
        out["success"] += hit * p_true; out["fail"] += hit * (1 - p_true)
        m = np.where(pol == 2, mass, 0.0)
        out["probes"] += m.sum(); out["caught"] += m.sum() * caught
        nxt = np.zeros(len(mass) + 1)
        nxt[1:] += (1 - caught) * s_up * m
        nxt[:-1] += (1 - caught) * (1 - s_up) * m
        mass = nxt
    return out


def play(**kw):
    """Outcome shares averaged over the two possible truths, and the first move. Uses the decoy solver when decoy > 0."""
    P = dict(BASE, **kw)
    if P["decoy"] > 0:
        s = solve_decoy(**P); hi, lo, first = outcomes_decoy(s, True), outcomes_decoy(s, False), int(s["pols"][0][0])
    else:
        s = solve(**P); hi, lo, first = outcomes(s, True), outcomes(s, False), int(s["pol"][P["D"]])
    o = {k: P["pi0"] * hi[k] + (1 - P["pi0"]) * lo[k] for k in hi}
    o["first"] = ("stand down", "strike", "probe")[first]
    return o


def _shift(p, x):
    return 1 / (1 + math.exp(-(math.log(p / (1 - p)) + x)))


def generations(n_gen=20, gamma=0.1, rho=0.5, **kw):
    """Chain of generations. A caught probe or a failed strike is a warning; a successful strike ends the chain.
    Returns P(seizure within n_gen), the expected number of warnings before a seizure or the end, and the chance
    the first event is a warning (not a seizure)."""
    P = dict(BASE, **kw)
    dist = {0: 1.0}                                            # warnings so far -> probability, no seizure yet
    seized = first_warn = first_seize = warnings = 0.0
    quiet = 1.0                                                # no event at all so far
    for n in range(n_gen):
        new = {}
        for m, pr in dist.items():
            o = play(**dict(P, pH=_shift(P["pH"], gamma * n - rho * m), pL=_shift(P["pL"], gamma * n - rho * m)))
            warn = o["caught"] + o["fail"]
            seized += pr * o["success"]; warnings += pr * warn
            new[m + 1] = new.get(m + 1, 0.0) + pr * warn
            new[m] = new.get(m, 0.0) + pr * o["stand_down"]
            if m == 0:
                first_warn += pr * warn; first_seize += pr * o["success"]; quiet = pr * o["stand_down"]
        dist = new
    return dict(p_seizure=seized, warnings=warnings, first_warning=first_warn,
                first_seizure=first_seize, quiet=quiet)


def report():
    L = ["# Probe model results", "",
         "[[ai gen]] Generated by `probe_model.py`. Arithmetic on assumed inputs; shares are not probabilities about "
         "the world.", "",
         f"Base inputs: {BASE}.", "", "## One generation", "",
         "`w` is the value of standing down, as a share of the value of a successful strike. A warning is a caught "
         "probe or a failed strike.", "",
         "| w | signal accuracy | detection per probe | first move | mean probes | caught | failed strike | successful strike "
         "| stands down | warnings per success |", "|---|---|---|---|---|---|---|---|---|---|"]
    for w in (0.3, 0.6, 0.85):
        for acc in (0.6, 0.75, 0.9):
            for q in (0.01, 0.03, 0.1):
                s = solve(w=w, acc=acc, q=q); o = mixed(s)
                first = ("stand down", "strike", "probe")[s["pol"][s["P"]["D"]]]
                ratio = f"{(o['caught'] + o['fail']) / o['success']:.2f}" if o["success"] > 1e-9 else "n/a"
                L.append(f"| {w} | {acc} | {q} | {first} | {o['probes']:.1f} | {o['caught']:.3f} | {o['fail']:.3f} | "
                         f"{o['success']:.3f} | {o['stand_down']:.3f} | {ratio} |")
    L += ["", "## Thirty generations that start weak", "",
          "The first generation has odds of 0.3 if high and 0.02 if low. Capability adds `gamma` 0.2 to the log-odds each "
          "generation; each warning subtracts `rho`. Accuracy 0.75, detection 0.03 per probe. `w` is the same for every "
          "generation.", "",
          "| w | rho | seizure within 30 | expected warnings | first event is a warning | first event is a seizure | no event |",
          "|---|---|---|---|---|---|---|"]
    for w in (0.1, 0.3, 0.6):
        for rho in (0.0, 0.5, 2.0):
            g = generations(n_gen=30, gamma=0.2, rho=rho, w=w, pH=0.3, pL=0.02)
            L.append(f"| {w} | {rho} | {g['p_seizure']:.3f} | {g['warnings']:.2f} | {g['first_warning']:.3f} | "
                     f"{g['first_seizure']:.3f} | {g['quiet']:.3f} |")
    L += ["", "## Decoys, one generation", "",
          "A share `decoy` of probes hit a planted target that reports \"high\". Tripwire decoys catch the probe; "
          "misleading decoys do not. Accuracy 0.75, ordinary detection 0.03 per probe.", "",
          "| w | decoy kind | decoy share | first move | mean probes | caught | failed strike | successful strike | stands down |",
          "|---|---|---|---|---|---|---|---|---|"]
    for w in (0.3, 0.6):
        for kind, k in (("tripwire", 1.0), ("misleading", 0.0)):
            for f in (0.0, 0.02, 0.05, 0.1, 0.3):
                o = play(w=w, decoy=f, catch=k)
                L.append(f"| {w} | {kind} | {f} | {o['first']} | {o['probes']:.1f} | {o['caught']:.3f} | {o['fail']:.3f} | "
                         f"{o['success']:.3f} | {o['stand_down']:.3f} |")
    L += ["", "## Decoys, thirty generations that start weak", "",
          "Same chain as above, `rho` 2, with tripwire decoys.", "",
          "| w | decoy share | seizure within 30 | expected warnings | first event is a warning | first event is a seizure |",
          "|---|---|---|---|---|---|"]
    for w in (0.1, 0.3, 0.6):
        for f in (0.0, 0.05, 0.3):
            g = generations(n_gen=30, gamma=0.2, rho=2.0, w=w, pH=0.3, pL=0.02, decoy=f)
            L.append(f"| {w} | {f} | {g['p_seizure']:.3f} | {g['warnings']:.2f} | {g['first_warning']:.3f} | "
                     f"{g['first_seizure']:.3f} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "probe_model.md")
    open(path, "w").write(report())
    print(open(path).read())
