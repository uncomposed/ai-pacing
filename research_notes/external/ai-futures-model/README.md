# AI Futures Model replication (issue #14)

[[ai gen]] First reproducible milestone, 2026-10-25. Status words follow
`CONTRIBUTING.md`: what is shown here is **source-model replication** and some
**counterfactual analysis inside the source model**. Nothing here is empirical
validation, and no date in this folder is a forecast by this project.

## Purpose

Reproduce the [AI Futures Model](https://github.com/AI-Futures-Project/aifm-public)
(AIFM) as a distinct development model, keeping its assumptions intact, before anything
couples it to the pact solver. Keep the runnable model separate from the AI 2027
narrative and from historical measurements.

## Status

| layer | status | where |
|---|---|---|
| source pinned | done: commit `1c40ecdb` (2026-09-09, MIT), config chains, input files by SHA-256 | `SOURCES.yaml`, `fetch_upstream.sh` |
| source-model replication: reference trajectory | **reproduced**: 21 golden series within rtol 1e-3 (observed max relative difference 1.6e-6, horizon lengths; all others below 1.3e-8); AC 2027.786 and AI2027-SC 2028.404 within 1e-10 years | `results/reference_trajectory.json` |
| source-model replication: seeded milestone distribution | **consistent with the published forecast within sampling tolerance**: 24 of 24 comparisons (p10/p50/p90 and achievement rate for six milestones) pass at z = 3; medians within 0.06 years. Not draw-by-draw identical (not expected) | `results/seeded_published-daniel-08-16-26_n1000.json` |
| numerical correctness | not checked beyond the upstream's own tests: 594 pass at the pin with Python 3.14.6, numpy 2.4.1, scipy 1.17.0; `tests/test_capability_cdf2d.py` does not collect because it needs matplotlib, which the upstream requirements omit | |
| empirical validation | **none**. Held-out comparison with METR (#12) and the #8 protocol is a follow-up | |

## What was run

All with Python 3.14.6, numpy 2.4.1, scipy 1.17.0 (the upstream pins) on Linux x86_64.

1. **Reference trajectory** (`aifm_runner.py reference`): the upstream defaults
   (identical to `tests/golden_data/default_trajectory.json` `_generation_parameters`)
   over [2015, 2050], compared series by series with the golden files.
2. **Seeded milestone distribution** (`aifm_runner.py rollouts --preset
   published-daniel-08-16-26 -n 1000`): the upstream `batch_rollout.py` with the flattened
   config exported next to the published Daniel 08-16-26 forecast, its input series
   (`inputs/2200.csv`) and its seed (20260810). Summarised with the upstream's statistic
   definitions and compared with the published 10,000-sample statistics.
3. **Feedback-off baseline** (`aifm_runner.py feedback-off`): the upstream's own
   human-only counterfactual at default parameters over [2017, 2200], with r_software
   kept and refit.
4. **Alternative calibration anchors** (`aifm_runner.py anchors`): the same defaults
   with each of the four AC anchor modes.

## Results

### Reference trajectory

Reproduced to about 1e-8 relative (`results/reference_trajectory.json`). Milestones at
default parameters, range [2015, 2050]: AC 2027.79, SAR 2028.37, TED-AI 2028.64,
SIAR 2028.80, ASI 2028.92. These are the source model's outputs at one parameter point.

### Seeded milestone distribution (`results/seeded_published-daniel-08-16-26_n1000.json`)

1,000 samples with the published run's config, inputs and seed (20260810), against the
published 10,000-sample statistics (9,612 successful). Statistic definitions are the
upstream's: unachieved milestones are placed at the simulation end (2200) before taking
quantiles; shares are draws under Daniel's elicited sampling measure, not calibrated
probabilities.

| milestone | p10 ours / published | p50 ours / published | p90 ours / published | achieved % ours / published |
|---|---|---|---|---|
| AC | 2026.90 / 2026.89 | 2027.92 / 2027.92 | 2031.63 / 2031.68 | 99.3 / 99.2 |
| AI2027-SC | 2027.29 / 2027.29 | 2028.85 / 2028.85 | 2039.44 / 2040.97 | 92.8 / 93.1 |
| SAR | 2027.21 / 2027.26 | 2028.94 / 2028.93 | 2037.18 / 2037.80 | 98.9 / 98.7 |
| SIAR | 2027.52 / 2027.55 | 2029.92 / 2029.97 | 2050.58 / 2051.53 | 97.7 / 96.9 |
| TED-AI | 2027.41 / 2027.46 | 2029.59 / 2029.61 | 2047.48 / 2048.06 | 97.5 / 96.9 |
| ASI | 2027.61 / 2027.63 | 2030.61 / 2030.63 | 2070.27 / 2073.46 | 95.2 / 94.4 |

All 24 comparisons pass the declared tolerance (`tolerances.json`: z = 3 on bootstrap
standard errors, sampling noise only). The check is tight at p10 and p50 (tolerances
0.07 to 0.67 years) and weak at p90, where unachieved runs at 2200 make the quantile
noisy (tolerances up to 38 years for AI2027-SC). So this replicates the centre of the
published distribution well and its upper tail only loosely.

Failures: 51 of 1,000 rollouts produced no result. 35 are the model's own rejection of
infeasible uplift beliefs in uplift-solved mode (3.5%; published: 388 of 10,000, 3.9%).
16 are the upstream's 30-second per-sample timeout, which depends on machine load (this
run shared four cores with other jobs); the published run had none outside
uplift-solved. Timeouts drop slow rollouts, which could bias the sample slightly.

### Feedback-off baseline (`results/feedback_off.json`)

Default parameters over [2017, 2200]. "Off" is the upstream's human-only counterfactual:
automation fraction 0, aggregate taste 1, coding labor = human FTEs; compute and labor
paths unchanged. A milestone's "off" date is when the off run first reaches the progress
level at which the full run crosses it.

| milestone | feedback on | off (same r_software 3.139) | off (r_software refit to 3.146) |
|---|---|---|---|
| AC | 2027.79 | 2028.07 | 2028.06 |
| SAR | 2028.38 | 2029.41 | 2029.39 |
| TED-AI | 2028.65 | 2031.22 | 2031.18 |
| SIAR | 2028.81 | 2033.52 | 2033.48 |
| ASI | 2028.93 | 2036.38 | 2036.32 |

Reading, within the source model only:

- AC arrives about 0.3 years later without any AI feedback. At these defaults the
  near-term path is driven by the exogenous compute and labor forecasts, not by
  recursive improvement.
- The feedback compresses AC-to-ASI from about 8.3 years to about 1.1 years. That
  compression is the model's takeoff claim, and it rests on the judgment parameters
  (taste slope, automation schedule, experiment-capacity asymptotes), not on fitted
  history.
- Refitting r_software barely matters (0.2%): with the default uplift belief the
  reconstructed historical AI contribution to 2024 software progress is small.
- Before 2026 the on and off paths differ by under 0.1 OOM, so the historical record
  cannot distinguish feedback-on from feedback-off at these defaults. This is the
  non-identifiability the issue's stopping rule asks to report; it has not yet been
  tested against held-out observations.

### Alternative calibration anchors (`results/anchors.json`)

Same default beliefs, different AC anchor:

| anchor | AC | SAR | TED-AI | ASI |
|---|---|---|---|---|
| uplift-solved (default) | 2027.79 | 2028.38 | 2028.65 | 2028.93 |
| revenue (USD 1e12/yr) | 2028.15 | 2028.76 | 2029.03 | 2029.34 |
| time-horizon (120,000 min) | 2028.39 | 2029.00 | 2029.30 | 2029.62 |
| ECI (250) | 2035.14 | 2036.36 | 2036.92 | 2037.52 |

The anchor choice alone moves AC by up to 7.4 years at fixed beliefs. In the observable
modes the doubling-time correction replaced the believed 5-month excess-uplift doubling
time with 6.3 (revenue), 7.2 (horizon) and 22.1 (ECI) months. Which parameters are
constrained by evidence and which by judgment is in `MECHANISMS.md`.

## Discrepancies and caveats

- **Upstream multiprocessing bug under Python 3.14 on Linux.** `batch_rollout.py` fails
  with "A SemLock created in a fork context is being shared with a process in a spawn
  context" (its `_NoDaemonProcess` subclasses the default-context `Process`, which
  Python 3.14 changed to forkserver on Linux). `aifm_runner.py` works around it by
  setting the global start method to `fork` before running the upstream script
  unchanged. `--mp-context fork` alone does not fix it.
