"""Independent re-solve of the GATE planner problem with scipy (issue #34).

[[ai gen]] NOT the official solver. Maximises the reconstructed objective (gate_indep.Model) over
the planner's decisions for every year of the optimisation horizon (2 x 80 = 160 years), using
L-BFGS-B with exact gradients from autograd. Decisions are parametrised without constraints:
output shares = softmax of 5 logits, training share of compute = logistic of 1 logit.

It starts from a neutral guess (constant shares), not from the official solution, so agreement
with the official trajectory is a test, not an input. Needs scipy and autograd (not part of
`make check`; run by the epoch-gate-resolve workflow or by hand):

    python resolve.py --preset default --out resolve_default.json
    python resolve.py --compare ../data/baseline_target.json resolve_default.json

Long: several minutes per preset.
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as onp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gate_indep as gi  # noqa: E402

# Neutral start: shares of output (consumption, capital, compute, HW R&D, SW R&D), training share.
NEUTRAL = (0.75, 0.15, 0.05, 0.025, 0.025, 0.5)
COMPARE_KEYS = ('gwp', 'consumption', 'capital', 'frac_automated', 'compute', 'training_compute',
                'runtime_compute', 'best_training_run', 'hardware', 'software', 'compute_investment',
                'effective_compute_investment', 'cognitive_ces_term',
                'q_consumption', 'q_capital', 'q_compute', 'q_hardware_rnd', 'q_software_rnd',
                'q_training_compute')


def decisions(xp, z):
    """z: (H, 6) unconstrained -> list of per-year decision tuples."""
    zs = z[:, :5]
    zs = zs - xp.max(zs, axis=1, keepdims=True)
    ex = xp.exp(zs)
    shares = ex / xp.sum(ex, axis=1, keepdims=True)
    train = 1.0 / (1.0 + xp.exp(-z[:, 5]))
    return [(shares[t, 0], shares[t, 1], shares[t, 2], shares[t, 3], shares[t, 4], train[t]) for t in range(z.shape[0])]


def z_from_q(q):
    q = onp.clip(onp.asarray(q, dtype=float), 1e-12, 1.0)
    z = onp.empty((len(q), 6))
    z[:, :5] = onp.log(q[:, :5])
    z[:, 5] = onp.log(q[:, 5] / (1 - q[:, 5]))
    return z


def solve(mp, horizon=160, start=None, maxiter=3000, tol=1e-13, log=print):
    import autograd
    import autograd.numpy as anp
    from scipy.optimize import minimize

    M_ag = gi.Model(mp, horizon=horizon, xp=anp)
    M_np = gi.Model(mp, horizon=horizon)
    z0 = z_from_q(onp.tile(NEUTRAL, (horizon, 1))) if start is None else start
    shape = z0.shape

    def f(flat):
        z = flat.reshape(shape)
        return M_ag.simulate(decisions(anp, z), record=False)

    vg = autograd.value_and_grad(f)
    t0, it = time.time(), [0]

    def fg(flat):
        v, g = vg(flat)
        return float(v), onp.asarray(g, dtype=float)

    def cb(xk):
        it[0] += 1
        if it[0] % 100 == 0:
            log(f'  iter {it[0]}: objective {f(xk):.10f} ({time.time() - t0:.0f} s)')

    res = minimize(fg, z0.ravel(), jac=True, method='L-BFGS-B', callback=cb,
                   options=dict(maxiter=maxiter, maxfun=maxiter * 2, ftol=tol, gtol=1e-10, maxcor=30))
    z = res.x.reshape(shape)
    out = M_np.simulate(onp.array([[gi._val(v) for v in row] for row in decisions(onp, z)]))
    info = dict(success=bool(res.success), message=str(res.message), nit=int(res.nit), nfev=int(res.nfev),
                seconds=round(time.time() - t0, 1), objective=out['objective'],
                grad_norm=float(onp.linalg.norm(res.jac)))
    return out, z, info


def compare(target_job, mine, upto=20):
    """Relative differences, steps 0..upto, between the official target and the re-solve."""
    steps = target_job['steps']
    rows = []
    for k in COMPARE_KEYS:
        if k not in target_job['trajectory']:
            continue
        ref = target_job['trajectory'][k]
        worst, at = 0.0, None
        for i, t in enumerate(steps):
            if t > upto:
                break
            a, b = ref[i], mine[k][t]
            d = 0.0 if a == b else abs(b - a) / max(abs(a), 1e-300)
            if d > worst:
                worst, at = d, t
        rows.append((k, worst, at))
    ms_ref = target_job['milestones']
    ms_mine = gi.milestones(list(mine['gwp']), list(mine['frac_automated']))
    obj_ref = target_job['diagnostics']['objective']
    return dict(max_rel_diff=rows, milestones_official={k: ms_ref[k] for k in ms_mine},
                milestones_resolve=ms_mine, objective_official=obj_ref, objective_resolve=mine['objective'],
                objective_rel_diff=(mine['objective'] - obj_ref) / obj_ref)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--preset', default='default', help='job name in data/baseline_target.json')
    ap.add_argument('--target', default=str(HERE.parent / 'data' / 'baseline_target.json'))
    ap.add_argument('--out', required=True)
    ap.add_argument('--maxiter', type=int, default=3000)
    ap.add_argument('--warm-start-official', action='store_true',
                    help='robustness run: start from the official decisions for years 0-79 (target file must hold them)')
    a = ap.parse_args()
    target = json.loads(Path(a.target).read_text())
    job = next(j for j in target['jobs'] if j['name'] == a.preset)
    mp = job['args']['modelParams']
    horizon = job['args']['simulationArgs']['years'] * job['args']['simulationArgs']['objective_horizon_multiplier']
    start = None
    if a.warm_start_official:
        q = gi.decisions_from_states(job['trajectory'])
        steps = job['steps']
        if steps[:80] != list(range(80)):
            sys.exit('target holds only a subset of steps; warm start needs a full official run')
        start = z_from_q(onp.vstack([q, onp.tile(q[-1], (horizon - len(q), 1))]))
    print(f'Re-solving {a.preset}: horizon {horizon} years, {horizon * 6} decision variables', flush=True)
    out, z, info = solve(mp, horizon=horizon, start=start, maxiter=a.maxiter)
    print(json.dumps(info), flush=True)
    cmp_ = compare(job, out)
    report = dict(about='[[ai gen]] Independent re-solve (NOT the official GATE solver); see independent/README.md.',
                  preset=a.preset, horizon=horizon, start='official' if a.warm_start_official else 'neutral ' + str(NEUTRAL),
                  solver=info, comparison=cmp_,
                  trajectory={k: [float(x) for x in v[:80]] for k, v in out.items() if k != 'objective'})
    Path(a.out).write_text(json.dumps(report, indent=1) + '\n')
    for k, d, t in cmp_['max_rel_diff']:
        print(f'  {k:30s} max rel diff steps 0-20: {d:.4f} (step {t})')
    print('  milestones official', cmp_['milestones_official'])
    print('  milestones resolve ', cmp_['milestones_resolve'])
    print(f"  objective official {cmp_['objective_official']:.8f} resolve {cmp_['objective_resolve']:.8f} "
          f"rel {cmp_['objective_rel_diff']:+.2e}")


if __name__ == '__main__':
    main()
