#!/usr/bin/env python3
"""Keep the off-Earth model's assumption register honest; never infer that an assumption is true.

    python3 tools/assumptions_tool.py check    # fail on any gap (wired into make check)
    python3 tools/assumptions_tool.py report   # ranked list of pact-favouring assumptions that lack an ablation

The register is model/assumptions.yaml. PARAMS is read from equilibrium_model.py with ast, so numpy is not needed.

Issue #8 additions, also checked:
  - every PARAMS entry and every other influential input has a role (observed measurement, source-model
    assumption, project assumption, policy choice or derived quantity); stakeholder validation is recorded apart
    from empirical support and never counts as it;
  - claims and literature-based assumptions link to dated evidence records (evidence/records.yaml) with an exact
    locator, and a record may only be cited for the uses its kind and reading allow;
  - a claim that reports an outcome share carries an outcome label (sampling measure, structural assumptions,
    horizon, predicate, Wilson interval, uncertainty types);
  - a PARAMS entry added after the admission rule took effect needs an admission record.
"""
import argparse
import ast
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / 'research_notes/Off Earth industry as misalignment control/model'
REGISTER = MODEL_DIR / 'assumptions.yaml'
SOLVER = MODEL_DIR / 'equilibrium_model.py'

SOURCES = {'cole_answer', 'agent_default', 'literature'}
FAVOURS = {'yes', 'no', 'mixed', 'unclear'}
ABLATION = {'run', 'partial', 'not_run'}
SURVIVED = {'yes', 'no', 'partly', 'pending', 'n/a'}
STATUS = {'implemented', 'verified', 'human_validated'}
DEPENDENCE = {'high': 3, 'medium': 2, 'low': 1}
FIELDS = {'id', 'statement', 'encoded_by', 'source', 'favours_pact', 'ablation', 'claims', 'dependence', 'status'}
OPTIONAL = {'why_favours', 'note', 'priority', 'validated_by', 'evidence'}
ROLES = {'observed_measurement', 'source_model_assumption', 'project_assumption', 'policy_choice', 'derived'}
ROLE_FIELDS = {'role', 'note', 'empirical_support', 'source_model', 'derived_from', 'stakeholder_validation', 'admission'}
ADMISSION_BASES = {'observable', 'external_model_mapping', 'consequential_omission'}
ADMISSION_FIELDS = ('basis', 'evidence_path', 'falsifier', 'decision_impact')
CLAIM_FIELDS = {'id', 'text', 'where', 'outcome_label'}
SHARE_CLAIM = re.compile(r'\d+(\.\d+)?\s*%|\b\d+ of \d+\b')

_ev_spec = importlib.util.spec_from_file_location('evidence_tool', ROOT / 'tools/evidence_tool.py')
evidence_tool = importlib.util.module_from_spec(_ev_spec)
_ev_spec.loader.exec_module(evidence_tool)


def load_yaml(path):
    try:
        import yaml
        return yaml.safe_load(path.read_text())
    except ImportError:    # make check already needs Ruby, whose standard library parses YAML
        out = subprocess.run(['ruby', '-ryaml', '-rjson', '-e', 'puts JSON.dump(YAML.safe_load(File.read(ARGV[0])))', str(path)],
                             check=True, capture_output=True, text=True)
        return json.loads(out.stdout)


def _number(node):
    """A baseline is a literal or plain arithmetic on literals (f_fab is 1 / 30)."""
    if not all(isinstance(n, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.operator, ast.unaryop))
               for n in ast.walk(node)):
        raise SystemExit(f'PARAMS baseline on line {node.lineno} is not plain arithmetic')
    return eval(compile(ast.Expression(node), '<PARAMS>', 'eval'), {'__builtins__': {}})


def load_params(path=SOLVER):
    """PARAMS name -> baseline value, read from the source without importing the solver."""
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if getattr(target, 'id', None) == 'PARAMS':
                return {e.elts[0].value: _number(e.elts[1].elts[0]) for e in node.value.args[0].elts}
    raise SystemExit(f'PARAMS not found in {path}')


