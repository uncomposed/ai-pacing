"""
Sampling-measure sensitivity of the robust-design hold shares (issue #8). No solving.

    python3 measure_sensitivity.py               # write results/measure_sensitivity.{md,json}
    python3 measure_sensitivity.py --verify K    # re-solve the first K batches of full__base and compare (slow: ~90 s each)

The robust-design shares are shares of draws under one sampling measure (AS-PRIORS): independent uniform or
log-uniform marginals over the PARAMS ranges, with point masses at zero for ell_inf, omega and f_E. They are not
calibrated probabilities. This script asks how the design ranking moves when that measure changes, without new
solves: the cached full-box draws (192, Latin hypercube, seed 20261016) are reweighted by the density ratio of an
alternative measure to the sampled one (self-normalised importance weights).

What reweighting can and cannot do:
1. It can change marginal shapes, point-mass shares, truncate ranges and add dependence (Gaussian copulas on the
   unit-cube coordinates) within the sampled support.
2. It cannot widen a range or add a point mass where no draw exists. Those measures are listed as unidentified,
   not estimated.
3. Its precision is the effective sample size (ESS) of the weights. Below MIN_ESS a measure's shares are reported
   but its ranking is marked not identified at this sample size. More draws under an unsupported measure would
   not make it supported (issue #8 stopping rule).
4. Draw identity: the draws are regenerated from robust_design.ensemble, not read from the cache (the cache does
   not store them). Each cache read is checked by run_identity (bytes, and run_identity.verify_draws: the
   regenerated draws must hash to the draws the cache's manifest or inventory entry is bound to; issue #6). --verify re-solves cached batches to check that the regenerated draws reproduce the
   cached outcomes. One batch (16 draws) was checked when this was written; see results/measure_sensitivity.md.

Status: implemented; the reweighting identities are tested in tests/test_measure_sensitivity.py. Not human_validated.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import os
from statistics import NormalDist

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np

import robust_design as rd
import run_identity as ri

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_MD = os.path.join(rd.RES, "measure_sensitivity.md")
OUT_JSON = os.path.join(rd.RES, "measure_sensitivity.json")
ENSEMBLE = "full"
SEED = 20261016
MIN_ESS = 30.0
INTERPRETATION = "share of draws under the stated sampling measure; not a calibrated probability"
COL = {u[0]: j for j, u in enumerate(rd.UNCERTAIN)}
SPEC = {u[0]: u for u in rd.UNCERTAIN}
BEST = "D_mult=3_T_reloc=4_d=0.99_q_red=2_seq=1"

# Each measure is a list of (kind, args). kinds: linear (log-uniform -> uniform on the same range),
# log (uniform -> log-uniform), pointmass (new share at zero), range (truncate to [a, b]),
# copula (Gaussian copula with correlation rho on the unit-cube coordinates of two parameters).
LOG_PARAMS = [u[0] for u in rd.UNCERTAIN if u[3] == "log"]
MEASURES: list[tuple[str, str, list]] = [("base", "the sampled measure (AS-PRIORS)", [])]
MEASURES += [(f"linear:{p}", f"{p} uniform instead of log-uniform on the same range", [("linear", p)]) for p in LOG_PARAMS]
MEASURES += [
    ("pm:ell_inf=0.1", "ell_inf: 10% at zero instead of 50%", [("pointmass", "ell_inf", 0.1)]),
    ("pm:ell_inf=0.9", "ell_inf: 90% at zero instead of 50%", [("pointmass", "ell_inf", 0.9)]),
    ("pm:omega=0", "omega: no point mass at zero (instead of a third)", [("pointmass", "omega", 0.0)]),
    ("pm:omega=2/3", "omega: two thirds at zero", [("pointmass", "omega", 2 / 3)]),
    ("pm:f_E=0", "f_E: no point mass at zero (instead of a third)", [("pointmass", "f_E", 0.0)]),
    ("pm:f_E=2/3", "f_E: two thirds at zero", [("pointmass", "f_E", 2 / 3)]),
    ("range:kill_pre>=0.5", "kill_pre restricted to [0.5, 1]", [("range", "kill_pre", 0.5, 1.0)]),
    ("range:kill_pre<=0.5", "kill_pre restricted to [0, 0.5]", [("range", "kill_pre", 0.0, 0.5)]),
    ("range:chi0>=0.25", "chi0 restricted to [0.25, 0.5] (towards Metzger's crude-chip growth)", [("range", "chi0", 0.25, 0.5)]),
    ("range:q>=0.5", "q restricted to [0.5, 1]", [("range", "q", 0.5, 1.0)]),
    ("range:B_R<=10", "B_R restricted to [0, 10]", [("range", "B_R", 0.0, 10.0)]),
    ("dep:q~D+0.5", "q and D positively dependent (one human security capacity), rho 0.5", [("copula", "q", "D", 0.5)]),
    ("dep:kill_pre~chi0-0.5", "kill_pre and chi0 negatively dependent (good crude chips weaken chip dependence), rho -0.5",
     [("copula", "kill_pre", "chi0", -0.5)]),
    ("dep:B_R~B_Rc+0.7", "B_R and B_Rc positively dependent, rho 0.7", [("copula", "B_R", "B_Rc", 0.7)]),
    ("dep:mu~s_R0+0.5", "rival hazard and rival start size positively dependent, rho 0.5", [("copula", "mu", "s_R0", 0.5)]),
    ("dep:all4", "all four dependence structures together",
     [("copula", "q", "D", 0.5), ("copula", "kill_pre", "chi0", -0.5), ("copula", "B_R", "B_Rc", 0.7), ("copula", "mu", "s_R0", 0.5)]),
]
# Alternatives the sample cannot represent. Listed, never estimated.
UNIDENTIFIED = [
    ("chi0 above 0.5", "Metzger suggests crude chips may carry growth near full speed (AS-CHI0); the box stops at 0.5. "
     "robust_design.md 13.8 answers this the right way, by re-solving at chi0 = 1 (full-box best stack 15 to 10 holds)."),
    ("kill_pre, q, D or any other parameter with a point mass", "only ell_inf, omega and f_E have draws at exactly zero."),
    ("Kmax above 1e13, D below 0.01 or any range wider than PARAMS", "no draws outside the sampled box."),
    ("dependence on parameters fixed in the box (rep, q_er, q_ea, H)", "they are not sampled."),
    ("a different equilibrium selection, horizon or outcome predicate", "structural or normative, not a sampling choice (#9, #10)."),
]

_ND = NormalDist()


def _probit(u: np.ndarray) -> np.ndarray:
    return np.array([_ND.inv_cdf(float(x)) for x in np.clip(u, 1e-12, 1 - 1e-12)])


def wilson(k: float, n: float, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials (n may be an effective sample size)."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, mid - half), min(1.0, mid + half))


def gaussian_copula_density(u1: np.ndarray, u2: np.ndarray, rho: float) -> np.ndarray:
    z1, z2 = _probit(u1), _probit(u2)
    q = (rho * rho * (z1 * z1 + z2 * z2) - 2 * rho * z1 * z2) / (2 * (1 - rho * rho))
    return np.exp(-q) / math.sqrt(1 - rho * rho)


def component_weight(U: np.ndarray, values: dict, comp: tuple) -> np.ndarray:
    """Density ratio (new / sampled) of one measure component at each draw. U: (n, d) unit coordinates."""
    kind = comp[0]
    if kind == "copula":
        _, a, b, rho = comp
        return gaussian_copula_density(U[:, COL[a]], U[:, COL[b]], rho)
    p = comp[1]
    _, lo, hi, scale, p0 = SPEC[p]
    v = values[p]
    cont = v > 0 if p0 > 0 else np.ones(len(v), bool)
    if kind == "linear":
        if scale != "log":
            raise ValueError(f"{p} is not log-uniform")
        w = np.ones(len(v))
        w[cont] = v[cont] * math.log(hi / lo) / (hi - lo)
        return w
    if kind == "log":
        if scale != "lin" or lo <= 0:
            raise ValueError(f"{p} cannot be made log-uniform")
        w = np.ones(len(v))
        w[cont] = (hi - lo) / (v[cont] * math.log(hi / lo))
        return w
    if kind == "pointmass":
        new = comp[2]
        if p0 <= 0:
            raise ValueError(f"{p} has no draws at zero; a point mass there is unidentified")
        return np.where(cont, (1 - new) / (1 - p0), new / p0)
    if kind == "range":
        a, b = comp[2], comp[3]
        if p0 > 0 or scale not in ("lin", "log"):
            raise ValueError(f"range truncation of {p} is not implemented")
        mass = (math.log(b / a) / math.log(hi / lo)) if scale == "log" else (b - a) / (hi - lo)
        return ((v >= a) & (v <= b)).astype(float) / mass
    raise ValueError(kind)


def weights(U: np.ndarray, values: dict, components: list) -> np.ndarray:
    w = np.ones(U.shape[0])
    for c in components:
        w = w * component_weight(U, values, c)
    return w


def ess(w: np.ndarray) -> float:
    s = w.sum()
    return float(s * s / (w * w).sum()) if s > 0 else 0.0


def weighted_share(w: np.ndarray, h: np.ndarray) -> float:
    return float((w * h).sum() / w.sum()) if w.sum() > 0 else float("nan")


def kendall_tau(a: list[float], b: list[float]) -> float:
    n, s, m = len(a), 0, 0
    for i in range(n):
        for j in range(i + 1, n):
            x, y = np.sign(a[i] - a[j]), np.sign(b[i] - b[j])
            if x != 0 and y != 0:
                s += int(x * y)
                m += 1
    return s / m if m else float("nan")


DESIGN_KEYS = set(rd.LEVERS) | set(rd.MODIFIERS)
_KV = re.compile(r"(?:^|_)([A-Za-z][A-Za-z0-9_]*?)=([^_]+)")


def design_levers(key: str) -> dict[str, str]:
    """Parse a cache design key ('D_mult=3_T_reloc=4_seq=1') into {name: value}; 'base' is {}."""
    return {} if key == "base" else dict(_KV.findall(key))


def load_designs(ens: str = ENSEMBLE, n: int | None = None, thetas=None) -> dict[str, np.ndarray]:
    """design key -> holds (0/1) for every cached lever design of the ensemble with the default solver settings.
    Runs that also set a test switch or an uncertain parameter (pf_bel, q_up, kill_pre, ...) are not designs and are skipped."""
    n = n or rd.N_FULL
    out = {}
    for f in sorted(os.listdir(rd.RUNS)):
        if not f.startswith(ens + "__") or not f.endswith(".npz") or f.count("__") != 1:
            continue
        if not set(design_levers(f[len(ens) + 2:-4])) <= DESIGN_KEYS:
            continue
        path = os.path.join(rd.RUNS, f)
        z = ri.load_for_read(path)
        if thetas is not None:
            ri.verify_draws(path, ens, thetas)
        h = rd.holds(z).astype(float)
        if len(h) == n:
            out[f[len(ens) + 2:-4]] = h
    return out


def analyse(U: np.ndarray, values: dict, designs: dict[str, np.ndarray]) -> dict:
    names = sorted(designs)
    base_w = np.ones(U.shape[0])
    base_share = [weighted_share(base_w, designs[d]) for d in names]
    rows = []
    for mid, desc, comps in MEASURES:
        w = weights(U, values, comps)
        e = ess(w)
        shares = [weighted_share(w, designs[d]) for d in names]
        order = sorted(range(len(names)), key=lambda i: (-shares[i], names[i]))
        top = names[order[0]]
        best = names.index(BEST) if BEST in names else None
        base_i = names.index("base") if "base" in names else None
        rows.append(dict(
            id=mid, description=desc, ess=round(e, 3), identified=e >= MIN_ESS,
            top=top, top_share=round(shares[order[0]], 6),
            best_stack_share=None if best is None else round(shares[best], 6),
            best_stack_interval=None if best is None else [round(x, 6) for x in wilson(shares[best] * e, e)],
            best_stack_rank=None if best is None else order.index(best) + 1,
            base_design_share=None if base_i is None else round(shares[base_i], 6),
            kendall_tau_vs_sampled=round(kendall_tau(base_share, shares), 4),
            shares={d: round(s, 6) for d, s in zip(names, shares)},
        ))
    return dict(rows=rows, designs=names)


def label(n: int) -> dict:
    return dict(
        interpretation=INTERPRETATION,
        sampling_measure=f"robust_design full box, {n} Latin-hypercube draws (seed {SEED}), reweighted to each measure below",
        structural_assumptions=["AS-SELECTION", "AS-HORIZON", "AS-SINGLE-AI", "AS-NOFIRSTSTRIKE", "AS-FIXEDTERMS", "AS-RIVAL-HOLDS"],
        horizon="300 years, 'peace' terminal value",
        predicate="holds: AI cooperates (or polices) at t = 0 and P(strike or harvest within 300 years) < 0.01; a likely rival still counts as holding",
        numerical_uncertainty="Wilson 95% interval with n = ESS (approximate: Latin hypercube draws, self-normalised weights)",
        uncertainty_types=dict(
            random_outcome="strike timing and rival births are random within the model; the predicate uses their expectation",
            parameter="the sampling measure over 45 parameters; this report varies it",
            model_form="the structural assumptions listed; not varied here",
            normative="the 1% threshold, the horizon and counting a likely rival as holding",
        ),
    )


def report(res: dict, n: int) -> tuple[str, dict]:
    rows = res["rows"]
    base = rows[0]
    lab = label(n)
    lines = [
        "# Sampling-measure sensitivity of design rankings (generated by measure_sensitivity.py; do not edit)", "",
        f"**Read every share as: {INTERPRETATION}.** Predicate: {lab['predicate']}. Horizon: {lab['horizon']}. "
        f"Sampling: {lab['sampling_measure']}. Numerical uncertainty: {lab['numerical_uncertainty']}. "
        f"Structural assumptions held fixed: {', '.join(lab['structural_assumptions'])}.", "",
        f"{len(res['designs'])} cached designs, {n} draws each. A measure with ESS below {MIN_ESS:g} is not identified at this sample "
        "size: its shares are shown, its ranking is not interpreted.", "",
        "Draw identity: the draws are regenerated, not read from the cache (issue #6). When this was written, the first solver "
        "batch of full__base (16 of 192 draws) was re-solved with numpy 1.26.4 and reproduced the cached act0 exactly and "
        "att within 7.5e-16 (`python3 measure_sensitivity.py --verify 1`). The other 176 draws were not re-solved.", "",
        "| measure | ESS | identified | top design | top share | best stack share (95%) | best stack rank | base design share | Kendall tau vs sampled |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        iv = r["best_stack_interval"]
        lines.append(f"| {r['id']} | {r['ess']:.1f} | {'yes' if r['identified'] else 'no'} | {r['top']} | {r['top_share']:.3f} | "
                     f"{r['best_stack_share']:.3f} ({iv[0]:.3f}-{iv[1]:.3f}) | {r['best_stack_rank']} | {r['base_design_share']:.3f} | "
                     f"{r['kendall_tau_vs_sampled']:.2f} |")
    ident = [r for r in rows if r["identified"]]
    changed = [r for r in ident if r["top"] != base["top"]]
    lo = min(r["best_stack_share"] for r in ident)
    hi = max(r["best_stack_share"] for r in ident)
    rev = [r for r in ident if r["best_stack_share"] <= r["base_design_share"]]
    moved = [r for r in ident if r["best_stack_rank"] != base["best_stack_rank"]]
    lines += ["", "## Summary", "",
              f"1. Identified measures: {len(ident)} of {len(rows)}. The top design changes under {len(changed)} of them"
              + (f" ({', '.join(r['id'] + ': ' + r['top'] for r in changed)})." if changed else ".")
              + f" The best stack ({BEST}) changes rank under {len(moved)} (rank {base['best_stack_rank']} under the sampled measure,"
              f" {min(r['best_stack_rank'] for r in ident)} to {max(r['best_stack_rank'] for r in ident)} across identified measures)."
              f" It falls to or below the base design under {len(rev)}.",
              f"2. Across identified measures the best stack's share ranges from {lo:.3f} to {hi:.3f}. This range is the result: "
              "no measure is preferred, so the shares are not averaged.",
              f"3. Lowest Kendall tau against the sampled ranking among identified measures: "
              f"{min(r['kendall_tau_vs_sampled'] for r in ident):.2f}.",
              "4. Many designs differ by one or two holding draws, and their intervals overlap; ties are broken by name. Rank changes "
              "among them are within sampling noise and are not evidence that one design beats another under that measure.",
              "", "## Alternatives the sample cannot represent (unidentified, not estimated)", ""]
    lines += [f"- {a}: {why}" for a, why in UNIDENTIFIED]
    lines += ["", "A full comparison with fresh draws under widened ranges and alternative point masses needs new solves "
              "(sims.yml); it has not been run."]
    payload = dict(label=lab, n_draws=n, min_ess=MIN_ESS, designs=res["designs"], rows=rows,
                   unidentified=[dict(alternative=a, reason=w) for a, w in UNIDENTIFIED])
    return "\n".join(lines) + "\n", payload


def build():
    U, thetas = rd.ensemble(ENSEMBLE, rd.N_FULL, seed=SEED)
    values = {p: np.array([t[p] for t in thetas]) for p in rd.UNAMES}
    designs = load_designs(thetas=thetas)
    return report(analyse(U, values, designs), rd.N_FULL)


def verify(k: int) -> None:
    U, thetas = rd.ensemble(ENSEMBLE, rd.N_FULL, seed=SEED)
    path = os.path.join(rd.RUNS, f"{ENSEMBLE}__base.npz")
    z = ri.load_for_read(path)
    print(f"draw identity: {ri.verify_draws(path, ENSEMBLE, thetas)}")
    for g in rd.batches_for(thetas)[:k]:
        r = rd._solve_batch(([rd.apply_design(thetas[i], {}) for i in g], rd.CFG))
        same = bool((r["act0"] == z["act0"][g]).all())
        print(f"batch of {len(g)} draws: act0 identical {same}; max |att - cached| {np.abs(r['att'] - z['att'][g]).max():.3g}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", type=int, default=0, help="re-solve this many batches of full__base and compare")
    a = ap.parse_args()
    if a.verify:
        verify(a.verify)
        return
    md, js = build()
    open(OUT_MD, "w").write(md)
    with open(OUT_JSON, "w") as f:
        json.dump(js, f, indent=1, sort_keys=True)
        f.write("\n")
    print(md)


if __name__ == "__main__":
    main()
