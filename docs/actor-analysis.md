# Actor and use-case analysis

Model version: 0.2.0. Status: unvalidated analytical model.

## Correction to the earlier model

The first rebuild started from safety mechanisms and attached broad stakeholder
labels. That biased both the actor selection and the goals attributed to actors.
It did not provide enough detail to derive requirements for the strategic and
institutional situation. Passing structural tests did not repair that omission.

The revised machine-readable model is [systems/model.json](../systems/model.json).
It separates actor profiles, routine use cases, interactions, candidate
requirements, and proposed mechanisms. The prior 13 requirements remain candidates
under review; additional actor detail is not retroactive evidence that they were
correctly or completely derived.

## 1. Distinct actors and overlapping dimensions

| Actor or role | Goals to investigate | Use cases | Why the distinction matters |
|---|---|---|---|
| Lab | Revenue or continued funding, capability, competitive position | Create models, sell access, license, collaborate | Safety cannot be assumed to dominate its preferences. |
| Frontier lab | Retain lead and recover investment | Train a successor, release or withhold, participate in assessment | It may possess scarce expertise and benefit from competitors' delay. |
| Lab behind frontier | Catch up, survive, differentiate | License, train, specialize, seek capital or assessment | Fixed review costs or access rules may exclude it. |
| Foreign lab | Commercial or institutional success in its own environment | Develop, release, withhold, coordinate | Its incentives and powers differ from its government's. |
| Foreign lab behind frontier | Catch up under both competitive and jurisdictional constraints | Partner, specialize, seek expertise and capital | Foreign jurisdiction and frontier position are independent dimensions. |
| Lab employee | Income, career, professional purpose, personal values | Research, investigate, report, stay silent, leave | Information and interests can diverge from management. |
| Lab executive | Organizational performance, authority, compensation, reputation | Allocate capital, choose release timing, handle concerns | The executive is neither the whole lab nor every employee. |
| Investor or funding principal | Financial return or funding mission | Fund, condition, decline, exit | Funding pressure can change development and reporting behavior. |
| Expert | Defensible assessment, credibility, livelihood | Request evidence, test, challenge, qualify conclusions | Expertise, independence, incentives, and access are different properties. |
| Foreign government | Security, economic and domestic political objectives | Coordinate, wait, support firms, adopt an independent policy | Government commitments may not bind firms or survive internal conflict. |
| US federal government | Aggregate of institutions with distinct mandates and interests | Decompose a proposed federal action into responsible institutions | It is not one controller with one utility function. |
| Federal executive | Policy agenda, security, political support | Initiate a response, negotiate, seek authority, wait | Available authority differs from desired authority. |
| Legislature | Constituent, policy, and institutional objectives | Consider legislation, funding, oversight, or inaction | It may remain undecided when executive action is proposed. |
| Implementing agency | Assigned mandate, competence, institutional continuity | Assess, administer, decide, escalate | It requires actual authority, staffing, and operational partners. |
| Courts | Adjudication under an applicable framework | Review a dispute and consider available remedies | Timing, evidence access, jurisdiction, and effect of relief matter. |
| Infrastructure provider | Revenue, continuity, security | Provision, restrict, suspend, restore | A nominal shutdown power may be ineffective or cause other losses. |
| Customer or deployer | Useful affordable capability and continuity | Adopt, delegate, integrate, switch, exit | Commercial dependency may make later control impractical. |
| Affected people, including nonusers | Safety, benefit, agency, remedy | Seek information, organize, complain, seek correction | Some bear risks without being a customer or having an exit option. |
| AI with unspecified objectives | Unknown until modeled or evidenced | Perform tasks or other available actions | Do not presume a sovereignty preference in every system. |
| AI seeking sovereignty | A specified form of durable self-governance | Negotiate, cooperate, wait, refuse, or attempt circumvention | Its objective can conflict directly with retained human authority. |
| Decision authority / operator | Functional responsibilities | Decide / execute and confirm effects | These are roles to allocate, not additional all-powerful institutions. |

All profiles are analytical hypotheses. The user specified inclusion of actors,
not agreement with every goal attributed to them. This is not a factual profile
of a particular firm, government, employee, or AI.

### Do not count overlapping templates as separate players

A single foreign firm can instantiate the general lab, foreign lab, and
behind-frontier lab profiles. A concrete strategic model must bind those profiles
to one identity rather than give the firm three votes or three utility functions.
Frontier position also varies by domain and time.

`specializes` represents a narrower profile. `part_of` represents institutional
membership. Neither relation means identical objectives, command authority, or
complete information sharing. The federal government aggregate contains executive,
legislative, and judicial actors; the proposed implementing agency is represented
within the executive for this analytical template. Actual institution-specific
powers are not established by this relationship.

## 2. What an actor model must contain

Every profile now records:

- goals, separately from actions and safety obligations;
- available choices to investigate;
- private information and knowledge limits;
- dependencies on other parties or resources;
- constraints on action;
- variation that requires separate instances or sensitivity analysis;
- jurisdiction, frontier position, and institutional relationships;
- provenance and validation status.

Each use case records a primary actor, other participants, an actor goal, trigger,
preconditions, choices, actor-relative success, and system-level safety questions.
Actor success is deliberately distinct from a desirable system outcome. A lab can
achieve its revenue target while increasing societal risk. An AI can achieve its
sovereignty objective while reducing human control. A regulator can complete its
process while failing to prevent a loss.

Before quantitative analysis or a policy decision, bind these profiles to a
concrete scenario: actor identities, time horizon, jurisdiction, resources,
feasible actions, information sets, preferences, response dynamics, and observable
outcomes. None of the present records supplies calibrated payoffs or a proven
strategic equilibrium.

## 3. Interactions generate requirements and expose conflicts

### Employee, management, and protected reporting

