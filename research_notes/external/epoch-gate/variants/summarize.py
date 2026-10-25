"""Reduce variant runs of the official GATE solver to a reviewed summary (issue #33). Stdlib only.

    python3 variants/summarize.py reduce <bundle-sha256> variants/summary.json <run.json>...
    python3 variants/summarize.py render [variants/summary.json]   # print RESULTS.md
    python3 variants/summarize.py check                             # RESULTS.md matches summary.json
    python3 variants/summarize.py compare <new-summary.json>         # fresh rerun vs committed summary

`reduce` reads one or more outputs of official/run_official.mjs for variants/jobs.json
and keeps, per job, optimizer diagnostics, the measures behind the conclusions, the
steps 0-20 trajectories of four variables, and the SHA-256 of the full trajectory.
`render` turns the summary into the verdict tables in RESULTS.md.

Verdict rule (the issue's stopping rule). A conclusion's predicate is evaluated for every
job. For a variant, if the predicate differs between its iteration caps, the verdict is
"not robust": it flips within the optimizer-noise band. Otherwise it is compared with
the default preset, which must itself agree across caps: same value "survives",
opposite value "flips". If the default disagrees across caps, no variant can be judged
against it ("not robust (baseline)").
"""
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUMMARY = HERE / 'summary.json'
RESULTS = HERE / 'RESULTS.md'
TRAJ_VARS = ['gwp', 'frac_automated', 'compute_investment', 'q_compute']
TRAJ_STEPS = 21  # steps 0-20
LEVEL_VARS = ['gwp', 'compute_investment']    # compared as |ln(a/b)|
SHARE_VARS = ['frac_automated', 'q_compute']  # compared as |a - b| (fraction points)
FAST_STEP = 9   # step t reports t+1 model years, so step 9 is "within 10 years"

CONCLUSIONS = [
    ('C1', 'Explosive growth: annual GWP growth reaches 30%/yr at some step.',
     lambda m: m['peak_gwp_growth'] >= 0.30),
    ('C2', 'Hyper-explosive growth: annual GWP growth reaches 100%/yr at some step.',
     lambda m: m['peak_gwp_growth'] >= 1.00),
    ('C3', 'Growth takes off before automation completes: GWP growth first reaches 30%/yr strictly '
           'before the automated fraction first reaches its maximum.',
     lambda m: m['first_step_growth_ge_30pct'] is not None and (
         m['first_step_f_at_max'] is None or m['first_step_growth_ge_30pct'] < m['first_step_f_at_max'])),
    ('C4', 'Fast automation: the automated fraction reaches its maximum within 10 model years (step <= 9).',
     lambda m: m['first_step_f_at_max'] is not None and m['first_step_f_at_max'] <= FAST_STEP),
    ('C5', 'Immediate compute build-out: the share of output invested in compute at step 0 is at least '
           '10 times the initial observed share I_Q(0)/Y(0).',
     lambda m: m['q_compute_0'] >= 10 * m['initial_compute_share']),
    ('C6', 'Compute build-out is transitional: by step 20 the compute share of output has fallen below '
           'half its peak over steps 0-20.',
     lambda m: m['q_compute_20'] < 0.5 * m['q_compute_peak_0_20']),
]


def first(pred, seq):
    return next((i for i, v in enumerate(seq) if pred(v)), None)


def measures(states, args):
    mp = args['modelParams']
    max_frac = max(b['max_frac'] for b in mp['beliefs']['max_frac_beliefs'])
    f = [s['frac_automated'] for s in states]
    y = [s['gwp'] for s in states]
    q = [s['q_compute'] for s in states]
    growth = [y[t + 1] / y[t] - 1 for t in range(len(y) - 1)]
    peak = max(range(len(growth)), key=lambda t: growth[t])
    qpk = max(range(TRAJ_STEPS), key=lambda t: q[t])
    return {
        'max_frac': max_frac,
        'initial_compute_share': mp['main']['compute_investment_init'] / mp['main']['gwp_init'],
        'peak_gwp_growth': growth[peak],
        'peak_gwp_growth_step': peak,
        'first_step_growth_ge_30pct': first(lambda v: v >= 0.30, growth),
        'first_step_f_ge_half_max': first(lambda v: v >= 0.5 * max_frac, f),
        'first_step_f_at_max': first(lambda v: v >= max_frac * (1 - 1e-9), f),
        'f_max_reached': max(f),
        'q_compute_0': q[0],
        'q_compute_peak_0_20': q[qpk],
        'q_compute_peak_step': qpk,
        'q_compute_20': q[20],
    }


