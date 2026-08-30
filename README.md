# AI Pacing canonical specification

This repository publishes AI Pacing as a versioned, machine-readable idea rather than a single privileged essay. Git is authoritative. Human-facing pages, PDFs, games, songs, simulations, critiques, and other works are renderings of an exact Git state.

The canonical source is [`spec/ai-pacing.yaml`](spec/ai-pacing.yaml). See
[`CANONICALITY.md`](CANONICALITY.md) for the exact authority order and the known
conformance gap between the YAML and the supplied editorial reference. The YAML
separates:

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

Validate a rendering against the exact historical specification and artifact bytes it targets:

```sh
ruby tools/rendering_tool.rb examples/renderings/minimal-reconstruction.yaml
```

The example intentionally targets the repository's first immutable commit. The validator resolves that commit, loads the specification from that historical state, checks every covered proposition there, and recomputes the artifact digest from the bytes stored in the target commit.

See [`docs/verification.md`](docs/verification.md) for the test model and [`generated/rendering-review-checklist.md`](generated/rendering-review-checklist.md) for attributable rendering review.

The repository also contains the standard IRAP files under `.idea/`. They give
AI Pacing a durable registry identity, declare the planned public Git mirror,
and define recognized `faithful_rendering` and `clean_room_reconstruction`
claims. Validate them with:

```sh
ruby tools/irap_tool.rb
```

Generate administrator-ready request bodies for the IRAP Publisher without
including an administrator token:

```sh
ruby tools/registry_payload.rb idea
ruby tools/registry_payload.rb dependency-map
```

The idea payload resolves the current checkout to a full commit ID. The
dependency-map payload uses the artifact and target digests already validated by
its rendering envelope.

## Clean-room reconstruction test

Build a sealed packet for a fresh model that contains no essay, executive
summary, deterministic reconstruction, or prior model answer:

```sh
make clean-room
```

The packet is written to `build/clean-room-generator/`. Give that directory—and
only that directory—to a model with no conversation memory, repository access,
or web access. Keep `eval/clean-room/evaluation-rubric.yaml` and the canonical
Markdown away from the generator; those belong to an independent verifier.

Audit structural drift between the newly supplied canonical Markdown and the
current YAML:

```sh
make clean-room-audit
```

This audit is deliberately diagnostic rather than part of `make check` for now:
the two sources materially diverge and need an editorial reconciliation rather
than an automatic overwrite. See [`docs/clean-room-reconstruction.md`](docs/clean-room-reconstruction.md).

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

An editable draw.io dependency map is available at
[`renderings/ai-pacing-dependency-map.drawio`](renderings/ai-pacing-dependency-map.drawio).
Its generic rendering envelope records the exact source commit, artifact digest,
scope, and omissions in [`examples/renderings/dependency-map.yaml`](examples/renderings/dependency-map.yaml).

## Publication rule

A rendering may initially name a branch for discovery, but any verification must resolve that branch to a full immutable Git commit object ID. Verification is an attributable judgment about the declared relationship between an artifact and that exact state. It is not endorsement or a quality award.