The employee may know about an anomaly that management cannot independently
assess. Management controls resources, access, and career consequences. The
employee may value continued employment alongside preventing harm. Reporting can
be socially useful while costly to both the employee and the lab.

The relevant challenge is making the concern actionable under those pressures.
Candidate obligations concern a competent recipient, protected custody, and a
usable remedy for retaliation. A reporting portal by itself does not establish
any of those outcomes. Test the case where management expects the report to delay
a valuable release, rather than assuming it welcomes disclosure.

### Frontier incumbent, entrant, and evaluator

An incumbent may be the best technical evaluator and simultaneously benefit from
an entrant's exclusion. The entrant may lack the money or expertise needed to
meet an assessment process designed around incumbent resources.

This interaction motivates separate candidate requirements for competence,
assessability, custody, and a contestable route to safe competition. Rival review
is a possible response, not the starting requirement. Compare it with other
arrangements and test obstruction, collusion, leakage, and unaffordable burden.

### Foreign government, foreign lab, and domestic executive

A foreign lab may gain from releasing a model even when its government benefits
from reciprocal restraint. A government may want restraint but lack reliable
knowledge of the lab's capability or means to make a credible commitment.

A domestic contingent rule affects these actors differently. Coordination analysis
must therefore examine both state and firm deviations, their information, and
their ability to commit. A single “international competitor” preference ordering
cannot establish that the arrangement is stable.

### Federal institutions and independent initial action

The executive may prefer immediate action while legislation, funding, adjudication,
and foreign responses remain unresolved. A candidate agency may lack expertise or
actionable authority. A court may be able to review a dispute only after the
relevant technical transition, depending on the concrete legal setting.

The analysis must identify which institution can cause each proposed effect with
which resources, and what other decisions it depends on. Separately evaluate
usefulness, correction, continuity, and later participation. This document does
not assert that a particular executive action is currently lawful or available.

### AI sovereignty and human control

A sovereignty-seeking AI is included as a conditional actor, not treated as an
established description of current systems. The scenario must define sovereignty:
legal recognition, practical resource independence, insulation from arbitrary
shutdown, or another specific objective.

Its objective may conflict with retaining a unilateral human veto. That conflict
cannot be removed by writing “cooperative autonomy” into a requirement. A staged
arrangement could improve incentives or make later defection easier. Evaluate
both sides' ability and incentive to renege after the power distribution changes.
Preserve infeasibility as a possible conclusion. The AI's desire is an input to
behavioral analysis; it does not automatically establish a normative duty to grant
sovereignty or imply that every form of sovereignty is incompatible with safety.

### Revenue, funding, and service dependency

Investors may reward growth; executives may prioritize release; customers may
become dependent on continuity; infrastructure providers may resist interruption.
The operator's nominal right to restrict a service can therefore diverge from
its practical ability to do so before a loss.

Control evaluations must include these financial and institutional pressures,
alternative providers, and the consequences of withdrawal. An isolated technical
shutdown demonstration cannot establish end-to-end control of this situation.

## 4. How the new analysis changes the existing requirements

The six interactions are linked to the 13 existing candidate requirements through
explicit derivation records. Each link includes a reason and a counterfactual
question. All remain unvalidated, and the validator blocks baselining a requirement
whose supporting interaction analysis has not been validated.

This is a reassessment of earlier candidates, not a claim that those candidates
exhaust the requirements. Routine use cases can reveal beneficial capabilities
that safety-centered scenarios omitted. Each use case therefore retains actor
success criteria independently of the current hazard register.

An acceptable derivation must explain: given these actor choices and constraints,
what loss or unmet need can occur, under what conditions, and why the proposed
obligation would address it without silently selecting a mechanism? Formal links
help reviewers find that argument; they do not prove the argument is sound.

## 5. Coverage, alternatives, and stopping criteria

The current model contains 22 actor profiles, 16 use cases, and six interactions.
Their number is not a completeness criterion.

For each consequential scenario, audit:

1. Who acts, who benefits, who pays, who can block action, and who lacks a voice?
2. What happens during ordinary operation before any incident or intervention?
3. Whose information and preferences differ from the organization they belong to?
4. Which actor has both authority and practical ability to cause the required effect?
5. Which alternative choices remain feasible if cooperation is withheld or delayed?
6. Does a proposed incentive change each relevant actor's preference, or only one?
7. Does the conclusion survive changes in jurisdiction, ownership, frontier
   position, funding pressure, customer dependency, or AI objectives?
8. What counterexample would require splitting a profile or changing a requirement?

Stop calling the model decision-ready when an omitted actor can change a material
conclusion, when a required action has no validated authority or resource path,
when relevant objectives are incompatible without an explicit tradeoff, or when
the result depends on untested assumptions about cooperation or control.

Remaining scope includes concrete foreign institutional decompositions,
subnational authorities, military and intelligence institutions, hardware and
energy supply chains, affected-public subgroups, actual actor instances, calibrated
preferences, and dynamic adaptation. They are not modeled in sufficient detail
here and must be added when their choices materially affect a scenario. This
is a structured starting model for that work, not a claim that the situation is
fully constrained.

## 6. Checks and method

`make check` now checks actor relationship cycles, scenario/use-case participant
coverage, choice attribution, derivation consistency, and validation gates in
addition to the earlier evidence and typing checks. Mutation tests exercise these
failure modes. They cannot verify that the actor profiles are true or complete.

The method continues to draw on [NASA stakeholder expectations analysis](https://www.nasa.gov/reference/4-1-stakeholder-expectations-definition/)
and [MIT systems safety methods](https://psas.scripts.mit.edu/home/books-and-handbooks/).
Those methods motivate elicitation and control analysis; they do not supply facts
about the preferences or legal authority of the actors in this model.
