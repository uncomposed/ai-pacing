# Bootstrapping AI Pacing from one actor

## Status

Design extension for canonical review. This document proposes additional mechanisms and design principles for AI Pacing without silently promoting them into the kernel. It is intentionally implementation-agnostic: legal, financial, technical, and organizational specialists should be able to instantiate these interfaces in different ways.

## Problem

The current frontier may face race dynamics in which a developer, employee, investor, or other actor prefers mutual restraint but fears becoming the unilateral loser if competitors continue racing. A useful pacing regime should therefore admit action by one actor before comprehensive law, regulation, or international agreement exists.

The bootstrap problem is:

> What can one actor do now that is low-cost while unreciprocated, becomes materially constraining when matched, lowers the next actor's cost of joining, and does not require trusting a central regulator or the private internal state of another laboratory?

This note develops five interfaces:

1. conditional reciprocal commitments;
2. participant downside mutualization;
3. publicly auditable capability predicates;
4. insider incentive inversion;
5. transparency credit without transparency dependence.

These are mechanisms, not mandated implementations.

## 1. Conditional reciprocal commitments

An actor should be able to make a binding standing commitment whose costly provisions activate only when predefined reciprocal conditions are satisfied.

Abstractly, actor `i` publishes a commitment function:

`P_i(C, R)`

where:

- `C` is verified coverage or participation by other relevant actors;
- `R` is an agreed observable risk/capability state;
- `P_i` is the resulting pacing obligation.

The first actor can therefore incur only bounded setup or commitment costs while avoiding immediate strategic surrender. Additional participation can automatically activate stronger obligations already specified in advance.

Desired properties:

- unilateral entry is possible;
- activation conditions are public and versioned;
- reciprocity can be automatic rather than renegotiated;
- obligations can deepen as participation increases;
- exit/withdrawal rules are defined before activation;
- later public institutions may adopt or supersede the private mechanism.

The exact instrument may be contractual, corporate-governance-based, financial, organizational, or another enforceable commitment form.

## 2. Participant downside mutualization

Race incentives are strengthened when complying with a pacing regime creates a large downside if another actor defects or wins the race. The regime should therefore permit mechanisms that reduce the compliant actor's downside from reciprocal restraint.

This interface is intentionally broad. Possible implementations may include collateral, insurance, contingent compensation, pooled capital, compensation design, mutual structures, guarantees, or other legal/financial forms.

The design objective is:

`loss_from_compliant_losing -> lower`

without requiring the regime to specify one financial product.

The same principle may apply at multiple levels:

- companies;
- employees;
- investors;
- other actors exposed to race-relative losses.

The framework should not prescribe cross-ownership, securities structures, or any specific fund. Those are implementation questions for experts operating under applicable law.

## 3. Public predicates and capability discovery

The bootstrap should prefer foundational predicates that can ultimately be established from evidence available outside the controlled organization.

### Public Predicate Rule

> No bootstrapped obligation should depend for its primary enforceability on a factual predicate that only the regulated actor can observe.

Internal evidence may strengthen confidence, but opacity should not invalidate the baseline rule.

A particularly useful public state variable is demonstrated public capability. Public testing does not reliably establish an upper bound on hidden capability, but repeated reproducible black-box testing can establish lower bounds on what publicly accessible systems can do.

A public capability record may be represented abstractly as:

`C = (task_distribution, environment, harness, budget, reliability, date)`

The public frontier is then an accumulating multidimensional set of reproducibly demonstrated capabilities. Evidence of capability can ratchet concern upward; failure to demonstrate a capability should not by itself establish that the capability is absent.

### Capability discovery as a useful product

One possible rendering is a multi-model router that sends ordinary user requests to multiple systems, evaluates or judges the outputs, returns a higher-quality answer to the user, and simultaneously produces comparative capability evidence. Evaluation subsidies can therefore buy both user value and frontier measurement.

This is an implementation example, not a canonical requirement.

