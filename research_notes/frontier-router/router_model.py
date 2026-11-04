"""Frontier router: measurement cost, break-even throughput, and release-rule dynamics.

A router whose terms of service let it answer a sampled share of requests with a
second model too, return the better answer, and keep a blinded comparison. This
file computes three things from stated inputs:

1. Measurement cost. How many comparisons a per-domain frontier estimate needs at
   a given precision, what they cost, and how much routed spend the router's fee
   must carry for the measurement to pay for itself (section 2 of the README).
2. The leapfrog ratchet. Under a release rule "no more than epsilon above the best
   model anyone else has released", signatories can take turns raising the
   frontier by epsilon. Under a rule referenced to non-signatories only, they
   cannot (section 3).
3. Variant shopping. A lab that may submit m candidate variants and release any
   one that measures within epsilon gets an expected admitted excess above
   epsilon that grows with m and the measurement noise (section 4).

Every input in BASE, RATCHET and SHOPPING is an illustrative assumption, not an estimate. The
outputs are arithmetic on those inputs: numerically checked against closed forms
in test_router_model.py, not empirically validated.

    python3 research_notes/frontier-router/router_model.py           # print the tables
    python3 research_notes/frontier-router/router_model.py --write   # rewrite results/scenarios.json
    python3 research_notes/frontier-router/router_model.py --check   # compare with the committed results

Standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import sys
from statistics import NormalDist

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE / 'results' / 'scenarios.json'
N01 = NormalDist()

# --------------------------------------------------------------------------
# 1. Measurement cost and break-even
# --------------------------------------------------------------------------


def comparisons_per_cell(half_width: float, win_rate: float = 0.5, confidence: float = 0.95) -> int:
    """Blinded pairwise comparisons needed so a win-rate estimate has the given half-width.

    Normal approximation to the binomial, worst case at win_rate 0.5:
    n = z^2 p (1 - p) / h^2, rounded up.
    """
    if not 0 < half_width < 0.5:
        raise ValueError('half_width must be in (0, 0.5)')
    z = N01.inv_cdf(0.5 + confidence / 2)
    return math.ceil(z * z * win_rate * (1 - win_rate) / (half_width * half_width))


def elo_gap(win_rate: float) -> float:
    """Bradley-Terry rating gap, in Elo points, that implies the given head-to-head win rate."""
    return 400 * math.log10(win_rate / (1 - win_rate))


def margin_floor_elo(half_width: float) -> float:
    """Smallest release margin that is larger than the measurement's own half-width, in Elo.

    A margin below the half-width of the comparison against the frontier
    reference cannot be told apart from noise, so it is not enforceable. The
    floor is the rating gap of a 0.5 + h win rate.
    """
    return elo_gap(0.5 + half_width)


def cost_per_comparison(mix: list[dict]) -> float:
    """Mean cost of one comparison (second response plus judging) over a task mix."""
    share = sum(t['share'] for t in mix)
    if not math.isclose(share, 1.0, abs_tol=1e-9):
        raise ValueError(f'task mix shares sum to {share}, not 1')
    return sum(t['share'] * (t['second_response_usd'] + t['judge_usd']) for t in mix)


def measurement(params: dict) -> dict:
    """Comparisons and dollars per period for a per-domain, per-model frontier estimate."""
    n = comparisons_per_cell(params['half_width'], confidence=params['confidence'])
    cells = params['domains'] * params['models']
    comparisons = n * cells
    unit = cost_per_comparison(params['task_mix'])
    cost = comparisons * unit
    return {
        'comparisons_per_cell': n,
        'cells': cells,
        'comparisons_per_period': comparisons,
        'usd_per_comparison': unit,
        'measurement_usd_per_period': cost,
        'shadow_share_of_requests': comparisons / params['requests_per_period'],
        'margin_floor_elo': margin_floor_elo(params['half_width']),
    }


def break_even(params: dict) -> dict:
    """Routed spend at which fee and data revenue cover measurement cost.

    Net per period = (fee_rate + best_of_two_premium) * spend + data_revenue
                     - measurement cost.
    Ordinary routing costs are assumed already covered by the base fee in an
    existing router, so only the increment the measurement adds is counted.
    Measurement cost is fixed for a given precision: it does not grow with
    traffic, so the share of spend it takes falls as spend rises.
    """
    m = measurement(params)
    take = params['fee_rate'] + params['best_of_two_premium']
    need = m['measurement_usd_per_period'] - params['data_revenue_usd_per_period']
    spend_star = max(need, 0.0) / take
    spend = params['routed_spend_usd_per_period']
    return {
        **m,
        'break_even_spend_usd_per_period': spend_star,
        'net_usd_per_period_at_spend': take * spend + params['data_revenue_usd_per_period'] - m['measurement_usd_per_period'],
        'measurement_share_of_spend': m['measurement_usd_per_period'] / spend,
    }


# --------------------------------------------------------------------------
# 2. Release-rule dynamics: the leapfrog ratchet
# --------------------------------------------------------------------------


def simulate_frontier(rule: str, signatories: int, epsilon: float, interval: float,
                      nonsignatory_speed: float, internal_speed: float, horizon: float,
                      start: float = 0.0) -> dict:
    """Deterministic release dynamics for signatories that release on a staggered cycle.

    Capability is in rating units. The best non-signatory release is
    start + nonsignatory_speed * t. Each signatory i releases at times
    (i / signatories + j) * interval and always wants to release as much as it
    is allowed and has: internal capability is start + internal_speed * t
    (the leader's internal stock, which the rule does not touch).

    rule 'all_others': a signatory may release up to epsilon above the best model
        any other lab, signatory or not, has released (the rule as first stated).
    rule 'non_signatories': a signatory may release up to epsilon above the best
        non-signatory release. Signatory releases do not move the reference;
        in the full proposal the shared ceiling moves only through adversarial
        review (K4), which this function does not model.
    """
    if rule not in ('all_others', 'non_signatories'):
        raise ValueError(rule)
    released = [start] * signatories
    events = []
    j = 0
    while True:
        batch = [((i / signatories + j) * interval, i) for i in range(signatories)]
        batch = [(t, i) for t, i in batch if t <= horizon + 1e-12]
        if not batch:
            break
        for t, i in batch:
            nonsig = start + nonsignatory_speed * t
            if rule == 'all_others':
                reference = max([nonsig] + [released[k] for k in range(signatories) if k != i])
            else:
                reference = nonsig
            internal = start + internal_speed * t
            released[i] = max(released[i], min(internal, reference + epsilon))
            events.append({'t': t, 'lab': i, 'released': released[i],
                           'frontier': max(max(released), nonsig)})
        j += 1
    # Long-run speed: slope of the frontier over the second half of the run, so
    # the start-up transient (internal capability still catching up) is excluded.
    last = events[-1]
    mid = min(events, key=lambda e: abs(e['t'] - last['t'] / 2))
    span = last['t'] - mid['t']
    return {'events': events, 'final_frontier': last['frontier'], 't_end': last['t'],
            'long_run_speed': (last['frontier'] - mid['frontier']) / span if span > 0 else 0.0}


def ratchet_speed_closed_form(rule: str, signatories: int, epsilon: float, interval: float,
                              nonsignatory_speed: float, internal_speed: float) -> float:
    """Long-run frontier speed implied by the two rules.

    all_others, two or more signatories: each release event adds epsilon on top
        of the previous one, and there are signatories / interval events per
        unit time, so the frontier moves at signatories * epsilon / interval
        (never slower than the non-signatories, never faster than internal
        capability).
    otherwise: the frontier tracks the non-signatories, epsilon above them.
    """
    if rule == 'all_others' and signatories >= 2:
        return min(internal_speed, max(nonsignatory_speed, signatories * epsilon / interval))
    return min(internal_speed, nonsignatory_speed)


# --------------------------------------------------------------------------
# 3. Variant shopping under a noisy measurement
# --------------------------------------------------------------------------


def pass_probability(excess: float, epsilon: float, noise_sd: float, variants: int) -> float:
    """Chance at least one of `variants` independent measurements of a model `excess` above
    the frontier comes in at or below epsilon."""
    one = N01.cdf((epsilon - excess) / noise_sd)
    return 1 - (1 - one) ** variants


def admitted_excess_closed_form(epsilon: float, noise_sd: float, variants: int, pass_target: float = 0.5) -> float:
    """True excess above the frontier at which a lab passes with probability pass_target.

    Solves 1 - (1 - Phi((eps - x) / sd))^m = q for x:
    x = eps - sd * Phi^-1(1 - (1 - q)^(1/m)).
    With one variant and q = 0.5 this is epsilon. It rises with m: the rule
    admits models further above the frontier the more tries a lab gets.
    """
    single = 1 - (1 - pass_target) ** (1 / variants)
    return epsilon - noise_sd * N01.inv_cdf(single)


def admitted_excess_monte_carlo(epsilon: float, noise_sd: float, variants: int, trials: int,
                                seed: int, pass_target: float = 0.5) -> float:
    """Bisection on simulated pass rates, as an independent check on the closed form."""
    rng = random.Random(seed)
    draws = [[rng.gauss(0.0, noise_sd) for _ in range(variants)] for _ in range(trials)]
    # Passing needs excess + noise <= epsilon for at least one variant, so a
    # trial passes exactly when excess <= epsilon - min(noise). The pass rate at
    # excess x is the share of trials with epsilon - min(noise) >= x, so the
    # target quantile of epsilon - min(noise) is the answer.
    thresholds = sorted(epsilon - min(row) for row in draws)
    k = int(math.floor((1 - pass_target) * trials))
    return thresholds[k]


# --------------------------------------------------------------------------
# Scenarios
# --------------------------------------------------------------------------

# Illustrative assumptions. Change them freely; nothing here is calibrated.
TASK_MIX = [
    {'name': 'chat and short tasks', 'share': 0.8, 'second_response_usd': 0.01, 'judge_usd': 0.005},
    {'name': 'long agentic or coding tasks', 'share': 0.2, 'second_response_usd': 0.50, 'judge_usd': 0.10},
]
BASE = {
    'domains': 200,              # long-tail domain cells the estimate is broken into
    'models': 12,                # models tracked against the frontier reference in each domain
    'half_width': 0.03,          # 95% half-width on each head-to-head win rate
    'confidence': 0.95,
    'task_mix': TASK_MIX,
    'requests_per_period': 1.0e9,     # requests a large router handles per month (assumed)
    'fee_rate': 0.055,               # platform fee on routed spend (OpenRouter's reported standard rate)
    'best_of_two_premium': 0.0,      # extra fee for the best-of-two feature; 0 = none
    'data_revenue_usd_per_period': 0.0,  # sale of aggregate frontier reports; 0 = none
    'routed_spend_usd_per_period': 1.0e7,  # monthly routed spend at which net is reported (assumed)
}
HALF_WIDTHS = [0.05, 0.03, 0.02, 0.01]
RATCHET = {'epsilon': 10.0, 'interval': 6.0, 'nonsignatory_speed': 1.0, 'internal_speed': 30.0, 'horizon': 36.0}
SHOPPING = {'epsilon': 10.0, 'noise_sd': 10.0, 'variants': [1, 3, 10, 27]}


def build() -> dict:
    precision = []
    for h in HALF_WIDTHS:
        r = break_even({**BASE, 'half_width': h})
        precision.append({'half_width': h, **{k: r[k] for k in (
            'margin_floor_elo', 'comparisons_per_cell', 'comparisons_per_period',
            'measurement_usd_per_period', 'shadow_share_of_requests',
            'break_even_spend_usd_per_period', 'net_usd_per_period_at_spend',
            'measurement_share_of_spend')}})
    revenue_cases = []
    for label, extra in [('fee only', {}),
                         ('fee + 0.5 pt best-of-two premium', {'best_of_two_premium': 0.005}),
                         ('fee + $100k/month frontier-report revenue', {'data_revenue_usd_per_period': 1.0e5})]:
        r = break_even({**BASE, **extra})
        revenue_cases.append({'case': label, 'break_even_spend_usd_per_period': r['break_even_spend_usd_per_period'],
                              'net_usd_per_period_at_spend': r['net_usd_per_period_at_spend']})
    ratchet = []
    for rule in ('all_others', 'non_signatories'):
        for k in (1, 2, 3, 5):
            sim = simulate_frontier(rule, k, **RATCHET)
            ratchet.append({'rule': rule, 'signatories': k,
                            'simulated_speed': sim['long_run_speed'],
                            'closed_form_speed': ratchet_speed_closed_form(
                                rule, k, RATCHET['epsilon'], RATCHET['interval'],
                                RATCHET['nonsignatory_speed'], RATCHET['internal_speed'])})
    shopping = []
    for m in SHOPPING['variants']:
        shopping.append({'variants': m,
                         'admitted_excess_closed_form': admitted_excess_closed_form(SHOPPING['epsilon'], SHOPPING['noise_sd'], m),
                         'admitted_excess_monte_carlo': admitted_excess_monte_carlo(SHOPPING['epsilon'], SHOPPING['noise_sd'], m, 20000, 7)})
    return {
        'status': 'illustrative arithmetic on assumed inputs; numerically checked, not empirically validated',
        'inputs': {'base': BASE, 'half_widths': HALF_WIDTHS, 'ratchet': RATCHET, 'shopping': SHOPPING},
        'precision_vs_cost': precision,
        'revenue_cases': revenue_cases,
        'ratchet': ratchet,
        'variant_shopping': shopping,
    }


def _round(x):
    if isinstance(x, float):
        return float(f'{x:.6g}')
    if isinstance(x, dict):
        return {k: _round(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_round(v) for v in x]
    return x


def compare(fresh: dict, committed: dict) -> None:
    if _round(fresh) != _round(committed):
        raise SystemExit('results/scenarios.json differs from a fresh build; find the cause before rewriting it')


def report(res: dict) -> str:
    out = ['Precision vs cost (fee only, assumed inputs)',
           f"{'half-width':>10} {'floor Elo':>9} {'comparisons/mo':>15} {'cost $/mo':>12} {'shadow share':>12} {'break-even spend $/mo':>22}"]
    for r in res['precision_vs_cost']:
        out.append(f"{r['half_width']:>10} {r['margin_floor_elo']:>9.1f} {r['comparisons_per_period']:>15,} "
                   f"{r['measurement_usd_per_period']:>12,.0f} {r['shadow_share_of_requests']:>12.2%} {r['break_even_spend_usd_per_period']:>22,.0f}")
    out += ['', 'Revenue cases at the base precision']
    for r in res['revenue_cases']:
        out.append(f"  {r['case']:<45} break-even ${r['break_even_spend_usd_per_period']:,.0f}/mo; net at $10M/mo routed: ${r['net_usd_per_period_at_spend']:,.0f}")
    out += ['', 'Frontier speed (rating units per month)']
    for r in res['ratchet']:
        out.append(f"  {r['rule']:<16} signatories={r['signatories']}: simulated {r['simulated_speed']:.2f}, closed form {r['closed_form_speed']:.2f}")
    out += ['', 'Variant shopping: true excess admitted at a 50% pass rate (epsilon 10, noise sd 10)']
    for r in res['variant_shopping']:
        out.append(f"  m={r['variants']:>2}: closed form {r['admitted_excess_closed_form']:.2f}, Monte Carlo {r['admitted_excess_monte_carlo']:.2f}")
    return '\n'.join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--write', action='store_true', help='rewrite results/scenarios.json')
    ap.add_argument('--check', action='store_true', help='compare a fresh build with results/scenarios.json')
    args = ap.parse_args(argv)
    res = build()
    if args.write:
        RESULTS.parent.mkdir(exist_ok=True)
        RESULTS.write_text(json.dumps(_round(res), indent=2) + '\n', encoding='utf-8')
    if args.check:
        compare(res, json.loads(RESULTS.read_text(encoding='utf-8')))
        print('results/scenarios.json matches a fresh build')
    print(report(res))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
