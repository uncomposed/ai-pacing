# Editorial reference status

`AI_Pacing_Canonical_Spec_v0.1.md` is the editorial reference the author
supplied on 2026-08-29. On 2026-11-06 it was frozen at that state. It is not
updated, it does not grow with the YAML, and where the two differ the YAML
controls (`CANONICALITY.md`). This note records the divergence as of the
integration of PRs #88, #90 and #92, so that nobody has to re-derive it from
`make clean-room-audit`, and says what each difference means.

Why freeze rather than reconcile: the reference is the only record of the
proposal in the author's own words before the YAML existed, so it is the
independent check the clean-room test needs. Editing it to match the YAML would
destroy that check. Renumbering the YAML to match it would touch sixteen
accepted IDs cited across the model, the research notes and the issues.
Generating a fresh editorial rendering from the YAML is already done
(`generated/minimal-reconstruction.md`) and is a projection, not a reference.

## Counts (`make clean-room-audit`, 2026-11-06)

| Measure | Count |
|---|---:|
| Nodes in the reference | 43 |
| Accepted nodes in the YAML | 35 |
| In the reference, no YAML node | 18 |
| In the YAML, not in the reference | 10 |
| Shared IDs with different titles | 24 |

## 1. In the reference, no YAML node: a backlog of candidates

These are propositions in the author's words that have never been reviewed
into the YAML. Each is a candidate for a spec-proposal issue. The ID in the
reference is **not** reserved for it in the YAML namespace: when one is
proposed, it takes the kind letter plus its proposal issue number, and the
registry's `renumbering` list records the reference's number.

| Reference ID | Title in the reference |
|---|---|
| D7 | Warning-shot ladder |
| D8 | Prefer learning before building maximum physical dry tinder |
| D9 | Compute stock and compute entanglement are different |
| D10 | Physical activation latency |
| D11 | Industrial dry tinder matters separately from GPUs |
| D12 | Preserve multiple human vetoes |
| D13 | Begin with control assurance, not general research licensing |
| D14 | Incremental domestic sequence |
| D15 | Strategic-compute licensing creates a fiscal control point |
| D16 | Cooperation should be divisible |
| D17 | International ladder |
| H6 | Physical reserve status can remain observable enough to matter |
| Q5 | Tax base |
| Q6 | Industrial vetoes |
| Q7 | Covert software |
| Q8 | Domestic coalition |
| Q9 | International verification |
| Q10 | Regime adaptation |

Several of these overlap YAML nodes under other IDs (for example the reference's
D9 and the YAML's D4 both separate compute stock from compute entanglement; the
reference's D17 and the YAML's I6 both describe the international ladder). A
proposal should say which YAML node it overlaps and whether it adds anything.

## 2. In the YAML, not in the reference: accepted after the reference was written

| YAML ID | Title | How it entered |
|---|---|---|
| I4, I5, I6, I7 | Implementation options recorded when the YAML was first written | initial YAML |
| H10 | Retrospective audit makes concealment a losing long-run strategy | issue #3, accepted in #22 |
| H14 | External-signal dependence preserves some A/P separation | issue #1, accepted in #22 |
| I11 | Do not optimize against the audit signal | issue #3, accepted in #22 |
| Q11, Q12, Q13 | Open questions from issues #1 and #3 | accepted in #22 |

The clean-room verifier judges these against `source.yaml` alone.

## 3. Shared IDs with different titles

Eight are the same proposition in different words (`collision:
same-proposition` in the registry): K1, K3, K4, K5, K6, K7, Q1, Q2. The
registry records this judgment; the editor has not yet reviewed it (issue #22,
open box).

Sixteen are different propositions under the same ID (`collision: legacy`):
D1 to D6, H1 to H5, I1 to I3, Q3 and Q4. For example the reference's H5 is
"Public-frontier reciprocity produces restraint rather than only ratcheting
upward", while the YAML's H5 is "Domestic benefits can sustain the
institution". These IDs keep their YAML meaning. A reference proposition that
lost its ID this way is treated like section 1: it may be proposed under a
fresh ID, with the renumbering recorded. The reference's H5 is the clearest
case, since the frontier-router model (issue #89) now bears on it and K6's
rationale points to it.

## What this note is not

It is not a rendering and not a second reference. If it disagrees with
`make clean-room-audit` at the same commit, the audit is right and this note
is stale.
