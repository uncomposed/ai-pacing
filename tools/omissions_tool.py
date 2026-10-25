#!/usr/bin/env python3
"""Keep the off-Earth model's omission matrix (issue #9) consistent; never infer that an omission is harmless.

    python3 tools/omissions_tool.py check    # fail on any gap (wired into make check)
    python3 tools/omissions_tool.py render   # rewrite the Markdown view, results/omissions.md, from the YAML

The matrix is model/omissions.yaml; the actor-structure design note is model/variants/actor_structures.yaml.
`check` fails when
  1. an omission named in #9 (or one of the two D18 checks carried over from #3) has no entry;
  2. an entry's status is not implemented_tested, excluded_scoped or unresolved, or lacks what its status needs:
     implemented_tested -> variant file, result files and test names that exist; excluded_scoped -> reason and scope;
     unresolved -> next_step; every entry -> narrowed_claim and finding;
  3. an assumption ID is not in the register (model/assumptions.yaml), or a conclusion ID is neither a register claim
     (AR-H*) nor a node in spec/ai-pacing.yaml;
  4. the variant-selection record names a variant that is not used by an entry, or an entry's variant is not recorded;
  5. an actor structure uses an entity kind, dimension, level or transition that systems/modes.yaml does not declare,
     a dimension on a kind it does not apply to, a host that is not in the structure, an omission ID that is not in
     the matrix, or any field outside the contract (so no capacity multiplier can stand in for an actor structure);
  6. results/omissions.md differs from what `render` would write.
"""
import argparse
import importlib.util
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / 'research_notes/Off Earth industry as misalignment control/model'
MATRIX = MODEL_DIR / 'omissions.yaml'
ACTORS = MODEL_DIR / 'variants/actor_structures.yaml'
VIEW = MODEL_DIR / 'results/omissions.md'
REGISTER = MODEL_DIR / 'assumptions.yaml'
SPEC = ROOT / 'spec/ai-pacing.yaml'
MODES = ROOT / 'systems/modes.yaml'

_spec = importlib.util.spec_from_file_location('assumptions_tool', ROOT / 'tools/assumptions_tool.py')
_at = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_at)
load_yaml = _at.load_yaml

REQUIRED_ITEMS = {
    'renegotiation_up', 'renegotiation_down', 'human_preventive_action', 'defensive_human_assets',
    'state_heterogeneity', 'private_information', 'equilibrium_selection', 'ai_objective_beliefs',
    'post_rival_dynamics', 'multi_agent_coalitions', 'sovereign_capable_lab_systems', 'improving_human_control',
    'd18_learning_after_failed_strike', 'd18_humans_strike_first',
}
STATUSES = {'implemented_tested', 'excluded_scoped', 'unresolved'}
ENTRY_FIELDS = {'id', 'title', 'issue_items', 'assumptions', 'conclusions', 'status', 'finding', 'narrowed_claim',
                'variant', 'results', 'tests', 'reason', 'scope', 'next_step', 'design'}
STATUS_NEEDS = {'implemented_tested': ('variant', 'results', 'tests'), 'excluded_scoped': ('reason', 'scope'),
                'unresolved': ('next_step',)}
STRUCT_FIELDS = {'id', 'title', 'entities', 'shared', 'transitions', 'solver_needs', 'threatens', 'omission'}
ENTITY_FIELDS = {'kind', 'host', 'state'}
TEST_REF = re.compile(r'^(?P<file>[^:]+)::(?P<cls>\w+)::(?P<meth>\w+)$')


def spec_ids():
    return set(re.findall(r'^  - id: ([A-Z][A-Z0-9-]*)\s*$', SPEC.read_text(), flags=re.M))


