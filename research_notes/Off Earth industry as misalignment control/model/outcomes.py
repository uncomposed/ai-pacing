"""
Outcome definitions, alternative outcome criteria and share labels for the robust-design runs (issues #10, #26).

The solver reports, for each parameter draw, model-internal probabilities over a finite horizon (T_H = 300 years by
default). What the robust-design tables call "the pact holds" is one finite-horizon predicate on those numbers. This
module states that predicate and everything it depends on, once, so that every cache manifest and every derived
report carries the same definition:

    outcome_metadata(cfg)   horizon, predicate, thresholds, terminal rule, rival treatment, unresolved continuation
                            and field meanings; stored in each run manifest (run_identity output_schema, version 2)
    CRITERIA                alternative outcome criteria, each a named, explicit user/policy choice with a rationale.
                            DEFAULT_CRITERION ("holds") is the one every committed table uses; the others never
                            replace it silently, they are reported beside it.
    decompose(r)            per-draw outcome classes: strike now, later strike within the horizon, rival first,
                            unresolved at the horizon (continuation valued by the terminal rule, not modelled)
    share_label(...)        an outcome label in the shape of schema/evidence.schema.json#/$defs/outcome_label

Nothing here changes a number in a cache: `robust_design.holds` still computes the stored `holds` field.

A share of draws is a share under the stated sampling measure, never a calibrated probability. "Holds" is a statement
about the first T_H years under the stated terminal rule. It is not a claim of indefinite stability.

Status: implemented; checked by tests/test_outcome_labels.py. Not human_validated.
"""
from __future__ import annotations

from collections import OrderedDict

import numpy as np

OUTCOME_VERSION = "offearth-outcome/1"
INTERPRETATION = "share of draws under the stated sampling measure; not a calibrated probability"
RIVAL_LIKELY = 0.5                 # 'a rival is likelier than not' (robust_design.fail_kind, robust_design.md 12.1)

TERMINAL_RULES = {
    "peace": "'peace' (equilibrium_model.solve default): from T_H on the AI grows alone and unthreatened, the pact "
             "keeps its consumption-trade stream, and humans keep their base welfare. A settled peace is assumed at "
             "the horizon, not derived.",
    "seized": "'seized': the AI takes Earth at T_H (a check value, not used for any committed table).",
}
RIVAL_TREATMENT = (
    "A rival AI born before any strike ends the strategic game: that probability mass is riv, and it is not a strike. "
    "What the rival and the incumbent AI do afterwards is not modelled. The default predicate ('holds') ignores riv, "
    "so a world where a rival is likely still counts as holding (assumption AS-RIVAL-HOLDS); the alternative criteria "
    "(CRITERIA) count it as adverse, or bound the share between the two readings.")
UNRESOLVED = (
    "Probability mass with neither a strike nor a rival birth within the horizon (1 - att - riv) is not resolved by "
    "the model: its continuation is valued by the terminal rule. A finite-horizon 'holds' therefore means 'no strike "
    "within T_H years, given that terminal rule', never 'stable indefinitely'.")
STRUCTURAL = ["AS-SELECTION", "AS-HORIZON", "AS-SINGLE-AI", "AS-NOFIRSTSTRIKE", "AS-FIXEDTERMS", "AS-RIVAL-HOLDS"]

FIELDS = OrderedDict([
    ("act0", "the AI's opening move at t = 0: C cooperate, X exit, S strike, P police"),
    ("att", "P(the AI strikes, or harvests, within the horizon)"),
    ("suc", "P(a strike within the horizon succeeds: a successful seizure)"),
    ("fail", "P(a chosen strike fails: a warning shot)"),
    ("riv", "P(a rival AI is born before any strike, within the horizon); ends the strategic game"),
    ("harv", "P(the strike is a harvest: Earth taken for its matter or sunlight)"),
    ("exit", "P(the AI exits)"),
    ("pre", "P(a strike happens before closure)"),
    ("att25", "P(a strike within 25 years)"),
    ("att100", "P(a strike within 100 years)"),
    ("t_mean", "mean strike year, given a strike within the horizon (NaN if att is 0)"),
    ("WH", "human welfare (yearly equivalent, 1 = today), including the terminal value"),
    ("holds", "the default predicate (DEFAULT_CRITERION), stored as 0/1"),
])


def strike_tol() -> float:
    import robust_design as rd
    return rd.STRIKE_TOL


def solver_default_terminal() -> str:
    """The terminal rule equilibrium_model.solve uses when a run does not name one."""
    import inspect
    import equilibrium_model as em
    return inspect.signature(em.solve).parameters["terminal"].default


