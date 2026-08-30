# Canonicality and projection boundaries

AI Pacing separates normative content from editorial references and generated
views so that a readable page cannot silently become the idea's authority.

## Authority order

1. An exact Git commit identifies an immutable state of the idea.
2. Within that state, `spec/ai-pacing.yaml` is the normative machine-readable
   specification.
3. `.idea/manifest.yaml`, `.idea/verifiers.yaml`, and
   `.idea/verification-policy.yaml` define IRAP identity and historical
   verification policy for that state.
4. `AI_Pacing_Canonical_Spec_v0.1.md` is the supplied editorial reference used
   to audit whether the YAML captured the intended proposal.
5. Files under `generated/`, diagrams, websites, essays, and other artifacts are
   projections or renderings. They never override the YAML.

The editorial reference currently contains claims and decompositions that have
not all been reconciled into YAML. This is an explicit open conformance issue,
not an invitation for a renderer to merge the files silently. Run
`make clean-room-audit` to inspect the drift.

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
