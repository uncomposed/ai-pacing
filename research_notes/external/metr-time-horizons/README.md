# METR time horizons: reproduction, dated observations and historical tests (#12)

[[ai gen]] Written 2026-10-25. First reproducible milestone for issue #12. METR is an evidence source
here, not a model of AI development or of sovereignty.

## Status

| question | status |
|---|---|
| Source replication | **Done for TH1.1 point estimates and trend statistics.** Every published TH1.1 p50 and p80 horizon (20 agents in METR's public runs) follows from METR's runs and method within the declared relative tolerance 1e-3 (largest difference 1.6e-4) using an independent numpy fit. Both published doubling times (128.744 and 187.778 days) are recomputed to 0.001 days from the published p50 values. METR's own code, run here at the upstream lockfile versions, gives the published point values to their 6 decimals. Bootstrap intervals: see Discrepancies. |
| Numerical correctness | The fitter's tests check parameter recovery, the first-order conditions of the penalized objective, the fractional-score identity and seeded bootstrap draws. Where the independent fit and scikit-learn differ, the independent fit has the lower objective (scikit-learn stops at its tolerance). |
| Empirical validation | **None.** The holdout and the per-model holdout (#56) are retrospective: their outcomes were public before the protocols were written. Both pre-declared verdicts are "not established". One prospective forecast is locked and unresolved. |

## What is here

| file | what |
|---|---|
| `fetch_sources.sh`, `sources.sha256` | Clones METR's `eval-analysis-public` (full history), checks out `52cb829`, extracts seven run-data vintages and downloads METR's published result files into a git-ignored cache; verifies every file by sha256. Network. |
| `horizon_fit.py` | Independent numpy re-implementation of METR's per-agent weighted logistic fit (scikit-learn's L2 objective, intercept unpenalized) and of their hierarchical bootstrap (task family, task, run; seed 42 + i). |
| `run_upstream.py` | Runs METR's own fitting and bootstrap code on the TH1.1 data, without DVC. |
| `reproduce.py` | Compares both with the published numbers; writes `results/reproduction.{json,md}`. |
| `batches.yaml`, `build_observations.py`, `data/observations.csv` | The dated observation table (below). Built from the cache; committed. |
| `holdout_protocol.yaml`, `holdout.py`, `results/holdout.{json,md}` | Retrospective rolling-origin holdout against flat and log-linear baselines. Offline. |
| `permodel_protocol.yaml`, `permodel.py`, `results/permodel.{json,md}` | Per-model holdout (#56): each new model forecast at its release date against B-FLAT, B-LOGLINEAR and the pre-declared B-COMPUTE. Offline. |
| `lock_forecast.py`, `forecasts/` | The locked forecast, its sha256 and its check. |
| `test_metr_time_horizons.py` | Fast checks (about 10 s, no network), run by `make check`. |
| `SOURCES.yaml` | Every source, pinned, with license and use. |

Evidence records `EV-METR-*` are in `evidence/records.yaml` (15 time-horizon batches and three
productivity studies), and the 24 retrospective and 4 locked forecasts are registered as
`FC-METR-*` in `evidence/protocol.yaml`. The `AD-METR` adapter in `systems/modes.yaml` now points here.

## How to run

```sh
cd research_notes/external/metr-time-horizons
python3 test_metr_time_horizons.py      # fast checks; also run by make check
python3 holdout.py --check              # recompute the holdout, compare with results/
python3 permodel.py --check             # recompute the per-model holdout (#56), compare with results/
python3 lock_forecast.py --check        # locked forecast hash and reproducibility

# Reproduction (network, pyyaml; the pinned CI venv for exact numbers)
bash fetch_sources.sh                   # cache in ./.cache, or $METR_CACHE
python build_observations.py            # rebuilds data/observations.csv (byte-identical with numpy 1.26.4)
python reproduce.py --bootstrap 1000    # about 2 minutes
python run_upstream.py --out results/upstream_th11.json   # METR's code; needs numpy 2.4.1, scikit-learn 1.8.0, pandas 2.3.3, joblib 1.5.3
```

The `metr-repro` workflow (`.github/workflows/metr-repro.yml`, run by hand) does all of this and uploads
the outputs as an artifact. It never commits.

## The reproduction target

METR's released analysis "Time Horizon 1.1" (blog 2026-01-29, corrected 2026-03-03), as published in
`metr.org/assets/benchmark_results_1_1.yaml` and computed from `reports/time-horizon-1-1` of
`eval-analysis-public` at `52cb829`. In source-native terms:

- **Quantity.** For each agent (a model with a scaffold), METR fits P(success) = sigmoid(a + b log2 t),
  with t the task's human time in minutes, by weighted logistic regression. The p-percent time horizon is
  the t at which the curve crosses p: p50 and p80, in **minutes of human expert time**. It measures task
  difficulty, not how long the agent works.
- **Human time.** The geometric mean of successful completion times of contracted experts (about five
  years' experience) given the same instructions as the agents; for some tasks an expert estimate or QA
  time. Only 5 of the 31 TH1.1 tasks of 8 hours or more have human baselines. METR says these times likely
  overstate what a high-context professional needs.
- **Tasks.** TH1.1: 228 tasks from HCAST, RE-Bench and short software tasks (SWAA); mostly software
  engineering, ML and cybersecurity; automatically scored. Task-suite commits: long tasks `799cc9c`, SWAA
  `f6cc840` (in the published file).
- **Weights and fit.** `invsqrt_task_weight` (diversity weighting across task families),
  `score_binarized`, regularization 1e-5 (scikit-learn `C = 1e5`). Before 2026-03-03 METR used 0.1, which
  shrank the slope; METR's page calls this a mistake it corrected.
- **Models and scaffolds.** The published file lists each model's scaffolds (column `scaffolds` of the
  table). Most TH1.1 agents ran METR's Inspect ReAct agent (`metr_agents/react`, with per-family
  solvers), but GPT-4 0314 carries `modular-public` and o1-preview `duet`; on TH1.0, GPT-5 ran in
  `flock-secret`. METR also mentions Triframe, Claude Code and Codex scaffolds. Scaffold, token budget and
  elicitation differ by model, so a horizon belongs to a model with a scaffold, not to weights alone.
- **Uncertainty.** 95% intervals from 1000 hierarchical bootstrap replicates over task families, tasks
  and runs. They are wide: often a factor of 2 to 5 between bounds; Claude Opus 4.6's p50 interval is
  317 to 3634 minutes around 719.

Results (`results/reproduction.md`):

- TH1.1 p50 and p80, 20 agents: independent fit within 1.6e-4 of the published value (tolerance 1e-3,
  declared in `reproduce.py`).
- Trend: METR's published doubling times recomputed from its own p50 values, as OLS of ln p50 on release
  date over frontier models, excluding values above 16 hours: 128.744 days since 2023 and 187.778 days
  for the stitched all-time series, both exact to 0.001. Without the 16-hour exclusion (which drops Claude
  Mythos Preview, 1045 minutes) they would be 124.8 and 182.7 days.
- TH1.0 (post-correction, 33 agents, a secondary check): 29 within 1e-3; four exceed it, by up to 1.7e-3
  (gpt-3.5-turbo-instruct p50; p80 of Claude 4 Opus, Claude 4 Sonnet and GPT-2 by 1.1e-3 to 1.3e-3).
  METR's scikit-learn code reproduces the published gpt-3.5-turbo-instruct value 0.599247 exactly, and our
  fit reaches a lower objective (by 0.015 on a scale of 8443), so the published value is scikit-learn's
  stopping point, not the optimum. Recorded as a failure against the declared tolerance, not hidden by
  widening it.

## The dated observation table

`data/observations.csv`: one row per (availability batch, model), 121 rows, with three dates kept apart:

- `model_release_date`: when the model was released (METR's x-axis);
- `runs_start`, `runs_end`: when METR's runs were made (from run timestamps; this is the observation date);
- `available`: when that value became public, with its basis in `batches.yaml` (METR's dated page
  entries, blog and arXiv dates, else the first upstream commit with the runs).

Values public before the 2026-03-03 correction are re-fitted from the run vintage public at the time,
with regularization 0.1; later values are copied from METR's files. Each batch is an evidence record.

What the dates show:

- **Late re-measurement of old models.** TH1.1's values for models from 2023 and 2024 come from runs made
  in September to November 2025. A test that places them at their release dates would let 2025 tasks and
  infrastructure into 2023 information sets. The holdout never does: a value enters an information set on
  its `available` date.
- **Page dates that predate the public runs.** For DeepSeek-R1, Grok 4, gpt-oss-120b, Claude Opus 4.1
  and Claude Sonnet 4.5, METR's page added the model before every run now in the public data. The value
  shown then came from runs that were replaced and are not public. These models enter at 2026-01-20 (late,
  not leaked); `build_observations.py` refuses any row whose runs end after its availability date.
- **Revisions.** The correction raised every p80 by 19% to 126% and moved p50 by -15% to +35% (largest
  increases for weak models; frontier p50s fell 5 to 15%). Run data were also replaced between vintages
  (Claude Opus 4.5 on TH1.0: 289 minutes in the 2026-01-20 runs, 278 with the same settings in the
  2026-03-05 runs). Old values are kept; scores are reported per vintage.
- **Missing values.** The pre-correction values of Claude Opus 4.6 and GPT-5.3-Codex (page 2026-02-20)
  are in no public vintage; they enter at 2026-03-03. GPT-5.4, Gemini 3.1 Pro and Claude Mythos Preview
  have published values but no public runs, so no run dates.

## The retrospective holdout

`holdout_protocol.yaml` was committed before `holdout.py` existed. Target: the frontier F(t), the largest
horizon among values public at t, per suite (TH1.0 and TH1.1 are never mixed) and per metric. Origins:
month-ends (7 for TH1.0 in 2025, 5 for TH1.1 in 2026); horizon 91 days. Baselines `B-FLAT` (F at the
cutoff) and `B-LOGLINEAR` (METR's trend method on the information set). Scores: absolute natural-log
error, 80% interval score on the log scale, 80% coverage; scored against values as first published and,
separately, the latest vintage.

Result (`results/holdout.md`): the declared verdict is **not established**. Under the declared rule
B-LOGLINEAR loses badly (mean abs log error 1.48 against 0.37 for TH1.0 p50; 1.90 against 0.51 for TH1.1
p50) and its intervals never cover. The cause is a design error in the declared rule, kept as a negative
result: it evaluated the trend at the target date minus the median publication lag of the whole
information set, and that set is dominated by old models scored long after release (TH1.0's paper models,
TH1.1's re-runs), so the trend was read more than a year in the past.

A post hoc variant that reads the trend at the target date (lag 0) is reported separately and is not part
of the verdict. It beats B-FLAT on TH1.1 (0.21 against 0.51 for p50) and at 182 days on both suites, but
not on TH1.0 at 91 days (0.41 against 0.37), so the same rule applied post hoc would still say "not
established". With 5 to 7 overlapping origins per series these are descriptions, not tests.

Saturation: METR calls values above 16 hours unreliable. Only Claude Mythos Preview (1045 minutes) is
above; dropping it (`NOSAT`) changes TH1.1 scores, not the verdict.

## The per-model holdout and B-COMPUTE (#56)

`permodel_protocol.yaml` was committed on its own, in
`6cea9d0edf0c796995e61398be5ef4fc715c0902`, before `permodel.py` existed and before any per-model score was
computed (its sha256 is checked by the tests, and the commit by a test that runs where history is available).
It is retrospective and not blind: every value in `data/observations.csv` and the #46 results had been read.

- **Targets.** Every model released on or after its suite's first publication date: 15 on TH1.0 (DeepSeek-V3-0324
  to Claude Opus 4.5) and 5 on TH1.1 (Claude Opus 4.6, GPT-5.3-Codex, Gemini 3.1 Pro, GPT-5.4, Claude Mythos
  Preview). Fixed by rule, none dropped. Older models were measured long after release and cannot be forecast at
  release from the same suite.
- **Cutoff.** The model's release date. The information set is every other model of the suite with a value public
  by then, at the value public then. The model's own value is excluded even when METR published it on release day
  (o3, o4-mini, GPT-5, GPT-5.1-Codex-Max); a sibling published the same day is not (o3 and o4-mini enter each
  other's sets).
- **Baselines.** B-FLAT: the largest value in the set. B-LOGLINEAR: METR's trend method on the set's
  frontier-advancing models, read at the target's release date (the #46 lag problem cannot arise). **B-COMPUTE**:
  the largest value grown from its model's release date at Epoch's frontier training-compute rate, 4.2x/year
  (90% CI 3.6x to 4.9x; `EV-EPOCH-COMPUTE-TREND-2024`, published 2024-05-28), elasticity 1 declared, not fitted.
  With an exponential compute path a fitted elasticity would make it identical to B-LOGLINEAR, so its only content
  is a growth rate from outside the horizon data. Per-model training compute was not used: Epoch has no estimate
  for most closed frontier targets and does not date its estimates.
- **Vintages.** V-FIRST (primary: inputs as public then, outcome as first published), V-LATEST (outcome at its
  latest value) and V-POSTFIX (inputs and outcome all at post-correction values, holding the 2026-03-03
  regularization revision fixed; uses revisions not public at the cutoff). Every TH1.0 target was first published
  before the correction and every TH1.1 target after it, so the declared split by correction date coincides with
  the suite split.
- **Rule.** "X beats Y" only with lower mean absolute log error in all 8 cells (two suites, p50 and p80, V-FIRST
  and V-POSTFIX), and for B-COMPUTE also at g = 3.6 and 4.9.

Result (`results/permodel.md`): **not established** for B-COMPUTE, and for B-LOGLINEAR against B-FLAT either way.
Mean absolute log error, V-FIRST (V-POSTFIX):

| suite, metric | targets | B-FLAT | B-LOGLINEAR | B-COMPUTE |
|---|---|---|---|---|
| TH1.0 p50 | 15 | 0.450 (0.418) | 0.487 (0.447) | 0.547 (0.523) |
| TH1.0 p80 | 15 | 0.509 (0.497) | 0.490 (0.447) | 0.677 (0.659) |
| TH1.1 p50 | 5 | 0.373 (0.385) | 0.355 (0.337) | 0.402 (0.379) |
| TH1.1 p80 | 5 | 0.394 (0.358) | 0.325 (0.308) | 0.313 (0.342) |

- B-COMPUTE is worst in every TH1.0 cell and loses to B-LOGLINEAR in 7 of 8 cells at every g. It wins only TH1.1
  p80 under V-FIRST (5 targets), and that win disappears under V-POSTFIX: it is partly an artefact of forecasting
  post-correction outcomes from pre-correction inputs. **B-COMPUTE is not promoted** (#56 stopping rule).
- All three baselines forecast a frontier value, and the targets include models that were never meant to be
  frontier (DeepSeek-V3-0324, DeepSeek-R1-0528, Gemini 2.5 Pro Preview, gpt-oss-120b, Kimi K2 Thinking: log
  errors 0.7 to 1.9 for B-FLAT and B-COMPUTE, 0.2 to 1.1 for B-LOGLINEAR, whose line sits below the frontier).
  That is a property of the declared target rule, not something adjusted after scoring. Mean errors of 0.3 to 0.7
  are factors of 1.4 to 2.
- Intervals: under V-FIRST and V-POSTFIX, B-LOGLINEAR's 80% intervals cover 67% to 73% of TH1.0 targets
  (53% for p80 under V-LATEST) and all 5 TH1.1 targets. B-FLAT and
  B-COMPUTE intervals need 3 earlier outcomes public by the cutoff: 4 TH1.0 targets have them, no TH1.1 target does.
- NOSAT (drops Claude Mythos Preview): changes TH1.1 numbers, not the verdicts.
- Targets are not independent (shared labs, scaffolds and information sets); with 15 and 5 targets these are
  descriptions, not a significance test.

The 20 forecasts are registered as `FC-METR-PM-*` in `evidence/protocol.yaml`, with inputs and resolution
records. These baseline errors are the comparators for AIFM in #45
(`research_notes/external/ai-futures-model/HELDOUT.md`).

## The locked forecast

`forecasts/FC-METR-TH11-LOCK-2026-10-25.json` (sha256 in `forecasts/SHA256SUMS`, added in commit
`b7875d76706f14134d76ec092a2b51102eb4246e`): B-FLAT and B-LOGLINEAR (lag 0) for the TH1.1 p50 and p80
frontier on 2027-04-30 and 2027-10-31, with all values and without values above 16 hours. For example,
p50 on 2027-04-30: flat 1045 minutes; trend 5595 minutes, 80% interval 2550 to 12276. The trend values
are far above the 16-hour range METR calls reliable for this suite, so they are statements about the fitted
line, not about what the suite can measure.

It is **unresolved if METR publishes no new TH1.1 value** (the page has not been updated since
2026-09-08), or switches suite. An unchanged frontier is not counted as a win for B-FLAT. If the PR is
squash-merged, `b7875d7` stays reachable from the PR's head ref; the sha256 is the durable check.

## Separate observables

Benchmark capability, adoption, realized task productivity and research output are different
quantities with different units and populations. None is converted into another here.

| observable | source here | unit | what it does not tell |
|---|---|---|---|
| benchmark capability | TH1.0, TH1.1 (`EV-METR-TH*`) | human-expert minutes at 50% / 80% success on self-contained, auto-scored tasks | productivity, adoption, messy or high-context work |
| realized task productivity | 2025 RCT (`EV-METR-RCT-2025`), 2026 follow-up (`EV-METR-UPLIFT-2026`) | ratio of implementation time with and without AI | capability ceilings; other developers, tasks or tools |
| benchmark-to-use gap | algorithmic vs holistic scoring (`EV-METR-ALGO-2025`) | share passing tests vs mergeable; minutes to fix | a general conversion factor |
| adoption | not measured here; the 2026 follow-up reports it as a cause of selection | | |
| research output | not measured | | |

The early-2025 RCT found tasks took 19% longer with AI (95% CI +2% to +39%) for 16 experienced developers
on their own large repositories, mostly with Cursor and Claude 3.5/3.7 Sonnet, while they believed they
were sped up by 20%. This is compatible with the time-horizon results rather than in conflict: METR's
tasks are self-contained and algorithmically scored, while the RCT's issues carried implicit requirements
(tests, documentation, style, review). METR's own follow-up found that Claude 3.7 Sonnet passed the
maintainers' tests on 38% of 18 such issues but produced no PR mergeable as-is, needing about 42 minutes
of fixing against 1.3 hours of maintainer time. Context and review overhead is one supported
reconciliation. The slowdown is not dismissed and not generalized: METR itself disclaims it for most
developers, other domains and later AI. The 2026 follow-up (57 developers) estimated -18% (CI -38% to
+9%) and -4% (CI -15% to +9%) time change, but METR calls the design unreliable: 30 to 50% of developers
withheld tasks they would not do without AI, pay fell to $50/h, and time reports fail for developers
running several agents at once. Those are selection and concurrency-accounting failures in a productivity
measurement, recorded as such, not a speedup estimate.

## Measurement caveats, selection and missing data

- **Selection of models.** METR says its reporting "is not a complete record": capacity-limited, it
  prioritizes models relevant to autonomy risk, measures some long after release and skips others. The
  frontier series is METR's frontier, not the world's. TH1.1 re-estimated 14 of 33 TH1.0 models.
- **Suite changes.** TH1.0 to TH1.1 changed tasks (73 added, 15 removed, 53 updated), human times and
  infrastructure (Vivaria to Inspect); METR's post-2023 doubling time moved from 165 to 131 days. Suites
  are scored separately; no cross-suite mapping is assumed.
- **Saturation.** Above 16 hours METR calls the suite unreliable; upper bounds are wide (Opus 4.6's p50
  upper bound is 3634 minutes). High-end values are measurement limits, not capability values.
- **Correlated tasks.** Tasks within a family share structure; METR's weights and family-level bootstrap
  account for part of it. Agents of the same lab and scaffold share failure modes; frontier points are
  not independent draws.
- **Model and scaffold revisions.** Scaffolds differ across agents; 2025 and 2026 runs replaced earlier
  ones for several models; the 2026-03-03 regularization fix revised every value. GPT-2's TH1.0 runs are
  imputed (`fake_gpt2_*` run ids, no timestamps).
- **Concurrency.** Benchmark runs are single-agent; the productivity follow-up found time accounting fails
  when developers run several agents concurrently. Nothing here measures multi-agent throughput.
- **Our own selection.** Every series, cutoff, sensitivity and the failed declared rule are reported
  (`results/holdout.md`), and the 24 retrospective forecasts are registered.

## Mode coverage

Against the mode contract (`systems/modes.yaml`, `docs/ai-development-modes.md`), these measurements are
evidence for `rd_capability` of model weights with a scaffold, under human-run evaluation (`AD-METR`):

- `MODE-HUMAN-LAB`: partial. Capability and productivity under human-run settings; nothing about effective
  control.
- `MODE-SOVEREIGN-CAPABLE`: partial at most. Bounded capability on a task suite; no test of sustained
  independent strategic action. No time-horizon level is mapped to `strategic_capability`.
- `MODE-SOVEREIGN`: not covered. Nothing here measures objective selection, custody of weights, compute or
  credentials, independent resource control, or industrial growth (#11). These measurements do not
  establish sovereignty.

## Discrepancies

1. **Bootstrap intervals.** Published 95% intervals are not reproduced exactly, by us or by METR's own
   code. METR's code at `52cb829`, run here on the public TH1.1 runs with 1000 replicates, gives intervals
   up to 8.3% (|log ratio| 0.083) from the published ones; our independent bootstrap (same hierarchy, same
   seeds 42 + i) agrees with METR's code run here to 0.18% (0.0018), and with the published intervals to a
   median of 1.5% (max 8.4%). So the published intervals are not what the public code gives on the public
   data. Why (another pipeline run, other data order or versions) is not established. No tolerance was
   declared for intervals before comparing; they are reported, not counted as replicated.
2. **TH1.0, four agents** above the 1e-3 tolerance (max 1.7e-3, above): scikit-learn's stopping point
   (checked by objective for gpt-3.5-turbo-instruct and GPT-4 0314 only).
3. **Model key.** GPT-5.3-Codex is `flamingo_2` in the runs and `gpt_5_3_codex` in the published file;
   Claude Opus 4.5 was renamed between vintages. Mapped explicitly in `batches.yaml`.
4. **Paper headline.** The arXiv abstract says Claude 3.7 Sonnet's horizon is "around 50 minutes"; our
   re-fit of the March 2025 data gives 59.0 minutes. The paper body was not read; not resolved.
5. **Declared holdout rule** was wrong (lag); kept, with the post hoc variant separate.
6. **Not reproducible from public data:** page values before 2026-03-03 (no archive reachable; Wayback
   connection reset), pre-correction values for Opus 4.6 and GPT-5.3-Codex, runs for the three models
   added after 2026-03-05.

## Not done (follow-ups)

- Optional RE-Bench fixed-budget comparisons and direct research-productivity observations.
- A cross-suite mapping. (Per-model forecasts and `B-COMPUTE`: done for #56, above; a per-model compute
  baseline with dated compute estimates is not possible from Epoch's data.)
- Scoring the locked forecast when, and if, METR publishes new TH1.1 values.
