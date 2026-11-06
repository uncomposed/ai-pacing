# Canonicality and projection boundaries

## Challenge workspace boundary

`systems/model.json` is the editable draft for stakeholder challenges,
requirements, and candidate solutions described in `docs/systems-engineering.md`.
It is not a rendering of the AI Pacing proposal and does not inherit the proposal's
kernel commitments. Its links to legacy proposition IDs record correspondence,
not empirical support or requirement satisfaction. The authority order below
continues to govern the existing AI Pacing proposal; no historical proposition
is retyped by adding this separate workspace.

AI Pacing separates normative content from editorial references and generated
views so that a readable page cannot silently become the idea's authority.

## Authority order

1. An exact Git commit identifies an immutable state of the idea.
2. Within that state, `spec/ai-pacing.yaml` is the normative machine-readable
   specification.
3. `.idea/manifest.yaml`, `.idea/verifiers.yaml`, and
   `.idea/verification-policy.yaml` define IRAP identity and historical
   verification policy for that state.
4. `AI_Pacing_Canonical_Spec_v0.1.md` is the supplied editorial reference,
   frozen at its 2026-08-29 state on 2026-11-06. It records what the author
   intended when the YAML was first written and is used to audit the YAML
   against that intent. It is not updated and does not grow with the YAML.
5. Files under `generated/`, diagrams, websites, essays, and other artifacts are
   projections or renderings. They never override the YAML.

Within the YAML, a node whose `provenance.author_status` is `proposed` is
recorded for the editor's review and is not part of the accepted idea. A
rendering must not present it as accepted. `spec/id-registry.yaml` records which
proposition IDs each source uses, so the YAML and the editorial reference cannot
acquire new silent ID collisions.

The editorial reference contains claims and decompositions that were never
reconciled into YAML, and the YAML has accepted nodes the reference does not
have. On 2026-11-06 the canonical editor's reviewer closed this as a recorded
divergence rather than an open conformance issue: the reference is frozen,
the YAML is canon, and `docs/editorial-reference-status.md` lists every
difference with what it means. Propositions the reference has and the YAML
lacks are a backlog of candidate proposals; each enters the YAML only through
a spec-proposal issue and a `proposed` node. A renderer must not merge the two
files silently. Run `make clean-room-audit` for the machine comparison.

## Low-distortion view rule

A low-distortion view should:

- identify the exact source commit and semantic digest;
- copy proposition statements and types rather than paraphrasing them;
- derive edges only from declared relations;
- preserve hypotheses, implementations, and open questions as distinct types;
- expose omissions and transformations;
- remain reproducible from the YAML; and
- describe itself as a projection, never as a second canonical source.

Animation may reveal sequence, dependency, or impact. It must not imply a
causal strength, certainty, priority, or temporal order absent from the YAML.