- **The published forecast predates the pinned code.** It was exported 2026-08-10; the
  model changed before the 2026-09-09 release (for example the doubling-time correction
  rule). The repository has one public commit, so the exact code that produced it is not
  available.
- **Seeded draws are not bit-reproducible across machines** (upstream note on
  `multivariate_normal(method="svd")`), so the published comparison is distributional,
  with a declared sampling tolerance (`tolerances.json`), not draw-by-draw.
- **Start-date dependence.** AC is 2027.786 when integrated from 2015 (golden range)
  and 2027.787 from 2017 (Monte Carlo range): the initial condition `logE0 = TC(t0) - 1`
  is approximate, as the model guide says.
- The input series' provenance is a deleted upstream workbook; historical rows and
  forecasts are not distinguished row by row.

## Files

| file | what |
|---|---|
| `SOURCES.yaml` | pins: commit, licence, config inheritance, input files by SHA-256, published reference |
| `fetch_upstream.sh` | fetches the pinned commit (not vendored: about 108 MB with the website) |
| `aifm_runner.py` | runs the model and writes `results/*.json` with provenance |
| `aifm_summary.py` | statistic definitions and tolerance checks, no upstream import |
| `tolerances.json` | declared tolerances and their basis |
| `results/` | small reviewed summaries |
| `MECHANISMS.md` | research labor, compute, software efficiency, coding automation, research judgment in native units; latent versus observed; evidence versus judgment; bottlenecks |
| `modes.md` | decision authority and resource control on the #5 mode contract (the `AD-AIFM` entry in `systems/modes.yaml`) |
| `GATE_OVERLAP.md` | shared compute-investment and research-efficiency feedback with GATE (#13) |
| `../../../evidence/records.yaml` (`EV-AIFM-*`) | AIFM outputs as source-model-output records with `fitted_to` (#8 contract) |
| `tests/test_aifm.py` | fast checks in `make check` (pins, flags follow from numbers, summary functions) |
| `requirements-upstream.txt` | environment for running the upstream |

## How to run

```sh
cd research_notes/external/ai-futures-model
./fetch_upstream.sh                      # -> .upstream (git-ignored)
python3.14 -m venv .venv-aifm && .venv-aifm/bin/pip install -r requirements-upstream.txt
.venv-aifm/bin/python aifm_runner.py reference
.venv-aifm/bin/python aifm_runner.py feedback-off
.venv-aifm/bin/python aifm_runner.py anchors
.venv-aifm/bin/python aifm_runner.py rollouts --preset published-daniel-08-16-26 -n 1000   # about 4 CPU-s per sample
python3 tests/test_aifm.py               # what make check runs
```

The `aifm` workflow (`.github/workflows/aifm.yml`, started by hand) does the same on a
GitHub runner, also runs the upstream golden tests, and uploads `results/` as an
artifact. It never commits; compare the artifact with the committed files and commit
deliberately.

## Not done in this milestone

- Held-out comparison with dated METR observations (#12) and simple trend and
  compute-only baselines under the #8 protocol.
- Transition interface (knowledge, compute, assets, dependencies, intervention,
  identity; reversible transitions).
- Bottleneck stages beyond what AIFM represents (review, integration); `MECHANISMS.md`
  only records their absence.
- Parameter-by-parameter evidence audit (the table in `MECHANISMS.md` is a first pass
  from config comments).
- The `pinned-q2-daniel` preset (current config and inputs) has not been run locally;
  the workflow can run it.
