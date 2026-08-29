# Verification and acceptance strategy

The test suite is designed to catch the failure mode that motivated the canonical specification: a plausible rewrite can remain locally fluent while silently changing the idea's type structure or damaging dependent claims.

## 1. Serialization and schema checks

These establish that the document can be parsed and has the expected shape. They catch missing required collections, invalid node types, malformed dates in the normalized JSON, and incompatible external tooling.

Passing these tests does **not** establish that the idea was modeled faithfully.

## 2. Referential and graph checks

Every source, proposition, audit event, and dependency has a stable ID. The validator rejects:

- duplicate IDs;
- dangling proposition or source references;
- duplicate edges;
- dependency cycles;
- node IDs whose prefixes disagree with their typed layer.

The `impact` command computes the transitive downstream claims of a proposed change. This is the omission check to run before revising a proposition.

## 3. Typed-layer checks

The validator requires every hypothesis to state a falsifier, evidence requirement, and stopping rule. Every implementation option must declare that it is replaceable. Every node must carry proposition-level provenance and human acceptance status.

These checks are meant to prevent:

- hypotheses becoming conclusions;
- implementation preferences becoming essential theory;
- open questions disappearing through confident prose;
- AI suggestions being included without human responsibility.

## 4. Semantic acceptance tests

The YAML contains executable assertions for the theory's important relationships. They test the stable semantic IDs and dependency paths rather than searching prose for favored words.

The current suite requires:

1. exactly seven kernel propositions;
2. a dependency path from capability/power separation to hardware entanglement;
3. a path from the research/deployment distinction to an external-agency boundary;
4. adversarial review between above-frontier gating and weights-as-bond implementation;
5. domestic entry and automatic foreign reciprocity in the same international mechanism;
6. legal, technical, and physical implementations of warning-time maximization;
7. falsifiable feasibility hypotheses;
8. visibly replaceable implementation options;
9. proposition-level provenance;
10. Git-commit-addressed publication and a universal rendering envelope.

The generated acceptance matrix gives a reviewable deterministic view of these results.

## 5. Mutation tests

The unit tests deliberately damage an in-memory copy of the specification. The suite confirms that validators catch:

- dangling dependencies;
- a dependency cycle;
- a hypothesis with no falsifier;
- silent promotion of an implementation option;
- unknown provenance;
- corruption of the seven-claim kernel checksum.

This is a lightweight falsification test for the validator itself. A validator that only succeeds on the canonical file without rejecting known-bad mutations provides weak evidence.

## 6. Deterministic-view tests

Views are rendered from normalized data in stable ID order. `make check` recomputes each view in memory and compares it byte-for-byte with the committed file. This catches manually edited projections and generation drift.

The normalized JSON receives a semantic SHA-256 after recursively sorting mapping keys. Reformatting YAML keys therefore does not change the digest; changing list order or semantic content does.

## 7. Rendering verification

An independently created artifact uses one generic rendering envelope regardless of medium. The manifest should declare:

- artifact URI and digest;
- creator identity;
- full target Git commit;
- claimed relationship;
- covered propositions;
- omissions and deviations;
- requested verification policy.

The verifier then produces an attributable judgment against that exact commit and preserves the evidence used. The permitted judgments are `verified`, `verified_with_deviations`, and `not_verified`.

Verification means the relationship was described accurately. A hostile critique may be verified; an elegant policy paper may fail for silently changing a hypothesis.

## 8. Human review and stopping rules

Automated checks cannot determine whether the English propositions are true, whether a historical source genuinely supports a claim, or whether important concepts were omitted from the model. Before a canonical release, a named reviewer should inspect:

- the minimal reconstruction against the intended idea;
- the audit trail against source material;
- each hypothesis's falsifier and stopping rule;
- the impact report for every changed kernel proposition;
- the diff of generated views;
- at least one critical or adversarial rendering.

A release should stop when any kernel claim lacks responsible human acceptance, when a foundational hypothesis has crossed its stopping rule, or when deterministic views cannot be reconciled with the YAML.