def validate(matrix, actors, register, modes, spec_node_ids, view_text=None):
    errors = []
    a_ids = {a['id'] for a in register['assumptions']}
    c_ids = {c['id'] for c in register['claims']}
    entries = matrix.get('omissions', [])
    ids = [e.get('id') for e in entries]
    if len(ids) != len(set(ids)):
        errors.append('duplicate omission IDs')
    covered = set()
    for e in entries:
        tag = f"omission {e.get('id')}"
        extra = set(e) - ENTRY_FIELDS
        if extra:
            errors.append(f'{tag}: unknown fields {sorted(extra)}')
        for f in ('id', 'title', 'issue_items', 'conclusions', 'status', 'finding', 'narrowed_claim'):
            if not e.get(f):
                errors.append(f'{tag}: missing {f}')
        covered |= set(e.get('issue_items') or [])
        st = e.get('status')
        if st not in STATUSES:
            errors.append(f'{tag}: status {st!r} is not one of {sorted(STATUSES)}')
        for f in STATUS_NEEDS.get(st, ()):
            if not e.get(f):
                errors.append(f'{tag}: status {st} needs {f}')
        for a in e.get('assumptions') or []:
            if a not in a_ids:
                errors.append(f'{tag}: assumption {a} is not in the register')
        for c in e.get('conclusions') or []:
            if c.startswith('AR-'):
                if c not in c_ids:
                    errors.append(f'{tag}: conclusion {c} is not a register claim')
            elif c not in spec_node_ids:
                errors.append(f'{tag}: conclusion {c} is not a register claim or a spec node')
        if st == 'implemented_tested':
            for p in [e.get('variant')] + list(e.get('results') or []):
                if p and not (MODEL_DIR / p).exists():
                    errors.append(f'{tag}: file {p} does not exist')
            for t in e.get('tests') or []:
                m = TEST_REF.match(t)
                if not m:
                    errors.append(f'{tag}: test {t!r} must look like file::Class::method')
                    continue
                f = MODEL_DIR / m['file']
                if not f.exists() or not re.search(rf'class {m["cls"]}\b[\s\S]*?def {m["meth"]}\(', f.read_text()):
                    errors.append(f'{tag}: test {t} not found')
        if e.get('design') and e['design'] not in {s['id'] for s in actors.get('structures', [])}:
            errors.append(f'{tag}: design {e["design"]} is not an actor structure')
    for item in sorted(REQUIRED_ITEMS - covered):
        errors.append(f'issue #9 item {item} has no omission entry')
    for item in sorted(covered - REQUIRED_ITEMS):
        errors.append(f'unknown issue item {item}')
    # variant selection record
    sel = matrix.get('variant_selection', [])
    chosen = {v['variant'] for v in sel if v.get('chosen')}
    used = {e['variant'] for e in entries if e.get('variant')}
    for v in sel:
        for f in ('variant', 'chosen', 'discriminates', 'reason'):
            if f not in v:
                errors.append(f"variant_selection {v.get('variant')}: missing {f}")
    for v in sorted(used - chosen):
        errors.append(f'variant {v} is used by an entry but not recorded as chosen in variant_selection')
    for v in sorted(chosen - used):
        errors.append(f'variant {v} is recorded as chosen but no entry uses it')
    errors += validate_actors(actors, modes, set(ids))
    if view_text is not None and view_text != render(matrix, actors):
        errors.append('results/omissions.md is stale: run python3 tools/omissions_tool.py render')
    return errors


def validate_actors(actors, modes, omission_ids):
    errors = []
    kinds = {k['id'] for k in modes['entity_kinds']}
    dims = {d['id']: d for d in modes['dimensions']}
    trans = {t['id'] for t in modes['transitions']}
    for s in actors.get('structures', []):
        tag = f"actor structure {s.get('id')}"
        extra = set(s) - STRUCT_FIELDS
        if extra:
            errors.append(f'{tag}: fields outside the contract {sorted(extra)}')
        ents = s.get('entities') or {}
        if not ents:
            errors.append(f'{tag}: no entities')
        for name, ent in ents.items():
            et = f'{tag} entity {name}'
            if set(ent) - ENTITY_FIELDS:
                errors.append(f'{et}: fields outside the contract {sorted(set(ent) - ENTITY_FIELDS)}')
            if ent.get('kind') not in kinds:
                errors.append(f"{et}: kind {ent.get('kind')!r} is not a contract entity kind")
            if ent.get('host') is not None and ent['host'] not in ents:
                errors.append(f"{et}: host {ent['host']} is not in the structure")
            for d, lvl in (ent.get('state') or {}).items():
                if d not in dims:
                    errors.append(f'{et}: {d} is not a contract dimension')
                    continue
                if lvl not in dims[d]['levels'] and lvl != 'unknown':
                    errors.append(f'{et}: {lvl!r} is not a level of {d}')
                if ent.get('kind') not in dims[d]['applies_to']:
                    errors.append(f"{et}: {d} does not apply to {ent.get('kind')}")
        for t in s.get('transitions') or []:
            if t not in trans:
                errors.append(f'{tag}: transition {t} is not in the contract')
        om = s.get('omission')
        if om is not None and om not in omission_ids:
            errors.append(f'{tag}: omission {om} is not in the matrix')
    return errors


