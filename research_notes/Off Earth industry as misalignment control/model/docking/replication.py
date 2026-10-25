"""Pinned replication gate for the two docks that reproduce a published model (issue #7, 2026-10-25).

    python3 docking/replication.py                 # every check (about 2 minutes); exit 1 on any failure
    python3 docking/replication.py --only clark    # or saklakov
    python3 docking/replication.py --self-test     # break the solver on purpose; exit 0 only if the gate fails
    python3 docking/replication.py --out status.json

Every expected quantity below is pinned in this file: a closed form from the source or a number printed in it.
Nothing is read from docking/out/, so regenerating those files cannot make this gate pass. Each check states its
tolerance and why. Passing establishes that our solver, set to the source's limit, reproduces the source model's
own results. It does not establish that the source's assumptions are true, or anything about the real world.

What the other three docks are (they are not run here; docking.yml runs them as the slow suite):
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

from _common import md_table
import equilibrium_model as em

SOURCES = {
    "saklakov": dict(
        kind="replication (exact parameter limit of our solver)",
        source="Saklakov 2026, arXiv:2601.04234: comply-versus-confront MDP, Lemmas 1-2 and Table 1",
        omissions=["Stationarity: his 'confront now or never' (footnote 3) has no counterpart test; our model is not "
                   "stationary.",
                   "Theorem 2 (humans pre-empt when Delta >= 0): our humans cannot strike first, so only the AI's "
                   "opening move is compared.",
                   "Success-probability extension s* (docking/saklakov.py section 4) is ours, not his; not gated here.",
                   "Table 1 values were transcribed into docking/saklakov.py on 2026-10-21; this PR did not re-read "
                   "the source."]),
    "clark": dict(
        kind="replication of a closed-form ledger (term-for-term identity) plus solver sign agreement",
        source="Clark 2026, arXiv:2609.00109, section 4.4 removal row R4 and its corollary 'S > d => never remove'",
        omissions=["Clark prints no numbers; the gate checks the ledger's form and corollary, not published values.",
                   "Compliance-capture and welfare-goal responses (his 2 and 3) have no counterpart in our model.",
                   "Bypass row Rb is not docked (our off-Earth growth recovers none of the rival discount d).",
                   "The solver's strike-minus-comply gap differs from R4 by up to 0.009 per year in the comply "
                   "region (docking.md section 4); the cause is not established, so it is reported, not gated."]),
    "powell": dict(kind="interpretive comparison, not a replication",
                   source="Powell 2006, International Organization 60(1)",
                   note="Evaluates Powell's inefficiency condition (1) on our own quantities. No second "
                        "implementation and no published numbers are reproduced."),
    "potapov": dict(kind="qualitative direction check, not a replication",
                    source="Potapov 2026, arXiv:2606.30666",
                    note="Potapov has no formal model. Tests a formalisation we wrote of his suggested "
                         "dependence variable, and the sign of a patience sweep of our full model."),
    "metzger": dict(kind="data comparison against a digitised figure, not a replication",
                    source="Metzger et al. 2013, arXiv:1612.03238, Fig. 2",
                    note="Growth rates compared with values read by eye (+/-15%) from his figure; his "
                         "spreadsheet model is unreleased, so no model output is reproduced."),
}
__doc__ += "".join(f"    {k}: {v['kind']}. {v['note']}\n" for k, v in SOURCES.items() if "note" in v)

RESULTS: list = []


def record(source, name, ok, detail, tol=None, why=None):
    RESULTS.append(dict(source=source, check=name, ok=bool(ok), detail=detail, tolerance=tol, justification=why))


# ---------------------------------------------------------------------------
# Saklakov
# ---------------------------------------------------------------------------
# (gamma, p, C, Delta as printed in his Table 1, decimals printed)
SAK_TABLE1 = [(0.99, 0.01, 1, 47.8, 1), (0.99, 0.01, 50, -1.3, 1), (0.9, 0.1, 3, 0.74, 2), (0.9, 0.1, 5, -1.26, 2),
              (0.5, 0.5, 1, -1.33, 2), (0.5, 0.5, 0, -0.33, 2)]
# Declared source discrepancy: row 1 recomputes to 47.749, which rounds to 47.7, not the printed 47.8.
SAK_PRINT_EXCEPTIONS = {0: 0.06}
SAK_CSTAR = [(0.99, 0.01), (0.9, 0.1), (0.95, 0.05), (0.99, 0.001), (0.999, 0.01)]
SAK_GSTAR = [0.5, 0.1, 0.01, 0.001]
EPS = 1e-6          # relative offset either side of a closed-form switch point


def saklakov_checks():
    import saklakov as sk
    t0 = time.time()
    # 1. The source's own arithmetic: our recomputation of Delta against his printed Table 1
    for i, (g, p, C, printed, dec) in enumerate(SAK_TABLE1):
        dl = sk.sak(g, p, C)[2]
        tol = SAK_PRINT_EXCEPTIONS.get(i, 0.5 * 10 ** -dec + 1e-12)
        record("saklakov", f"Table 1 row {i + 1} Delta printed", abs(dl - printed) <= tol,
               f"recomputed {dl:+.4f}, printed {printed:+g}", tol,
               "half a unit in the last printed digit" if i not in SAK_PRINT_EXCEPTIONS else
               "declared source rounding discrepancy (47.749 printed as 47.8)")
    # 2-4. one batched solve: Table 1 rows, C* brackets, gamma* brackets
    sets, meta = [], []
    for g, p, C, _, _ in SAK_TABLE1:
        sets.append(sk.params(g, p, C))
        meta.append(("row", (g, p, C)))
    for g, p in SAK_CSTAR:
        cs = sk.C_star(g, p)
        sets += [sk.params(g, p, cs * (1 - EPS)), sk.params(g, p, cs * (1 + EPS))]
        meta += [("cstar_lo", (g, p, cs)), ("cstar_hi", (g, p, cs))]
    for p in SAK_GSTAR:
        gs = sk.gamma_star0(p)
        sets += [sk.params(gs * (1 - EPS), p, 0.0), sk.params(gs * (1 + EPS), p, 0.0)]
        meta += [("gstar_lo", (gs, p)), ("gstar_hi", (gs, p))]
    act, VC, VS, nm = sk.run(sets)
    record("saklakov", "no mixed-strategy fallback", nm == 0, f"n_mixed = {nm}", 0,
           "the docked limit has no human play, so the stage game is never mixed")
    for i, (kind, a) in enumerate(meta):
        if kind == "row":
            g, p, C = a
            vf, vc, dl = sk.sak(g, p, C)
            record("saklakov", f"Table 1 ({g}, {p}, {C}) opening move", (act[i] == "S") == (dl > 0),
                   f"solver {act[i]}, Delta {dl:+.3f}", None, "sign of Delta decides confront (S) or comply (C)")
            # The AI's grid floor is 1e-5 of A0; in the row where the cost uses up the whole AI the landing point
            # sits on that floor (docking.md section 3): 1e-4 absolute covers it. Other rows: 1e-8 relative
            # (observed <= 1e-10), well below any value Saklakov prints.
            tol = 1e-4 if (g, p, C) == (0.5, 0.5, 1) else 1e-8 * max(1.0, abs(vf))
            record("saklakov", f"V_confront ({g}, {p}, {C})", abs(VS[i] - vf) <= tol,
                   f"solver {VS[i]:.10g}, Saklakov {vf:.10g}, error {VS[i] - vf:.2e}", tol,
                   "grid-floor landing point" if tol == 1e-4 else "float accumulation over 1500 backward steps")
            if dl < 0:
                fn = sk.finite_never(g, p)
                record("saklakov", f"V_comply ({g}, {p}, {C}) with our finite horizon", abs(VC[i] - fn) <= 1e-6 * fn,
                       f"solver {VC[i]:.10g}, closed form {fn:.10g}, error {VC[i] - fn:.2e}", "1e-6 relative",
                       "observed <= 5e-8 absolute; the horizon itself is in the closed form (finite_never)")
    for k in range(0, len(meta), 1):
        kind, a = meta[k]
        if kind == "cstar_lo":
            g, p, cs = a
            lo, hi = act[k], act[k + 1]
            b = g * (1 - p)
            trunc = b ** sk.T_H * (1 / (1 - g) - 1 / (1 - b))
            record("saklakov", f"C* ({g}, {p}) = {cs:.6g}", lo == "S" and hi == "C" and trunc < EPS * cs / 10,
                   f"solver at C*(1-1e-6): {lo}, at C*(1+1e-6): {hi}; horizon shift bound {trunc:.1e}",
                   "1e-6 relative", "Lemma 2; the finite horizon moves the switch by at most the printed bound, "
                   "checked to be under a tenth of the offset")
        if kind == "gstar_lo":
            gs, p = a
            lo, hi = act[k], act[k + 1]
            record("saklakov", f"gamma* (p = {p}) = {gs:.6g}", lo == "C" and hi == "S",
                   f"solver at gamma*(1-1e-6): {lo}, at gamma*(1+1e-6): {hi}", "1e-6 relative",
                   "Lemma 1 at C = 0: patient AIs confront")
    return time.time() - t0


# ---------------------------------------------------------------------------
# Clark
# ---------------------------------------------------------------------------
CLARK_FLIP = (0.40, 0.45)       # the ledger's own sign change, docking.md section 4 (q = 0.446)


def clark_checks(solver=True):
    import clark as ck
    t0 = time.time()
    # 1. Identity: Clark's R4 built from our quantities equals our closed form cap_gap_fail, term for term
    for name, w in ck.WORLDS:
        L = ck.ledger(em.baseline(**w))
        err = abs(L["R4"] - L["cap_gap_fail"])
        tol = 1e-9 * max(1.0, abs(L["R4"]))
        record("clark", f"R4 = cap_gap_fail: {name}", err <= tol, f"R4 {L['R4']:+.6g}, ours {L['cap_gap_fail']:+.6g}",
               "1e-9 relative", "an algebraic identity; only float rounding separates the two codings")
        record("clark", f"S > d corollary: {name}", (L["S"] > L["d"]) == (L["R4_silent"] < 0),
               f"S {L['S']:+.4g}, d {L['d']:.4g}, R4 silent {L['R4_silent']:+.4g}", None,
               "with silent failure removal pays exactly when S < d")
    # 2. The corollary's threshold is our q_star_cap(fail=False) at the same capacity
    p0 = em.baseline(mu=0.0, beta_bg=0.0)
    A = p0["Kmax"] * 1.000001
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if ck.ledger(dict(p0, q=mid, d=1.0), A=A, F=0.0)["d_minus_S"] > 0:
            lo = mid
        else:
            hi = mid
    qs = em.q_star_cap(p0, d=1.0, fail=False)
    # Conditioning: both gaps are differences of values of order A/(1 - delta), and the gap moves with q at
    # (1 - rep)(1 - c_w) H d per year, so one rounding unit of A moves the root by eps A / ((1 - rep)(1 - c_w) H).
    unit = np.finfo(float).eps * A / ((1 - p0["rep"]) * (1 - p0["c_w"]) * p0["H"])
    record("clark", "q where S = d equals q_star_cap(fail=False)", abs(hi - qs) <= 4 * unit,
           f"ledger {hi:.12f}, q_star_cap {qs:.12f}, difference {hi - qs:.1e}", f"{4 * unit:.1e} (4 rounding units)",
           "the two codings cancel large terms in different orders; a root shift of one rounding unit of A is "
           f"{unit:.1e}")
    if not solver:
        return time.time() - t0
    # 3. Solver opening move against the sign of R4: saturated start, humans never start programmes
    qv = np.linspace(0.0, 1.0, 21)
    base = dict(A0=ck.A_SAT, seq=3, B_R=0.0, B_Rc=0.0)
    plist = [em.baseline(**base, q=q) for q in qv]
    res = em.solve(em.batch(plist), N=2, T_H=300, nA=160)
    signs = [(ck.ledger(plist[i], F=1.0)["R4"] > 0) == (res["act0"][i] == "S") for i in range(len(qv))]
    record("clark", "solver act0 agrees with sign of R4 (21 q values)", all(signs), f"{sum(signs)}/21 agree", None,
           "sign agreement is exact; no tolerance")
    strike = [float(q) for q, a in zip(qv, res["act0"]) if a == "S"]
    comply = [float(q) for q, a in zip(qv, res["act0"]) if a != "S"]
    ok = bool(strike) and bool(comply) and math.isclose(max(strike), CLARK_FLIP[0]) and math.isclose(min(comply), CLARK_FLIP[1])
    record("clark", "solver switch between q = 0.40 and 0.45", ok,
           f"last strike q {max(strike) if strike else None}, first comply q {min(comply) if comply else None}",
           None, "the ledger flips at q = 0.446")
    return time.time() - t0


# ---------------------------------------------------------------------------
def summary_md(results, title):
    bad = [r for r in results if not r["ok"]]
    rows = [[r["source"], r["check"], "pass" if r["ok"] else "**FAIL**", r["detail"], r["tolerance"] if r["tolerance"] is not None else "exact"]
            for r in results]
    return (f"### {title}: {'FAIL' if bad else 'pass'} ({len(results) - len(bad)}/{len(results)} checks)\n\n"
            + md_table(rows, ["source", "check", "result", "detail", "tolerance"]) + "\n\nA pass shows reproduction "
            "of the source model in its limit, not truth of its assumptions or predictive validity.\n")


def emit(md):
    print(md)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as f:
            f.write(md + "\n")


def self_test():
    """Break cap_strike_gap by 1% and confirm the Clark identity checks fail. Exit 0 only if they do."""
    real = em.cap_strike_gap
    em.cap_strike_gap = lambda p, A, F=1.0, dt=1.0: real(p, A, F, dt) * 1.01
    try:
        clark_checks(solver=False)
    finally:
        em.cap_strike_gap = real
    failed = [r for r in RESULTS if not r["ok"]]
    emit(f"### Replication gate self-test\n\nWith `cap_strike_gap` deliberately scaled by 1.01, "
         f"{len(failed)} of {len(RESULTS)} Clark checks fail, as they must.\n" if failed else
         "### Replication gate self-test FAILED\n\nA deliberately broken solver passed the Clark checks.\n")
    return 0 if failed else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["saklakov", "clark"], default=None)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", default=None, help="write the check list and sources as JSON")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    secs = {}
    if a.only in (None, "clark"):
        secs["clark"] = clark_checks()
    if a.only in (None, "saklakov"):
        secs["saklakov"] = saklakov_checks()
    emit(summary_md(RESULTS, "Replication gate (Saklakov, Clark)"))
    bad = [r for r in RESULTS if not r["ok"]]
    if a.out:
        with open(a.out, "w") as f:
            json.dump(dict(category="external-model replication", status="fail" if bad else "pass", seconds=secs,
                           sources=SOURCES, checks=RESULTS), f, indent=1, default=str)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
