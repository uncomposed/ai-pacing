# Issue 91: editor decision on the I11 relation

[[ai gen]] Paraphrased by Claude from Cole's decisions in a Claude Code review
session on 2026-11-06, in which the open PRs were reviewed. Nothing from the
session is quoted. The decision closes the last open box of issue #91 ("Editor
decision on the I11 relation"). Status: `implemented` and `verified` (`make
check` passes). Not `human_validated`.

## The question

I11 (accepted as an option in #22) forbids using trace-based detectors,
interpretability probes and retrospective-audit results as a training or
selection signal for the models they audit. I13 (proposed in #91) admits a
candidate model to AI research and development only if it passes a gate that
its sibling instances and rival lineages audit. The candidate is therefore both
auditor and audited, and the gate is a selection on audit results. The #91 PR
left the relation unresolved.

## What the reviewer put to the editor

1. Selection is optimization with a bounded budget. Choosing the best of n
   candidates moves the policy at most about log n nats of KL from the base
   policy (the best-of-n bound, SRC-BEIRAMI-2024-BEST-OF-N). Gradient training
   against a monitor has no such bound. The labs' own stated practice draws
   the line there: OpenAI calls patching training environments flagged by a
   chain-of-thought monitor "a very small evolutionary optimization pressure"
   (SRC-BAKER-2025-COT-MONITORING) and reports confidence that there are no
   significant direct chain-of-thought grading pressures (SRC-GPT-6-ASTRA-CARD).
2. Two findings argue for a hard cap on attempts rather than a recorded count:
   monitor-aware models under equal reinforcement-learning pressure learn to
   evade a monitor substantially faster than unaware controls
   (SRC-HASKINS-2026-MONITOR-AWARENESS), and I13 requires the candidate to know
   the sanction schedule; and in auditing games, the blue team could not
   reliably separate sandbagging from benign models, with elicitation raising
   benign scores too (SRC-TAYLOR-2025-AUDITING-GAMES), so Tier 2's
   false-positive rate on honest models is unmeasured.
3. Retraining after a failure, with the training environment, data and recipe
   unchanged by the result, is selection and stays inside the budget. Changing
   the environment, data or reward in response to a gate outcome is a direct
   effect and is forbidden.

## Decisions

| # | item | decision | applied as |
|---|---|---|---|
| 1 | Attempts per generation | hard cap, not a recorded count | I13 statement: attempts are hard-capped (illustratively three) |
| 2 | "Back in the oven" | allowed only with the training environment, data and recipe committed before the first attempt and unchanged between attempts | I13 statement and rationale; I11 rationale names the budget and the prohibition |
| 3 | Restart point | a failed attempt restarts from the last passing checkpoint, or from scratch with a fresh seed | I13 statement, as an option the operator must choose before the first attempt |
| 4 | I11 wording | keep I11; state the carve-out as an optimization budget in its rationale rather than an exception | I11 rationale; K7 → I11 assertion unchanged |
| 5 | H16 | the I11 relation is resolved; the bounded selection pressure and the Tier 2 false-positive base rate become scope limits and evidence needed | H16 `scope_limits`, `evidence_needed` |

Sources read for this decision are recorded with how far they were read
(abstracts unless stated). The off-Earth model was not run.

## Addendum, same session: the retained record

Asked whether the enclave should retain activations and states so that a
later interpretability advance can audit every past thought, the reviewer
proposed retaining what makes every run reproducible (inputs, seeds, frozen
stack, manifest, activation hashes) rather than raw activations, with replay
as the audit mechanism. The editor agreed, on the condition that the
encrypted-away record cannot become a backdoor around the sanction. Applied
as: a retention sentence in I13's statement, the encryption-with-the-weights
rule, a scope limit in H16 on the sanction locking the record and on replay
fidelity, and a replay-fidelity line in H10's evidence needed (an
editor-approved addition to an accepted node's evidence field; its statement
is unchanged).
