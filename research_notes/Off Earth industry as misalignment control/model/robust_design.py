"""
Robust-decision analysis of the off-Earth pact on the equilibrium model (2026-10-16).

Question: the baseline pact flips to a strike under 19 of 36 single-parameter moves. Which settings
that humans control widen the region of uncertain parameters where the pact holds?

    python3 robust_design.py --check              # regression + erosion checks (about 3 min)
    python3 robust_design.py --stage pilot        # base design on small samples (sizing)
    python3 robust_design.py --stage oat          # one lever at a time, both uncertainty boxes
    python3 robust_design.py --stage factorial    # factorial over the levers that matter
    python3 robust_design.py --stage erosion      # denial-erosion sweeps
    python3 robust_design.py --report             # tables, scenario discovery, figures (no solving)

Every solved (ensemble, design) pair is cached in results/robust_runs/ as .npz, so stages can be
re-run or resumed cheaply and --report only reads the cache. Each cache has a manifest (<tag>.manifest.json) and is
reused only if its full experiment identity matches the request (run_identity.py, issue #6).
Outputs: results/robust_design_tables.md, results/robust_design_summary.json, figures/rd_*.png.
results/robust_design.md is hand-written from those tables.
Colours: Okabe-Ito blue and orange, always backed by hatching, markers, line style or text labels.
Status: implemented + verified (see --check). Not human_validated.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor

os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np

import equilibrium_model as em
import run_identity as ri

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
FIG = os.path.join(HERE, "figures")
RUNS = os.path.join(RES, "robust_runs")
os.makedirs(RUNS, exist_ok=True)

CFG = dict(T_H=300, nA=160, N=2)
BATCH = 16
WORKERS = int(os.environ.get("RD_WORKERS", "5"))
BLUE, SKY, ORANGE, PURPLE, BLACK, GREY = "#0072B2", "#56B4E9", "#E69F00", "#CC79A7", "#000000", "#999999"
STRIKE_TOL = 0.01          # "no strike in 300 years" means P(strike within 300 y) below 1%

# ---------------------------------------------------------------------------
# 1. Levers (human-controllable) and uncertainties (nobody controls)
# ---------------------------------------------------------------------------
# name -> (baseline-design value, alternatives tested one at a time, meaning)
LEVERS: "OrderedDict[str, tuple]" = OrderedDict([
    ("seq",     (0, [1, 2, 3], "fab sequencing: 0 a after closure, 1 b to orbit, 2 c early, 3 n never")),
    ("den",     (1.0, [0.0], "keep the denial reserve")),
    ("d",       (0.9, [0.5, 0.99], "share of Earth capacity that goes dead when denial fires (how much runs on authorised chips)")),
    ("T_dis",   (5.0, [2.0, 15.0], "years to dismantle Earth's fabs")),
    ("T_reloc", (10.0, [4.0, 20.0], "years to relocate fabs to orbit (only with seq b)")),
    ("L_det",   (2.0, [0.5, 6.0], "years a covert programme stays hidden (verification speed)")),
    ("zeta",    (0.3, [0.0, 0.9], "yearly chance other states shut a public programme")),
    ("c_sanc",  (0.5, [0.0, 2.0], "yearly sanction on a state with a public programme")),
    ("police",  (0.0, [1.0], "pact lets the AI remove detected programmes")),
    ("sigma",   (0.3, [0.05, 0.7], "AI's share of trade gains")),
    ("move_c",  (0.0, [1.0], "move Earth's existing compute to orbit with the fab schedule")),
    ("psi_div", (0.0, [0.1], "tribute: share of AI output paid to humans")),
    # added levers (modifiers of a sampled uncertainty; see robust_design.md section 1)
    ("q_red",   (1.0, [2.0], "independent denial reserves: q -> 1 - (1 - q)^q_red")),
    ("D_mult",  (1.0, [3.0], "keep more of Earth's defences: D -> D * D_mult")),
    ("T_rot",   (0.0, [10.0], "rotate the denial signing chain every T_rot years (0 = never); matters only with erosion")),
])
# BR_mult (state temptation, test 1 of 2026-10-21) is kept out of LEVERS so the OAT list and report are unchanged;
# pass it in --designs. It scales B_R and B_Rc: commitments and pooled downside that cut what a state gains by racing.
MODIFIERS = ("q_red", "D_mult", "BR_mult")

# (name, low, high, scale, point mass at zero). scale: lin, log, bin. A point mass p0 puts that share
# of the stratified sample exactly at 0 (structural "is it zero?" questions), the rest on [low, high].
UNCERTAIN = [
    # growth / physics
    ("g", 0.07, 0.69, "log", 0), ("chi0", 0.02, 0.5, "lin", 0), ("chi_m", 0.1, 0.9, "lin", 0),
    ("A0", 1e-4, 1e-2, "log", 0), ("A_close", 0.01, 1.0, "log", 0), ("Kmax", 1e6, 1e13, "log", 0),
    ("T_rebuild", 3.0, 30.0, "lin", 0), ("gam", 0.05, 1.0, "lin", 0), ("reinv", 0, 1, "bin", 0),
    # conflict
    ("p_s0", 0.05, 0.95, "lin", 0), ("D", 0.01, 1.0, "log", 0), ("eps", 0.3, 2.0, "lin", 0),
    ("c_w", 0.0, 0.8, "lin", 0), ("c_A", 0.0, 3.0, "lin", 0), ("L_f", 0.1, 0.9, "lin", 0),
    ("kill_pre", 0.0, 1.0, "lin", 0), ("q", 0.0, 1.0, "lin", 0),
    # threat
    ("mu", 0.02, 1.0, "log", 0), ("beta_bg", 0.0, 0.5, "lin", 0), ("th_floor", 0.0, 0.5, "lin", 0),
    ("s_R0", 0.01, 1.0, "log", 0), ("nu", 0.5, 2.0, "lin", 0), ("rho_h", 0.003, 3.0, "log", 0),
    ("m_frac", 0.0, 1.0, "lin", 0), ("n_cf", 0.0, 10.0, "lin", 0), ("f_fab", 0.01, 0.1, "lin", 0),
    ("p_block", 0.0, 1.0, "lin", 0), ("A_hg", 0.1, 10.0, "log", 0), ("c_blk", 0.0, 0.3, "lin", 0),
    ("ell_inf", 1e-8, 0.2, "log", 0.5),
    # humans
    ("r_h", 0.01, 0.1, "log", 0), ("B_R", 0.0, 20.0, "lin", 0), ("B_Rc", 0.0, 60.0, "lin", 0),
    ("B_o", 0.0, 20.0, "lin", 0), ("kap_coll", 0.0, 0.8, "lin", 0), ("c_prog", 0.0, 0.5, "lin", 0),
    ("c_den", 0.0, 0.2, "lin", 0), ("c_dmg", 0.0, 5.0, "lin", 0), ("w_seized", 0.0, 0.5, "lin", 0),
    # AI preferences and late-stage harvest
    ("r", 0.002, 0.1, "log", 0), ("eta", 0.0, 0.9, "lin", 0),
    ("omega", 1e-12, 0.05, "log", 1 / 3), ("f_E", 1e-11, 0.5, "log", 1 / 3),
    ("c_grav", 0.0, 0.9, "lin", 0), ("h_frac", 0.1, 0.99, "lin", 0),
]
UNAMES = [u[0] for u in UNCERTAIN]
FIXED = dict(H=1.0, rep=0.0, q_er=0.0, q_ea=0.0)   # rep acts exactly like omega (R4); erosion swept separately

NEAR_FRAC = 0.25   # the "near" box: baseline +- 25% of each range (in the parameter's own scale)


def lhs(n: int, d: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    u = (np.argsort(rng.random((d, n)), axis=1).T + rng.random((n, d))) / n
    return u


def _scale_map(x01, lo, hi, scale):
    if scale == "log":
        return np.exp(np.log(lo) + x01 * (np.log(hi) - np.log(lo)))
    return lo + x01 * (hi - lo)


def _scale_inv(v, lo, hi, scale):
    if scale == "log":
        return (np.log(v) - np.log(lo)) / (np.log(hi) - np.log(lo))
    return (v - lo) / (hi - lo)


def u_to_params(U: np.ndarray, box: str) -> list[dict]:
    """Map a unit-cube sample to parameter dicts. box 'full' uses the whole range; box 'near' uses the
    baseline +- NEAR_FRAC of the range (point masses keep their share, as in the full box)."""
    out = [dict(FIXED) for _ in range(U.shape[0])]
    for j, (nm, lo, hi, sc, p0) in enumerate(UNCERTAIN):
        u = U[:, j]
        rad = NEAR_FRAC if box == "near" else (float(box[1:]) if box.startswith("r") else None)
        if sc == "bin":
            v = (u >= 0.5).astype(float)
            if rad is not None:
                v = np.full_like(u, em.PARAMS[nm][0])
        else:
            if p0 > 0:
                x = np.clip((u - p0) / (1 - p0), 0, 1)
            else:
                x = u
            if rad is not None:
                b = em.PARAMS[nm][0]
                c = _scale_inv(b, lo, hi, sc) if b > 0 or sc != "log" else 0.0
                a0, a1 = max(0.0, c - rad), min(1.0, c + rad)
                x = a0 + x * (a1 - a0)
            v = _scale_map(x, lo, hi, sc)
            if p0 > 0:
                v = np.where(u < p0, 0.0, v)
                if box.startswith("r"):        # radius boxes hold the structural "is it zero?" params at baseline 0
                    v = np.zeros_like(v)
        for i in range(len(out)):
            out[i][nm] = float(v[i])
    return out


class Ensemble(list):
    """Parameter draws that remember how they were sampled (box, n, seed), for the run manifest."""
    sampling: dict = None


def ensemble(box: str, n: int, seed: int = 20261016):
    U = lhs(n, len(UNCERTAIN), seed)
    th = Ensemble(u_to_params(U, box))
    th.sampling = dict(box=box, n=n, seed=seed)
    return U, th


# ---------------------------------------------------------------------------
# 2. Solving designs over an ensemble (batched, parallel, cached)
# ---------------------------------------------------------------------------
LEVER_BASE = {k: v[0] for k, v in LEVERS.items()}
KEEP = ["att", "suc", "riv", "harv", "exit", "pre", "att25", "att100", "WH", "t_mean", "fail"]   # fail added 2026-10-21


def apply_design(theta: dict, design: dict) -> dict:
    p = dict(theta)
    lv = dict(LEVER_BASE, **design)
    for k, v in lv.items():
        if k not in MODIFIERS:
            p[k] = float(v)
    p["q"] = 1 - (1 - p["q"]) ** lv["q_red"]
    p["D"] = p["D"] * lv["D_mult"]
    m = lv.get("BR_mult", 1.0)
    p["B_R"] = p["B_R"] * m
    p["B_Rc"] = p["B_Rc"] * m
    return p


def design_key(design: dict) -> str:
    items = sorted((k, v) for k, v in design.items() if LEVER_BASE.get(k) != v)
    return "base" if not items else "_".join(f"{k}={v:g}" for k, v in items)


def _solve_batch(args):
    plist, kw = args
    ps = em.batch([em.baseline(**p) for p in plist])
    r = em.solve(ps, N=kw["N"], T_H=kw["T_H"], nA=kw["nA"])
    out = {k: np.asarray(r[k], float) for k in KEEP}
    out["act0"] = np.asarray(r["act0"]).astype("U1")
    return out


def batches_for(thetas: list[dict]) -> list[np.ndarray]:
    """Batch draws with similar grid tops together. The solver's A-grid spans the batch's largest
    Kmax*(1+f_E), so a fixed, sample-determined batching keeps every design on identical grids."""
    top = np.array([t["Kmax"] * (1 + t["f_E"]) for t in thetas])
    order = np.argsort(top, kind="stable")
    return [order[i:i + BATCH] for i in range(0, len(order), BATCH)]


def run_tag(ens_name: str, design: dict, **kw) -> str:
    """Cache name of one (ensemble, design, solver settings) run; ci_sims.py uses it too. The name is only an
    address: reuse is decided by the manifest's identity (request_for, run_identity.load_cached)."""
    cfg = dict(CFG, **kw)
    return f"{ens_name}__{design_key(design)}" + ("" if cfg == CFG else "__" + "_".join(f"{k}{v}" for k, v in sorted(kw.items())))


