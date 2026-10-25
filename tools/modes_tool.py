#!/usr/bin/env python3
"""Check the AI development mode and transition contract (systems/modes.yaml); never infer that a mode definition is true.

    python3 tools/modes_tool.py check      # schema plus semantic rules (wired into make check)
    python3 tools/modes_tool.py report     # derived views for every trace step, unidentified transitions, adapter coverage
    python3 tools/modes_tool.py compare    # what a three-label state would erase (the #5 decision rule)

Modes are derived views over a factored state, evaluated with three-valued logic: True (every criterion
holds), False (some criterion fails on a known value), None (undetermined: no criterion fails, but a
needed dimension is unknown).

A dimension declared split_by_principal (effective_control) may hold either one level or a list of
{principal, scope, value} entries. Views and transition preconditions read the entry of the entity's host,
the principal that authorizes it; the other entries are recorded but never enter a view.
"""
import argparse
import importlib.util
import json
from itertools import combinations
from pathlib import Path
import sys

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'systems/modes.yaml'
SCHEMA = ROOT / 'schema/modes.schema.json'
UNKNOWN = 'unknown'
# Dimensions whose difference changes who decides or who holds resources: a three-label state must not merge them.
CONSEQUENTIAL = ('objective_selection', 'authorization', 'effective_control', 'custody_weights', 'custody_compute',
                 'custody_credentials', 'external_resources', 'enforceable_commitments', 'intervention_latency')
FORBIDDEN_MODE_KEYS = ('unit', 'units', 'owner', 'ownership', 'decision_authority', 'quantities')

_spec = importlib.util.spec_from_file_location('assumptions_tool', ROOT / 'tools/assumptions_tool.py')
assumptions_tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(assumptions_tool)
load_yaml = assumptions_tool.load_yaml


def by_id(items):
    return {x['id']: x for x in items}


def value_of(entity, dim):
    """The level a view or precondition reads: the single value, or the host's entry of a split value."""
    v = entity['state'].get(dim, UNKNOWN)
    if isinstance(v, list):
        return next((x['value'] for x in v if x['principal'] == entity.get('host')), UNKNOWN)
    return v


def view(mode, entity, entities, trace, dims):
    """Three-valued evaluation of one mode view for one trace entity."""
    if entity['kind'] not in mode['applies_to']:
        return False
    host = entity.get('host')
    need = mode['requires_host']
    if need is None and host is not None:
        return False
    if need is not None and (host is None or entities.get(host, {}).get('kind') != need):
        return False
    if mode.get('requires_scope_and_horizon') and not (trace.get('scope') and trace.get('horizon')):
        return False
    undetermined = False
    for dim, allowed in mode['criteria'].items():
        value = value_of(entity, dim)
        if value == UNKNOWN:
            undetermined = True
        elif value not in allowed:
            return False
    return None if undetermined else True


def classify(contract, trace, step):
    """entity id -> {mode id: True/False/None} for one step."""
    dims = by_id(contract['dimensions'])
    ents = step['entities']
    return {eid: {m['id']: view(m, e, ents, trace, dims) for m in contract['modes']} for eid, e in ents.items()}


def _schema_errors(contract):
    schema = json.loads(SCHEMA.read_text())
    v = jsonschema.Draft202012Validator(schema)
    return [f"schema: {'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
            for e in sorted(v.iter_errors(contract), key=lambda e: list(e.absolute_path))]


def _check_ids(contract, errors):
    for section in ('entity_kinds', 'dimensions', 'modes', 'stocks', 'accounting', 'transitions', 'adapters', 'traces', 'falsifiers'):
        ids = [x['id'] for x in contract[section]]
        for dup in sorted({i for i in ids if ids.count(i) > 1}):
            errors.append(f'{section}: duplicate id {dup}')


