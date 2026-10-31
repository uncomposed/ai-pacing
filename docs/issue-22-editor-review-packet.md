# Issue 22 editor-review packet: the eight proposed nodes

[[ai gen]] Drafted 2026-10-30 by Claude for the canonical editor. The editor's decisions, made on 2026-10-31, are in the last section; the blocks above are the packet as reviewed. The packet itself does not change the YAML. Every recommendation is a suggestion for Cole to accept, reject or revise. The stopping rule in issue 22 still applies: leave a node proposed rather than accept it to clear the list.

How to read this. One block per node. Each block has a plain-language summary, what depends on it, what the tooling will refuse, what the repo's own evidence says, and one recommendation with one reason. Answer by node number if dictating, for example "1 yes, 4 revise, 6 leave".

## Summary table

| # | node | kind | recommendation | one reason |
|---|---|---|---|---|
| 1 | H10 retrospective audit | hypothesis | **revise, then accept as hypothesis** | Keystone: four other nodes cannot be accepted until this one is, and its detection half has one supporting case while its deterrence half has none |
| 2 | H14 external-signal dependence | hypothesis | **accept as hypothesis**, with one wording line | It has a falsifier, needed evidence and a stopping rule, and it names the reason separability might survive that H1 does not |
| 3 | Q13 cooperative autonomy path | open question | **accept** (status `unresolved`) | It is the canonical home the whole off-Earth program lacks, and the model has already sharpened two of its seven sub-questions |
| 4 | I11 do not train against the audit signal | implementation | **accept**, after dropping H10 from its `implements` list | It stands on its own as known practice and does not need retrospective audit to be true |
| 5 | Q11 auditor independence | open question | **accept** once H10 is accepted, or drop the H10 relation and accept now | Cheap, real, and already named as an optimistic assumption inside H10 |
| 6 | D18 closing-window dynamics | derived | **revise: retype as a hypothesis and leave proposed** | A derived mechanism whose direction is unknown is not derived from anything; the model has narrowed it to a testable conditional |
| 7 | D19 model sharing compresses gaps | derived | **revise: retype as a hypothesis, drop I3 from its grounding** | It is an empirical claim with four listed tensions, and a replaceable implementation choice should not ground a derived mechanism |
| 8 | Q12 inter-lab convergence | open question | **accept** once D19 is settled, or drop the D19 relation and accept now | Real question, and its content survives whatever happens to D19 |

**Order matters.** The checker refuses an accepted node whose `derived_from`, `supports`, `implements` or `relates_to` names a proposed node. H10 is named by D18, I11 and Q11. D19 is named by Q12. So decide H10 first, then D18, I11 and Q11; decide D19 before Q12. H14 and Q13 are independent and can go in any order.

---

## 1. H10: Retrospective audit makes concealment a losing long-run strategy

**Plain language.** Keep tamper-evident records of what frontier systems did, including reasoning traces. Detectors improve over time while the record stays fixed. So a system that hid an excursion from today's monitors still has to survive every future audit. Two claims are bundled: later audits will find things (detection), and a system that values its goals will be deterred because being caught tightens the regime for everyone like it (deterrence).

**What depends on it.** Conditions K7 and D5. Grounds D18. Named in I11's `implements` and Q11's `relates_to`. Downstream of K7 and D5 by the impact tool: D4, I1, I2, I4, I5.

**What the repo's evidence says.**
- Hugging Face reconstruction (issue 15): later audits found what first passes missed, and about 7 percent of transcripts were spoofed. One case, fitted after the fact, supports the detection half once.
- Pact model test 3 (ratchet after a failed strike, a crude stand-in for human learning) had almost no effect. The deterrence half has no support in the model.
- Counter-evidence to record under `evidence_needed`: the chain-of-thought concealment picture is mixed. Ciphers cost task performance, steganography much less, and at least one 2026 system card reports high chain-of-thought controllability with no stated accuracy cost. That bears directly on the falsifier "systems learn to produce traces that pass future-style audits". These sources are in a session memory note, not yet in `evidence/records.yaml`, so they would need to be read and recorded before being cited.

