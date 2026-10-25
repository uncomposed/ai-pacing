# Changelog

## Unreleased

- ID hygiene (issue #23): renumbered the off-Earth report's candidate nodes D7, D8, Q6, Q7, Q8 to D20, D21, Q14, Q15, Q16 (report text and registry; no `reserved-conflict` entries remain), prefixed the assumption register's claim IDs `AR-H1` to `AR-H13` (enforced by `tools/assumptions_tool.py`) and `equilibrium.md` section 7 questions `EQ-Q1` to `EQ-Q10`, and reclassified them as prefixed local namespaces in the registry. Regenerated only `results/assumptions_report.md`. No accepted node or model output changed.
- Added a `proposed` acceptance status: proposed nodes must name their proposal issue, are excluded from kernel-identity, node-existence, and dependency-path acceptance assertions, the minimal reconstruction, and kernel coverage, and cannot ground or be depended on by accepted nodes.
- Recorded issues #1 and #3 as proposed, not accepted, nodes: H14 (external-signal dependence, issue H6), Q13 (cooperative autonomy path, issue Q5), H10 (retrospective audit), D18 (closing-window dynamics, a risk to test), I11 (keep the audit signal out of the training loop), Q11 (auditor independence), D19 (review-based model sharing against a singleton), and Q12 (convergence versus correlated failure).
- Added `spec/id-registry.yaml`, a reserved-ID registry across the YAML, the editorial reference, the off-Earth research report, and the proposal issues, with its JSON Schema, `make check` enforcement, a `next-id` command, and the old-to-new ID mapping.
- Added `docs/proposed-extensions.md` with the issue #1 reviews of D5/I1/I2 and K7, the Hugging Face worked example marked provisional pending issue #15, and positioning against Yudkowsky and Soares and Spaniel as characterized in issue #3.
- Added Alexey Potapov's “Reframing AGI Confrontation with Off-Earth Autonomy” as independently convergent related work without changing the origin provenance of earlier AI Breakout claims.

## 0.1.0 — 2026-08-29

- Reconstructed the seven-proposition canonical kernel from the prior AI Pacing specification.
- Added typed derived mechanisms, hypotheses, implementation choices, and open questions.
- Added proposition-level provenance and a documentary audit trail.
- Added executable semantic acceptance tests and explicit hypothesis stopping rules.
- Added deterministic views, semantic hashing, mutation tests, and JSON Schema validation.
- Encoded Git as the authority, commit-addressed verification, and one universal rendering envelope.
- Added a generic rendering manifest, historical-commit resolver, artifact hashing, and relationship-claim tests.
