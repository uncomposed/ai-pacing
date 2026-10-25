"""Outcome measures kept separate, and policy-ranking reversals (issue #9).

Every variant run reports, per (structure, policy):
    conflict_year     first year of open conflict (AI strike or human shutdown attempt), conditional mean; None = none
    P_ai_strike       probability the AI ever strikes
    successful_harm   P(successful seizure) x (1 - w_seized): the expected share of human welfare a seizure destroys
    control_retained  P(no successful seizure within the horizon)
    V_H               human welfare (discounted at r_h)
    distribution      the AI's value and the humans' value, compared with the reference policy (who gains, who loses)
A policy's sign on a measure is +1 (better for humans), -1 (worse) or 0 (|difference| below TOL). A reversal is a
measure on which a policy is better than the reference in one structure and worse in another; a conflict is a structure
in which a policy is better on one measure and worse on another. No averaging over structures is done: the stopping
rule of #9 keeps conditional conclusions instead.
"""
from __future__ import annotations

TOL = 1e-6
RANKED = ("conflict_year", "P_ai_strike", "successful_harm", "control_retained", "V_H")
BETTER_HIGH = {"conflict_year": True, "P_ai_strike": False, "successful_harm": False, "control_retained": True,
               "V_H": True}


def measures_preventive(r: dict, w_seized: float) -> dict:
    ys = [y for y, pr in ((r["strike_year"], r["att"]), (r["shutdown_year"], r["hk"])) if y is not None and pr > 0.01]
    return dict(conflict_year=min(ys) if ys else None, P_ai_strike=r["att"],
                successful_harm=r["P_seizure"] * (1 - w_seized), control_retained=r["control_retained"],
                V_H=r["V_H"], V_A_excess=r["E_A"], P_human_first=r["hk"], P_warning_shot=r["fail"],
                P_ai_eliminated=r["dead"])


def measures_bargaining(r: dict, w_seized: float) -> dict:
    return dict(conflict_year=r["strike_year"], P_ai_strike=1.0 if r["strike_year"] is not None else 0.0,
                successful_harm=r["P_seizure"] * (1 - w_seized), control_retained=r["control_retained"],
                V_H=r["V_H"], V_A_excess=r["V_A"], pv_transfer_H=r["pv_transfer_H"])


def sign(m: str, a, b) -> int:
    """Sign of policy value a against reference b on measure m, from the humans' side."""
    if m == "conflict_year":                      # None (no conflict) is the latest possible
        a = float("inf") if a is None else a
        b = float("inf") if b is None else b
        if a == b or abs(a - b) < 0.5:            # timing is reported in years; under half a year is a tie
            return 0
        return 1 if a > b else -1
    d = a - b
    if abs(d) <= TOL * max(1.0, abs(a), abs(b)):
        return 0
    return (1 if d > 0 else -1) * (1 if BETTER_HIGH[m] else -1)


def distribution(mp: dict, mr: dict) -> str:
    dh = mp["V_H"] - mr["V_H"]
    da = mp["V_A_excess"] - mr["V_A_excess"]
    f = lambda x, s: "same" if abs(x) <= TOL * max(1.0, abs(s)) else ("gain" if x > 0 else "loss")
    return f"humans {f(dh, mr['V_H'])}, AI {f(da, mr['V_A_excess'])}"


def analyse(table: dict, reference: str) -> dict:
    """table[structure][policy] = measures. Returns signs, cross-structure reversals and within-structure conflicts."""
    structures = list(table)
    policies = [p for p in table[structures[0]] if p != reference]
    signs, reversals, conflicts, dist = {}, [], [], {}
    for p in policies:
        signs[p] = {s: {m: sign(m, table[s][p][m], table[s][reference][m]) for m in RANKED} for s in structures}
        dist[p] = {s: distribution(table[s][p], table[s][reference]) for s in structures}
        for m in RANKED:
            better = [s for s in structures if signs[p][s][m] > 0]
            worse = [s for s in structures if signs[p][s][m] < 0]
            if better and worse:
                reversals.append(dict(policy=p, measure=m, better_in=better, worse_in=worse))
        for s in structures:
            up = [m for m in RANKED if signs[p][s][m] > 0]
            down = [m for m in RANKED if signs[p][s][m] < 0]
            if up and down:
                conflicts.append(dict(policy=p, structure=s, better_on=up, worse_on=down))
    return dict(reference=reference, signs=signs, reversals=reversals, conflicts=conflicts, distribution=dist)