**Concern.** The `conditions` edges to K7 and D5 read as if K7 fails when H10 fails. H1 is a necessary condition for the kernel. H10 is one contributor to warning time. The stopping rule already says "do not count retrospective audit as extending warning time", which is the right strength. Say so in the rationale so the edge is not over-read.

**Recommendation: revise, then accept as hypothesis.** Trim the rationale's deterrence sentence to "may deter", add the chain-of-thought controllability evidence to `evidence_needed` as evidence against, and state in the rationale that the edge to K7 is contributory. Reason: it is the keystone for four other nodes and its detection half has one real supporting case, while the deterrence half is speculation that the model did not confirm.

---

## 2. H14: External-signal dependence preserves some A/P separation

**Plain language.** Being very smart is not enough to act in the world. For important classes of consequential action, a system still needs information, experiments or feedback from outside before it can convert capability into power reliably. That need is a reason the separation between capability and power might persist, and a place where a system has to show itself.

**What depends on it.** Conditions K1, K2, K3, K7 and D5. Largest impact set of the eight: everything downstream of the kernel.

**What the repo's evidence says.** None yet. The sources are an 80,000 Hours episode that was not re-read and a Spoken Margins session recorded only in issue 1. The systems workspace models the same split as `HYP-SIGNAL` and `HYP-MARGIN`. The node is honest about all of this.

**Overlap to reconcile.** The exposure-tax hypothesis in `docs/bootstrap-pacing.md` section 7 says converting hidden capability into power requires actions with observable effects in independently controlled human systems. H14 is the input side (the system needs signal from the world). Exposure tax is the output side (the system leaves marks on the world). Same underlying bet, two faces. One sentence in H14's rationale naming that distinction resolves the issue 22 checklist item without a merge. If Cole later wants the output side in the spec, it is a separate hypothesis with its own falsifier, at the next free H ID.

**Concern.** Same as H10: `conditions` to five accepted nodes overstates. H14 is a reason separability might hold, not a requirement for K1. The stopping rule is already phrased as "do not count as a contributor", which is right.

**Recommendation: accept as hypothesis**, after adding the one-line input-versus-output distinction from the exposure-tax hypothesis and the contributory wording. Reason: it meets every field rule, it names a mechanism H1 leaves implicit, and its source caveats are already written down.

---

## 3. Q13: Can a credible cooperative autonomy path reduce incentives for AI defection?

**Plain language.** Could a staged, verifiable path toward more AI autonomy make cooperation better than a grab for power, without a commitment problem that wrecks it or a transfer of capability that comes too early? Seven sub-questions are kept verbatim from issue 1.

**What depends on it.** Nothing. `relates_to` K1, K2, K3, K7, D5. Accepting an open question commits the spec to the question, not to any answer.

**What the repo's evidence says.** This is the question the entire off-Earth program is working on, and the model has sharpened two sub-questions:
- Sub-question 2, "can humanity credibly commit to future autonomy": the bargaining variant found that when humans can renegotiate the AI's terms down without commitment, the AI strikes pre-emptively. The preservation sweep on the draft paper branch found amnesty has to be certain (credibility exactly 1) to hold.
- Sub-question 5, "is physical separation useful because it reduces dependency, or is decoupling the variable": the model's answer so far is that dismantling fabs (decoupling the threat) carries the result, and Earth's value as a prize barely moves it.

**Why this one matters most.** Today the off-Earth pact has no canonical home. It appears in the YAML only as sources and inside D18's model-evidence text. Accepting Q13 puts the question in canon and leaves the pact as research until a D or H node is proposed to answer it. That is the clean way to connect the two halves of the repo without promoting unvalidated model results.

**Recommendation: accept** (set `author_status: unresolved`), and add a short `model_evidence` field pointing at the two findings above, labelled implemented and verified, not empirical. Reason: it is the canonical anchor the off-Earth work needs, and the evidence to cite already exists in the repo.

