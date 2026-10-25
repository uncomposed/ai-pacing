"""Keep all 80 rows of the official presets' decisions and key states (stdlib only).

    python3 independent/extract_full.py <run.json> data/baseline_target.json independent/data/official_full.json

<run.json> is an official/run_official.mjs output holding the unmodified presets. The committed
baseline target keeps only steps 0-20 and a few later ones; replaying the official decisions
through the independent model (tests/test_independent.py) and evaluating the objective need every
row. Provenance: each preset's world_path must hash to the `full_world_path_sha256` recorded in
the baseline target, so this file can only come from the same pinned solver run.
"""
import hashlib
import json
import sys

KEYS = ['q_consumption', 'q_capital', 'q_compute', 'q_hardware_rnd', 'q_software_rnd', 'q_training_compute',
        'gwp', 'consumption', 'capital', 'frac_automated', 'compute', 'training_compute', 'runtime_compute',
        'best_training_run', 'hardware', 'software', 'effective_compute_investment', 'cognitive_ces_term',
        'labor_share', 'runtime_compute_share']


def main(run_path, target_path, out_path):
    run = json.load(open(run_path))
    target = {j['name']: j for j in json.load(open(target_path))['jobs']}
    out = {'about': ('[[ai gen]] All 80 rows of selected fields of the official GATE presets, rerun under Node from '
                     'the pinned bundle; produced by independent/extract_full.py. Source-model outputs, not observations.'),
           'license_note': 'Model outputs of Epoch AI\'s GATE, reproduced with attribution (CC BY 4.0 per epoch.ai/gate).',
           'node': run['node'],
           'presets': {}}
    for r in run['results']:
        job = r['job']
        if job.get('modelParams') or job.get('solverArgs'):
            continue
        name = job['name']
        wp = r['rerun']['world_path']
        sha = hashlib.sha256(json.dumps(wp, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        if sha != target[name]['full_world_path_sha256']:
            sys.exit(f'{name}: world_path hash {sha} differs from the baseline target; not the pinned run')
        out['presets'][name] = {
            'full_world_path_sha256': sha,
            'objective': r['rerun']['objective'],
            'utility': r['rerun']['utility'],
            'rows': {k: [s[k] for s in wp['states']] for k in KEYS},
        }
    with open(out_path, 'w') as fh:
        json.dump(out, fh, separators=(',', ':'))
        fh.write('\n')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
