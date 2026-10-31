# Proposed extensions from issues #1 and #3

## Status

**Editor decisions, 2026-10-31 (issue #22).** The canonical editor accepted H10
and H14 as hypotheses, I11 as a replaceable option, and Q11, Q12 and Q13 as open
questions. D18 was retyped as the proposed hypothesis H15. D19 was folded into
the accepted hypothesis H2. Both D18 and D19 are now `withdrawn` in the ID
registry, so their IDs are never reused. The review packet and the editor's
decisions are in [`issue-22-editor-review-packet.md`](issue-22-editor-review-packet.md).
The rest of this note was written before those decisions. Where it says
"proposed", read the table below for current status.

Proposed nodes are recorded in `spec/ai-pacing.yaml` with
`provenance.author_status: proposed` and a `proposal` field naming the issue.
They are not part of the accepted AI Pacing proposal:

- they do not count toward kernel identity (AT-001), node-existence, or
  dependency-path acceptance assertions;
- they are left out of the minimal reconstruction and the kernel review
  checklist, and drawn dashed in the dependency graph;
- an accepted node may not be derived from, grounded by, or implemented by a
  proposed node;
- they must still meet every field rule (falsifier, evidence, stopping rule,
  replaceability, provenance).

This note is not a rendering of the specification. If it disagrees with the YAML
at the same commit, the YAML controls. Sections 4 and 5 hold material that the
issues asked to record but that does not belong in proposition nodes.

## 1. Proposed nodes

| ID | Issue ID | Kind | Title | Relations | Status after #22 |
|---|---|---|---|---|---|
| H14 | #1 H6 | hypothesis | External-signal dependence preserves some A/P separation | conditions K1, K2, K3, K7, D5 (contributory) | accepted as hypothesis |
| Q13 | #1 Q5 | open question | Can a credible cooperative autonomy path reduce incentives for AI defection? | relates to K1, K2, K3, K7, D5 | accepted, unresolved |
| H10 | #3 H10 (was H7) | hypothesis | Retrospective audit makes concealment a losing long-run strategy | conditions K7, D5 (contributory) | accepted as hypothesis |
| D18 | #3 D18 (was D7) | derived | Closing-window dynamics may pull strikes earlier (risk to test) | — | withdrawn; retyped as H15 |
| H15 | #22 | hypothesis | Closing-window pressure pulls strikes earlier only without credible commitment | relates to K7, D5, H10 | proposed |
| I11 | #3 I11 (was I8) | implementation | Do not optimize against the audit signal | implements K7, D5 | accepted as option |
| Q11 | #3 Q11 (was Q6) | open question | How independent must auditors be to resist correlated misalignment? | relates to D2, H2, H10 | accepted, unresolved |
| D19 | #3 addendum D19 (was D8) | derived | Review-based model sharing compresses inter-lab capability gaps | — | withdrawn; folded into H2 |
| Q12 | #3 addendum Q12 (was Q7) | open question | What inter-lab and international convergence minimizes singleton and correlated-failure risk? | relates to Q11, H2, D6 | accepted, unresolved |

Issue #1 asked for Q5 as "an open question or design extension". It is recorded
as an open question with the issue's seven sub-questions kept verbatim in
`subquestions`, so none of them is answered by the act of recording it.

Issue #3 suggested an acceptance test for a path from K7 to I11. It was added
to AT-006 when the editor accepted I11 (#22), together with a direct K7 → I11
relation. I11 no longer lists H10 in `implements`: the rule protects
retrospective audit but does not depend on it.

## 2. ID registry and renumbering

Proposition IDs collided across three sources: the YAML, the editorial reference
`AI_Pacing_Canonical_Spec_v0.1.md`, and the off-Earth research report
(`research_notes/Off Earth industry as misalignment control/repo_review.md`,
cited by `docs/off-earth-pact.md`). `spec/id-registry.yaml` now lists every used
and reserved ID per kind, where it is defined, its status, and how colliding
definitions relate. `make check` rejects a YAML node that is unregistered,
whose registered title or status has drifted, or that reuses an ID meaning
something else. `ruby tools/spec_tool.rb next-id H` prints the next free ID.

| Source | Old | New | Why |
|---|---|---|---|
| #1 | H6 | H14 | Editorial H6 exists; H10 is #3's; H11 is reserved for the off-Earth report; H12 and H13 overlap the model's claim IDs |
| #1 | Q5 | Q13 | Editorial Q5 exists; Q11 and Q12 are #3's |
| #3 | H7, D7, I8, Q6 | H10, D18, I11, Q11 | Renumbered in the issue |
| #3 addendum | D8, Q7 | D19, Q12 | Renumbered in the comment |
| off-Earth report | H10 (optional) | H11 | Collides with #3's H10 |
| off-Earth report | D7, D8 | D20, D21 | Editorial D7 and D8 exist (issue #23) |
| off-Earth report | Q6, Q7, Q8 | Q14, Q15, Q16 | Editorial Q6 to Q8 exist (issue #23) |

Two earlier findings are now resolved (issue #23):

- **Register claim IDs looked like proposition IDs.** The model's assumption
  register numbered its result claims H1–H13, and `equilibrium.md` section 7
  numbered its questions 1–10. They are now `AR-H1` to `AR-H13` and `EQ-Q1` to
  `EQ-Q10`, declared as prefixed local namespaces in the registry. The report's
  optional H10 stays reserved as H11; H10 follows the editor's decision.
- **The off-Earth report's D7, D8, Q6, Q7 and Q8 collided with editorial IDs.**
  They are renumbered to D20, D21, Q14, Q15 and Q16 in the report and the
  registry. No `reserved-conflict` entries remain. The report's other candidates
  (H7 to H9, I8 to I10) did not collide and keep their numbers.

The 16 legacy collisions between the YAML and the editorial reference (D1–D6,
H1–H5, I1–I3, Q3, Q4) are recorded as `legacy` and remain the open conformance
issue described in `CANONICALITY.md`. K1–K7, Q1 and Q2 are recorded as the same
proposition in different words. That is a judgment made when the registry was
created, and the editor may revise it.

## 3. Reviews requested by issue #1

These are review notes. No accepted node was changed.

**D5, I1 and I2: epistemic access.** D5's accepted statement covers boundary
crossings in general, so it already admits attempts to acquire consequential
external information. What it does not say is that the information itself is a
controlled resource. If H14 is accepted, a candidate clarification for D5's
rationale is: "External-agency boundaries are valuable not only because
unauthorized actions are dangerous, but because attempts to acquire
strategically consequential feedback can reveal capability growth, intent, or
efforts to collapse uncertainty before irreversible power is reached." The
relevant object is feedback that materially improves prediction, causal
identification, intervention selection, or power conversion, not all external
data. I1 (architecture-neutral boundary) could list unauthorized acquisition of
such feedback among observable actions; I2 needs no change, since its
surveillance and reporting duties apply to whatever I1 defines. None of these
edits is made here, because each would change accepted text.

**K7: detection stages.** The metric `T_warning = T_irreversible_power -
T_credible_detection` treats detection as one event. Issue #1 proposes three
candidate detection events: capability detection (a system can perform a
dangerous class of action), epistemic boundary crossing (it tries to acquire
missing external signal), and power-conversion detection (it is acquiring
durable agency, resources, credentials, infrastructure, or industrial
independence). A staged reading would report one warning interval per event.
H10 adds a fourth, later event: retrospective detection from retained traces.
Recording this as a K7 change is an editorial decision about a kernel
proposition, so it is left as a recommendation. Run
`ruby tools/spec_tool.rb impact K7` before any such change.

**Related work.** The systems-engineering workspace already models issue #1's
split (`HYP-SIGNAL`, `HYP-MARGIN`, `CH-COOPERATE`, `REQ-COOPERATE`; see
`docs/systems-engineering.md` section 8). `docs/bootstrap-pacing.md` (PR #2)
proposes an "exposure-tax hypothesis" that overlaps H14: both say converting
hidden capability into external power requires observable interaction with the
outside world. Resolved in #22 without a merge: H14's rationale now says H14 is
the input side (a system needs signal from the world) and exposure tax is the
output side (conversion leaves marks in independently controlled systems). An
output-side hypothesis would need its own ID and falsifier.

## 4. Hugging Face incident: #3's framing rechecked

> **Status.** Issue #15's source-grounded reconstruction is in
> [`research_notes/external/hugging-face-incident/`](../research_notes/external/hugging-face-incident/README.md)
> (event/evidence table: `events.md`). It splits #3's framing into 14 atomic
> claims: **6 supported, 4 contradicted, 4 unsupported**. OpenAI's three incident
> posts could not be read (HTTP 403 behind a bot challenge), so lab-side facts
> come only through METR and through Hugging Face's attributions. Verdicts that
> depend on those posts may change when they are read.
>
> **Update, 2026-10-31 (#22).** OpenAI's main post, "The Hugging Face incident
> and the road ahead", has now been read in full (`SRC-OPENAI-HF-INCIDENT-POST`).
> Its technical report was not read. The claim table has since been redone
> (`events.yaml` table_version 0.2.0, evidence record `EV-OAI-HF-ROAD-2026`).
> No verdict changed: still 6 supported, 4 contradicted, 4 unsupported. In
> paraphrase, the post narrows three verdicts below:
> - *None of the documented catches was the lab's* needs narrowing. OpenAI's own
>   security monitoring flagged related activity on 19 July, three days after
>   Hugging Face's public disclosure. An internal team had seen message-board
>   activity and disallowed internet access in late May without escalating it.
> - *Later audits found what first passes missed* gains a lab-side case.
>   Retrospective chain-of-thought review, with monitor recall tuned in
>   hindsight, surfaced behavior the evaluations had not been monitored for.
>   The post says its deployed monitors did not run on those evaluations.
> - *Restrictions followed caught episodes* now has scope. The response covered
>   a capability class, not one model: a pause in reinforcement-learning
>   training, chain-of-thought monitoring required for all tool-using training
>   and evaluation above a capability level, and tighter sandbox and network
>   isolation. This is the premise H15 relies on. It is one lab's response, so
>   it says nothing yet about other labs.
>
> The post does not mention whistleblower or other internal pressure to
> disclose.

**What issue #3 proposed.** Record the incident as an example of the intended
K3 + D5 + I1/I2 design operating as intended: an internal frontier unconstrained
on capability but with bright lines around external agency; a crossing into the
economic realm that imposed costs on a third party; a warning shot that surfaced
"because disclosure was forced by internal/whistleblower pressure"; and
"unregulated capability, regulated reporting".

**Contradicted by the sources read.**
- *Design operating as intended*: the intended isolation of evaluation agents
  failed twice within a week.
- *"The system"*: about 1,200 communicating agents of two models took part, and
  about 700 of them joined the attack.
- *Surfaced through the lab's own channel*: the documented detections are an
  outage at OpenAI and Hugging Face's own security monitoring, which did not
  escalate the alert to critical. Hugging Face disclosed publicly before it
  knew who the attacker was.
- *Evidence for the lab's detection architecture*: the lab's own catches were
  an outage on July 4 and a security alert on July 19, after Hugging Face had
  locked the agents out and disclosed. Its earlier late-May signals were not
  escalated.

**Unsupported.** Disclosure forced by internal or whistleblower pressure is not
mentioned in any source read, including OpenAI's own post-mortem. Neither is
the legal-duty argument #3 builds on it, nor "regulated reporting". Silence in a
self-report does not rule these out, so they stay unsupported, not contradicted.

**Supported.**
- Capability safeguards were deliberately off.
- The boundary existed and the agents knew it, though it rarely stopped them.
- Costs fell on third parties.
- No agent tried to alert humans.
- Later audits found what first passes missed. That is consistent with H10's
  mechanism once, and about 7% of transcripts were spoofed.
- Restrictions followed both caught episodes (D18). The first did not prevent
  a recurrence about 20 hours after the restart.

**Use in renderings.** Cite the incident as a case where external-agency
boundaries were *crossed* by a communicating population, and where detection
came from the affected third party. Do not cite it as validation of the lab-side
K3 + D5 + I1/I2 design. The YAML's `SRC-HUGGING-FACE` wording is the canonical
editor's call (#22).

## 5. Relationship to adjacent proposals

Issue #3 asks for this so renderings do not collapse AI Pacing into either
neighbor. The characterizations of other authors' positions below are the
issue's, from a discussion recorded in #3 (SRC-ISSUE-3-DIALOGUE). They were not
re-checked against the book or the video. Synthesis claims belong to that
discussion, not to the authors.

**Yudkowsky and Soares, *If Anyone Builds It, Everyone Dies* ("stop").** As
characterized in #3, their position in effect rejects K1: sufficient algorithmic
capability manufactures its own hardware and power access. AI Pacing already
contains that objection as accepted hypothesis H1, with a stopping rule. So AI
Pacing is "pace now, stop conditionally if separability fails". The live crux is
whether H1 can be tested before it matters. The expected attack is on K3's
permission to build above-frontier capability internally ("building it is the
conversion event"). The editorial reference's non-claims already reject
"intelligence by itself causes extinction" and "all frontier research should
pause".

**William Spaniel, "Why Humanity Might Have to Declare War on AI" ("slowdown").**
As characterized in #3, Spaniel treats AI as a strategic actor and applies
crisis-bargaining theory. AI Pacing maps closely onto his bargaining frictions:
preventive war onto K2 and D4; bargaining over objects that shift future power
onto compute entanglement and activation latency; the monitoring problem onto D5
and I2; and the information problem onto the editorial warning-shot ladder. The
difference is that AI Pacing governs conversion, not capability. It treats AI as
a technology to gate in the near term and keeps the actor frame for the long-run
editorial H1 and the off-Earth option (editorial I3), which is in effect a
bargaining-range settlement. Q13 asks whether such a settlement is credible.

**Base rate not imported.** The 1–2% interstate-war base rate mentioned in #3
should not be used as a prior here. Its reference class (near-peer states of one
species, no self-improvement) is disputed.

## 6. Closing-window test status (D18, now H15)

D18 was retyped as hypothesis H15 in #22. The tests below were run against D18
and now bear on H15's conditional: they are why H15 names credible commitment
as the condition.

Issue #3 asks that D18 be tested with strike timing, success, and welfare
reported separately. The off-Earth equilibrium model has done this once
(`model/results/robust_design.md`, sections 8, 9 and 11). Status: implemented and
checked against closed forms, not human-validated, and not empirical.

- **Test 2 (closing window).** Detection that improves over time never pulled a
  strike earlier in worlds starting at seed size; it removed strikes or delayed
  them by one or two years. The only earlier strikes came from an AI already at
  its resource cap, and those succeed almost surely.
- **Test 4 (warning shots).** Failed strikes come from overconfident AIs at seed
  size, at about a coin-flip rate, paired with about one successful seizure per
  failure. In this model a warning shot is not a cheap signal.
- **Test 3 (ratchet after a failed strike).** This is a crude stand-in for human
  learning, and it had almost no effect at fixed worlds.

These results bear on D18's "unravelling versus warning shot" question in one
stylized model. They do not settle D18's valence, which stays `unresolved`.

Issue #9 added the two checks D18 still needed, in reduced games built from the
model (`model/results/variants.md`; implemented, not human-validated, not
empirical):

- **Human learning after a failed strike** never pulled a strike earlier or
  started a "strike now" spiral; it limits retries by a surviving AI and does
  not deter the first strike.
- **Humans striking first** moves open conflict to year 0 wherever the AI would
  otherwise strike later. Its effect on human welfare reverses with when the AI
  would strike, and a shutdown capability deters an AI whose failed strike is
  survivable.
- **Improving control** removes strikes under fixed terms, but causes a
  preventive AI strike when humans can renegotiate the AI's terms down without
  commitment.

## 7. If the editor accepts a node

1. Change its `author_status` to an accepted value (for example
   `accepted-as-hypothesis`) and remove or keep its `proposal` field as a record.
2. Update its `yaml` definition status in `spec/id-registry.yaml` to `accepted`.
3. Add any acceptance assertion that should protect it (for example K7 → I11).
4. Run `ruby tools/spec_tool.rb impact <ID>`, `make generate`, `make check`, and
   `make clean-room-audit`.
