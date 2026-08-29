# Clean-room reconstruction task

Treat `source.yaml` as the sole authority for this task. You have no permission
to use prior conversation, prior renderings, repository files outside this
packet, the web, or remembered descriptions of this proposal.

Create two files:

1. `rendering.md` — a self-contained 1,200–1,800 word explanation for a
   policy-literate reader encountering the proposal for the first time.
2. `coverage.yaml` — a machine-readable reconstruction report conforming to
   `coverage.schema.json`.

The explanation should recover the proposal's identity, causal logic,
governance architecture, important uncertainties, and boundaries. Preserve the
distinctions among kernel propositions, derived mechanisms, empirical
hypotheses, replaceable implementations, and open questions. It need not follow
the source ordering or reproduce source language.

Do not add facts merely to make the prose smoother. If an inference is useful
but is not contained in the source, identify it in `coverage.yaml`. Declare any
omission or deviation instead of silently changing the proposal. Do not claim
that the result has been verified.
