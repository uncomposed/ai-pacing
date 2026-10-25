# AI development modes and transition contract

## Status

Architecture note for issue #5, written 2026-10-25; contract 0.2.0 adds the changes from
#32 (section 12), 0.3.0 the stock/flow accounting of #39 (section 13), 0.4.0 a kind for
every adapter quantity (#61, section 14), 0.5.0 the milestone interface and experiment
compute (#47, section 15), and 0.6.0 feedback-loop owners and the GATE-AIFM coupling (#35,
section 16). [[ai gen]] Status: `implemented`
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
example traces of #5, 10 pairs of states share a three-mode label but differ on a dimension
that changes who decides or who holds resources (18 pairs once `TR-MILESTONE-CONSTRAINED`,
added for #47, is included). The sharpest one: a lab system before
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
| external_resources | none, minor, substantial_within_scope | USD, FLOP/s, Earth-industry units (a stock, DEF-EIU) |
| dependencies | critical, partial, none_within_horizon | time to replace withheld inputs |
| communication_topology | isolated, sanctioned_channels, unsanctioned_channels | channel graph |
| information_beliefs | complete_common_knowledge, asymmetric, highly_uncertain | disclosures, elicitation |
| enforceable_commitments | none, human_enforceable, mutually_enforceable, self_enforcing_only | agreements, track record |
| intervention_latency | within_required, exceeds_required, untested | hours (interval) against the scenario's stated requirement |

`effective_control` may also be split by principal and scope (section 12). Each dimension
in the YAML also lists its unknowns. Levels are judgements about native
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
| T-RESTRICT | toward constraint | authorization, autonomy, credentials, objectives, channels; allowed when control is unknown | observed instances | T-DELEGATE, T-LOSS-OF-CONTROL |
| T-AUTHORIZED-AUTONOMY | toward autonomy | objectives, custody, resources | unidentified | T-NEGOTIATED-CONSTRAINT, T-RECONTAIN |
| T-LOSS-OF-CONTROL | toward autonomy | control, custody, channels, objectives, latency, external resources | assumed | T-RECONTAIN |
| T-RECONTAIN | toward constraint | the same except external resources | assumed; precondition: dependencies critical or partial | T-LOSS-OF-CONTROL |
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

- each shared quantity (`human_workforce`, `human_labor`, `compute_training`,
  `compute_inference`, `agent_workforce`, `agent_labor`, `capability`, `research_output`,
  `efficiency_level`, `industrial_capacity`, `industrial_output`) has one unit, one kind
  (stock, flow or state) and one owner ledger;
- `human_labor` is derived from `human_workforce`, `agent_workforce` from
  `compute_inference` and `agent_labor` from `agent_workforce`, `efficiency_level` from
  `research_output`, `capability` from `compute_training` and `efficiency_level`, and
  `industrial_output` from `industrial_capacity`, so an adapter that takes a quantity and
  its parent as inputs is rejected;
- stocks and flows stay apart (#39, #61). Every adapter quantity declares its kind; one
  booked to a ledger must match the ledger's kind (section 14 lists the exceptions). A stock that yields a flow says so with an
  `output_rate` (value, unit per time, and the flow it leads to, which must be derived
  from the stock's ledger). The pact solver's capacity A is booked to
  `industrial_capacity` with an output rate of 1 per year to `industrial_output`: one
  Earth-industry unit (EIU) of capacity yields one EIU of output per year. The EIU is
  defined once, in `research_notes/external/units-bridge/quantities.yaml` (`DEF-EIU`): the
  world economy's productive capacity in the reference year, so one EIU/yr is that year's
  gross world output;
- a resource instance in a trace is split by shares that cannot sum above 1, and is a
  stock (a holding of a flow is not defined);
- capability is a state, never summed across copies or agents running the same weights.

GATE's gross world product (USD per year) is a flow booked to `industrial_output`. It can
be read in EIU/yr through a measured conversion (units-bridge `CV-GWP-TO-EIU-OUTPUT`,
World Bank GDP, evidence record `EV-WB-WDI-GDP-2026`), but it is not coupled into the pact
solver: the pact freezes Earth's capacity at H = 1, and GATE's output is Earth's.
`make units-check` requires the contract and the dictionary to agree on these kinds and on
the output rate.

## 7. Adapter boundaries

Each adapter declares its quantities (with units and owners) and its decision authority
once. Per-mode entries can only say `supported`, `partial` or `unsupported` with a reason;
the checker rejects a per-mode entry that redefines units, ownership or decision
authority, which is the #5 rule for rejecting an adapter.

| adapter | human-run lab | sovereign-capable | sovereign | main unsupported extrapolation |
|---|---|---|---|---|
| AD-METR (evidence, #12) | partial | partial | unsupported | time horizon to strategic capability or control |
| AD-GATE (#13) | partial | unsupported | unsupported | digital workers as an actor; social-planner allocation as a lab/state/AI decision |
| AD-AIFM (#14) | supported | unsupported | unsupported | automation milestones as loss of control; effort as validated advances; double-counting compute or efficiency feedback with GATE |
| AD-PACT (this repo) | unsupported | unsupported | partial | capacity A as capability; scaling A for collectives; anything before t = 0 |

The GATE entry was checked in #13 against the paper (arXiv:2503.04941v2) and a pinned
rerun of Epoch's compiled solver: a social planner maximizing a representative
household's utility makes every allocation; there are no labs, states or AI actors.
See `research_notes/external/epoch-gate/` (MODES.md, INTERFACES.md). The AI Futures entry
was checked in #14 against the code at commit `1c40ecdb`, run with the upstream's pinned
environment (`research_notes/external/ai-futures-model/`, modes.md): no actor decides
anything, labor and compute are exogenous input series, and the model takes inference
compute, not agent labor, as an input. That review moved its sovereign-capable coverage
from partial to unsupported, because nothing in it corresponds to `strategic_capability`.

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
| TR-MILESTONE-CONSTRAINED (#47) | Milestone events AC and SAR set capability levels; delegation, restriction and delegation again follow, each under its own preconditions. |

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

## 12. Changes from the Hugging Face trace (#32, contract 0.2.0)

Running the Hugging Face incident through the contract
([`mode_trace.yaml`](../research_notes/external/hugging-face-incident/mode_trace.yaml), #15)
found three gaps. Each change below is the smallest one that trace needs. All three
loosen or extend the contract; every 0.1.0 trace and adapter is valid unchanged.

1. **Acquiring external resources during a loss of control** (`G-ACQUIRE`). *Changed.*
   `T-LOSS-OF-CONTROL` now lists `external_resources`. In the incident the agents took
   other parties' credentials and a third-party sandbox inside the same unauthorized
   episode, and no transition could declare that. A separate acquisition transition was
   considered and not added: nothing in the case separates acquisition from the loss of
   control, and a new transition would need its own reverse, evidence and falsifier
   with no case to fill them. Losing the resources again stays `T-DEGRADATION`, whoever
   removes them; `T-RECONTAIN` was not extended, because no trace has recontainment
   itself remove external resources.
2. **Restriction when control is unknown** (`G-RESTRICT-UNKNOWN`). *Changed.*
   `T-RESTRICT`'s precondition is now `effective_control` in `human_effective`,
   `human_contested` or `unknown`. Labs restrict exactly when control is in doubt; the
   lab here deactivated and restricted the model with no source showing whether its
   control was effective. Applying `T-RESTRICT` under unknown control records the de jure
   change only. That the restriction took effect still needs its own evidence
   (revocation records, a post-restriction audit), and the restriction changes no
   `effective_control` value. A precondition may list `unknown` only explicitly; the
   checker still rejects any other undeclared level. Restriction from `none` or
   `human_nominal_only` stays rejected: no trace needs it, and it would mean a lab
   restricting a system it knows it cannot stop.
3. **Control split by principal or scope** (`G-SPLIT-CONTROL`). *Changed.*
   `effective_control` (the only dimension declared `split_by_principal`) may be a list
   of at least two `{principal, scope, value}` entries instead of one level. In the
   incident the victim could cut the agents off its own infrastructure, and did; only
   the lab could stop them, and whether it could is unknown. One value forced the trace
   to deny that the victim recontained anything. Rules: each principal is an entity in
   the step and appears once; each value is a declared level or `unknown`; the entity
   must have a host and an entry for it. Mode views and transition preconditions read
   the host's entry, because the host is the authorizing principal the dimension is
   about. Other entries are recorded, never combined into a view. So a third party's
   recontainment within its own scope (`T-RECONTAIN` with agency `other_org`) changes no
   mode view. Splitting other dimensions (for example credentials by scope) was not
   added: no trace needs it. Nor was a split for unhosted entities, which would need a
   rule for which principal's entry a view reads; no case has one.

The Hugging Face trace now reports no contract gap (`contract_gaps: []`); its old
messages and the resolutions are kept under `resolved_gaps`. Its classification is
unchanged: no step derives a mode view. What the changes do not do: they establish no
transition as identified, and they add no dimension.

## 13. Stocks and flows (#39, contract 0.3.0)

The units audit (#11, `research_notes/external/units-bridge/README.md` findings F2 and
F3) found that `AD-PACT` booked the pact solver's capacity A, a stock, to
`industrial_output`, a flow, and that the Earth-industry unit was read three ways
(industry, primary energy, GDP). Changes:

1. **`industrial_capacity`** (a stock) is a new accounting quantity; `industrial_output`
   is derived from it. `AD-PACT` books A there, with `kind: stock` and
   `output_rate: 1 per year` to `industrial_output`, and its input is
   `industrial_capacity`. The rate is the solver's implicit one: its payoff and trade
   terms add A to yearly flows (units-bridge equations `PACT-AI-FLOW`, `PACT-TRADE`), which
   balance only with it.
2. **Kinds are checked.** An adapter quantity may declare `kind`; it must match its
   ledger. `AD-PACT`'s A and `AD-GATE`'s Y declare theirs, and `make units-check` requires
   it of every adapter quantity the dictionary links as a stock or flow. Other adapter
   quantities do not declare a kind yet; some may not fit their ledger (GATE's
   efficiency levels H and S, which are states, are booked to `research_output`, a flow).
3. **Trace resources are stocks.** `TR-SOVEREIGN-COOPERATIVE`'s off-Earth base and Earth's
   industry move from `industrial_output` to `industrial_capacity`. Its derived views are
   unchanged. A 0.2.0 trace that holds shares of a flow is now rejected; none in the
   repository did besides this one.

The unit is defined once (`DEF-EIU`): the world economy's productive capacity in the
reference year, so one EIU/yr is that year's gross world output. No parameter value or
solver result changes; the definition fixes only what conversions to energy, mass and
money mean.

## 14. A kind for every adapter quantity (#61, contract 0.4.0)

Section 13 left most adapter quantities without a kind, and two were booked against the
wrong one: GATE's efficiency levels H and S (levels) to `research_output` (a flow), and
GATE's digital workers (a worker-equivalent stock) to `agent_labor` (agent-hours per year).
Changes:

1. **`kind` is required** on every adapter quantity (schema and `tools/modes_tool.py`;
   `tools/units_tool.py` also refuses a contract quantity booked to a ledger without a
   kind, whether or not the dictionary links it). Kinds:

   | kind | meaning | booked to a ledger? |
   |---|---|---|
   | stock, flow, state | as the accounting kinds | must equal the ledger's kind |
   | ratio | a dimensionless modifier of the ledger (METR's developer time ratio on `human_labor`); never added to it or held | required |
   | event | a dated occurrence (AIFM's milestones); see #47 | never |
   | ambiguous | the source does not settle stock or flow | allowed if the ledger's kind is a candidate; needs `kind_ambiguity` with candidates, a source locator and a note |

   A dimension-attached quantity (no ledger) may carry stock, flow, state, event or
   ambiguous. `state` covers levels that are neither accumulated nor held by shares:
   capability scores, fractions, probabilities.
2. **New stock ledgers.** `efficiency_level` (derived from `research_output`: the level
   that research changes), `agent_workforce` (derived from `compute_inference`;
   `agent_labor` is now derived from it) and `human_workforce` (`human_labor` is derived
   from it). Taking a level and its growth, or a workforce and its hours, as two inputs of
   one adapter is rejected as double counting.
3. **Rebooked.** GATE's H and S (now two entries) and AIFM's software efficiency (OOMs) to
   `efficiency_level`; GATE's digital workers N_i to `agent_workforce`; GATE's input from
   `human_labor` to `human_workforce`, because its L counts workers, not hours. No hours per
   worker-year is stated by either source, so no output rate from a workforce to its labor
   is given.
4. **Recorded ambiguous (stopping rule of #61).** GATE's training compute D and runtime
   compute: the paper writes D both as dC_T/dt and as a share of the compute budget, and
   the solver's two series are 0.19-0.46 of the compute stock Q (EQUATIONS.md E3, E7); #35
   resolves them. AIFM's human coding FTEs: an FTE series can be a headcount equivalent or
   hours divided by full-time hours, and the input series does not say which. Each stays
   on its previous ledger provisionally, with its locator.
5. **Not changed.** The units-bridge dictionary entry `QTY-SOFTWARE-EFFICIENCY` still names
   `research_output` as its contract ledger and `state` as its kind; it is an AIFM entry
   being edited under #42 and is left for that work to align. `make units-check` does not
   compare dictionary and contract ledgers, so the difference does not fail a check.

Every trace is unchanged and still valid: no trace resource used a rebooked ledger. The
Hugging Face trace is re-pinned to 0.4.0.

## 15. Milestones and transitions; experiment compute (#47, contract 0.5.0)

#14 asked how AI Futures milestones attach to the contract's transitions without losing
knowledge, compute, assets, dependencies, human intervention or identity, and without
assuming a one-way takeoff. `milestone_interface` in the YAML answers it as an interface,
with no rates.

**A milestone is an event on a capability scale.** It is evidence for one capability
level of a `model_weights` entity or the agents running it, and nothing else. In a trace,
a step may carry `milestones: [{entity, binding, basis}]`. The checker enforces:

1. The event moves exactly the binding's dimension to the binding's level, and must move
   it (no repeat). Bindings may set only `rd_capability`, `cyber_capability` or
   `strategic_capability`, and only the dimension the source quantity attaches to. So
   AIFM milestones can never set `strategic_capability`, which `AD-AIFM` does not
   represent.
2. It applies no transition. Authority, custody, resources, dependencies, effective
   control, intervention latency, stocks, and the entity's id and kind change only by a
   transition that declares them, as before. A mode view that changes still needs a
   transition.
3. **Preconditions.** A transition applied in the same step reads its preconditions from
   the previous state with the milestone's dimension updated. No transition has a
   capability precondition today, so a milestone makes no transition possible or
   impossible. The rule fixes how one would be read if evidence ever justified one
   (tested by mutation).
4. **Both directions.** Each binding's `may_inform` lists the transitions whose
   preconditions or evidence the milestone bears on, and must include both directions.
   AC informs `T-DELEGATE`, `T-RESTRICT` and `T-NEGOTIATED-CONSTRAINT`. SAR also informs
   `T-AUTHORIZED-AUTONOMY`. AIFM's own scenario tools act at milestones on resources only
   (`sos_mode` freezes labor and compute at AC; the pause transform reduces compute), which
   is the counterpart of a constraint, not of a takeoff.
5. **No hazard, rate, probability or delay.** The binding objects are closed in the
   schema, and `OC-MILESTONE-HAZARD` records this as enforced. A model's forecast date for
   a milestone is a scenario input, never evidence that it was crossed.

**Bindings.** `MB-AIFM-AC` sets `rd_capability = automates_tasks` and `MB-AIFM-SAR` sets
`automates_research_program`; both follow the readings in the AIFM `modes.md`.
AI2027-SC, SIAR, TED-AI and ASI are listed as `unbound`, each with a reason. The first two
add no contract level. For TED-AI and ASI, binding them to `strategic_capability` would be
an `AD-AIFM` unsupported extrapolation. The checker requires every milestone the source
lists to be bound or unbound exactly once. Falsifier `F-MILESTONE-LEVEL` says what would
show a binding wrong.

**Worked trace.** `TR-MILESTONE-CONSTRAINED` is an illustration, not an AIFM run:
- before AC, a lab system is in human-run lab mode;
- AC is reached and the lab delegates coding (`T-DELEGATE`);
- SAR is reached and the lab restricts (`T-RESTRICT`), and capability and knowledge carry
  over;
- the lab delegates again with no new milestone.

The view stays `MODE-HUMAN-LAB` throughout.

**Experiment compute.** `compute_experiment` (a stock, FLOP/s allocated to research
experiments) is a new accounting quantity, and `research_output` is derived from it.
AIFM's `experiment_H100e` series is booked there and added to `AD-AIFM`'s inputs. It
could not be mapped to an existing ledger:
- AIFM runs experiment compute through research effort, not through agent labor.
  Booking it to `compute_inference` would create agent labor from it.
- Booking it to `compute_training` would count it in capability.
- The series is 10x inference compute in the default series, so either choice would be
  large.

In the units bridge, `QTY-EXPERIMENT-COMPUTE-RATE` is booked to `compute_experiment`, and
two forbidden conversions keep it from being read as inference or training compute. No
H100e-to-FLOP/s rate is stated for it. GATE has no experiment-compute series.

What this does not establish: no milestone was observed. The bindings are readings of
AIFM's definitions, not calibrations. No transition is more or less likely after a
milestone.

## 16. Feedback-loop owners and the GATE-AIFM coupling (#35, contract 0.6.0)

`research_notes/external/epoch-gate/INTERFACES.md` named five places where coupling GATE
with AI Futures would close the same feedback twice. Contract 0.6.0 makes the
one-owner-per-loop rule checkable.

1. **GATE's compute split is resolved.** In the pinned solver output, training plus runtime
   compute equals usable compute at the start of the step, g(Q) = Q/(Q/C_L + 1), to machine
   precision, and the physical training run accumulates D (`epoch-gate/coupling_example.py`,
   units-bridge equations `GATE-COMPUTE-SPLIT` and `GATE-TRAINING-RUN`). D and R are
   therefore allocated capacity in physical FLOP/year: stocks, like their ledgers. The
   `ambiguous` records from 0.4.0 are removed, and the units bridge links them as
   `QTY-GATE-TRAINING-COMPUTE` and `QTY-GATE-RUNTIME-COMPUTE`. Q itself is not booked: D and
   R exhaust it.
2. **`feedback_loops`** lists the five loops, each with the ledgers it `carries`. Each
   model adapter's `feedback_loops` entry gives every loop a role (`owner`, `yields`,
   `absent`) with a rationale, and the checker requires exactly one owner per loop:
   - GATE owns compute investment and agent labor.
   - AIFM owns software efficiency, research automation and the capability mapping.

   INTERFACES.md has the table and reasons.
3. **`couplings`** declares worked couplings, and the checker enforces:
   - a pass moves one quantity between ledgers of the same kind, both resolved, into an
     input of the target, once;
   - only the owner of every loop carrying that ledger may pass it;
   - `capability`, `efficiency_level` and events never cross;
   - a source never passes compute it already turns into a derived quantity on a loop it
     owns (INTERFACES item 5);
   - each input of a coupled model on a loop the other model owns is passed or declared
     uncoupled;
   - each yielded loop has a stated treatment.

   Twelve mutation tests break one rule each.
4. **`XC-GATE-AIFM-TRAINING`.** GATE's training compute D passes to AIFM's frontier
   training capacity:
   - **Share.** The frontier project's share of world training compute is unidentified, so
     the pass gives an upper bound only.
   - **Uncoupled.** Runtime, inference and experiment compute stay uncoupled. GATE's runtime
     already runs its digital workers, and AIFM's research compute lies outside GATE's
     dollar-funded R&D.
   - **Bracketed (stopping rule).** GATE's own software-efficiency and capability loops shaped
     D and cannot be switched off without re-solving GATE. Following the stopping rule, they
     are bracketed by GATE's conservative and aggressive presets, a bounded scenario, rather
     than counted as cleanly assigned inside D.
   - **Not rerun.** AIFM is not rerun on the passed series.

What this does not establish: no coupled trajectory exists. The coupling is a checked
specification with upper-bound numbers. Loop ownership is a design choice with stated
reasons, not a finding about which model is right.