def _cell(x):
    if isinstance(x, list):
        return ', '.join(str(v) for v in x)
    return ' '.join(str(x).split()) if x is not None else ''


def render(matrix, actors):
    L = ['# Omission matrix (issue #9)', '',
         '[[ai gen]] Generated from `omissions.yaml` by `python3 tools/omissions_tool.py render`; '
         '`make check` fails if this file is stale. The YAML is authoritative. Statuses: `implemented_tested` '
         '(a bounded variant exists and is tested), `excluded_scoped` (left out, with the claim scope narrowed), '
         '`unresolved` (not tested; the dependent claim is narrowed). No entry is empirical validation.', '',
         '## Summary', '',
         '| ID | omission | status | assumptions | conclusions it could change |',
         '|---|---|---|---|---|']
    for e in matrix['omissions']:
        L.append(f"| {e['id']} | {_cell(e['title'])} | {e['status']} | {_cell(e.get('assumptions') or [])} | "
                 f"{_cell(e['conclusions'])} |")
    L += ['', '## Findings and narrowed claims', '']
    for e in matrix['omissions']:
        L += [f"### {e['id']}: {_cell(e['title'])}", '',
              f"- **Status:** `{e['status']}`. Issue items: {_cell(e['issue_items'])}."]
        if e.get('variant'):
            L.append(f"- **Variant:** `{e['variant']}`; results {_cell(['`' + r + '`' for r in e['results']])}; "
                     f"tests {_cell(['`' + t + '`' for t in e['tests']])}.")
        if e.get('design'):
            L.append(f"- **Design note:** `variants/actor_structures.yaml` {e['design']}.")
        for f, name in (('reason', 'Reason'), ('scope', 'Scope'), ('next_step', 'Next step')):
            if e.get(f):
                L.append(f'- **{name}:** {_cell(e[f])}')
        L += [f"- **Finding:** {_cell(e['finding'])}", f"- **Narrowed claim:** {_cell(e['narrowed_claim'])}", '']
    L += ['## Variant selection', '', '| variant | chosen | discriminates | reason |', '|---|---|---|---|']
    for v in matrix['variant_selection']:
        L.append(f"| {_cell(v['variant'])} | {'yes' if v['chosen'] else 'no'} | {_cell(v['discriminates'])} | "
                 f"{_cell(v['reason'])} |")
    L += ['', '## Actor structures through the mode contract (design only)', '',
          '| ID | structure | entities (kind) | transitions | omission |', '|---|---|---|---|---|']
    for s in actors['structures']:
        ents = ', '.join(f"{n} ({e['kind']})" for n, e in s['entities'].items())
        L.append(f"| {s['id']} | {_cell(s['title'])} | {ents} | {_cell(s['transitions'])} | {s['omission'] or ''} |")
    return '\n'.join(L) + '\n'


def load_all():
    return (load_yaml(MATRIX), load_yaml(ACTORS), load_yaml(REGISTER), load_yaml(MODES), spec_ids())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['check', 'render'])
    a = ap.parse_args()
    matrix, actors, register, modes, nodes = load_all()
    if a.command == 'render':
        VIEW.write_text(render(matrix, actors))
        print(f'wrote {VIEW.relative_to(ROOT)}')
        return
    errors = validate(matrix, actors, register, modes, nodes, VIEW.read_text() if VIEW.exists() else '')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        sys.exit(1)
    counts = {s: sum(e['status'] == s for e in matrix['omissions']) for s in sorted(STATUSES)}
    print(f"omission matrix: {len(matrix['omissions'])} entries ("
          + ', '.join(f'{v} {k}' for k, v in counts.items()) + f"), {len(actors['structures'])} actor structures, no gaps")


if __name__ == '__main__':
    main()
