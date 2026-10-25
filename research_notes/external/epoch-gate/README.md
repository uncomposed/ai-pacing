# Epoch GATE: pinned rerun and equation map (issue #13)

[[ai gen]] Written 2026-10-25. First reproducible milestone for #13, not the whole issue.

GATE (Erdil et al., arXiv:2503.04941) is Epoch AI's integrated assessment model of AI
automation: investment builds compute, compute automates tasks, output funds more
investment. This folder pins the paper and the model's executable form, reruns the
official solver, maps the paper's equations onto the solver's output, and records what
the model represents (who decides, which modes, which units).

## Status

| kind of claim | status here |
|---|---|
| **Source replication** (official code reproduces its own published outputs) | **Done for the three playground presets.** Epoch's compiled solver, rerun under Node from the pinned bundle, reproduces the playground's cached runs bit for bit (10,484 values per preset, max relative difference 0). |
| **Independent implementation** | **Partial, labelled.** `gate_core.py` evaluates paper equations on the official solver's states and decisions. It does not solve the planner problem. Six equations hold to rounding on every step of the three presets (E1-E4, E16 with E17, and the capital share in E14); three hold as inequalities (E6 caps, E7 monotone training run, E8-E9 deployed share within the frontier); the rest are not reproduced (E5, the R&D growth part of E6, E10-E13 runtime and task layer, E14 TFP once automation starts, E15, E18, E19). See [EQUATIONS.md](EQUATIONS.md). |
| **Numerical correctness of GATE** | **Not established.** The solver stops at its iteration cap (40) in every run; doubling the cap moves trajectory values by up to 2% (steps 0-20) but leaves every milestone unchanged. See "Convergence". |
| **Empirical validation** | **None.** Nothing here is compared with observations. Matching a published trajectory is not evidence that GATE's assumptions hold, and says nothing about sovereign AI. |

The official solver's source is not public (see Sources). "Official code" here means
the compiled WebAssembly that Epoch ships in its playground, run unchanged.

## Sources (details in [SOURCES.yaml](SOURCES.yaml))

- **Paper**: arXiv:2503.04941 v1 (2025-03-06) and v2 (2025-03-12), CC BY 4.0. The v2 TeX
  source was read in full for sections 2-5 and appendices B-C. v1 to v2 is editorial
  (footnotes, acknowledgements, one paragraph on bottlenecks, a missing `dt`); no
  equation or default changes.
- **Executable model**: the playground bundle `https://epoch.ai/generated/gate.js`,
  SHA-256 `c2104290...e72731`, fetched 2026-10-25. It contains the solver (C++ compiled
  to WebAssembly, `implementation: "C++"` in its arguments), the parameter table, and
  `cache_default`, the precomputed runs of the Default, Conservative and Aggressive
  presets. The URL is unversioned; the hash is the pin. The code has no license
  statement, so it is fetched by script and **not vendored**. The page footer licenses
  "Epoch AI's work" under CC BY 4.0; we read that as covering the documentation and the
  model outputs we reproduce here with attribution, not as a code license.
- **Source repository**: the paper's figure README names
  `github.com/epoch-research/gate` at commit `6b825f8dee4f6a0d56b382f0f7c8190756e6379a`.
  `git ls-remote` on that URL (and on `GATE`, `gate-model`, `gate-playground`,
  `epoch-gate`, `ai-economic-model`, `takeoff-model`) asks for credentials, which for
  GitHub means private or absent. It was not reachable on 2026-10-25. No public GATE
  source was found.

## How to run

Fast checks (no network, no solving, part of `make check`):

```sh
python3 research_notes/external/epoch-gate/tests/test_epoch_gate.py
```

Full rerun of the official solver (needs network for the bundle and Node >= 20; about
100 s for the ten jobs):

```sh
cd research_notes/external/epoch-gate
official/fetch_bundle.sh /tmp/gate                                  # fails if the hash changed
node official/run_official.mjs /tmp/gate/gate.js /tmp/gate/run.json official/jobs.json
python3 official/compare_official.py /tmp/gate/run.json            # vs data/baseline_target.json
python3 official/diagnostics.py                                    # convergence and sensitivity summary
```

The `epoch-gate` workflow (`.github/workflows/epoch-gate.yml`, run by hand) does the
same and uploads the run as an artifact. It never commits. `data/baseline_target.json`
was produced by `official/extract_target.py` from a local run on 2026-10-25 (Node
v22.22.0); a second local run from a fresh download was bit-identical.

## Baseline target (native units)

Jobs are in `official/jobs.json`; values in `data/baseline_target.json`. Step index t
reports the state t+1 model years after the initial state (`labor[t] = L0 exp(g_L (t+1))`
exactly); the paper puts the initial state at the start of 2025, but we do not attach
calendar years. Default preset:

