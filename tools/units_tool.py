#!/usr/bin/env python3
"""Check the quantity dictionary, conversions and equations of the research-to-industry bridge (issue #11).

    python3 tools/units_tool.py check     # schema, units, dimensions, links, stocks and flows, the stopping rule (make check)
    python3 tools/units_tool.py report    # quantities by category and conversions by class

Files: research_notes/external/units-bridge/{quantities,conversions,equations}.yaml.
Dimensional analysis only shows that units agree. It cannot show that a conversion is meaningful (a METR horizon
and a doubling time are both times); `semantic`, the conversion classes and the forbidden list carry that part.
"""
import argparse
import ast
from collections import deque
import importlib.util
import math
from pathlib import Path
import re
import sys

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / 'research_notes/external/units-bridge'
FILES = {'quantities': BRIDGE / 'quantities.yaml', 'conversions': BRIDGE / 'conversions.yaml',
         'equations': BRIDGE / 'equations.yaml'}
SCHEMA = ROOT / 'schema/units-bridge.schema.json'
MODES = ROOT / 'systems/modes.yaml'
RECORDS = ROOT / 'evidence/records.yaml'

_spec = importlib.util.spec_from_file_location('assumptions_tool', ROOT / 'tools/assumptions_tool.py')
assumptions_tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(assumptions_tool)
load_yaml = assumptions_tool.load_yaml

# The mode contract writes adapter units in prose; this is how each reads in dictionary units.
CONTRACT_UNITS = {
    'human-hours': 'h', 'Earth-industry units (H = 1)': 'EIU', 'USD per year': 'USD/yr', 'source-native (FLOP)': 'FLOP',
    'ratio (with AI / without)': '1', 'fraction of tasks': '1', 'probability': '1', 'orders of magnitude (OOMs)': '1',
    "share of today's leading-edge capacity": 'LEC', 'source-native multiplier': '1',
    'date a threshold on the effective-compute scale is crossed': 'yr',
    'eFLOP (software-adjusted, S(0) = 1)': 'FLOP', 'real USD per year': 'USD/yr',
    'Earth-industry units (EIU, a stock; H = 1)': 'EIU', 'per year': '1/yr',
}
# Quantity kinds that the stock/flow rule applies to (issue #39). Other kinds (rate, state, share, ...) are not checked.
STOCK_FLOW = ('stock', 'flow')
TIME = 'time'
ESTIMATED = {'observed_primary', 'observed_secondary', 'source_model_output', 'external_pending'}
SCENARIO = {'scenario', 'project_assumption'}
# Categories a capability metric must never reach through coupled conversions (#11 stopping rule).
GUARDED = {'supply_chain_closure', 'external_control'}
# Symbols without a value are checked for dimensions only; this stand-in value avoids 1 - 1 = 0 and similar.
PLACEHOLDER = 0.7310585786300049


class UnitError(ValueError):
    pass


# ---------------------------------------------------------------------------------------------------- unit algebra
def combine(a, b, sign=1):
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + sign * v
        if out[k] == 0:
            del out[k]
    return out


def power(d, n):
    if any((v * n) != int(v * n) for v in d.values()):
        raise UnitError(f'non-integer power {n} of a dimensional quantity')
    return {k: int(v * n) for k, v in d.items() if v * n}


def parse_unit(text, units):
    """'person*h/yr' -> (scale to base units, {dimension: exponent})."""
    text = str(text).strip()
    tokens = re.split(r'([*/])', text)
    scale, dims, sign = 1.0, {}, 1
    for tok in tokens:
        tok = tok.strip()
        if tok in ('*', '/'):
            sign = 1 if tok == '*' else -1
            continue
        m = re.fullmatch(r'([A-Za-z0-9_]+)(?:\^(-?\d+))?', tok)
        if not m:
            raise UnitError(f'cannot parse unit {text!r}')
        sym, exp = m.group(1), int(m.group(2) or 1)
        if sym == '1' and exp == 1:
            continue
        if sym not in units:
            raise UnitError(f'unknown unit {sym!r} in {text!r}')
        u = units[sym]
        scale *= u['factor'] ** (sign * exp)
        dims = combine(dims, power(u.get('dims', {}), sign * exp))
    return scale, dims


