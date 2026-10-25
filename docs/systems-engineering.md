# AI governance: challenges, requirements, and candidate solutions

Status: draft for stakeholder validation, 2026-09-15.

**Actor-model revision:** [Actor and use-case analysis](actor-analysis.md) supersedes
the initial eight-role summary below. Model 0.2.0 now distinguishes actor profiles,
routine use cases, and conflicting interactions before reassessing requirements.
The original candidate requirements remain unvalidated.

The editable model is [`systems/model.json`](../systems/model.json). It models the
problem to be addressed, then attaches proposed mechanisms. Existing AI Pacing
claims retain their historical meaning in `spec/ai-pacing.yaml`; they are not
requirements on every possible solution. This workspace can compare AI Pacing
with alternatives without silently rewriting its identity.

## 1. Corrected understanding of the assignment

The earlier review substituted nearby concerns for several intended mechanisms.
These corrections are part of the model's input, not empirical findings:

1. **Safe reporting:** safety concerns must become actionable while weights and
   other dangerous artifacts remain protected. Protection against retaliation
   and protection against dangerous disclosure are distinct obligations.
2. **Third-party evaluators:** this is a proposed way to make development
   assessable by experts, not the underlying need itself. The ambiguous word
   “interperatible” is provisionally interpreted as expert intelligibility and
   assessability. Cross-organization interoperability is not silently substituted.
3. **Expertise, custody, competition:** the evaluator needs relevant expertise;
   dangerous actors must not acquire weights; the lab seeks to become a safe
   frontier competitor. These are three separate conditions. Third-party status
   alone proves none of them. Rival expertise could help while creating leakage,
   collusion, or exclusion risks.
4. **International incentives:** a public-frontier rule is a proposed incentive
   mechanism affecting competitors' choices to coordinate. Reacting to a foreign
   release is only one branch of that mechanism, not its purpose.
5. **Effective control:** control must actually be exercised and take effect
   before it is lost. Detection, a warning, a decision, or a command alone does
   not establish that this happened.
6. **Initial action:** an actor can act while others are still deciding. Their
   state is unresolved, not necessarily refusal or noncooperation. Execution,
   usefulness, and preservation of future choices require separate analysis.

The handwritten attachment is a source of priorities and candidate mechanisms.
Its imperatives are not treated as commands to adopt those policies. The career
note is outside this governance-model scope.

## 2. System boundary and critical perspective

The system is the sociotechnical arrangement through which AI is developed,
assessed, given external authority, operated, constrained, and retired. It
includes people, institutions, incentives, information, technical interfaces,
and physical dependencies. No assumption of a single effective global controller
is made.

**Mission:** enable beneficial development and use while preventing unacceptable
losses of safety, agency, and effective control. This is a proposed mission, not
a demonstrated consensus. Different stakeholders can disagree on acceptable
loss, who benefits, and whose authority is legitimate.

### Initial actor summary (superseded by the detailed actor analysis)

| Actor | Relevant interest or role | Critical question |
|---|---|---|
| Affected people, including nonusers | Safety, benefits, agency, remedy | Who represents those who cannot participate? |
| Developing lab | Become a safe frontier competitor | Does governance reward safety or protect incumbents? |
| Employee | Communicate concerns safely | Is the channel usable under actual employment pressures? |
| Expert evaluator | Understand and challenge material claims | How is competence established, and who checks conflicts? |
| Accountable authority | Decide and correct consequential actions | What makes its authority legitimate and practically effective? |
| Operator | Execute and sustain controls | Does a command produce the intended physical or digital effect? |
| International competitor | Strategic security and opportunity | What are its outside options and beliefs? |
| AI as possible strategic actor | Conditional behavioral role | Do preferences and commitment capacity support bargaining analysis? |

These interests are elicitation hypotheses. No stakeholder interviews or consent
are claimed. AI behavioral agency does not establish moral status or entitlement.

Scarce resources include expert attention, protected evidence, effective legal
and operational authority, intervention time, infrastructure dependencies, and
credibility. Scarcity must enter candidate evaluations rather than being hidden
behind phrases such as “independent review.”

Boundary review must ask who defines safety, who can contest that definition,
who controls evidence, who bears intervention costs, and who benefits from delay.
The current affected-public record is deliberately broad and needs decomposition
by geography, exposure, vulnerability, and representation before baselining.

## 3. Metamodel and relationship semantics

