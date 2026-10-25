"""Independent re-implementation of the GATE planner model (Default preset and its parameter family).

[[ai gen]] Written for issue #34. This is NOT Epoch AI's code and NOT the official model. It is
written from the paper (arXiv:2503.04941v2, TeX source), the playground's parameter table
(input_default2 in the pinned bundle) and identities read off the official solver's output.
The compiled solver (WebAssembly) was run as a black box; it was not decompiled. Every rule
below is labelled with where it comes from:

  [paper]     an equation printed in the paper, used as printed
  [table]     a definition or derivation in the paper's appendix or the playground parameter table
  [observed]  a discretisation or timing convention the paper does not state, identified because
              it makes the official output satisfy the equation to rounding (evidence in
              RECONSTRUCTION.md); an identification of an exact rule, not a fitted value
  [fitted constant]  one positive scale factor of the reported objective, OBJECTIVE_K; it does
              not move the optimum

Nothing in the R&D law is fitted: theta and phi follow from the parameter table.

Row convention (matches the solver's `*_path` arrays): row t applies the planner's decisions of
year t to the start-of-year state s_t. It reports that year's output and flows (gwp, consumption,
frac_automated, cognitive_ces_term, training/runtime compute, investments) together with the
end-of-year state s_{t+1} (capital, labor, compute, hardware, software, best_training_run).

The same code runs on numpy (default) or on autograd.numpy (pass xp=autograd.numpy), which is
how independent/resolve.py gets exact gradients. Branches (argmin over the boundary, caps) are
taken on values, so gradients are those of the selected branch.
"""
import math

import numpy as np

# Discretisation constants of the official solver, identified from its output [observed].
N_TASKS = 1000          # left Riemann grid for the task integral (simulationArgs ..._integral = 1000)
N_BOUNDARY = 200        # human/digital boundary searched on multiples of 1/200 (..._search = 200)
N_LATTICE = 300         # f^-1 is floored onto 300 log-spaced compute points
LATTICE_PAD_OOM = 5.0   # lattice spans [log10 training_compute_init - 5, log10 T + 5]
SCHEDULE_X_OFFSET = 5.0  # reported automation_schedule_x = log10 T - Delta - 5 (display only)
RD_MIN_GROWTH = 1.001   # efficiency grows at least 0.1%/yr below its ceiling [observed]
OBJECTIVE_REF_C = 1e5   # objective = utility * (-(1e5)^(eta-1))  [observed, exact over 13 runs]
OBJECTIVE_K = 0.04866629  # [fitted constant] scale of the solver's `utility`; see RECONSTRUCTION.md
NEG = -1e6              # stands in for log10 f^-1(i) = -inf (no inference penalty)


def _val(x):
    """Plain float of a value that may be an autograd box (for branch decisions only)."""
    while hasattr(x, '_value'):
        x = x._value
    return float(x)


