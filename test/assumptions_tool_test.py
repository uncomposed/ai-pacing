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

    def test_unprefixed_claim_id_is_rejected(self):
        self.claim('AR-H1')['id'] = 'H1'
        self.rejects('claim H1: ID must look like AR-H1')

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

    # ---- issue #8: roles, evidence links, outcome labels, admission
    def claim(self, ident):
        return next(c for c in self.reg['claims'] if c['id'] == ident)

    def test_every_param_has_a_role_and_none_is_an_observation(self):
        roles = self.reg['parameter_roles']
        self.assertEqual(set(self.params), set(roles))
        self.assertFalse([p for p, r in roles.items() if r['role'] == 'observed_measurement'])

    def test_param_without_role_is_rejected(self):
        del self.reg['parameter_roles']['chi0']
        self.rejects('PARAMS entry chi0 has no role')

    def test_stakeholder_validation_is_not_empirical_support(self):
        r = self.reg['parameter_roles']['rho_h']
        r['role'] = 'observed_measurement'
        self.rejects('needs empirical_support records (stakeholder validation is not empirical support)')
        r['empirical_support'] = [{'record': 'EV-COLE-ROUND2', 'locator': 'R1'}]
        self.rejects('EV-COLE-ROUND2 is a stakeholder_statement, which cannot be cited as empirical_support')

    def test_model_output_is_not_empirical_support(self):
        r = self.reg['parameter_roles']['g']
        r['role'] = 'observed_measurement'
        r['empirical_support'] = [{'record': 'EV-METZGER-2013', 'locator': 'Fig. 2'}]
        self.rejects('EV-METZGER-2013 is a source_model_output, which cannot be cited as empirical_support')

    def test_secondary_reading_is_not_empirical_support(self):
        # The committed record has been read in primary form (#15); test the rule on a secondary-only copy.
        recs = copy.deepcopy(tool.evidence_tool.records_by_id())
        recs['EV-METR-HF-2026']['reading'] = 'read_secondary_only'
        self.entry('AS-SINGLE-AI')['evidence'][0]['use'] = 'empirical_support'
        errors = tool.validate(self.reg, self.params, recs)
        self.assertTrue(any('EV-METR-HF-2026 is read_secondary_only; only a record read in primary form can be empirical support'
                            in e for e in errors), errors)

    def test_unread_source_only_motivates(self):
        self.entry('AS-POWERSEEK')['evidence'][0]['use'] = 'source_model_basis'
        self.rejects('EV-TURNER-2019 was not read')

    def test_literature_assumption_needs_an_exact_evidence_link(self):
        del self.entry('AS-GROWTH-G')['evidence']
        self.rejects('AS-GROWTH-G: a literature source needs an evidence link')
        self.entry('AS-GCITE')['evidence'][0]['locator'] = ''
        self.rejects('without an exact locator')

    def test_unknown_evidence_record_is_rejected(self):
        self.entry('AS-ELLINF')['evidence'][0]['record'] = 'EV-NOPE'
        self.rejects('cites unknown evidence record EV-NOPE')

    def test_source_model_assumption_names_its_record(self):
        del self.reg['parameter_roles']['g']['source_model']
        self.rejects('input g: a source-model assumption names its source_model record')

    def test_derived_input_needs_known_parents(self):
        self.reg['other_inputs']['IN-Q-EFFECTIVE']['derived_from'] = ['q', 'IN-MISSING']
        self.rejects('derived_from names unknown input IN-MISSING')

    def test_share_claim_needs_outcome_label(self):
        del self.claim('AR-H10')['outcome_label']
        self.rejects('claim AR-H10: reports an outcome share but has no outcome_label')

    def test_outcome_label_cannot_claim_calibrated_probability(self):
        self.claim('AR-H10')['outcome_label']['interpretation'] = 'probability the pact holds'
        self.rejects('claim AR-H10: schema outcome_label')

    def test_outcome_label_interval_must_match_counts(self):
        self.claim('AR-H10')['outcome_label']['numerical_uncertainty'][1]['k'] = 30
        self.rejects('is not the Wilson 95% interval')

    def test_outcome_label_needs_all_uncertainty_types(self):
        del self.claim('AR-H10')['outcome_label']['uncertainty_types']['normative']
        self.rejects('claim AR-H10: schema outcome_label')

    def test_new_param_needs_admission(self):
        params = dict(self.params, new_knob=0.0)
        self.reg['parameters']['new_knob'] = ['AS-CHI0']
        self.reg['parameter_roles']['new_knob'] = {'role': 'project_assumption'}
        self.rejects('PARAMS entry new_knob was added after 2026-10-25 and has no admission record', params)
        self.reg['parameter_roles']['new_knob']['admission'] = {
            'basis': 'consequential_omission', 'evidence_path': 'planned: #9 comparison',
            'falsifier': 'no ranking change when varied', 'decision_impact': 'AR-H1 under renegotiation'}
        self.assertEqual([], tool.validate(self.reg, params))
        self.reg['parameter_roles']['new_knob']['admission']['basis'] = 'hunch'
        self.rejects('new_knob: admission basis must be one of', params)

    @unittest.skipUnless(shutil.which('ruby'), 'ruby not installed')
    def test_ruby_fallback_parses_the_same_register(self):
        with mock.patch.dict('sys.modules', {'yaml': None}):
            self.assertEqual(json.loads(json.dumps(self.reg)), tool.load_yaml(tool.REGISTER))


if __name__ == '__main__':
    unittest.main()
