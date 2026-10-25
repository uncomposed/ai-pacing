# AI development modes and transition contract

## Status

Architecture note for issue #5, written 2026-10-25. [[ai gen]] Status: `implemented`
(contract, checker and tests); nothing is `verified` against evidence and nothing is
`human_validated`. Every definition, level and transition is **proposed**: an
analytical device to review, not an empirical claim or a settled threshold.

Machine-readable form: [`systems/modes.yaml`](../systems/modes.yaml), shape fixed by
[`schema/modes.schema.json`](../schema/modes.schema.json), rules checked by
[`tools/modes_tool.py`](../tools/modes_tool.py). `make check` runs the checker and its
mutation tests (`test/modes_tool_test.py`). `make modes-report` prints the derived
views for every example trace and the three-label comparison below.

The YAML is authoritative where it and this note differ. Like `systems/model.json`, the
contract is a workspace separate from the canonical AI Pacing specification; it changes
no proposition in `spec/ai-pacing.yaml`, and it does not rewrite #1 or #3.

## 1. Why a contract

The pact solver starts with one strategic AI that already sets its own objectives and
owns an off-Earth base. Development models (AI Futures, GATE) assume humans allocate
research and compute. METR measures task performance of systems evaluated by humans.
Connecting their outputs without saying who decides, who holds which resources and who
can intervene would silently change actors and causal assumptions. The contract names
those things once, so each adapter can say what it represents and what it does not.

## 2. Representation: factored state, modes as derived views

The decision rule in #5 asks to compare a minimal three-mode state with a factored state
whose modes are derived views, and to keep the smaller one that preserves consequential
distinctions.

**Choice: factored state.** Each entity carries a value (or `unknown`) on sixteen
dimensions. The three modes are predicates over that state, evaluated three-valued:
holds, fails, or undetermined when a needed dimension is `unknown`. An entity can match
two views at once, or none.

**Evidence for the choice** (`python3 tools/modes_tool.py compare`): across the five
example traces, 10 pairs of states share a three-mode label but differ on a dimension
that changes who decides or who holds resources. The sharpest one: a lab system before
and after a failed intervention (`TR-NOMINAL-CONTROL`, steps 1 and 2) has the same
label, while `effective_control`, `custody_credentials`, `objective_selection` and
`intervention_latency` all differ. A three-label state would keep calling it a human-run
lab. Caveat: the traces were written by the same author as the contract, so this shows
the labels *can* erase distinctions, not how often they do. Falsifier `F-LABEL-SUFFICES`
says what would reverse the choice.

## 3. Entities, dimensions, observables

Entity kinds: `agent_instance`, `model_weights`, `agent_collective`, `lab`, `state`,
`other_org`. Shared weights, a collective of agents, the lab hosting them and a state are
different entities, each with its own entry. Copies of one set of weights share one
capability; they are never added up.

| dimension | levels (plus `unknown`) | native units / observables |
|---|---|---|
| strategic_capability | limited, assisted_only, independent_plausible, independent_demonstrated | source-native (METR time horizons are capability on a task suite, not strategic action) |
| rd_capability | none, assists_humans, automates_tasks, automates_research_program | METR hours, RE-Bench, AIFM milestones |
| cyber_capability | low, moderate, high | evaluation scores, incidents |
| objective_selection | human_institution, shared, system_self | task records, behaviour under conflict |
| authorization (de jure) | none, supervised_tasks, delegated_autonomy, broad_autonomy | policies, permissions |
| effective_control (de facto) | human_effective, human_contested, human_nominal_only, none | drills, incident outcomes, access audits |
| custody_weights / _compute / _credentials | human_institution, shared, system_self, third_party | access logs, scheduler records, key rotation |
| operational_autonomy | step_approved, task_level, long_horizon_unsupervised | hours between approvals |
| external_resources | none, minor, substantial_within_scope | USD, FLOP/s, Earth-industry units |
| dependencies | critical, partial, none_within_horizon | time to replace withheld inputs |
| communication_topology | isolated, sanctioned_channels, unsanctioned_channels | channel graph |
| information_beliefs | complete_common_knowledge, asymmetric, highly_uncertain | disclosures, elicitation |
| enforceable_commitments | none, human_enforceable, mutually_enforceable, self_enforcing_only | agreements, track record |
| intervention_latency | within_required, exceeds_required, untested | hours (interval) against the scenario's stated requirement |

Each dimension in the YAML also lists its unknowns. Levels are judgements about native
quantities with a stated basis. The contract never converts a quantity into a level by a
fixed number, and the checker refuses any mode criterion that is not a declared level, so
no numeric sovereignty threshold can be added to complete the schema.

