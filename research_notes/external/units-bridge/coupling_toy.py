"""Minimal research-to-industry coupling toy, compared with the pact solver's unchanged exogenous growth law (#11).

Status: a toy. Every parameter is a normalization or a bounded scenario (conversions.yaml, equations.yaml); nothing
is calibrated and nothing here feeds the pact solver. Pure Python, runs in well under a second:

    python3 coupling_toy.py            # write results/coupling_toy.{md,json}
    python3 coupling_toy.py --check    # recompute and compare with the committed results (exit 1 on drift)

Baseline (equilibrium_model.py, unchanged): A_{t+1} = A_t exp(g chi dt (1 - A_t / Kmax)).

Toy (one-year steps, all stocks in EIU of the output they support; equations TOY-* in equations.yaml):
    Y   = nu min(K, E, C_ops)                     output; nu = 1/yr (CV-CAPACITY-TO-OUTPUT)
    C_ops = (1 - phi) C,  C_res = phi C            one compute ledger split by shares (mode-contract accounting)
    D   = D_h + lam C_res                          design and integration throughput; lam is the coding-speed lever
    budget   c_K dK + c_E dE + c_C dC <= s Y dt    investment from output
    design   dK + dE + dC <= D dt                  every new unit of capacity must be designed and integrated
    energy   dE <= r_E E dt,  E + dE <= E_max      deployment-rate and resource caps
    chips    dC <= (Q_imp + eta_crude crude K + eta_le le K) dt
             crude = 1 once K >= K_crude (basic chip production), le = 1 once K >= A_close (leading-edge closure)
A planner raises the balanced level L = min(K, E, C_ops) as far as all constraints allow (bisection). With every cap
slack and kappa = c_K + c_E + c_C / (1 - phi) = s / (exp(g dt) - 1), the toy reproduces the baseline with chi = 1 and
A << Kmax exactly (equation TOY-REDUCES-TO-PACT). That is a reduction check, not evidence for either model.
"""
import argparse
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OUT_JSON = HERE / 'results/coupling_toy.json'
OUT_MD = HERE / 'results/coupling_toy.md'
SOLVER = HERE.parents[1] / 'Off Earth industry as misalignment control/model/equilibrium_model.py'
GROWTH_LAW = 'Ain * np.exp(P["g"] * chi * dt * np.maximum(0.0, 1.0 - Ain / Kmax))'

BASE = dict(g=0.35, A0=1e-3, Kmax=1e9, A_close=0.1, chi0=0.15,      # pact PARAMS baselines (read and checked below)
            s=0.5, phi=0.2, D_h=0.0, lam=1e9, r_E=math.inf, E_max=math.inf,
            Q_imp=math.inf, eta_crude=0.0, K_crude=math.inf, eta_le=math.inf, delta=0.0, T=40)
INF = math.inf


def pact_params():
    """The baselines this toy borrows, read from PARAMS without importing numpy."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('assumptions_tool', HERE.parents[2] / 'tools/assumptions_tool.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    p = mod.load_params()
    return {k: p[k] for k in ('g', 'A0', 'Kmax', 'A_close', 'chi0')}


def baseline_path(g, A0, T, chi=1.0, Kmax=1e9, A_close=None, chi_pre=None):
    """The solver's growth step iterated along one path (as docking/metzger.py `our_path`)."""
    A = [A0]
    for _ in range(T):
        a = A[-1]
        c = chi if A_close is None or a >= A_close else chi_pre
        A.append(a * math.exp(g * c * max(0.0, 1 - a / Kmax)))
    return A


