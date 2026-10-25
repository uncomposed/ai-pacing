# GATE source-to-equation map

[[ai gen]] 2026-10-25. Paper: arXiv:2503.04941v2 TeX source (`model-technical.tex`); line
numbers refer to that file. Solver: the pinned playground bundle (SOURCES.yaml). Solver
names are the keys of its output (`<name>_path` arrays) and of its `modelParams`.

Status words:

- **exact**: holds on the official solver's output to rounding (relative error < 1e-12) at
  every step 0-20 of the three presets; tested in `tests/test_epoch_gate.py` with
  `gate_core.py`.
- **inequality**: a constraint that holds on every reported step; tested.
- **not reproduced**: the solver's form could not be recovered from its output; the paper's
  form is recorded, the gap is a discrepancy (README D-numbers).
- **not checked**: no attempt in this milestone.

`gate_core.py` is an independent implementation in the sense required by #13 only for the
equations marked exact or inequality: written from the paper, evaluated on the solver's
states and decisions. It does not solve the planner problem.

## State, choice and parameter names

| paper | meaning | unit (paper) | solver output | solver parameter |
|---|---|---|---|---|
| L(t) | human labor force | workers | `labor` | `main.labor_force_init`, `labor.pop_growth` (g_L) |
| K(t) | non-compute capital | real USD | `capital` | `main.capital_init`, `capital.depreciation` (delta_K), `capital.adj_timescale_k` (a_K) |
| Q(t) | physical compute stock | FLOP/year | `compute` (see E4, D6) | `compute.depreciation` (delta_Q), `compute.adj_timescale_q` (a_Q), `compute.exponent` (chi), `main.physical_compute_limit` (C_L) |
| H(t) | hardware efficiency | FLOP/year/$ | `hardware` | `main.hardware_init`, `rnd.hardware_cap`, `main.hardware_growth_init`, `main.hardware_inputs_init`, `rnd.hardware_returns`, `rnd.total_lambda_rnd_hardware`, `rnd.gamma_rnd_hardware` |
| S(t) | software efficiency | eFLOP/FLOP, S(0)=1 | `software` (8.43 at step 0, see README D8) | `main.software_init`, `rnd.software_cap`, `main.software_growth_init`, `main.software_inputs_init`, `rnd.software_returns`, `rnd.total_lambda_rnd_software`, `rnd.gamma_rnd_software` |
| C_T(t) | largest training run | eFLOP | `best_training_run`; physical: `physical_best_training_run` | `main.best_training_run` |
| f(t) | fraction of tasks automated | [0,1] | `frac_automated` | `automation.train_reqs` (log10 T), `automation.flop_gap_frac`, `automation.initial_frac` |
| Y(t) | gross world product | real USD/year | `gwp` | `main.gwp_init` |
| c(t) L(t) | consumption | real USD/year | `consumption` | |
| I_Q, I_K, I_H^RD, I_S^RD | gross investment flows | real USD/year | `compute_investment`; others as share x `gwp` | |
| shares of Y | planner's output split (choice) | fraction | `q_consumption`, `q_capital`, `q_compute`, `q_hardware_rnd`, `q_software_rnd` | |
| D, sum_i C_I,i | training vs runtime compute (choice) | eFLOP/year | `training_compute`, `runtime_compute`; shares `q_training_compute`, `q_runtime_compute` | |
| I_q | effective compute investment after adjustment cost | $ | `effective_compute_investment` | |
| m, iota_max | inference-training tradeoff slope, max inference multiplier | -, OOM | | `runtime.inference_oom_per_training_oom`, `runtime.tradeoff_range_oom_max` |
| gamma_0, gamma_1 | runtime requirement intercept (OOM) and slope | - | | `runtime.initial_compute_cost_oom`, `runtime.range_oom` |
| rho, alpha, mu | task substitution, capital elasticity, fixed-factor elasticity | - | `capital_share` | `main.ces_term_rho`, `production.alpha`, `production.delta` (mu) |
| beta, eta | discount rate, CRRA | - | | `objective.discount_rate`, `objective.eta` |
| xi | R&D wedge (add-on) | - | | `rnd.rnd_wedge` |
| G(f_i), zeta_i | beliefs over automation functions (add-on) | - | | `beliefs.max_frac_beliefs` |

## Equations