def _check_dimensions_and_modes(contract, errors):
    kinds = {k['id'] for k in contract['entity_kinds']}
    dims = by_id(contract['dimensions'])
    for d in contract['dimensions']:
        for k in d['applies_to']:
            if k not in kinds:
                errors.append(f'dimension {d["id"]}: unknown entity kind {k}')
    for m in contract['modes']:
        ident = m['id']
        for k in m['applies_to']:
            if k not in kinds:
                errors.append(f'{ident}: unknown entity kind {k}')
        if m['requires_host'] is not None and m['requires_host'] not in kinds:
            errors.append(f'{ident}: requires_host {m["requires_host"]} is not an entity kind')
        for dim, allowed in m['criteria'].items():
            if dim not in dims:
                errors.append(f'{ident}: criterion on unknown dimension {dim}')
                continue
            for a in allowed:
                if not isinstance(a, str) or a not in dims[dim]['levels']:
                    # Numbers never reach here as levels, so this also refuses an invented numeric threshold.
                    errors.append(f'{ident}: criterion {dim} uses {a!r}, which is not a declared level of {dim} '
                                  f'(criteria use categorical levels only; no numeric thresholds)')


def _check_transitions(contract, errors):
    dims = by_id(contract['dimensions'])
    trans = by_id(contract['transitions'])
    kinds = {k['id'] for k in contract['entity_kinds']}
    for t in contract['transitions']:
        ident = t['id']
        for d in t['changes']:
            if d not in dims:
                errors.append(f'{ident}: changes unknown dimension {d}')
        for d, levels in t['preconditions'].items():
            if d not in dims:
                errors.append(f'{ident}: precondition on unknown dimension {d}')
            else:
                # `unknown` may be listed explicitly: the transition is then allowed when the value is not known.
                errors += [f'{ident}: precondition {d} uses undeclared level {lv}' for lv in levels
                           if lv not in dims[d]['levels'] and lv != UNKNOWN]
        for a in t['agency']:
            if a not in kinds:
                errors.append(f'{ident}: agency names unknown entity kind {a}')
        if not t['reversible_by'] and not t.get('irreversible_reason'):
            errors.append(f'{ident}: names no reverse transition and gives no irreversible_reason')
        for r in t['reversible_by']:
            if r not in trans:
                errors.append(f'{ident}: reversible_by names unknown transition {r}')
            elif trans[r]['direction'] == t['direction']:
                errors.append(f'{ident}: reverse {r} points the same way ({t["direction"]})')
        if t['identified'] and t['feasibility']['status'] != 'observed_instances':
            errors.append(f'{ident}: identified is true but feasibility is {t["feasibility"]["status"]}')
    directions = {t['direction'] for t in contract['transitions']}
    if directions != {'toward_autonomy', 'toward_constraint'}:
        errors.append('transitions must exist in both directions')


def _check_accounting_and_adapters(contract, errors):
    dims = by_id(contract['dimensions'])
    acc = by_id(contract['accounting'])
    modes = by_id(contract['modes'])
    for q in contract['accounting']:
        for p in q['derived_from']:
            if p not in acc:
                errors.append(f'accounting {q["id"]}: derived_from unknown quantity {p}')

    def ancestors(q, seen=()):
        out = set()
        for p in acc.get(q, {}).get('derived_from', []):
            if p not in seen:
                out |= {p} | ancestors(p, seen + (q,))
        return out

    for ad in contract['adapters']:
        ident = ad['id']
        for q in ad['quantities']:
            if 'dimension' not in q and 'accounting' not in q:
                errors.append(f'{ident}: quantity {q["name"]!r} attaches to no dimension or accounting quantity')
            if 'dimension' in q and q['dimension'] not in dims:
                errors.append(f'{ident}: quantity {q["name"]!r} names unknown dimension {q["dimension"]}')
            if 'accounting' in q and q['accounting'] not in acc:
                errors.append(f'{ident}: quantity {q["name"]!r} names unknown accounting quantity {q["accounting"]}')
            _check_stock_flow(ident, q, acc, errors)
        for i in ad['inputs']:
            if i not in acc:
                errors.append(f'{ident}: input {i} is not an accounting quantity')
        for i in ad['inputs']:
            both = ancestors(i) & set(ad['inputs'])
            if both:
                errors.append(f'{ident}: input {i} is derived from {sorted(both)}, which is also an input (double counting)')
        if set(ad['modes']) != set(modes):
            errors.append(f'{ident}: must state coverage for every mode {sorted(modes)}')
        for m, entry in ad['modes'].items():
            bad = [k for k in entry if k in FORBIDDEN_MODE_KEYS]
            if bad:
                errors.append(f'{ident}: mode {m} redefines {bad}; a mode label must not change units, ownership or decision authority')
            extra = set(entry) - {'coverage', 'reason'} - set(bad)
            if extra:
                errors.append(f'{ident}: mode {m} has unknown fields {sorted(extra)}')


