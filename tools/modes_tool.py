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
# The only dimensions a milestone event may set (#47); authority and resource dimensions move only by transitions.
CAPABILITY = ('strategic_capability', 'rd_capability', 'cyber_capability')

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
    """Issues #39 and #61: every quantity declares a kind; one booked to a ledger has the ledger's kind, is a ratio on it, or
    is recorded ambiguous with a source locator; an output rate leads from a stock to a flow derived from it."""
    where = f'{ident}: quantity {q["name"]!r}'
    led = acc.get(q.get('accounting'))
    kind = q['kind']
    if kind == 'ambiguous':
        amb = q.get('kind_ambiguity')
        if amb is None:
            errors.append(f'{where} is ambiguous but gives no kind_ambiguity (candidates and source locator) (#61)')
        elif led is not None and led['kind'] not in amb['candidates']:
            errors.append(f'{where} is ambiguous between {amb["candidates"]} but is booked to {q["accounting"]}, a {led["kind"]}')
    elif 'kind_ambiguity' in q:
        errors.append(f'{where} declares kind {kind} and also kind_ambiguity; drop one (#61)')
    if 'accounting' not in q:
        if kind == 'ratio':
            errors.append(f'{where} is a ratio but names no accounting quantity it applies to (#61)')
    elif kind == 'event':
        errors.append(f'{where} is an event; an event is never booked to an accounting quantity (#61)')
    elif led is not None and kind not in ('ratio', 'ambiguous') and led['kind'] != kind:
        errors.append(f'{where} is a {kind} booked to {q["accounting"]}, a {led["kind"]}; '
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


def _ancestors(acc, q, seen=()):
    out = set()
    for p in acc.get(q, {}).get('derived_from', []):
        if p not in seen:
            out |= {p} | _ancestors(acc, p, seen + (q,))
    return out


def _check_loops_and_couplings(contract, errors):
    """Issue #35: one owner per feedback loop; a coupling cannot close a loop twice (epoch-gate/INTERFACES.md)."""
    acc = by_id(contract['accounting'])
    loops = by_id(contract['feedback_loops'])
    adapters = by_id(contract['adapters'])
    for lp in contract['feedback_loops']:
        for a in lp['carries']:
            if a not in acc:
                errors.append(f'feedback loop {lp["id"]}: carries unknown accounting quantity {a}')
    owners = {lid: [] for lid in loops}
    for ad in contract['adapters']:
        for lid, entry in ad.get('feedback_loops', {}).items():
            if lid not in loops:
                errors.append(f'{ad["id"]}: feedback_loops names unknown loop {lid}')
            elif entry['role'] == 'owner':
                owners[lid].append(ad['id'])
    for lid, who in owners.items():
        if len(who) != 1:
            errors.append(f'feedback loop {lid}: must have exactly one owning adapter (has {who or "none"})')
    owner = {lid: who[0] for lid, who in owners.items() if len(who) == 1}
    carried_by = {}
    for lp in contract['feedback_loops']:
        for a in lp['carries']:
            carried_by.setdefault(a, []).append(lp['id'])
    for xc in contract['couplings']:
        where = f'coupling {xc["id"]}'
        coupled = [a for a in xc['adapters'] if a in adapters]
        for a in xc['adapters']:
            if a not in adapters:
                errors.append(f'{where}: unknown adapter {a}')
            elif set(adapters[a].get('feedback_loops', {})) != set(loops):
                errors.append(f'{where}: {a} must state a role for every feedback loop {sorted(loops)}')
        quants = {a: {q['name']: q for q in adapters[a]['quantities']} for a in coupled}
        passed, targets = set(), set()
        for p in xc['passes']:
            src, dst, led = p['from'], p['to'], p['accounting']
            pw = f'{where}: pass {src["adapter"]} {src["quantity"]!r} -> {dst["adapter"]}'
            qs = quants.get(src['adapter'], {}).get(src['quantity'])
            qd = quants.get(dst['adapter'], {}).get(dst['quantity'])
            if qs is None or qd is None:
                errors.append(f'{pw}: both ends must be quantities of coupled adapters')
                continue
            if src['adapter'] == dst['adapter']:
                errors.append(f'{pw}: a pass joins two different adapters')
            if qs.get('accounting') != led or qd.get('accounting') != led:
                errors.append(f'{pw}: both ends must be booked to {led} (they are {qs.get("accounting")}, {qd.get("accounting")})')
            if 'ambiguous' in (qs['kind'], qd['kind']) or qs['kind'] != qd['kind']:
                errors.append(f'{pw}: kinds must be resolved and equal ({qs["kind"]}, {qd["kind"]})')
            if 'event' in (qs['kind'], qd['kind']) or led in ('capability', 'efficiency_level'):
                errors.append(f'{pw}: {led} never crosses a coupling (rival capability mappings and one software-efficiency '
                              f'base; INTERFACES.md items 2 and 4)')
            if led not in adapters[dst['adapter']]['inputs']:
                errors.append(f'{pw}: {led} is not an input of {dst["adapter"]}')
            if (dst['adapter'], led) in targets:
                errors.append(f'{pw}: {dst["adapter"]} already receives {led} from another pass')
            targets.add((dst['adapter'], led))
            passed.add(led)
            for lid in carried_by.get(led, []):
                if owner.get(lid) != src['adapter']:
                    errors.append(f'{pw}: {led} carries loop {lid}, owned by {owner.get(lid)}, not by the source')
            # INTERFACES.md item 5: compute the source already turns into a derived quantity on a loop it owns is used up.
            for q in adapters[src['adapter']]['quantities']:
                b = q.get('accounting')
                if b and led in _ancestors(acc, b):
                    for lid in carried_by.get(b, []):
                        if owner.get(lid) == src['adapter']:
                            errors.append(f'{pw}: {src["adapter"]} already turns {led} into {b} on loop {lid}, which it '
                                          f'owns; passing it counts the same {led} twice')
        unc = {u['accounting'] for u in xc['uncoupled']}
        for u in unc - set(acc):
            errors.append(f'{where}: uncoupled names unknown accounting quantity {u}')
        for u in unc & passed:
            errors.append(f'{where}: {u} is both passed and uncoupled')
        # each input of a coupled adapter carried by a loop another coupled adapter owns is passed or declared uncoupled
        for a in coupled:
            for i in adapters[a]['inputs']:
                for lid in carried_by.get(i, []):
                    if owner.get(lid) in coupled and owner[lid] != a and i not in passed | unc:
                        errors.append(f'{where}: {a} takes {i} (loop {lid}, owned by {owner[lid]}) from its own series; '
                                      f'pass it from the owner or list it as uncoupled')
        # each loop a coupled adapter yields is treated explicitly (never both live unannounced)
        yielded = {(y['adapter'], y['loop']): y for y in xc['yielded']}
        for a in coupled:
            for lid, entry in adapters[a].get('feedback_loops', {}).items():
                if entry['role'] == 'yields' and owner.get(lid) in coupled and (a, lid) not in yielded:
                    errors.append(f'{where}: {a} yields {lid}; state its treatment under yielded')
        for (a, lid), y in yielded.items():
            if adapters.get(a, {}).get('feedback_loops', {}).get(lid, {}).get('role') != 'yields':
                errors.append(f'{where}: yielded lists {lid} for {a}, which does not yield it')
            elif y['treatment'] == 'separate_ledger' and set(loops[lid]['carries']) & passed:
                errors.append(f'{where}: {lid} is treated as a separate ledger but a pass carries it')
            elif y['treatment'] == 'embedded_bracketed' and not any(p['from']['adapter'] == a for p in xc['passes']):
                errors.append(f'{where}: {lid} is embedded in {a}\'s passed series, but {a} passes nothing')


def _check_milestone_interface(contract, errors):
    """Issue #47: a milestone sets one capability level, informs transitions in both directions, and carries no rate."""
    mi = contract['milestone_interface']
    dims = by_id(contract['dimensions'])
    trans = by_id(contract['transitions'])
    kinds = {k['id'] for k in contract['entity_kinds']}
    adapters = {a['id']: {q['name']: q for q in a['quantities']} for a in contract['adapters']}
    listed = {}
    for s in mi['sources']:
        q = adapters.get(s['adapter'], {}).get(s['quantity'])
        if q is None:
            errors.append(f'milestone_interface: adapter {s["adapter"]} has no quantity {s["quantity"]!r}')
        elif q['kind'] != 'event':
            errors.append(f'milestone_interface: {s["adapter"]} {s["quantity"]!r} is a {q["kind"]}, not an event')
        for m in s['milestones']:
            listed[(s['adapter'], m)] = q or {}
    covered = {}
    ids = [b['id'] for b in mi['bindings']]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        errors.append(f'milestone_interface: duplicate binding {dup}')
    for b in mi['bindings']:
        where = f'milestone_interface {b["id"]}'
        key = (b['adapter'], b['milestone'])
        covered.setdefault(key, []).append(b['id'])
        q = listed.get(key)
        if q is None:
            errors.append(f'{where}: {b["milestone"]} is not a milestone listed for {b["adapter"]}')
            q = {}
        d, level = b['sets']['dimension'], b['sets']['level']
        if d not in CAPABILITY:
            errors.append(f'{where}: sets {d}; a milestone sets a capability dimension only {list(CAPABILITY)}')
        elif q.get('dimension') not in (None, d):
            errors.append(f'{where}: sets {d}, but its adapter quantity attaches to {q["dimension"]}')
        if d in dims and level not in dims[d]['levels']:
            errors.append(f'{where}: level {level!r} is not a declared level of {d}')
        for k in b['entity_kinds']:
            if k not in kinds:
                errors.append(f'{where}: unknown entity kind {k}')
            elif d in dims and k not in dims[d]['applies_to']:
                errors.append(f'{where}: {d} does not apply to a {k}')
        directions = set()
        for t in b['may_inform']:
            if t not in trans:
                errors.append(f'{where}: may_inform names unknown transition {t}')
            else:
                directions.add(trans[t]['direction'])
        if directions != {'toward_autonomy', 'toward_constraint'}:
            errors.append(f'{where}: may_inform must name transitions in both directions (a milestone opens no one-way takeoff), '
                          f'has {sorted(directions)}')
    for u in mi['unbound']:
        key = (u['adapter'], u['milestone'])
        if key not in listed:
            errors.append(f'milestone_interface: unbound {u["milestone"]} is not a milestone listed for {u["adapter"]}')
        covered.setdefault(key, []).append('unbound')
    for key in sorted(listed):
        n = len(covered.get(key, []))
        if n != 1:
            errors.append(f'milestone_interface: {key[0]} milestone {key[1]} must be bound or listed unbound exactly once ({n})')


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
    bindings = by_id(contract['milestone_interface']['bindings'])
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
            # milestone events (#47): each sets one capability level and applies no transition
            events = {}
            for m in step.get('milestones', []):
                b = bindings.get(m['binding'])
                if b is None:
                    errors.append(f'{where}: unknown milestone binding {m["binding"]}')
                elif m['entity'] not in ents:
                    errors.append(f'{where}: milestone {m["binding"]} on {m["entity"]}, which is not in the step')
                elif ents[m['entity']]['kind'] not in b['entity_kinds']:
                    errors.append(f'{where}: milestone {m["binding"]} cannot attach to a {ents[m["entity"]]["kind"]}')
                else:
                    d = b['sets']['dimension']
                    if d in events.get(m['entity'], {}):
                        errors.append(f'{where}: {m["entity"]} has two milestone events on {d}')
                    events.setdefault(m['entity'], {})[d] = b
            if prev is None:
                if applied:
                    errors.append(f'{where}: the first step cannot apply a transition')
                if events:
                    errors.append(f'{where}: the first step cannot carry a milestone event')
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
                # A milestone moves its own dimension to its level, first; preconditions then read that value.
                read = {'state': dict(before['state']), 'host': before.get('host')}
                for d, b in events.get(eid, {}).items():
                    level = b['sets']['level']
                    if before['state'].get(d) == level:
                        errors.append(f'{where}: milestone {b["id"]} on {eid} sets {d} to {level}, which it already was')
                    if e['state'].get(d) != level and d not in allowed:
                        errors.append(f'{where}: milestone {b["id"]} sets {eid} {d} to {level}, but the step has {e["state"].get(d)}')
                    allowed.add(d)
                    read['state'][d] = level
                for d in sorted(changed - allowed):
                    errors.append(f'{where}: {eid} {d} changed from {before["state"].get(d)} to {e["state"].get(d)} '
                                  f'without a transition that declares it')
                for t in ts:
                    if not changed & set(t['changes']):
                        errors.append(f'{where}: {eid} applies {t["id"]} but none of its dimensions changed (relabelling)')
                    for d, levels in t['preconditions'].items():
                        if value_of(read, d) not in levels:
                            errors.append(f'{where}: {eid} applies {t["id"]} but {d} was {value_of(read, d)}, not in {levels}')
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
    _check_milestone_interface(contract, errors)
    _check_loops_and_couplings(contract, errors)
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