def run(**over):
    p = dict(BASE, **over)
    g, phi, s = p['g'], p['phi'], p['s']
    kappa = s / (math.exp(g) - 1)                    # TOY-REDUCES-TO-PACT
    cK = cE = kappa / 3
    cC = (1 - phi) * kappa / 3                       # TOY-COST-NORMALIZATION
    K = E = p['A0']
    C = p['A0'] / (1 - phi)
    Y, binding, lam_hist = [], [], []
    for t in range(p['T'] + 1):
        Cops, Cres = (1 - phi) * C, phi * C
        level = min(K, E, Cops)
        Y.append(level)                              # nu = 1/yr: output in EIU/yr equals the level in EIU
        if t == p['T']:
            break
        D = p['D_h'] + p['lam'] * Cres
        budget = s * level
        dE_max = min(p['r_E'] * E, max(0.0, p['E_max'] - E))
        chips = p['Q_imp'] + (p['eta_crude'] * K if K >= p['K_crude'] else 0.0) + (p['eta_le'] * K if K >= p['A_close'] else 0.0)

        def needs(L):
            return max(0.0, L - K), max(0.0, L - E), max(0.0, L / (1 - phi) - C)

        def slack(L):
            dK, dE, dC = needs(L)
            return {'budget': budget - (cK * dK + cE * dE + cC * dC), 'design': D - (dK + dE + dC),
                    'energy': dE_max - dE, 'chips': chips - dC}

        lo, hi = level, level * 1e3
        if all(v >= 0 for v in slack(hi).values()):
            raise RuntimeError('no constraint binds; widen the search')
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if all(v >= -1e-15 * max(1.0, level) for v in slack(mid).values()):
                lo = mid
            else:
                hi = mid
        sl = slack(hi)
        binding.append(min(sl, key=sl.get))
        dK, dE, dC = needs(lo)
        K, E, C = K * (1 - p['delta']) + dK, E + dE, C + dC
    rates = [math.log(Y[t + 1] / Y[t]) for t in range(p['T'])]
    return {'Y': Y, 'rates': rates, 'binding': binding}


def years_to(path, target):
    for t, y in enumerate(path):
        if y >= target:
            return t
    return None


SCENARIOS = [
    # (id, title, overrides, lam values)
    ('slack', 'No physical cap; design binds below lam* (coding-limited regime)', {}, [0.5, 1, 2, 4, 8, 16]),
    ('energy', 'Energy deployment capped at r_E = 0.10/yr', {'r_E': 0.10}, [1, 2, 8, 64]),
    ('resource', 'Energy resource capped at E_max = 0.02 EIU', {'E_max': 0.02}, [2, 8, 64]),
    ('quota', 'Chips: import quota 1e-4 EIU/yr, no local fabs below A_close', {'Q_imp': 1e-4}, [2, 8, 64]),
    ('quota_crude', 'Quota plus basic local chips (eta_crude 0.1/yr from K >= 1.6e-6 EIU)',
     {'Q_imp': 1e-4, 'eta_crude': 0.1, 'K_crude': 1.6e-6}, [2, 8, 64]),
]


def compute():
    pp = pact_params()
    for k, v in pp.items():
        assert BASE[k] == v, f'toy baseline {k} = {BASE[k]} but PARAMS says {v}'
    out = {'pact_params': pp, 'lam_star': None, 'scenarios': {}}
    phi, g = BASE['phi'], BASE['g']
    # design throughput needed for unconstrained growth, per unit of research compute
    out['lam_star'] = (math.exp(g) - 1) * (2 * (1 - phi) + 1) / phi
    T = BASE['T']
    base = baseline_path(g, BASE['A0'], T, Kmax=BASE['Kmax'])
    base_chi0 = baseline_path(g, BASE['A0'], T, Kmax=BASE['Kmax'], A_close=BASE['A_close'], chi_pre=BASE['chi0'])
    out['baseline'] = {'mean_rate': math.log(base[-1] / base[0]) / T, 'years_to_A_close': years_to(base, BASE['A_close'])}
    out['baseline_chi0'] = {'mean_rate': math.log(base_chi0[-1] / base_chi0[0]) / T,
                            'years_to_A_close': years_to(base_chi0, BASE['A_close'])}
    red = run()
    no_cap = baseline_path(g, BASE['A0'], T, Kmax=math.inf)
    out['reduction_max_rel_diff'] = max(abs(a / b - 1) for a, b in zip(red['Y'], no_cap))
    out['kmax_term_max'] = max(abs(a / b - 1) for a, b in zip(base, no_cap))
    for sid, title, over, lams in SCENARIOS:
        rows = []
        for lam in lams:
            r = run(lam=lam, **over)
            late, early = r['rates'][-5:], r['rates'][:5]
            counts = {k: r['binding'].count(k) for k in ('design', 'energy', 'chips', 'budget')}
            rows.append({'lam': lam, 'mean_rate': math.log(r['Y'][-1] / r['Y'][0]) / T,
                         'rate_first5': sum(early) / len(early), 'rate_last5': sum(late) / len(late), 'chi_eff_last5': sum(late) / len(late) / g,
                         'Y_final': r['Y'][-1], 'years_to_A_close': years_to(r['Y'], BASE['A_close']),
                         'binding_years': counts})
        out['scenarios'][sid] = {'title': title, 'overrides': {k: (str(v) if v == INF else v) for k, v in over.items()}, 'rows': rows}
    return out


