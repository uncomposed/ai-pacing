# GATE interfaces: units, ownership, and double counting with AI Futures

[[ai gen]] 2026-10-25. Draft for #13 box 6 and #11. It uses the #5 contract's accounting
quantities (`systems/modes.yaml`, `accounting`). When it was drafted, AI Futures (#14) had
not been pinned, and the statements about it below that are marked README-level date from
then. #14 has since pinned and run it (`research_notes/external/ai-futures-model/`,
GATE_OVERLAP.md). The section "Resolution (#35)" at the end resolves the compute units,
assigns each loop one owner and gives a worked coupling.

## Native units and time

| quantity | GATE unit | GATE ledger | contract accounting quantity | conversion and caveats |
|---|---|---|---|---|
| Physical compute stock Q (`compute`) | FLOP/year (stock of capacity) | aggregate (planner) | `compute_training` + `compute_inference` (shared stock) | Contract uses FLOP/s: divide by 3.156e7 s/year. Q is *not* capped at C_L; only usable compute g(Q) is (E19). |
| Training compute D (`training_compute`) | physical FLOP/year: the training share of usable capacity g(Q) at the start of the step (resolved in #35) | aggregate | `compute_training` (a stock, contract 0.6.0) | D[t] + R[t] = g(Q[t-1]) exactly; step 0 splits D_init + R_init. Over the one-year step D is also the FLOP performed: `physical_best_training_run` adds D each step. FLOP/s = D / 3.156e7. |
| Runtime compute (`runtime_compute`) | as D, the runtime share | aggregate | `compute_inference` (a stock) | Runs the digital workers; never passed to another model (loop L-AGENT-LABOR below). |
| Largest training run C_T (`best_training_run`) | eFLOP, software-adjusted with S(start of 2025) = 1 | aggregate | `capability` (state) | eFLOP depends on GATE's own S(t); not comparable to another model's effective compute without re-basing (below). `physical_best_training_run` is FLOP. |
| Task coverage f (`frac_automated`) | fraction of a unit task continuum | aggregate | `capability` | Planner's deployed share, below the frontier until f = 1 (E9). Not an `rd_capability` level. |
| Digital workers N_i | human-worker equivalents per task | aggregate | `agent_workforce` (a stock, derived from `compute_inference`; #61) | Never take both N and runtime compute as inputs to another model. `agent_labor` (hours/year) needs hours per worker-year, which GATE does not give. |
| Hardware efficiency H | FLOP/year per USD | aggregate | `efficiency_level` (a stock, derived from `research_output`; #61) | A level, not research output. |
| Software efficiency S | eFLOP/FLOP | aggregate | `efficiency_level` (#61) | A level, not research output. |
| Human labor L | workers (not hours) | aggregate | `human_workforce` (a stock; #61) | `human_labor` (person-hours/year) needs hours per worker-year; GATE has no hours. Exogenous growth g_L = 0.25%/yr. |
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

## Resolution (#35)

**Compute units (E7).** In every pinned run that reports the split (default, conservative,
aggressive), `training_compute[t] + runtime_compute[t] = Q[t-1] / (Q[t-1]/C_L + 1)`, the
usable compute at the start of the step, to machine precision (step 0 splits
`training_compute_init + runtime_compute_init`). And `physical_best_training_run[t] =
physical_best_training_run[t-1] + training_compute[t]`. So Q is a capacity stock in
FLOP/year, and D and R are its allocations, which together exhaust usable capacity. Each is a
stock (allocated capacity) in physical FLOP/year that, over a one-year step, equals the FLOP
performed. The ratio (D + R)/Q fell to about 0 only because Q passed the heat limit C_L =
2e38 FLOP/year, where g(Q) saturates. Checked by `coupling_example.py` and
`tests/test_epoch_gate.py` (`ComputeSplit`); units-bridge equations `GATE-COMPUTE-SPLIT` and
`GATE-TRAINING-RUN`. Q is not booked in the contract, since D and R already exhaust it.
The eFLOP series `best_training_run` still grows faster than software-adjusted D. That is
`continuous_training` re-applying S to past training. It stays unreproduced and is not
passed.

**One owner per loop** (`systems/modes.yaml`, `feedback_loops` and each adapter's
`feedback_loops`; the checker requires exactly one owner):

| loop (item above) | carries | owner | other model | why |
|---|---|---|---|---|
| L-COMPUTE-INVESTMENT (1) | compute_training, compute_inference, compute_experiment | AD-GATE | AIFM absent | only GATE makes compute investment endogenous |
| L-SOFTWARE-EFFICIENCY (2) | efficiency_level | AD-AIFM | GATE yields | AIFM has an explicit research production function; GATE's R&D law is not reproduced (E6) |
| L-RESEARCH-AUTOMATION (3) | research_output | AD-AIFM | GATE absent | GATE does not automate R&D |
| L-CAPABILITY-MAPPING (4) | capability | AD-AIFM | GATE yields | AIFM's milestones are the contract's milestone bindings (#47); GATE's f is a planner choice |
| L-AGENT-LABOR (5) | agent_workforce, agent_labor | AD-GATE | AIFM yields | digital workers in production are GATE's core channel |

**Coupling rules the checker enforces** (`couplings` in `systems/modes.yaml`):
1. A pass moves one adapter quantity to another on the same ledger, with resolved and equal
   kinds, into an input of the target, at most once per ledger.
2. A pass comes only from the owner of every loop that carries its ledger.
3. `capability`, `efficiency_level` and events never cross. Capability mappings are rivals,
   and effective compute is computed on one S (items 2 and 4).
4. A source never passes compute it already turns into a derived quantity on a loop it owns
   (item 5). So GATE's runtime compute R cannot become AIFM's inference compute.
5. Every input of a coupled model that is carried by a loop another coupled model owns is
   either passed or listed as uncoupled with a reason.
6. Every loop a coupled model yields has a stated treatment: `comparison_only`,
   `embedded_bracketed` (live inside a passed series, bracketed by scenarios) or
   `separate_ledger`.

**Worked example `XC-GATE-AIFM-TRAINING`** (passes the checks above and the contract's
double-counting rule):
- **The pass.** GATE's D goes to AIFM's frontier training capacity as H100e = s · D /
  1.262e22. s is the frontier project's share of world training compute. It is
  unidentified (units-bridge `CV-GATE-D-TO-FRONTIER-TRAINING`), so s = 1 is an upper bound
  only. `coupling_example.json` gives the upper bound at steps 0, 5, 10 and 20 for the three
  presets, for example 7.2e5 H100e at step 0 in the default run.
- **Uncoupled.** Inference and experiment compute stay uncoupled. AIFM keeps its own
  research series, which lie outside GATE's budget: GATE funds research in dollars, and
  D + R exhaust its usable compute.
- **Bracketed, not switched off.** GATE's own software-efficiency and capability loops shaped
  D. They cannot be switched off without re-solving GATE, so they are bracketed by the
  conservative and aggressive presets. Per the stopping rule, this is a bounded scenario,
  not a clean assignment of those loops inside D.
- **AIFM is not rerun on the passed series.** This is a specification, not a coupled
  trajectory.

## Open items for the interface

- Calendar mapping of step index 0.
- The frontier share s of world training compute (no source pinned).
- Re-solving GATE with software efficiency exogenous, to switch its loop off instead of
  bracketing it.
- Running AIFM on the passed series (the upstream is fetched at a pinned commit; this needs
  the network and is not part of `make check`).