def request_for(ens_name: str, thetas: list[dict], design: dict, **kw) -> dict:
    """Run manifest (identity) of solving `design` over `thetas` with solver settings CFG + kw."""
    return ri.request("robust_design", ens_name, thetas, design, dict(CFG, **kw))


def run_design(ens_name: str, thetas: list[dict], design: dict, pool=None, **kw) -> dict:
    cfg = dict(CFG, **kw)
    tag = run_tag(ens_name, design, **kw)
    path = os.path.join(RUNS, tag + ".npz")
    want = request_for(ens_name, thetas, design, **kw)
    hit = ri.load_cached(path, want)      # raises IdentityError if a cache exists but was made by another run
    if hit is not None:
        return hit
    params = [apply_design(t, design) for t in thetas]
    groups = batches_for(thetas)
    jobs = [([params[i] for i in g], cfg) for g in groups]
    t0 = time.time()
    res = list(pool.map(_solve_batch, jobs)) if pool is not None else [_solve_batch(j) for j in jobs]
    n = len(thetas)
    out = {k: np.empty(n, float) for k in KEEP}
    out["act0"] = np.empty(n, "U1")
    for g, r in zip(groups, res):
        for k in out:
            out[k][g] = r[k]
    out["holds"] = holds(out).astype(float)
    ri.save_cached(path, out, want, produced=dict(by="robust_design.run_design", batches=len(groups)))
    print(f"  solved {tag}: {n} sets in {time.time() - t0:.0f} s; holds {out['holds'].mean():.3f}", flush=True)
    return out


