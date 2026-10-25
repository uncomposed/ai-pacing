"""Independent implementation of GATE equations that can be checked against solver output.

[[ai gen]] Written from the paper (arXiv:2503.04941v2, TeX source) without access to
Epoch's source code. It is NOT a re-implementation of the GATE solver: it does not
solve the planner problem. It evaluates the paper's equations on the official solver's
reported states and decisions, so each equation is either confirmed (an identity that
holds to rounding), confirmed as an inequality, or reported with its residual.
Stdlib only, so it runs in `make check` without numpy.

Equation numbers (E1...) refer to EQUATIONS.md.
"""
import math

LOG10 = math.log10


# --- E9: automation function (paper eq. "automation function", Sec. 3.1) ---------------
def automation_fraction(log10_c, log10_t, delta_flop, f_init):
    """Fraction of tasks automatable with capability C_{T+iota} = 10**log10_c (eFLOP)."""
    lo = log10_t - delta_flop
    if log10_c <= lo:
        return f_init
    if log10_c > log10_t:
        return 1.0
    return f_init + (1 - f_init) * (log10_c - lo) / delta_flop


# --- E8: capability with the inference multiplier (eq. training_vs_inference_tradeoff) -----
def log10_capability(log10_train, iota_max_oom, m):
    """log10 C_{T+iota} = log10 C_T + log10(iota_max)/m."""
    return log10_train + iota_max_oom / m


# --- E11: runtime requirement per task (eq. "runtime compute req") ------------------------
def log10_runtime_requirement(i, log10_ct, log10_f_inv_i, m, gamma0, gamma1):
    return m * max(0.0, log10_f_inv_i - log10_ct) + gamma0 + gamma1 * i


# --- E14: Cobb-Douglas output (eq. final_goods_production_function, mu = 0) ---------------
def implied_tfp(gwp, capital, task_composite, alpha):
    return gwp / (capital ** alpha * task_composite ** (1 - alpha))


# --- E17: capital adjustment cost (eq. capital-adj-cost) inverted -------------------------
def effective_capital_investment(gross, capital, a_k):
    """Solve I_K = I_k + a_K I_k^2 / (2K) for I_k."""
    if a_k == 0:
        return gross
    return (math.sqrt(1 + 2 * a_k * gross / capital) - 1) * capital / a_k


def check_states(states, params, upto=None):
    """Evaluate the checkable equations on solver states. Returns a dict of residuals.

    `states` is a dict of lists keyed by variable (as in data/baseline_target.json
    `trajectory`), with `steps` the step indices. Exact identities are reported as max
    relative residuals; inequalities as counts of violations; approximate laws as
    residual series.
    """
    steps = states['steps']
    n = len(steps) if upto is None else sum(1 for t in steps if t <= upto)
    p = params
    L0, gL = p['main']['labor_force_init'], p['labor']['pop_growth']
    alpha = p['production']['alpha']
    out = {}

    def rel(a, b):
        return 0.0 if a == b else abs(a - b) / max(abs(a), abs(b))

    # E1 labor law of motion, perfect reallocation: L(t) = L0 exp(g_L t), reported at t+1.
    out['E1_labor'] = max(rel(states['labor'][i], L0 * math.exp(gL * (steps[i] + 1))) for i in range(n))
    # E2 output budget: consumption + four investment shares exhaust output.
    out['E2_output_shares_sum'] = max(abs(sum(states[k][i] for k in
                                      ('q_consumption', 'q_capital', 'q_compute', 'q_hardware_rnd', 'q_software_rnd')) - 1)
                                      for i in range(n))
    out['E2_consumption_eq_share_times_gwp'] = max(rel(states['consumption'][i], states['q_consumption'][i] * states['gwp'][i]) for i in range(n))
    out['E2_compute_investment_eq_share_times_gwp'] = max(rel(states['compute_investment'][i], states['q_compute'][i] * states['gwp'][i]) for i in range(n))
    # E3 compute budget: training and runtime shares exhaust the compute allocation, and
    # reported training and runtime compute are in the ratio of their shares.
    out['E3_compute_shares_sum'] = max(abs(states['q_training_compute'][i] + states['q_runtime_compute'][i] - 1) for i in range(n))
    out['E3_training_runtime_ratio'] = max(rel(states['training_compute'][i] / states['runtime_compute'][i],
                                               states['q_training_compute'][i] / states['q_runtime_compute'][i]) for i in range(n))
    # E14 capital share equals alpha (Cobb-Douglas, mu = 0).
    out['E14_capital_share_eq_alpha'] = max(rel(states['capital_share'][i], alpha) for i in range(n))
    # E14 implied TFP A = Y / (K^alpha T^(1-alpha)), with T read as cognitive_ces_term.
    out['E14_implied_tfp'] = [implied_tfp(states['gwp'][i], states['capital'][i], states['cognitive_ces_term'][i], alpha) for i in range(n)]
    # E5/E6 caps: H <= H_max, S <= S_max.
    out['E6_hardware_cap_violations'] = sum(states['hardware'][i] > p['rnd']['hardware_cap'] * (1 + 1e-12) for i in range(n))
    out['E6_software_cap_violations'] = sum(states['software'][i] > p['rnd']['software_cap'] * (1 + 1e-12) for i in range(n))
    # E7 largest training run is non-decreasing (dC_T/dt = D >= 0).
    out['E7_training_run_decreases'] = sum(states['best_training_run'][i + 1] < states['best_training_run'][i] for i in range(n - 1))
    return out