| step | GWP (USD/yr) | f automated | Q compute stock (FLOP/yr) | C_T largest run (eFLOP) | compute investment (USD/yr) | share of output to compute | to capital + HW R&D + SW R&D |
|---|---|---|---|---|---|---|---|
| 0 | 1.308e14 | 0.100 | 5.266e28 | 9.074e27 | 1.255e13 | 0.096 | 0.145 |
| 2 | 1.571e14 | 0.318 | 7.419e29 | 2.913e30 | 1.893e13 | 0.120 | 0.079 |
| 4 | 2.594e14 | 0.585 | 6.485e30 | 9.002e31 | 3.723e13 | 0.144 | 0.067 |
| 6 | 4.450e14 | 0.784 | 4.059e31 | 1.379e33 | 6.659e13 | 0.150 | 0.106 |
| 8 | 9.067e14 | 0.946 | 2.056e32 | 1.318e34 | 1.340e14 | 0.148 | 0.125 |
| 9 | 1.427e15 | 1.000 | 4.483e32 | 3.656e34 | 2.036e14 | 0.143 | 0.120 |
| 10 | 2.507e15 | 1.000 | 9.659e32 | 9.599e34 | 3.167e14 | 0.126 | 0.114 |
| 15 | 1.452e18 | 1.000 | 1.416e35 | 2.637e36 | 7.179e16 | 0.049 | 0.122 |
| 20 | 6.053e21 | 1.000 | 5.359e38 | 2.152e39 | 7.516e19 | 0.012 | 0.136 |

Milestones (first step at which ...):

| preset | f >= 0.5 | f >= 0.9 | f = 1 | GWP growth >= 30%/yr | peak GWP growth (step) |
|---|---|---|---|---|---|
| Default (T = 1e36.5, HW returns 5.2, SW returns 1.25) | 4 | 8 | 9 | 5 | 515%/yr (19) |
| Conservative (1e38, 1, 1) | 5 | 13 | 15 | 10 | 388%/yr (22) |
| Aggressive (1e33, 7.1, 2) | 2 | 3 | 3 | 1 | 582%/yr (16) |

**Tolerances.** (1) Rerun vs playground cache and rerun vs committed target: relative
1e-12 (achieved: 0; WebAssembly floating point is deterministic). (2) For any
independent re-solve (follow-up), the optimizer itself only pins trajectories to about
2% over steps 0-20 (see below), so the target there is: milestones exact, trajectory
values within 5%, objective within 1e-3 relative. These are proposals; nothing has been
compared against them yet.

## Convergence and sensitivity (from `official/diagnostics.py`)

The solver is sign-gradient descent with Adam-style steps (`method:
sign_gradient_descent`, learning rate 0.6 to 0.01, `maxiter` 40, `fun_tol` 0.02) over a
160-year optimization horizon (`objective_horizon_multiplier` 2 x 80 years). It
*minimizes* `objective` (it falls along `objective_path`); the paper's two sanity checks
(simpler policy class; log-spliced utility) both score worse than the main solution in
every run, so both pass.

| job | objective | max rel. diff vs default, steps 0-20 | milestone changes |
|---|---|---|---|
| maxiter 20 | 0.546321 | 18% (compute stock, step 20) | none |
| maxiter 40 (default) | 0.546174 | - | - |
| maxiter 80 | 0.546135 | 2.0% (compute investment, step 14) | none |
| train_reqs 36.4 | 0.539888 | 36% (compute investment, step 14) | GWP growth >= 30%: step 5 -> 4 |
| train_reqs 36.6 | 0.552639 | 29% (compute investment, step 14) | none |

- Every run stops at `maxiter`, never at `fun_tol`. Over the last 10 iterations of the
  default run the objective still moves 2e-5 (relative). The trajectory is therefore
  optimizer-limited at the percent level; milestones (integer steps) are not.
- A 0.1-OOM change in the AGI training requirement moves compute investment at step 14 by
  about 30% in both directions while milestones barely move. That is larger than the
  maxiter effect, so it is probably real sensitivity rather than noise, but we have not
  separated the two (follow-up). Epoch's own documentation warns that results can be
  optimizer artefacts and suggests exactly this perturbation test.

Cheap comparisons (exploratory, default preset, one parameter changed; objectives are not
comparable across different worlds):