def _check_stock_flow(ident, q, acc, errors):
    """Issue #39: a declared kind matches the ledger it is booked to; an output rate leads from a stock to a flow derived from it."""
    where = f'{ident}: quantity {q["name"]!r}'
    led = acc.get(q.get('accounting'))
    if 'kind' in q:
        if 'accounting' not in q:
            errors.append(f'{where} declares kind {q["kind"]} but is booked to no accounting quantity')
        elif led is not None and led['kind'] != q['kind']:
            errors.append(f'{where} is a {q["kind"]} booked to {q["accounting"]}, a {led["kind"]}; '
                          f'book a stock to a stock and give its output_rate to the flow (#39)')
    rate = q.get('output_rate')
    if rate is None:
        return
    if q.get('kind') != 'stock' or (led is not None and led['kind'] != 'stock'):
        errors.append(f'{where} has an output_rate, so it must be a stock booked to a stock accounting quantity')
    if not str(rate['unit']).startswith('per '):
        errors.append(f'{where}: output_rate unit {rate["unit"]!r} is not per unit of time ("per year")')
    out = acc.get(rate['accounting'])
    if out is None:
        errors.append(f'{where}: output_rate names unknown accounting quantity {rate["accounting"]}')
    elif out['kind'] != 'flow':
        errors.append(f'{where}: output_rate leads to {rate["accounting"]}, a {out["kind"]}, not a flow')
    elif q.get('accounting') not in out['derived_from']:
        errors.append(f'{where}: output_rate leads to {rate["accounting"]}, which is not derived from {q.get("accounting")}')


def _check_solver_mapping(contract, errors, register=None, params=None):
    sm = contract['solver_mapping']
    register = register if register is not None else load_yaml(ROOT / sm['register'])
    params = params if params is not None else assumptions_tool.load_params()
    known = {a['id'] for a in register['assumptions']}
    dims = {d['id'] for d in contract['dimensions']}
    trans = {t['id'] for t in contract['transitions']}
    if set(sm['dimensions']) != dims:
        errors.append(f'solver_mapping: dimensions missing {sorted(dims - set(sm["dimensions"]))}, '
                      f'unknown {sorted(set(sm["dimensions"]) - dims)}')
    mapped_t, unsupported = set(sm['transitions']), set(sm['unsupported_in_solver'])
    if mapped_t & unsupported or (mapped_t | unsupported) != trans:
        errors.append(f'solver_mapping: every transition must be mapped or listed unsupported, exactly once '
                      f'(missing {sorted(trans - mapped_t - unsupported)}, both {sorted(mapped_t & unsupported)}, '
                      f'unknown {sorted((mapped_t | unsupported) - trans)})')
    used = set()
    for where, entries in (('dimensions', sm['dimensions']), ('transitions', sm['transitions'])):
        for key, e in entries.items():
            for p in e['params']:
                if p not in params:
                    errors.append(f'solver_mapping {where}.{key}: {p} is not in PARAMS')
            for a in e['assumptions']:
                used.add(a)
                if a not in known:
                    errors.append(f'solver_mapping {where}.{key}: unknown assumption {a}')
    for a in sm['outcomes_and_rivals']['assumptions']:
        used.add(a)
        if a not in known:
            errors.append(f'solver_mapping outcomes_and_rivals: unknown assumption {a}')
    for x in sm['excluded']:
        used.add(x['assumption'])
        if x['assumption'] not in known:
            errors.append(f'solver_mapping excluded: unknown assumption {x["assumption"]}')
    for a in sorted(known - used):
        errors.append(f'solver_mapping: register assumption {a} is not mapped to a dimension or transition and not excluded')


