"""Evidence for the reconstruction: probe the official solver as a black box (numpy only).

    node official/run_official.mjs gate.js probes.json independent/probe_jobs.json
    python3 independent/identify.py probes.json independent/data/identification.json

[[ai gen]] Each probe changes one parameter of the Default preset. For every run this script
measures, from the official output alone:

  quadrature   J_solver / J_exact, where J_solver is read off compute_allocation in the all-digital,
               penalty-free years (step 60) and J_exact = int_0^1 R_i^(rho/(rho-1)) di; compared with
               the left Riemann sum on 1000 points.
  lattice      the spacing and an anchor of the grid onto which f^-1 is floored, read off the
               penalised part of compute_allocation; compared with
               linspace(log10 training_compute_init - 5, log10 T + 5, 300).
  schedule_x   the reported automation_schedule_x against log10 T - Delta - 5,
               Delta = flop_gap_frac (log10 T - log10 C_T(0)).
  objective    objective / utility against -(1e5)^(eta - 1), and the scale K of utility.
  replay       the official decisions run through gate_indep.Model: worst relative difference over all
               reported fields and all 80 rows, and the objective.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate_indep as gi  # noqa: E402

FIELDS = ['gwp', 'consumption', 'capital', 'labor', 'frac_automated', 'compute', 'training_compute',
          'runtime_compute', 'best_training_run', 'physical_best_training_run', 'hardware', 'software',
          'compute_investment', 'effective_compute_investment', 'cognitive_ces_term']


def quadrature(mp, s, t=60):
    rho = mp['main']['ces_term_rho']; g0 = mp['runtime']['initial_compute_cost_oom']; g1 = mp['runtime']['range_oom']
    e = rho / (rho - 1)
    k = e * g1 * math.log(10)
    exact = 10 ** (e * g0) * ((math.exp(k) - 1) / k if k > 0 else 1.0)
    CI = s[t - 1]['runtime_compute'] * s[t - 1]['software']
    Js = CI * 10 ** (e * g0) / s[t]['compute_allocation'][0]
    left = 10 ** (e * g0) * np.mean(np.exp(k * np.arange(gi.N_TASKS) / gi.N_TASKS))
    return Js / exact, left / exact


def lattice(mp, s):
    rho = mp['main']['ces_term_rho']; g1 = mp['runtime']['range_oom']; m = mp['runtime']['inference_oom_per_training_oom']
    e = rho / (rho - 1)
    pts = set()
    prev = mp['main']['best_training_run']
    for t in range(len(s)):
        a = s[t]['compute_allocation']
        lc = math.log10(prev)
        if a[0] > 0:
            for j in range(101):
                if a[j] <= 0:
                    break
                pen = math.log10(a[j] / a[0]) / e - g1 * j / 100
                if pen > 1e-6:
                    pts.add(round(lc + pen / m, 9))
        prev = s[t]['best_training_run']
    v = sorted(pts)
    if len(v) < 3:
        return None
    d0 = min(b - a for a, b in zip(v, v[1:]))
    ks = [round((x - v[0]) / d0) for x in v]
    A = np.vstack([np.ones(len(ks)), ks]).T
    (c, d), *_ = np.linalg.lstsq(A, np.array(v), rcond=None)
    res = float(np.max(np.abs(A @ np.array([c, d]) - v)))
    T = mp['automation']['train_reqs']
    lo = math.log10(mp['main']['training_compute_init']) - gi.LATTICE_PAD_OOM
    d_pred = (T + gi.LATTICE_PAD_OOM - lo) / (gi.N_LATTICE - 1)
    phase = ((c - lo) / d_pred) % 1.0
    return dict(points=len(v), spacing=float(d), spacing_predicted=d_pred, fit_residual=res,
                anchor_offset_in_spacings=min(phase, 1 - phase))


def replay(mp, s, raw):
    try:
        M = gi.Model(mp)
    except NotImplementedError as ex:
        return dict(skipped=str(ex))
    q = gi.decisions_from_states(s)
    # years 80-159 are not reported; holding the last decision there changes the objective by < 1e-6
    q_full = np.vstack([q, np.tile(q[-1], (2 * len(q) - len(q), 1))])
    out = M.simulate(q_full)
    worst, where, first = 0.0, None, None
    for k in FIELDS:
        ref = np.array([x[k] for x in s])
        rel = np.abs(out[k][:len(s)] - ref) / np.maximum(np.abs(ref), 1e-300)
        i = int(rel.argmax())
        if rel[i] > worst:
            worst, where = float(rel[i]), f'{k} step {i}'
        bad = np.nonzero(rel > 1e-9)[0]
        if len(bad) and (first is None or bad[0] < first[0]):
            first = (int(bad[0]), k)
    return {'max_rel_diff': worst, 'at': where, 'first_step_above_1e-9': first,
            'objective_rel_diff': out['objective'] / raw['objective'] - 1}


def main(run_path, out_path):
    run = json.load(open(run_path))
    rows = []
    for r in run['results']:
        mp, raw = r['args']['modelParams'], r['rerun']
        s, wp = raw['world_path']['states'], raw['world_path']
        a = mp['automation']
        L0 = mp['main']['labor_force_init']; eta = mp['objective']['eta']
        disc = mp['objective']['discount_rate'] - mp['labor']['pop_growth']
        S1 = sum(math.exp(-disc * t) * (x['consumption'] / L0) ** (1 - eta) for t, x in enumerate(s))
        qs, ql = quadrature(mp, s)
        delta = a['flop_gap_frac'] * (a['train_reqs'] - math.log10(mp['main']['best_training_run']))
        rows.append(dict(
            name=r['job']['name'], job=r['job'],
            quadrature_solver_over_exact=qs, quadrature_left1000_over_exact=ql,
            lattice=lattice(mp, s),
            schedule_x=wp['automation_schedule_x'][0],
            schedule_x_predicted=a['train_reqs'] - delta - gi.SCHEDULE_X_OFFSET,
            objective_over_utility=raw['objective'] / raw['utility'],
            objective_over_utility_predicted=-gi.OBJECTIVE_REF_C ** (eta - 1),
            utility_scale_K=-raw['utility'] / S1,
            replay=replay(mp, s, raw)))
    Ks = [x['utility_scale_K'] for x in rows]
    summary = dict(
        about='[[ai gen]] Output of independent/identify.py on a black-box run of independent/probe_jobs.json.',
        node=run['node'], runs=rows,
        K_min=min(Ks), K_max=max(Ks), K_used=gi.OBJECTIVE_K)
    Path(out_path).write_text(json.dumps(summary, indent=1) + '\n')
    for x in rows:
        lat = x['lattice'] or {}
        rp = x['replay']
        print(f"{x['name']:14s} quad {x['quadrature_solver_over_exact']:.10f}/{x['quadrature_left1000_over_exact']:.10f}"
              f"  lattice {lat.get('spacing', float('nan')):.10f}/{lat.get('spacing_predicted', float('nan')):.10f}"
              f"  schedx {x['schedule_x'] - x['schedule_x_predicted']:+.1e}"
              f"  obj/util {x['objective_over_utility'] / x['objective_over_utility_predicted'] - 1:+.1e}"
              f"  K {x['utility_scale_K']:.9f}"
              f"  replay {rp.get('max_rel_diff', float('nan')):.1e} obj {rp.get('objective_rel_diff', float('nan')):+.1e}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