def reduce_runs(run_paths, bundle_sha):
    spec_jobs = {j['name']: j for j in json.loads((HERE / 'jobs.json').read_text())}
    jobs, node = {}, set()
    for p in run_paths:
        run = json.loads(Path(p).read_text())
        node.add(run['node'])
        for r in run['results']:
            name = r['job']['name']
            if name not in spec_jobs:
                raise SystemExit(f'{name}: not in variants/jobs.json')
            if r['job'] != spec_jobs[name]:
                raise SystemExit(f'{name}: job differs from variants/jobs.json')
            rerun = r['rerun']
            wp = rerun['world_path']
            states = wp['states']
            objp = wp['objective_path']
            jobs[name] = {
                'name': name, 'variant': r['job']['variant'], 'cap': r['job']['cap'],
                'diagnostics': {
                    'objective': rerun['objective'],
                    'iterations': len(objp),
                    'stopped_at_maxiter': len(objp) >= r['args']['solverArgs']['maxiter'],
                    'rel_change_last_10_iterations': abs(objp[-1] - objp[-11]) / abs(objp[-11]),
                    'checks_pass': bool(rerun['check'] and rerun['simple_policy_check'] and rerun['spliced_utility_check']),
                },
                'measures': measures(states, r['args']),
                'trajectory_steps_0_20': {k: [states[t][k] for t in range(TRAJ_STEPS)] for k in TRAJ_VARS},
                'full_world_path_sha256': hashlib.sha256(
                    json.dumps(wp, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            }
    missing = sorted(set(spec_jobs) - set(jobs))
    if missing:
        raise SystemExit(f'missing jobs: {missing}')
    return {
        'about': ('Variant runs of Epoch\'s compiled GATE solver (pinned playground bundle), issue #33. '
                  'Source-model outputs, not observations. Generated by variants/summarize.py reduce; see README.md.'),
        'license_note': 'Model outputs of Epoch AI\'s GATE, reproduced with attribution (CC BY 4.0 per epoch.ai/gate).',
        'bundle_sha256': bundle_sha,
        'node': sorted(node),
        'jobs': [jobs[n] for n in spec_jobs],
    }


def compare(new, ref):
    """Errors between a fresh summary and the committed one. WebAssembly arithmetic is
    deterministic, so every full-trajectory hash must match."""
    errors = []
    if new['bundle_sha256'] != ref['bundle_sha256']:
        errors.append(f'bundle {new["bundle_sha256"]} != committed {ref["bundle_sha256"]}')
    nj = {j['name']: j for j in new['jobs']}
    for j in ref['jobs']:
        n = nj.get(j['name'])
        if n is None:
            errors.append(f'{j["name"]}: missing')
        elif n['full_world_path_sha256'] != j['full_world_path_sha256']:
            errors.append(f'{j["name"]}: full trajectory differs from the committed run')
    return errors


# ---------------------------------------------------------------- verdicts

def by_variant(summary):
    out = {}
    for j in summary['jobs']:
        out.setdefault(j['variant'], {})[j['cap']] = j
    return out


def judge(values, base_values):
    """values, base_values: predicate value per cap (lists of bool)."""
    if len(set(values)) > 1:
        return 'not robust'
    if len(set(base_values)) > 1:
        return 'not robust (baseline)'
    return 'survives' if values[0] == base_values[0] else 'flips'


def verdicts(summary):
    vs = by_variant(summary)
    caps = sorted(vs['default'])
    table = {}
    for cid, _, pred in CONCLUSIONS:
        base = [pred(vs['default'][c]['measures']) for c in caps]
        for v, jobs in vs.items():
            vals = [pred(jobs[c]['measures']) for c in caps]
            if v == 'default':
                verdict = ('holds' if base[0] else 'fails') if len(set(base)) == 1 else 'not robust'
            else:
                verdict = judge(vals, base)
            table[(v, cid)] = {'values': vals, 'verdict': verdict}
    return caps, table


def distances(a, b):
    """(levels, shares): max |ln(a/b)| over LEVEL_VARS and max |a - b| over SHARE_VARS, steps 0-20.
    Shares are compared in absolute terms because late-run shares near zero make relative
    differences meaningless (0.0002 against 0.0001 is a factor of two and economically nothing)."""
    lv = max(abs(math.log(x / y)) for k in LEVEL_VARS for x, y in zip(a[k], b[k]))
    sh = max(abs(x - y) for k in SHARE_VARS for x, y in zip(a[k], b[k]))
    return lv, sh


def noise_and_sensitivity(summary):
    """Per variant: optimizer noise = largest distance (see distances) between any lower cap and
    the highest cap of the same variant; sensitivity = the distance between the variant and the
    default preset, both at the highest cap."""
    vs = by_variant(summary)
    top = max(vs['default'])
    out = {}
    for v, jobs in vs.items():
        ref = jobs[top]['trajectory_steps_0_20']
        ds = [distances(jobs[c]['trajectory_steps_0_20'], ref) for c in jobs if c != top]
        noise = (max(d[0] for d in ds), max(d[1] for d in ds))
        sens = distances(ref, vs['default'][top]['trajectory_steps_0_20'])
        out[v] = (noise, sens)
    return out


# ---------------------------------------------------------------- rendering

SHORT = {'survives': 'survives', 'flips': '**flips**', 'not robust': '*not robust*',
         'not robust (baseline)': '*not robust (baseline)*', 'holds': 'holds', 'fails': 'fails'}


def fmt_steps(vals):
    vals = ['never' if v is None else str(v) for v in vals]
    return vals[0] if len(set(vals)) == 1 else ' / '.join(vals)


def render(summary):
    spec = json.loads((HERE / 'spec.json').read_text())
    labels = {v['name']: (v['group'], v['label']) for v in spec['variants']}
    caps, table = verdicts(summary)
    vs = by_variant(summary)
    ns = noise_and_sensitivity(summary)
    capstr = ' / '.join(str(c) for c in caps)
    L = []
    L.append('# GATE variants: do the qualitative conclusions survive? (issue #33)')
    L.append('')
    L.append('Generated by `python3 variants/summarize.py render` from `variants/summary.json`; do not edit by hand.')
    L.append('[[ai gen]] Source-model outputs of the pinned official solver (bundle '
             f'`{summary["bundle_sha256"][:12]}...`, Node {", ".join(summary["node"])}). Not observations, not forecasts.')
    L.append('')
    L.append(f'Every variant was run at optimizer iteration caps {capstr}. Verdict rule: if a conclusion\'s '
             'predicate differs between a variant\'s caps it is *not robust* (it flips inside the '
             'optimizer-noise band); otherwise it **survives** or **flips** relative to the default preset.')
    L.append('')
    L.append('## Conclusions tested')
    L.append('')
    for cid, text, _ in CONCLUSIONS:
        L.append(f'- **{cid}.** {text}')
    L.append('')
    L.append('## Verdicts')
    L.append('')
    ids = [c[0] for c in CONCLUSIONS]
    L.append('| variant | group | ' + ' | '.join(ids) + ' |')
    L.append('|---|---|' + '---|' * len(ids))
    for v in vs:
        L.append(f'| `{v}` | {labels[v][0]} | ' + ' | '.join(SHORT[table[(v, c)]['verdict']] for c in ids) + ' |')
    L.append('')
    counts = {}
    for (v, c), r in table.items():
        if v != 'default':
            counts.setdefault(c, {}).setdefault(r['verdict'], 0)
            counts[c][r['verdict']] += 1
    for c in ids:
        L.append(f'- {c}: ' + ', '.join(f'{k} {n}' for k, n in sorted(counts[c].items())))
    L.append('')
    L.append(f'## Measures behind the verdicts (caps {capstr}; one value when all caps agree)')
    L.append('')
    L.append('Steps index model years after the initial state (step t is t+1 years). "f max" is the '
             'variant\'s maximum automatable fraction.')
    L.append('')
    L.append('| variant | f max | f >= half max | f at max | growth >= 30% | peak growth %/yr (step) | '
             'q_compute step 0 | q_compute peak 0-20 (step) | q_compute step 20 |')
    L.append('|---|---|---|---|---|---|---|---|---|')
    for v, jobs in vs.items():
        m = [jobs[c]['measures'] for c in caps]
        peak = ' / '.join(f'{x["peak_gwp_growth"] * 100:.0f} ({x["peak_gwp_growth_step"]})' for x in m)
        L.append(f'| `{v}` | {m[0]["max_frac"]:g} | {fmt_steps([x["first_step_f_ge_half_max"] for x in m])} | '
                 f'{fmt_steps([x["first_step_f_at_max"] for x in m])} | {fmt_steps([x["first_step_growth_ge_30pct"] for x in m])} | '
                 f'{peak} | ' + ' / '.join(f'{x["q_compute_0"]:.3f}' for x in m) + ' | '
                 + ' / '.join(f'{x["q_compute_peak_0_20"]:.3f} ({x["q_compute_peak_step"]})' for x in m) + ' | '
                 + ' / '.join(f'{x["q_compute_20"]:.4f}' for x in m) + ' |')
    L.append('')
    L.append(f'Initial observed compute share I_Q(0)/Y(0) = {vs["default"][caps[0]]["measures"]["initial_compute_share"]:.5f} '
             '(C5 threshold is 10 times this).')
    L.append('')
    L.append('## Optimizer noise versus sensitivity')
    L.append('')
    L.append(f'Distances over steps 0-20. *Levels*: largest |ln(a/b)| in {" and ".join(LEVEL_VARS)} (0.1 is about 10%). '
             f'*Shares*: largest absolute difference in {" and ".join(SHARE_VARS)} (fraction points). *Noise*: between '
             f'each lower cap and cap {caps[-1]} of the same variant. *Sensitivity*: between the variant and the default '
             f'preset, both at cap {caps[-1]}. A ratio near or below 1 means the trajectory change cannot be told apart '
             'from optimizer noise, whatever the milestones say.')
    L.append('')
    L.append('| variant | levels: noise | levels: sensitivity | ratio | shares: noise | shares: sensitivity | ratio |')
    L.append('|---|---|---|---|---|---|---|')

    def ratio(s, n):
        return f'{s / n:.1f}' if n > 0 else 'inf'
    for v, ((nl, nsh), (sl, ssh)) in ns.items():
        if v == 'default':
            L.append(f'| `{v}` | {nl:.3f} | - | - | {nsh:.4f} | - | - |')
        else:
            L.append(f'| `{v}` | {nl:.3f} | {sl:.3f} | {ratio(sl, nl)} | {nsh:.4f} | {ssh:.4f} | {ratio(ssh, nsh)} |')
    L.append('')
    L.append('## Optimizer diagnostics')
    L.append('')
    L.append('| variant | objective by cap | stopped at cap | rel. objective change over last 10 iterations | solver checks pass |')
    L.append('|---|---|---|---|---|')
    for v, jobs in vs.items():
        d = [jobs[c]['diagnostics'] for c in caps]
        L.append(f'| `{v}` | ' + ' / '.join(f'{x["objective"]:.6f}' for x in d) + ' | '
                 + ' / '.join('yes' if x['stopped_at_maxiter'] else 'no' for x in d) + ' | '
                 + ' / '.join(f'{x["rel_change_last_10_iterations"]:.1e}' for x in d) + ' | '
                 + ' / '.join('yes' if x['checks_pass'] else 'NO' for x in d) + ' |')
    L.append('')
    return '\n'.join(L)


def main(argv):
    if argv[:1] == ['reduce']:
        bundle_sha, out = argv[1], Path(argv[2])
        s = reduce_runs(argv[3:], bundle_sha)
        out.write_text(json.dumps(s, indent=None, separators=(',', ':')).replace('{"name"', '\n{"name"') + '\n')
        print(f'wrote {out} ({len(s["jobs"])} jobs)')
    elif argv[:1] == ['render']:
        path = Path(argv[1]) if len(argv) > 1 else SUMMARY
        sys.stdout.write(render(json.loads(path.read_text())))
    elif argv[:1] == ['compare']:
        errors = compare(json.loads(Path(argv[1]).read_text()), json.loads(SUMMARY.read_text()))
        print('\n'.join(errors) or 'every job bit-identical to variants/summary.json (full trajectory hash)')
        if errors:
            sys.exit(1)
    elif argv[:1] == ['check']:
        if RESULTS.read_text() != render(json.loads(SUMMARY.read_text())):
            sys.exit('variants/RESULTS.md does not match variants/summary.json')
        print('variants/RESULTS.md matches variants/summary.json')
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
