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
