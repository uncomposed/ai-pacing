#!/usr/bin/env python3
"""Check dated evidence records and the historical-evaluation protocol; never infer that evidence supports a claim.

    python3 tools/evidence_tool.py check     # records, protocol and forecast registry (wired into make check)
    python3 tools/evidence_tool.py report    # one line per record: kind, reading, dates, allowed uses

Also a small library for the shared evaluation protocol (docs/evidence-protocol.md): date bounds, information-set
(contamination) checks, independence of evidence, Wilson intervals, rolling origins, simple baselines and scores.
Pure Python; no numpy.
"""
import argparse
import calendar
import datetime as dt
import importlib.util
import json
import math
from pathlib import Path
import sys

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / 'evidence/records.yaml'
PROTOCOL = ROOT / 'evidence/protocol.yaml'
SCHEMA = ROOT / 'schema/evidence.schema.json'

OBSERVATION_KINDS = {'observation', 'observation_report'}
# What a claim may cite a record for, by record kind. Stakeholder statements and model outputs are never empirical support.
USES = {
    'empirical_support': OBSERVATION_KINDS,
    'source_model_basis': {'source_model_output', 'source_model_assumption', 'formal_result'},
    'stakeholder_input': {'stakeholder_statement'},
    'motivation': OBSERVATION_KINDS | {'source_model_output', 'source_model_assumption', 'formal_result', 'stakeholder_statement'},
}


def load_yaml(path):
    spec = importlib.util.spec_from_file_location('assumptions_tool', ROOT / 'tools/assumptions_tool.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.load_yaml(path)


# ---------------------------------------------------------------- dates
def date_bounds(text):
    """Earliest and latest day a YYYY, YYYY-MM or YYYY-MM-DD string allows."""
    parts = [int(p) for p in str(text).split('-')]
    if len(parts) == 1:
        return dt.date(parts[0], 1, 1), dt.date(parts[0], 12, 31)
    if len(parts) == 2:
        y, m = parts
        return dt.date(y, m, 1), dt.date(y, m, calendar.monthrange(y, m)[1])
    d = dt.date(*parts)
    return d, d


def available_by(record, cutoff):
    """True only if the record was certainly available on the cutoff date (conservative for partial dates)."""
    return date_bounds(record['availability_date'])[1] <= date_bounds(cutoff)[0]


# ---------------------------------------------------------------- independence
def ancestors(records, ident, seen=None):
    seen = set() if seen is None else seen
    for d in records.get(ident, {}).get('depends_on', []):
        if d not in seen:
            seen.add(d)
            ancestors(records, d, seen)
    return seen


def independent(records, a, b):
    """Two records are not independent if one depends on the other, they share an ancestor, or both were fitted to
    a common dataset."""
    ra, rb = records[a], records[b]
    anc_a, anc_b = ancestors(records, a) | {a}, ancestors(records, b) | {b}
    if anc_a & anc_b:
        return False
    fit_a = set(ra['fitted_to']).union(*[set(records[x]['fitted_to']) for x in anc_a if x in records])
    fit_b = set(rb['fitted_to']).union(*[set(records[x]['fitted_to']) for x in anc_b if x in records])
    return not (fit_a & fit_b)


# ---------------------------------------------------------------- scoring helpers
def wilson(k, n, z=1.959963984540054):
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, mid - half), min(1.0, mid + half))


def interval_score(lo, hi, y, alpha):
    """Gneiting-Raftery interval score of a central (1 - alpha) interval; lower is better."""
    return (hi - lo) + (2 / alpha) * max(0.0, lo - y) + (2 / alpha) * max(0.0, y - hi)


def abs_log_error(forecast, observed):
    return abs(math.log(forecast) - math.log(observed))


