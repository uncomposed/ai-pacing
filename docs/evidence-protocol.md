# Evidence and validation contract

## Status

Infrastructure note for issue #8, written 2026-10-25. [[ai gen]] Status: `implemented`
(schemas, checkers, tests and one small reweighting run). Nothing here is empirical
validation, and no evaluation has been run under the protocol yet. The METR suite (#12)
is the first acceptance case.

Files:

- [`evidence/records.yaml`](../evidence/records.yaml): dated evidence records.
- [`evidence/protocol.yaml`](../evidence/protocol.yaml): evaluation rules, baselines,
  scoring rules and the forecast registry, which is empty for now.
- [`schema/evidence.schema.json`](../schema/evidence.schema.json): shapes of records,
  forecasts and outcome labels.
- [`tools/evidence_tool.py`](../tools/evidence_tool.py): checker and protocol helpers.
- [`tools/assumptions_tool.py`](../tools/assumptions_tool.py): now also checks roles,
  evidence links, outcome labels and parameter admission in the model's
  `assumptions.yaml`.
- `model/measure_sensitivity.py` and its outputs in `model/results/`.

`make check` runs all of it.

## 1. Roles for every influential input

Every PARAMS entry (`parameter_roles`) and every other influential input
(`other_inputs`: sampling measure, horizon, outcome predicate, equilibrium selection,
number of states, numerical settings, robust-design modifiers and the quantities derived
from them) has exactly one role:

| role | needs | count now |
|---|---|---|
| observed_measurement | `empirical_support`: observation records read in primary form | 0 |
| source_model_assumption | `source_model`: a record of the source model, with locator | 0 (`g` was one until the #11 recheck showed 0.35 is not a Metzger value) |
| project_assumption | nothing beyond its register entry | 76 |
| policy_choice | nothing; a human lever | 16 |
| derived | `derived_from`: other inputs | 3 |

No parameter is an observed measurement today. That is the honest state of the model,
not a gap in the check.

Stakeholder validation is recorded separately. Thirty-three parameters carry
`stakeholder_validation` naming the Cole answers behind them. It never counts as
empirical support. The checker rejects an input marked as an observation that has only
stakeholder validation, and it rejects citing a stakeholder statement as empirical
support. `human_validated` on an assumption also remains stakeholder validation, not
evidence.

## 2. Dated evidence records

A record gives:

- source and version;
- observation date and information-availability date. Partial dates are compared
  conservatively, using the latest day they allow;
- units, population and protocol;
- extraction provenance: method, exact locator, who extracted it and when;
- uncertainty;
- dependence on other records (`depends_on`) and the datasets it was fitted to
  (`fitted_to`);
- intended uses and uses it must not serve.

The record's `kind` and `reading` limit what a claim may cite it for:

| use | allowed kinds | extra condition |
|---|---|---|
| empirical_support | observation, observation_report | read in primary form |
| source_model_basis | source-model output or assumption, formal result | not unread |
| stakeholder_input | stakeholder statement | |
| motivation | any | |

Claims link to evidence as `{record, locator, use}`. A nonempty citation field is not
enough: every literature-based assumption in the register must carry such a link. Four
records are seeded from what the register already cites:

- Metzger et al.: a source-model output, read, Fig. 2 digitized;
- Turner et al.: a formal result, not read, so it may only motivate;
- the METR Hugging Face investigation: seeded as read only in secondary coverage, then
  read in primary form by #15 on 2026-10-25 (the counts matched);
- Cole's round-2 answers: a stakeholder statement.

#15 added seven records for the Hugging Face incident and its comparison case: the two
Hugging Face posts and the AISI incident blog (read in primary form), three OpenAI posts
(not read: HTTP 403), and the AISI technical report (kept unread on purpose as a
held-out resolution source). See
`research_notes/external/hugging-face-incident/`.

Model predictions and observations stay separate by kind. Two records are not
independent if one depends on the other, if they share an ancestor, or if they were
fitted to a common dataset (`evidence_tool.independent`).

## 3. Outcome-share labels

A claim whose text reports a share (a percentage or "k of n") must carry an
`outcome_label`. The label holds:

- the fixed interpretation *"share of draws under the stated sampling measure; not a
  calibrated probability"*;
- the sampling measure;
- the structural assumptions held fixed;
- the horizon;
- the predicate;
- Wilson 95% intervals, which the checker recomputes from k and n;
- the four uncertainty types: random outcome, parameter, model form and normative.

AR-H10 is the only register claim that reports shares, and it now carries a label.
`measure_sensitivity.py` writes the same label into its outputs.

## 4. Alternative measures and dependence

`measure_sensitivity.py` reweights the cached full-box robust-design runs: 192 Latin
hypercube draws and 38 lever designs. Each design is evaluated under 31 sampling
measures:

- each log-uniform marginal made uniform;
- alternative point-mass shares for `ell_inf`, `omega` and `f_E`;
- truncated ranges for `kill_pre`, `chi0`, `q` and `B_R`;
- four Gaussian-copula dependence structures, and all four together.

There are no new solves. Results are in
`model/results/measure_sensitivity.md` (and `.json`):

- 28 measures are identified (ESS of at least 30). Three are not: making `Kmax`,
  `omega` or `f_E` uniform puts almost all weight on a few draws.
- Across identified measures the best stack's share ranges from 0.025 to 0.194, against
  0.078 under the sampled measure. Its rank among the 38 designs moves between 2 and 8.
  The top design changes under one measure, on a tie. The best stack never falls to or
  below the base design.
- Many designs differ by one or two holding draws, so most rank changes are within
  noise.
- Alternatives the sample cannot represent are listed and not estimated: `chi0` above
  0.5, point masses on other parameters, wider ranges, and dependence on unsampled
  parameters.

The shares are not averaged over measures: no measure is preferred, so the range is the
result.

Draw identity: the cache stores outcomes but not draws (#6), so the draws are
regenerated. One solver batch of `full__base` (16 of 192 draws) was re-solved with
numpy 1.26.4 and matched the cache exactly on `act0`, with `att` within 7.5e-16. The
other draws were not re-solved.

Follow-up: a full comparison with fresh draws under widened ranges and new point masses
needs new solves through `sims.yml`. It has not been run.

## 5. Historical-evaluation protocol

`evidence/protocol.yaml` fixes these rules:

- `P-CUTOFF`: each forecast has an information cutoff, and every input must have been
  available by then (checked).
- `P-REVISIONS`: a revision is a new record; the old one is kept and scores are
  reported per vintage.
- `P-ROLLING`: rolling origins over cutoffs and horizons declared in advance.
- `P-BASELINES`: compare against `B-FLAT`, `B-LOGLINEAR` and, where defined,
  `B-COMPUTE`. A model is not promoted unless it beats them robustly.
- `P-SCORING`: absolute log error, the 80% interval score and coverage.
- `P-CONTAMINATION`: no post-cutoff inputs, calibration targets or tuning, and no
  double counting of models fitted to the same data.
- `P-SELECTION`: report everything that was tried.
- `P-LABEL`: retrospective versus locked forecasts. A locked forecast needs a commit
  hash, and one whose outcome was already observed when it was issued is rejected as
  mislabelled (checked).

`evidence_tool.py` provides `rolling_origins`, the two simple baselines,
`interval_score`, `abs_log_error`, `wilson` and the date and independence checks. All
are tested on synthetic cases.

## 6. Parameter admission

A PARAMS entry added after 2026-10-25 needs an `admission` record:

- `basis`: observable, external_model_mapping or consequential_omission;
- `evidence_path`;
- `falsifier`;
- `decision_impact`.

The 83 existing entries are listed as grandfathered: they were not admitted under this
rule. The stopping rule of #8 applies. Adding Monte Carlo draws does not make an
unsupported distribution supported, and quantities known only by bounds are reported as
ranges.

## 7. What this does not establish

- No empirical likelihood, calibration or hindcast has been run. The protocol is
  machinery until #12 uses it.
- The evidence records describe how sources were read. Of the four seeded records, only
  the METR investigation (after #15's primary reading) is usable as empirical support,
  and then only for the uses its record allows.
- Reweighting explores alternative measures only within the sampled support, with the
  precision its ESS allows.