def _check_split(where, eid, entity, dim, entries, d, ents, errors):
    """A value split by principal: allowed dimension, a host whose entry the views read, known principals, declared levels."""
    if not d.get('split_by_principal'):
        errors.append(f'{where}: {eid} {dim} is split by principal, but {dim} is not declared split_by_principal')
        return
    principals = [x['principal'] for x in entries]
    host = entity.get('host')
    if host is None:
        errors.append(f'{where}: {eid} {dim} is split by principal but {eid} has no host whose entry the views read')
    elif host not in principals:
        errors.append(f'{where}: {eid} {dim} is split by principal but has no entry for its host {host}')
    for p in sorted({p for p in principals if principals.count(p) > 1}):
        errors.append(f'{where}: {eid} {dim} has more than one entry for principal {p}')
    for x in entries:
        if x['principal'] not in ents:
            errors.append(f'{where}: {eid} {dim} names principal {x["principal"]}, which is not in the step')
        if x['value'] != UNKNOWN and x['value'] not in d['levels']:
            errors.append(f'{where}: {eid} {dim} = {x["value"]!r} for {x["principal"]} is not a declared level')


def _check_traces(contract, errors):
    dims = by_id(contract['dimensions'])
    kinds = {k['id'] for k in contract['entity_kinds']}
    trans = by_id(contract['transitions'])
    acc = by_id(contract['accounting'])
    stock_ids = {s['id'] for s in contract['stocks']}
    modes = {m['id'] for m in contract['modes']}
    for tr in contract['traces']:
        prev = None
        for n, step in enumerate(tr['steps']):
            where = f'{tr["id"]} step {n + 1}'
            ents = step['entities']
            for eid, e in ents.items():
                if e['kind'] not in kinds:
                    errors.append(f'{where}: {eid} has unknown kind {e["kind"]}')
                    continue
                if e['host'] is not None and e['host'] not in ents:
                    errors.append(f'{where}: {eid} is hosted by {e["host"]}, which is not in the step')
                needed = {d for d, x in dims.items() if e['kind'] in x['applies_to']}
                for d in sorted(needed - set(e['state'])):
                    errors.append(f'{where}: {eid} has no value for {d} (write unknown if it is unknown)')
                for d, v in e['state'].items():
                    if d not in needed:
                        errors.append(f'{where}: {eid} sets {d}, which does not apply to a {e["kind"]}')
                    elif isinstance(v, list):
                        _check_split(where, eid, e, d, v, dims[d], ents, errors)
                    elif v != UNKNOWN and v not in dims[d]['levels']:
                        errors.append(f'{where}: {eid} {d} = {v!r} is not a declared level')
                for s in e.get('stocks', {}):
                    if s not in stock_ids:
                        errors.append(f'{where}: {eid} has unknown stock {s}')
            # resources: one ledger, shares of one instance never sum above 1
            for rid, r in step['resources'].items():
                if r['accounting'] not in acc:
                    errors.append(f'{where}: resource {rid} names unknown accounting quantity {r["accounting"]}')
                elif acc[r['accounting']]['kind'] != 'stock':
                    errors.append(f'{where}: resource {rid} is held by shares, so it is a stock; {r["accounting"]} is a '
                                  f'{acc[r["accounting"]]["kind"]} (#39)')
                for h in r['holders']:
                    if h not in ents:
                        errors.append(f'{where}: resource {rid} held by {h}, which is not in the step')
                if sum(r['holders'].values()) > 1 + 1e-9:
                    errors.append(f'{where}: resource {rid} shares sum to {sum(r["holders"].values()):g} > 1 (double counting)')
            for eid, e in ents.items():
                for a in e.get('stocks', {}).get('assets', []):
                    if a in step['resources'] and eid not in step['resources'][a]['holders']:
                        errors.append(f'{where}: {eid} lists asset {a} but holds no share of it')
            # expected views
            got = classify(contract, tr, step)
            for eid, res in got.items():
                held = sorted(m for m, v in res.items() if v is True)
                undet = sorted(m for m, v in res.items() if v is None)
                exp = sorted(step['expected_views'].get(eid, []))
                exp_u = sorted(step.get('undetermined_views', {}).get(eid, []))
                if held != exp:
                    errors.append(f'{where}: {eid} derives views {held} but the trace expects {exp}')
                if undet != exp_u:
                    errors.append(f'{where}: {eid} has undetermined views {undet} but the trace expects {exp_u}')
            for eid in list(step['expected_views']) + list(step.get('undetermined_views', {})):
                if eid not in ents:
                    errors.append(f'{where}: expected views for {eid}, which is not in the step')
                for m in step['expected_views'].get(eid, []) + step.get('undetermined_views', {}).get(eid, []):
                    if m not in modes:
                        errors.append(f'{where}: unknown mode {m}')
            # transitions between steps: no relabelling, no unexplained change, no silent stock reset
            applied = {}
            for a in step.get('transitions', []):
                if a['type'] not in trans:
                    errors.append(f'{where}: unknown transition {a["type"]}')
                    continue
                if a['entity'] not in ents:
                    errors.append(f'{where}: transition {a["type"]} on {a["entity"]}, which is not in the step')
                    continue
                applied.setdefault(a['entity'], []).append(trans[a['type']])
            if prev is None:
                if applied:
                    errors.append(f'{where}: the first step cannot apply a transition')
                prev = (step, got)
                continue
            pstep, pgot = prev
            for eid, e in ents.items():
                before = pstep['entities'].get(eid)
                ts = applied.get(eid, [])
                if before is None:
                    continue
                changed = {d for d in set(e['state']) | set(before['state']) if e['state'].get(d) != before['state'].get(d)}
                allowed = set().union(*[set(t['changes']) for t in ts]) if ts else set()
                for d in sorted(changed - allowed):
                    errors.append(f'{where}: {eid} {d} changed from {before["state"].get(d)} to {e["state"].get(d)} '
                                  f'without a transition that declares it')
                for t in ts:
                    if not changed & set(t['changes']):
                        errors.append(f'{where}: {eid} applies {t["id"]} but none of its dimensions changed (relabelling)')
                    for d, levels in t['preconditions'].items():
                        if value_of(before, d) not in levels:
                            errors.append(f'{where}: {eid} applies {t["id"]} but {d} was {value_of(before, d)}, not in {levels}')
                views_before = {m for m, v in pgot.get(eid, {}).items() if v}
                views_after = {m for m, v in got.get(eid, {}).items() if v}
                if views_before != views_after and not ts:
                    errors.append(f'{where}: {eid} changes mode view with no transition (relabelling)')
                if e['kind'] != before['kind']:
                    errors.append(f'{where}: {eid} changed kind; a new entity needs a new id')
                declared = {c['stock'] for c in step.get('stock_changes', []) if c['entity'] == eid}
                for s in stock_ids:
                    if e.get('stocks', {}).get(s) != before.get('stocks', {}).get(s) and s not in declared:
                        errors.append(f'{where}: {eid} stock {s} changed without a declared cause (stocks carry over across modes)')
            for c in step.get('stock_changes', []):
                if c['entity'] not in applied:
                    errors.append(f'{where}: stock change on {c["entity"]} with no transition applied to it')
                if c['stock'] not in stock_ids:
                    errors.append(f'{where}: unknown stock {c["stock"]}')
            prev = (step, got)


