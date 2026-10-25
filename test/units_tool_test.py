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

    # issue #39: the unit is defined once, and stocks and flows stay apart
    def modes_copy(self):
        m = copy.deepcopy(MODES)
        pact = next(a for a in m['adapters'] if a['id'] == 'AD-PACT')
        return m, next(x for x in pact['quantities'] if x['name'] == 'AI capacity A')

    def defn(self, ident):
        return next(x for x in self.q['definitions'] if x['id'] == ident)

    def test_eiu_definition_is_a_stock_with_rejected_readings(self):
        d = self.defn('DEF-EIU')
        self.assertEqual(d['kind'], 'stock')
        self.assertEqual(d['output_rate']['conversion'], 'CV-CAPACITY-TO-OUTPUT')
        rejected = ' '.join(r['reading'] for r in d['rejects']).lower()
        for word in ('industry', 'primary energy', 'gdp'):
            self.assertIn(word, rejected)
        roles = {b['role'] for b in d['basis']}
        self.assertEqual(roles, {'stock', 'flow'})

    def test_unit_defined_twice(self):
        extra = copy.deepcopy(self.defn('DEF-EIU'))
        extra['id'] = 'DEF-EIU-ENERGY'
        self.q['definitions'].append(extra)
        self.rejects('already has a definition (DEF-EIU); a unit is defined once')

    def test_unit_without_definition(self):
        self.q['definitions'] = [x for x in self.q['definitions'] if x['id'] != 'DEF-LEC']
        self.rejects('normalized dimension le_capacity has no definition')

    def test_definition_needs_rejected_alternatives(self):
        self.defn('DEF-EIU')['rejects'] = []
        self.rejects('quantities_file')

    def test_definition_basis_equation_must_exist(self):
        self.defn('DEF-EIU')['basis'][0]['equation'] = 'PACT-NOWHERE'
        self.rejects('basis names unknown equation PACT-NOWHERE')

    def test_flow_unit_in_use_needs_output_rate(self):
        del self.defn('DEF-EIU')['output_rate']
        self.rejects('so the definition states its output rate')

    def test_output_rate_must_be_a_normalization_from_stock_to_flow(self):
        self.defn('DEF-EIU')['output_rate']['conversion'] = 'CV-EIU-TO-PRIMARY-POWER'
        self.rejects('must be a normalization with one value')

    def test_stock_booked_to_flow(self):
        self.qty('QTY-TOY-CAPITAL')['contract']['accounting'] = 'industrial_output'
        self.rejects('QTY-TOY-CAPITAL: a stock is booked to industrial_output, a flow')

    def test_flow_booked_to_stock(self):
        self.qty('QTY-INDUSTRIAL-OUTPUT')['contract']['accounting'] = 'industrial_capacity'
        self.rejects('QTY-INDUSTRIAL-OUTPUT: a flow is booked to industrial_capacity, a stock')

    def test_normalized_flow_needs_per_time(self):
        self.qty('QTY-TOY-DESIGN')['unit'] = 'EIU'
        self.c['conversions'] = [x for x in self.c['conversions'] if 'TOY-DESIGN' not in x['from'] + x['to']]
        self.e['equations'] = [x for x in self.e['equations'] if 'D' not in x['text'].split()]
        self.rejects('QTY-TOY-DESIGN: a flow in a normalized unit is per time')

    def test_normalized_stock_has_no_time(self):
        self.qty('QTY-PACT-A')['unit'] = 'EIU/yr'
        self.rejects('QTY-PACT-A: a stock in a normalized unit carries no time dimension')

    def test_contract_books_a_as_flow_again(self):
        modes, a = self.modes_copy()
        a['accounting'] = 'industrial_output'
        a['kind'] = 'flow'
        errors = tool.validate(self.q, self.c, self.e, modes, PARAMS)
        self.assertTrue(any("must declare kind stock (it declares flow)" in x for x in errors), errors)

    def test_contract_must_declare_kind(self):
        modes, a = self.modes_copy()
        del a['kind']
        errors = tool.validate(self.q, self.c, self.e, modes, PARAMS)
        self.assertTrue(any("must declare kind stock (it declares None)" in x for x in errors), errors)

    def test_unlinked_contract_quantity_must_declare_kind(self):
        # #61: also for contract quantities the dictionary does not link (GATE's digital workers)
        m = copy.deepcopy(MODES)
        gate = next(a for a in m['adapters'] if a['id'] == 'AD-GATE')
        del next(x for x in gate['quantities'] if x['name'] == 'digital workers N_i')['kind']
        errors = tool.validate(self.q, self.c, self.e, m, PARAMS)
        self.assertTrue(any("AD-GATE: contract quantity 'digital workers N_i' is booked to agent_workforce but declares no kind"
                            in x for x in errors), errors)

    def test_dictionary_cannot_resolve_an_ambiguity_to_another_kind(self):
        modes, a = self.modes_copy()
        a['kind'] = 'ambiguous'
        a['kind_ambiguity'] = {'candidates': ['flow', 'state'], 'locator': 'x', 'note': 'x'}
        del a['output_rate']
        errors = tool.validate(self.q, self.c, self.e, modes, PARAMS)
        self.assertTrue(any("is ambiguous between ['flow', 'state'], not stock" in x for x in errors), errors)

    def test_contract_output_rate_must_match_dictionary(self):
        modes, a = self.modes_copy()
        a['output_rate']['value'] = 0.3
        errors = tool.validate(self.q, self.c, self.e, modes, PARAMS)
        self.assertTrue(any('output rate 0.3 per year differs from CV-CAPACITY-TO-OUTPUT' in x for x in errors), errors)

    def test_output_rate_without_matching_conversion(self):
        self.c['conversions'] = [x for x in self.c['conversions'] if x['id'] != 'CV-CAPACITY-TO-OUTPUT']
        self.defn('DEF-EIU')['output_rate']['conversion'] = 'CV-RATE-TO-DOUBLING'
        self.rejects('but no normalization leads from QTY-PACT-A to a quantity booked there')

    def test_observed_primary_needs_a_primary_observation_record(self):
        self.cv('CV-GWP-TO-EIU-OUTPUT')['evidence']['ref'] = 'EV-GATE-PAPER-2025'
        self.rejects('CV-GWP-TO-EIU-OUTPUT: observed_primary needs an evidence record')

    def test_gwp_factor_is_reciprocal_of_reference_gwp(self):
        self.e['symbols']['Y_ref']['value'] = 2.0e14          # PPP instead of market exchange rates
        self.rejects('CV-GWP-TO-EIU-OUTPUT: derivation gives')

    def test_gwp_conversion_stays_uncoupled(self):
        self.assertFalse(self.cv('CV-GWP-TO-EIU-OUTPUT')['coupled'])

    def test_solver_flow_terms_need_the_output_rate(self):
        self.eq('PACT-AI-FLOW')['text'] = 'Y_AI = A + sigma * T_trade'
        self.rejects('equation PACT-AI-FLOW: adds earth_industry to earth_industry*time^-1')

    def test_schema_rejects_unknown_evidence_status(self):
        self.qty('QTY-CHI0')['evidence']['status'] = 'validated'
        self.rejects('quantities_file')


if __name__ == '__main__':
    unittest.main()
