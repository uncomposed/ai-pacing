"""EXTENSION (issue #49), not AIFM behaviour: a review/integration throughput cap.

The pinned AI Futures Model turns every unit of research effort into research stock:
d(RS)/dt = RE(t, logE). This extension inserts one stage between the two, so that only
effort that a review/integration stage can absorb counts as validated progress:

    d(RS)/dt = min( RE(t, logE),  kappa * RE_human(t) )

RE_human(t) is the upstream's own human-only research effort at time t (automation 0,
aggregate taste 1, coding labor from human FTEs, same experiment compute), computed with
the upstream's compute_research_effort. kappa is the largest multiple of a no-AI lab's
research throughput that review and integration can validate. kappa = inf is the upstream.

How it is applied: at run time, inside a context manager, the name
`progress_model.integration.progress_rate_at_time` (the right-hand side that the
upstream's `integrate_progress` ODE calls) is rebound to a wrapper that caps the second
rate. Nothing on disk is changed; the original is restored on exit. Every other part of
the upstream runs unchanged, including the calibration of r_software, the uplift
reconstruction and the automation-schedule anchoring, which never call that name. So the
cap acts on the realized trajectory only, with the upstream's calibration held fixed.

Not changed by the cap, and therefore not adjusted (read with care):
- `results["research_efforts"]` and every multiplier derived from it (AIR-*x, AI2027-SC)
  are the upstream's post-hoc *demand* for research effort at the capped state, not the
  validated flow. `cap_diagnostics` reports the validated flow separately.
- Milestones defined on progress (AC, SAR, SIAR, STRAT-AI, TED-AI, ASI) are fine: their
  thresholds are functions of progress and are fixed before integration.
"""

from __future__ import annotations

import math
from contextlib import contextmanager

PATCH_TARGET = "progress_model.integration.progress_rate_at_time"

EXTENSION_LABEL = ("EXTENSION by this project (issue #49), not AIFM behaviour: research stock grows at "
                   "min(RE, kappa * RE_human); the pinned upstream is unmodified and the cap is applied by "
                   f"rebinding {PATCH_TARGET} at run time.")


def human_only_research_effort(t, data, params):
    """RE_human(t): the upstream's human-only research effort at time t (scalar or array).

    Same inputs and interpolation as progress_rate_at_time / integrate_progress_human_only:
    log-space interpolation where the upstream uses it, serial coding labor
    L_HUMAN ** parallel_penalty * coding_labor_normalization, aggregate taste 1.
    """
    import numpy as np
    from progress_model.progress_rate import compute_research_effort

    if data.can_use_log_L_HUMAN:
        L = np.exp(np.interp(t, data.time, data.log_L_HUMAN))
    else:
        L = np.interp(t, data.time, data.L_HUMAN)
    if data.can_use_log_experiment_H100e:
        X = np.exp(np.interp(t, data.time, data.log_experiment_H100e))
    else:
        X = np.interp(t, data.time, data.experiment_H100e)
    coding = np.power(np.maximum(L, 0.0), params.parallel_penalty) * params.coding_labor_normalization
    return compute_research_effort(np.maximum(X, 0.0), coding, params.alpha_experiment_capacity,
                                   params.rho_experiment_capacity, params.experiment_compute_exponent, 1.0)


def capped_rhs(original, kappa):
    """Wrap the upstream ODE right-hand side so d(RS)/dt <= kappa * RE_human(t)."""

    def rhs(t, state, time_series_data, params, RS_0=None, **kw):
        rates = original(t, state, time_series_data, params, RS_0=RS_0, **kw)
        if getattr(params, "human_only", False) or math.isinf(kappa):
            return rates
        cap = kappa * float(human_only_research_effort(t, time_series_data, params))
        if rates[1] > cap:
            rates = [rates[0], cap]
        return rates

    rhs.__wrapped__ = original
    rhs.review_cap_kappa = kappa
    return rhs


def install(kappa: float):
    """Rebind the upstream ODE right-hand side to the capped one; returns the original."""
    if not (kappa > 0):
        raise ValueError(f"kappa must be positive (inf disables the cap), got {kappa}")
    import progress_model.integration as integration

    original = integration.progress_rate_at_time
    if hasattr(original, "review_cap_kappa"):
        raise RuntimeError("review_cap is already active; nesting is not supported")
    integration.progress_rate_at_time = capped_rhs(original, kappa)
    return original