---

## 4. I11: Do not optimize against the audit signal

**Plain language.** Never use the detectors, interpretability probes or audit results as a training or selection signal for the models they audit. Keep a held-out audit channel. Otherwise you train models to look clean rather than be clean.

**What depends on it.** Nothing downstream. The node's own `implements` list names K7, D5 and H10. The relations section has only D5 to I11. The issue asked for an acceptance assertion `path_exists` from K7 to I11.

**What the repo's evidence says.** No repo evidence, but this is the one proposed node with a known published basis outside the repo: a 2025 OpenAI paper on monitoring reasoning models found that optimizing chain of thought against a monitor produced obfuscated reasoning, and recommended against it. That paper should be read and recorded as a source before it is cited.

**Blocker.** `implements: [K7, D5, H10]` names a proposed node, so the checker will refuse acceptance until H10 is accepted or H10 is removed from the list. The rationale's claim "without this rule H10 degrades by construction" is true but does not make I11 depend on H10. The rule is good whether or not retrospective audit works.

**Recommendation: accept** as a replaceable implementation, after removing H10 from `implements`, adding K7 to the relations section, adding the K7 to I11 path assertion, and recording the OpenAI monitoring paper as a source. Reason: it is established practice that stands without H10, and it is the cheapest of the eight to defend.

---

## 5. Q11: How independent must auditors be to resist correlated misalignment?

**Plain language.** Future auditors are themselves models. If they share training, architecture or a lab with what they audit, they may share its blind spots or its goals. How much diversity makes collusion implausible, and can rival review supply it?

**What depends on it.** Nothing. `relates_to` D2, H2 (accepted) and H10 (proposed).

**What the repo's evidence says.** None. H10 already lists auditor independence as an optimistic assumption, so the question is recognized inside the hypothesis it qualifies.

**Blocker.** The H10 relation blocks acceptance until H10 is accepted. Dropping the relation would be a loss of information; waiting is better.

**Recommendation: accept** (status `unresolved`) in the same change as H10. Reason: the question is real, cheap to hold open, and already assumed away inside H10.

---

## 6. D18: Closing-window dynamics may pull strikes earlier (risk to test)

**Plain language.** Every caught excursion tightens surveillance on every system. A misaligned system watching that happen sees its prospects worsen and may strike sooner. Whether that is good (early strikes fail and act as warning shots) or bad (early strikes sometimes succeed) is unresolved. The off-Earth pact adds a twist: human states also lose relative power over time, so the same pressure can push humans toward preventive action.

**What depends on it.** Nothing. Derived from K7, D5 and H10 (proposed). `valence: unresolved`.

**What the repo's evidence says.** The most-tested node of the eight, all in the pact model and its reduced variants, all implemented and checked against closed forms, none empirical:
- Test 2: detection improving over time never pulled a strike earlier for an AI starting at seed size. It removed strikes or delayed them a year or two. The only earlier strikes came from an AI already at its resource cap, and those succeed almost surely.
- Test 4: failed strikes come from overconfident AIs at about coin-flip odds, paired with about one successful seizure per failure. A warning shot is not cheap in this model.
- Issue 9 variants: human learning after a failed strike never pulled a strike earlier. Humans striking first moves open conflict to year 0 wherever the AI would otherwise strike later. Improving control removes strikes under fixed terms but causes a preventive AI strike when humans can renegotiate the AI's terms down without commitment.

So in one stylized model the closing window is not an unravelling risk on its own. It becomes one when humans can tighten terms without commitment. That is a conditional, and it is testable.

**Concern about the type.** The typed layers define D as "mechanisms logically or strategically derived from kernel propositions". A node whose direction is unknown cannot be derived. It reads as a hypothesis: "Closing-window pressure pulls strikes earlier only when humans can tighten terms on a cooperating AI without a credible commitment." That has a falsifier (a model or case where the window pulls strikes earlier under committed terms, or fails to under uncommitted ones), evidence needed (a second model not built by this project; incident data on restriction ladders) and a stopping rule.

