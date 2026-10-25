# AI Futures Model: mechanisms in native units

[[ai gen]] Written 2026-10-25 from the code and model guide at the pinned commit
`1c40ecdb` (`progress_model/`, `progress_model/README.md`). File and line references are to
that commit. This describes what the source model assumes. It does not endorse it, and
nothing here is validated against observations.

## State, time and the one capability scale

- Time `t`: decimal calendar years.
- `logE` ("progress"): log10 of **cumulative effective compute**, in OOMs. Every
  capability schedule (automation, taste, horizon, revenue, ECI, milestones) is a function
  of this one scalar.
- `RS` (research stock): accumulated software-research effort, in the model's effort
  units (`RS_0 = RE_0^2 / (dRE/dt)_0` at the start of the data; `integration.py`).

```
SE = r_software * log10(RS / RS_0)            software efficiency, OOMs ("2025-FLOP per FLOP")
EC = TC(t) + SE                               effective-compute rate, log10 FLOP/yr
d(logE)/dt = 10^(EC - logE) / ln 10           progress_rate.py:444-448
d(RS)/dt   = RE(t, logE)                      research effort, the only place AI feeds back
```

`TC(t) = log10(training_H100e(t) * 1.262e22)`: instantaneous frontier training capacity
in FLOP/yr (`config.FLOP_PER_H100E_YEAR = 0.4e15 FLOP/s * 3.15576e7 s`).

## The five mechanisms

| mechanism | native quantity and unit | how it enters | exogenous or endogenous |
|---|---|---|---|
| research labor (human) | `L_HUMAN`, FTEs (input series) | CES with AI coding labor (`rho_coding_labor = -2`), then raised to `parallel_penalty = 0.5` to give serial coding labor | exogenous path; never responds to AI |
| compute | `inference_H100e`, `experiment_H100e`, `training_H100e`: H100-equivalents running at a time (rates, not stocks) | inference compute powers AI coding labor; experiment compute enters research effort as `experiment_H100e^0.655` in a CES with serial coding labor; training capacity sets `TC(t)` | exogenous paths, supplied by the input CSV; **no compute-investment feedback inside the model** |
| software efficiency | `SE`, OOMs of effective FLOP per physical FLOP; `r_software` (dimensionless returns to research stock), calibrated so the software-progress rate at 2024.0 equals `software_progress_rate_at_reference_year = 1` OOM/yr | `10^SE = (RS/RS_0)^r_software` multiplies training compute | endogenous (through `RS`) |
| coding automation | automation fraction `A(logE)` in [0, 1], a logistic in progress (`automation_logistic_asymptote = 1.1`, clipped); AI coding labor from inference compute on an optimal-CES task frontier (`coding_labor_mode = optimal_ces`, `coding_automation_efficiency_slope = 3` OOMs per anchor-progress-year) | raises serial coding labor; the serial uplift `M` is the elicited observable (2.0 at 2026.578 with a 5-month excess doubling time, default) | endogenous in `logE` |
| research judgment ("research taste", experiment selection) | AI taste in SDs of the human researcher distribution, rising linearly in progress (`ai_research_taste_slope = 3` SD per anchor-progress-year; 0 SD at AC); human taste is a bounded normal with median-to-top (99.9th pct) multiplier 3.97 and `taste_limit = 16` | aggregate taste `E[max(T, F)]` multiplies research effort | endogenous in `logE` |

Research effort is `RE = taste_aggregate * CES(experiment_H100e^0.655, serial_coding_labor)`
(`progress_rate.py:compute_research_effort`; `rho_experiment_capacity` and `alpha` are
solved from `inf_labor_asymptote = 15`, `inf_compute_asymptote = 1000`,
`inv_compute_anchor_exp_cap = 2.8`).

**Feedback-off** (`params.human_only`): `A = 0`, aggregate taste 1, coding labor is human
labor only. All exogenous paths are unchanged. See `results/feedback_off.json`.

## Latent versus directly observed