def rolling_origins(times, cutoffs, horizon):
    """For each cutoff: (indices with time <= cutoff, indices with cutoff < time <= cutoff + horizon)."""
    out = []
    for c in cutoffs:
        train = [i for i, t in enumerate(times) if t <= c]
        test = [i for i, t in enumerate(times) if c < t <= c + horizon]
        if train and test:
            out.append((c, train, test))
    return out


def flat_forecast(times, values, train, t_new):
    last = max(train, key=lambda i: times[i])
    return values[last]


def loglinear_forecast(times, values, train, t_new):
    xs = [times[i] for i in train]
    ys = [math.log(values[i]) for i in train]
    if len(xs) < 2:
        return values[train[-1]]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    return math.exp(my + slope * (t_new - mx))


# ---------------------------------------------------------------- checks
def _schema(defn, instance):
    schema = json.loads(SCHEMA.read_text())
    sub = dict(schema['$defs'][defn])
    sub['$defs'] = schema['$defs']
    v = jsonschema.Draft202012Validator(sub)
    return [f"schema {defn}: {'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
            for e in sorted(v.iter_errors(instance), key=lambda e: list(e.absolute_path))]


def validate_records(doc):
    errors = _schema('records_file', doc)
    if errors:
        return errors
    ids = [r['id'] for r in doc['records']]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        errors.append(f'duplicate record {dup}')
    recs = {r['id']: r for r in doc['records']}
    for r in doc['records']:
        ident = r['id']
        try:
            avail = date_bounds(r['availability_date'])
            if r['observation_date'] != 'not_applicable':
                start = date_bounds(r['observation_date']['start'])
                end = date_bounds(r['observation_date']['end'])
                if start[0] > end[1]:
                    errors.append(f'{ident}: observation starts after it ends')
                if end[0] > avail[1]:
                    errors.append(f'{ident}: observed after it became available')
            date_bounds(r['extraction']['date'])
        except ValueError as e:
            errors.append(f'{ident}: bad date ({e})')
        if r['kind'] in OBSERVATION_KINDS and r['observation_date'] == 'not_applicable':
            errors.append(f'{ident}: an observation needs an observation_date')
        if r['kind'] == 'stakeholder_statement' and r['extraction']['method'] != 'recorded_statement':
            errors.append(f'{ident}: a stakeholder statement is extracted as recorded_statement')
        if r['reading'] != 'read_primary' and r['extraction']['method'] not in ('summarized_from_secondary',):
            errors.append(f'{ident}: reading is {r["reading"]} but extraction method is {r["extraction"]["method"]}')
        for d in r['depends_on']:
            if d not in recs:
                errors.append(f'{ident}: depends_on unknown record {d}')
        if ident in ancestors(recs, ident):
            errors.append(f'{ident}: depends on itself')
    return errors


def validate_links(links, recs, where):
    """links: [{record, locator, use}] from a claim or assumption. Returns errors."""
    errors = []
    for link in links:
        rid, use = link.get('record'), link.get('use')
        if rid not in recs:
            errors.append(f'{where}: cites unknown evidence record {rid}')
            continue
        if not str(link.get('locator', '')).strip():
            errors.append(f'{where}: cites {rid} without an exact locator (figure, table, section)')
        if use not in USES:
            errors.append(f'{where}: use {use!r} must be one of {sorted(USES)}')
            continue
        r = recs[rid]
        if r['kind'] not in USES[use]:
            errors.append(f'{where}: {rid} is a {r["kind"]}, which cannot be cited as {use}')
        if use == 'empirical_support' and r['reading'] != 'read_primary':
            errors.append(f'{where}: {rid} is {r["reading"]}; only a record read in primary form can be empirical support')
        if use != 'motivation' and r['reading'] == 'not_read':
            errors.append(f'{where}: {rid} was not read; an unread source can only be cited as motivation')
    return errors


