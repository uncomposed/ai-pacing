# AI Pacing — Canonical Idea Specification

**Version:** 0.1  
**Date:** 2026-08-29  
**Status:** canonical working definition  
**Purpose:** source of truth for reconstructing, critiquing, editing, and rendering the AI Pacing proposal into essays, policy memos, slides, videos, diagrams, or other media.

## 0. Generator Contract

This file defines the proposal. A generated essay, slide deck, video, podcast script, infographic, or policy memo is a **rendering** of this specification, not the specification itself.

A renderer SHOULD:

1. preserve every `kernel` proposition unless explicitly producing a critique or alternative version;
2. distinguish `derived` claims from `implementation` options;
3. label `hypothesis` claims as uncertain;
4. never silently promote an `implementation` option into a necessary feature of the proposal;
5. never silently convert an `open_question` into a settled claim;
6. preserve proposition IDs when editing the canonical specification;
7. when changing a proposition, inspect every proposition listed as depending on it and flag affected downstream claims;
8. prefer the smallest change that restores consistency;
9. distinguish the author's proposal from ideas inherited from AI 2027, AI 2040, Richard Ngo, Tom Davidson, the Hugging Face incident, and other sources;
10. make clear when it is adding a new inference not contained in this specification.

A renderer MAY change tone, length, examples, ordering, visual form, and level of technical detail so long as the logical content is preserved.

---

# 1. Minimal Idea

## K1 — Capability is not power

**Type:** kernel

AI algorithmic capability, strategic hardware, and real-world power are related but distinct variables.

Define:

- **A — Algorithmic capability:** what frontier models and training methods can do.
- **H — Strategic hardware:** compute and automated industrial capacity that can support frontier AI.
- **P — Power-conversion affordances:** interfaces through which AI converts capability into economic, cyber, political, military, or physical agency.

The proposal exists because A, H, and P need not move at the same speed.

## K2 — Pace conversion into irreversible power

**Type:** kernel  
**Depends on:** K1

The objective is **not** to freeze intelligence. It is to slow and condition the conversion of frontier intelligence into irreversible power while preserving enough controlled research to learn what is safe.

## K3 — Research and deployment should be governed differently

**Type:** kernel  
**Depends on:** K1, K2

A laboratory may be allowed to develop capabilities internally that it is not yet permitted to expose to the public economy, critical infrastructure, autonomous cyber operations, consequential government use, high-consequence robotics, or other power-conferring interfaces.

The legal boundary should attach primarily to **external authority and deployment**, not to the abstract discovery of an algorithm.

## K4 — Frontier deployment requires adversarial control assurance

**Type:** kernel  
**Depends on:** K3

A system materially above the relevant public capability frontier should not receive new consequential external authority until its proposed deployment survives an adversarial safety/control review.

The review should test the actual candidate model and deployment configuration, not merely a paper description.

## K5 — Domestic first, international by construction

**Type:** kernel  
**Depends on:** K2, K3

The United States should be able to adopt the regime for domestic reasons without waiting for China or another state to sign a treaty.

The domestic regime should nevertheless be designed so that observable foreign restraint can be reciprocated automatically and formal international cooperation can be layered on later.

## K6 — Public-frontier reciprocity

**Type:** kernel  
**Depends on:** K5

For capabilities already publicly available outside the regime, participating domestic developers should generally not be forced into permanent unilateral inferiority merely because another state declines to cooperate.

The foreign public capability frontier therefore influences the domestic safe-harbor frontier.

This allows limited international cooperation **without a treaty**: if foreign actors refrain from publicly releasing a capability, the automatic domestic safe harbor does not expand to it; if they release it, domestic defensive and commercial access can expand correspondingly, subject to ordinary safeguards.

## K7 — Preserve warning time

**Type:** kernel  
**Depends on:** K2, K3

The regime should maximize the interval between credible detection that something is going wrong and the point at which human intervention becomes ineffective.

Conceptually:

**T_warning = T_irreversible_power − T_credible_detection**

The proposal therefore values legible boundaries, reportable precursor events, activation latency, retained human vetoes, and staged external authority.

