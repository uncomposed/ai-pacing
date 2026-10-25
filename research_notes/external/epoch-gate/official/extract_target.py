"""Reduce a run_official.mjs output to the committed baseline target (stdlib only).

    python3 official/extract_target.py <run.json> <bundle-sha256> data/baseline_target.json

Keeps, per job: the arguments, optimizer diagnostics, milestones, a subset of the
trajectory in native units, the SHA-256 of the full trajectory as serialized, and,
for unmodified presets, how the rerun compares with the playground's cached run.
"""
import hashlib
import json
import sys

STEPS = list(range(0, 21)) + [25, 30, 40, 50, 60, 79]
PRESET_VARS = [
    'gwp', 'consumption', 'capital', 'labor', 'frac_automated',
    'compute', 'training_compute', 'runtime_compute', 'best_training_run', 'physical_best_training_run',
    'hardware', 'software', 'compute_investment', 'effective_compute_investment', 'cognitive_ces_term', 'capital_share',
    'q_consumption', 'q_capital', 'q_compute', 'q_hardware_rnd', 'q_software_rnd',
    'q_training_compute', 'q_runtime_compute',
]
VARIANT_VARS = ['gwp', 'frac_automated', 'compute', 'compute_investment', 'q_compute', 'q_consumption']
DIAG_KEYS = ['objective', 'utility', 'simple_objective', 'spliced_objective',
             'check', 'simple_policy_check', 'spliced_utility_check']


def milestones(states):
    f = [s['frac_automated'] for s in states]
    y = [s['gwp'] for s in states]
    growth = [y[t + 1] / y[t] - 1 for t in range(len(y) - 1)]

    def first(pred, seq):
        return next((i for i, v in enumerate(seq) if pred(v)), None)

    peak = max(range(len(growth)), key=lambda t: growth[t])
    return {
        'first_step_frac_automated_ge_0.5': first(lambda v: v >= 0.5, f),
        'first_step_frac_automated_ge_0.9': first(lambda v: v >= 0.9, f),
        'first_step_frac_automated_eq_1': first(lambda v: v >= 1.0, f),
        'first_step_gwp_growth_ge_30pct': first(lambda v: v >= 0.30, growth),
        'peak_gwp_growth': growth[peak],
        'peak_gwp_growth_step': peak,
        'gwp_ratio_last_to_first': y[-1] / y[0],
    }


def cached_vs_rerun(cached, rerun):
    worst, where, n = 0.0, None, 0
    for k in ('utility', 'objective', 'simple_objective', 'spliced_objective'):
        a, b = cached[k], rerun[k]
        e = 0.0 if a == b else abs(a - b) / abs(a)
        n += 1
        if e > worst:
            worst, where = e, k
    flags_equal = all(cached[k] == rerun[k] for k in ('check', 'simple_policy_check', 'spliced_utility_check'))
    cs, rs = cached['world_path']['states'], rerun['world_path']['states']
    only_cached = sorted(set(cs[0]) - set(rs[0]))
    only_rerun = sorted(set(rs[0]) - set(cs[0]))
    for t, (x, y) in enumerate(zip(cs, rs)):
        for k in set(x) & set(y):
            if isinstance(x[k], list):
                vals = zip(x[k], y[k])
            else:
                vals = [(x[k], y[k])]
            for a, b in vals:
                n += 1
                e = 0.0 if a == b else abs(a - b) / max(abs(a), 1e-300)
                if e > worst:
                    worst, where = e, f'step {t} {k}'
    op = cached['world_path']['objective_path'] == rerun['world_path']['objective_path']
    return {
        'values_compared': n, 'max_rel_diff': worst, 'max_at': where,
        'objective_path_identical': op, 'check_flags_identical': flags_equal,
        'same_number_of_steps': len(cs) == len(rs),
        'fields_only_in_cached': only_cached, 'fields_only_in_rerun': only_rerun,
    }


def main(run_path, bundle_sha, out_path):
    run = json.load(open(run_path))
    jobs = []
    for r in run['results']:
        job, rerun = r['job'], r['rerun']
        wp = rerun['world_path']
        states = wp['states']
        unmodified = r['cached'] is not None
        keep = PRESET_VARS if unmodified else VARIANT_VARS
        full = json.dumps(wp, sort_keys=True, separators=(',', ':'))
        objp = wp['objective_path']
        entry = {
            'name': job['name'],
            'job': job,
            'args': r['args'],
            'diagnostics': {
                **{k: rerun[k] for k in DIAG_KEYS},
                'iterations': len(objp),
                'maxiter': r['args']['solverArgs']['maxiter'],
                'stopped_at_maxiter': len(objp) >= r['args']['solverArgs']['maxiter'],
                'objective_path': objp,
                'rel_change_last_10_iterations': abs(objp[-1] - objp[-11]) / abs(objp[-11]) if len(objp) > 10 else None,
            },
            'automation_schedule_x': wp['automation_schedule_x'],
            'automation_schedule_y': wp['automation_schedule_y'],
            'milestones': milestones(states),
            'steps': STEPS,
            'trajectory': {k: [states[t][k] for t in STEPS] for k in keep},
            'full_world_path_sha256': hashlib.sha256(full.encode()).hexdigest(),
            'n_steps': len(states),
        }
        if unmodified:
            entry['cached_vs_rerun'] = cached_vs_rerun(r['cached'], rerun)
        jobs.append(entry)
    out = {
        'about': ('GATE baseline target: outputs of Epoch\'s compiled GATE solver (playground bundle '
                  'https://epoch.ai/generated/gate.js) rerun under Node. Source-model outputs, not observations. '
                  'Generated by official/extract_target.py; see README.md.'),
        'license_note': 'Model outputs of Epoch AI\'s GATE, reproduced with attribution (Epoch AI; CC BY 4.0 per epoch.ai/gate). See SOURCES.yaml.',
        'bundle_sha256': bundle_sha,
        'node': run['node'],
        'step_note': 'Index t of the solver output. labor[t] = L0*exp(g_L*(t+1)) exactly, so index t reports the state after t+1 model years (see README).',
        'jobs': jobs,
    }
    with open(out_path, 'w') as fh:
        json.dump(out, fh, indent=1)
        fh.write('\n')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