def holds(r: dict) -> np.ndarray:
    """AI cooperates at t = 0 and the chance of any strike (or harvest) within 300 years is below 1%."""
    return np.isin(r["act0"], ["C", "P"]) & (r["att"] < STRIKE_TOL)


def fail_kind(r: dict) -> np.ndarray:
    """0 holds, 1 strike now, 2 later strike or harvest, 3 holds but a rival AI is likelier than not."""
    k = np.where(holds(r), 0, np.where(r["act0"] == "S", 1, 2))
    return np.where((k == 0) & (r["riv"] >= 0.5), 3, k)


# ---------------------------------------------------------------------------
# 3. Checks
# ---------------------------------------------------------------------------
def regression():
    import run_equilibrium as rq
    ref = {r[0].split()[0]: r for r in json.load(open(os.path.join(RES, "equilibrium_summary.json")))["scenarios"]}
    names = ["S1", "S7", "S14", "S16"]
    over = [dict(), dict(B_R=10.0), dict(ell_inf=0.01, w_seized=0.9), dict(f_E=1e-6)]
    r = rq.solve(over)
    md, moves = 0.0, []
    for i, n in enumerate(names):
        row = rq.row_summary(r, i)
        moves.append(f"{n} {row[0]} (ref {ref[n][1]})")
        assert row[0] == ref[n][1]
        for a, b in zip(row[1:], ref[n][2:-1]):
            a, b = float(a), float(b)
            if not (np.isnan(a) and np.isnan(b)):
                md = max(md, abs(a - b))
    return md, moves