| job | f = 1 at step | GWP growth >= 30% at step | peak GWP growth |
|---|---|---|---|
| default | 9 | 5 | 515%/yr |
| no labor reallocation (`labor_reallocation_friction` on) | 9 | 9 | 514%/yr |
| R&D wedge 8 (planner sees 1/8 of R&D returns; the playground table's default for the add-on) | 10 | 6 | 446%/yr |
| planner certain only 80% of tasks are automatable (`max_frac_beliefs` [{prob 1, max_frac 0.8}]) | never (f caps at 0.8) | 5 | 52%/yr |

These are single runs, not the comparison #13 asks for; see "Not done".

## Discrepancies

- **D1. Source not public.** The paper cites a private repository commit. We ran the
  compiled solver instead; we cannot tell whether the bundle corresponds to commit
  `6b825f8`. The bundle's parameter table and the paper disagree in places (D4), so it is
  probably later.
- **D2. Cached presets carry extra fields.** The playground's cached Conservative and
  Aggressive runs have ten output fields (`gwp_growth_per_year`, `savings_rate`, `gwp3`,
  ...) that the shipped solver does not produce; the Default cache does not. On every
  shared field the values are identical. So those two caches were made by a build with
  more reporting but the same numbers.
- **D3. FLOP gap mapping.** The paper defines the automation threshold as T/10^Delta with
  Delta in OOMs; the playground's `flop_gap_frac` is a fraction. Across all ten runs the
  solver's threshold satisfies Delta = flop_gap_frac x (log10 T - 16.608061) exactly. The
  paper says the fraction is relative to "the initial distance in OOMs between the largest
  initial training run and AGI training requirements", but log10 of the initial largest
  run is 25.70, not 16.61. The origin of 16.608 is not explained.
- **D4. Parameter defaults differ between paper and playground.** FLOP gap fraction: paper
  table 0.55, paper text 0.52, playground 0.55. R&D: the paper gives lambda_H 0.14,
  phi_H 0.0769, theta_H 0.192, lambda_S 0.0625 (range printed as "0.14 to 1"), phi_S 0.32,
  theta_S 0.0307; the playground uses `hardware_returns` 5.2 and `software_returns` 1.25
  (described as lambda/phi), lambda 0.14 for both, and a "researcher elasticity" 0.35 that
  the paper does not have. Paper lambda_H/phi_H is 1.82, not 5.2. The playground's R&D law
  is therefore not the paper's equation as printed, and we could not reconstruct it (E5,
  E6 in EQUATIONS.md).
- **D5. Discretisation.** The paper writes continuous-time laws. The solver steps capital
  and compute as K' = K e^(-delta) + I' (exponential depreciation over the year, the
  entering year's effective investment added undepreciated). The naive forward-Euler
  reading is off by 0.22% per year for capital. Both are recorded in tests.
- **D6. `compute` is the physical stock.** The solver's `compute` follows the physical
  stock law Q (FLOP/year), not the effective-compute law C = Q S; effective compute is not
  reported as such. `training_compute + runtime_compute` is 19% of Q at step 0, peaks at 46% (step 10) and
  falls toward 0 later in the default run. Resolved in #35 (E7): the two exhaust usable compute g(Q) at the start of
  each step, and the share falls once g(Q) saturates at the heat limit. Q can exceed the 2e38 FLOP/year heat limit (Aggressive, step 20:
  2.7e41); the paper caps only usable compute g(Q).
- **D7. TFP after automation.** Y / (K^alpha T^(1-alpha)) with T read as the solver's
  `cognitive_ces_term` is constant (514.0) while f = f_init and drifts down once automation
  starts (default: 455 at step 10). So `cognitive_ces_term` is not the full task composite
  of the paper's production function once digital workers enter, or A is not constant.
  Unresolved.
- **D8. Initial jump.** Software efficiency is 8.43 at step 0 against S(0) = 1, and GWP is 1.308e14 against Y(0) = 1.10e14 in the parameter
  table, with f still at f_init. Not investigated.

## Who decides, modes, interfaces

- [MODES.md](MODES.md): GATE's decision-maker is a social planner maximizing a
  representative household's utility. No labs, states, firms or AIs. Mapping to the #5
  contract: human-run lab partial; sovereign-capable and sovereign unsupported. The
  contract's `AD-GATE` entry in `systems/modes.yaml` is updated to this verified mapping.
- [INTERFACES.md](INTERFACES.md): ownership, budget, compute, labor, physical-resource and
  time units, and where coupling GATE with AI Futures (#14) would count the same feedback
  twice.
- `evidence/records.yaml` (#8 contract): `EV-GATE-PAPER-2025` (kind
  `source_model_assumption`) and `EV-GATE-PLAYGROUND-2026` (kind `source_model_output`, the
  pinned bundle and the baseline target). Neither is an observation.

## Not done (Done-when boxes of #13)

1. Pin paper/model/parameters/license; independent implementation labelled with an
   equation map: **done** (with D1: no public source).
2. Small baseline target in native units with tolerances and optimizer diagnostics:
   **done.**
3. Reproduce the target before adding sovereignty/control: **done for the official
   solver**; an independent re-solve of the planner problem is not attempted.
4. Who allocates and whose objective: **done** (MODES.md).
5. Mode mapping with unsupported modes marked: **done** (MODES.md, `AD-GATE`).
6. Ownership/budget/compute/labor/physical/time interfaces; no double counting with AI
   Futures: **specified** (INTERFACES.md, "Resolution (#35)"). The compute units are
   resolved, each loop has one owner in `systems/modes.yaml`, and there is a checked worked
   coupling (`coupling_example.py`). AIFM is not rerun on the passed series, and the
   calendar mapping of step 0 is open.
7. Bottleneck/partial-automation, allocation and feedback-off comparisons; do policy
   conclusions survive: **not done.** Three single exploratory runs above. GATE has no
   feedback-off switch; one would have to be built (e.g. fixing investment shares at their
   initial values), and that is outside the source model.
8. Separate source replication, historical component validation and hypothetical
   extensions in status and outputs: **partly** (status table above; no historical
   component validation exists yet).