| Record | Meaning | Required relationship |
|---|---|---|
| Source | Intent, proposal, method, analysis, or empirical evidence | Explicit locator and role |
| Actor | Stakeholder or functional participant | Referenced in a scenario |
| Resource | Capacity, asset, or enabling condition | Owner and scenario |
| Loss | Something stakeholders cannot accept losing | Stakeholder; linked hazard |
| Hazard | A system state that can lead to loss | Loss and constraining requirement |
| Scenario | Trigger, participants, resources, success, adverse path | Challenge |
| Challenge | Open problem arising in a scenario | Candidate requirement |
| Requirement | Candidate obligation and observable criterion | Challenge, accountable actor, hazard, evaluation |
| Hypothesis | Uncertain proposition a mechanism may depend on | Falsifier, evidence plan, stopping rule |
| Proposal | Replaceable candidate mechanism | Requirements it proposes to address |
| Evaluation | One proposal tested against specified requirements | Scope, baseline, method, pass rule, evidence status |
| Decision | Scoped selection, rejection, or deferral | Comparisons, evidence, owner, risks, revisit trigger |
| Control loop | Controller, process, action, feedback, resources | Requirements and hazardous contexts |
| Conflict | Obligations that may trade off | Explicit unresolved decision and owner |

A coverage link is a claim about intended relevance, not logical entailment or
proof of satisfaction. A source of author intent is not empirical evidence.
A new requirement may have a planned evaluation with no candidate allocated;
completion requires a specific candidate. Open needs do not require invented
solutions just to pass the structural gate.
A hypothesis is not a requirement. A functional controller is not proof that the
necessary legal authority exists. Evaluation obligations require an analysis;
they do not imply the analysis will produce a favorable answer.

Separate namespaces avoid confusion between `HYP-*` and legacy `H*`, or between
new hazards and old hypotheses. `legacy_refs` identify correspondence with the
historical YAML, not equivalence or endorsement. Requirement text must remain
understandable if every current proposal is removed. Architecture-specific
constraints belong in a selected design's decomposition, with their allocation
and rationale recorded, rather than retroactively narrowing the parent challenge.

The model is an open-world analysis: absent evidence means unknown. All current
requirements are candidates, all evaluations are plans, and no proposal has been
selected. Actor profiles include goals, choices, private information, dependencies, and
constraints. Use cases record actor-relative success separately from system
safety. Interactions explain candidate requirement derivations. The strict schema rejects unknown fields; a new kind or relationship
requires a reviewed schema and validator change and a model-version migration.

## 4. Challenges and the proposed mechanisms attached to them

| Challenge | Obligations to investigate | Candidate mechanisms |
|---|---|---|
| Safe reporting | Actionable delivery; protected custody; usable anti-retaliation remedy | Protected reporting and evidence handling |
| Expert assessability of development | Competence; intelligible and reproducible evidence; safe competitive entry | Third-party experts; controlled rival review; public technical evaluator |
| Exercise effective control in time | Action takes effect before prevention deadline; reliable feedback | Tripwires connected to control; retained dependencies and activation latency |
| Incentives for international coordination | Declared range of incentive-compatible choices | Public-frontier reciprocity; negotiated commitments |
| Useful action while others decide | Local executability; feasible later participation, revision, or withdrawal | Incremental domestic steps |
| Durable cooperation with capable AI | Evaluate incentives alongside changes in control capacity | Staged autonomy; bounded reversible incentives |
| Accountable power | Accessible review and effective correction | Distributed review and remedy |

Safe development and safe deployment span these challenges; neither is reduced
to one evaluation event. “Distributed power” remains an author priority requiring
stakeholder validation. It is operationalized provisionally through contestability
and effective remedy, not assumed to mean distributing weights or removing all
central authority.

The alternative candidates are analyst proposals, not endorsements. They have
not been demonstrated feasible or exhaustive. The unchanged baseline is included
in every evaluation plan. Where only one mechanism has been identified, the
alternative search remains open rather than being fabricated as a completed trade
study.

## 5. Control analysis: observe, decide, act, confirm

The model contains preliminary control loops for evidence handling, consequential
authority, and cross-jurisdiction commitments. Each records unsafe omission,
unsafe provision, wrong timing, and wrong duration. Causal scenarios include
stale process models, absent authority, unexecuted commands, and correlated failures.
This is an initial STPA-informed analysis, not a complete STPA study.

For a specified loss scenario, define all times against the same clock:

- `t0`: start of the hazardous transition under analysis;
- `t_deadline_lower`: conservative earliest time after which the required
  protective effect cannot prevent that loss;