def fmt(dims):
    return '*'.join(f'{k}^{v}' if v != 1 else k for k, v in sorted(dims.items())) or 'dimensionless'


class Q:
    """A value in base units with its dimensions."""
    __slots__ = ('v', 'd')

    def __init__(self, v, d):
        self.v, self.d = v, d


def evaluate(text, symbols, units):
    """Evaluate an expression or (in)equation; raise UnitError on any dimensional inconsistency."""
    tree = ast.parse(text.replace('<=', ' <= ').replace('>=', ' >= ').replace(' = ', ' == '), mode='eval').body

    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return Q(float(n.value), {})
        if isinstance(n, ast.Name):
            if n.id not in symbols:
                raise UnitError(f'unknown symbol {n.id}')
            s = symbols[n.id]
            scale, d = parse_unit(s['unit'], units)
            return Q(s.get('value', PLACEHOLDER) * scale, d)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            x = ev(n.operand)
            return Q(-x.v if isinstance(n.op, ast.USub) else x.v, x.d)
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, (ast.Add, ast.Sub)):
                if a.d != b.d:
                    raise UnitError(f'adds {fmt(a.d)} to {fmt(b.d)}')
                return Q(a.v + b.v if isinstance(n.op, ast.Add) else a.v - b.v, a.d)
            if isinstance(n.op, ast.Mult):
                return Q(a.v * b.v, combine(a.d, b.d))
            if isinstance(n.op, ast.Div):
                return Q(a.v / b.v, combine(a.d, b.d, -1))
            if isinstance(n.op, ast.Pow):
                if b.d:
                    raise UnitError('dimensional exponent')
                return Q(a.v ** b.v, power(a.d, b.v))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            args = [ev(x) for x in n.args]
            f = n.func.id
            if f in ('exp', 'log', 'log10'):
                if len(args) != 1 or args[0].d:
                    raise UnitError(f'{f} of a dimensional argument ({fmt(args[0].d)})')
                return Q(getattr(math, f)(args[0].v), {})
            if f in ('min', 'max'):
                if any(x.d != args[0].d for x in args):
                    raise UnitError(f'{f} over different dimensions: {", ".join(fmt(x.d) for x in args)}')
                return Q((min if f == 'min' else max)(x.v for x in args), args[0].d)
        if isinstance(n, ast.Compare) and len(n.ops) == 1:
            a, b = ev(n.left), ev(n.comparators[0])
            if a.d != b.d:
                raise UnitError(f'left side is {fmt(a.d)}, right side is {fmt(b.d)}')
            return (a, b)
        raise UnitError(f'unsupported expression: {ast.dump(n)[:60]}')

    return ev(tree)


# ------------------------------------------------------------------------------------------------------- validation
def _schema(defn, instance):
    import json
    schema = json.loads(SCHEMA.read_text())
    sub = dict(schema['$defs'][defn])
    sub['$defs'] = schema['$defs']
    return [f'{defn}: {e.message} at {"/".join(str(p) for p in e.absolute_path)}'
            for e in jsonschema.Draft202012Validator(sub).iter_errors(instance)]


def bridging(dims, physical, normalized):
    """A factor bridges when it mixes a normalized and a physical non-time dimension, or two physical non-time ones."""
    phys = {k for k in dims if k in physical and k != TIME}
    norm = {k for k in dims if k in normalized}
    return bool(phys and norm) or len(phys) > 1