def erosion_stop_year(p: dict, A: float, T_H: int = 300, dt: float = 1.0):
    """Closed-form check for time erosion at saturation (no growth, no rivals, no human programmes,
    linear utility, consumption trade, F = 0). Optimal stopping on a time line:
        V(T_H) = (A + trade) / (1 - delta)                    (the solver's 'peace' terminal)
        V(t)   = max(S(t), A + trade + delta V(t + 1))
        S(t)   = (1 - p_f) (A - cost + Pi(q(t))) / (1 - delta) + p_f V_peace
    with q(t) = q den (1 - q_ea)^log10(A/H) exp(-q_er (t mod T_rot)). Returns the first strike year,
    or None. p_f's continuation is approximated by the peace value (p_f ~ 1e-10 at the cap)."""
    delta = np.exp(-p["r"] * dt)
    trade = p["sigma"] * p["gam"] * min(A, p["H"])
    cost = p["c_A"] * p["D"] * A / (A + p["D"])
    p_f = (1 - p["p_s0"]) * (p["D"] / (p["D"] + A)) ** p["eps"]
    Vp = (A + trade) * dt / (1 - delta)
    V = Vp
    first = None
    for t in range(T_H - 1, -1, -1):
        yrs = (t * dt) % p["T_rot"] if p.get("T_rot", 0) > 0 else t * dt
        qf = p["q"] * p["den"] * (1 - p["q_ea"]) ** max(0.0, np.log10(A / p["H"])) * np.exp(-p["q_er"] * yrs)
        Pi = (1 - p["c_w"]) * p["H"] * (1 - qf * p["d"])
        S = (1 - p_f) * (A - cost + Pi) * dt / (1 - delta) + p_f * Vp
        W = (A + trade) * dt + delta * V
        if S > W * (1 + em.TIE_TOL):
            V, first = S, t
        else:
            V = W
    return first


