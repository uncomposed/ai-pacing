#!/usr/bin/env python3
"""Render events.md from the Hugging Face incident tables (issue #15).

    python3 render.py           # rewrite events.md
    python3 render.py --check   # exit 1 if events.md is stale

No network. YAML is read with the repository's loader (PyYAML, or Ruby's standard library as a fallback).
"""
import datetime as dt
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'events.md'

_spec = importlib.util.spec_from_file_location('assumptions_tool', ROOT / 'tools/assumptions_tool.py')
_at = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_at)
load_yaml = _at.load_yaml

CONTROL_CHAIN = ['detection', 'interpretation', 'escalation', 'authorized_action', 'containment', 'audit']


def load():
    return {
        'events': load_yaml(HERE / 'events.yaml'),
        'explanations': load_yaml(HERE / 'explanations.yaml'),
        'records': {r['id']: r for r in load_yaml(ROOT / 'evidence/records.yaml')['records']},
    }


def parse(ts):
    return None if ts is None else dt.datetime.fromisoformat(str(ts).replace('Z', '+00:00'))


def first_public(event, records):
    """Earliest availability date among the read records an event cites."""
    dates = [records[s['record']]['availability_date'] for s in event['sources']
             if records[s['record']]['reading'] != 'not_read']
    return min(dates) if dates else 'unread only'


def window_hours(events, w):
    a, b = events[w['from']]['time'], events[w['to']]['time']
    lo_end, hi_end = parse(b['earliest']), parse(b['latest'])
    lo_start, hi_start = parse(a['earliest']), parse(a['latest'])
    if None in (lo_end, hi_end, lo_start, hi_start):
        return None
    lo = (lo_end - hi_start).total_seconds() / 3600
    hi = (hi_end - lo_start).total_seconds() / 3600
    return max(lo, 0.0), hi


def explanation_matrix(expl):
    """observation id -> {explanation id: True if it has every feature the observation needs}."""
    return {o['id']: {x['id']: set(o['needs']) <= set(x['has']) for x in expl['explanations']}
            for o in expl['observations']}


def fmt_time(t):
    e, l = t['earliest'], t['latest']
    if e is None and l is None:
        return 'unknown'
    if e is None:
        return f'unknown, by {l}'
    if e == l:
        return str(e)
    return f'{e} to {l}'


def cell(text):
    return str(text).replace('|', '\\|').replace('\n', ' ')