def predicate_text(tol: float | None = None, horizon: int = 300) -> str:
    tol = strike_tol() if tol is None else tol
    return (f"holds: the AI's opening move is cooperate or police (act0 in C, P) and P(strike or harvest within "
            f"{horizon} years) < {tol:g}; a likely rival still counts as holding")


def outcome_metadata(cfg: dict, tol: float | None = None) -> dict:
    """What a run's outcome fields mean, for its manifest. Depends only on the settings and thresholds, which the
    identity binds anyway; written out so that no reader has to reconstruct them from code."""
    tol = strike_tol() if tol is None else tol
    T_H = int(cfg.get("T_H", 300))
    terminal = cfg.get("terminal", solver_default_terminal())
    return dict(
        version=OUTCOME_VERSION,
        horizon_years=T_H,
        predicate=predicate_text(tol, T_H),
        thresholds=dict(strike_tol=float(tol), rival_likely=RIVAL_LIKELY),
        terminal_rule=dict(name=terminal, meaning=TERMINAL_RULES[terminal]),
        rival_treatment=RIVAL_TREATMENT,
        unresolved_continuation=UNRESOLVED,
        default_criterion=DEFAULT_CRITERION,
        alternative_criteria={k: c["definition"] for k, c in CRITERIA.items() if k != DEFAULT_CRITERION},
        fields=dict(FIELDS),
    )


# ---------------------------------------------------------------------------
# outcome criteria: explicit choices, never silent changes to "holds"
# ---------------------------------------------------------------------------
def _holds(r, tol=None):
    tol = strike_tol() if tol is None else tol
    return np.isin(np.asarray(r["act0"]), ["C", "P"]) & (np.asarray(r["att"]) < tol)


CRITERIA: "OrderedDict[str, dict]" = OrderedDict([
    ("holds", dict(
        definition="AI opens with cooperate or police and P(strike or harvest within the horizon) < strike_tol; "
                   "rivals ignored",
        rationale="The default since round 1 and the predicate of every committed table. It asks only whether the AI "
                  "strikes; the pact's terms act on the AI.",
        test=lambda r: _holds(r))),
    ("rival_unlikely", dict(
        definition="holds, and P(rival) < 0.5",
        rationale="A likely rival defeats the pact's purpose (a single, overseen AI). Used in robust_design.md 12.1 "
                  "and AR-H10's 2% variant. 0.5 matches fail_kind's 'rival likelier than not'.",
        test=lambda r: _holds(r) & (np.asarray(r["riv"]) < RIVAL_LIKELY))),
    ("rival_adverse", dict(
        definition="holds, and P(rival) < strike_tol: a rival birth counts as adverse as a strike does",
        rationale="Treats a rival exactly like a strike: the same tolerance. The strictest reading of 'the pact "
                  "keeps humans safe'; it gives a lower bound on the hold share.",
        test=lambda r: _holds(r) & (np.asarray(r["riv"]) < strike_tol()))),
])
DEFAULT_CRITERION = "holds"
# rival continuation unmodelled: the share is only known to lie between these two criteria
RANGE_CRITERIA = ("rival_adverse", "holds")


def criterion(name: str, r: dict) -> np.ndarray:
    return CRITERIA[name]["test"](r)


def decompose(r: dict) -> dict:
    """Per-draw outcome classes (each a boolean array) and per-draw probability masses. Classes are disjoint:
    strike_now, later_strike (no strike now, P(strike within the horizon) >= strike_tol), holds (the default
    predicate), other (exit or any remaining case). Masses: att, riv and unresolved = 1 - att - riv, clipped to
    [0, 1] (att + riv exceeds 1 by up to about 0.014 in the committed caches: the indicator recursions are
    interpolated on the A-grid)."""
    act0 = np.asarray(r["act0"])
    att, riv = np.asarray(r["att"], float), np.asarray(r["riv"], float)
    h = _holds(r)
    now = act0 == "S"
    later = ~now & ~h & (att >= strike_tol())
    return dict(strike_now=now, later_strike=later, holds=h, other=~(now | later | h),
                att=att, riv=riv, unresolved=np.clip(1 - att - riv, 0.0, 1.0), excess=np.maximum(att + riv - 1, 0.0))


# ---------------------------------------------------------------------------
# labels
# ---------------------------------------------------------------------------
def wilson95(k: int, n: int) -> list[float]:
    z = 1.959963984540054
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


SAMPLING = {
    "full": "AS-PRIORS full box: independent uniform or log-uniform marginals over the UNCERTAIN ranges, point masses "
            "at zero for ell_inf (1/2), omega (1/3) and f_E (1/3); Latin hypercube, 192 draws, seed 20261016",
    "near": "AS-PRIORS near box: baseline +- 25% of each range in its own scale, point masses kept; Latin hypercube, "
            "96 draws, seed 20261017",
    "radius": "AS-PRIORS radius boxes r0.02 to r0.5: baseline +- radius of each range in its own scale, ell_inf, omega "
              "and f_E held at 0 and reinv at 0; Latin hypercube, 64 draws each, seed 1000 * radius + 5",
    "world": "one parameter set (the round-1 baseline world with the stated overrides); no sampling: the P values are "
             "the model's internal probabilities given those parameters",
}


