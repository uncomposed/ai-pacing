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
- The evaluation is the moment of highest risk: a model that expects to fail
  has its strongest reason to act during it. Run it under the strongest
  available control, before any internal use. The kept outer key also lowers
  that incentive.

## Known weaknesses

- **Selection against the gate.** Retraining until some checkpoint passes is
  optimization. Record the attempt counts, rotate the plants, and have parties
  other than the lab verify passes. The relation to I11 ("do not optimize
  against the audit signal") is open: I11 forbids selecting *audited* models
  on audit results; this gate selects *auditors* on their findings.
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