class Model:
    """Parameters and derived constants. `mp` is the solver's modelParams dict."""

    def __init__(self, mp, horizon=160, xp=np):
        self.mp, self.xp, self.horizon = mp, xp, horizon
        a, r, mn = mp['automation'], mp['runtime'], mp['main']
        rnd, comp, cap = mp['rnd'], mp['compute'], mp['capital']
        # automation [paper eq. automation function; table: FLOP gap fraction]
        self.T = a['train_reqs']
        self.f_init = a['initial_frac']
        self.ct0 = mn['best_training_run']
        self.delta_flop = a['flop_gap_frac'] * (self.T - math.log10(self.ct0))   # [table]
        self.x_thr = self.T - self.delta_flop
        self.schedule_x = self.x_thr - SCHEDULE_X_OFFSET
        self.m = r['inference_oom_per_training_oom']
        self.iota_oom = r['tradeoff_range_oom_max']
        self.g0, self.g1 = r['initial_compute_cost_oom'], r['range_oom']
        # f^-1 lattice [observed]
        self.lat_lo = math.log10(mn['training_compute_init']) - LATTICE_PAD_OOM
        self.lat_d = (self.T + LATTICE_PAD_OOM - self.lat_lo) / (N_LATTICE - 1)
        # production [paper]; A calibrated so that Y(0) = A L0^(1-alpha) K0^alpha [observed]
        self.rho = mn['ces_term_rho']
        self.e = self.rho / (self.rho - 1.0)
        self.alpha = mp['production']['alpha']
        if mp['production'].get('delta', 0) != 0:
            raise NotImplementedError('non-accumulable factor (mu > 0) not reconstructed')
        self.L0, self.gL = mn['labor_force_init'], mp['labor']['pop_growth']
        self.K0, self.Y0 = mn['capital_init'], mn['gwp_init']
        self.A = self.Y0 / (self.L0 ** (1 - self.alpha) * self.K0 ** self.alpha)
        if mn.get('labor_reallocation_friction', 0):
            raise NotImplementedError('no-reallocation labor mode not reconstructed')
        # R&D [paper eq. r_d_equation with ceilings; table: lambda = lambda' * p, phi = lambda'/returns,
        # theta from the initial growth rate]
        self.rd = {}
        for k, X0, I0, g0_ in (('hardware', mn['hardware_init'], mn['hardware_inputs_init'], mn['hardware_growth_init']),
                               ('software', mn['software_init'], mn['software_inputs_init'], mn['software_growth_init'])):
            lam = rnd['total_lambda_rnd_' + k]
            lam_labor = lam / rnd['gamma_rnd_' + k]        # returns to research labor (0.4)
            phi = lam_labor / rnd[k + '_returns']
            theta = g0_ * X0 ** phi / I0 ** lam
            self.rd[k] = dict(X0=X0, lam=lam, phi=phi, theta=theta, cap=rnd[k + '_cap'])
        if rnd.get('rnd_wedge', 1) != 1:
            raise NotImplementedError('R&D wedge add-on not reconstructed')
        beliefs = mp.get('beliefs', {}).get('max_frac_beliefs', [{'prob': 1, 'max_frac': 1}])
        if not (len(beliefs) == 1 and beliefs[0]['max_frac'] == 1):
            raise NotImplementedError('beliefs add-on not reconstructed')
        # compute [paper]
        self.chi, self.aQ, self.dQ = comp['exponent'], comp['adj_timescale_q'], comp['depreciation']
        self.CL = mn['physical_compute_limit']
        self.aK, self.dK = cap['adj_timescale_k'], cap['depreciation']
        # initial state [observed: Q0 = initial runtime + initial training compute]
        self.Q0 = mn['runtime_compute_init'] + mn['training_compute_init']
        self.CI0 = mn['runtime_compute_init']
        self.PCT0 = mn['best_training_run']   # physical_best_training_run starts at C_T(0) [observed]
        # objective [paper eq. objective-function; per-capita normalisation observed]
        self.eta = mp['objective']['eta']
        self.disc = mp['objective']['discount_rate'] - self.gL
        # task grid
        p = np.arange(N_TASKS) / N_TASKS
        self.p = p
        self.base_log_req = self.g0 + self.g1 * p
        x = self.x_thr + (p - self.f_init) / (1 - self.f_init) * self.delta_flop
        lat = self.lat_lo + np.floor((x - self.lat_lo) / self.lat_d + 1e-9) * self.lat_d
        # A lattice point below the threshold automates only f_init, so f^-1 = 0 there (the paper's
        # footnote definition) and there is no inference penalty [observed: step 2 to rounding].
        self.finv = np.where((p <= self.f_init) | (lat < self.x_thr), NEG, lat)
        self.bk = np.arange(0, N_TASKS + 1, N_TASKS // N_BOUNDARY)   # boundary candidates (cells)

    # --- automation frontier [paper eq. automation function + eq. training_vs_inference_tradeoff]
    def f_max(self, log_ct):
        x = log_ct + self.iota_oom / self.m
        if _val(x) <= self.x_thr:
            return self.f_init
        f = self.f_init + (1 - self.f_init) * (x - self.x_thr) / self.delta_flop
        return 1.0 if _val(f) >= 1.0 else f

    # --- task layer [paper eqs. digital workers, runtime requirement, CES, T_i = L_i + N_i]
    def composite(self, CI, log_ct, L, fmax):
        """Effective labor T and the chosen human/digital boundary b.

        Humans and digital workers are perfect substitutes within a task [paper: T_i = L_i + N_i].
        The planner puts digital workers on [0, b) and spreads humans uniformly over [b, 1],
        b <= frontier. With the optimal split of runtime compute across [0, b),
        T^rho = CI^rho J(b)^(1-rho) + (1-b)^(1-rho) L^rho,  J(b) = int_0^b R_i^(rho/(rho-1)) di.
        The boundary is chosen on values (numpy); the chosen candidate is then evaluated with xp.
        """
        xp, rho, e = self.xp, self.rho, self.e
        lc, fm = _val(log_ct), _val(fmax)
        # value pass (numpy) to pick the boundary
        pen = self.m * np.maximum(0.0, self.finv - lc)
        live = self.p < fm - 1e-12
        terms = np.where(live, np.power(10.0, e * (self.base_log_req + pen)), 0.0) / N_TASKS
        cs = np.concatenate(([0.0], np.cumsum(terms)))
        cands = [(int(k), k / N_TASKS) for k in self.bk if k / N_TASKS <= fm + 1e-12]
        kf = None
        if fm < 1.0:
            # the frontier itself is a candidate, with a fractional last cell [observed: variants
            # whose optimum sits at the frontier; residual up to 1e-4 there, see RECONSTRUCTION.md]
            kf = int(math.floor(fm * N_TASKS + 1e-12))
            cands.append((-1, fm))
        CIv, Lv = _val(CI), _val(L)
        best = None
        for k, b in cands:
            J = cs[k] if k >= 0 else cs[kf] + (fm * N_TASKS - kf) * terms[kf]
            X = (CIv ** rho * J ** (1 - rho) if J > 0 else 0.0) + ((1 - b) ** (1 - rho) * Lv ** rho if b < 1 - 1e-12 else 0.0)
            if best is None or X < best[0]:
                best = (X, k, b)
        _, k, b = best
        # differentiable pass for the chosen candidate
        if k == 0:
            X = L ** rho
            return X ** (1 / rho), 0.0
        n = k if k > 0 else kf
        pen_x = self.m * xp.maximum(0.0, self.finv[:n] - log_ct)
        J = xp.sum(xp.power(10.0, e * (self.base_log_req[:n] + pen_x))) / N_TASKS
        if k < 0:
            pen_f = self.m * xp.maximum(0.0, self.finv[kf] - log_ct)
            J = J + (fmax * N_TASKS - kf) * xp.power(10.0, e * (self.base_log_req[kf] + pen_f)) / N_TASKS
            b = fmax
        X = CI ** rho * J ** (1 - rho)
        if _val(b) < 1 - 1e-12:
            X = X + (1 - b) ** (1 - rho) * L ** rho
        return X ** (1 / rho), _val(b)

    # --- R&D [paper eq. r_d_equation and Lambda ceiling; exponential one-year step observed]
    def rd_step(self, kind, X, I):
        xp, c = self.xp, self.rd[kind]
        lam_factor = (math.log(c['cap']) - xp.log(X * 1.0)) / (math.log(c['cap']) - math.log(c['X0']))
        if _val(lam_factor) <= 0:
            return X
        Ipos = I if _val(I) > 0 else 0.0 * I + 1e-300
        g = c['theta'] * X ** (-c['phi']) * Ipos ** c['lam'] * lam_factor
        # Near the ceiling the solver grows at least 0.1%/yr until it reaches the cap exactly
        # [observed: hardware steps 40-41 and software 42-46 of the Default run].
        new = X * xp.exp(g) if _val(g) > math.log(RD_MIN_GROWTH) else X * RD_MIN_GROWTH
        return new if _val(new) < c['cap'] else 0.0 * new + c['cap']

    # --- compute adjustment cost [paper eq. compute_adjustment_cost], inverted
    def effective_compute_investment(self, IQ, Q, H):
        return Q / (self.aQ * H) * ((self.chi * self.aQ * H * IQ / Q + 1.0) ** (1.0 / self.chi) - 1.0)

    # --- capital adjustment cost [paper eq. capital-adj-cost], inverted
    def effective_capital_investment(self, IK, K):
        return (self.xp.sqrt(1.0 + 2.0 * self.aK * IK / K) - 1.0) * K / self.aK

    def usable(self, Q):
        """Heat-limited usable compute g(Q) [paper]."""
        return Q / (Q / self.CL + 1.0)

    def simulate(self, q, years=None, record=True):
        """Simulate rows 0..years-1. q[t] = (output shares: consumption, capital, compute,
        hardware R&D, software R&D, summing to 1; training share of usable compute).

        record=True returns a dict of numpy arrays named like the solver output plus 'objective';
        record=False returns only the objective (works under autograd)."""
        xp = self.xp
        years = len(q) if years is None else years
        K, Q, H, S = self.K0, self.Q0, self.rd['hardware']['X0'], self.rd['software']['X0']
        CT, PCT, CI = self.ct0, self.PCT0, self.CI0
        rows, cons = [], []
        for t in range(years):
            qc, qk, qQ, qH, qS, qT = (q[t][i] for i in range(6))
            L = self.L0 * math.exp(self.gL * t)
            log_ct = xp.log10(CT) if not isinstance(CT, float) else math.log10(CT)
            fm = self.f_max(log_ct)
            Tc, b = self.composite(CI, log_ct, L, fm)
            Y = self.A * Tc ** (1 - self.alpha) * K ** self.alpha
            cons.append(qc * Y)
            IQ, IK, IH, IS = qQ * Y, qk * Y, qH * Y, qS * Y
            Iq = self.effective_compute_investment(IQ, Q, H)
            Ik = self.effective_capital_investment(IK, K)
            # compute used this year: start-of-year stock and software [observed]
            G = self.usable(Q)
            TR, RT = qT * G, (1.0 - qT) * G
            CT_new = CT + TR * S
            H_new = self.rd_step('hardware', H, IH)
            S_new = self.rd_step('software', S, IS)
            Q_new = Q * math.exp(-self.dQ) + Iq * H      # [observed: exponential depreciation]
            K_new = K * math.exp(-self.dK) + Ik
            if record:
                rows.append(dict(gwp=Y, consumption=cons[-1], frac_automated=fm, cognitive_ces_term=Tc, boundary=b,
                                 compute_investment=IQ, effective_compute_investment=Iq, training_compute=TR,
                                 runtime_compute=RT, capital=K_new, labor=self.L0 * math.exp(self.gL * (t + 1)),
                                 compute=Q_new, hardware=H_new, software=S_new, best_training_run=CT_new,
                                 physical_best_training_run=PCT + TR,
                                 q_consumption=qc, q_capital=qk, q_compute=qQ, q_hardware_rnd=qH,
                                 q_software_rnd=qS, q_training_compute=qT, q_runtime_compute=1 - qT))
            K, Q, H, S, CT, PCT = K_new, Q_new, H_new, S_new, CT_new, PCT + TR
            CI = RT * S   # runtime hardware allocated this year runs next year at next year's software [observed]
        obj = self.objective(cons)
        if not record:
            return obj
        out = {k: np.array([_val(r[k]) for r in rows]) for k in rows[0]}
        out['objective'] = _val(obj)
        return out

    def objective(self, cons):
        """Solver-scale objective (minimised): K (1e5)^(eta-1) sum_t e^{-(beta-g_L) t} (C_t/L0)^(1-eta).

        A positive affine transform of the paper's sum of e^{-(beta-g_L)t} (c^(1-eta)-1)/(1-eta), with
        per-capita consumption taken as C_t / L(0) [observed]; K is the one fitted scale."""
        total = 0.0
        for t, C in enumerate(cons):
            total = total + math.exp(-self.disc * t) * (C / self.L0) ** (1 - self.eta)
        return OBJECTIVE_K * OBJECTIVE_REF_C ** (self.eta - 1) * total


def decisions_from_states(states):
    """Official decisions (rows of q) from solver output rows (list of dicts or dict of lists)."""
    keys = ('q_consumption', 'q_capital', 'q_compute', 'q_hardware_rnd', 'q_software_rnd', 'q_training_compute')
    if isinstance(states, dict):
        return np.array([states[k] for k in keys]).T
    return np.array([[s[k] for k in keys] for s in states])


def milestones(gwp, frac):
    """Milestones as defined by official/extract_target.py."""
    growth = [gwp[t + 1] / gwp[t] - 1 for t in range(len(gwp) - 1)]

    def first(pred, seq):
        return next((i for i, v in enumerate(seq) if pred(v)), None)

    peak = max(range(len(growth)), key=lambda t: growth[t])
    return {
        'first_step_frac_automated_ge_0.5': first(lambda v: v >= 0.5, frac),
        'first_step_frac_automated_ge_0.9': first(lambda v: v >= 0.9, frac),
        'first_step_frac_automated_eq_1': first(lambda v: v >= 1.0, frac),
        'first_step_gwp_growth_ge_30pct': first(lambda v: v >= 0.30, growth),
        'peak_gwp_growth_step': peak,
    }
