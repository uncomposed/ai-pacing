#!/usr/bin/env python3
"""Recompute RE-Bench's released numbers from data/ and report what matches (issue #58). [[ai gen]]

    python3 reproduce.py                 # write results/reproduction.json
    python3 reproduce.py --check         # recompute and compare with the committed file (numbers within 1e-9)

Offline, standard library only. Every check says what it recomputes, from what, the tolerance, and the
verdict. Mismatches are results: they are reported, not tuned away. Checks that need data METR has not
released are listed with status not_reproducible.
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / 'data'
OUT = HERE / 'results' / 'reproduction.json'

# Raw-value transforms in the scoring code (data/task_scores.csv names them; build_data.py checks the code).
TRANSFORM = {
    'log(loss - 1.5)': lambda x: math.log(x - 1.5),
    'log(seconds)': math.log,
    'log(milliseconds)': math.log,
}


def decimals(s):
    return len(s.split('.')[1]) if '.' in s else 0


def half_unit(s):
    return 0.5 * 10 ** -decimals(s)


def load():
    tasks = {r['paper_name'].lower(): r for r in csv.DictReader((DATA / 'task_scores.csv').read_text(encoding='utf-8').splitlines())}
    paper = json.loads((DATA / 'paper_values.json').read_text())
    hb = list(csv.DictReader((DATA / 'human_baselines.csv').read_text(encoding='utf-8').splitlines()))
    return tasks, paper, hb


def score_interval(t, which):
    """Interval of the start or reference score allowed by the published rounding. Uses the raw value through the
    code's transform where the README gives one (more precise than the 2-digit score), else the rounded score."""
    raw, score = t[f'{which}_raw'], t[f'{which}_score']
    if raw and t['score_transform'] in TRANSFORM:
        f = TRANSFORM[t['score_transform']]
        a, b = f(float(raw) - half_unit(raw)), f(float(raw) + half_unit(raw))
        return min(a, b), max(a, b)
    return float(score) - half_unit(score), float(score) + half_unit(score)


def norm_interval(y, s, r):
    """Range of (y - s) / (r - s) over s and r in their intervals (monotone in each, so corners suffice)."""
    vals = [(y - si) / (ri - si) for si in s for ri in r]
    return min(vals), max(vals)


def check_transforms(tasks):
    """README start and reference scores equal the scoring code's transform of the README raw values."""
    out = []
    for name, t in tasks.items():
        if not t['start_raw'] or t['score_transform'] not in TRANSFORM:
            continue
        f = TRANSFORM[t['score_transform']]
        for which in ('start', 'reference'):
            got = f(float(t[f'{which}_raw']))
            pub = t[f'{which}_score']
            ok = abs(got - float(pub)) <= half_unit(pub) + 1e-12
            # The raw value is itself rounded: also accept a match within that rounding.
            lo, hi = score_interval(t, which)
            ok_raw = lo - half_unit(pub) <= float(pub) <= hi + half_unit(pub)
            out.append({'environment': t['paper_name'], 'which': which, 'raw': float(t[f'{which}_raw']),
                        'transform': t['score_transform'], 'recomputed': round(got, 6), 'published': float(pub),
                        'tolerance': 'half a unit in the last published digit', 'match': ok or ok_raw})
    return out


def raw_to_score(t, raw, unit):
    tr = t['score_transform']
    if tr in TRANSFORM:
        return TRANSFORM[tr](raw)
    if unit == '%':
        return raw / 100
    return raw  # win rate, 1 - distance: the paper's raw ceiling is already on the score scale


def check_ceilings(tasks, paper):
    """Paper Table 'ceiling_estimates': normalized ceilings from the raw ceilings and the README start/reference scores."""
    out = []
    for row in paper['v2']['ceiling']:
        t = tasks[row['environment'].lower()]
        s, r = score_interval(t, 'start'), score_interval(t, 'reference')
        # For lower-is-better scores the low raw end gives the high normalized end; the paper lists both ranges
        # in ascending order, so pair them by sorting on the recomputed normalized value.
        y = sorted((raw_to_score(t, x, row['raw_unit']) for x in row['raw']),
                   key=lambda yi: sum(norm_interval(yi, s, r)))
        rec, ok = [], True
        for yi, pub in zip(y, row['normalized']):
            lo, hi = norm_interval(yi, s, r)
            rec.append([round(lo, 4), round(hi, 4)])
            ok &= lo - 0.005 <= pub <= hi + 0.005
        # Reference score that the published normalized range implies, holding the start score at the README value.
        s0 = float(t['start_score']) if not t['start_raw'] else TRANSFORM[t['score_transform']](float(t['start_raw']))
        implied_ref = [s0 + (yi - s0) / ni for yi, ni in zip(y, row['normalized'])]
        out.append({'environment': row['environment'], 'raw': row['raw'], 'raw_unit': row['raw_unit'],
                    'published_normalized': row['normalized'], 'recomputed_range': rec,
                    'implied_reference_score': [round(x, 4) for x in implied_ref],
                    'readme_reference_score': float(t['reference_score']),
                    'tolerance': 'published value within the recomputed range widened by 0.005 (its own rounding)',
                    'match': ok})
    return out


