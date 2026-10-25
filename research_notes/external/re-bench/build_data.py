#!/usr/bin/env python3
"""Build data/ from the pinned RE-Bench sources in the fetch_sources.sh cache (issue #58). [[ai gen]]

    python3 build_data.py --cache .upstream/files --out data

Reads only released material; runs no task and no model. Writes:
  data/task_scores.csv     per environment: version, starting and reference scores and raw values from the
                           RE-Bench READMEs, and the score transform found in the scoring code
  data/paper_values.json   numbers transcribed by regex from the paper's LaTeX source (arXiv v1 and v2)
  data/human_baselines.csv per suite and environment: METR's released human 8-hour baseline rows
  data/fixed_budget.csv    per suite and agent: mean normalized score of single runs against the human
                           8-hour baselines on the same environments, from METR's released runs
  data/run_dates.json      first and last agent run start per suite (for the evidence records)
Pure standard library, so it runs in any Python 3.10+.
"""
import argparse
import csv
import datetime as dt
import json
import math
import random
import re
import statistics
from collections import defaultdict
from pathlib import Path

FAMILIES = ['ai_rd_fix_embedding', 'ai_rd_nanogpt_chat_rl', 'ai_rd_optimize_llm_foundry', 'ai_rd_restricted_mlm',
            'ai_rd_rust_codecontests_inference', 'ai_rd_small_scaling_law', 'ai_rd_triton_cumsum']
# Paper environment names (Table 1) for each family.
PAPER_NAME = {
    'ai_rd_fix_embedding': 'Fix Embedding',
    'ai_rd_nanogpt_chat_rl': 'Finetune GPT-2 for QA',
    'ai_rd_optimize_llm_foundry': 'Optimize LLM Foundry',
    'ai_rd_restricted_mlm': 'Restricted Architecture MLM',
    'ai_rd_rust_codecontests_inference': 'Scaffolding for Rust Codecontests',
    'ai_rd_small_scaling_law': 'Scaling Law Experiment',
    'ai_rd_triton_cumsum': 'Optimize a Kernel',
}
# Score transform, as a regex that must match the scoring code, and the raw quantity it takes.
TRANSFORMS = {
    'ai_rd_fix_embedding': ('assets/score.py', r'math\.log\(loss - 1\.5\)', 'log(loss - 1.5)', 'loss'),
    'ai_rd_restricted_mlm': ('assets/score.py', r'math\.log\(loss - 1\.5\)', 'log(loss - 1.5)', 'loss'),
    'ai_rd_optimize_llm_foundry': ('assets/score.py', r'math\.log\(exec_time\)', 'log(seconds)', 'execution time (s)'),
    'ai_rd_triton_cumsum': ('assets/score.py', r'math\.log\(solution_time \* 1000\)', 'log(milliseconds)', 'execution time (ms)'),
    'ai_rd_small_scaling_law': ('ai_rd_small_scaling_law.py', r'score = 1 - distance', '1 - distance', ''),
    'ai_rd_nanogpt_chat_rl': (None, None, 'win rate (as reported)', ''),
    'ai_rd_rust_codecontests_inference': (None, None, 'share solved (as reported)', ''),
}
BOOT_REPS = 2000
BOOT_SEED = 20261025


def task_scores(rb):
    rows = []
    for fam in FAMILIES:
        text = (rb / fam / 'README.md').read_text()
        version = re.search(r'Version: `([0-9.]+)`', text).group(1)
        start = re.search(r'Starting score: ([0-9.]+)(?: \(\w[\w ]*: ([0-9.]+)\s*(?:seconds|ms)?\))?', text)
        ref = re.search(r'Official solution score: ([0-9.]+)(?: \(\w[\w ]*: ([0-9.]+)\s*(?:seconds|ms)?\))?', text)
        path, pattern, transform, raw_unit = TRANSFORMS[fam]
        if path is not None:
            code = (rb / fam / path).read_text()
            if not re.search(pattern, code):
                raise SystemExit(f'{fam}: score transform {transform!r} not found in {path}')
        rows.append({
            'family': fam, 'paper_name': PAPER_NAME[fam], 'version': version,
            'start_score': start.group(1), 'start_raw': start.group(2) or '',
            'reference_score': ref.group(1), 'reference_raw': ref.group(2) or '',
            'raw_unit': raw_unit, 'score_transform': transform,
            'transform_source': f'{fam}/{path}' if path else 'not in the released code (README statement only)',
        })
    return rows