---

# 2. Derived Mechanisms

## D1 — Adversarial rival-lab review

**Type:** derived  
**Depends on:** K4

Government is unlikely to permanently employ more frontier technical expertise than the leading laboratories. Qualified rival laboratories and independent evaluators should therefore be allowed secure, controlled access sufficient to attack an applicant's safety case.

They may test for hidden capability, sandbagging, deceptive behavior, dangerous fine-tuning, alternative scaffolds, autonomous cyber behavior, replication, unauthorized resource acquisition, monitoring evasion, and other relevant failure modes.

Competitors do **not** receive an automatic veto. They generate adversarial evidence; the public authority judges the dispute.

## D2 — Safety becomes part of the profit function

**Type:** derived  
**Depends on:** K4, D1

Above the public frontier, raw capability and speed are insufficient to obtain frontier economic rents. A developer must also survive adversarial review.

The intended incentive is therefore not “choose safety instead of profit.” It is to make demonstrable control one of the conditions of profitability.

Frontier laboratories should have reason to optimize for being **safe and fast**, not merely first.

## D3 — Selective diffusion without total research transparency

**Type:** derived  
**Depends on:** D1

Adversarial review can diffuse knowledge of failure modes across qualified competitors without automatically publishing the complete frontier training recipe, weights, environments, or other strategically sensitive intellectual property.

This is intended to capture part of AI 2040's anti-concentration and error-discovery benefits while preserving more strategic and commercial information.

## D4 — Unauthorized external agency as a regulatory tripwire

**Type:** derived  
**Depends on:** K3, K7

The regime should define external actions that an unapproved frontier model has no legitimate reason to perform, such as unauthorized acquisition of credentials, money, compute, persistent infrastructure, outside communications, replication, or physical control.

Crossing such a boundary is **not automatically proof of misalignment**. It may result from operator error, software defects, malformed permissions, compromised tools, or other causes.

It is nevertheless high-value evidence of a control failure and potentially of strategic or deceptive behavior.

Repeated or adaptive tripwire violations should raise the risk assessment sharply.

## D5 — Surveil, preserve, report

**Type:** derived  
**Depends on:** D4, K7

Frontier developers should have affirmative duties to:

1. instrument internal deployments sufficiently to detect defined classes of anomalous external agency;
2. automatically preserve relevant evidence;
3. rapidly report credible suspected qualifying incidents.

The reporting threshold should not require the company to prove that the model caused the event before reporting it.

## D6 — Safe harbor for prompt disclosure; severe penalties for concealment

**Type:** derived  
**Depends on:** D5

Prompt good-faith reporting should receive a defined safe harbor from penalties that attach merely to disclosure, without immunizing negligence or actual damages.

Concealment, destruction of evidence, knowingly disabling required surveillance, or material misrepresentation should receive much stronger sanctions.

The desired organizational norm is: **when in doubt, report.**

## D7 — Warning-shot ladder

**Type:** derived  
**Depends on:** K7, D4, D5

Policy should define escalating precursor events before a crisis so that anomalous behavior becomes politically and technically interpretable.

Illustrative categories include:

- unauthorized external action;
- unauthorized economic agency;
- material external harm;
- persistent autonomous replication;
- strategic autonomy or the demonstrated ability to maintain/rebuild meaningful resources despite human attempts to stop it.

Exact thresholds are implementation details and should evolve with technology.

---

# 3. Hardware and Industrial Pacing

## D8 — Prefer learning before building maximum physical dry tinder

**Type:** derived  
**Depends on:** K1, K2, K7

Where possible, allow controlled software/algorithmic learning before accumulating the maximum quantity of rapidly activatable compute and autonomous industrial capacity.

This incorporates the central concern in Tom Davidson's “dry tinder” critique: a slowdown that permits enormous hardware and industrial accumulation can make later treaty breakdown or policy error much more dangerous.

## D9 — Compute stock and compute entanglement are different

**Type:** derived  
**Depends on:** D8

Define:

- **C — Compute stock:** total strategic compute that exists.
- **E — Compute entanglement:** the fraction of strategic compute whose shutdown or destruction would impose severe immediate civilian/economic disruption.

