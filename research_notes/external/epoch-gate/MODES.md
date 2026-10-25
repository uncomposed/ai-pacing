# GATE: who decides, and the three modes

[[ai gen]] 2026-10-25. Vocabulary from the #5 contract (`systems/modes.yaml`,
`docs/ai-development-modes.md`). The machine-readable result is the contract's `AD-GATE`
adapter entry, updated in this change; this note gives the reasons.

## Who allocates, and whose objective is optimized

GATE has exactly one decision-maker: **a social planner** (paper lines 183, 190, 454, 603).
Each year it chooses

- the split of output Y among consumption, capital investment, compute investment, hardware
  R&D and software R&D (five shares summing to 1; solver `q_*`), and
- the split of the compute budget between training and runtime (solver
  `q_training_compute`, `q_runtime_compute`);

the allocation of runtime compute across automated tasks and of human labor across tasks
follow from first-order conditions given those choices (line 1087). The planner maximizes
the discounted CRRA utility of **one representative household's** consumption (line 615),
with perfect foresight in the baseline and a known prior over automation functions in the
uncertainty add-on.

The paper says why: to avoid committing to market structures for compute and ideas
(line 190), and it calls the result a benchmark "under minimal market frictions" (line 603)
and a possible upward-biased path because the planner internalizes R&D spillovers (line
729). The R&D-wedge add-on is its only device for a less-than-optimal allocator, and it is
still a planner with a misspecified model, not a set of competing actors (line 1104).

So, in contract terms:

| question | GATE's answer | contract consequence |
|---|---|---|
| Which entities exist? | One closed economy. No `lab`, `state`, `other_org`, `agent_instance`, `agent_collective` or `model_weights` entity. | Nothing to attach a mode view to. |
| Who chooses? | A planner, solved by an optimizer (sign-gradient descent, 40 iterations, 160-year horizon). | The allocations are an optimum of a stated objective, not a forecast of what labs, states or AIs will do. |
| Whose objective? | A representative household's consumption utility. | `objective_selection` is not represented. There is no AI objective at all. |
| Who owns compute, weights, output? | Implicitly the household; all stocks are aggregate. | `custody_weights`, `custody_compute`, `custody_credentials`, `external_resources` are not represented. |
| What are AIs? | "Digital workers": runtime compute per task, a production input (line 523). | `agent_labor` in the accounting sense only; never an entity. |
| Control, authorization, intervention? | Absent. | `authorization`, `effective_control`, `operational_autonomy`, `intervention_latency`, `dependencies`, `communication_topology`, `enforceable_commitments` are not represented. |
| Capability? | Largest training run C_T (eFLOP) and the fraction of a task continuum automatable. | Maps to `capability` (accounting) and, loosely, to `rd_capability` only in the sense of task coverage; nothing maps to `strategic_capability` or `cyber_capability`. |

## Mode mapping

| mode (#5) | coverage | reason |
|---|---|---|
| `MODE-HUMAN-LAB` | **partial** | GATE's world is one in which humans (through the planner) direct every allocation and AI never acts on its own account, which is consistent with this mode's premise. But the mode is a predicate over a lab entity with `effective_control = human_effective`, weights in lab custody and intervention `within_required`, and GATE has no lab, no custody and no control. It can supply world-level background (output, compute, automation) for lab entities, not a lab's own state. |
| `MODE-SOVEREIGN-CAPABLE` | **unsupported** | Requires `strategic_capability` at `independent_plausible` or above for a lab-hosted system. GATE has no strategic capability and no system entity. Full automation (f = 1) is coverage of economic tasks, not independent strategic action. |
| `MODE-SOVEREIGN` | **unsupported** | Requires `objective_selection = system_self`, no host, no effective human control and substantial `external_resources`. GATE has no AI objective, all output accrues to the household, and no resource is held by an AI. |

**Not supported extensions** (listed so that nobody adds them silently):

1. Treating digital workers as an actor. They are compute-per-task in a CES aggregator.
   Turning them into an `agent_collective` with objectives would be a new model, not GATE.
2. Reading the planner's allocation as a lab's, a state's or an AI's decision. Real
   allocators have different objectives, information and constraints; GATE's allocation is
   an optimum and its quantitative path is optimizer-limited at the percent level
   (README, "Convergence").
3. Reading f = 1 (full automation) as a transition. No contract transition (`T-DELEGATE`,
   `T-LOSS-OF-CONTROL`, ...) is represented; f is not `authorization` or
   `operational_autonomy`.
4. Using GATE's post-automation dynamics. Epoch's own documentation says the model is
   likely to make poor predictions close to and after full automation (training compute
   falls to zero once f = 1).

**What a coupling may use.** World-level trajectories in native units (GWP, compute stock,
largest training run, task coverage) as an exogenous background for `MODE-HUMAN-LAB`
entities, labelled as a planner benchmark, through #11's quantity bridge. The comparison
the decision rule of #13 allows: if no defensible coupling exists, GATE stays a comparative
model.