- `L_observe`, `L_interpret`, `L_authorize`, `L_execute`, `L_confirm`: conservative
  upper bounds for the serial response path, measured from `t0`;
- `B`: scenario-specific safety allowance.

A conservative serial-path condition is:

`margin = t_deadline_lower - (t0 + L_observe + L_interpret + L_authorize + L_execute + L_confirm + B) > 0`

This is a necessary timing check for that modeled path, not a sufficient safety
proof. Concurrent processes require a justified critical-path model; correlated
delays and failed observations cannot be assumed away. Tests must establish actual
protective effect, actuator availability, adequate authority, valid state estimates,
and persistence of the effect. A positive margin cannot rescue the wrong action.

External-signal dependence is a separate hypothesis from observability or usable
latency. A system could need signal and acquire it covertly or almost instantly.
Conversely, a control mechanism might remain effective without signal dependence.
`HYP-SIGNAL` therefore does not automatically entail `HYP-MARGIN`.

## 6. International coordination and entry are distinct problems

Coordination analysis identifies each actor's choices, preferences, information,
commitments, and outside options. It compares coordination with unilateral and
joint deviations under uncertain observation. Domestic rules can alter those
payoffs before a release occurs. A foreign release is not automatically evidence
that expanding domestic access is safe.

Entry analysis represents other actors as undecided. It asks separately:

1. Can the initiating actor execute the step with its own authority and resources?
2. Does it produce sufficient value under specified possible responses?
3. Does it preserve credible later participation, revision, and exit?

Passing the first condition proves neither the second nor the third. No numerical
utility or net-benefit claim is asserted without a defensible model and sensitivity
analysis. Contingent reciprocity and unilateral entry remain replaceable proposals.

## 7. Verification, validation, and selection

**Structural verification:** schema, unique IDs, reference types, provenance
references, scenario scope, coverage, evaluation scope, and evidence-state gates.
Run `make systems-check`. The full repository gate also runs these checks.

**Requirement validation:** responsible stakeholders assess whether the obligations
and loss definitions express their actual needs. Record the validation artifact,
resolve parameter gaps, and only then baseline a requirement. Author confirmation
of intended meaning is distinct from stakeholder validation of a policy requirement.

**Candidate verification:** execute a frozen evaluation for one candidate within
a declared envelope. Record a reviewer and evidence artifact. Tests of another
candidate cannot establish this one's satisfaction. Evidence integrity and source
content still require substantive review; a nonempty artifact locator is not proof.

**Decision:** compare alternatives and baseline, resolve material conflicts,
record residual risks and a revisit trigger. Selection requires passed evidence
for the selected candidate's claimed scope and supported dependencies. Alternatives
may fail or be inconclusive; that outcome needs evidence too. A partial selection
must narrow the proposal's claimed scope explicitly.

Quantitative thresholds remain unresolved where the sources supply none. Those
requirements cannot be baselined or declared satisfied. Do not invent a numeric
threshold merely to make a sentence look testable.

### Audit and stopping rules

- Remove every current proposal: do the challenges and needs still make sense?
- Reverse every proposed causal argument: could the objective be met without it?
- Inspect actors missing from scenario coverage and losses without constraints.
- Check development, evaluation, deployment, operation, incident response, and
  retirement, including transitions and simultaneous failures.
- Test absent, deceptive, delayed, contradictory, and excessive feedback.
- Test shared ownership and infrastructure behind supposedly independent controls.
- Check whether protected evidence can leak or whether secrecy defeats assessment.
- Check whether review suppresses safe entrants or only shifts hazards elsewhere.
- Do not baseline unresolved or unvalidated requirements.
- Stop crediting a mechanism when its hypothesis stopping rule is crossed.
- Do not select on documentation completeness alone; require substantive evidence.

Mutation tests deliberately introduce false satisfaction, invalid links, evidence
substitution, unsupported hypotheses, and missing coverage. They test the checking
machinery, not the truth of the governance proposal. No finite schema proves
completeness, logical truth of natural-language claims, or real-world safety.

## 8. GitHub issue 1: proposed reorganization

No remote issue has been edited. A reviewable split is:

1. **Investigate external-signal dependence in specified consequential domains.**
   Links to `HYP-SIGNAL`. Freeze initial information, domains, target performance,
   interaction budget, and comparison conditions before drawing conclusions.
2. **Determine whether candidate boundaries permit effective intervention.**
   Links to `HYP-MARGIN`, `REQ-CONTROL`, and `REQ-FEEDBACK`. Measure full control
   effectiveness and timing, separately from signal dependence.