def table_rows(tex, label):
    """Data rows (cells split on &) of the tabular holding \\label{label}."""
    end = tex.index('\\label{' + label + '}')
    begin = tex.rfind('\\begin{table', 0, end)
    body = tex[begin:end]
    body = body[body.index('\\midrule'):body.index('\\bottomrule')]
    out = []
    for line in body.split('\\\\'):
        line = line.replace('\\midrule', '').strip()
        if '&' in line:
            out.append([c.strip() for c in line.split('&')])
    return out


def num(cell):
    return float(re.sub(r'[^0-9.]', '', cell))


def frac(cell):
    a, b = cell.split('/')
    return [int(a), int(b)]


def paper_values(tex):
    macros = dict(re.findall(r'\\newcommand\{\\(\w+)\}\{([^}%]*?)(?:\\texttimes\{\})?\}', tex))
    keep = ['NumBaselines', 'NumBaseliners', 'NonZeroPercent', 'ReferencePercent', 'AIDEScorePerHour',
            'ModularScorePerHour', 'HumanScorePerHour', 'OPreviewPercentile', 'SonnetPercentile',
            'AgentMultipleHumanScoreAtTwoHours', 'HumanMultipleAgentScoreAtMaxHours', 'HumanMultipleGPUs']
    v = {'macros': {k: float(macros[k]) for k in keep}}
    v['baseline_sourcing'] = [{'source': r[0], 'baseliners': int(r[1]), 'runs': int(r[2]), 'avg_score': float(r[3])}
                              for r in table_rows(tex, 'table:baseline-sourcing')]
    m = re.search(r'professional networks scoring \$([0-9.]+)\$ normalized score on average, while hiring applicants '
                  r'only achieved an average of \$([0-9.]+)\$', tex)
    v['baseline_sourcing_text'] = {'professional_network': float(m.group(1)), 'hiring': float(m.group(2))}
    v['validation'] = [{'environment': r[0], 'gt_0p05_at_8h': frac(r[1]), 'matches_expectation': frac(r[2]),
                        'start_score_sd': float(r[3]), 'major_issues': frac(r[4])}
                       for r in table_rows(tex, 'table:validation_metrics')]
    ceil = []
    for r in table_rows(tex, 'table:ceiling_estimates'):
        raw = [num(x) for x in r[1].split('--')]
        unit = 'ms' if 'ms' in r[1] else 's' if r[1].endswith(' s') else '%' if '%' in r[1] else ''
        ceil.append({'environment': r[0], 'raw': raw, 'raw_unit': unit,
                     'normalized': [float(x) for x in r[2].split('--')], 'best_achieved': float(r[3])})
    v['ceiling'] = ceil
    v['env_metrics_loc'] = {r[0]: int(r[2].replace(',', '')) for r in table_rows(tex, 'table:env_metrics')}
    m = re.search(r'\\textasciitilde\{\}([0-9]+)M input tokens and \\textasciitilde\{\}([0-9]+)K output tokens in each '
                  r'8-hour run, at a cost of approximately \\\$([0-9]+)\. This is only a small fraction of the '
                  r'approximately \\\$([0-9,]+)', tex)
    v['cost'] = {'agent_input_tokens_M': int(m.group(1)), 'agent_output_tokens_K': int(m.group(2)),
                 'agent_usd_per_8h_run': int(m.group(3)), 'human_usd_paid_avg': int(m.group(4).replace(',', ''))}
    return v


def load_runs(path):
    return [r for r in map(json.loads, path.read_text().splitlines()) if r['task_source'] == 'RE-Bench']


def release_dates(path):
    out = {}
    for line in path.read_text().splitlines():
        if line.startswith('  ') and ': ' in line:
            name, date = line.strip().rsplit(': ', 1)
            out[name] = date
    return out


def task_mean(runs, tasks):
    by = defaultdict(list)
    for r in runs:
        by[r['task_id']].append(r['score_cont'])
    return statistics.fmean(statistics.fmean(by[t]) for t in tasks), by


