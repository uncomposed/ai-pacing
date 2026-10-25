# AI Futures Model on the mode contract

[[ai gen]] Written 2026-10-25 against the mode contract of #5 (PR #19,
`systems/modes.yaml`, `docs/ai-development-modes.md`) and the AIFM code at commit
`1c40ecdb`. The adapter entry `AD-AIFM` in `systems/modes.yaml` is the machine-readable
form; this note gives the reasoning per dimension. Every mapping is a reading of the
source code, not evidence about the world.

## Decision authority and resource control

AIFM has no decision-maker. Its four resource paths (human coding labor in FTEs;
inference, experiment and training compute in H100e) are read from
`inputs/input_data.csv` and interpolated in time (`progress_rate.py:progress_rate_at_time`).
Nothing in the ODE changes them. The only endogenous loop is research productivity:
capability (`logE`) raises the automation fraction and AI research taste, which raise
research effort, which raises software efficiency, which raises `logE`.

So, in contract terms:

| dimension | AIFM | note |
|---|---|---|
| rd_capability | represented (latent) | automation fraction, AI taste (SD) and milestones are schedules in `logE`. A reading of levels, not a conversion rule: small `A` with uplift above 1 is `assists_humans`; AC ("fully automates an AGI project's coding work") is at most `automates_tasks` for coding; SAR ("fully automates AI R&D") is the model's counterpart of `automates_research_program`. The contract forbids fixed numeric thresholds, and none is introduced here. |
| strategic_capability | absent | TED-AI and ASI are thresholds on the research-taste scale ("at least as good as top human experts at virtually all cognitive tasks"), defined inside the model; nothing tests independent strategic action. |
| cyber_capability | absent | |
| objective_selection | absent | no objective for any actor. Research is not "directed" by anyone; effort is a production function of inputs. |
| authorization, operational_autonomy | absent | the automation fraction is the share of coding tasks AI performs, not how often humans approve its work. |
| effective_control, intervention_latency | absent (assumed) | resources keep flowing per forecast whatever the capability; no intervention exists. |
| custody_weights, custody_compute, custody_credentials | absent | compute is an input series with no owner; the contract ledger (`lab`) is assigned by us. |
| external_resources, dependencies | absent | the AI holds nothing. |
| communication_topology, information_beliefs, enforceable_commitments | absent | one aggregate project. |

Scenario tools around the ODE, not run in this milestone:

- `sos_mode`: freezes labor and compute at a milestone (default AC) and zeroes training
  growth (software-only singularity). A modelling counterfactual, not a decision.
- `pause_transform.py`: the website's freeze-and-reduce pause. An exogenous human policy
  on resources (closest to `T-RESTRICT` acting on compute), with no actor choosing it.
- `plan_a_covert_proj/`: a separate simulation of an international slowdown deal with a
  legal consortium, a covert project, theft of software progress and detection. It has
  more actors than the core model and would need its own mapping; it is out of scope here.

## Per-mode coverage

| mode | coverage | why |
|---|---|---|
| MODE-HUMAN-LAB | supported | the implicit setting: human-forecast resources, AI raising research productivity. Control is assumed by omission, so the model can never show this view failing. |
| MODE-SOVEREIGN-CAPABLE | unsupported (was `partial` in the README-based draft) | no counterpart to `strategic_capability`, the view's defining dimension. |
| MODE-SOVEREIGN | unsupported | no AI objective, custody or resources. |

Human-led research feedback without sovereignty is exactly what AIFM models: its full
feedback loop runs inside MODE-HUMAN-LAB. Autonomous successor development and strategic
sovereignty need separate evidence and are not implied by any AIFM output.

## Inputs and the accounting ledger

AIFM's inputs are `human_labor`, `compute_inference` and `compute_training`. It converts
inference compute to AI coding labor itself, so `agent_labor` must not also be given to it
(the contract rejects that as double counting). The README-based draft listed
`agent_labor`; the code shows `inference_H100e` is the input.

Gap for #5/#11: AIFM's **experiment compute** (`experiment_H100e`, 10x inference compute
in the default series) has no accounting quantity in the contract. It is neither training
nor inference. Mapping it to `compute_training` would double count with the training
series. We leave it unmapped and flag it rather than extend the contract in this PR.

## Evidence records

AIFM outputs are `source_model_output` records, never observations. Its present-day
horizon level is fitted to METR measurements and its revenue and ECI levels to Epoch
data, so any AIFM output is non-independent of METR (#12) and Epoch records through
`fitted_to`. The records are `EV-AIFM-*` in `evidence/records.yaml` (#8 contract).
