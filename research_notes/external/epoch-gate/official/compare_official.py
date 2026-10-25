"""Compare a fresh run of the official solver with the committed baseline target.

    python3 official/compare_official.py <run.json> [data/baseline_target.json]

Rebuilds the target from <run.json> (same reduction as extract_target.py) and compares
it with the committed one. Pass criteria, per job:
  * full_world_path_sha256 identical (the whole trajectory, every variable and step), or,
    if not, every committed trajectory value and diagnostic within RTOL;
  * milestones and check flags identical;
  * for unmodified presets, the rerun equals the playground's cached run (max_rel_diff 0).
Exit status 1 on any failure; the report lists every difference.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_target  # noqa: E402

RTOL = 1e-12  # wasm arithmetic is IEEE-754 deterministic; any drift is a finding


def rel(a, b):
    return 0.0 if a == b else abs(a - b) / max(abs(a), abs(b), 1e-300)


def compare(new, ref):
    errors, notes = [], []
    if new['bundle_sha256'] != ref['bundle_sha256']:
        errors.append(f'bundle hash {new["bundle_sha256"]} != committed {ref["bundle_sha256"]}')
    nj = {j['name']: j for j in new['jobs']}
    for rj in ref['jobs']:
        name = rj['name']
        j = nj.get(name)
        if j is None:
            errors.append(f'{name}: missing from new run')
            continue
        if j['full_world_path_sha256'] == rj['full_world_path_sha256']:
            notes.append(f'{name}: full trajectory bit-identical')
        else:
            notes.append(f'{name}: full trajectory hash differs; comparing committed subset with rtol {RTOL}')
            for k, vals in rj['trajectory'].items():
                for t, a, b in zip(rj['steps'], vals, j['trajectory'][k]):
                    if rel(a, b) > RTOL:
                        errors.append(f'{name}: {k} at step {t}: {b!r} vs committed {a!r}')
        for k in ('objective', 'utility', 'simple_objective', 'spliced_objective'):
            if rel(j['diagnostics'][k], rj['diagnostics'][k]) > RTOL:
                errors.append(f'{name}: {k} {j["diagnostics"][k]!r} vs committed {rj["diagnostics"][k]!r}')
        for k in ('check', 'simple_policy_check', 'spliced_utility_check'):
            if j['diagnostics'][k] != rj['diagnostics'][k]:
                errors.append(f'{name}: {k} changed')
        for k, v in rj['milestones'].items():
            if isinstance(v, float) and isinstance(j['milestones'][k], float):
                if rel(v, j['milestones'][k]) > RTOL:
                    errors.append(f'{name}: milestone {k} {j["milestones"][k]!r} vs {v!r}')
            elif j['milestones'][k] != v:
                errors.append(f'{name}: milestone {k} {j["milestones"][k]!r} vs {v!r}')
        if 'cached_vs_rerun' in j and j['cached_vs_rerun']['max_rel_diff'] != 0.0:
            errors.append(f'{name}: rerun differs from the playground cache: {j["cached_vs_rerun"]}')
    return errors, notes


def main(run_path, target_path):
    ref = json.load(open(target_path))
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / 'target.json'
        extract_target.main(run_path, ref['bundle_sha256'], str(out))
        new = json.load(open(out))
    errors, notes = compare(new, ref)
    print('\n'.join(notes))
    if errors:
        print(f'{len(errors)} difference(s):')
        print('\n'.join(errors))
        return 1
    print(f'OK: {len(ref["jobs"])} jobs match the committed baseline target')
    return 0


if __name__ == '__main__':
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    here = Path(__file__).resolve().parent.parent
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else str(here / 'data' / 'baseline_target.json')))
