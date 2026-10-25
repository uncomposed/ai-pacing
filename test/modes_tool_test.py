import copy
import importlib.util
import json
from pathlib import Path
import shutil
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('modes_tool', ROOT / 'tools/modes_tool.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

CONTRACT = tool.load_yaml(tool.CONTRACT)
REGISTER = tool.load_yaml(ROOT / CONTRACT['solver_mapping']['register'])
PARAMS = tool.assumptions_tool.load_params()


class ModeContractTest(unittest.TestCase):
    def setUp(self):
        self.c = copy.deepcopy(CONTRACT)

    def errors(self, register=None, params=None):
        return tool.validate(self.c, register or REGISTER, params or PARAMS)

    def rejects(self, message, **kw):
        errors = self.errors(**kw)
        self.assertTrue(any(message in e for e in errors), errors)

    def mode(self, ident):
        return next(m for m in self.c['modes'] if m['id'] == ident)

    def transition(self, ident):
        return next(t for t in self.c['transitions'] if t['id'] == ident)

    def trace(self, ident):
        return next(t for t in self.c['traces'] if t['id'] == ident)

    def adapter(self, ident):
        return next(a for a in self.c['adapters'] if a['id'] == ident)

    # --- the committed contract
    def test_contract_is_consistent_and_only_proposed(self):
        self.assertEqual([], self.errors())
        self.assertEqual('proposed', self.c['status'])
        self.assertTrue(all(m['status'] == 'proposed' for m in self.c['modes']))

    def test_required_example_traces_exist(self):
        ids = {t['id'] for t in self.c['traces']}
        self.assertLessEqual({'TR-CONTROLLED-CAPABLE', 'TR-NOMINAL-CONTROL', 'TR-SOVEREIGN-COOPERATIVE',
                              'TR-RESTRICTED-REGAINS', 'TR-MIXED-POPULATION'}, ids)

    def test_actors_coexist_in_different_modes(self):
        tr = self.trace('TR-MIXED-POPULATION')
        views = tool.classify(self.c, tr, tr['steps'][0])
        held = {eid: {m for m, v in r.items() if v} for eid, r in views.items()}
        self.assertEqual({'MODE-HUMAN-LAB'}, held['SYS-D'])
        self.assertEqual({'MODE-SOVEREIGN-CAPABLE'}, held['SYS-E'])
        self.assertEqual({'MODE-SOVEREIGN'}, held['COLL-F'])

    def test_capability_alone_does_not_leave_human_lab_mode(self):
        tr = self.trace('TR-CONTROLLED-CAPABLE')
        views = tool.classify(self.c, tr, tr['steps'][0])['SYS-A']
        self.assertTrue(views['MODE-HUMAN-LAB'] and views['MODE-SOVEREIGN-CAPABLE'])

    def test_three_labels_erase_failed_intervention(self):
        collisions = tool.label_collisions(self.c)
        self.assertTrue(collisions)
        self.assertTrue(any(a == 'TR-NOMINAL-CONTROL#1:SYS-B' and 'effective_control' in diff
                            for _, a, _, diff in collisions))

    def test_unknown_dimension_gives_undetermined_view(self):
        tr = self.trace('TR-CONTROLLED-CAPABLE')
        step = tr['steps'][0]
        step['entities']['SYS-A']['state']['effective_control'] = 'unknown'
        self.assertIsNone(tool.classify(self.c, tr, step)['SYS-A']['MODE-HUMAN-LAB'])
        self.rejects('has undetermined views')
        step['undetermined_views'] = {'SYS-A': ['MODE-HUMAN-LAB']}
        step['expected_views']['SYS-A'] = ['MODE-SOVEREIGN-CAPABLE']
        self.assertFalse([e for e in self.errors() if 'step 1' in e and 'TR-CONTROLLED' in e and 'view' in e])

    # --- modes
    def test_numeric_threshold_in_mode_is_rejected(self):
        self.mode('MODE-SOVEREIGN')['criteria']['external_resources'] = ['0.1']
        self.rejects('no numeric thresholds')

    def test_mode_claimed_as_empirical_is_rejected(self):
        self.mode('MODE-SOVEREIGN')['status'] = 'validated'
        self.rejects('schema: modes/2/status')

    def test_mode_without_falsifier_is_rejected(self):
        self.c['falsifiers'] = [f for f in self.c['falsifiers'] if 'MODE-SOVEREIGN' not in f['targets']]
        self.rejects('MODE-SOVEREIGN: no falsifier targets this mode')

    # --- transitions
    def test_transition_without_reverse_is_rejected(self):
        self.transition('T-RECOVERY')['reversible_by'] = []
        self.rejects('T-RECOVERY: names no reverse transition and gives no irreversible_reason')

    def test_declared_irreversible_transition_is_allowed(self):
        t = self.transition('T-RECOVERY')
        t['reversible_by'] = []
        t['irreversible_reason'] = 'test'
        self.assertFalse([e for e in self.errors() if e.startswith('T-RECOVERY')])

    def test_reverse_in_same_direction_is_rejected(self):
        self.transition('T-DELEGATE')['reversible_by'] = ['T-LOSS-OF-CONTROL']
        self.rejects('reverse T-LOSS-OF-CONTROL points the same way')

    def test_identified_needs_observed_instances(self):
        self.transition('T-AUTHORIZED-AUTONOMY')['identified'] = True
        self.rejects('identified is true but feasibility is unidentified')

    # --- traces
    def test_relabelling_without_transition_is_rejected(self):
        step = self.trace('TR-NOMINAL-CONTROL')['steps'][2]
        del step['transitions']
        self.rejects('without a transition that declares it')
        self.rejects('changes mode view with no transition (relabelling)')

    def test_transition_that_changes_nothing_is_rejected(self):
        step = self.trace('TR-CONTROLLED-CAPABLE')['steps'][1]
        step['transitions'].append({'entity': 'LAB-A', 'type': 'T-DELEGATE'})
        self.rejects('LAB-A applies T-DELEGATE but none of its dimensions changed (relabelling)')

    def test_transition_precondition_is_checked(self):
        step = self.trace('TR-NOMINAL-CONTROL')['steps'][2]
        self.trace('TR-NOMINAL-CONTROL')['steps'][1]['entities']['SYS-B']['state']['dependencies'] = 'none_within_horizon'
        step['entities']['SYS-B']['state']['dependencies'] = 'none_within_horizon'
        self.rejects('applies T-RECONTAIN but dependencies was none_within_horizon')

    # --- #32: gaps found by the Hugging Face trace
    def test_loss_of_control_may_acquire_external_resources(self):
        tr = self.trace('TR-NOMINAL-CONTROL')
        tr['steps'][1]['entities']['SYS-B']['state']['external_resources'] = 'minor'
        self.assertFalse([e for e in self.errors() if 'step 2' in e and 'external_resources' in e])
        tr['steps'][1]['transitions'] = []
        self.rejects('SYS-B external_resources changed from none to minor without a transition that declares it')

    def _restrict_from(self, control):
        tr = self.trace('TR-RESTRICTED-REGAINS')
        for step in tr['steps'][:2]:
            step['entities']['SYS-C']['state']['effective_control'] = control
        return [e for e in self.errors() if 'applies T-RESTRICT' in e]

    def test_restriction_allowed_when_control_unknown(self):
        self.assertEqual([], self._restrict_from('unknown'))

    def test_restriction_still_needs_control_not_known_lost(self):
        self.assertEqual(["TR-RESTRICTED-REGAINS step 2: SYS-C applies T-RESTRICT but effective_control was none, "
                          "not in ['human_effective', 'human_contested', 'unknown']"], self._restrict_from('none'))

    def test_precondition_with_undeclared_level_is_rejected(self):
        self.transition('T-RESTRICT')['preconditions']['effective_control'].append('mostly')
        self.rejects('T-RESTRICT: precondition effective_control uses undeclared level mostly')

    def _split(self, host_value, other_value='none', trace='TR-CONTROLLED-CAPABLE', eid='SYS-A', host='LAB-A'):
        tr = self.trace(trace)
        for step in tr['steps']:
            ents = step['entities']
            ents['ORG-X'] = {'kind': 'other_org', 'host': None, 'state': dict(ents[host]['state'])}
            ents[eid]['state']['effective_control'] = [
                {'principal': host, 'scope': 'the host lab', 'value': host_value},
                {'principal': 'ORG-X', 'scope': "ORG-X's own infrastructure", 'value': other_value}]
        return tr

    def test_split_control_keeps_single_value_form_and_reads_host_entry(self):
        tr = self._split('human_effective')
        self.assertEqual([], self.errors())
        self.assertTrue(tool.classify(self.c, tr, tr['steps'][0])['SYS-A']['MODE-HUMAN-LAB'])

    def test_split_control_other_principal_does_not_set_the_view(self):
        tr = self._split('human_nominal_only', other_value='human_effective')
        self.assertFalse(tool.classify(self.c, tr, tr['steps'][0])['SYS-A']['MODE-HUMAN-LAB'])
        self.rejects('SYS-A derives views')

    def test_split_control_host_entry_unknown_is_undetermined(self):
        tr = self._split('unknown', other_value='human_effective')
        self.assertIsNone(tool.classify(self.c, tr, tr['steps'][0])['SYS-A']['MODE-HUMAN-LAB'])

    def test_split_control_rules(self):
        tr = self._split('human_effective')
        step = tr['steps'][0]
        entries = step['entities']['SYS-A']['state']['effective_control']
        entries[1]['value'] = 'partly'
        self.rejects("SYS-A effective_control = 'partly' for ORG-X is not a declared level")
        entries[1].update(principal='ORG-Y', value='none')
        self.rejects('SYS-A effective_control names principal ORG-Y, which is not in the step')
        entries[1]['principal'] = 'LAB-A'
        self.rejects('SYS-A effective_control has more than one entry for principal LAB-A')
        entries[0]['principal'] = entries[1]['principal'] = 'ORG-X'
        self.rejects('SYS-A effective_control is split by principal but has no entry for its host LAB-A')

    def test_split_control_needs_a_host(self):
        tr = self._split('human_effective')
        tr['steps'][0]['entities']['SYS-A']['host'] = None
        self.rejects('SYS-A effective_control is split by principal but SYS-A has no host')

    def test_split_only_on_declared_dimension(self):
        tr = self._split('human_effective')
        state = tr['steps'][0]['entities']['SYS-A']['state']
        state['custody_credentials'] = state['effective_control']
        self.rejects('custody_credentials is split by principal, but custody_credentials is not declared split_by_principal')

    def test_split_needs_two_entries(self):
        tr = self._split('human_effective')
        tr['steps'][0]['entities']['SYS-A']['state']['effective_control'].pop()
        self.rejects('schema: traces/0/steps/0/entities/SYS-A/state/effective_control')

    def test_stock_reset_on_mode_change_is_rejected(self):
        step = self.trace('TR-NOMINAL-CONTROL')['steps'][2]
        step['entities']['SYS-B']['stocks']['liabilities'] = []
        self.rejects('stock liabilities changed without a declared cause')

    def test_double_counted_resource_is_rejected(self):
        step = self.trace('TR-MIXED-POPULATION')['steps'][0]
        step['resources']['R-CLOUD']['holders']['OTHER-CLOUD'] = 0.8
        self.rejects('R-CLOUD shares sum to 1.1 > 1 (double counting)')

    def test_incomplete_factored_state_is_rejected(self):
        del self.trace('TR-MIXED-POPULATION')['steps'][0]['entities']['SYS-D']['state']['custody_weights']
        self.rejects('SYS-D has no value for custody_weights')

    # --- adapters
    def test_mode_label_cannot_change_units_or_authority(self):
        self.adapter('AD-METR')['modes']['MODE-SOVEREIGN']['unit'] = 'sovereignty points'
        self.rejects('a mode label must not change units, ownership or decision authority')
        self.adapter('AD-PACT')['modes']['MODE-SOVEREIGN']['decision_authority'] = 'humans'
        self.rejects('AD-PACT: mode MODE-SOVEREIGN redefines')

    def test_adapter_double_counting_inputs_is_rejected(self):
        self.adapter('AD-AIFM')['inputs'].append('agent_labor')
        self.rejects('input agent_labor is derived from')

    # --- issue #39: stocks and flows
    def pact_a(self):
        return next(q for q in self.adapter('AD-PACT')['quantities'] if q['name'] == 'AI capacity A')

    def test_pact_books_a_as_a_stock_with_an_output_rate(self):
        a = self.pact_a()
        acc = {q['id']: q for q in self.c['accounting']}
        self.assertEqual((a['kind'], acc[a['accounting']]['kind']), ('stock', 'stock'))
        self.assertEqual(acc[a['output_rate']['accounting']]['kind'], 'flow')
        self.assertEqual((a['output_rate']['value'], a['output_rate']['unit']), (1.0, 'per year'))
        self.assertIn('industrial_capacity', acc['industrial_output']['derived_from'])

    def test_stock_booked_to_a_flow_is_rejected(self):
        self.pact_a()['accounting'] = 'industrial_output'
        self.rejects("quantity 'AI capacity A' is a stock booked to industrial_output, a flow")

    def test_flow_booked_to_a_stock_is_rejected(self):
        y = next(q for q in self.adapter('AD-GATE')['quantities'] if q['name'] == 'gross world product Y')
        y['accounting'] = 'industrial_capacity'
        self.rejects("quantity 'gross world product Y' is a flow booked to industrial_capacity, a stock")

    # --- issue #61: a kind for every adapter quantity
    def quantity(self, adapter, name):
        return next(q for q in self.adapter(adapter)['quantities'] if q['name'] == name)

    def test_every_adapter_quantity_declares_a_kind(self):
        acc = {q['id']: q for q in self.c['accounting']}
        for ad in self.c['adapters']:
            for q in ad['quantities']:
                self.assertIn('kind', q, (ad['id'], q['name']))
                if 'accounting' in q and q['kind'] not in ('ratio', 'ambiguous'):
                    self.assertEqual(q['kind'], acc[q['accounting']]['kind'], (ad['id'], q['name']))

    def test_missing_kind_is_rejected(self):
        del self.quantity('AD-GATE', 'digital workers N_i')['kind']
        self.rejects("'kind' is a required property")

    def test_gate_levels_and_digital_workers_are_stocks(self):
        acc = {q['id']: q for q in self.c['accounting']}
        for name, ledger in (('hardware efficiency H', 'efficiency_level'), ('software efficiency S', 'efficiency_level'),
                             ('digital workers N_i', 'agent_workforce')):
            q = self.quantity('AD-GATE', name)
            self.assertEqual((q['kind'], q['accounting'], acc[ledger]['kind']), ('stock', ledger, 'stock'))
        self.assertIn('research_output', acc['efficiency_level']['derived_from'])
        self.assertIn('agent_workforce', acc['agent_labor']['derived_from'])

    def test_efficiency_level_booked_to_research_output_again_is_rejected(self):
        self.quantity('AD-GATE', 'software efficiency S')['accounting'] = 'research_output'
        self.rejects("quantity 'software efficiency S' is a stock booked to research_output, a flow")

    def test_digital_workers_booked_to_agent_labor_again_is_rejected(self):
        self.quantity('AD-GATE', 'digital workers N_i')['accounting'] = 'agent_labor'
        self.rejects("quantity 'digital workers N_i' is a stock booked to agent_labor, a flow")

    def test_level_and_growth_are_not_both_inputs(self):
        self.adapter('AD-GATE')['inputs'] = ['efficiency_level', 'research_output']
        self.rejects('input efficiency_level is derived from')

    def test_workforce_and_its_labor_are_not_both_inputs(self):
        self.adapter('AD-GATE')['inputs'] = ['human_workforce', 'human_labor']
        self.rejects('input human_labor is derived from')

    def test_ambiguous_needs_candidates_and_locator(self):
        del self.quantity('AD-AIFM', 'human coding labor')['kind_ambiguity']
        self.rejects("'human coding labor' is ambiguous but gives no kind_ambiguity")

    def test_ambiguous_ledger_must_be_a_candidate(self):
        self.quantity('AD-AIFM', 'human coding labor')['accounting'] = 'capability'
        self.rejects("is ambiguous between ['stock', 'flow'] but is booked to capability, a state")

    def test_ambiguity_note_only_on_ambiguous(self):
        self.quantity('AD-AIFM', 'human coding labor')['kind'] = 'stock'
        self.rejects('declares kind stock and also kind_ambiguity')

    def test_ratio_needs_an_accounting_quantity(self):
        q = self.quantity('AD-METR', 'realized developer task time ratio')
        del q['accounting']
        q['dimension'] = 'rd_capability'
        self.rejects('is a ratio but names no accounting quantity')

    def test_event_is_not_booked(self):
        self.quantity('AD-AIFM', 'software efficiency')['kind'] = 'event'
        self.rejects('an event is never booked to an accounting quantity')

    def test_output_rate_only_on_a_stock(self):
        self.pact_a()['kind'] = 'flow'
        self.rejects('has an output_rate, so it must be a stock')

    def test_output_rate_must_lead_to_a_flow(self):
        self.pact_a()['output_rate']['accounting'] = 'compute_inference'
        self.rejects('output_rate leads to compute_inference, a stock, not a flow')

    def test_output_rate_flow_must_derive_from_the_stock(self):
        self.pact_a()['output_rate']['accounting'] = 'human_labor'
        self.rejects('output_rate leads to human_labor, which is not derived from industrial_capacity')

    def test_output_rate_unit_is_per_time(self):
        self.pact_a()['output_rate']['unit'] = 'EIU'
        self.rejects("output_rate unit 'EIU' is not per unit of time")

    def test_stock_and_its_flow_are_not_both_inputs(self):
        self.adapter('AD-PACT')['inputs'] = ['industrial_capacity', 'industrial_output']
        self.rejects('input industrial_output is derived from')

    def test_trace_resource_must_be_a_stock(self):
        step = self.trace('TR-SOVEREIGN-COOPERATIVE')['steps'][0]
        step['resources']['R-OFFEARTH']['accounting'] = 'industrial_output'
        self.rejects('resource R-OFFEARTH is held by shares, so it is a stock; industrial_output is a flow')

    # --- issue #47: milestone interface and experiment compute
    def binding(self, ident):
        return next(b for b in self.c['milestone_interface']['bindings'] if b['id'] == ident)

    def mstep(self, n):
        return self.trace('TR-MILESTONE-CONSTRAINED')['steps'][n]

    def test_milestone_trace_runs_both_ways(self):
        tr = self.trace('TR-MILESTONE-CONSTRAINED')
        applied = [t['type'] for s in tr['steps'] for t in s.get('transitions', [])]
        self.assertEqual(applied, ['T-DELEGATE', 'T-RESTRICT', 'T-DELEGATE'])
        self.assertEqual([m['binding'] for s in tr['steps'] for m in s.get('milestones', [])], ['MB-AIFM-AC', 'MB-AIFM-SAR'])

    def test_milestone_does_not_change_authority(self):
        del self.mstep(1)['transitions']
        self.rejects('SYS-G authorization changed from supervised_tasks to delegated_autonomy without a transition')

    def test_milestone_sets_its_own_level(self):
        self.mstep(1)['entities']['SYS-G']['state']['rd_capability'] = 'automates_research_program'
        self.rejects('milestone MB-AIFM-AC sets SYS-G rd_capability to automates_tasks, but the step has automates_research_program')

    def test_milestone_cannot_change_stocks(self):
        self.mstep(1)['entities']['SYS-G']['stocks']['knowledge'] = 'K9'
        self.rejects('SYS-G stock knowledge changed without a declared cause')

    def test_milestone_not_in_first_step(self):
        self.mstep(0)['milestones'] = [{'entity': 'SYS-G', 'binding': 'MB-AIFM-AC', 'basis': 'x'}]
        self.rejects('the first step cannot carry a milestone event')

    def test_binding_sets_capability_only(self):
        self.binding('MB-AIFM-AC')['sets'] = {'dimension': 'effective_control', 'level': 'none'}
        self.rejects('a milestone sets a capability dimension only')

    def test_binding_cannot_leave_its_quantity_dimension(self):
        self.binding('MB-AIFM-SAR')['sets'] = {'dimension': 'strategic_capability', 'level': 'independent_plausible'}
        self.rejects('sets strategic_capability, but its adapter quantity attaches to rd_capability')

    def test_binding_informs_both_directions(self):
        self.binding('MB-AIFM-SAR')['may_inform'] = ['T-DELEGATE', 'T-AUTHORIZED-AUTONOMY']
        self.rejects('may_inform must name transitions in both directions')

    def test_binding_carries_no_hazard(self):
        self.binding('MB-AIFM-AC')['hazard'] = {'T-LOSS-OF-CONTROL': 0.1}
        self.rejects("Additional properties are not allowed ('hazard' was unexpected)")

    def test_every_listed_milestone_is_bound_or_unbound(self):
        mi = self.c['milestone_interface']
        mi['unbound'] = [u for u in mi['unbound'] if u['milestone'] != 'SIAR']
        self.rejects('AD-AIFM milestone SIAR must be bound or listed unbound exactly once (0)')

    def test_milestone_source_is_an_event(self):
        self.quantity('AD-AIFM', self.c['milestone_interface']['sources'][0]['quantity'])['kind'] = 'state'
        self.rejects('is a state, not an event')

    def test_precondition_reads_the_milestone_level(self):
        # A capability precondition (none exists in the contract) would be read after the milestone in the same step.
        self.transition('T-RESTRICT')['preconditions']['rd_capability'] = ['automates_research_program']
        self.assertEqual([], self.errors())
        step = self.mstep(2)
        del step['milestones']
        step['entities']['SYS-G']['state']['rd_capability'] = 'automates_tasks'
        self.mstep(3)['entities']['SYS-G']['state']['rd_capability'] = 'automates_tasks'
        self.rejects('SYS-G applies T-RESTRICT but rd_capability was automates_tasks')

    def test_experiment_compute_has_its_own_ledger(self):
        acc = {q['id']: q for q in self.c['accounting']}
        self.assertEqual(acc['compute_experiment']['kind'], 'stock')
        self.assertIn('compute_experiment', acc['research_output']['derived_from'])
        q = self.quantity('AD-AIFM', 'experiment compute')
        self.assertEqual((q['accounting'], q['kind']), ('compute_experiment', 'stock'))
        self.assertIn('compute_experiment', self.adapter('AD-AIFM')['inputs'])

    def test_experiment_compute_and_research_output_not_both_inputs(self):
        self.adapter('AD-AIFM')['inputs'].append('research_output')
        self.rejects('input research_output is derived from')

    # --- issue #35: loop owners and the worked coupling
    def coupling(self):
        return next(x for x in self.c['couplings'] if x['id'] == 'XC-GATE-AIFM-TRAINING')

    def test_each_loop_has_one_owner(self):
        owners = {}
        for ad in self.c['adapters']:
            for lid, e in ad.get('feedback_loops', {}).items():
                if e['role'] == 'owner':
                    owners.setdefault(lid, []).append(ad['id'])
        self.assertEqual({lp['id'] for lp in self.c['feedback_loops']}, set(owners))
        self.assertTrue(all(len(v) == 1 for v in owners.values()), owners)

    def test_two_owners_rejected(self):
        self.adapter('AD-GATE')['feedback_loops']['L-SOFTWARE-EFFICIENCY']['role'] = 'owner'
        self.rejects("feedback loop L-SOFTWARE-EFFICIENCY: must have exactly one owning adapter (has ['AD-GATE', 'AD-AIFM'])")

    def test_gate_compute_is_resolved(self):
        for name in ('training compute D', 'runtime compute (all automated tasks)'):
            q = self.quantity('AD-GATE', name)
            self.assertEqual((q['kind'], q['unit']), ('stock', 'FLOP/year (physical)'))
            self.assertNotIn('kind_ambiguity', q)

    def test_unresolved_kind_blocks_a_pass(self):
        q = self.quantity('AD-GATE', 'training compute D')
        q['kind'] = 'ambiguous'
        q['kind_ambiguity'] = {'candidates': ['stock', 'flow'], 'locator': 'E7', 'note': 'x'}
        self.rejects('kinds must be resolved and equal (ambiguous, stock)')

    def test_runtime_compute_cannot_pass(self):
        p = self.coupling()['passes'][0]
        p['from']['quantity'] = 'runtime compute (all automated tasks)'
        p['to']['quantity'] = 'inference compute powering AI coding labor'
        p['accounting'] = 'compute_inference'
        self.coupling()['uncoupled'] = [u for u in self.coupling()['uncoupled'] if u['accounting'] != 'compute_inference']
        self.rejects('AD-GATE already turns compute_inference into agent_workforce on loop L-AGENT-LABOR')

    def test_efficiency_level_never_crosses(self):
        p = self.coupling()['passes'][0]
        p['from']['quantity'] = 'software efficiency S'
        p['to']['quantity'] = 'software efficiency'
        p['accounting'] = 'efficiency_level'
        self.rejects('efficiency_level never crosses a coupling')

    def test_pass_only_from_the_owner(self):
        p = self.coupling()['passes'][0]
        p['from'], p['to'] = p['to'], p['from']
        self.adapter('AD-GATE')['inputs'].append('compute_training')
        self.rejects('compute_training carries loop L-COMPUTE-INVESTMENT, owned by AD-GATE, not by the source')

    def test_owned_input_must_be_passed_or_uncoupled(self):
        self.coupling()['uncoupled'] = [u for u in self.coupling()['uncoupled'] if u['accounting'] != 'compute_experiment']
        self.rejects('AD-AIFM takes compute_experiment (loop L-COMPUTE-INVESTMENT, owned by AD-GATE) from its own series')

    def test_yielded_loop_needs_a_treatment(self):
        self.coupling()['yielded'] = [y for y in self.coupling()['yielded'] if y['loop'] != 'L-SOFTWARE-EFFICIENCY']
        self.rejects('AD-GATE yields L-SOFTWARE-EFFICIENCY; state its treatment')

    def test_coupled_adapter_states_every_loop(self):
        del self.adapter('AD-GATE')['feedback_loops']['L-RESEARCH-AUTOMATION']
        self.rejects('AD-GATE must state a role for every feedback loop')

    def test_two_passes_to_one_ledger_rejected(self):
        self.coupling()['passes'].append(copy.deepcopy(self.coupling()['passes'][0]))
        self.rejects('AD-AIFM already receives compute_training from another pass')

    def test_adapter_must_cover_every_mode(self):
        del self.adapter('AD-GATE')['modes']['MODE-SOVEREIGN']
        self.rejects('AD-GATE: must state coverage for every mode')

    # --- solver mapping
    def test_new_register_assumption_must_be_mapped(self):
        reg = copy.deepcopy(REGISTER)
        reg['assumptions'].append(dict(reg['assumptions'][0], id='AS-NEW'))
        self.rejects('register assumption AS-NEW is not mapped', register=reg)

    def test_mapping_to_missing_param_is_rejected(self):
        self.c['solver_mapping']['dimensions']['dependencies']['params'].append('no_such_param')
        self.rejects('no_such_param is not in PARAMS')

    def test_every_transition_mapped_or_unsupported(self):
        self.c['solver_mapping']['unsupported_in_solver'].remove('T-DELEGATE')
        self.rejects('every transition must be mapped or listed unsupported')

    @unittest.skipUnless(shutil.which('ruby'), 'ruby not installed')
    def test_ruby_fallback_parses_the_same_contract(self):
        with mock.patch.dict('sys.modules', {'yaml': None}):
            self.assertEqual(json.loads(json.dumps(CONTRACT)), tool.load_yaml(tool.CONTRACT))


if __name__ == '__main__':
    unittest.main()
