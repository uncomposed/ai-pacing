# AI Pacing canonical specification

This repository publishes AI Pacing as a versioned, machine-readable idea rather than a single privileged essay. Git is authoritative. Human-facing pages, PDFs, games, songs, simulations, critiques, and other works are renderings of an exact Git state.

The canonical source is [`spec/ai-pacing.yaml`](spec/ai-pacing.yaml). It separates:

- `K` — kernel propositions that define the idea;
- `D` — derived mechanisms;
- `H` — falsifiable feasibility hypotheses;
- `I` — replaceable implementation choices;
- `Q` — open questions.

Every proposition records sources, the role AI played, and the canonical editor's acceptance status. The audit trail distinguishes documentary evidence from historical inference.

## Quality gate

Run the complete local gate:

```sh
make check
```

It checks YAML structure, typed and referential integrity, dependency cycles, provenance, hypothesis falsifiability, ten semantic acceptance tests, mutation tests, JSON Schema conformance, and whether committed deterministic views are stale.

Regenerate all views after an accepted model change:

```sh
make generate
make check
```

Inspect downstream claims before changing a proposition:

```sh
ruby tools/spec_tool.rb impact K4
```

Compute the format-independent semantic digest:

```sh
ruby tools/spec_tool.rb digest
```

See [`docs/verification.md`](docs/verification.md) for the test model and [`generated/rendering-review-checklist.md`](generated/rendering-review-checklist.md) for attributable rendering review.

## Deterministic projections

The generator produces:

- normalized canonical JSON and a semantic SHA-256;
- a seven-proposition minimal reconstruction;
- a chronological audit trail;
- a dependency graph;
- a flat claim register;
- an acceptance-test matrix;
- a rendering-verification checklist.

These files are projections, not parallel authorities. If a generated view and the YAML at the same commit disagree, the YAML controls and `make check` should report the stale view.

## Publication rule

A rendering may initially name a branch for discovery, but any verification must resolve that branch to a full immutable Git commit object ID. Verification is an attributable judgment about the declared relationship between an artifact and that exact state. It is not endorsement or a quality award.