def validate(q, c, e, modes, params, records=None):
    errors = _schema('quantities_file', q) + _schema('conversions_file', c) + _schema('equations_file', e)
    if errors:
        return errors
    units = q['units']
    physical, normalized = set(q['dimensions']['physical']), set(q['dimensions']['normalized'])
    for sym, u in units.items():
        for d in u['dims']:
            if d not in physical | normalized:
                errors.append(f'unit {sym}: unknown dimension {d}')
    qty, dims = {}, {}
    for x in q['quantities']:
        if x['id'] in qty:
            errors.append(f'duplicate quantity {x["id"]}')
        qty[x['id']] = x
        try:
            dims[x['id']] = parse_unit(x['unit'], units)[1]
        except UnitError as err:
            errors.append(f'{x["id"]}: {err}')
    # categories
    for cat in q['categories']:
        if not any(x['category'] == cat for x in q['quantities']):
            errors.append(f'category {cat} has no quantity')
    for x in q['quantities']:
        if x['category'] not in q['categories']:
            errors.append(f'{x["id"]}: unknown category {x["category"]}')
    # mode contract and solver links
    acc = {a['id'] for a in modes['accounting']}
    dimn = {d['id'] for d in modes['dimensions']}
    mode_ids = {m['id'] for m in modes['modes']}
    adapters = {a['id']: {qq['name']: qq for qq in a['quantities']} for a in modes['adapters']}

    def check_contract(where, ct, unit_dims=None):
        out = []
        if 'accounting' in ct and ct['accounting'] not in acc:
            out.append(f'{where}: unknown accounting quantity {ct["accounting"]}')
        if 'dimension' in ct and ct['dimension'] not in dimn:
            out.append(f'{where}: unknown mode-contract dimension {ct["dimension"]}')
        if 'mode' in ct and ct['mode'] not in mode_ids:
            out.append(f'{where}: unknown mode {ct["mode"]}')
        aq = ct.get('adapter_quantity')
        if aq:
            found = adapters.get(aq['adapter'], {}).get(aq['name'])
            if found is None:
                out.append(f'{where}: adapter {aq["adapter"]} has no quantity {aq["name"]!r}')
            elif unit_dims is not None:
                alias = CONTRACT_UNITS.get(found['unit'])
                if alias is None:
                    out.append(f'{where}: cannot read the contract unit {found["unit"]!r}; add it to CONTRACT_UNITS')
                elif parse_unit(alias, units)[1] != unit_dims:
                    out.append(f'{where}: unit {fmt(unit_dims)} differs from the contract unit {found["unit"]!r}')
        return out

    for x in q['quantities']:
        errors += check_contract(x['id'], x['contract'], dims.get(x['id']))
        for p in x.get('pact_params', []):
            if p not in params:
                errors.append(f'{x["id"]}: pact parameter {p} is not in PARAMS')
        if x['models'] and 'AD-PACT' not in x['models'] and x.get('pact_params'):
            errors.append(f'{x["id"]}: names pact parameters but not the AD-PACT model')
    # closure and sovereignty concepts
    concept_of = {}
    elements = set()
    for cl in q['closure_and_sovereignty']:
        errors += check_contract(cl['id'], cl['contract'])
        key = (cl['contract'].get('dimension') or cl['contract'].get('mode'), cl['contract'].get('element'))
        if key in elements:
            errors.append(f'{cl["id"]}: maps to the same contract element as another concept {key}')
        elements.add(key)
        for qid in cl['quantities']:
            if qid not in qty:
                errors.append(f'{cl["id"]}: unknown quantity {qid}')
            elif qid in concept_of:
                errors.append(f'{qid} belongs to two concepts ({concept_of[qid]}, {cl["id"]})')
            concept_of[qid] = cl['id']
        if 'mode' in cl['contract'] and cl['quantities']:
            errors.append(f'{cl["id"]}: a mode is a derived view, not a quantity; list no quantities')
    # equations
    syms = e['symbols']
    for name, s in syms.items():
        try:
            d = parse_unit(s['unit'], units)[1]
        except UnitError as err:
            errors.append(f'symbol {name}: {err}')
            continue
        if 'quantity' in s:
            if s['quantity'] not in qty:
                errors.append(f'symbol {name}: unknown quantity {s["quantity"]}')
            elif dims.get(s['quantity']) != d:
                errors.append(f'symbol {name}: unit {s["unit"]} does not match {s["quantity"]} ({qty[s["quantity"]]["unit"]})')
    for eq in e['equations']:
        try:
            res = evaluate(eq['text'], syms, units)
            if not isinstance(res, tuple):
                raise UnitError('not an equation or inequality')
            lhs, rhs = res
        except (UnitError, SyntaxError, ValueError, ZeroDivisionError) as err:
            errors.append(f'equation {eq["id"]}: {err}')
            continue
        if 'check_value' in eq:
            target = syms.get(eq['check_value'], {})
            if 'value' not in target:
                errors.append(f'equation {eq["id"]}: check_value {eq["check_value"]} has no value')
            elif not math.isclose(lhs.v, rhs.v, rel_tol=1e-3):
                errors.append(f'equation {eq["id"]}: {eq["check_value"]} is declared {lhs.v:.6g} but evaluates to {rhs.v:.6g} (base units)')
    # conversions
    seen, pairs = set(), {}
    for cv in c['conversions']:
        ident, cls = cv['id'], cv['class']
        where = f'conversion {ident}'
        if ident in seen:
            errors.append(f'duplicate conversion {ident}')
        seen.add(ident)
        if cv['from'] not in qty or cv['to'] not in qty:
            errors.append(f'{where}: unknown quantity {cv["from"] if cv["from"] not in qty else cv["to"]}')
            continue
        pairs.setdefault((cv['from'], cv['to']), []).append(cv)
        if cls == 'forbidden':
            if not cv.get('reason'):
                errors.append(f'{where}: a forbidden conversion states its reason')
            if cv['coupled'] or 'factor' in cv:
                errors.append(f'{where}: a forbidden conversion has no factor and is never coupled')
            continue
        for f in ('form', 'mechanism', 'delay', 'constraints', 'evidence'):
            if not cv.get(f):
                errors.append(f'{where}: needs {f}')
        if not cv.get('form') or not cv.get('delay'):
            continue
        ev = cv.get('evidence', {}).get('status')
        fac = cv.get('factor')
        if cls in ('normalization', 'identity', 'empirical_scale_estimate', 'bounded_scenario') and not fac:
            errors.append(f'{where}: a {cls} needs a factor with a unit')
            continue
        if cls == 'unidentified':
            if cv['coupled']:
                errors.append(f'{where}: an unidentified conversion must stay uncoupled (#11 stopping rule)')
            if fac and ('value' in fac or 'bounds' in fac):
                errors.append(f'{where}: an unidentified conversion carries no value or bounds; make it a bounded_scenario')
        if fac and (cv['from'] not in dims or cv['to'] not in dims):
            continue                                        # a unit error is already reported for the quantity
        if fac:
            try:
                fscale, fd = parse_unit(fac['unit'], units)
            except UnitError as err:
                errors.append(f'{where}: {err}')
                continue
            a, b = dims[cv['from']], dims[cv['to']]
            form = cv['form']
            got = {'linear': combine(a, fd), 'reciprocal': combine(fd, a, -1), 'log10': {}, 'exp10': fd}[form]
            if form == 'log10' and a != fd:
                errors.append(f'{where}: log10 needs a reference with the dimensions of {cv["from"]} ({fmt(a)}), not {fmt(fd)}')
            if form == 'exp10' and a:
                errors.append(f'{where}: exp10 needs a dimensionless index, {cv["from"]} is {fmt(a)}')
            if got != b:
                errors.append(f'{where}: {fmt(a)} via factor {fac["unit"]} gives {fmt(got)}, but {cv["to"]} is {fmt(b)}')
            bridge = bridging(fd, physical, normalized) or (form == 'linear' and bridging(combine(b, a, -1), physical, normalized))
            if cls in ('normalization', 'identity'):
                if bridge:
                    errors.append(f'{where}: factor {fac["unit"]} bridges different dimensions, so it is an empirical scale estimate or a scenario, not a {cls}')
                if 'bounds' in fac or 'value' not in fac:
                    errors.append(f'{where}: a {cls} has one exact value and no bounds')
                if ev != 'normalization':
                    errors.append(f'{where}: a {cls} has evidence status normalization')
            if cls == 'empirical_scale_estimate':
                if ev not in ESTIMATED:
                    errors.append(f'{where}: an empirical scale estimate needs evidence status in {sorted(ESTIMATED)}')
                if cv['coupled'] and 'bounds' not in fac:
                    errors.append(f'{where}: a coupled empirical scale estimate needs bounds')
            if cls == 'bounded_scenario':
                if 'bounds' not in fac:
                    errors.append(f'{where}: a bounded scenario needs bounds')
                if ev not in SCENARIO:
                    errors.append(f'{where}: a bounded scenario has evidence status scenario or project_assumption')
            if 'bounds' in fac:
                lo, hi = fac['bounds']
                if not lo <= hi or ('value' in fac and not lo <= fac['value'] <= hi):
                    errors.append(f'{where}: bounds {fac["bounds"]} do not contain the value')
            if cv.get('derivation'):
                try:
                    r = evaluate(cv['derivation'], syms, units)
                except (UnitError, SyntaxError) as err:
                    errors.append(f'{where}: derivation: {err}')
                else:
                    if r.d != fd:
                        errors.append(f'{where}: derivation gives {fmt(r.d)}, factor unit is {fmt(fd)}')
                    elif 'value' in fac and not math.isclose(r.v, fac['value'] * fscale, rel_tol=1e-3):
                        errors.append(f'{where}: derivation gives {r.v / fscale:.6g} {fac["unit"]}, declared {fac["value"]:.6g}')
        a_cl, b_cl = concept_of.get(cv['from']), concept_of.get(cv['to'])
        if a_cl and b_cl and a_cl != b_cl:
            errors.append(f'{where}: links {a_cl} to {b_cl}; closure and sovereignty concepts stay distinct (#11 box 5)')
        if cv['delay'].get('kind') in ('fixed', 'bounded'):
            dl = cv['delay']
            try:
                if parse_unit(dl.get('unit', ''), units)[1] != {TIME: 1}:
                    errors.append(f'{where}: delay unit must be a time')
            except UnitError as err:
                errors.append(f'{where}: delay: {err}')
    for (a, b), cvs in pairs.items():
        if any(x['class'] == 'forbidden' for x in cvs) and len(cvs) > 1:
            errors.append(f'{a} -> {b} is forbidden and also declared as {", ".join(x["id"] for x in cvs if x["class"] != "forbidden")}')
    # the stopping rule: no coupled path from a capability metric into closure or control
    graph = {}
    for cv in c['conversions']:
        if cv['coupled'] and cv['class'] != 'forbidden':
            graph.setdefault(cv['from'], []).append(cv['to'])
    for start in (x['id'] for x in q['quantities'] if x['category'] == 'capability_metric'):
        queue, seen_q = deque([start]), {start}
        while queue:
            node = queue.popleft()
            for nxt in graph.get(node, []):
                if nxt in seen_q:
                    continue
                seen_q.add(nxt)
                t = qty.get(nxt, {})
                if t.get('category') in GUARDED or t.get('no_calibration_from_capability'):
                    errors.append(f'stopping rule: capability metric {start} reaches {nxt} through coupled conversions')
                queue.append(nxt)
    errors += check_stock_flow(q, c, e, modes, units, qty, dims, normalized)
    errors += check_primary_evidence(q, c, records if records is not None else load_yaml(RECORDS))
    return errors