def validate_protocol(doc, recs):
    errors = _schema('protocol_file', doc)
    if errors:
        return errors
    base = {b['id'] for b in doc['baselines']}
    scores = {s['id'] for s in doc['scoring_rules']}
    for f in doc['forecasts']:
        ident = f['id']
        if f['label'] == 'locked' and not f.get('lock_commit'):
            errors.append(f'{ident}: a locked forecast needs lock_commit')
        if date_bounds(f['issued'])[1] < date_bounds(f['information_cutoff'])[0]:
            errors.append(f'{ident}: issued before its information cutoff')
        for i in f['inputs']:
            if i not in recs:
                errors.append(f'{ident}: unknown input record {i}')
            elif not available_by(recs[i], f['information_cutoff']):
                errors.append(f'{ident}: input {i} (available {recs[i]["availability_date"]}) postdates the cutoff '
                              f'{f["information_cutoff"]} (contamination)')
        for b in f['baselines']:
            if b not in base:
                errors.append(f'{ident}: unknown baseline {b}')
        for s in f['scoring']:
            if s not in scores:
                errors.append(f'{ident}: unknown scoring rule {s}')
        res = f['resolution']
        if res is not None:
            if res['record'] not in recs:
                errors.append(f'{ident}: resolution cites unknown record {res["record"]}')
            elif f['label'] == 'locked':
                r = recs[res['record']]
                if r['observation_date'] == 'not_applicable':
                    errors.append(f'{ident}: resolution record {r["id"]} has no observation date')
                elif date_bounds(r['observation_date']['start'])[0] <= date_bounds(f['issued'])[1]:
                    errors.append(f'{ident}: labelled locked but its outcome was observed by the issue date; label it retrospective')
    return errors


def validate_outcome_label(label, where, known_assumptions=None):
    errors = _schema('outcome_label', label)
    if errors:
        return [f'{where}: {e}' for e in errors]
    for a in label['structural_assumptions']:
        if known_assumptions is not None and a not in known_assumptions:
            errors.append(f'{where}: outcome label names unknown assumption {a}')
    for u in label['numerical_uncertainty']:
        lo, hi = wilson(u['k'], u['n'])
        if u['k'] > u['n']:
            errors.append(f'{where}: {u["quantity"]}: k > n')
        elif abs(lo - u['interval'][0]) > 5e-4 or abs(hi - u['interval'][1]) > 5e-4:
            errors.append(f'{where}: {u["quantity"]}: interval {u["interval"]} is not the Wilson 95% interval '
                          f'[{lo:.4f}, {hi:.4f}] of {u["k"]}/{u["n"]}')
    return errors


def load_records():
    return load_yaml(RECORDS)


def records_by_id(doc=None):
    doc = doc if doc is not None else load_records()
    return {r['id']: r for r in doc['records']}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['check', 'report'])
    a = ap.parse_args()
    rdoc, pdoc = load_records(), load_yaml(PROTOCOL)
    errors = validate_records(rdoc)
    if not errors:
        errors += validate_protocol(pdoc, records_by_id(rdoc))
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        sys.exit(1)
    if a.command == 'check':
        print(f'evidence: {len(rdoc["records"])} records, {len(pdoc["rules"])} protocol rules, '
              f'{len(pdoc["forecasts"])} registered forecasts; dates and links consistent; nothing here is validation')
    else:
        print('| id | kind | reading | observed | available | may be cited as |')
        print('|---|---|---|---|---|---|')
        for r in rdoc['records']:
            obs = r['observation_date'] if r['observation_date'] == 'not_applicable' else \
                f"{r['observation_date']['start']} to {r['observation_date']['end']}"
            uses = [u for u, kinds in USES.items() if r['kind'] in kinds
                    and not (u == 'empirical_support' and r['reading'] != 'read_primary')
                    and not (u != 'motivation' and r['reading'] == 'not_read')]
            print(f"| {r['id']} | {r['kind']} | {r['reading']} | {obs} | {r['availability_date']} | {', '.join(uses)} |")


if __name__ == '__main__':
    main()
