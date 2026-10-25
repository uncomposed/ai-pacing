import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('omissions_tool', ROOT / 'tools/omissions_tool.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class OmissionMatrixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = tool.load_all()

    def setUp(self):
        self.matrix, self.actors, self.reg, self.modes, self.nodes = copy.deepcopy(self.base)

    def errors(self, view=None):
        return tool.validate(self.matrix, self.actors, self.reg, self.modes, self.nodes, view)

    def rejects(self, message):
        errs = self.errors()
        self.assertTrue(any(message in e for e in errs), errs)

    def entry(self, ident):
        return next(e for e in self.matrix['omissions'] if e['id'] == ident)

    def structure(self, ident):
        return next(s for s in self.actors['structures'] if s['id'] == ident)

    def test_committed_matrix_and_view_pass(self):
        self.assertEqual([], self.errors(tool.VIEW.read_text()))

    def test_missing_issue_item_is_rejected(self):
        self.matrix['omissions'] = [e for e in self.matrix['omissions'] if e['id'] != 'OM-HETEROGENEITY']
        self.rejects('issue #9 item state_heterogeneity has no omission entry')

    def test_d18_checks_are_required(self):
        self.entry('OM-LEARNING')['issue_items'] = []
        self.rejects('issue #9 item d18_learning_after_failed_strike has no omission entry')

    def test_bad_status_is_rejected(self):
        self.entry('OM-PRIVATE-INFO')['status'] = 'probably_fine'
        self.rejects("status 'probably_fine' is not one of")

    def test_implemented_without_tests_is_rejected(self):
        self.entry('OM-RENEG-UP')['tests'] = []
        self.rejects('status implemented_tested needs tests')

    def test_unknown_test_is_rejected(self):
        self.entry('OM-RENEG-UP')['tests'] = ['tests/test_variants.py::Bargaining::test_does_not_exist']
        self.rejects('not found')

    def test_excluded_without_scope_is_rejected(self):
        del self.entry('OM-LAB-SYSTEMS')['scope']
        self.rejects('status excluded_scoped needs scope')

    def test_unresolved_without_next_step_is_rejected(self):
        del self.entry('OM-MULTI-AGENT')['next_step']
        self.rejects('status unresolved needs next_step')

    def test_missing_narrowed_claim_is_rejected(self):
        self.entry('OM-TIGHTEN')['narrowed_claim'] = ''
        self.rejects('missing narrowed_claim')

    def test_unknown_assumption_and_conclusion_are_rejected(self):
        self.entry('OM-TIGHTEN')['assumptions'].append('AS-NOPE')
        self.entry('OM-TIGHTEN')['conclusions'].append('AR-H99')
        self.entry('OM-TIGHTEN')['conclusions'].append('D999')
        self.rejects('assumption AS-NOPE is not in the register')
        self.rejects('conclusion AR-H99 is not a register claim')
        self.rejects('conclusion D999 is not a register claim or a spec node')

    def test_unrecorded_variant_is_rejected(self):
        self.entry('OM-RENEG-UP')['variant'] = 'variants/rankings.py'
        self.rejects('variant variants/rankings.py is used by an entry but not recorded')

    def test_actor_structure_rejects_capacity_multiplier(self):
        self.structure('AST-COPIES')['capacity_multiplier'] = 10
        self.rejects('fields outside the contract')
        self.structure('AST-COPIES')['entities']['SWARM']['A_mult'] = 10
        self.rejects("fields outside the contract ['A_mult']")

    def test_actor_structure_rejects_unknown_level_and_kind(self):
        self.structure('AST-COPIES')['entities']['SWARM']['state']['effective_control'] = 'mostly'
        self.structure('AST-COPIES')['entities']['WEIGHTS']['kind'] = 'swarm'
        self.rejects("'mostly' is not a level of effective_control")
        self.rejects("kind 'swarm' is not a contract entity kind")

    def test_actor_structure_rejects_dimension_on_wrong_kind(self):
        self.structure('AST-LAB-CAPABLE')['entities']['LAB']['state']['custody_weights'] = 'human_institution'
        self.rejects('custody_weights does not apply to lab')

    def test_stale_view_is_rejected(self):
        errs = self.errors(tool.VIEW.read_text() + 'edited by hand\n')
        self.assertTrue(any('stale' in e for e in errs), errs)


if __name__ == '__main__':
    unittest.main()