def check_sourcing(paper):
    rows = {r['source']: r for r in paper['v2']['baseline_sourcing']}
    total = rows.pop('Total')
    runs = sum(r['runs'] for r in rows.values())
    people = sum(r['baseliners'] for r in rows.values())
    wmean = sum(r['runs'] * r['avg_score'] for r in rows.values()) / runs
    text = paper['v2']['baseline_sourcing_text']
    return {
        'runs_sum': runs, 'runs_total': total['runs'], 'runs_match': runs == total['runs'],
        'baseliners_sum': people, 'baseliners_total': total['baseliners'], 'baseliners_match': people == total['baseliners'],
        'run_weighted_mean': round(wmean, 4), 'published_total_mean': total['avg_score'],
        'mean_match': abs(wmean - total['avg_score']) <= 0.005 + 0.005,  # rounding of the inputs and the total
        'text_vs_table': {'professional_network': [text['professional_network'], rows['Professional network']['avg_score']],
                          'hiring': [text['hiring'], rows['ML RS/RE hiring process']['avg_score']]},
        'text_matches_table': text['professional_network'] == rows['Professional network']['avg_score']
        and text['hiring'] == rows['ML RS/RE hiring process']['avg_score'],
    }


def check_validation(paper):
    v = paper['v2']['validation']
    m = paper['v2']['macros']
    k = sum(r['gt_0p05_at_8h'][0] for r in v)
    n = sum(r['gt_0p05_at_8h'][1] for r in v)
    ek = sum(r['matches_expectation'][0] for r in v)
    en = sum(r['matches_expectation'][1] for r in v)
    ik = sum(r['major_issues'][0] for r in v)
    i_n = sum(r['major_issues'][1] for r in v)
    return {
        'gt_0p05': {'k': k, 'n': n, 'share_pct': round(100 * k / n, 2), 'abstract_pct': m['NonZeroPercent'],
                    'n_matches_NumBaselines': n == m['NumBaselines'],
                    'match': abs(100 * k / n - m['NonZeroPercent']) <= 0.5},
        'per_environment_gt_0p05_above_70pct': all(r['gt_0p05_at_8h'][0] / r['gt_0p05_at_8h'][1] > 0.7 for r in v),
        'matches_expectation': {'k': ek, 'n': en, 'pooled_pct': round(100 * ek / en, 2),
                                'pooled_above_80pct': ek / en > 0.8,
                                'environments_at_or_below_80pct': [r['environment'] for r in v
                                                                   if r['matches_expectation'][0] / r['matches_expectation'][1] <= 0.8]},
        'major_issues': {'k': ik, 'n': i_n, 'pct': round(100 * ik / i_n, 2), 'above_5pct': ik / i_n > 0.05},
    }


def check_metr_baselines(paper, hb, tasks):
    """METR's released human rows (eval-analysis-public 52cb829) against the paper's validation table."""
    fam_by_name = {t['paper_name'].lower(): t['family'] for t in tasks.values()}
    out = []
    for suite in ('TH1.0', 'TH1.1'):
        rows = {r['task'].split('/')[0]: r for r in hb if r['suite'] == suite}
        for v in paper['v2']['validation']:
            r = rows.get(fam_by_name[v['environment'].lower()])
            if r is None:
                out.append({'suite': suite, 'environment': v['environment'], 'paper_runs': v['gt_0p05_at_8h'][1],
                            'released_runs': None, 'note': 'environment not in this suite'})
                continue
            out.append({'suite': suite, 'environment': v['environment'],
                        'paper_runs': v['gt_0p05_at_8h'][1], 'released_runs': int(r['runs']),
                        'paper_gt_0p05': v['gt_0p05_at_8h'][0], 'released_gt_0p05': int(r['gt_0p05']),
                        'same_counts': v['gt_0p05_at_8h'] == [int(r['gt_0p05']), int(r['runs'])]})
    n_released = {s: sum(int(r['runs']) for r in hb if r['suite'] == s) for s in ('TH1.0', 'TH1.1')}
    return {'per_environment': out, 'released_human_runs': n_released,
            'paper_human_runs': paper['v2']['macros']['NumBaselines']}