## 4. Insider incentive inversion

If a laboratory defects from a pacing commitment, management may have incentives to conceal the breach while employees may face financial, career, legal, or social costs for reporting it.

The regime should permit mechanisms that invert this ordering:

`prompt disclosure < being caught < concealment/retaliation`

in expected cost to the violating organization, while reducing the personal cost of good-faith reporting for insiders.

Possible implementation families include:

- safe harbors;
- anti-retaliation protections;
- career or income protection;
- bounties or contingent rewards;
- pooled downside protection;
- escalation rights;
- other mechanisms that make concealment individually less attractive.

The canonical idea should not prescribe a specific employee mutual, fund, equity swap, bounty percentage, or compensation instrument.

### Reward the proposition, not the payload

A reporting mechanism should reward establishing the relevant violation, not unnecessary exfiltration of dangerous assets, model weights, proprietary information, or other sensitive material.

The desired property is that insiders can expose a breach without making the underlying hazard easier to proliferate.

## 5. Transparency credit without transparency dependence

AI Pacing should behave as if the laboratory and the AI-development process may eventually become internally opaque.

Design principle:

> Design for opacity; exploit transparency opportunistically.

Public capability and observable external consequences provide the baseline evidence available even when private inspection fails. Privacy-preserving audits, secure evaluations, interpretability, telemetry, and other internal transparency mechanisms should be aggressively developed because each can improve confidence and reduce the cost of cooperation.

But no single increase in opacity should mechanically increase permitted power.

A useful abstraction is:

`permission = baseline_permission + verified_transparency_credit`

If a private assurance mechanism fails, the associated transparency credit should disappear; the underlying public obligations should not disappear with it.

This creates positive incentives for laboratories to compete on better verification technology while keeping the safety case robust to verification failure.

## 6. Adversarial audit-development market

Once reciprocal commitments exist, each participant has a direct interest in detecting hidden defection by other participants while protecting its own sensitive information.

The regime should therefore permit or encourage adversarial development of privacy-preserving verification techniques:

- one actor proposes an auditing method;
- rivals, researchers, or designated red teams attempt to defeat it;
- successful attacks improve the next version;
- better verification can justify stronger reciprocal commitments, lower collateral requirements, or additional permissions.

The important object is not one trusted digital monitor. It is an evolving verification ecology in which failure is expected and informative.

No particular cryptographic, cyber, hardware, or interpretability technique is canonical.

## 7. Economic-boundary tripwires

A bounded internal system should not acquire unauthorized control over external rivalrous resources merely because it can reason about them.

A useful architecture-neutral boundary is unauthorized acquisition or exercise of claims over external resources such as:

- money or financial accounts;
- compute;
- credentials;
- labor;
- land or property;
- physical infrastructure;
- persistent hosted processes;
- communications accounts;
- companies, contracts, logistics, energy, or robots.

Crossing such a boundary is not automatically proof of misalignment. It is high-value evidence that the boundary between internal capability and external power has failed.

### Exposure-tax hypothesis

A potentially useful hypothesis is that converting hidden internal capability into durable external power often requires actions that create observable causal effects in independently controlled human systems before irreversible dominance is reached.

If true, external economic agency imposes an epistemic exposure tax on covert power-seeking. The regime should seek to maximize this tax through redundant independent observers and retained human-controlled dependencies.

This must remain a falsifiable hypothesis. A sufficiently capable system may use proxies, disposable probes, excellent simulation, authorized channels, or other methods to reduce exposure. The framework should therefore treat this mechanism as an additional warning opportunity, not a complete containment proof.

## 8. Self-assembly path

One plausible bootstrap path is:

`individual -> conditional employee commitment -> corporate governance commitment -> reciprocal corporate compact -> stronger verification incentives -> wider participation -> public institution`

Each step should create an actor or artifact capable of triggering the next step.

Examples of replaceable implementation choices include:

