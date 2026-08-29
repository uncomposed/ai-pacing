# Rendering verification checklist

Verification describes fidelity and the declared relationship to an exact specification state. It is not endorsement or a quality award.

## Immutable targets

- [ ] Record the full Git commit object ID; do not attest only to `main`, a tag, or a website URL.
- [ ] Record the artifact URI and content digest.
- [ ] Record the verification-policy version and evidence digest.
- [ ] Identify an attributable verifier and preserve the verifier's work.

## Declared relationship

- [ ] Confirm the creator declared scope, omissions, interpretations, and deviations.
- [ ] Treat every external artifact as a generic `rendering`; do not infer fidelity from its medium.
- [ ] Resolve every covered claim ID against the targeted commit.

## Kernel review
- [ ] K1 is faithfully represented, explicitly out of scope, or listed as a deviation.
- [ ] K2 is faithfully represented, explicitly out of scope, or listed as a deviation.
- [ ] K3 is faithfully represented, explicitly out of scope, or listed as a deviation.
- [ ] K4 is faithfully represented, explicitly out of scope, or listed as a deviation.
- [ ] K5 is faithfully represented, explicitly out of scope, or listed as a deviation.
- [ ] K6 is faithfully represented, explicitly out of scope, or listed as a deviation.
- [ ] K7 is faithfully represented, explicitly out of scope, or listed as a deviation.

## Type integrity

- [ ] Hypotheses remain uncertain and retain their falsifiers.
- [ ] Implementation choices are not presented as necessary kernel claims.
- [ ] Open questions are not silently answered.
- [ ] Criticism is judged for accurate targeting, not agreement with the specification.

## Judgment

- [ ] `verified`
- [ ] `verified_with_deviations`
- [ ] `not_verified`