NOT_REPRODUCIBLE = [
    {'claim': 'best agents score 4x human experts at a 2-hour total budget (abstract; Fig. 1)',
     'value': '4x', 'status': 'not_reproducible',
     'why': "needs per-run score trajectories for agents and humans; the paper says 'Analysis code and anonymized "
            "human expert data coming soon', and no such release was found in METR's public repositories on 2026-10-25"},
    {'claim': 'humans narrowly exceed the top agent at 8 hours and reach 2x its score at 32 hours (abstract; Fig. 1)',
     'value': '2x', 'status': 'not_reproducible', 'why': 'as above'},
    {'claim': 'best 8-hour allocations of o1-preview (AIDE) and Claude 3.5 Sonnet (Modular) match the 36th and 37th '
              'percentile of human experts (Sec. 4.2)', 'value': '36, 37', 'status': 'not_reproducible', 'why': 'as above'},
    {'claim': '82% of expert attempts score above 0.05 and 24% match or exceed the reference (abstract)',
     'value': '82%, 24%', 'status': 'partly_checked',
     'why': "82% is compared with the paper's own validation table (see validation); 24% needs the human data"},
    {'claim': 'agents score 36.8 (AIDE) and 25.3 (Modular) times per hour against 3.4 for humans (Sec. 5.1)',
     'value': '36.8, 25.3, 3.4', 'status': 'not_reproducible', 'why': 'needs the run logs'},
    {'claim': 'about 29M input and 499K output tokens and about $123 per 8-hour agent run, against about $1,855 '
              'paid per human run (Sec. 6.2)', 'value': '$123, $1,855', 'status': 'not_reproducible', 'why': 'needs the run logs'},
]


def build():
    tasks, paper, hb = load()
    tr = check_transforms(tasks)
    ce = check_ceilings(tasks, paper)
    so = check_sourcing(paper)
    va = check_validation(paper)
    mb = check_metr_baselines(paper, hb, tasks)
    return {
        'description': 'RE-Bench released numbers recomputed from data/ (issue #58); see README.md',
        'readme_transforms': tr,
        'readme_transforms_all_match': all(x['match'] for x in tr),
        'ceiling_table': ce,
        'ceiling_matches': sum(x['match'] for x in ce), 'ceiling_rows': len(ce),
        'baseline_sourcing': so,
        'validation_table': va,
        'metr_released_human_baselines': mb,
        'paper_revision_changes': sorted(paper['changed_from_v1']),
        'not_reproducible': NOT_REPRODUCIBLE,
    }


def compare(new, ref, path='$'):
    if isinstance(ref, dict):
        assert isinstance(new, dict) and new.keys() == ref.keys(), f'{path}: keys differ'
        for k in ref:
            compare(new[k], ref[k], f'{path}.{k}')
    elif isinstance(ref, list):
        assert isinstance(new, list) and len(new) == len(ref), f'{path}: lengths differ'
        for i, (a, b) in enumerate(zip(new, ref)):
            compare(a, b, f'{path}[{i}]')
    elif isinstance(ref, bool) or not isinstance(ref, (int, float)):
        assert new == ref, f'{path}: {new!r} != {ref!r}'
    else:
        assert math.isclose(new, ref, rel_tol=1e-9, abs_tol=1e-12), f'{path}: {new!r} vs {ref!r}'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true', help='compare with the committed results/reproduction.json')
    a = ap.parse_args()
    res = build()
    if a.check:
        compare(json.loads(json.dumps(res)), json.loads(OUT.read_text()))
        print('reproduce: results/reproduction.json matches a fresh recomputation')
        return 0
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1) + '\n')
    print(f"reproduce: transforms {'all match' if res['readme_transforms_all_match'] else 'MISMATCH'}; "
          f"ceiling table {res['ceiling_matches']}/{res['ceiling_rows']} rows match; "
          f"sourcing text matches table: {res['baseline_sourcing']['text_matches_table']}; "
          f"82% vs validation table: {res['validation_table']['gt_0p05']['share_pct']}%")
    return 0


if __name__ == '__main__':
    sys.exit(main())