| # | paper (line) | equation (paper form) | solver status | notes |
|---|---|---|---|---|
| E1 | Table 4, 694; 577 | L(t) = L(0) e^{g_L t} (perfect reallocation) | **exact** | Reported index t is t+1 years after the initial state: `labor[t] = L0 exp(g_L (t+1))`. |
| E2 | 627 | L c + I_Q + I_H^RD + I_S^RD + I_K <= Y (output budget) | **exact** | Five output shares sum to 1; `consumption = q_consumption gwp`; `compute_investment = q_compute gwp`. Binding with equality. |
| E3 | 626 | D + integral C_I,i <= C (compute budget) | **exact** (shares) | `q_training_compute + q_runtime_compute = 1` and `training_compute/runtime_compute = q_training/q_runtime`. How the two flows relate to the stock is open (E7). |
| E4 | 396, 701 | dQ/dt = I_q H - delta_Q Q | **exact** as Q' = Q e^{-delta_Q} + I_q' H | Q is the solver's `compute`, I_q' its `effective_compute_investment` for the entered step, H start-of-step `hardware` (D5, D6). |
| E5 | 384 | I_Q = Q/(chi a_Q H) ((a_Q I_q H/Q + 1)^chi - 1) | not reproduced | Inverting with Q = `compute` does not give `effective_compute_investment`. Tobin's q for compute is reported (`tobin_q_compute`, 999 at step 0). |
| E6 | 319-321, 356-364 | dH/H = theta_H H^{-phi_H} (I_H^RD)^{lambda_H} Lambda_H(H); same for S; Lambda = (log X_max - log X)/(log X_max - log X(0)) | caps: **inequality** (H <= H_max, S <= S_max); growth law not reproduced | Playground parametrization differs from the paper (README D4): returns = lambda/phi = 5.2 and 1.25, plus a "researcher elasticity" 0.35 absent from the paper. Calibrating theta from `*_growth_init` and testing the printed law leaves ratios of 0.28-1.03 between observed and predicted growth. |
| E7 | 248, 704 | dC_T/dt = D | **inequality** (C_T non-decreasing) | `best_training_run[0] = 5e25 + training_compute[0]` holds at step 0 only; afterwards the eFLOP run grows faster than the sum of `training_compute` (software applied to past training, `continuous_training: true`). Physical part **exact** (#35): `physical_best_training_run[t] = [t-1] + training_compute[t]`, and `training_compute[t] + runtime_compute[t] = g(Q[t-1])` (step 0: `training_compute_init + runtime_compute_init`) to machine precision, so D and R are allocations of usable capacity in FLOP/year. Their share of Q falls toward 0 only where g(Q) saturates at C_L (`coupling_example.py`). The eFLOP run's faster growth stays unreproduced. |
| E8 | 269 | C_{T+iota} = C_T iota^{1/m} | used in E9 | iota_max = 10^5 (5 OOM), m = 2: +2.5 OOM. |
| E9 | 500-505 | f(C) = f_init below T/10^Delta; log-linear to 1 at T | **inequality**: deployed `frac_automated` <= f(C_T iota_max^{1/m}) at every step | The solver's threshold (`automation_schedule_x`) satisfies Delta = flop_gap_frac (log10 T - 16.608061) in all ten runs (D3). `frac_automated` is a planner choice below the frontier until f = 1, not the frontier itself. |
| E10 | 527 | N_i = C_I,i / R_i (digital workers) | not checked | `compute_allocation` (101-point task grid) is reported but not decoded. |
| E11 | 537 | R_i = max(1, f^{-1}(i)/C_T)^m 10^{gamma_0 + gamma_1 i} | not reproduced | Implemented in `gate_core.log10_runtime_requirement` for later use; not tested against the solver. |
| E12 | 644 | T = (integral T_i^rho di)^{1/rho}, rho < 0 | not reproduced | Paper: 100-point task grid for labor/CES, 20 for digital workers (line 1077). |
| E13 | 650 | T_i = L_i + N_i if i <= f, else L_i | not reproduced | |
| E14 | 636, 660 | Y = A T^{1-alpha-mu} K^alpha F^mu, A constant | capital share: **exact** (`capital_share = alpha`); A: constant (514.0) only while f = f_init | With T read as `cognitive_ces_term`, implied A drifts once automation starts (D7). |
| E15 | 615, 1091 | max sum_t e^{-(beta - g_L)(t-1)} (c_t^{1-eta} - 1)/(1-eta) over 2 x 80 years | not checked | Solver minimizes `objective` (falls along `objective_path`); its relation to `utility` and to this sum is not reconstructed. |
| E16 | 674, 698 | dK/dt = I_k - delta_K K | **exact** as K' = K e^{-delta_K} + I_k' | Forward Euler K(1 - delta_K) + I_k' is off by 0.22% per year (D5); both tested. |
| E17 | 670 | I_K = I_k + a_K I_k^2 / (2K) | **exact** (jointly with E16) | I_k' from gross `q_capital' gwp'` and start-of-step K. |
| E18 | 447, 713 | dC/dt = C dS/S - delta_Q C + I_q H S (effective compute) | not checked | The solver does not report C under this name; its `compute` follows E4 (D6). |
| E19 | 412 | usable compute g(Q) = Q / (Q/C_L + 1) | not checked | Q exceeds C_L in the Aggressive run (2.7e41 at step 20). |
| E20 | 752-799 | beliefs add-on: prior over automation functions capped at zeta_i, Bayesian conditioning | not checked | Exercised once (`default_max_frac_0.8`): f caps at 0.8. |
| E21 | 733-740 | R&D wedge xi: planner sees I^RD/xi; plan solved once, then simulated with true returns | not checked | Exercised once (`default_rnd_wedge_8`). |
| S1 | 1075-1094 | solution: gradient descent on 5 decisions per year over tau_optim = 2 tau_plan | observed | Bundle arguments: `sign_gradient_descent`, `maxiter` 40, learning rate 0.6 to 0.01, `fun_tol` 0.02, `combined_adam_sign_*`. Always stops at maxiter. |
| S2 | 1644 | sanity checks: simpler policy class; log-spliced utility | observed | Both pass in every run (`check`, `simple_policy_check`, `spliced_utility_check`). |
