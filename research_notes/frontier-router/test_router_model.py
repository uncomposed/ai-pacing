"""Fast checks for the frontier-router model. No network; standard library only.

    python3 research_notes/frontier-router/test_router_model.py      (run by make check)

These check numerical correctness (closed forms, identities, a seeded Monte
Carlo) and that the committed results match a fresh build. They say nothing
about whether the assumed inputs are realistic.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import router_model as M  # noqa: E402


class Measurement(unittest.TestCase):
    def test_comparisons_per_cell_matches_the_binomial_formula(self):
        # z = 1.96, p = 0.5, h = 0.03 -> 1.96^2 * 0.25 / 0.0009 = 1067.1 -> 1068
        self.assertEqual(M.comparisons_per_cell(0.03), 1068)
        self.assertEqual(M.comparisons_per_cell(0.01), math.ceil(M.N01.inv_cdf(0.975) ** 2 * 0.25 / 1e-4))

    def test_cost_scales_with_inverse_square_of_precision(self):
        a = M.measurement({**M.BASE, 'half_width': 0.02})['measurement_usd_per_period']
        b = M.measurement({**M.BASE, 'half_width': 0.01})['measurement_usd_per_period']
        self.assertAlmostEqual(b / a, 4.0, delta=0.01)

    def test_elo_gap_is_antisymmetric_and_zero_at_even(self):
        self.assertEqual(M.elo_gap(0.5), 0.0)
        self.assertAlmostEqual(M.elo_gap(0.6), -M.elo_gap(0.4))
        self.assertAlmostEqual(M.elo_gap(10 / 11), 400.0)

    def test_task_mix_must_sum_to_one(self):
        with self.assertRaises(ValueError):
            M.cost_per_comparison([{'share': 0.5, 'second_response_usd': 1, 'judge_usd': 0}])

    def test_break_even_net_is_zero_at_break_even_spend(self):
        r = M.break_even(M.BASE)
        at = M.break_even({**M.BASE, 'routed_spend_usd_per_period': r['break_even_spend_usd_per_period']})
        self.assertAlmostEqual(at['net_usd_per_period_at_spend'], 0.0, delta=1e-6)

    def test_measurement_cost_does_not_grow_with_traffic(self):
        small = M.break_even({**M.BASE, 'requests_per_period': 1e8, 'routed_spend_usd_per_period': 1e6})
        large = M.break_even({**M.BASE, 'requests_per_period': 1e10, 'routed_spend_usd_per_period': 1e8})
        self.assertEqual(small['measurement_usd_per_period'], large['measurement_usd_per_period'])
        self.assertAlmostEqual(small['shadow_share_of_requests'] / large['shadow_share_of_requests'], 100.0)


class Ratchet(unittest.TestCase):
    def test_simulation_matches_closed_form(self):
        for rule in ('all_others', 'non_signatories'):
            for k in (1, 2, 3, 4, 5):
                sim = M.simulate_frontier(rule, k, **M.RATCHET)['long_run_speed']
                cf = M.ratchet_speed_closed_form(rule, k, M.RATCHET['epsilon'], M.RATCHET['interval'],
                                                 M.RATCHET['nonsignatory_speed'], M.RATCHET['internal_speed'])
                self.assertAlmostEqual(sim, cf, places=9, msg=f'{rule} k={k}')

    def test_one_signatory_cannot_ratchet(self):
        self.assertEqual(M.ratchet_speed_closed_form('all_others', 1, 10, 6, 1, 30), 1)

    def test_more_signatories_speed_up_the_all_others_rule(self):
        speeds = [M.ratchet_speed_closed_form('all_others', k, 10, 6, 1, 30) for k in (2, 3, 5)]
        self.assertEqual(speeds, sorted(speeds))
        self.assertGreater(speeds[0], 1)

    def test_internal_capability_caps_the_ratchet(self):
        sim = M.simulate_frontier('all_others', 5, epsilon=10, interval=1, nonsignatory_speed=1,
                                  internal_speed=4, horizon=40)
        self.assertAlmostEqual(sim['long_run_speed'], 4.0, places=9)

    def test_non_signatory_rule_never_exceeds_reference_plus_epsilon(self):
        sim = M.simulate_frontier('non_signatories', 4, **M.RATCHET)
        for e in sim['events']:
            self.assertLessEqual(e['released'], M.RATCHET['nonsignatory_speed'] * e['t'] + M.RATCHET['epsilon'] + 1e-9)


class VariantShopping(unittest.TestCase):
    def test_one_variant_admits_exactly_epsilon(self):
        self.assertAlmostEqual(M.admitted_excess_closed_form(10, 10, 1), 10.0)

    def test_closed_form_solves_the_pass_probability(self):
        for m in (1, 3, 10, 27):
            x = M.admitted_excess_closed_form(10, 10, m)
            self.assertAlmostEqual(M.pass_probability(x, 10, 10, m), 0.5, places=9)

    def test_monte_carlo_agrees_with_closed_form(self):
        for m in (1, 3, 10, 27):
            cf = M.admitted_excess_closed_form(10, 10, m)
            mc = M.admitted_excess_monte_carlo(10, 10, m, 20000, 7)
            self.assertAlmostEqual(cf, mc, delta=0.25, msg=f'm={m}')

    def test_admitted_excess_rises_with_variants(self):
        xs = [M.admitted_excess_closed_form(10, 10, m) for m in (1, 2, 5, 20)]
        self.assertEqual(xs, sorted(xs))


class CommittedResults(unittest.TestCase):
    def test_committed_results_match_a_fresh_build(self):
        committed = json.loads((HERE / 'results' / 'scenarios.json').read_text(encoding='utf-8'))
        M.compare(M.build(), committed)


if __name__ == '__main__':
    unittest.main(verbosity=1)