def check_automation(states, params, schedule_x, upto=None):
    """E8-E9: the deployed fraction never exceeds what the frontier can automate.

    The threshold T/10^Delta is taken from the solver's reported automation_schedule_x
    (its log10); the mapping from the playground's `flop_gap_frac` to Delta is not stated in
    the paper (see README, discrepancies). Returns violations and the slack series.
    """
    steps = states['steps']
    n = len(steps) if upto is None else sum(1 for t in steps if t <= upto)
    a, r = params['automation'], params['runtime']
    log10_t = a['train_reqs']
    delta = log10_t - schedule_x
    slack = []
    for i in range(n):
        cap = log10_capability(LOG10(states['best_training_run'][i]), r['tradeoff_range_oom_max'], r['inference_oom_per_training_oom'])
        feasible = automation_fraction(cap, log10_t, delta, a['initial_frac'])
        slack.append(feasible - states['frac_automated'][i])
    return {'delta_flop_implied': delta,
            'violations': sum(s < -1e-9 for s in slack),
            'slack': slack}


def _consecutive(steps):
    return [i for i in range(len(steps) - 1) if steps[i + 1] == steps[i] + 1]


def capital_law_residuals(states, params, scheme='exponential'):
    """E16-E17: one-year step of the paper's capital law dK/dt = I_k - delta_K K, with
    I_k from the adjustment-cost equation inverted at the start-of-step K and the gross
    investment q_capital*Y reported for the step being entered.

    scheme 'exponential': K' = K exp(-delta_K) + I_k   (matches the solver to rounding)
    scheme 'euler':       K' = K (1 - delta_K) + I_k   (the naive reading; kept to show
                                                         the discretisation matters)
    Returns relative residuals (predicted - reported) / reported per step.
    """
    steps = states['steps']
    dK, aK = params['capital']['depreciation'], params['capital']['adj_timescale_k']
    keep = math.exp(-dK) if scheme == 'exponential' else 1 - dK
    res = []
    for i in _consecutive(steps):
        K = states['capital'][i]
        gross = states['q_capital'][i + 1] * states['gwp'][i + 1]
        pred = K * keep + effective_capital_investment(gross, K, aK)
        res.append((pred - states['capital'][i + 1]) / states['capital'][i + 1])
    return res


def compute_stock_law_residuals(states, params):
    """E4: dQ/dt = I_q H - delta_Q Q, stepped as Q' = Q exp(-delta_Q) + I_q' H, where Q is
    the solver's `compute` (physical compute stock, FLOP/year), I_q' its
    `effective_compute_investment` for the step being entered and H the start-of-step
    hardware efficiency. Matches the solver to rounding. How `effective_compute_investment`
    follows from `compute_investment` through the adjustment cost (E5) is not reproduced."""
    steps = states['steps']
    dQ = params['compute']['depreciation']
    res = []
    for i in _consecutive(steps):
        Q = states['compute'][i]
        pred = Q * math.exp(-dQ) + states['effective_compute_investment'][i + 1] * states['hardware'][i]
        res.append((pred - states['compute'][i + 1]) / states['compute'][i + 1])
    return res