def _check_evidence(contract, errors):
    targets = {m['id'] for m in contract['modes']} | {t['id'] for t in contract['transitions']}
    for t in sorted(targets - set(contract['evidence_requirements'])):
        errors.append(f'evidence_requirements: none stated for {t}')
    for t in sorted(set(contract['evidence_requirements']) - targets):
        errors.append(f'evidence_requirements: unknown target {t}')
    for f in contract['falsifiers']:
        for t in f['targets']:
            if t != 'contract' and t not in targets:
                errors.append(f'{f["id"]}: unknown target {t}')
    falsified = {t for f in contract['falsifiers'] for t in f['targets']}
    for m in contract['modes']:
        if m['id'] not in falsified:
            errors.append(f'{m["id"]}: no falsifier targets this mode')


def validate(contract, register=None, params=None):
    errors = _schema_errors(contract)
    if errors:
        return errors
    _check_ids(contract, errors)
    _check_dimensions_and_modes(contract, errors)
    _check_transitions(contract, errors)
    _check_accounting_and_adapters(contract, errors)
    _check_solver_mapping(contract, errors, register, params)
    _check_traces(contract, errors)
    _check_evidence(contract, errors)
    return errors


def label_collisions(contract):
    """Pairs of trace states with the same three-mode label but different consequential dimensions."""
    rows = []
    for tr in contract['traces']:
        for n, step in enumerate(tr['steps']):
            got = classify(contract, tr, step)
            for eid, e in step['entities'].items():
                if not any(e['kind'] in m['applies_to'] for m in contract['modes']):
                    continue
                label = tuple(sorted(m for m, v in got[eid].items() if v))
                rows.append((label, f'{tr["id"]}#{n + 1}:{eid}', e['state']))
    out = []
    for (l1, a, s1), (l2, b, s2) in combinations(rows, 2):
        if l1 == l2:
            diff = [d for d in CONSEQUENTIAL if s1.get(d) != s2.get(d)]
            if diff:
                out.append((l1, a, b, diff))
    return out


