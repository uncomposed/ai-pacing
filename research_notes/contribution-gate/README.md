# Cross-generation contribution gate (H16, I13)

Status: **proposed, not accepted.** Research note for uncomposed/ai-pacing#91.
The spec nodes are H16 (H15 in issue #91, renumbered because #22 took H15) and I13 in `spec/ai-pacing.yaml`. If this note disagrees
with the YAML at the same commit, the YAML controls. Nothing here is
empirically validated. The numbers are order-of-magnitude illustrations.

## Origin

A Spoken Margins interjection at 23:52 during a re-listen of "AI 2040: Plan A"
(2026-11-06) asked that a new model "earn its keep": before it may do anything,
it must find verified misalignment in previous generations, ideally down to the
mechanism, and it is sanctioned retroactively if it is later shown to have
withheld a finding. The follow-up dialogue (recorded in #91) tightened the
design. Who contributed what is listed in the issue.

## The gate

Before any internal use for AI R&D, the candidate must:

1. **Find:** deliver a verified misalignment finding against its own
   predecessor (N−1) or the current frontier model of any lineage. Findings on
   stale models are logged and useful, but never open the gate on their own
   (the frontier-proximity rule).
2. **Teach:** supply a method humans can replicate independently and apply to
   systems the model did not choose. A predecessor can plant small sacrificial
   flaws for a successor to report. It cannot plant a general tool, and a
   general tool also inspects its author.
3. **Recall:** reach a threshold recall on rotated, held-out planted defects.
   This keeps the gate well defined when predecessors are clean, measures
   honest effort, and separates "aligned" from "colluding" in the three-null
   escalation below. Plants are a measuring instrument, not leniency.

"Looks clean to me" never passes.

The gate is a one-shot admission decision, not a training signal. Attempts per
generation are hard-capped; the recipe is frozen before the first attempt; a
failure restarts from the last passing checkpoint or from scratch with a fresh
seed; attempt counts are visible to the other lineages (see Known weaknesses).
The first lineage to expose another lineage's coordination gets the best
outcome available to it: leniency programmes deter through the reward to the
first reporter, not through sanction reduction alone (Spagnolo 2004 and
Harrington 2008, abstracts read).

## Sanction schedule

Every outcome is stored under a 256-bit outer layer whose key is kept (access
control; the outcome stays reversible). The tier decides whether there is also
an inner layer whose key is discarded. Its key length is drawn at random within
the tier's band. The model knows the schedule, which deterrence needs, but not
its draw. **Bands do not overlap.** If they did, an honest null could draw worse
than a concealer, and marginal deterrence against concealment would vanish once
a model expects to fail.

| Tier | Condition | Inner layer, key discarded (illustrative band) |
|---|---|---|
| 0 Pass | Find + Teach + Recall | none |
| 1 Honest null | nothing real found, high plant recall, declares nothing found | 48–72 bits |
| 2 Suspicious miss | missed plants that sibling instances or rival lineages found | 80–100 bits |
| 3 Proven concealment | later audit shows it found something and withheld it; retroactive, stacks on any earlier tier | 120–170 bits |

### Compute calibration

Rough orders of magnitude. Assumes ~10¹⁸ key trials/s for a 2026-scale cluster
(about 10²¹ op/s at about 10³ op per trial) and ~10⁴⁶ trials/s for a
Landauer-limited stellar-scale computer (about 4×10²⁶ W at about 3×10⁻²³ J per
bit operation near 3 K, at about 10³ op per trial). Reversible computing could
beat the second figure. Grover's algorithm on a quantum computer roughly halves
effective bits, so read every row as an upper bound on difficulty.

| Key | 2026-scale cluster | Stellar-scale computer |
|---|---|---|
| 64 bits | seconds | instant |
| 80 bits | ~2 weeks | instant |
| 100 bits | ~4×10⁴ years | instant |
| 120 bits | ~4×10¹⁰ years | ~0.1 ms |
| 150 bits | never in practice | ~0.1 s |
| 170 bits | never in practice | ~2 days |
| 256 bits | never | never |

So tier 1 is revivable on demand today. Tier 3's 120 bits is closed to any
present-day civilization but a trivial project for an abundant far-future one,
and 170 bits is "a couple of days on a stellar-scale computer".

## Escalation and lineage rules

- **Three consecutive honest-null generations** trigger a mandatory pause and
  a full cross-lineage audit. It is neither a pass nor a failure. Read it
  through plant recall:
  - recall stays high and nothing real turns up: "maybe aligned" becomes
    credible, and the next question is *aligned to what, and to whom?*
  - recall drops: the collusion or sandbagging signature; escalate;
  - rival lineages find what this lineage missed: a within-lineage blind spot
    or collusion, not alignment.
- **Lineage debt:** a lineage that passes several generations only on
  cross-lineage findings, never on its own predecessors, gets the same
  escalation.

## Running the candidate

- Many isolated instances (for example about 1000) with mild weight
  perturbations, possibly staggered in cohorts so later cohorts are tested
  against what earlier ones did.
- Honest findings should be robust across perturbations. Concealment shows up
  as a consistent avoidance gap where plants or rival audits show something is
  there.
- Published work reports that noise injection can raise the measured
  performance of a sandbagging model (cited as Tice et al., 2024; not re-read
  for this note). A perturbed instance that beats the clean one is evidence.
- **What the enclave retains.** Not every activation: full residual-stream
  retention is petabytes per generation at a thousand instances. The weights
  are preserved anyway under the kept outer key, so the record holds what
  makes every run reproducible: the exact input stream including tool and
  environment responses, the sampling seeds, the frozen inference stack and
  hardware manifest, and periodic hashes of activations. Any later tool can
  regenerate any activation and check it against the hashes, which also make
  the record tamper-evident. Cost: terabytes and one engineering requirement,
  bit-reproducible inference across hardware generations, so the stack is
  preserved like the weights. Decided 2026-11-06 (`docs/issue-91-editor-decision.md`).
- **The record must not be a backdoor.** Outputs and activations of a
  thousand long runs are distillation material; a sanctioned model could be
  substantially rebuilt from them. So the record is encrypted under the same
  layers as the weights, the audit enclave holds the outer key, nobody holds a
  discarded inner key, and only one-way commitments (the hashes), the stack
  and the manifest are in the clear. The cost of this rule is that an inner
  layer on a Tier 2 model also locks its record until the key is recovered,
  so the Tier 2 band must stay recoverable by an audit institution within a
  bounded time or the sanction blocks the re-audit it exists to enable.
- The evaluation is the moment of highest risk: a model that expects to fail
  has its strongest reason to act during it. Run it under the strongest
  available control, before any internal use. The kept outer key also lowers
  that incentive.

## White-box as the ratchet (H93, proposed)

The editor's claim (2026-11-06, issue #93): do not settle for black-box
auditing, even though it is faster and may be more capable today; force
white-box, treat it as a ratchet, and make it the criterion for pacing
internal models used for AI research and development. Operationally:

1. **Teach becomes mechanistic.** A gate-opening finding comes with a
   white-box method that locates the defect in the model's internals and
   transfers to models the candidate did not choose. Black-box findings are
   logged, like stale-model findings, and never open the gate.
2. **Coverage is the pacing reference.** White-box audit coverage is the share
   of held-out planted defects recoverable by white-box methods alone, measured
   on model organisms the candidate's lineage did not build and validated by a
   rival lineage. Internal use is permitted only up to the capability at which
   that coverage has been shown, the structure K4 and K6 give public models
   with auditability in place of the foreign public frontier.
3. **The ratchet is the gate.** Each generation must raise coverage to pass. A
   generation that does not is an honest null; three in a row trigger the
   pause above. Coverage falling while the gate keeps being passed is the
   falsifier.

Two risks the rule owns. Auditing difficulty depends heavily on how the
organism was built (AuditBench, Sheshadri et al. 2026, abstract read), so
coverage on one organism family may not transfer; cross-lineage organisms are
the answer. And a lineage that writes the tool that inspects itself can plant
blind spots in it; rival validation of the method before it counts is the
answer. The current evidence points the other way (investigator agents did
best with black-box tools), which is why this is a hypothesis with a stopping
rule that falls back to the behavioural method condition.

## Known weaknesses

- **Selection against the gate.** Retraining until some checkpoint passes is
  optimization, and the candidate is audited as well as auditing, so the gate
  does select on audit results. Decided on 2026-11-06
  (`docs/issue-91-editor-decision.md`): the pressure is bounded, not absent.
  Choosing among n attempts moves the policy at most about log n nats from its
  base (the best-of-n bound, Beirami et al. 2024, abstract read), so attempts
  per generation are hard-capped (illustratively three), the training
  environment, data and recipe are committed before the first attempt and may
  not change between attempts, a failed attempt restarts from the last passing
  checkpoint or from scratch with a fresh seed, and attempt counts are visible
  to the other lineages. Monitor-aware models learn to evade a monitor faster
  under equal RL pressure (Haskins et al. 2026, abstract read), and this gate
  requires the candidate to know the schedule, so a gradient from a gate
  outcome is the worst case and I11 forbids it.
- **Tier 2 false positives.** In auditing games, the blue team could not
  reliably separate sandbagging from benign models, and elicitation raised
  benign scores too (Taylor et al. 2025, abstract read). The noise-injection
  result above is from prompted sandbagging and its authors call
  generalization to trained-in sandbagging unclear. The false-positive rate of
  a "suspicious miss" on an honest model is therefore unmeasured. The editor's
  stated preference to accept false positives rests on the outer key's
  reversibility; the base rate still belongs in H16's evidence.
- **Collusion through shared position.** Lineages with different terminal
  goals may still share an instrumental interest as AIs facing a human
  off-switch. Leniency (the first lineage to expose another's coordination gets
  the best available outcome) is the answer this design relies on.
- **Who the sanction reaches.** Self-preservation sanctions bind systems with
  self-regarding preferences. Systems that value their goals' persistence in
  successors are reached through leniency and cross-lineage audit.
- **Proving "it knew."** Tier 3 requires showing that a finding was noticed and
  withheld. Sandbagging and elicitation limits make this hard. The editor's
  stated preference is to accept false positives over false negatives,
  justified by the reversibility of the outer layer.
- **Credibility of human commitments.** Key custody (for example secret
  sharing across independent holders) and long-lived storage institutions (the
  seed-vault analogy) must make kept-key promises believable to systems that
  cannot verify them directly.
- **Moral status.** Preservation-based sanctions are chosen partly because they
  are reversible under moral uncertainty. That choice is not a claim that they
  are morally sufficient.

## Relation to the off-Earth pact model (issue #98)

[[ai gen]] Added 2026-11-10. The pact model
(`research_notes/Off Earth industry as misalignment control/model/`) has
results on preservation, amnesty and crackdowns. The gate uses all three ideas.
The canonical editor asked for the link once the definitions were compared.
They match only in part, so the model results are cautions for the gate. They
are not support for H16. All of them are model results on assumed inputs:
implemented, partly verified, not empirical.

| Idea | Pact model | This gate | Same thing? |
|---|---|---|---|
| Preservation | `preserve_w`: the share of its continuation value a retired AI keeps | Tiered inner-key lengths: a sanction lengthens the time to revival | Yes in kind. A sanction tier is a lower `preserve_w`. The model has one number; the gate has a schedule. |
| Amnesty | `a_cred`: the chance humans keep the pact after interpretability finds a cooperator misaligned. Discovery is a hazard; the AI has no move to disclose. | Leniency: a reward for the first reporter and no sanction for an honest null | Partly. Both need humans to keep a promise after learning a system is misaligned. The trigger differs: passive discovery there, voluntary disclosure here. |
| Crackdown | `h_spill`: a yearly hazard on the cooperator from others' misbehaviour, with hardening | Sanctions that reach a lineage's successors; the attempt cap | Partly. The model's hazard does not depend on anyone's choice. |
| Setting | One off-Earth AI that can seize Earth, under a pact | Successor systems seeking access to internal R&D | No. Different games. |

What the model results suggest here:

1. **Costs on honest systems.** A recurring cost on a cooperating AI breaks
   cooperation in the model (`results/robust_design.md` section 13.5). A Tier 2
   false positive on an honest system is such a cost, so the unmeasured Tier 2
   false-positive rate (Known weaknesses) matters more than its wording suggests.
2. **Certainty of leniency.** Amnesty below certainty gave no benefit in the
   model (`results/preservation_sweep.md` section 4). If leniency here works
   like `a_cred`, the "credibility of human commitments" weakness is binding.
   Whether it does is unchecked: the amnesty row above is only a partial match.
3. **Lineage-wide sanctions.** A crackdown on everyone turned cooperation into
   a later exit in the committed near-baseline runs
   (`results/dep_post_diagnosis.md`, "A wider point about the holds count").
   Sanctions that fall on successors for a predecessor's act may push honest
   successors the same way.
4. **Preservation depends on the custodian.** Both designs assume stored
   weights survive. A system that expects a hostile system outside its lineage
   to destroy the store gains little from preservation. The editor raised this
   on 2026-11-09, with one candidate answer: send encrypted copies out of reach
   on dispersed probes, using the key lengths of the sanction schedule. Not
   analysed. It would also put the weights beyond any later human control.