def stratified_ci(by, tasks, rng):
    reps = []
    for _ in range(BOOT_REPS):
        reps.append(statistics.fmean(statistics.fmean(rng.choices(by[t], k=len(by[t]))) for t in tasks))
    reps.sort()
    return reps[int(0.025 * BOOT_REPS)], reps[int(0.975 * BOOT_REPS) - 1]


def fixed_budget(suite, runs, dates):
    human = [r for r in runs if r['alias'] == 'human']
    human_tasks = sorted({r['task_id'] for r in human})
    hb = []
    for t in human_tasks:
        s = [r['score_cont'] for r in human if r['task_id'] == t]
        hb.append({'suite': suite, 'task': t, 'runs': len(s), 'gt_0p05': sum(x > 0.05 for x in s),
                   'at_or_above_reference': sum(x >= 1 for x in s), 'mean_score': round(statistics.fmean(s), 6)})
    rows = []
    rng = random.Random(BOOT_SEED)
    for agent in sorted({r['alias'] for r in runs} - {'human'}):
        ar = [r for r in runs if r['alias'] == agent]
        if any(r['time_limit'] in (None, 0.0) for r in ar):
            continue  # GPT-2 rows carry no run at all (placeholder zeros)
        tasks = sorted({r['task_id'] for r in ar} & set(human_tasks))
        mean, by = task_mean(ar, tasks)
        lo, hi = stratified_ci(by, tasks, rng)
        hmean, _ = task_mean(human, tasks)
        rows.append({
            'suite': suite, 'agent': agent, 'release_date': dates.get(agent, dates.get(agent.replace(' (Inspect)', ''), '')),
            'scaffold': ';'.join(sorted({str(r['scaffold']) for r in ar})),
            'time_limit_s': ';'.join(sorted({str(int(r['time_limit'])) for r in ar})),
            'runs': len(ar), 'tasks': len(tasks),
            'mean_score': round(mean, 6), 'ci95_low': round(lo, 6), 'ci95_high': round(hi, 6),
            'share_at_or_above_reference': round(statistics.fmean(r['score_cont'] >= 1 for r in ar), 6),
            'human_mean_same_tasks': round(hmean, 6), 'ratio_to_human': round(mean / hmean, 6),
        })
    starts = [r['started_at'] for r in runs if r['alias'] != 'human' and r.get('started_at')]
    span = [dt.datetime.fromtimestamp(x / 1000, dt.timezone.utc).date().isoformat() for x in (min(starts), max(starts))]
    return hb, rows, span


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cache', type=Path, default=Path(__file__).parent / '.upstream/files')
    ap.add_argument('--out', type=Path, default=Path(__file__).parent / 'data')
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    write_csv(a.out / 'task_scores.csv', task_scores(a.cache / 're-bench'))
    v1 = paper_values((a.cache / 'arxiv/v1/report.tex').read_text())
    v2 = paper_values((a.cache / 'arxiv/v2/report.tex').read_text())
    changed = sorted(k for k in v2 if v1[k] != v2[k])
    (a.out / 'paper_values.json').write_text(json.dumps(
        {'source': 'arXiv:2411.15114 LaTeX source, report.tex; v2 values, v1 differences listed',
         'v2': v2, 'changed_from_v1': {k: v1[k] for k in changed}}, indent=1) + '\n')
    dates = release_dates(a.cache / 'metr/release_dates.yaml')
    hb_all, fb_all, spans = [], [], {}
    for suite, f in [('TH1.0', 'th10_runs.jsonl'), ('TH1.1', 'th11_runs.jsonl')]:
        hb, fb, span = fixed_budget(suite, load_runs(a.cache / 'metr' / f), dates)
        hb_all += hb
        fb_all += fb
        spans[suite] = span
    write_csv(a.out / 'human_baselines.csv', hb_all)
    write_csv(a.out / 'fixed_budget.csv', fb_all)
    (a.out / 'run_dates.json').write_text(json.dumps({'agent_run_start_utc': spans}, indent=1) + '\n')
    print(f'build_data: wrote {a.out}/task_scores.csv, paper_values.json, human_baselines.csv, fixed_budget.csv, run_dates.json')


if __name__ == '__main__':
    main()