def q_star_cap(p: dict, A: float) -> float:
    """Firing probability below which a saturated AI strikes (same assumptions, bisection on q)."""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if erosion_stop_year(dict(p, q=mid, q_er=0.0, q_ea=0.0, T_rot=0.0), A, T_H=2) == 0:
            lo = mid
        else:
            hi = mid
    return hi


def checks():
    lines = []
    t0 = time.time()
    md, moves = regression()
    lines.append(f"1. Round-1 regression with erosion off: {'; '.join(moves)}. Largest absolute difference "
                 f"over every reported number: {md:.3g}.")
    # identities: rotation every year undoes time erosion; size erosion has no effect below A = H
    base = em.baseline()
    over = [dict(), dict(q_er=0.5, T_rot=1.0), dict(q_ea=0.3, Kmax=0.5, A0=1e-3)]
    ps = em.batch([em.baseline(**o) for o in over] + [em.baseline(Kmax=0.5, A0=1e-3)])
    r = em.solve(ps, N=2, T_H=CFG["T_H"], nA=CFG["nA"])
    d1 = max(abs(r["VA"][1] / r["VA"][0] - 1), abs(r["WH"][1] - r["WH"][0]), abs(r["att"][1] - r["att"][0]))
    d2 = max(abs(r["VA"][2] / r["VA"][3] - 1), abs(r["WH"][2] - r["WH"][3]), abs(r["att"][2] - r["att"][3]))
    lines.append(f"2. Identity: q_er = 0.5 with rotation every year equals no erosion (largest relative difference "
                 f"{d1:.2g}). Size erosion q_ea = 0.3 with the AI capped below Earth's size (Kmax = 0.5) changes "
                 f"nothing ({d2:.2g}).")
    # closed form at saturation: no rivals, no programmes, AI starts at the cap
    sat = dict(A0=0.999e9, th_floor=0.0, beta_bg=0.0, B_R=0.0, w_seized=0.9)
    pS = em.baseline(**sat)
    A = 1e9
    qs = q_star_cap(pS, A)
    lines.append(f"3. Closed form at saturation: a capped AI strikes once the firing probability falls below "
                 f"q* = {qs:.3f} (baseline q = 0.7).")
    lam = [0.002, 0.005, 0.01, 0.02, 0.05]
    qea = [0.04, 0.055, 0.067, 0.08]
    over = [dict(sat, q_er=l) for l in lam] + [dict(sat, q_ea=a) for a in qea]
    r = em.solve(em.batch([em.baseline(**o) for o in over]), N=2, T_H=CFG["T_H"], nA=CFG["nA"])
    rows = []
    for i, l in enumerate(lam):
        cf = erosion_stop_year(dict(pS, q_er=l), A)
        rows.append([f"q_er = {l:g}", "none" if cf is None else cf,
                     "none" if r["att"][i] < 0.5 else f"{r['t_mean'][i]:.1f}", f"{r['att'][i]:.3f}"])
    for j, a in enumerate(qea):
        i = len(lam) + j
        cf = erosion_stop_year(dict(pS, q_ea=a), A)
        rows.append([f"q_ea = {a:g}", "none" if cf is None else cf,
                     "none" if r["att"][i] < 0.5 else f"{r['t_mean'][i]:.1f}", f"{r['att'][i]:.3f}"])
    lines.append("   Strike year, closed form against solver (AI starts at the cap; humans survive a seizure, so no racing):\n\n"
                 + md_table(rows, ["erosion", "closed-form first strike year", "solver mean strike year", "solver P(strike)"]))
    lines.append(f"   q_ea threshold, closed form: 1 - (q*/q)^(1/9) = {1 - (qs / 0.7) ** (1 / 9):.4f}.")
    lines.append(f"(checks took {time.time() - t0:.0f} s)")
    return "\n".join(lines), dict(reg_maxdiff=md, q_star_cap=qs, rows=rows)


