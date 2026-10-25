"""Mutation tests for tools/units_tool.py: each test breaks one rule and expects the checker to say so."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('units_tool', ROOT / 'tools/units_tool.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

FILES, MODES, PARAMS = tool.load_all()


class UnitsBridgeTest(unittest.TestCase):
    def setUp(self):
        self.q = copy.deepcopy(FILES['quantities'])
        self.c = copy.deepcopy(FILES['conversions'])
        self.e = copy.deepcopy(FILES['equations'])

    def errors(self):
        return tool.validate(self.q, self.c, self.e, MODES, PARAMS)

    def rejects(self, message):
        errors = self.errors()
        self.assertTrue(any(message in e for e in errors), errors)

    def qty(self, ident):
        return next(x for x in self.q['quantities'] if x['id'] == ident)

    def cv(self, ident):
        return next(x for x in self.c['conversions'] if x['id'] == ident)

    def eq(self, ident):
        return next(x for x in self.e['equations'] if x['id'] == ident)

    def test_committed_files_pass(self):
        self.assertEqual(self.errors(), [])

    # units and dimensions
    def test_unit_algebra(self):
        units = self.q['units']
        self.assertEqual(tool.parse_unit('person*h/yr', units)[1], {'person': 1})
        scale, dims = tool.parse_unit('J/yr', units)
        self.assertAlmostEqual(scale, 1 / 31557600)
        self.assertEqual(dims, {'energy': 1, 'time': -1})
        self.assertEqual(tool.parse_unit('1/yr', units)[1], {'time': -1})
        with self.assertRaises(tool.UnitError):
            tool.parse_unit('furlong', units)

    def test_unknown_unit_in_quantity(self):
        self.qty('QTY-PACT-A')['unit'] = 'EIUs'
        self.rejects("unknown unit 'EIUs'")

    def test_inconsistent_equation(self):
        self.eq('TOY-DESIGN')['text'] = 'D = D_h + lam'
        self.rejects('equation TOY-DESIGN: adds')

    def test_exp_of_dimensional_argument(self):
        self.eq('PACT-GROWTH')['text'] = 'A_next = A * exp(g * chi * (1 - A / Kmax))'
        self.rejects('exp of a dimensional argument')

    def test_min_over_mixed_dimensions(self):
        self.eq('TOY-OUTPUT')['text'] = 'Y = nu * min(K, E, D)'
        self.rejects('min over different dimensions')

    def test_check_value_mismatch(self):
        self.e['symbols']['u_t']['value'] = 2.4e-9
        self.rejects('equation METZGER-BRIDGE: u_t is declared')

    def test_symbol_unit_must_match_its_quantity(self):
        self.e['symbols']['g']['unit'] = 'yr'
        self.rejects('symbol g: unit yr does not match QTY-GROWTH-RATE-G')

    # conversions
    def test_conversion_dimensions(self):
        self.cv('CV-CAPACITY-TO-OUTPUT')['factor']['unit'] = '1'
        self.rejects('conversion CV-CAPACITY-TO-OUTPUT: earth_industry via factor 1 gives earth_industry')

    def test_bridging_factor_is_not_a_normalization(self):
        x = self.cv('CV-EIU-TO-PRIMARY-POWER')
        x['class'] = 'normalization'
        x['factor'].pop('bounds')
        x['evidence']['status'] = 'normalization'
        self.rejects('bridges different dimensions, so it is an empirical scale estimate or a scenario')

    def test_derivation_must_reproduce_factor(self):
        self.cv('CV-METZGER-T-TO-EIU')['factor']['value'] = 2.4e-10
        self.c['conversions'][[x['id'] for x in self.c['conversions']].index('CV-METZGER-T-TO-EIU')]['factor']['bounds'] = [1e-11, 1e-8]
        self.rejects('conversion CV-METZGER-T-TO-EIU: derivation gives')

    def test_scenario_needs_bounds(self):
        self.cv('CV-TOY-COMPUTE-TO-DESIGN')['factor'].pop('bounds')
        self.rejects('a bounded scenario needs bounds')

    def test_unidentified_must_stay_uncoupled(self):
        self.cv('CV-HORIZON-TO-DEV-TIME')['coupled'] = True
        self.rejects('an unidentified conversion must stay uncoupled')

    def test_unidentified_carries_no_value(self):
        self.cv('CV-METZGER-RATE-TO-G')['factor']['value'] = 1.0
        self.rejects('an unidentified conversion carries no value or bounds')

    def test_conversion_needs_mechanism_and_delay(self):
        del self.cv('CV-RATE-TO-DOUBLING')['mechanism']
        self.rejects('conversion CV-RATE-TO-DOUBLING: needs mechanism')

    def test_forbidden_needs_reason_and_no_coupling(self):
        x = self.cv('CV-NO-HORIZON-TO-STRIKE-ODDS')
        x['coupled'] = True
        self.rejects('a forbidden conversion has no factor and is never coupled')

    def test_forbidden_pair_cannot_also_be_declared(self):
        self.c['conversions'].append({'id': 'CV-SNEAK', 'from': 'QTY-METZGER-GEN-SPACING', 'to': 'QTY-DOUBLING-TIME',
                                      'class': 'identity', 'form': 'linear', 'factor': {'value': 1.0, 'unit': '1'},
                                      'mechanism': 'x', 'delay': {'kind': 'none', 'note': 'x'}, 'constraints': 'x',
                                      'evidence': {'status': 'normalization', 'ref': 'x'}, 'coupled': True})
        self.rejects('is forbidden and also declared as CV-SNEAK')

    def test_stopping_rule_blocks_capability_to_strike_odds(self):
        """A coupled chain METR horizon -> developer time -> strike odds is refused, even if each link looks fine."""
        self.cv('CV-HORIZON-TO-DEV-TIME').update({'class': 'bounded_scenario', 'coupled': True,
                                                  'factor': {'value': 0.1, 'bounds': [0.01, 1.0], 'unit': '1/h'},
                                                  'evidence': {'status': 'scenario', 'ref': 'x'}})
        self.c['conversions'].append({'id': 'CV-BAD', 'from': 'QTY-DEV-TIME-RATIO', 'to': 'QTY-STRIKE-ODDS',
                                      'class': 'bounded_scenario', 'form': 'linear',
                                      'factor': {'value': 0.5, 'bounds': [0.1, 0.9], 'unit': '1'},
                                      'mechanism': 'x', 'delay': {'kind': 'none', 'note': 'x'}, 'constraints': 'x',
                                      'evidence': {'status': 'scenario', 'ref': 'x'}, 'coupled': True})
        self.rejects('stopping rule: capability metric QTY-METR-HORIZON reaches QTY-STRIKE-ODDS')

    def test_closure_concepts_stay_distinct(self):
        x = self.cv('CV-LOCAL-CHIPS-TO-CHI0')
        x['to'] = 'QTY-LE-CLOSURE-THRESHOLD'
        self.rejects('links CL-BASIC-CHIPS to CL-LEADING-EDGE-FAB')

    def test_sovereignty_is_a_view_not_a_quantity(self):
        cl = next(x for x in self.q['closure_and_sovereignty'] if x['id'] == 'CL-EFFECTIVE-SOVEREIGNTY')
        cl['quantities'] = ['QTY-INTERVENTION-LATENCY']
        self.rejects('a mode is a derived view, not a quantity')

    def test_concepts_map_to_different_contract_elements(self):
        a = next(x for x in self.q['closure_and_sovereignty'] if x['id'] == 'CL-BASIC-CHIPS')
        b = next(x for x in self.q['closure_and_sovereignty'] if x['id'] == 'CL-LEADING-EDGE-FAB')
        a['contract'] = dict(b['contract'])
        self.rejects('maps to the same contract element as another concept')

    # links to the mode contract and the solver
    def test_unknown_accounting_id(self):
        self.qty('QTY-AGENT-LABOR')['contract']['accounting'] = 'agent_time'
        self.rejects('unknown accounting quantity agent_time')

    def test_adapter_quantity_unit_must_agree(self):
        self.qty('QTY-METR-HORIZON')['unit'] = 'yr*task'
        self.rejects('differs from the contract unit')

    def test_unknown_adapter_quantity(self):
        self.qty('QTY-PACT-A')['contract']['adapter_quantity']['name'] = 'AI capability'
        self.rejects("adapter AD-PACT has no quantity 'AI capability'")

    def test_pact_param_must_exist(self):
        self.qty('QTY-GROWTH-RATE-G')['pact_params'] = ['g_off']
        self.rejects('pact parameter g_off is not in PARAMS')

    def test_every_category_needs_a_quantity(self):
        self.q['quantities'] = [x for x in self.q['quantities'] if x['category'] != 'software_efficiency']
        self.c['conversions'] = [x for x in self.c['conversions'] if 'ECI' not in x['from'] and 'EFFICIENCY' not in x['from']]
        self.rejects('category software_efficiency has no quantity')

    def test_schema_rejects_unknown_evidence_status(self):
        self.qty('QTY-CHI0')['evidence']['status'] = 'validated'
        self.rejects('quantities_file')


if __name__ == '__main__':
    unittest.main()