def validate(reg, params, records=None):
    errors = []
    claims = {c['id'] for c in reg.get('claims', [])}
    ids = [a.get('id') for a in reg.get('assumptions', [])]
    known = set(ids)
    for ident in {i for i in ids if ids.count(i) > 1}:
        errors.append(f'duplicate assumption ID {ident}')
    for a in reg.get('assumptions', []):
        ident = a.get('id', '?')
        missing, extra = FIELDS - set(a), set(a) - FIELDS - OPTIONAL
        if missing:
            errors.append(f'{ident}: missing fields {sorted(missing)}')
            continue
        if extra:
            errors.append(f'{ident}: unknown fields {sorted(extra)}')
        src, abl = a['source'], a['ablation']
        if src.get('kind') not in SOURCES or not str(src.get('where', '')).strip():
            errors.append(f'{ident}: source needs kind in {sorted(SOURCES)} and a non-empty where')
        if a['favours_pact'] not in FAVOURS:
            errors.append(f'{ident}: favours_pact must be one of {sorted(FAVOURS)}')
        if a['dependence'] not in DEPENDENCE:
            errors.append(f'{ident}: dependence must be one of {sorted(DEPENDENCE)}')
        if abl.get('status') not in ABLATION or abl.get('survived') not in SURVIVED:
            errors.append(f'{ident}: ablation needs status in {sorted(ABLATION)} and survived in {sorted(SURVIVED)}')
        elif abl['status'] != 'not_run' and not str(abl.get('where', '')).strip():
            errors.append(f'{ident}: an ablation marked {abl["status"]} must say where it was run')
        elif abl['status'] == 'not_run' and abl['survived'] != 'n/a':
            errors.append(f'{ident}: an ablation that was not run cannot have survived = {abl["survived"]}')
        if src.get('kind') == 'cole_answer' and a['favours_pact'] == 'yes' and abl.get('status') not in ('run', 'partial'):
            errors.append(f'{ident}: Cole answer that favours the pact has no recorded ablation')
        if a['status'] not in STATUS:
            errors.append(f'{ident}: status must be one of {sorted(STATUS)}')
        elif a['status'] == 'human_validated' and a.get('validated_by') != 'Cole':
            errors.append(f'{ident}: human_validated is set only by Cole (validated_by: Cole)')
        for c in a['claims']:
            if c not in claims:
                errors.append(f'{ident}: unknown claim {c}')
        for e in a['encoded_by']:
            if 'param' in e:
                p = e['param']
                if p not in params:
                    errors.append(f'{ident}: encoded_by names {p}, which is not in PARAMS')
                elif 'value' in e and not isinstance(e['value'], (int, float)):
                    errors.append(f'{ident}: {p} value {e["value"]!r} is not a number (YAML reads 1.0e9 as text; write 1000000000.0)')
                elif 'value' in e and not e.get('variant') and float(e['value']) != float(params[p]):
                    errors.append(f'{ident}: {p} is recorded as {e["value"]} but its PARAMS baseline is {params[p]}')
            elif not str(e.get('structure', '')).strip():
                errors.append(f'{ident}: each encoded_by item needs a param or a structure')
    pmap = reg.get('parameters', {})
    for p in params:
        if p not in pmap:
            errors.append(f'PARAMS entry {p} has no register entry')
    for p, refs in pmap.items():
        if p not in params:
            errors.append(f'register parameter {p} is not in PARAMS')
        if not refs:
            errors.append(f'register parameter {p} names no assumption')
        for r in refs or []:
            if r not in known:
                errors.append(f'register parameter {p} names unknown assumption {r}')
    errors += validate_evidence(reg, params, records, known)
    return errors


def _links(value, use):
    """Normalise a role's evidence field ({record, locator} or a list of them) to claim links with a fixed use."""
    items = value if isinstance(value, list) else [value]
    return [dict(i, use=use) if isinstance(i, dict) else {'record': i, 'use': use} for i in items]