| quantity | status | basis |
|---|---|---|
| `logE`, `RS`, `SE`, `r_software` | latent | no direct measurement; `r_software` is calibrated to an elicited rate |
| automation fraction, AI taste (SD), aggregate taste | latent | schedules in progress; slopes are elicited beliefs |
| milestones AC, AI2027-SC, SAR, SIAR, STRAT-AI, TED-AI, ASI, AIR-nx | latent | threshold crossings of latent schedules (`_impl.py` `compute_milestones`); none is defined by an observable test |
| serial coding uplift `M` at the reference date | elicited, nominally observable | judgment (Daniel Q2: 2.0, 80% CI 1.25-5); uplift studies exist but the value is not read from one |
| METR p80 time horizon at 2026.269 (186 min) and its doubling time (0.333 yr) | observed (via METR), then elicited | METR measurement as stated in config comments; doubling time is a geomean of an elicited CI |
| revenue at 2026.374 (USD 4.7e10/yr) and its growth factor (5/yr) | observed level, elicited growth | Epoch/company revenue series; growth elicited |
| ECI at 2026.525 (162) and growth (15/yr) | observed level (Epoch ECI), elicited growth | |
| input series (labor FTEs, H100e) | historical estimates then forecasts | upstream workbook, not public; no per-row provenance |
| AC thresholds (`ac_time_horizon_minutes` 1.2e5, revenue 1e12 USD, ECI 250) | judgment | elicited; they define AC in the observable modes |

So the observable anchors constrain *levels at a date*; every rate of change past the
present, every milestone threshold and the shape of every schedule is judgment.

## Which parameters are constrained by evidence and which by judgment

Our reading of the pinned defaults (`config.py` comments name each elicitation):

- **Constrained (in part) by observations**: present horizon level, present revenue level,
  present ECI level, the historical part of the input series, and the 2024 software
  progress rate of about 1 OOM/yr (a literature-based estimate of algorithmic progress;
  the source is not cited in the code).
- **Judgment (elicited, with 80% CIs in the sampling configs)**: serial uplift and its
  doubling time, horizon doubling time and its decay, AC thresholds, taste slope and
  taste distribution, `ted_ai_m2b`, experiment-capacity asymptotes, `parallel_penalty`,
  CES elasticities, automation asymptote and efficiency slope, gap, and all forecast
  years of the input series.
- **Calibrated (derived)**: `r_software`, `progress_at_aa` (except in uplift-solved, where
  it is an output), automation-schedule anchors, experiment-capacity CES parameters.

`results/anchors.json` shows how much the anchor choice alone moves AC at default
beliefs: 2027.8 (uplift-solved), 2028.1 (revenue), 2028.4 (time-horizon), 2035.1 (ECI).

## Research bottlenecks represented and not represented

| stage (issue #14) | in AIFM | how |
|---|---|---|
| goal selection | partly | research taste multiplies effort; it is described as experiment-selection skill, so it covers choosing experiments rather than research goals |
| coding | yes | serial coding labor from human FTEs and AI labor from inference compute |
| experimentation | yes | experiment compute in the research-effort CES |
| evaluation / review | no | no separate stage; effort converts to research stock directly |
| integration into later systems | no | software efficiency applies immediately to all training compute (`EC = TC + SE`) |

There is no distinction between more code, agent-hours or experiments and *validated*
advances incorporated into later systems: every unit of research effort adds to `RS`,
and `RS` maps deterministically to efficiency. A bottleneck at review or integration
would cap the feedback that AIFM lets run freely. This is a structural assumption to
carry into any coupling, not something the model tests.

## What the model does not decide

Resource paths are exogenous (`progress_model/README.md`, "Modeling assumptions"):
"AI feedback changes research productivity; the ODE does not itself decide future labor
or compute budgets." No actor chooses anything. The optional SOS mode freezes labor and
compute at a milestone; the pause transform and the Plan A covert-project simulation are
separate scenario tools, not decisions inside the ODE. See `modes.md`.