**Recommendation: revise and leave proposed.** A D ID cannot hold a hypothesis, so either reserve the next free H ID for the retyped version and retire D18 in the registry, or keep D18 as is and leave it proposed. Do not accept it as a derived mechanism. Reason: the evidence already in hand says the mechanism is conditional, and a conditional with a falsifier is a hypothesis, not a derived mechanism.

---

## 7. D19: Review-based model sharing compresses inter-lab capability gaps

**Plain language.** Because above-frontier release means letting rivals attack your actual model, rivals get controlled exposure to frontier systems. That tends to narrow the gap between participating labs, which makes a decisive lead by any one lab, and so a singleton, less likely. A second reason for rival review beyond safety, and a reason trailing labs might join.

**What depends on it.** Nothing. Derived from K4, D2 and I3. Named in Q12's `relates_to`. Four tensions and two non-claims are recorded in the node.

**What the repo's evidence says.** None. The node's own tensions are the strongest content: compression of capability versus compression of method diversity; domestic versus international compression; aggregate acceleration; leader incentives. Each is a way the claim could be false.

**Concerns.**
- "Tends to compress" is an empirical claim about how labs respond to access. It needs a falsifier, not a derivation. The tensions list already reads like `evidence_needed`.
- `derived_from` includes I3, a replaceable implementation choice. If I3 is swapped for another way to stake access, D19 should not fall. A derived mechanism should rest on K and D nodes only.
- H2 (accepted) already carries the anti-concentration bet as a hypothesis with a stopping rule. D19 may be a sharper restatement of H2's upside, in which case it belongs as a note on H2 rather than a new node.

**Recommendation: revise.** Either fold the singleton-prevention point into H2's rationale and reject D19, or reserve the next free H ID, restate it as a hypothesis with a falsifier taken from its own tensions, and drop I3 from the grounding. Reason: it is an empirical claim with four listed ways to fail, and an implementation choice should not ground a derived mechanism.

---

## 8. Q12: What inter-lab and international convergence minimizes singleton and correlated-failure risk?

**Plain language.** How much should labs and states converge in capability? Too little and one of them gets a decisive lead. Too much, by sharing methods, and they all fail the same way. Where is the balance?

**What depends on it.** Nothing. `relates_to` D19 (proposed), Q11 (proposed), H2 and D6 (accepted).

**What the repo's evidence says.** None. The question survives whatever happens to D19: the tension between a decisive lead and correlated failure is real on its own.

**Blocker.** The D19 and Q11 relations block acceptance until both are settled. If D19 is rejected or retyped, update the relation to the replacement or remove it.

**Recommendation: accept** (status `unresolved`) once D19 and Q11 are settled, updating the relations to match. Reason: the question is real and cheap to hold open, and its content does not depend on D19 being true.

---

## The other items on the issue 22 checklist

1. **Fresh IDs** (H6 to H14, Q5 to Q13, report H10 to H11). The registry records the renumbering with reasons and `make check` passes. Nothing for the editor to do except confirm. If D18 or D19 are retyped as hypotheses, the next free IDs are H15 and H16; run `ruby tools/spec_tool.rb next-id H` and add registry entries before use.
2. **Same-proposition judgments** (YAML K1 to K7, Q1, Q2 treated as the same as the editorial Markdown entries). I did not compare the two texts word by word. The `make clean-room-audit` output is the input for that decision, and it is diagnostic only.
3. **Locator and date for SRC-ISSUE-1-SPOKEN-MARGINS.** Only Cole has the Spoken Margins session reference. One line in the YAML source entry.
4. **Reconcile H14 with the exposure-tax hypothesis.** Covered in block 2: one sentence on input side versus output side, no merge.
5. **Issue form "unreserved" option.** Keep it. A proposer without write access cannot bump `next_free` in the registry. The maintainer reserves the ID when the proposal is recorded, which is what happened for issues 1 and 3.
6. **Hugging Face worked example.** Issue 15 landed and `docs/proposed-extensions.md` section 4 already reflects it: six claims supported, four contradicted, four unsupported, with OpenAI's own posts still unread. The remaining editorial decision is the wording of `SRC-HUGGING-FACE` in the YAML, whose contribution line says precursor incidents "can function as warning shots". Detection came from the victim, not the lab, and pact-model test 4 found warning shots are not cheap. A narrower wording would be "evidence that internal research can confer external agency and that boundary crossings by a communicating population can be detected by affected third parties". That edits an accepted source record, so it is the editor's call.