3. **Characterize sustainable human–AI cooperation under changing power.**
   Links to `CH-COOPERATE`, `HYP-AI`, and `REQ-COOPERATE`. Attach staged autonomy
   and bounded incentives as alternatives rather than writing autonomy into the need.

An investigation can conclude supported, refuted, narrowed, or inconclusive.
Changing the historical AI Pacing specification is a subsequent explicit decision.
The issue's podcast attribution is not independently established by this rebuild;
its proposal is the source being modeled.

## 9. Legacy proposition coverage and intentional gaps

The following map accounts for all 29 legacy YAML nodes. It is a migration review,
not an assertion that the new model fully reproduces or validates their content.

| Legacy nodes | Treatment in the challenge workspace |
|---|---|
| K1 | Distinction between capability, resources, and consequential agency informs the boundary; operational separability remains uncertain. |
| K2 | Preservation of control informs the mission; pacing is a candidate strategy rather than a universal requirement. |
| K3 | Different treatment of development and deployment is a design option; both remain within lifecycle analysis. |
| K4 | Expert assurance is decomposed into competence, assessability, custody, and competitive entry; the public-frontier trigger is not inherited as a requirement. |
| K5 | Independent initial action and future participation are separated in CH-ENTRY. |
| K6 | Reciprocity is PROP-RECIP, attached to CH-COORD. |
| K7 | Warning time is refined into effective control before a prevention deadline. |
| D1 | The release compact remains an aggregate proposal in the baseline; no compact is mandated. |
| D2, I3 | Controlled rival-lab review is PROP-RIVAL, with distinct expertise, custody, and competition obligations. |
| D3 | Profit incentives are an unvalidated causal mechanism; review success is not assumed to make safety profitable. A dedicated economic hypothesis remains to be elicited. |
| D4, I4, I5 | Infrastructure dependencies and activation latency are PROP-DEPEND; detailed engineering and common-cause analysis remain open. |
| D5, I1 | Boundary events contribute to PROP-TRIPWIRE; useful warning depends on effective action and feedback. |
| D6, I6 | International sequencing is a proposal; the exact seven-stage order is not required. |
| H1 | Operational separability remains an explicit unresolved boundary assumption; the legacy falsifier still matters. |
| H2 | Leakage and review value enter CON-CUSTODY; quantitative net value remains unevaluated. |
| H3 | Public-frontier measurability remains an unresolved prerequisite of PROP-RECIP; it needs a dedicated measurement study before selection. |
| H4 | Activation latency remains an unresolved prerequisite of PROP-DEPEND; a positive time margin must be demonstrated. |
| H5 | Durable political support is not established by independent initial executability; stakeholder and coalition validation remain open. |
| I2 | Safe reporting and evidence handling become PROP-REPORT; sanctions and legal safe harbors require jurisdiction-specific design. |
| I7 | Data-center taxation remains an unallocated legacy option; no stakeholder-derived fiscal requirement has been established. |
| Q1 | Frontier measurement remains unresolved, not a reason to presume a single scalar frontier. |
| Q2 | Expert assessment and custody remain separate obligations and a recorded conflict. |
| Q3 | Independence of vetoes is an open common-cause question, not a count of nominal controllers. |
| Q4 | Collapse of separability remains a falsification case for control proposals. |

The current model is a seed for analysis, not a closed or exhaustive inventory.
Operational separability, frontier measurement, activation latency, and rival-review
value have explicit untested hypothesis records and block selection of dependent
proposals. Durable political support is a separate untested hypothesis; initial
executability does not establish it. A full jurisdiction-specific control structure,
retirement scenario, economic model, coalition model, and stakeholder elicitation
are subsequent evidence work, not facts supplied by this draft.

## 10. Method sources

This model adapts, rather than claims full compliance with:

- [NASA stakeholder expectations](https://www.nasa.gov/reference/4-1-stakeholder-expectations-definition/): identify intended use and stakeholder needs.
- [NASA requirements definition](https://www.nasa.gov/reference/4-2-technical-requirements-definition/): derive and validate obligations with traceability.
- [NASA design solution definition](https://www.nasa.gov/reference/4-4-design-solution-definition/): evaluate alternatives against expectations and constraints.
- [MIT systems safety methods](https://psas.scripts.mit.edu/home/books-and-handbooks/): analyze losses, hazards, control structures, and unsafe control actions.

These sources justify the analysis method, not the proposed AI policies.
