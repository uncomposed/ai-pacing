"""Checks for probe_model.py: closed forms, identities and a seeded Monte Carlo. Run: python3 test_probe_model.py"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probe_model as pm

def close(a, b, tol=1e-6):
    assert abs(a - b) < tol, (a, b)

# 1. Uninformative probes are never bought: the value is the better of a blind strike and standing down.
for w in (0.3, 0.6):
    s = pm.solve(acc=0.5, w=w)
    close(s["V0"], max(0.5 * 0.9 + 0.5 * 0.05, w)); assert s["pol"][s["P"]["D"]] != 2

# 2. A perfect probe is bought once: V = q c + (1 - q) delta (pi0 max(pH, w) + (1 - pi0) max(pL, w)).
#    With pH 0.9, pL 0.05, pi0 0.5, w 0.6, c 0, delta 1 the AI probes iff q < 1 - 0.6 / 0.75 = 0.2.
for q, probes in ((0.19, True), (0.21, False)):
    s = pm.solve(acc=1 - 1e-12, q=q, delta=1.0)
    assert (s["pol"][s["P"]["D"]] == 2) == probes
    close(s["V0"], max((1 - q) * 0.75, 0.6))

# 3. Free, patient probing learns the truth: V -> pi0 max(pH, w) + (1 - pi0) max(pL, w).
close(pm.solve(q=0.0, delta=1.0, acc=0.8)["V0"], 0.75, 1e-4)

# 4. Outcomes sum to one, for each true type, and match a seeded simulation.
rng = np.random.default_rng(7)
s = pm.solve(); P, pol = s["P"], s["pol"]
for high in (True, False):
    o = pm.outcomes(s, high)
    close(o["caught"] + o["success"] + o["fail"] + o["stand_down"], 1.0, 1e-9)
    n, cnt = 40000, dict(caught=0, success=0, fail=0, stand_down=0)
    for _ in range(n):
        i = P["D"]
        while True:
            a = pol[i]
            if a == 0: cnt["stand_down"] += 1; break
            if a == 1: cnt["success" if rng.random() < (P["pH"] if high else P["pL"]) else "fail"] += 1; break
            if rng.random() < P["q"]: cnt["caught"] += 1; break
            i += 1 if rng.random() < (P["acc"] if high else 1 - P["acc"]) else -1
    for k in cnt:
        se = max((o[k] * (1 - o[k]) / n) ** 0.5, 1e-4)
        assert abs(cnt[k] / n - o[k]) < 4 * se, (k, cnt[k] / n, o[k])

# 5. The AI's value never rises with the detection chance.
v = [pm.solve(q=q)["V0"] for q in (0.0, 0.01, 0.03, 0.1, 0.3)]
assert all(a >= b - 1e-12 for a, b in zip(v, v[1:]))

# 6. Generations: the event shares add up, and with no hardening and no growth every generation is the same game.
g = pm.generations(n_gen=5, gamma=0.0, rho=0.0)
o = pm.mixed(pm.solve())
close(g["first_seizure"], o["success"] * sum(o["stand_down"] ** k for k in range(5)), 1e-9)
close(g["first_warning"] + g["first_seizure"] + g["quiet"], 1.0, 1e-9)
print("probe model: 6 checks passed (closed forms, identities, seeded Monte Carlo); nothing here is empirical")