def active_kappa():
    """The kappa currently installed, or None when the upstream right-hand side is in place."""
    import progress_model.integration as integration

    return getattr(integration.progress_rate_at_time, "review_cap_kappa", None)


@contextmanager
def review_cap(kappa: float):
    """Apply the cap to every upstream `integrate_progress` call inside the block."""
    original = install(kappa)
    try:
        yield
    finally:
        import progress_model.integration as integration

        integration.progress_rate_at_time = original


def cap_series(model, kappa: float) -> dict:
    """Arrays on the output grid of a finished run: demand, cap, expected and integrated flow.

    demand is the upstream's post-hoc research effort at the (capped) state; flow is
    d(RS)/dt read off the integrated research stock, which should equal min(demand, cap)
    up to integration error.
    """
    import numpy as np

    r = model.results
    t = np.asarray(r["times"], dtype=float)
    demand = np.asarray(r["research_efforts"], dtype=float)
    re_h = np.asarray(human_only_research_effort(t, model.data, model.params), dtype=float)
    cap = kappa * re_h
    return {"times": t, "demand": demand, "re_human": re_h, "cap": cap,
            "expected_flow": np.minimum(demand, cap),
            "flow": np.gradient(np.asarray(r["research_stock"], dtype=float), t)}


def cap_diagnostics(series: dict, t_end_check: float | None = None) -> dict:
    """Where the cap binds, and a self-check that the integrated flow equals min(demand, cap).

    The self-check skips grid points next to a switch between binding and not binding,
    where the finite difference straddles the kink, and points after t_end_check (the
    upstream clamps research stock at a ceiling late in fast runs).
    """
    import numpy as np

    t, demand, cap = series["times"], series["demand"], series["cap"]
    binding = demand > cap * (1 + 1e-9)
    smooth = np.ones(t.size, dtype=bool)
    same = binding[1:] == binding[:-1]
    smooth[1:] &= same
    smooth[:-1] &= same
    smooth[[0, -1]] = False
    if t_end_check is not None:
        smooth &= t <= t_end_check
    exp = series["expected_flow"][smooth]
    rel = np.abs(series["flow"][smooth] - exp) / np.maximum(exp, 1e-300)
    return {
        "first_binding_year": float(t[np.argmax(binding)]) if binding.any() else None,
        "flow_self_check": {"points": int(rel.size),
                            "median_rel_err": float(np.median(rel)) if rel.size else None,
                            "p99_rel_err": float(np.quantile(rel, 0.99)) if rel.size else None,
                            "max_rel_err": float(np.max(rel)) if rel.size else None},
    }


def gap_after_ac(records, milestone: str):
    """Upstream definition of time from AC to a milestone (generate_conditional_timing.py).

    Over rollouts that achieved AC; a milestone reached at or before AC counts as 0; one
    never reached counts as not reached at any finite time (None here).
    Returns (n_with_ac, list of gaps with None for not reached).
    """
    gaps = []
    for r in records:
        ac = r["milestones"].get("AC")
        if ac is None:
            continue
        m = r["milestones"].get(milestone)
        gaps.append(None if m is None else max(0.0, m - ac))
    return len(gaps), gaps


def gap_stats(records, milestone: str, thresholds=()) -> dict:
    """p10/p50/p90 of the AC-relative gap (not reached placed at 1e6, as upstream) and P(gap <= x)."""
    import numpy as np

    n, gaps = gap_after_ac(records, milestone)
    if not n:
        return {"n_with_ac": 0}
    vals = np.array([1e6 if g is None else g for g in gaps], dtype=float)
    q = np.quantile(vals, (0.1, 0.5, 0.9))
    out = {"n_with_ac": n, "num_reached": int(sum(g is not None for g in gaps)),
           "p10": float(q[0]), "p50": float(q[1]), "p90": float(q[2]),
           "share_le": {str(x): float(np.mean(vals <= x)) for x in thresholds}}
    return out