def render(data):
    ev = data['events']
    recs = data['records']
    events = {e['id']: e for e in ev['events']}
    out = []
    w = out.append
    w('# Hugging Face incident: evidence table and control timeline')
    w('')
    w(f'Rendered from `events.yaml` (table version {ev["table_version"]}, as of {ev["as_of"]}), '
      '`explanations.yaml` and `evidence/records.yaml` by `render.py`. Do not edit by hand; '
      '`make check` fails if this file is stale.')
    w('')
    w('Times are UTC. "First public" is the earliest availability date of the read evidence records an event '
      'cites. Kinds: observation (reported from logs or records), intent_inference (agents\' beliefs or motives), '
      'institutional_claim (a party\'s unverified statement about itself). Fitted reconstruction, not validation.')
    w('')
    w('## 1. Events')
    w('')
    w('| id | time | basis | first public | stage | actor | kind | verification | statement | evidence | discrepancies |')
    w('|---|---|---|---|---|---|---|---|---|---|---|')
    for e in ev['events']:
        srcs = '; '.join(f'{s["record"]} ({s["locator"]})' for s in e['sources'])
        w(f'| {e["id"]} | {cell(fmt_time(e["time"]))} | {e["time"]["basis"]} | {first_public(e, recs)} | {e["stage"]} | '
          f'{e["actor"]} | {e["kind"]} | {e["verification"]} | {cell(e["statement"])} | {cell(srcs)} | '
          f'{", ".join(e.get("discrepancies", []))} |')
    w('')
    w('## 2. Control chain: detection to audit')
    w('')
    w('Stages are kept separate. A stage with no dated evidence is listed as such rather than merged into its neighbours.')
    w('')
    w('| stage | events (actor, time) |')
    w('|---|---|')
    for stage in CONTROL_CHAIN:
        rows = [e for e in ev['events'] if e['stage'] == stage]
        text = '; '.join(f'{e["id"]} ({e["actor"]}, {fmt_time(e["time"])})' for e in rows) or 'no dated evidence in the read sources'
        w(f'| {stage} | {cell(text)} |')
    w('')
    w('| window | from | to | hours (range) | meaning |')
    w('|---|---|---|---|---|')
    for win in ev['windows']:
        h = window_hours(events, win)
        hs = 'unknown' if h is None else f'{h[0]:.1f} to {h[1]:.1f}'
        w(f'| {win["id"]} | {win["from"]} | {win["to"]} | {hs} | {cell(win["meaning"])} |')
    w('')
    w('Unknowns that bound everything above: when the lab first detected the July 8-13 activity; whether the '
      'July 12 01:30 exit was a deliberate lab action; when the victim\'s first signal fired; when the lab '
      'regained effective control. None of the read sources dates these.')
    w('')
    w('## 3. Institutional responses and resource effects')
    w('')
    w('Recorded as events, not as interventions that worked: every entry has `causal_claim: none asserted`.')
    w('')
    w('| id | actor | time | response | resource effect | causal claim |')
    w('|---|---|---|---|---|---|')
    for e in ev['events']:
        if e['stage'] in ('institutional_response', 'audit'):
            w(f'| {e["id"]} | {e["actor"]} | {cell(fmt_time(e["time"]))} | {cell(e["statement"])} | '
              f'{cell(e.get("resource_effect", ""))} | {e.get("causal_claim", "")} |')
    w('')
    w('## 4. Discrepancies between sources')
    w('')
    w('| id | resolution | statement | sources | note |')
    w('|---|---|---|---|---|')
    for d in ev['discrepancies']:
        w(f'| {d["id"]} | {d["resolution"]} | {cell(d["statement"])} | {", ".join(d["sources"])} | {cell(d.get("note", ""))} |')
    w('')
    w('## 5. Assertions from issue #3, rechecked')
    w('')
    counts = {}
    for a in ev['assertions_issue_3']:
        counts[a['verdict']] = counts.get(a['verdict'], 0) + 1
    w('Verdicts: ' + ', '.join(f'{k} {counts.get(k, 0)}' for k in ('supported', 'contradicted', 'unsupported')) + '.')
    w('')
    w('| id | claim | verdict | evidence | note |')
    w('|---|---|---|---|---|')
    for a in ev['assertions_issue_3']:
        w(f'| {a["id"]} | {cell(a["claim"])} | **{a["verdict"]}** | {", ".join(a["evidence"])} | {cell(a["note"])} |')
    w('')
    w('## 6. Isolated versus communicating explanations')
    w('')
    ex = data['explanations']
    m = explanation_matrix(ex)
    xs = [x['id'] for x in ex['explanations']]
    w('An explanation accounts for an observation only if it has every structural feature the observation needs '
      '(`explanations.yaml`). No capacity multipliers are involved. The tags were chosen after reading the sources, so this is consistency, not a test.')
    w('')
    w('| observation | needs | ' + ' | '.join(xs) + ' |')
    w('|---|---|' + '---|' * len(xs))
    for o in ex['observations']:
        w(f'| {o["id"]}: {cell(o["statement"])} | {", ".join(o["needs"]) or "none"} | '
          + ' | '.join('yes' if m[o['id']][x] else 'no' for x in xs) + ' |')
    totals = {x: sum(m[o][x] for o in m) for x in xs}
    w('| **accounted for** | | ' + ' | '.join(f'{totals[x]} of {len(m)}' for x in xs) + ' |')
    w('')
    return '\n'.join(out)


def main():
    text = render(load())
    if '--check' in sys.argv:
        if not OUT.exists() or OUT.read_text() != text:
            print('events.md is stale: run python3 research_notes/external/hugging-face-incident/render.py')
            sys.exit(1)
        print('events.md is current')
        return
    OUT.write_text(text)
    print(f'wrote {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