def validate_evidence(reg, params, records=None, known=None):
    """Issue #8: roles, evidence links, outcome labels and the parameter-admission rule."""
    errors = []
    recs = records if records is not None else evidence_tool.records_by_id()
    known = known if known is not None else {a['id'] for a in reg.get('assumptions', [])}
    for c in reg.get('claims', []):
        where = f'claim {c.get("id", "?")}'
        extra = set(c) - CLAIM_FIELDS
        if extra:
            errors.append(f'{where}: unknown fields {sorted(extra)}')
        if 'outcome_label' in c:
            errors += evidence_tool.validate_outcome_label(c['outcome_label'], where, known)
        elif SHARE_CLAIM.search(c.get('text', '')):
            errors.append(f'{where}: reports an outcome share but has no outcome_label')
    for a in reg.get('assumptions', []):
        ident = a.get('id', '?')
        links = a.get('evidence', [])
        errors += evidence_tool.validate_links(links, recs, ident)
        if a.get('source', {}).get('kind') == 'literature' and not links:
            errors.append(f'{ident}: a literature source needs an evidence link (record and locator), not only a citation')
    roles = reg.get('parameter_roles')
    other = reg.get('other_inputs', {})
    if roles is None:
        return errors + ['parameter_roles is missing']
    for p in params:
        if p not in roles:
            errors.append(f'PARAMS entry {p} has no role')
    for p in roles:
        if p not in params:
            errors.append(f'parameter_roles names {p}, which is not in PARAMS')
    for p in other:
        if p in params:
            errors.append(f'other_inputs repeats PARAMS entry {p}')
    for name, r in list(roles.items()) + list(other.items()):
        where = f'input {name}'
        extra = set(r) - ROLE_FIELDS
        if extra:
            errors.append(f'{where}: unknown fields {sorted(extra)}')
        role = r.get('role')
        if role not in ROLES:
            errors.append(f'{where}: role must be one of {sorted(ROLES)}')
            continue
        if role == 'observed_measurement':
            if not r.get('empirical_support'):
                why = ' (stakeholder validation is not empirical support)' if r.get('stakeholder_validation') else ''
                errors.append(f'{where}: an observed measurement needs empirical_support records{why}')
            else:
                errors += evidence_tool.validate_links(_links(r['empirical_support'], 'empirical_support'), recs, where)
        elif r.get('empirical_support'):
            errors += evidence_tool.validate_links(_links(r['empirical_support'], 'empirical_support'), recs, where)
        if role == 'source_model_assumption':
            if not r.get('source_model'):
                errors.append(f'{where}: a source-model assumption names its source_model record')
            else:
                errors += evidence_tool.validate_links(_links(r['source_model'], 'source_model_basis'), recs, where)
        if role == 'derived':
            deps = r.get('derived_from') or []
            if not deps:
                errors.append(f'{where}: a derived quantity lists derived_from')
            for d in deps:
                if d not in params and d not in other:
                    errors.append(f'{where}: derived_from names unknown input {d}')
        if 'stakeholder_validation' in r and not str(r['stakeholder_validation']).strip():
            errors.append(f'{where}: empty stakeholder_validation')
    rule = reg.get('admission_rule')
    if rule is None:
        return errors + ['admission_rule is missing']
    grand = set(rule.get('grandfathered', []))
    for p in sorted(grand - set(params)):
        errors.append(f'admission_rule grandfathers {p}, which is not in PARAMS')
    for p in params:
        if p in grand:
            continue
        adm = (roles.get(p) or {}).get('admission')
        if not adm:
            errors.append(f'PARAMS entry {p} was added after {rule.get("effective")} and has no admission record '
                          f'({", ".join(ADMISSION_FIELDS)})')
            continue
        if adm.get('basis') not in ADMISSION_BASES:
            errors.append(f'{p}: admission basis must be one of {sorted(ADMISSION_BASES)}')
        for f in ADMISSION_FIELDS[1:]:
            if not str(adm.get(f, '')).strip():
                errors.append(f'{p}: admission needs a non-empty {f}')
    return errors


def ranked(reg):
    """Pact-favouring assumptions without a full ablation, most load-bearing first."""
    rows = [a for a in reg['assumptions'] if a['favours_pact'] == 'yes' and a['ablation']['status'] != 'run']
    key = lambda a: (a['ablation']['status'] != 'not_run', -DEPENDENCE[a['dependence']], -len(a['claims']), a['id'])
    return sorted(rows, key=key)


def report(reg):
    lines = ['# Pact-favouring assumptions without a full ablation (auto-generated by tools/assumptions_tool.py report)', '',
             'Order: never ablated first, then partly ablated; within each, by how much the headline claims depend on it '
             '(dependence, then number of claims). This ranks what the register says; it is not a new result.', '',
             '| rank | id | ablation | dependence | claims | source | statement |', '|---|---|---|---|---|---|---|']
    for i, a in enumerate(ranked(reg), 1):
        lines.append(f"| {i} | {a['id']} | {a['ablation']['status']} | {a['dependence']} | {', '.join(a['claims'])} | "
                     f"{a['source']['kind']} | {a['statement'].strip()} |")
    flagged = [a for a in reg['assumptions'] if a.get('priority')]
    if flagged:
        lines += ['', '## Priority flags (whatever their direction)', '', '| id | favours pact | ablation | priority |', '|---|---|---|---|']
        lines += [f"| {a['id']} | {a['favours_pact']} | {a['ablation']['status']} | {a['priority']} |" for a in flagged]
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['check', 'report'])
    a = ap.parse_args()
    reg, params = load_yaml(REGISTER), load_params()
    errors = validate(reg, params)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        sys.exit(1)
    if a.command == 'check':
        n = len(reg['assumptions'])
        roles = [r['role'] for r in reg['parameter_roles'].values()] + [r['role'] for r in reg.get('other_inputs', {}).values()]
        counts = ', '.join(f'{roles.count(r)} {r}' for r in sorted(ROLES) if roles.count(r))
        print(f'assumption register: {n} assumptions, {len(params)} PARAMS entries covered, no gaps; '
              f'input roles: {counts}')
    else:
        print(report(reg))


if __name__ == '__main__':
    main()