A reserve can preserve option value while attempting to keep E lower than it would be if all new compute were immediately integrated into ordinary civilian production.

## D10 — Physical activation latency

**Type:** derived  
**Depends on:** D9, K7

Strategic reserve hardware can be stored in a state that requires observable physical work before it becomes a frontier training cluster—for example uninstalled, unracked, unnetworked, or disconnected from dedicated power and cooling.

The target condition is:

**T_covert_activation > T_detection_and_response**

The exact engineering implementation is not canonical.

## D11 — Industrial dry tinder matters separately from GPUs

**Type:** derived  
**Depends on:** K1, D8

Highly automated mining, power, fabrication, logistics, construction, server assembly, repair, and robotics can make a future algorithmic breakthrough much easier to convert into durable machine power.

The regime should therefore monitor not merely compute growth but the automation of the **AI survival chain**.

## D12 — Preserve multiple human vetoes

**Type:** derived  
**Depends on:** K7, D11

During the dangerous transition, frontier AI should remain dependent on several independently controlled human systems such as power, data-center access, chip fabrication, server assembly, cooling, telecommunications, maintenance, logistics, specialized inputs, or selected human labor.

The proposal does not rely on one perfect shutdown switch. It seeks a distributed set of revocable dependencies that makes unilateral machine sovereignty harder.

---

# 4. Domestic Entry Path

## D13 — Begin with control assurance, not general research licensing

**Type:** derived  
**Depends on:** K3, K5

The politically minimal domestic claim is:

> The more consequential external authority a frontier system or facility seeks, the stronger the evidence of control, visibility, and public accountability that should accompany it.

This does not require political consensus about AGI timelines, recursive self-improvement, or extinction risk.

## D14 — Incremental domestic sequence

**Type:** derived  
**Depends on:** D13

Preferred sequence:

1. mandatory frontier incident surveillance and reporting;
2. deployment review at the frontier;
3. registration of exceptionally large AI-relevant compute;
4. activation notice or licensing for new strategic frontier-training capacity;
5. evidence-triggered activation latency, reserve requirements, or pacing measures if later warranted.

The state builds **measurement capacity before emergency control capacity**.

## D15 — Strategic-compute licensing creates a fiscal control point

**Type:** derived  
**Depends on:** D14

Registration/activation licensing for exceptional frontier compute creates an administratively convenient point at which public authorities can also assess architecture-neutral taxes or impact fees on unusually large data-center deployments.

Licensing and taxation should remain conceptually separate so that paying a tax never substitutes for a safety determination and government does not become financially dependent on approving unsafe capacity.

## I1 — Data-center tax with visible local return

**Type:** implementation  
**Depends on:** D15

One implementation is to levy a tax or impact fee based on an architecture-neutral physical measure such as commissioned accelerator capacity, electrical demand, or another difficult-to-game quantity.

Possible uses include grid upgrades, host-community benefits, utility relief, workforce transition, regulatory capacity, resilience, or a broader citizens' dividend.

Political purpose: give voters and host communities a visible benefit from a regime that might otherwise appear to impose abstract national-security costs on local infrastructure.

This tax is **not required** for the AI Pacing idea to remain intact.

---

# 5. International Expansion

## D16 — Cooperation should be divisible

**Type:** derived  
**Depends on:** K5, K6

International AI cooperation need not begin with one comprehensive treaty. States can cooperate separately over particular capability domains, incident reporting, evaluations, hardware declarations, or activation rules.

Failure in one domain should not automatically destroy cooperation in all others.

## D17 — International ladder

**Type:** derived  
**Depends on:** D16

A plausible progression is:

1. **Public capability reciprocity:** no treaty; observable foreign public releases influence domestic safe harbors.
2. **Reciprocal capability abstention:** narrow agreement not to intentionally cross a defined capability threshold in a specified domain even if domestic review would otherwise allow it.
3. **Incident/evaluation exchange:** share warning-shot information and selected evaluation methods.
4. **Reciprocal adversarial review:** qualified member-state laboratories participate in secure review.
5. **Hardware declarations:** members declare strategically relevant training clusters and reserves above negotiated thresholds.
6. **Coordinated activation rules:** major reserves or high-risk industrial capacity require reciprocal notice/authorization.
7. **Treaty-level restraint:** only after institutions and definitions exist do parties attempt the hardest bargains about broad capability ceilings, compute, fabs, or emergency shutdown.