def check_primary_evidence(q, c, records):
    """A value marked observed_primary cites a dated evidence record that is an observation read in primary form."""
    errors = []
    recs = {r['id']: r for r in records['records']}
    for x in q['quantities'] + c['conversions']:
        ev = x.get('evidence', {})
        if ev.get('status') != 'observed_primary':
            continue
        ids = re.findall(r'EV-[A-Z0-9-]*[A-Z0-9]', ev['ref'])
        good = [i for i in ids if recs.get(i, {}).get('kind') == 'observation' and recs[i].get('reading') == 'read_primary']
        if not good:
            errors.append(f'{x["id"]}: observed_primary needs an evidence record in evidence/records.yaml that is an '
                          f'observation read in primary form (cites {ids or "none"})')
    return errors


def check_stock_flow(q, c, e, modes, units, qty, dims, normalized):
    """Issue #39: one definition per normalized unit, and stocks and flows kept apart in the dictionary and contract."""
    errors = []
    acc_kind = {a['id']: a['kind'] for a in modes['accounting']}
    adapters = {a['id']: {qq['name']: qq for qq in a['quantities']} for a in modes['adapters']}
    convs = {cv['id']: cv for cv in c['conversions']}
    eqs = {x['id'] for x in e['equations']}
    # definitions: exactly one per normalized dimension, a stock, with its links
    defined = {}
    for df in q['definitions']:
        where = f'definition {df["id"]}'
        if df['dimension'] not in normalized:
            errors.append(f'{where}: {df["dimension"]} is not a normalized dimension')
        if df['dimension'] in defined:
            errors.append(f'{where}: {df["dimension"]} already has a definition ({defined[df["dimension"]]}); a unit is defined once')
        defined[df['dimension']] = df['id']
        try:
            if parse_unit(df['unit'], units)[1] != {df['dimension']: 1}:
                errors.append(f'{where}: unit {df["unit"]} is not one unit of {df["dimension"]}')
        except UnitError as err:
            errors.append(f'{where}: {err}')
        for b in df['basis']:
            if b['equation'] not in eqs:
                errors.append(f'{where}: basis names unknown equation {b["equation"]}')
        for cid in df['measured_by']:
            if cid not in convs:
                errors.append(f'{where}: measured_by names unknown conversion {cid}')
        for r in df['rejects']:
            if r.get('kept_as') and r['kept_as'] not in convs:
                errors.append(f'{where}: rejected reading kept as unknown conversion {r["kept_as"]}')
        flow_dims = {df['dimension']: 1, TIME: -1}
        uses_flow = any(dims.get(x['id']) == flow_dims for x in q['quantities'])
        rate = df.get('output_rate')
        if uses_flow and not rate:
            errors.append(f'{where}: quantities use {df["unit"]} per time, so the definition states its output rate')
        if rate:
            cv = convs.get(rate['conversion'])
            if cv is None:
                errors.append(f'{where}: output_rate names unknown conversion {rate["conversion"]}')
            elif cv['class'] != 'normalization' or 'value' not in cv.get('factor', {}):
                errors.append(f'{where}: output_rate {cv["id"]} must be a normalization with one value')
            elif (qty.get(cv['from'], {}).get('kind') != 'stock' or qty.get(cv['to'], {}).get('kind') != 'flow'
                  or dims.get(cv['from']) != {df['dimension']: 1} or dims.get(cv['to']) != flow_dims):
                errors.append(f'{where}: output_rate {cv["id"]} must lead from a stock in {df["unit"]} to a flow in {df.get("flow_unit")}')
            try:
                if df.get('flow_unit') is None or parse_unit(df['flow_unit'], units)[1] != flow_dims:
                    errors.append(f'{where}: flow_unit must be {df["unit"]} per time')
            except UnitError as err:
                errors.append(f'{where}: {err}')
    for d in normalized:
        if d not in defined:
            errors.append(f'normalized dimension {d} has no definition; a normalized unit is defined once (#39)')
    # #61: every contract quantity booked to an accounting quantity declares its kind, linked here or not
    for ad_id, quants in adapters.items():
        for name, found in quants.items():
            if 'accounting' in found and 'kind' not in found:
                errors.append(f'{ad_id}: contract quantity {name!r} is booked to {found["accounting"]} but declares no kind (#61)')
    # stocks and flows
    for x in q['quantities']:
        ident, kind, d = x['id'], x['kind'], dims.get(x['id'])
        ak = acc_kind.get(x['contract'].get('accounting'))
        if kind in STOCK_FLOW and ak in STOCK_FLOW and kind != ak:
            errors.append(f'{ident}: a {kind} is booked to {x["contract"]["accounting"]}, a {ak}; '
                          f'book it to a {kind} and state the output rate between them (#39)')
        if d is not None and any(k in normalized for k in d):
            per_time = d.get(TIME, 0) == -1
            if kind == 'flow' and not per_time:
                errors.append(f'{ident}: a flow in a normalized unit is per time ({x["unit"]} is not)')
            if kind in ('stock', 'threshold') and TIME in d:
                errors.append(f'{ident}: a {kind} in a normalized unit carries no time dimension ({x["unit"]})')
        aq = x['contract'].get('adapter_quantity')
        found = adapters.get(aq['adapter'], {}).get(aq['name']) if aq else None
        if found is None:
            continue
        if found.get('kind') == 'ambiguous':
            # #61: the contract records the source as ambiguous; the dictionary may pick a candidate, never another kind.
            if kind in STOCK_FLOW and kind not in found.get('kind_ambiguity', {}).get('candidates', []):
                errors.append(f'{ident}: the contract quantity {aq["adapter"]} {aq["name"]!r} is ambiguous between '
                              f'{found.get("kind_ambiguity", {}).get("candidates")}, not {kind}')
        elif kind in STOCK_FLOW and acc_kind.get(found.get('accounting')) in STOCK_FLOW and found.get('kind') != kind:
            errors.append(f'{ident}: the contract quantity {aq["adapter"]} {aq["name"]!r} must declare kind {kind} '
                          f'(it declares {found.get("kind")})')
        rate = found.get('output_rate')
        if rate:
            match = [cv for cv in c['conversions'] if cv['from'] == ident and cv['class'] == 'normalization'
                     and qty.get(cv['to'], {}).get('contract', {}).get('accounting') == rate['accounting']]
            if not match:
                errors.append(f'{ident}: {aq["adapter"]} declares an output rate to {rate["accounting"]}, but no '
                              f'normalization leads from {ident} to a quantity booked there')
            for cv in match:
                alias = CONTRACT_UNITS.get(rate['unit'])
                if alias is None:
                    errors.append(f'{ident}: cannot read the output-rate unit {rate["unit"]!r}; add it to CONTRACT_UNITS')
                    continue
                cs, cd = parse_unit(alias, units)
                fs, fd = parse_unit(cv['factor']['unit'], units)
                if cd != fd or not math.isclose(rate['value'] * cs, cv['factor']['value'] * fs, rel_tol=1e-9):
                    errors.append(f'{ident}: {aq["adapter"]} output rate {rate["value"]} {rate["unit"]} differs from '
                                  f'{cv["id"]} ({cv["factor"]["value"]} {cv["factor"]["unit"]})')
    return errors