## If Cole accepts any node

From `docs/proposed-extensions.md` section 7, for each accepted node: change `author_status`, update the registry definition status to `accepted`, add any acceptance assertion (K7 to I11 for block 4), then `make generate`, `make check` and `make clean-room-audit`. Commit the regenerated views with the spec change. Do all of this on a branch, one PR, with `Closes #22` only if every box is met.

## What this packet does not do

It does not change the YAML, the registry or any doc. It does not re-read the podcast, video or book that the proposed nodes cite. It does not check the editorial Markdown against the YAML for the same-proposition item. Every "what the evidence says" line restates results that are implemented and verified in the repo, none of which is empirical validation.

## Editor decisions, 2026-10-31

[[ai gen]] Paraphrased by Claude from Cole's listener interjections in a Spoken Margins review of this packet on 2026-10-31, and his answers to follow-up questions in the same session. Nothing from the session is quoted. Where Cole did not comment, he approved the default named below.

| # | node | decision | applied as |
|---|---|---|---|
| 1 | H10 | agreed with the recommendation | `accepted-as-hypothesis`; deterrence trimmed to "may deter"; contributory edges stated; chain-of-thought controllability recorded as evidence against, after reading the sources (`SRC-GPT-6-ASTRA-CARD`, `SRC-STICKLAND-KORBAK-2025`) |
| 2 | H14 | agreed | `accepted-as-hypothesis`; input-side versus output-side sentence on exposure tax; contributory edges stated |
| 3 | Q13 | agreed | `unresolved`, with `model_evidence` labelled implemented and not empirical |
| 4 | I11 | agreed | `accepted-as-option`; H10 dropped from `implements`; K7 → I11 relation and AT-006 assertion; `SRC-BAKER-2025-COT-MONITORING` recorded after reading its abstract |
| 5 | Q11 | no interjection; default approved | `unresolved`, accepted with H10 |
| 6 | D18 | agreed to revise and leave proposed; default approved for how | retyped as proposed hypothesis H15; D18 `withdrawn` in the registry (a new status) |
| 7 | D19 | "use the cleanest way to model it"; default approved | folded into H2's rationale, tensions and non-claims; D19 `withdrawn` |
| 8 | Q12 | agreed | `unresolved`; relation to D19 removed |

Checklist items:

1. Fresh IDs: confirmed, no change.
2. Same-proposition judgments: **not reviewed.** This box stays open.
3. Spoken Margins locator: added from the session file's own title and timestamp. No content was copied.
4. H14 and exposure tax: resolved as in block 2.
5. The "unreserved" option in the issue form: kept.
6. Hugging Face: Cole asked whether the incident shows agents reaching outside the lab, being detected, and surveillance tightening as a result. OpenAI's own post, now read, supports the detection and the tightening. The tightening was class-wide at one lab: an RL pause and chain-of-thought monitoring required above a capability level. Detection came first from the affected third party. The case is mainly evidence for the output side (exposure tax and H10's detection half), not for H14's input side. `SRC-HUGGING-FACE` now uses the narrower wording, and the post is recorded as `SRC-OPENAI-HF-INCIDENT-POST`.

Status: `implemented` and `verified` (`make check` and `make clean-room-audit` pass). Not `human_validated`.