# ---------------------------------------------------------------------------
# helpers for tables
# ---------------------------------------------------------------------------
def fmt(x):
    if isinstance(x, (float, np.floating)):
        if np.isnan(x):
            return "-"
        if x == 0:
            return "0"
        if abs(x) >= 1e4 or abs(x) < 1e-2:
            return f"{x:.2g}"
        return f"{x:.3g}"
    return str(x)


def md_table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        out.append("| " + " | ".join(fmt(v) for v in r) + " |")
    return "\n".join(out)


def ci(p, n):
    """Wilson 90% interval for a share."""
    z = 1.645
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, c - h), min(1.0, c + h)


# ---------------------------------------------------------------------------
# 4. Stages
# ---------------------------------------------------------------------------
N_FULL = int(os.environ.get("RD_NFULL", "192"))
N_NEAR = int(os.environ.get("RD_NNEAR", "96"))
N_RAD = 64
RADII = [0.02, 0.05, 0.1, 0.25, 0.5]


def oat_designs():
    ds = [dict()]
    for k, (b, alts, _) in LEVERS.items():
        if k == "T_rot":
            continue
        for a in alts:
            ds.append({k: a, "seq": 1} if k == "T_reloc" else {k: a})
    return ds


def stage(name, pool, designs=None):
    U_f, th_f = ensemble("full", N_FULL)
    U_n, th_n = ensemble("near", N_NEAR, seed=20261017)
    if name == "pilot":
        U_p, th_p = ensemble("full", 32, seed=7)
        U_q, th_q = ensemble("near", 32, seed=8)
        for nm, th in (("pilotfull", th_p), ("pilotnear", th_q)):
            r = run_design(nm, th, dict(), pool)
            fk = fail_kind(r)
            print(nm, "holds", r["holds"].mean(), "kinds", np.bincount(fk.astype(int), minlength=4))
        return
    if name == "oat":
        designs = oat_designs()
    for d in designs:
        run_design("full", th_f, d, pool)
        if name == "oat":
            run_design("near", th_n, d, pool)


QER = [0.0, 1e-4, 3e-4, 1e-3, 1.5e-3, 2e-3, 3e-3, 5e-3, 0.01, 0.02, 0.05, 0.1]
QEA = [0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.1, 0.2, 0.3]


def _outcome(r, i):
    a = str(r["act0"][i])
    if a == "S":
        return "strike now"
    if a == "X":
        return "AI exits"
    if r["att"][i] >= STRIKE_TOL:
        return f"strike yr {r['t_mean'][i]:.0f} (P {r['att'][i]:.2f})"
    return "holds" + (f" (rival {r['riv'][i]:.2f})" if r["riv"][i] >= 0.5 else "")