def load_all():
    return ({k: load_yaml(p) for k, p in FILES.items()}, load_yaml(MODES), assumptions_tool.load_params())


def report(q, c):
    lines = ['# Quantity dictionary and conversions (issue #11)', '', 'Generated by `python3 tools/units_tool.py report`.', '']
    for cat in q['categories']:
        lines += [f'## {cat}', '', '| id | unit | evidence |', '|---|---|---|']
        lines += [f'| {x["id"]} | {x["unit"]} | {x["evidence"]["status"]} |' for x in q['quantities'] if x['category'] == cat]
        lines.append('')
    lines += ['## Conversions', '', '| id | from | to | class | coupled |', '|---|---|---|---|---|']
    lines += [f'| {cv["id"]} | {cv["from"]} | {cv["to"]} | {cv["class"]} | {cv["coupled"]} |' for cv in c['conversions']]
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['check', 'report'])
    a = ap.parse_args()
    files, modes, params = load_all()
    errors = validate(files['quantities'], files['conversions'], files['equations'], modes, params)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        sys.exit(1)
    if a.command == 'check':
        cls = {}
        for cv in files['conversions']['conversions']:
            cls[cv['class']] = cls.get(cv['class'], 0) + 1
        print(f'units bridge: {len(files["quantities"]["definitions"])} unit definitions (stocks; output rate stated), '
              f'{len(files["quantities"]["quantities"])} quantities in {len(files["quantities"]["categories"])} categories, '
              f'{len(files["equations"]["equations"])} equations dimensionally consistent, conversions '
              + ', '.join(f'{v} {k}' for k, v in sorted(cls.items()))
              + '; no coupled path from capability metrics to closure or control; nothing validated empirically')
    else:
        print(report(files['quantities'], files['conversions']))


if __name__ == '__main__':
    main()
