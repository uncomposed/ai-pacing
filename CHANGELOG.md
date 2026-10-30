# Changelog

## Unreleased

- ID hygiene (issue #23): renumbered the off-Earth report's candidate nodes D7, D8, Q6, Q7, Q8 to D20, D21, Q14, Q15, Q16 (report text and registry; no `reserved-conflict` entries remain), prefixed the assumption register's claim IDs `AR-H1` to `AR-H13` (enforced by `tools/assumptions_tool.py`) and `equilibrium.md` section 7 questions `EQ-Q1` to `EQ-Q10`, and reclassified them as prefixed local namespaces in the registry. Regenerated only `results/assumptions_report.md`. No accepted node or model output changed.
- Added a `proposed` acceptance status: proposed nodes must name their proposal issue, are excluded from kernel-identity, node-existence, and dependency-path acceptance assertions, the minimal reconstruction, and kernel coverage, and cannot ground or be depended on by accepted nodes.
- Recorded issues #1 and #3 as proposed, not accepted, nodes: H14 (external-signal dependence, issue H6), Q13 (cooperative autonomy path, issue Q5), H10 (retrospective audit), D18 (closing-window dynamics, a risk to test), I11 (keep the audit signal out of the training loop), Q11 (auditor independence), D19 (review-based model sharing against a singleton), and Q12 (convergence versus correlated failure).
- Added `spec/id-registry.yaml`, a reserved-ID registry across the YAML, the editorial reference, the off-Earth research report, and the proposal issues, with its JSON Schema, `make check` enforcement, a `next-id` command, and the old-to-new ID mapping.
- Added `docs/proposed-extensions.md` with the issue #1 reviews of D5/I1/I2 and K7, the Hugging Face worked example marked provisional pending issue #15, and positioning against Yudkowsky and Soares and Spaniel as characterized in issue #3.
- Added Alexey Potapov's “Reframing AGI Confrontation with Off-Earth Autonomy” as independently convergent related work without changing the origin provenance of earlier AI Breakout claims.
- Reconstructed the July 2026 Hugging Face incident from primary sources as 24 dated events with a topology, explanations, a mode trace and four frozen held-out predictions, kept abstract with no technique detail (first milestone of #15) (#28).
- Pinned Epoch's GATE bundle by hash and reran its official solver unchanged, with an equation map, planner-to-mode mapping and interfaces (#13) (#29).
- Scored the four frozen AISI held-out predictions for the Hugging Face case: a held-out check of a fitted reconstruction with three resolvable predictions, not validation of AI Pacing mechanisms (#36).
- Closed the three mode-contract gaps found by the Hugging Face trace in contract 0.2.0, loosening or extending the contract so that 0.1.0 examples stay valid (#32) (#37).
- Added a units bridge from AI research to industry: a recheck of the Metzger scale, a 38-quantity dictionary, a checker and a coupling toy (#11) (#38).
- Pinned and replicated the AI Futures Model at upstream commit `1c40ecdb`, covering the reference trajectory, a seeded milestone distribution and the feedback-off baseline (first milestone of #14) (#44).
- Reproduced METR's TH1.1 analysis from public data, with a dated observation table, a retrospective holdout and a locked forecast (first milestone of #12) (#46).
- Added bounded variants of the pact model testing strategic conclusions against bargaining, human preventive action and actor structures, with an omission matrix checked in `make check` (first milestone of #9) (#50).
- Made the METR reproduction workflow compare its headline within a tolerance instead of as exact text (#59).
- Defined the Earth-industry unit once and booked capacity A as a stock with an explicit output rate (#39) (#60).
- Added a METR per-model holdout with a pre-declared compute baseline (B-COMPUTE) (#56) and an AIFM held-out audit (#45) (#63).
- Declared a kind for every adapter quantity in the mode contract (0.4.0) (#64).
- Bound simulation caches and shard merges to experiment identity through run manifests (#21).
- Separated the model CI gates by evidence category (#43).
- Re-pinned METR and AI Futures quantities in the units bridge to native units; the coding chain stays unidentified (#42) (#68).
- Tested which qualitative GATE conclusions survive 22 variants at three optimizer caps, and added a bundle redeploy watch (#33) (#62).
- Read primary sources behind the units bridge's measured scales, in a first pass that records two of three sources as not read (#40) (#67).
- Added primary evidence records for AIFM's Epoch inputs (ECI and revenue), reporting differences without reconciling them (#66) (#70).
- Mode contract 0.5.0: a milestone-to-transition interface and `compute_experiment` (#47) (#69).
- Resolved GATE's compute split and coupled GATE to AIFM with one owner per loop (contract 0.6.0) (#78).
- Pinned RE-Bench and recorded fixed-budget comparisons (first milestone of #58) (#79).
- Diagnosed the R6c cell A_close 0.03, L_f 0.9 as grid artefacts at the saturation cap (#51) (#80).

## 0.1.0 — 2026-08-29

- Reconstructed the seven-proposition canonical kernel from the prior AI Pacing specification.
- Added typed derived mechanisms, hypotheses, implementation choices, and open questions.
- Added proposition-level provenance and a documentary audit trail.
- Added executable semantic acceptance tests and explicit hypothesis stopping rules.
- Added deterministic views, semantic hashing, mutation tests, and JSON Schema validation.
- Encoded Git as the authority, commit-addressed verification, and one universal rendering envelope.
- Added a generic rendering manifest, historical-commit resolver, artifact hashing, and relationship-claim tests.
