#!/usr/bin/env python3
"""Validate traceability and evidence gates; never infer empirical truth from links."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import jsonschema

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'systems/model.json'
SCHEMA = ROOT / 'schema/systems-model.schema.json'
# These are typed references, not untyped dependency edges. Direction is explicit.
REFS = {
    'actors': {'specializes': 'actors', 'part_of': 'actors'}, 'resources': {'owners': 'actors'}, 'losses': {'stakeholders': 'actors'},
    'hazards': {'losses': 'losses'},
    'scenarios': {'actors': 'actors', 'resources': 'resources', 'hazards': 'hazards', 'use_cases': 'use_cases'},
    'challenges': {'scenarios': 'scenarios'},
    'requirements': {'challenges': 'challenges', 'scenarios': 'scenarios', 'accountable_actor': 'actors', 'hazards': 'hazards', 'derivation_interactions': 'interactions'},
    'hypotheses': {},
    'proposals': {'addresses': 'requirements', 'depends_on': 'hypotheses'},
    'evaluations': {'requirements': 'requirements', 'proposals': 'proposals'},
    'decisions': {'proposal': 'proposals', 'requirements': 'requirements', 'evaluations': 'evaluations',
                  'alternatives': 'proposals', 'decision_maker': 'actors'},
    'control_loops': {'controller': 'actors', 'resources': 'resources', 'requirements': 'requirements', 'hazards': 'hazards'},
    'conflicts': {'requirements': 'requirements', 'decision_owner': 'actors'},
    'use_cases': {'primary_actor': 'actors', 'participants': 'actors'},
    'interactions': {'actors': 'actors', 'scenarios': 'scenarios', 'use_cases': 'use_cases', 'candidate_requirements': 'requirements'},
}
PREFIXES = dict(zip(['sources', *REFS], ['SRC', 'ACT', 'RES', 'LOSS', 'HAZ', 'SC', 'CH', 'REQ', 'HYP', 'PROP', 'EV', 'DEC', 'CTRL', 'CON', 'UC', 'INT']))

def values(value):
    return value if isinstance(value, list) else [value]

def validate(model):
    schema = json.loads(SCHEMA.read_text())
    errors = [f"schema {'.'.join(map(str, e.path))}: {e.message}" for e in
              jsonschema.Draft202012Validator(schema).iter_errors(model)]
    if errors:
        return errors
    for c in ('actors', 'requirements'):
        for n in model[c]:
            if n['validation'] == 'validated' and not n['validation_artifact'].strip():
                errors.append(f"{n['id']}: validation requires a recorded artifact")
    for h in model['hypotheses']:
        if h['status'] != 'untested' and (not h['assessment_artifact'].strip() or h['reviewer'] == 'unassigned'):
            errors.append(f"{h['id']}: hypothesis assessment requires evidence and reviewer")
    groups = {c: {n['id']: n for n in model[c]} for c in PREFIXES}
    seen = set()
    for c in PREFIXES:
        for n in model[c]:
            ident = n['id']
            if ident in seen:
                errors.append(f'duplicate ID {ident}')
            seen.add(ident)
            if not ident.startswith(PREFIXES[c] + '-'):
                errors.append(f'{ident}: wrong prefix for {c}')
            fields = {**REFS.get(c, {}), **({'sources': 'sources'} if c != 'sources' else {})}
            for field, target in fields.items():
                for ref in values(n[field]):
                    if ref not in groups[target]:
                        errors.append(f'{ident}: {field} requires {target}, got {ref}')
    if errors:
        return errors
    # Organizational membership and specialization are separate acyclic relations.
    for relation in ('specializes', 'part_of'):
        done, active = set(), set()
        def visit(ident):
            if ident in active:
                errors.append(f'{ident}: cycle in actor {relation}')
                return
            if ident in done:
                return
            active.add(ident)
            for parent in groups['actors'][ident][relation]:
                visit(parent)
            active.remove(ident)
            done.add(ident)
        for ident in groups['actors']:
            visit(ident)
    for scenario in model['scenarios']:
        for ident in scenario['use_cases']:
            case = groups['use_cases'][ident]
            if not {case['primary_actor'], *case['participants']} <= set(scenario['actors']):
                errors.append(f"{scenario['id']}: use case participants missing for {ident}")
    for interaction in model['interactions']:
        ident = interaction['id']
        scoped_actors = {a for sid in interaction['scenarios'] for a in groups['scenarios'][sid]['actors']}
        scoped_cases = {u for sid in interaction['scenarios'] for u in groups['scenarios'][sid]['use_cases']}
        if not set(interaction['actors']) <= scoped_actors or not set(interaction['use_cases']) <= scoped_cases:
            errors.append(f'{ident}: interaction outside scenario scope')
        choice_actors = [c['actor'] for c in interaction['actor_choices']]
        if len(choice_actors) != len(set(choice_actors)) or not set(choice_actors) <= set(interaction['actors']):
            errors.append(f'{ident}: invalid actor choices')
        if interaction['status'] == 'validated' and not interaction['validation_artifact'].strip():
            errors.append(f'{ident}: validated interaction requires evidence')
        for rid in interaction['candidate_requirements']:
            if ident not in groups['requirements'][rid]['derivation_interactions']:
                errors.append(f'{ident}: asymmetric requirement derivation {rid}')
    def covered(collection, field, target):
        return any(target in values(n[field]) for n in model[collection])
    for c, downstream, field in [('actors', 'scenarios', 'actors'), ('resources', 'scenarios', 'resources'),
                                  ('losses', 'hazards', 'losses'), ('hazards', 'requirements', 'hazards'),
                                  ('scenarios', 'challenges', 'scenarios'), ('challenges', 'requirements', 'challenges'),
                                  ('requirements', 'evaluations', 'requirements'), ('use_cases', 'scenarios', 'use_cases')]:
        for ident in groups[c]:
            if not covered(downstream, field, ident):
                errors.append(f'{ident}: missing coverage in {downstream}.{field}')
    for r in model['requirements']:
        for ident in r['derivation_interactions']:
            interaction = groups['interactions'][ident]
            if r['id'] not in interaction['candidate_requirements']:
                errors.append(f"{r['id']}: asymmetric interaction derivation {ident}")
            if not set(r['scenarios']) & set(interaction['scenarios']):
                errors.append(f"{r['id']}: derivation outside scenario scope")
            if r['status'] in ('baselined', 'satisfied') and interaction['status'] != 'validated':
                errors.append(f"{r['id']}: baselining requires validated interaction {ident}")
        parent_scope = {s for c in r['challenges'] for s in groups['challenges'][c]['scenarios']}
        if not set(r['scenarios']) <= parent_scope:
            errors.append(f"{r['id']}: scenario outside challenge scope")
        scenarios = [groups['scenarios'][i] for i in r['scenarios']]
        scoped_hazards = {h for s in scenarios for h in s['hazards']}
        if not set(r['hazards']) <= scoped_hazards:
            errors.append(f"{r['id']}: hazard outside challenge scenario scope")
        if r['status'] in ('baselined', 'satisfied') and (r['unresolved'] or r['validation'] != 'validated'):
            errors.append(f"{r['id']}: unresolved or unvalidated requirement cannot be baselined")
        if r['status'] == 'satisfied' and not any(e['status'] == 'passed' and r['id'] in e['requirements'] for e in model['evaluations']):
            errors.append(f"{r['id']}: satisfaction requires passed evaluation")
    for e in model['evaluations']:
        if e['status'] != 'planned' and not e['proposals']:
            errors.append(f"{e['id']}: completed evaluation requires a candidate")
        # All proposals named by an evaluation must address all named requirements.
        for p in e['proposals']:
            if not set(e['requirements']) <= set(groups['proposals'][p]['addresses']):
                errors.append(f"{e['id']}: evaluation scope not addressed by {p}")
        if e['status'] != 'planned' and (not e['artifact'].strip() or e['reviewer'] == 'unassigned'):
            errors.append(f"{e['id']}: completed evaluation requires evidence artifact and reviewer")
        if e['status'] == 'passed':
            for ident in e['requirements']:
                r = groups['requirements'][ident]
                if r['unresolved'] or r['validation'] != 'validated' or r['status'] not in ('baselined', 'satisfied'):
                    errors.append(f"{e['id']}: pass requires a resolved baselined requirement {ident}")
    for d in model['decisions']:
        p = groups['proposals'][d['proposal']]
        if d['proposal'] in d['alternatives']:
            errors.append(f"{d['id']}: proposal is its own alternative")
        if not set(d['requirements']) <= set(p['addresses']):
            errors.append(f"{d['id']}: decision exceeds proposal scope")
        evidence = [groups['evaluations'][x] for x in d['evaluations']]
        if any(not set(e['proposals']) <= {d['proposal'], *d['alternatives']} for e in evidence):
            errors.append(f"{d['id']}: unrelated evaluation")
        if d['outcome'] == 'select':
            if p['status'] != 'selected':
                errors.append(f"{d['id']}: selection and proposal status disagree")
            if any(groups['hypotheses'][h]['status'] != 'supported' for h in p['depends_on']):
                errors.append(f"{d['id']}: selection depends on unsupported hypothesis")
            for req in d['requirements']:
                if not any(e['status'] == 'passed' and d['proposal'] in e['proposals'] and req in e['requirements'] for e in evidence):
                    errors.append(f"{d['id']}: selection lacks passed evidence for {req}")
            for alternative in d['alternatives']:
                if not any(alternative in e['proposals'] and e['status'] != 'planned' for e in evidence):
                    errors.append(f"{d['id']}: alternative {alternative} lacks completed comparison")
    for p in model['proposals']:
        if p['status'] == 'selected':
            covered_reqs = {r for d in model['decisions'] if d['proposal'] == p['id'] and d['outcome'] == 'select' for r in d['requirements']}
            if not set(p['addresses']) <= covered_reqs:
                errors.append(f"{p['id']}: selection requires decisions for its complete claimed scope")
        if not covered('evaluations', 'proposals', p['id']):
            errors.append(f"{p['id']}: missing evaluation plan")
    return sorted(errors)

def report(model):
    lines = ['# Systems model traceability', '',
             'Generated from `systems/model.json`. Links express proposed coverage, not proven satisfaction.', '',
             '| Requirement | Challenge | Proposals | Evaluation | Status |', '|---|---|---|---|---|']
    for r in model['requirements']:
        ps = ', '.join(p['id'] for p in model['proposals'] if r['id'] in p['addresses']) or 'None'
        es = ', '.join(e['id'] for e in model['evaluations'] if r['id'] in e['requirements'])
        lines.append(f"| {r['id']}: {r['title']} | {', '.join(r['challenges'])} | {ps} | {es} | {r['status']} |")
    lines += ['', '## Open obligations', '']
    for r in model['requirements']:
        lines.extend(f"- {r['id']}: {u}" for u in r['unresolved'])
    lines += ['', '## Unresolved conflicts', '']
    lines += [f"- {c['id']}: {c['statement']}" for c in model['conflicts']]
    return '\n'.join(lines) + '\n'

def trace_requirement(model, ident):
    """Render recorded paths without treating graph connectivity as entailment."""
    groups = {c: {n['id']: n for n in model[c]} for c in PREFIXES}
    r = groups['requirements'][ident]
    digest = hashlib.sha256(json.dumps(model, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    lines = [f"# {ident}: {r['title']}", '', r['statement'], '',
             f"Model {model['model_version']}; snapshot SHA-256 `{digest}`.", '',
             f"Status: {r['status']}; validation: {r['validation']}; basis: {r['basis']}.", '',
             '**Reading rule:** These are recorded rationales and coverage claims, not proven entailments. '
             'A proposal is not evidence that a requirement is necessary or satisfied.', '',
             '## Upstream: challenge and operating scope', '']
    source_ids = set(r['sources'])
    for cid in r['challenges']:
        c = groups['challenges'][cid]
        lines += [f"- {cid}: {c['statement']}"]
        source_ids.update(c['sources'])
    for sid in r['scenarios']:
        s = groups['scenarios'][sid]
        lines += [f"- {sid}: {s['statement']}", f"  - Success: {s['success']}", f"  - Adverse path: {s['adverse']}"]
        source_ids.update(s['sources'])
    lines += ['', '## Upstream: actor interests and derivation', '']
    for iid in r['derivation_interactions']:
        i = groups['interactions'][iid]
        lines += [f"### {iid}: {i['title']}", '',
                  f"Interaction status: {i['status']}; scenarios: {', '.join(i['scenarios'])}.", '',
                  f"Conflict: {i['statement']}", '',
                  f"Information difference: {i['information_asymmetry']}", '',
                  f"Recorded rationale: {i['derivation']}", '',
                  f"Counterfactual test: {i['counterfactual']}", '', 'Actors directly named in this interaction:', '']
        source_ids.update(i['sources'])
        for aid in i['actors']:
            a = groups['actors'][aid]
            lines += [f"- {aid}: {a['title']} ({a['validation']})",
                      f"  - Goals: {'; '.join(a['goals'])}.",
                      f"  - Constraints: {'; '.join(a['constraints'])}.",
                      f"  - Dependencies: {'; '.join(a['dependencies'])}."]
            source_ids.update(a['sources'])
        lines += ['', 'Use cases referenced by the interaction (may include additional participants):', '']
        for uid in i['use_cases']:
            u = groups['use_cases'][uid]
            lines += [f"- {uid}: {u['title']}; primary actor: {u['primary_actor']}",
                      f"  - Goal: {u['statement']}",
                      f"  - Actor-relative success: {u['actor_success']}"]
            source_ids.update(u['sources'])
    lines += ['', '## Upstream: hazardous states and stakeholder losses', '']
    for hid in r['hazards']:
        h = groups['hazards'][hid]
        lines += [f"- {hid}: {h['statement']}"]
        source_ids.update(h['sources'])
        for lid in h['losses']:
            loss = groups['losses'][lid]
            lines += [f"  - {lid}: {loss['statement']} Stakeholders: {', '.join(loss['stakeholders'])}."]
            source_ids.update(loss['sources'])
    owner = groups['actors'][r['accountable_actor']]
    lines += ['', '## Allocation and downstream candidate mechanisms', '',
              f"Accountable role: {owner['id']} — {owner['title']} ({owner['category']}). "
              'Concrete authority and resources still require validation.', '']
    proposals = [p for p in model['proposals'] if ident in p['addresses']]
    if not proposals:
        lines += ['No proposed mechanism is allocated.']
    for p in proposals:
        lines += [f"- {p['id']}: {p['title']} ({p['status']}) — {p['statement']}"]
        for hid in p['depends_on']:
            h = groups['hypotheses'][hid]
            lines += [f"  - Depends on {hid} ({h['status']}): {h['statement']}",
                      f"    - Stop crediting it when: {h['stopping_rule']}"]
    lines += ['', '## Evidence path and unresolved obligations', '', f"Criterion: {r['criterion']}", '']
    for e in model['evaluations']:
        if ident in e['requirements']:
            lines += [f"- {e['id']} ({e['status']}); candidate: {', '.join(e['proposals']) or 'unallocated'}",
                      f"  - Method: {e['method']}", f"  - Baseline: {e['baseline']}",
                      f"  - Pass rule: {e['pass_rule']}",
                      f"  - Evidence: {e['artifact'] or 'none'}; reviewer: {e['reviewer']}."]
    lines += ['', 'Unresolved:', ''] + [f'- {item}' for item in r['unresolved']]
    lines += ['', 'Cross-requirement conflicts:', '']
    conflicts = [c for c in model['conflicts'] if ident in c['requirements']]
    lines += [f"- {c['id']}: {c['statement']} Resolution: {c['resolution']}." for c in conflicts] or ['None recorded; absence is not evidence of completeness.']
    lines += ['', '## Upstream source register', '',
              'These sources locate intent and analytical inputs. They are not interchangeable with empirical evidence.', '']
    for sid in sorted(source_ids):
        source = groups['sources'][sid]
        lines += [f"- {sid} ({source['role']}): {source['locator']}"]
    lines += ['', '## Limits of this trace', '',
              '- Goal statements do not yet have independently versioned goal IDs or per-goal evidence.',
              '- Actor templates have not been bound to concrete institutions, people, jurisdictions, or calibrated preferences.',
              '- Interaction rationales must be reviewed for each requirement; the same interaction can motivate several distinct obligations.',
              '- Traceability establishes inspectable relationships, not necessity, sufficiency, exhaustive coverage, or real-world safety.']
    return '\n'.join(lines) + '\n'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'report', 'trace'])
    parser.add_argument('--requirement', help='Requirement ID for trace, for example REQ-COMPETE')
    parser.add_argument('--model', type=Path, default=MODEL)
    args = parser.parse_args()
    model = json.loads(args.model.read_text())
    errors = validate(model)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    if args.command == 'trace':
        if args.requirement not in {r['id'] for r in model['requirements']}:
            parser.error('trace requires --requirement with a known requirement ID')
        print(trace_requirement(model, args.requirement), end='')
    elif args.command == 'report':
        print(report(model), end='')
    else:
        count = sum(len(model[c]) for c in PREFIXES)
        print(f'Systems model: {count} records; structural and evidence-gate checks passed; empirical validation remains open.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
