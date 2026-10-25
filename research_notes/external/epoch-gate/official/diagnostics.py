"""Optimizer and sensitivity diagnostics from the committed baseline target (stdlib only).

    python3 official/diagnostics.py [data/baseline_target.json]

Prints, for each variant of the default preset, the largest relative difference from
the default run on the shared trajectory variables over steps 0-20, and the milestone
changes. Used to write README.md section "Convergence and sensitivity"; no solving.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def max_rel_diff(a, b, steps, upto=20):
    worst, where = 0.0, None
    for k in a:
        if k not in b:
            continue
        for i, t in enumerate(steps):
            if t > upto:
                break
            x, y = a[k][i], b[k][i]
            e = 0.0 if x == y else abs(x - y) / max(abs(x), 1e-300)
            if e > worst:
                worst, where = e, (t, k)
    return worst, where


def report(target):
    jobs = {j['name']: j for j in target['jobs']}
    base = jobs['default']
    lines = []
    for name, j in jobs.items():
        if j['job']['preset'] != 0 or name == 'default':
            continue
        w, at = max_rel_diff(base['trajectory'], j['trajectory'], base['steps'])
        dm = {k: (base['milestones'][k], v) for k, v in j['milestones'].items() if base['milestones'][k] != v and 'step' in k}
        lines.append(f'{name}: objective {j["diagnostics"]["objective"]:.6f} (default {base["diagnostics"]["objective"]:.6f}); '
                     f'max rel diff steps 0-20 {w:.3g} at {at}; milestone changes (default, variant) {dm}')
    return '\n'.join(lines)


if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'data' / 'baseline_target.json'
    print(report(json.load(open(path))))
