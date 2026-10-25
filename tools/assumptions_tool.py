#!/usr/bin/env python3
"""Keep the off-Earth model's assumption register honest; never infer that an assumption is true.

    python3 tools/assumptions_tool.py check    # fail on any gap (wired into make check)
    python3 tools/assumptions_tool.py report   # ranked list of pact-favouring assumptions that lack an ablation

The register is model/assumptions.yaml. PARAMS is read from equilibrium_model.py with ast, so numpy is not needed.
"""
import argparse
import ast
import json
from pathlib import Path
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
OPTIONAL = {'why_favours', 'note', 'priority', 'validated_by'}


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


def validate(reg, params):
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
        print(f'assumption register: {n} assumptions, {len(params)} PARAMS entries covered, no gaps')
    else:
        print(report(reg))


if __name__ == '__main__':
    main()