- employee conditional-action agreements;
- board or trust resolutions;
- reciprocal bonds;
- conditional governance rights;
- pooled or insured downside protection;
- public capability routers;
- breach bounties;
- privacy-preserving auditing competitions.

None is individually required for the idea to remain intact.

## 9. Design invariants

A serious rendering of bootstrap pacing should preserve these invariants:

1. **One actor can enter first.** Initial participation must not require prior universal agreement.
2. **Unreciprocated exposure is bounded.** The first actor should not need to accept the full sucker's payoff before others join.
3. **Reciprocity can activate automatically.** Matching commitments should not require a fresh grand bargain at every step.
4. **Public predicates anchor the baseline.** Foundational obligations should not rely solely on private facts controlled by the regulated actor.
5. **Hidden capability is not certified away.** Failure to demonstrate a capability is not evidence that it does not exist.
6. **Marginal transparency always helps.** Better auditing, interpretability, or reporting can increase confidence without becoming a single point of failure.
7. **Opacity never grants permission by itself.** Losing visibility should not automatically relax constraints.
8. **Insiders can expose defection safely.** Reporting channels should reward establishing a violation without requiring dangerous exfiltration.
9. **Cheating becomes harder as independent observers increase.** The cost of successful concealment should grow with the number and diversity of independently motivated observers.
10. **Implementation remains replaceable.** Finance, law, cryptography, corporate governance, and evaluation methods should remain expert design spaces behind stable interfaces.

## 10. Canonical propositions to review

This extension suggests review of, rather than silent modification to, the following current propositions:

- **K3 / D5 / I1 / I2:** clarify the economic/external-agency boundary and the role of independent external evidence.
- **K4 / D2 / H2 / Q2:** separate the requirement for adversarial assurance from the current implementation emphasis on direct rival-lab access; privacy-preserving and third-party mechanisms should remain valid implementations.
- **K5 / K6 / D6 / I6:** add self-assembling conditional reciprocity before treaty-level or government-mediated coordination.
- **K7:** consider whether warning time should explicitly include public capability, external consequence, and insider-alarm channels.
- **H3 / Q1:** distinguish public capability lower bounds from claims about complete or hidden capability measurement.
- **H5:** test whether participant downside mutualization can create constituencies for restraint independent of catastrophic-risk agreement.

## 11. Open questions

- What forms of conditional commitment are legally durable while preserving unilateral entry?
- Which public capability dimensions are sufficiently reproducible to anchor reciprocal rules?
- How should public capability comparisons control for harnesses, budgets, scaffolds, and model access conditions?
- How should a regime distinguish legitimate whistleblowing from unsafe exfiltration or false accusations?
- Which forms of downside mutualization reduce race incentives without producing unacceptable competition, securities, governance, or moral-hazard problems?
- How should transparency credit be quantified without Goodharting the assurance process?
- Can privacy-preserving audits remain useful against systems with superhuman cyber capability?
- How much external causal interaction is actually required before dangerous systems can acquire durable power?
- Which independently controlled economic and physical systems provide the strongest observable warning boundaries?
- When does private mechanism design cease to be sufficient and require statutory public authority?

## 12. Failure conditions

The bootstrap architecture should be reconsidered if evidence shows that:

- reciprocal conditional commitments do not materially change race incentives;
- public capability measurements are too manipulable or irreproducible even as lower bounds;
- insider incentives systematically increase proliferation or unsafe disclosure more than they improve detection;
- downside mutualization substantially increases moral hazard or collusion without compensating safety value;
- private verification repeatedly provides false confidence that weakens baseline controls;
- external power conversion can occur without enough observable interaction to create useful warning time;
- or dominant actors can evade the regime at lower cost than compliant actors can participate.

The desired architecture is therefore not a promise that one mechanism will work. It is a fault-tolerant coordination system that can absorb improved implementations while preserving a stable vector: slow the conversion of capability into irreversible power, make cooperation easier to enter than defection, and accumulate independent evidence before control is lost.
