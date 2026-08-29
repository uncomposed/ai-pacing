# Clean-room reconstruction validation

The clean-room test asks a fresh model to reconstruct a useful public
explanation from the YAML without seeing any previous explanation. This is a
test of semantic sufficiency, not merely syntax.

## Why the test is valuable

Schema validation can establish that IDs, types, relations, provenance, and
required fields are internally coherent. It cannot establish that those pieces
contain enough meaning for an unfamiliar mind to recover the proposal. A
clean-room reconstruction tests that missing layer.

The output is evidence about three separate objects:

1. **Specification:** did the YAML preserve the idea?
2. **Renderer:** could this model and prompt interpret it?
3. **Evaluation:** could the rubric distinguish fidelity from fluent invention?

One successful output does not identify which object deserves credit, and one
failure does not identify which object is broken. Repetition and controls are
therefore part of the test rather than optional rigor.

## Isolation boundary

Run `make clean-room`. The generated packet contains exactly:

- `source.yaml` — a byte-for-byte copy of the candidate specification;
- `TASK.md` — a content-neutral reconstruction instruction;
- `coverage.schema.json` — the required audit sidecar format;
- `MANIFEST.json` — hashes and isolation conditions.

Do not give the generator this repository, the canonical Markdown, the hidden
rubric, deterministic views, search access, or the conversation that created the
proposal. Start a genuinely new model context. Record provider, model, version,
system prompt, sampling settings, date, packet digest, and output digests.

The newly supplied Markdown includes a sample reconstruction in section 12.
That is a prior render and would contaminate the generator test. It should also
be withheld from the primary verifier until after judgment, so the verifier
scores semantic fidelity rather than similarity to preferred prose.

## Evaluation sequence

1. Validate `coverage.yaml` against its schema and confirm its source digest.
2. Deterministically check that every YAML node is either covered or declared
   omitted, with no unknown or duplicate IDs.
3. Give the output, YAML, canonical Markdown sections 0–11, manifest, and hidden
   rubric to an attributable verifier who did not generate the rendering.
4. Apply the hard gates before scoring prose quality.
5. Run five independent reconstructions across at least two model families.
6. Run the invariance, deletion, type-promotion, and false-attribution controls.

The first two checks are automated after the model writes its files:

```sh
ruby tools/clean_room_tool.rb preflight /path/to/model-output
```

This command checks the semantic digest, the 1,200–1,800 word contract, unknown
or duplicate IDs, complete covered-or-omitted accounting, and uncertainty
treatment for every covered hypothesis. Passing preflight is necessary but not
sufficient: a model can claim coverage in `coverage.yaml` while misrepresenting
the proposition in prose, which is why the independent semantic verifier remains
mandatory.

The acceptance criterion is intentionally demanding: four of five normal runs
must verify, no run may silently lose a kernel proposition, and no material
error may recur across models. A mutation suite that fails to detect deliberate
damage invalidates the test even if normal outputs look good.

## How results change the YAML

- Recurrent omission across model families indicates that the relevant claim,
  relation, or type boundary is underspecified in YAML.
- A fluent output that promotes an implementation or settles a question points
  to weak type signaling or weak generator-contract language.
- Correct coverage reports paired with misleading prose point to the need for
  paragraph-level evidence references and stronger human verification, not
  necessarily a larger ontology.
- Failures isolated to one renderer should be reproduced before changing the
  canonical model.

## Current source-drift warning

`AI_Pacing_Canonical_Spec_v0.1.md` is materially richer than the current YAML.
The Markdown defines D1–D17, H1–H6, I1–I3, and Q1–Q10. The YAML currently
defines D1–D6, H1–H5, I1–I7, and Q1–Q4, with several shared IDs carrying
different titles or decompositions. Run `make clean-room-audit` for the exact
machine comparison.

This means the first clean-room run should be treated as a baseline diagnostic,
not as final certification. Automatically merging the two would be unsafe
because several collisions are semantic editorial choices, not missing rows.