def markdown(res):
    L = ['# Coupling toy: research to industry, against the exogenous growth baseline', '',
         '[[ai gen]] Generated by `python3 coupling_toy.py` (issue #11). A toy: every parameter is a normalization or a',
         'bounded scenario, nothing is calibrated, and nothing here feeds the pact solver. See README.md.', '',
         f'Pact baselines read from PARAMS: g = {res["pact_params"]["g"]}, A0 = {res["pact_params"]["A0"]}, '
         f'A_close = {res["pact_params"]["A_close"]}, chi0 = {res["pact_params"]["chi0"]}. Horizon {BASE["T"]} years; '
         f'research share of compute phi = {BASE["phi"]}, savings share s = {BASE["s"]}.', '',
         '## Baseline (unchanged solver growth law)', '',
         '| case | mean growth /yr | years to A_close |', '|---|---|---|',
         f'| chips available (chi = 1) | {res["baseline"]["mean_rate"]:.3f} | {_yrs(res["baseline"]["years_to_A_close"])} |',
         f'| chips denied below A_close (chi0) | {res["baseline_chi0"]["mean_rate"]:.3f} | {_yrs(res["baseline_chi0"]["years_to_A_close"])} |', '',
         f'Reduction check: with every cap slack the toy reproduces the chi = 1 path without the Kmax term to a relative '
         f'{res["reduction_max_rel_diff"]:.1e} (bisection tolerance); the Kmax term itself changes the baseline by at most '
         f'{res["kmax_term_max"]:.1e} over the horizon.', '',
         f'Design throughput needed for growth at g, per unit of research compute: lam* = {res["lam_star"]:.2f} /yr.', '']
    for sid, sc in res['scenarios'].items():
        L += [f'## {sid}: {sc["title"]}', '',
              '| lam (/yr) | mean growth /yr | growth, first 5 yr | growth, last 5 yr | chi_eff, last 5 yr | years to A_close | binding years: design / energy / chips / budget |',
              '|---|---|---|---|---|---|---|']
        for r in sc['rows']:
            b = r['binding_years']
            L.append(f'| {r["lam"]:g} | {r["mean_rate"]:.4f} | {r["rate_first5"]:.4f} | {r["rate_last5"]:.4f} | {r["chi_eff_last5"]:.3f} | '
                     f'{_yrs(r["years_to_A_close"])} | '
                     f'{b["design"]} / {b["energy"]} / {b["chips"]} / {b["budget"]} |')
        L.append('')
    L += ['## Reading', '',
          '- **Limiting case.** Once energy deployment, an energy resource or a chip quota binds, raising lam (faster',
          '  coding) leaves the output path unchanged: the rows for large lam are identical. Coding speed matters only in',
          '  the design-bound regime (lam below lam*), and only until the next physical cap binds.',
          '- **chi0 is not a constant.** Under a fixed chip quota the effective multiplier chi_eff = rate / g falls over',
          '  time (growth becomes linear in the quota), unlike the solver\'s constant chi0. Basic local chips (crude',
          '  closure at Metzger scale) restore part of the growth long before leading-edge closure.',
          '- None of these numbers is an estimate. They show which couplings can matter, not how large they are.']
    return '\n'.join(L) + '\n'


def _yrs(y):
    return y if y is not None else f'> {BASE["T"]}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if GROWTH_LAW not in SOLVER.read_text():
        sys.exit('the solver growth law changed; update baseline_path and this check')
    res = compute()
    text = json.dumps(res, indent=1, sort_keys=True) + '\n'
    md = markdown(res)
    if a.check:
        old = json.loads(OUT_JSON.read_text())
        drift = _drift(old, json.loads(text))
        if drift or OUT_MD.read_text() != md:
            sys.exit('coupling_toy results drift from the committed copy: ' + '; '.join(drift[:5] or ['markdown differs']))
        print('coupling toy: committed results reproduce')
        return
    OUT_JSON.write_text(text)
    OUT_MD.write_text(md)
    print(md)


def _drift(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return [f'{path}: keys differ']
        return [d for k in a for d in _drift(a[k], b[k], f'{path}/{k}')]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f'{path}: lengths differ']
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in _drift(x, y, f'{path}/{i}')]
    if isinstance(a, float) and isinstance(b, float):
        return [] if math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-15) else [f'{path}: {a} != {b}']
    return [] if a == b else [f'{path}: {a!r} != {b!r}']


if __name__ == '__main__':
    main()
