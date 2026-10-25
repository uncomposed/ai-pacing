import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('systems_tool', ROOT / 'tools/systems_tool.py')
systems = importlib.util.module_from_spec(spec)
spec.loader.exec_module(systems)

class SystemsModelTest(unittest.TestCase):
    def setUp(self):
        self.model = json.loads(systems.MODEL.read_text())

    def node(self, collection, ident):
        return next(n for n in self.model[collection] if n['id'] == ident)

    def rejects(self, message):
        errors = systems.validate(self.model)
        self.assertTrue(any(message in e for e in errors), errors)

    def test_draft_is_valid_but_claims_no_satisfaction(self):
        self.assertEqual([], systems.validate(self.model))
        self.assertTrue(all(r['status'] == 'candidate' for r in self.model['requirements']))
        self.assertTrue(all(e['status'] == 'planned' for e in self.model['evaluations']))
        self.assertEqual([], self.model['decisions'])

    def test_unknown_fields_are_rejected(self):
        self.model['requirements'][0]['satisfies'] = ['PROP-REPORT']
        self.rejects('Additional properties')

    def test_wrong_reference_type_is_rejected(self):
        self.model['proposals'][0]['addresses'] = ['ACT-LAB']
        self.rejects('requires requirements')

    def test_duplicate_id_is_rejected(self):
        self.model['requirements'][1]['id'] = self.model['requirements'][0]['id']
        self.rejects('duplicate ID')

    def test_unknown_provenance_is_rejected(self):
        self.model['requirements'][0]['sources'] = ['SRC-MISSING']
        self.rejects('requires sources')

    def test_missing_hazard_coverage_is_rejected(self):
        h = copy.deepcopy(self.model['hazards'][0]);h['id'] = 'HAZ-UNCOVERED'
        self.model['hazards'].append(h)
        self.rejects('missing coverage')

    def test_out_of_scope_scenario_is_rejected(self):
        self.model['requirements'][0]['scenarios'] = ['SC-COORD']
        self.rejects('scenario outside challenge scope')

    def test_out_of_scope_hazard_is_rejected(self):
        self.model['requirements'][0]['hazards'] = ['HAZ-RACE']
        self.rejects('hazard outside challenge scenario scope')

    def test_false_satisfaction_is_rejected(self):
        self.model['requirements'][0]['status'] = 'satisfied'
        self.rejects('satisfaction requires passed evaluation')

    def test_unresolved_requirement_cannot_be_baselined(self):
        self.model['requirements'][0]['status'] = 'baselined'
        self.rejects('unresolved or unvalidated')

    def test_validation_requires_artifact(self):
        self.model['requirements'][0]['validation'] = 'validated'
        self.rejects('validation requires a recorded artifact')

    def test_completed_evaluation_requires_evidence(self):
        self.model['evaluations'][0]['status'] = 'failed'
        self.rejects('completed evaluation requires evidence')

    def test_hypothesis_promotion_requires_assessment(self):
        self.model['hypotheses'][0]['status'] = 'supported'
        self.rejects('hypothesis assessment requires evidence')

    def test_missing_unsafe_action_category_is_rejected(self):
        del self.model['control_loops'][0]['unsafe_actions']['wrong_timing']
        self.rejects('required property')

    def test_selected_proposal_requires_complete_scope(self):
        self.model['proposals'][0]['status'] = 'selected'
        self.rejects('selection requires decisions')

    def selected_fixture(self):
        # Synthetic records exercise the gate. They are not empirical evidence.
        p = self.node('proposals', 'PROP-THIRD');p['status'] = 'selected'
        h = self.node('hypotheses', 'HYP-EXPERT')
        h.update(status='supported', assessment_artifact='fixture://assessment', reviewer='fixture reviewer')
        evidence = []
        for r in self.model['requirements']:
            if r['id'] in p['addresses']:
                r.update(status='baselined', unresolved=[], validation='validated', validation_artifact='fixture://validation')
                for ident in r['derivation_interactions']:
                    self.node('interactions', ident).update(status='validated', validation_artifact='fixture://interaction')
        for e in self.model['evaluations']:
            if e['requirements'][0] in p['addresses'] and e['proposals'][0] in ['PROP-THIRD', 'PROP-PUBLIC']:
                e.update(status='passed' if e['proposals']==['PROP-THIRD'] else 'failed', artifact='fixture://evaluation', reviewer='fixture reviewer')
                evidence.append(e['id'])
        self.model['decisions'] = [{
            'id':'DEC-TEST','title':'Synthetic selection','statement':'Test gate only.',
            'sources':['SRC-SYNTHESIS'],'basis':'analyst-inference',
            'proposal':'PROP-THIRD','requirements':p['addresses'], 'evaluations':evidence,
            'alternatives':['PROP-PUBLIC'],'outcome':'select','decision_maker':'ACT-AUTHORITY',
            'rationale':'Synthetic comparison.','residual_risks':'Fixture only.', 'revisit_trigger':'Changed scope.'}]

    def test_scoped_evidence_can_pass_selection_gate(self):
        self.selected_fixture()
        self.assertEqual([], systems.validate(self.model))

    def test_other_candidate_evidence_cannot_establish_selection(self):
        self.selected_fixture()
        for e in self.model['evaluations']:
            if e['proposals'] == ['PROP-THIRD']:e['status'] = 'failed'
            elif e['proposals'] == ['PROP-PUBLIC'] and e['id'] in self.model['decisions'][0]['evaluations']:e['status'] = 'passed'
        self.rejects('selection lacks passed evidence')

    def test_unsupported_dependency_blocks_selection(self):
        self.selected_fixture()
        self.node('hypotheses','HYP-EXPERT')['status'] = 'refuted'
        self.rejects('selection depends on unsupported hypothesis')

    def test_unperformed_alternative_comparison_blocks_selection(self):
        self.selected_fixture()
        for e in self.model['evaluations']:
            if e['proposals'] == ['PROP-PUBLIC']:e['status'] = 'planned'
        self.rejects('lacks completed comparison')

    def test_report_is_deterministic(self):
        self.assertEqual(systems.report(self.model), systems.report(copy.deepcopy(self.model)))

    def test_new_requirement_can_have_an_unallocated_plan(self):
        r = copy.deepcopy(self.model['requirements'][0]);r['id'] = 'REQ-NEW'
        self.model['requirements'].append(r)
        for ident in r['derivation_interactions']:
            self.node('interactions', ident)['candidate_requirements'].append(r['id'])
        e = copy.deepcopy(self.model['evaluations'][0])
        e.update(id='EV-NEW', requirements=['REQ-NEW'], proposals=[])
        self.model['evaluations'].append(e)
        self.assertEqual([], systems.validate(self.model))
        e.update(status='passed', artifact='fixture://evidence', reviewer='fixture reviewer')
        self.rejects('completed evaluation requires a candidate')

    def test_actor_specialization_cycle_is_rejected(self):
        self.node('actors', 'ACT-LAB')['specializes'] = ['ACT-BEHIND-LAB']
        self.rejects('cycle in actor specializes')

    def test_actor_membership_cycle_is_rejected(self):
        self.node('actors', 'ACT-FEDERAL')['part_of'] = ['ACT-REGULATOR']
        self.rejects('cycle in actor part_of')

    def test_use_case_cannot_hide_a_participant(self):
        self.node('scenarios', 'SC-REPORT')['actors'].remove('ACT-EMPLOYEE')
        self.rejects('use case participants missing')

    def test_interaction_cannot_assign_choices_to_an_unrelated_actor(self):
        self.node('interactions', 'INT-REPORT')['actor_choices'][0]['actor'] = 'ACT-COURTS'
        self.rejects('invalid actor choices')

    def test_derivation_requires_matching_links(self):
        self.node('requirements', 'REQ-REPORT')['derivation_interactions'].remove('INT-REPORT')
        self.rejects('asymmetric requirement derivation')

    def test_unvalidated_actor_interaction_blocks_baseline(self):
        self.selected_fixture()
        self.node('interactions', 'INT-ENTRY')['status'] = 'unvalidated'
        self.rejects('baselining requires validated interaction')

    def test_interaction_validation_requires_an_artifact(self):
        self.node('interactions', 'INT-REPORT')['status'] = 'validated'
        self.rejects('validated interaction requires evidence')

    def test_every_requirement_has_a_renderable_trace(self):
        for requirement in self.model['requirements']:
            with self.subTest(requirement=requirement['id']):
                trace = systems.trace_requirement(self.model, requirement['id'])
                self.assertIn('Status: candidate; validation: unvalidated', trace)
                self.assertIn('Evidence: none; reviewer: unassigned.', trace)
                self.assertIn('## Limits of this trace', trace)

    def test_competition_trace_preserves_conflict_and_distinguishes_candidates(self):
        trace = systems.trace_requirement(self.model, 'REQ-COMPETE')
        for ident in ['ACT-BEHIND-LAB', 'UC-CATCHUP', 'INT-ENTRY', 'HAZ-CAPTURE',
                      'LOSS-BENEFIT', 'PROP-RIVAL', 'PROP-PUBLIC', 'CON-COMPETE', 'SRC-ACTOR-CORRECTION']:
            self.assertIn(ident, trace)
        self.assertIn('unvalidated', trace)
        self.assertNotIn('EV-COOPERATE', trace)

    def test_trace_snapshot_changes_when_upstream_actor_changes(self):
        before = systems.trace_requirement(self.model, 'REQ-COMPETE')
        self.node('actors', 'ACT-BEHIND-LAB')['goals'].append('Additional hypothetical goal')
        after = systems.trace_requirement(self.model, 'REQ-COMPETE')
        self.assertNotEqual(before.split('snapshot SHA-256')[1].splitlines()[0],
                            after.split('snapshot SHA-256')[1].splitlines()[0])
        self.assertIn('Additional hypothetical goal', after)

if __name__ == '__main__':
    unittest.main()
