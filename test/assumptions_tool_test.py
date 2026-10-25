import copy
import importlib.util
import json
from pathlib import Path
import shutil
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('assumptions_tool', ROOT / 'tools/assumptions_tool.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class AssumptionRegisterTest(unittest.TestCase):
    def setUp(self):
        self.reg = tool.load_yaml(tool.REGISTER)
        self.params = tool.load_params()

    def entry(self, ident):
        return next(a for a in self.reg['assumptions'] if a['id'] == ident)

    def rejects(self, message, params=None):
        errors = tool.validate(self.reg, params or self.params)
        self.assertTrue(any(message in e for e in errors), errors)

    def test_register_is_complete_and_claims_no_human_validation(self):
        self.assertEqual([], tool.validate(self.reg, self.params))
        self.assertTrue(all(a['status'] != 'human_validated' for a in self.reg['assumptions']))

    def test_new_param_without_entry_is_rejected(self):
        self.rejects('PARAMS entry new_knob has no register entry', dict(self.params, new_knob=0.0))

    def test_stale_param_is_rejected(self):
        self.reg['parameters']['gone'] = ['AS-KILLPRE']
        self.rejects('register parameter gone is not in PARAMS')

    def test_unknown_assumption_reference_is_rejected(self):
        self.reg['parameters']['chi0'] = ['AS-MISSING']
        self.rejects('unknown assumption AS-MISSING')

    def test_pro_pact_cole_answer_without_ablation_is_rejected(self):
        a = self.entry('AS-ELLINF')
        a['ablation'] = {'status': 'not_run', 'survived': 'n/a'}
        self.rejects('AS-ELLINF: Cole answer that favours the pact has no recorded ablation')

    def test_unablated_agent_default_is_allowed(self):
        a = self.entry('AS-CHI0')
        a['ablation'] = {'status': 'not_run', 'survived': 'n/a'}
        self.assertEqual([], tool.validate(self.reg, self.params))

    def test_ablation_without_location_is_rejected(self):
        self.entry('AS-KILLPRE')['ablation']['where'] = ' '
        self.rejects('must say where it was run')

    def test_value_drift_is_rejected(self):
        self.rejects('chi0 is recorded as 0.15 but its PARAMS baseline is 0.9', dict(self.params, chi0=0.9))

    def test_variant_values_are_not_compared(self):
        self.assertTrue(any(e.get('variant') for e in self.entry('AS-CRACKDOWN')['encoded_by']))

    def test_human_validation_needs_cole(self):
        self.entry('AS-KILLPRE')['status'] = 'human_validated'
        self.rejects('human_validated is set only by Cole')

    def test_duplicate_id_is_rejected(self):
        self.reg['assumptions'].append(copy.deepcopy(self.entry('AS-KILLPRE')))
        self.rejects('duplicate assumption ID AS-KILLPRE')

    def test_unknown_field_is_rejected(self):
        self.entry('AS-KILLPRE')['verified_by_me'] = True
        self.rejects('unknown fields')

    def test_report_ranks_never_ablated_first(self):
        rows = tool.ranked(self.reg)
        statuses = [a['ablation']['status'] for a in rows]
        self.assertEqual(statuses, sorted(statuses, key=lambda s: s != 'not_run'))

    def test_report_lists_priority_flags_whatever_the_direction(self):
        a = self.entry('AS-ACLOSE')
        a['priority'] = 'TEST FLAG'
        self.assertIn('| AS-ACLOSE | unclear |', tool.report(self.reg))

    @unittest.skipUnless(shutil.which('ruby'), 'ruby not installed')
    def test_ruby_fallback_parses_the_same_register(self):
        with mock.patch.dict('sys.modules', {'yaml': None}):
            self.assertEqual(json.loads(json.dumps(self.reg)), tool.load_yaml(tool.REGISTER))


if __name__ == '__main__':
    unittest.main()