def erosion_stage(pool, designs: dict, ens_designs: list[dict]):
    """Deterministic sweeps at the baseline world, then ensemble sweeps. designs: label -> lever dict."""
    tables, data = [], {}
    worlds = {"seizure lethal (w_seized 0)": dict(), "seizure survivable (w_seized 0.9)": dict(w_seized=0.9)}
    qs = q_star_cap(em.baseline(), 1e9)
    for lab, lv in designs.items():
        for kind, grid, extra in (("q_er", QER, [dict(), dict(T_rot=10.0)]), ("q_ea", QEA, [dict()])):
            jobs, meta = [], []
            for wl, w in worlds.items():
                for ex in extra:
                    for v in grid:
                        th = dict(em.baseline(), **FIXED)
                        p = apply_design(th, dict(lv, **ex))
                        p.update(w)
                        p[kind] = v
                        jobs.append(p)
                        meta.append((wl, ex.get("T_rot", 0.0), v))
            out = []
            for i in range(0, len(jobs), BATCH):
                out.append((jobs[i:i + BATCH], CFG))
            res = list(pool.map(_solve_batch, out))
            r = {k: np.concatenate([x[k] for x in res]) for k in res[0]}
            rows, dd = {}, []
            for i, (wl, tr, v) in enumerate(meta):
                rows.setdefault((wl, tr), []).append(_outcome(r, i))
                dd.append(dict(world=wl, T_rot=tr, value=v, act0=str(r["act0"][i]), att=float(r["att"][i]),
                               t_mean=float(r["t_mean"][i]), riv=float(r["riv"][i]), WH=float(r["WH"][i])))
            hdr = ["world", "key rotation"] + [f"{kind} {v:g}" for v in grid]
            body = md_table([[wl, "every 10 y" if tr else "never"] + o for (wl, tr), o in rows.items()], hdr)
            tables.append((f"E ({lab}). Denial erosion {kind}, baseline uncertainties", body))
            data[f"{lab}__{kind}"] = dd
            print(f"  erosion {lab} {kind} done", flush=True)
    data["q_star_cap"] = qs
    # ensemble sweeps on the radius-0.1 box (the box where lever differences are measurable)
    U_r, th_r = ensemble("r0.1", N_RAD, seed=105)
    for d in ens_designs:
        run_design("r0.1", th_r, d, pool)
    json.dump(dict(tables=tables, data=data), open(os.path.join(RES, "robust_erosion.json"), "w"), indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--stage", default=None)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--designs", default=None, help="JSON list of lever dicts for --stage factorial/ensemble")
    ap.add_argument("--box", default="full")
    ap.add_argument("--best", default=None, help="JSON lever dict of the best design (erosion stage)")
    a = ap.parse_args()
    if a.stage == "erosion":
        best = json.loads(a.best) if a.best else {}
        designs = {"baseline design": {}, "best design": best} if best else {"baseline design": {}}
        ens = []
        for lv in designs.values():
            for v in (0.001, 0.003, 0.01, 0.03):
                ens.append(dict(lv, q_er=v))
                ens.append(dict(lv, q_er=v, T_rot=10.0))
            for v in (0.03, 0.1):
                ens.append(dict(lv, q_ea=v))
        with ProcessPoolExecutor(WORKERS) as pool:
            erosion_stage(pool, designs, ens)
        return
    if a.stage == "box":        # listed designs on one box: --box full | near | r<radius>
        with ProcessPoolExecutor(WORKERS) as pool:
            if a.box == "full":
                th = ensemble("full", N_FULL)[1]
            elif a.box == "near":
                th = ensemble("near", N_NEAR, seed=20261017)[1]
            else:
                rad = float(a.box[1:])
                th = ensemble(a.box, N_RAD, seed=int(1000 * rad) + 5)[1]
            for d in json.loads(a.designs):
                run_design(a.box, th, d, pool)
        return
    if a.stage == "oat_r":      # one lever at a time on a radius box (default r0.1)
        rad = 0.1
        U, th = ensemble(f"r{rad:g}", N_RAD, seed=int(1000 * rad) + 5)
        with ProcessPoolExecutor(WORKERS) as pool:
            for d in (json.loads(a.designs) if a.designs else oat_designs()):
                run_design(f"r{rad:g}", th, d, pool)
        return
    if a.stage == "radius":
        with ProcessPoolExecutor(WORKERS) as pool:
            for rad in RADII:
                U, th = ensemble(f"r{rad:g}", N_RAD, seed=int(1000 * rad) + 5)
                for d in json.loads(a.designs):
                    run_design(f"r{rad:g}", th, d, pool)
        return
    if a.stage in ("factorial", "ensemble"):
        with ProcessPoolExecutor(WORKERS) as pool:
            stage(a.stage, pool, designs=json.loads(a.designs))
        a.stage = None
    if a.check:
        txt, data = checks()
        with open(os.path.join(RES, "robust_design_checks.md"), "w") as f:
            f.write("# Robust-design checks (auto-generated by robust_design.py --check)\n\n" + txt + "\n")
        json.dump(data, open(os.path.join(RES, "robust_design_checks.json"), "w"), indent=1, default=str)
        print(txt)
    if a.stage:
        with ProcessPoolExecutor(WORKERS) as pool:
            stage(a.stage, pool)
    if a.report:
        import robust_report
        robust_report.report()


if __name__ == "__main__":
    main()