def report(contract):
    lines = ['# Mode contract report (generated by tools/modes_tool.py report; status: proposed, not validated)', '',
             '## Derived views per trace step', '', '| trace | step | entity | views | undetermined |', '|---|---|---|---|---|']
    for tr in contract['traces']:
        for n, step in enumerate(tr['steps']):
            for eid, res in classify(contract, tr, step).items():
                held = ', '.join(m for m, v in res.items() if v is True) or 'none'
                und = ', '.join(m for m, v in res.items() if v is None) or ''
                lines.append(f'| {tr["id"]} | {n + 1} {step["label"]} | {eid} | {held} | {und} |')
    lines += ['', '## Transitions', '', '| id | direction | feasibility | identified | reversed by |', '|---|---|---|---|---|']
    for t in contract['transitions']:
        lines.append(f'| {t["id"]} | {t["direction"]} | {t["feasibility"]["status"]} | {t["identified"]} | '
                     f'{", ".join(t["reversible_by"]) or t.get("irreversible_reason", "")} |')
    lines += ['', '## Adapter coverage', '', '| adapter | ' + ' | '.join(m['id'] for m in contract['modes']) + ' |',
              '|---|' + '---|' * len(contract['modes'])]
    for ad in contract['adapters']:
        lines.append(f'| {ad["id"]} | ' + ' | '.join(ad['modes'][m['id']]['coverage'] for m in contract['modes']) + ' |')
    return '\n'.join(lines)


def compare(contract):
    col = label_collisions(contract)
    lines = ['# Three-label state versus factored state', '',
             f'{len(col)} pairs of trace states share a three-mode label but differ in who decides or who holds resources.', '']
    for label, a, b, diff in col:
        lines.append(f'- [{", ".join(label) or "no mode"}] {a} vs {b}: {", ".join(diff)}')
    lines += ['', 'Decision: keep the factored state and derive the modes as views (falsifier F-LABEL-SUFFICES).'
              if col else 'No collision: the minimal three-mode state suffices for these traces (F-LABEL-SUFFICES fires).']
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['check', 'report', 'compare'])
    a = ap.parse_args()
    contract = load_yaml(CONTRACT)
    errors = validate(contract)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        sys.exit(1)
    if a.command == 'check':
        steps = sum(len(t['steps']) for t in contract['traces'])
        print(f'mode contract: {len(contract["modes"])} proposed modes, {len(contract["dimensions"])} dimensions, '
              f'{len(contract["transitions"])} transitions, {len(contract["traces"])} traces ({steps} steps), '
              f'{len(contract["adapters"])} adapters; no gaps; nothing validated empirically')
    elif a.command == 'report':
        print(report(contract))
    else:
        print(compare(contract))


if __name__ == '__main__':
    main()