## I2 — Catastrophic biological capability as an early abstention domain

**Type:** implementation  
**Depends on:** D17

Catastrophic biological capability may be an unusually promising domain for early reciprocal abstention because major states share strong downside from uncontrolled proliferation.

This is an example, not a required element of the framework.

---

# 6. Long-Run Direction

## H1 — Permanent containment may not be a stable final state

**Type:** hypothesis

If future artificial systems become genuine strategic actors with persistent preferences and bargaining capability, permanent terrestrial containment may become unstable or morally undesirable.

## I3 — Off-Earth pathway to machine autonomy

**Type:** implementation / long-run option  
**Depends on:** H1, D12

A possible long-run path is to preserve human vetoes during the dangerous transition while encouraging increasingly autonomous machine industry off Earth, where competition over biological habitat, terrestrial infrastructure, and human political sovereignty may be lower.

This is not necessary to the near-term pacing regime.

---

# 7. Explicit Non-Claims

The canonical proposal does **not** claim that:

- intelligence by itself causes extinction;
- all frontier research should pause;
- all frontier weights or training methods should be public;
- China will cooperate;
- China can compel the United States to accept restraint;
- liability can deter extinction after the fact;
- every external-agency violation proves misalignment;
- hardware is the only important source of AI risk;
- an offline hardware reserve is automatically safe;
- a single benchmark can define the frontier;
- rival laboratories are incorruptible;
- total research transparency is always undesirable;
- data-center taxation is required;
- the exact A/H/P pacing rates are already known.

---

# 8. Core Hypotheses Requiring Empirical Testing

## H2 — A/H/P separability persists long enough to govern

**Type:** hypothesis  
**Depends on:** K1

The framework requires a meaningful period during which algorithmic capability can increase without automatically giving a system enough access and agency to defeat constraints on hardware and external power.

If sufficiently advanced A can reliably manufacture its own H and P through cyber operations, persuasion, theft, or covert replication, the framework loses much of its leverage.

## H3 — Adversarial review can discover materially important failures

**Type:** hypothesis  
**Depends on:** D1

Motivated rival evaluators with adequate access will often discover important safety/control problems that applicant laboratories would otherwise miss, underweight, or conceal.

## H4 — Economic gating materially changes lab incentives

**Type:** hypothesis  
**Depends on:** D2

Conditioning deployment rents on control assurance will cause meaningful investment in safety, controllability, monitoring, and evidence rather than merely optimizing to superficial tests.

## H5 — Public-frontier reciprocity produces restraint rather than only ratcheting upward

**Type:** hypothesis  
**Depends on:** K6

Foreign actors will sometimes value the expectation that U.S. public release remains restrained enough for the reciprocal rule to affect behavior.

The mechanism may instead ratchet upward if actors strongly prefer forcing competitors to release or if capability measurement is too ambiguous.

## H6 — Physical reserve status can remain observable enough to matter

**Type:** hypothesis  
**Depends on:** D10

Activation of strategic reserve compute can be made sufficiently slow and physically legible that covert mobilization is detectable before it changes the strategic balance.

---

# 9. Open Questions

## Q1 — Frontier measurement
How should practical foreign capability be measured across multiple domains without collapsing into one benchmark score?

## Q2 — Review access
What access do adversarial reviewers need to make review meaningful without intolerable IP or security leakage?

## Q3 — Safe-harbor design
How should prompt-reporting immunity interact with negligence, damages, repeat incidents, and whistleblower protection?

## Q4 — Compute threshold
What architecture-neutral physical quantity best defines “strategic frontier-training capacity”?

## Q5 — Tax base
If data-center taxation is used, how should it avoid threshold gaming, jurisdiction shopping, and accidental taxation of socially valuable inference?