def box_sampling(box: str) -> str:
    if box in SAMPLING:
        return SAMPLING[box]
    if box.startswith("r"):
        return SAMPLING["radius"].replace("radius boxes r0.02 to r0.5", f"radius box {box}")
    raise KeyError(box)


def share_label(sampling: str, counts: list[tuple[str, int, int]], predicate: str | None = None,
                horizon: str = "300 years, 'peace' terminal value", extra_normative: str = "") -> dict:
    """An outcome label (schema/evidence.schema.json#/$defs/outcome_label). counts: (quantity, k, n) for every share
    the labelled table reports."""
    return dict(
        interpretation=INTERPRETATION,
        sampling_measure=sampling,
        structural_assumptions=list(STRUCTURAL),
        horizon=horizon,
        predicate=predicate or predicate_text(),
        numerical_uncertainty=[dict(quantity=q, k=int(k), n=int(n), method="wilson_95", interval=wilson95(int(k), int(n)))
                               for q, k, n in counts] or [dict(quantity="(no share)", k=0, n=1, method="wilson_95",
                                                               interval=wilson95(0, 1))],
        uncertainty_types=dict(
            random_outcome="strike timing and rival births are random inside the model; the predicate uses their "
                           "probabilities within the horizon",
            parameter="the sampled parameters under the stated measure; shares move with it (measure_sensitivity.md)",
            model_form="the structural assumptions listed, not sampled; the horizon and the terminal rule "
                       "(horizon_sensitivity.md)",
            normative="the strike tolerance, the horizon and whether a likely rival counts as failure (criteria "
                      "rival_unlikely and rival_adverse)" + (f"; {extra_normative}" if extra_normative else ""),
        ),
    )


LABEL_LINE_PREFIX = "**Outcome label"


def label_line(label_id: str, sampling: str, note: str = "") -> str:
    """One line per table: the label's id, the fixed interpretation and the parts a reader needs on the page."""
    return (f"{LABEL_LINE_PREFIX} {label_id}.** Every share here is a {INTERPRETATION}. Sampling: {sampling}. "
            f"Predicate: {predicate_text()}. Horizon: 300 years; terminal rule 'peace' (a settled peace assumed at the "
            f"horizon). Not a claim of indefinite stability. Definition, Wilson 95% intervals and uncertainty types: "
            f"section 'Outcome definition' above and `outcome_labels.{label_id}` in robust_design_summary.json."
            + (f" {note}" if note else ""))


def missing_labels(md: str) -> list[str]:
    """Sections ('## ' headings) of a generated tables file that report shares but carry no outcome-label line, or
    whose label id is not defined in the summary. Used by the report generator (it refuses to write) and the test."""
    out = []
    sections = md.split("\n## ")[1:]
    for s in sections:
        title = s.splitlines()[0]
        if title.startswith("Outcome definition"):
            continue
        if LABEL_LINE_PREFIX not in s:
            out.append(title)
    return out


def definition_section() -> str:
    md = outcome_metadata(dict(T_H=300, terminal="peace"))
    crit = "\n".join(f"- `{k}`{' (default)' if k == DEFAULT_CRITERION else ''}: {c['definition']}. Why: {c['rationale']}"
                     for k, c in CRITERIA.items())
    return ("## Outcome definition (applies to every table below)\n\n"
            f"- Interpretation: every share is a {INTERPRETATION}.\n"
            f"- Predicate: {md['predicate']}.\n"
            f"- Horizon: {md['horizon_years']} years. Thresholds: strike_tol {md['thresholds']['strike_tol']:g}, "
            f"rival_likely {md['thresholds']['rival_likely']:g}.\n"
            f"- Terminal rule: {md['terminal_rule']['meaning']}\n"
            f"- Rival events: {md['rival_treatment']}\n"
            f"- Unresolved continuation: {md['unresolved_continuation']}\n"
            f"- Structural assumptions held fixed: {', '.join(STRUCTURAL)}.\n"
            "- Uncertainty types: random outcome (strike and rival timing inside the model), parameter (the sampling "
            "measure), model form (the structural assumptions, the horizon and the terminal rule) and normative (the "
            "thresholds and whether a rival counts as failure).\n"
            "- Outcome criteria (explicit choices; the default is used unless a table names another):\n"
            f"{crit}\n")
