# AIFM against dated METR observations: held-out comparison (#45)

[[ai gen]] Written 2026-10-25. **Result: no held-out test is possible yet**, so nothing is scored (the
#45 stopping rule). Feedback-on and feedback-off are **not identifiable** from METR's observations, even in
sample. Nothing here is empirical validation of AIFM or of any baseline.

## Why no observation is held out

An observation can test AIFM only if it is independent of AIFM's inputs (`fitted_to` and `depends_on` in
`evidence/records.yaml`), became public after AIFM's information cutoff, and is on the suite AIFM's horizon is
expressed in. `heldout_audit.py` checks all three for every METR time-horizon record (15 of them, from #12).
None passes:

- **Cutoff.** AIFM has one public commit, `1c40ecdb` of 2026-09-09; no earlier vintage of its code, inputs or
  elicitations is public, so its information cutoff cannot be placed earlier. Its forecasts were elicited in Q2
  2026 (present day 2026.578) and the published Monte Carlo was exported 2026-08-10. The latest METR value is
  from 2026-05-08. METR's page says it is no longer actively updated (last updated 2026-09-08), and its TH1.0 and
  TH1.1 result files were unchanged on 2026-10-25 (same sha256 as in `../metr-time-horizons/sources.sha256`).
- **Inputs.** AIFM's bundled `inputs/metr/benchmark_results_1_1.yaml` is byte-identical to METR's published TH1.1
  file (sha256 `aae31902...`): the post-correction TH1.1 records `EV-METR-TH11-2026-03-03`, `-04-10`, `-04-15`,
  `-05-08`, plus three TH1.0 values that METR's file carries (GPT-2, davinci-002, gpt-3.5-turbo-instruct; in
  `EV-METR-TH10-2026-03-03`). At default parameters the horizon curve is anchored at `present_horizon` 186 min
  at 2026.269 (Claude Mythos Preview's p80, `EV-METR-TH11-2026-05-08`), and its doubling time (Daniel's Q2
  median of 4 months) was elicited with METR's published trend in view (METR's own from-2023 doubling time on
  this file is 128.7 days, 4.2 months). The bundled file itself is read by the code only for parameters left
  unset and for the `metr_mse` diagnostic. The two AIFM output records now cite those primary records in
  `fitted_to` (TH1.1) and `depends_on` (TH1.1 and the TH1.0 batch), replacing the bundled-copy placeholder.
  The pre-correction TH1.1 values are earlier fits of the same runs and are linked to the later records by
  `depends_on` in #12's records, so they are not independent either.
- **Suite.** TH1.0 values are not in AIFM's inputs apart from the three above, but they are on another task
  suite: comparing them with AIFM's TH1.1-anchored horizon would need a cross-suite mapping that does not exist
  (#12; the METR records' `not_for`). They were also all public before AIFM's cutoff.

| records | independent of AIFM outputs | public after 2026-09-09 | on TH1.1 | held out |
|---|---|---|---|---|
| 8 TH1.0 batches (2025-03-19 to 2026-03-03) | no (revision chain shares the TH1.0 batch AIFM bundles) | no | no | no |
| 3 pre-correction TH1.1 batches | no (earlier fits of the same runs) | no | yes | no |
| 4 post-correction TH1.1 batches | no (`fitted_to`) | no | yes | no |

So the scoring under `evidence/protocol.yaml` that #45 asks for has no data to run on. A retrospective
comparison on these observations would be an in-sample fit, and is not reported as a test.

## What AIFM would have to beat (from #56)

The per-model holdout (`../metr-time-horizons/results/permodel.md`) gives the comparators any held-out AIFM
score would face on the same TH1.1 targets: mean absolute log error, as first published, 0.373 (B-FLAT), 0.355
(B-LOGLINEAR), 0.402 (B-COMPUTE) for p50 and 0.394, 0.325, 0.313 for p80, over 5 models. AIFM's horizon is a
p80. No baseline beat the others robustly; B-COMPUTE was not promoted. AIFM was not scored on these targets:
all five are in its inputs, and Claude Mythos Preview is its anchor.

## Non-identifiability of feedback on and off (in sample)

`results/horizon_identifiability.json` (`aifm_runner.py horizon-identifiability`; default parameters; pinned
upstream, Python 3.14.6, numpy 2.4.1, scipy 1.17.0) evaluates AIFM's p80 horizon curve at the release date of
every model in its METR file, with feedback on (the full model, in the progress coordinates the curve was fitted
in, which reproduces the upstream's own `compute_metr_mse` exactly) and off (the upstream's human-only
counterfactual, with the 2024-calibrated `r_software` and with it refit, through the same curve). This is an
**in-sample diagnostic**, not a held-out test.

| | feedback on | off, same calibration | off, r_software refit |
|---|---|---|---|
| mean squared log error, p80, 26 observations | 1.222 | 1.202 | 1.225 |
| mean absolute log error | 0.944 | 0.930 | 0.943 |

- Over 2019 to 2026-04, the on and off curves are never more than 0.060 apart in log horizon (6%; 0.039 with
  the refit). METR's own 95% intervals on these p80 values have a median half-width of 0.81 in log terms.
- The fits are equal within any reasonable noise, and the off path fits marginally better. **Feedback-on and
  feedback-off fit the observed horizons equally well: they are not identifiable from METR data to date.** This
  confirms, in horizon units, the under-0.1-OOM progress gap #44 reported.
- AIFM's in-sample errors are large (mean absolute log error 0.94, a factor of about 2.6) because its curve is
  one anchor point with an elicited, decaying doubling time, not a fit to history; it overstates the horizons of
  2023 to 2025 models. That says how the model is built, not how it would forecast.

Where the paths separate, inside the source model only (statements about AIFM, not forecasts by this
project):

| decimal year | on (min) | off, refit (min) | log separation |
|---|---|---|---|
| 2026.75 | 530 | 470 | 0.12 |
| 2027.33 (about 2027-04-30) | 2,511 | 1,787 | 0.34 |
| 2027.83 (about 2027-10-31) | 15,268 | 6,558 | 0.85 |
| 2028.0 | 36,162 | 10,600 | 1.23 |

The separation reaches METR's typical interval half-width only around late 2027, at horizons of thousands of
minutes. METR calls TH1.1 values above 16 hours (960 min) unreliable. So on TH1.1, the observations that could
tell feedback on from off lie where the suite cannot measure reliably. AIFM's milestone thresholds are further
still (AC in time-horizon mode: 120,000 min, about 650 times the anchor), so no milestone-relevant trend can be
checked against METR observations yet.

## What would make a held-out test possible

1. New METR time-horizon values on TH1.1 published after 2026-09-09. METR has stopped updating the page, so
   this may not happen on this suite.
2. A successor suite with a published mapping to TH1.1, or AIFM restated in that suite's units.
3. A locked AIFM forecast (on and off) committed now and scored on whatever is published next, alongside the
   #12 locked baselines. This is the only route that does not depend on METR changing course.

## Files

| file | what |
|---|---|
| `heldout_audit.py` | the independence and cutoff audit; offline; its conclusions are tested in `tests/test_aifm.py` |
| `aifm_runner.py horizon-identifiability` | the in-sample on/off diagnostic (needs the upstream; run by the `aifm` workflow) |
| `results/horizon_identifiability.json` | its output, reviewed and committed |
