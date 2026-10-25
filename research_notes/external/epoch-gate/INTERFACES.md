# GATE interfaces: units, ownership, and double counting with AI Futures

[[ai gen]] 2026-10-25. Draft for #13 box 6 and #11. It uses the #5 contract's accounting
quantities (`systems/modes.yaml`, `accounting`). AI Futures (#14) has not been pinned or
run; statements about it come from the contract's `AD-AIFM` entry (README-level) and are
marked as such.

## Native units and time

| quantity | GATE unit | GATE ledger | contract accounting quantity | conversion and caveats |
|---|---|---|---|---|
| Physical compute stock Q (`compute`) | FLOP/year (stock of capacity) | aggregate (planner) | `compute_training` + `compute_inference` (shared stock) | Contract uses FLOP/s: divide by 3.156e7 s/year. Q is *not* capped at C_L; only usable compute g(Q) is (E19). |
| Training compute D (`training_compute`) | solver-native per step; the paper says eFLOP | aggregate | `compute_training` | Ratio of D + runtime to Q unresolved (E7); do not convert until it is. |
| Runtime compute (`runtime_compute`) | as D | aggregate | `compute_inference` | as D. |
| Largest training run C_T (`best_training_run`) | eFLOP, software-adjusted with S(start of 2025) = 1 | aggregate | `capability` (state) | eFLOP depends on GATE's own S(t); not comparable to another model's effective compute without re-basing (below). `physical_best_training_run` is FLOP. |
| Task coverage f (`frac_automated`) | fraction of a unit task continuum | aggregate | `capability` | Planner's deployed share, below the frontier until f = 1 (E9). Not an `rd_capability` level. |
| Digital workers N_i | human-worker equivalents per task | aggregate | `agent_labor` (derived from `compute_inference`) | Never take both N and runtime compute as inputs to another model. |
| Hardware efficiency H | FLOP/year per USD | aggregate | `research_output` | |
| Software efficiency S | eFLOP/FLOP | aggregate | `research_output` | |
| Human labor L | workers (not hours) | aggregate | `human_labor` (person-hours/year) | Multiply by hours per worker-year; GATE has no hours. Exogenous growth g_L = 0.25%/yr. |
| Output Y, consumption, investment flows | real USD/year (price base not stated beyond "real USD") | aggregate | `industrial_output` | Not the pact solver's Earth-industry units. Readable in EIU/yr through units-bridge `CV-GWP-TO-EIU-OUTPUT` (measured, uncoupled; #39). |
| Capital K | real USD | aggregate | none | Non-compute capital; no contract quantity. |
| Physical resources | non-accumulable factor F with elasticity mu (default 0); heat limit C_L = 2e38 FLOP/year | aggregate | none | Energy and land enter only through mu and C_L. No chips, fabs or power as separate stocks (fab scale-up is reported as `chip_fabrication_scale_up`, a ratio). |
| Time | one-year steps; index t = t+1 years after the initial state (start of 2025 per the paper); 80-year plan, 160-year optimization horizon | | | Use step offsets, not calendar years, until the start date is confirmed against the playground's labels. |

**Ownership and budget.** Every stock is aggregate and implicitly the household's. There is
one budget (Y, real USD/year) and one compute budget (Q). Any split of GATE quantities
across labs, states or AIs (the contract's mixed-population accounting) is an assumption
added outside GATE and must be declared as such.

## Where coupling with AI Futures would count the same thing twice

The contract already rejects an adapter that takes a quantity and its parent as inputs. The
risks below are larger than that rule catches, because both models *produce* the feedback
rather than take it as input.

1. **Compute investment feedback.** GATE makes compute investment endogenous: output funds
   compute, compute raises output (the core loop). AI Futures takes compute as a forecast
   (contract `AD-AIFM`, README-level, to verify in #14). Feeding GATE's compute path into
   AI Futures is one use of the loop; also letting AI Futures' accelerated progress raise
   GATE's output, which then raises GATE's compute, closes the loop a second time. Pick one
   model to own the compute-investment loop.
2. **Software efficiency.** GATE's S(t) grows from R&D spending (E6, not reproduced). AI
   Futures has its own software-efficiency multiplier driven by research labor and
   automation. Applying both to the same effective-compute number multiplies two models of
   the same progress. Effective compute must be re-based to one S.
3. **Automation of research.** GATE explicitly does not automate R&D: AI raises output only
   through digital workers in production, R&D is funded in dollars (paper line 325 and the
   TFP footnote at line 664). AI Futures' core mechanism is automation of AI research. These
   are different channels, but if AI Futures' research speed-up is fed in as GATE's software
   or hardware growth, and GATE's extra output is also spent on R&D, the R&D channel is
   counted once as labor automation and once as spending.
4. **Effective-compute milestones vs task coverage.** Both models map effective compute to
   capability (GATE: T = 1e36.5 eFLOP for full automation with a FLOP gap; AI Futures:
   milestones on an effective-compute scale). Using one model's milestone dates to set the
   other's capability state double counts the capability assumption. Treat them as rival
   mappings and compare.
5. **Labor.** GATE's digital workers derive from runtime compute. If AI Futures' agent labor
   (also derived from inference compute) is added to GATE's production, the same inference
   compute is counted twice; the contract's `derived_from` rule covers this only if both are
   declared as inputs of one adapter.

**Rule for #11 and #14.** One model owns each loop: compute investment (GATE, if a macro
budget is wanted), research automation and software efficiency (AI Futures, if research
feedback is wanted). The other model's version of that loop is switched off or used only as
a comparison run, never both live in one coupled trajectory.

## Open items for the interface

- Units of `training_compute` and `runtime_compute` relative to Q (E7) must be resolved
  before any compute quantity crosses from GATE to another model.
- Calendar mapping of step index 0.
- AI Futures pinning (#14) to replace the README-level statements above.