## 4. The three modes (proposed)

They are analytical modes, not a ladder: no order is implied, and none is a stage every
system passes through.

1. **Human-run lab** (`MODE-HUMAN-LAB`): hosted by a lab; objectives set by humans (or
   shared); `effective_control = human_effective`; weights in the lab's custody;
   intervention `within_required`. Capability is unconstrained: AI assistance and heavy
   automation are compatible with this mode.
2. **Sovereign-capable system within a lab** (`MODE-SOVEREIGN-CAPABLE`): hosted by a lab
   and `strategic_capability` at `independent_plausible` or above. It says nothing about
   control; it overlaps with the human-run view when control is effective
   (`TR-CONTROLLED-CAPABLE`). Capability alone does not establish sovereignty.
3. **Sovereign AI** (`MODE-SOVEREIGN`): no host; `objective_selection = system_self`;
   no effective human control; `external_resources = substantial_within_scope`, judged
   against a scope and horizon the trace must state. Legal recognition, alignment,
   off-Earth location and complete material independence are separate attributes, listed
   under `not_implied`.

**Uncertain and uncovered cases.** A lab system whose intervention capability is
untested matches no view (`TR-NOMINAL-CONTROL` step 1); so does one whose control has
failed but which still lacks independent resources (step 2). These are not errors: the
factored state records why, and the report lists them. A needed dimension that is
`unknown` makes a view undetermined rather than false, and traces must say so.

## 5. Transitions in both directions

| transition | direction | changes | feasibility | reversed by |
|---|---|---|---|---|
| T-DELEGATE | toward autonomy | authorization, operational autonomy | observed instances | T-RESTRICT |
| T-RESTRICT | toward constraint | authorization, autonomy, credentials, objectives, channels | observed instances | T-DELEGATE, T-LOSS-OF-CONTROL |
| T-AUTHORIZED-AUTONOMY | toward autonomy | objectives, custody, resources | unidentified | T-NEGOTIATED-CONSTRAINT, T-RECONTAIN |
| T-LOSS-OF-CONTROL | toward autonomy | control, custody, channels, objectives, latency | assumed | T-RECONTAIN |
| T-RECONTAIN | toward constraint | the same | assumed; precondition: dependencies critical or partial | T-LOSS-OF-CONTROL |
| T-NEGOTIATED-CONSTRAINT | toward constraint | commitments | unidentified | T-COMMITMENT-LAPSE |
| T-COMMITMENT-LAPSE | toward autonomy | commitments | assumed (pact exit move) | T-NEGOTIATED-CONSTRAINT |
| T-DEGRADATION | toward constraint | resources, dependencies | assumed (failed strike, crackdown) | T-RECOVERY |
| T-RECOVERY | toward autonomy | resources, dependencies | assumed (growth to closure) | T-DEGRADATION |

Each transition in the YAML records agency, preconditions, delay (all `unknown`: no rate
is asserted), cost, hysteresis, persistence and the evidence of effective control it
needs. Naming a reverse does not claim the reverse is feasible: `T-RECONTAIN` is assumed
feasible only while dependencies remain. **Only delegation and restriction are
identified** (observed and routine). All other transitions remain unidentified.

The checker enforces, for every trace step:

- a changed dimension must be declared by a transition applied in that step;
- an applied transition must change at least one of its dimensions (no relabelling);
- preconditions must hold in the previous step;
- stocks (knowledge, copies, assets, liabilities, commitments) carry over unless the step
  declares a change with a cause. A mode label change never resets them.

## 6. Mixed populations and accounting