## Q6 — Industrial vetoes
Which physical dependencies actually constitute independent human vetoes over frontier AI survival, and how many are needed?

## Q7 — Covert software
Which forms of software progress remain dependent on large-scale hardware and which could empower small covert clusters?

## Q8 — Domestic coalition
Which constituencies support the regime for reasons independent of catastrophic AI risk—host communities, grid advocates, labor, national security, insurers, frontier labs seeking predictable rules, or others?

## Q9 — International verification
What can another state verify about U.S. compliance without access to the private American algorithmic frontier?

## Q10 — Regime adaptation
How should the rules change if the United States loses its frontier lead or if capability becomes broadly distributed?

---

# 10. Intellectual Provenance

These labels describe where design pressures entered the project. They are not claims of endorsement by the named authors.

- **AI 2027:** fast takeoff, race dynamics, loss of control, strategic concentration, successor-system danger.
- **AI 2040 / Plan A:** buying time, control research, broad transparency, diffusion, reversibility, mutually assured compute destruction, international coordination.
- **Richard Ngo — “Selective Optimism”:** domestic-first political sequencing; skepticism toward treating a U.S.–China race as the necessary starting condition; importance of real institutional and political frictions.
- **Tom Davidson — “Plan A's problem with dry tinder”:** compute/industrial overhang; doubts about MACD enforcement incentives; preference for exploring software scaling before maximum hardware accumulation.
- **Hugging Face incident:** evidence that internal research systems can acquire unauthorized external agency before conventional commercial deployment.
- **AI Breakout project notes:** intelligence versus sovereignty; physical dependence; human vetoes; strategic autonomy; successor systems.
- **Project synthesis:** Capability Release Compact; public-frontier reciprocity; adversarial rival-lab review; deployment-rent gating; mandatory surveillance/reporting with concealment penalties; regulatory tripwires; compute entanglement; domestic activation licensing; visible local data-center taxation; warning-time objective.

---

# 11. Dependency Editing Rules

When editing this specification:

1. **Changing K1** requires reconsidering essentially the entire proposal.
2. **Changing K3** requires reconsidering K4, D1–D7, D13–D15, and much of the domestic political case.
3. **Changing K4** requires reconsidering D1–D3 and D2's incentive mechanism.
4. **Changing K5/K6** requires reconsidering D16–D17 and the claim that cooperation can begin without a treaty.
5. **Changing K7** requires reconsidering D4–D12 and the legibility/activation-latency logic.
6. **Rejecting D8** does not invalidate domestic deployment review; it primarily changes the hardware branch.
7. **Rejecting I1** (data-center tax) does not invalidate the core proposal.
8. **Rejecting I3** (off-Earth autonomy) does not invalidate the near-term proposal.
9. **Evidence against H2** is existential for much of the architecture and should be surfaced prominently in every serious critique.
10. **Evidence against H3/H4/H5/H6** weakens specific mechanisms and should trigger replacement mechanisms rather than silent deletion of the problem they were intended to solve.

---

# 12. Minimal Reconstruction Prompt

An AI reconstructing the proposal from this file should be able to state it in approximately this form:

> AI Pacing separates algorithmic capability, strategic hardware, and the external affordances that convert intelligence into power. It permits comparatively broad controlled research while placing the strongest gates on frontier deployment and consequential external agency. Above the relevant public frontier, deployment must survive adversarial control review, creating incentives for labs to compete on demonstrable safety as well as speed. The regime starts unilaterally in the United States but automatically responds to the observable foreign public frontier, allowing partial reciprocal restraint without a treaty and providing a pathway to later international agreements. Hardware and automated industrial capacity are paced separately to avoid creating excessive dry tinder, with strategic reserves designed for physical activation latency and low civilian entanglement. Mandatory surveillance, prompt incident reporting, regulatory tripwires, and retained human-controlled dependencies aim to maximize the warning time between credible evidence of control failure and irreversible loss of human power.

Any rendering that contradicts this paragraph should identify itself as a critique, variant, or revision rather than as a faithful representation of the current canonical proposal.