Actors coexist in different modes in one step (`TR-MIXED-POPULATION`: a human-run lab
system, a sovereign-capable system in a second lab, and a sovereign collective renting
part of a provider's cluster). To prevent double counting:

- each shared quantity (`human_labor`, `compute_training`, `compute_inference`,
  `agent_labor`, `capability`, `research_output`, `industrial_output`) has one unit and
  one owner ledger;
- `agent_labor` is derived from `compute_inference`, and `capability` from
  `compute_training`, so an adapter that takes a quantity and its parent as inputs is
  rejected;
- a resource instance in a trace is split by shares that cannot sum above 1;
- capability is a state, never summed across copies or agents running the same weights.

## 7. Adapter boundaries

Each adapter declares its quantities (with units and owners) and its decision authority
once. Per-mode entries can only say `supported`, `partial` or `unsupported` with a reason;
the checker rejects a per-mode entry that redefines units, ownership or decision
authority, which is the #5 rule for rejecting an adapter.

| adapter | human-run lab | sovereign-capable | sovereign | main unsupported extrapolation |
|---|---|---|---|---|
| AD-METR (evidence, #12) | partial | partial | unsupported | time horizon to strategic capability or control |
| AD-GATE (#13) | partial | unsupported | unsupported | automated labor as an actor; optimizer allocation as a lab/state/AI decision |
| AD-AIFM (#14) | supported | partial | unsupported | automation milestones as loss of control; double-counting compute feedback with GATE |
| AD-PACT (this repo) | unsupported | unsupported | partial | capacity A as capability; scaling A for collectives; anything before t = 0 |

The GATE entry rests on the paper's abstract (arXiv:2503.04941) and the AI Futures
entry on the repository README, both read 2026-10-25; neither model was run and no
version is pinned. Claims about who allocates resources in them are marked "to verify"
in the YAML and are for #13 and #14 to settle.

## 8. The pact solver on the contract

`solver_mapping` maps every one of the 49 entries in the solver's assumption register
(`model/assumptions.yaml`) to a dimension, a transition, the outcome/rival block, or a
stated exclusion, and cites only PARAMS names that exist; the checker fails when the
register gains an unmapped entry. In contract terms the solver represents:

- one `agent_instance` with `objective_selection = system_self` (AS-POWERSEEK,
  AS-COHERENT-EU), no host, and `dependencies = critical` until `A_close`
  (AS-ACLOSE, AS-KILLPRE), then `none_within_horizon`;
- human control as the denial reserve and pre-closure shutdown (`effective_control`:
  q, d, kill_pre), with no human first strike (AS-NOFIRSTSTRIKE) and so no intervention
  latency on a cooperator;
- `communication_topology` fixed at one AI (AS-SINGLE-AI, AS-NOALLY);
- transitions `T-DEGRADATION` (failed strike, crackdown), `T-RECOVERY` (growth to
  closure), `T-COMMITMENT-LAPSE` (exit), `T-RESTRICT` (deprecation and crackdown on
  discovery) and `T-RECONTAIN` (firing the reserve);
- **not** `T-DELEGATE`, `T-AUTHORIZED-AUTONOMY`, `T-LOSS-OF-CONTROL` or
  `T-NEGOTIATED-CONSTRAINT`. The development phase that would lead to its t = 0 state is
  outside it.

So the solver is, at best, a partial model of `MODE-SOVEREIGN` with a dependency phase.
Its results do not transfer to systems inside labs. Rival AIs born to states are new
entities, not a mode change of the main AI. Equilibrium selection, horizon and sampling
priors are excluded here and belong to #9, #10 and #8.

## 9. Example traces

All five cases #5 asks for are in the YAML and checked on every `make check`:

| trace | shows |
|---|---|
| TR-CONTROLLED-CAPABLE | High capability under effective control: both lab views hold; delegation changes authorization, not control. |
| TR-NOMINAL-CONTROL | Authorization unchanged while intervention fails; no view holds; recontainment restores the human-run view, and the incident record carries over. |
| TR-SOVEREIGN-COOPERATIVE | The pact after closure: sovereign and cooperating; exit changes commitments, not the mode. |
| TR-RESTRICTED-REGAINS | Delegation, restriction, then regained autonomy through credentials kept through the restriction; still not sovereign. |
| TR-MIXED-POPULATION | Three systems in three different views in one step, with a shared cluster split by shares. |

The traces are illustrations, not reconstructions of real events. #15 is where the
Hugging Face incident is reconstructed; this contract supplies the vocabulary only.

## 10. Falsifiers, omissions and evidence requirements

`falsifiers` in the YAML name observations that would show a mode definition or the
representation wrong (for example, a lab meeting every `MODE-HUMAN-LAB` criterion that
still could not stop its system in time). Every mode must have one. `evidence_requirements`
states, for every mode and transition, what evidence would support it. `omission_checks`
lists what the contract leaves out on purpose (legal status, alignment) or has not yet
handled (persistence across resets as a dimension, human-internal actors, transition rates).

## 11. What this does not establish

- No mode boundary, level or transition is validated against evidence.
- No transition rate, delay or probability is given.
- Adapter coverage is a statement about what each source represents, pending the
  source-specific replications (#12, #13, #14).
- The three-label comparison uses author-written traces.

Later issues use the contract as follows: #9 (actor structures and collectives through
entities and topology, not capacity multipliers), #10 (outcomes stated against entities
and horizons), #11 (the accounting quantities), #12 to #14 (adapters), #15
(classification of the incident through the views and `T-LOSS-OF-CONTROL`/`T-RECONTAIN`).
