# Units and evidence bridging AI research progress to industrial growth and chip autonomy (#11)

[[ai gen]] 2026-10-25. Status: first milestone. Machinery, an audit and a toy; nothing here is
empirical validation, and nothing is coupled into the pact solver.

| kind of result | status |
|---|---|
| Source replication | Metzger Fig. 2 re-digitized from the arXiv manuscript's raster; rates reproduce the docking's within 0.01/yr. No other source model is replicated here (METR, GATE and AI Futures belong to #12, #13, #14); #42 rechecked the dictionary against the METR and AI Futures replications, and no link from horizon to developer time to research output is identified. |
| Numerical correctness | Every declared conversion and 17 equations pass a dimensional check; derived factors are recomputed; the toy reduces to the solver's unchanged growth law (relative 2e-12). |
| Empirical validation | None. No conversion is fitted to data. Two measured scales: world GDP, read in primary form (World Bank WDI, #39), which sets the output scale of the Earth-industry unit; world primary energy, read only in secondary summaries. A measured scale is not a validated model. |

## Files

| file | what |
|---|---|
| `quantities.yaml` | Quantity dictionary: units, dimensions, observables, mode-contract mapping, evidence status. Covers capability metrics, research labor and output, software efficiency, training and inference compute, energy, physical capital and output, supply-chain closure, external control. Also the four closure and sovereignty concepts (box 5). |
| `conversions.yaml` | Every cross-model conversion: units, form, mechanism, delay, constraints, evidence status, coupled or not. Classes separate normalizations and identities from empirical scale estimates, bounded scenarios, unidentified links and forbidden ones. |
| `equations.yaml` | The solver's growth law, the Metzger energy bridge and the toy's equations, with symbol units, for the dimensional check. |
| `data/world_gdp_wdi.json` | World GDP 2022-2025 (market rates, current and constant 2015 US$; PPP) and industry's share of value added, copied from the World Bank API with the SHA-256 of each response (#39; evidence record `EV-WB-WDI-GDP-2026`). |
| `coupling_toy.py`, `results/coupling_toy.{md,json}` | Research-to-industry toy with compute, energy, capital and chip-supply bottlenecks, against the exogenous baseline (box 4, box 6 limiting case). |
| `metzger/RECHECK.md`, `metzger/digitize_fig2.py`, `metzger/fig2_digitized.json` | Box 1: source and version recheck, re-digitization, citation correction. |
| `tests/test_units_bridge.py` | Offline tests (under 2 s), run by `make test`. |
| `../../../tools/units_tool.py`, `../../../test/units_tool_test.py`, `../../../schema/units-bridge.schema.json` | Checker (`make units-check`, part of `make check`), its mutation tests, and the file shapes. |

## How to run

```sh
make units-check                                   # schema, units, dimensions, contract links, stopping rule
make units-report                                  # quantities by category, conversions by class
python3 research_notes/external/units-bridge/coupling_toy.py           # rewrite results/coupling_toy.*
python3 research_notes/external/units-bridge/coupling_toy.py --check   # compare with the committed results
python3 research_notes/external/units-bridge/metzger/digitize_fig2.py  # needs network, pdfimages, numpy, Pillow
```

## What the checker enforces

- Unit strings parse into declared base dimensions. Two dimensions are normalizations, not physical:
  `earth_industry` (EIU, the solver's H = 1) and `le_capacity` (LEC, the solver's F = 1).
- **Each normalized unit is defined once** (`definitions` in `quantities.yaml`, #39): as a stock, with
  the solver equations that read it as a stock or as a flow, the conversions that measure it, and the
  readings it rejects. A unit used per time must state its output rate, a normalization from a stock to a
  flow in that unit.
- **Stocks and flows stay apart** (#39). A stock is never booked to a flow accounting quantity of the mode
  contract, nor a flow to a stock. In a normalized unit a flow carries 1/time and a stock or threshold
  does not. An adapter quantity the dictionary links as a stock or flow declares the same `kind` in
  `systems/modes.yaml`, and an adapter `output_rate` equals the dictionary's output-rate conversion.
  (`tools/modes_tool.py` checks the contract side: a declared kind matches its ledger, an output rate
  leads to a flow derived from the stock, trace resources are stocks.)
- A value marked `observed_primary` cites a record in `evidence/records.yaml` that is an observation read
  in primary form.
- Conversions are dimensionally consistent for their form (linear, reciprocal, log10, exp10).
- A factor that mixes a normalized and a physical dimension (W/EIU, EIU/t), or two physical
  dimensions other than time, cannot be a normalization or an identity. It must be an empirical scale
  estimate (with an evidence status and, if coupled, bounds), a bounded scenario (bounds only), or
  unidentified.
- Unidentified and forbidden conversions are never coupled and carry no value.
- A derivation, when given, reproduces the declared factor and unit.
- **Stopping rule**: no chain of coupled conversions leads from a capability metric to supply-chain
  closure, external control, or a quantity marked `no_calibration_from_capability` (strike odds,
  the denial reserve). The forbidden list names the obvious shortcuts explicitly.
- Mode-contract references exist, and the dictionary's unit agrees with each adapter quantity's unit in
  `systems/modes.yaml`. Pact parameters named exist in PARAMS.
- The four closure and sovereignty concepts map to different contract elements, no quantity belongs to
  two of them, no conversion links two of them, and sovereignty lists no quantities (it is a view).

Dimensional analysis cannot tell a METR horizon (hours) from a doubling time (years) by meaning; the
`semantic` field, the classes and the forbidden list carry that part.

## The Earth-industry unit (#39)

**Definition (`DEF-EIU`).** One EIU is the productive capacity of the whole world economy in the
reference year (2024 for measured scales, 2023 to 2025 in their bounds): the capital, energy supply,
compute, labour and organisation that produce that year's gross world output. It is a **stock**. Its
output rate is fixed by convention at 1/yr (`CV-CAPACITY-TO-OUTPUT`), so one EIU/yr is the reference
year's gross world output as a real quantity.

**Why this one.** It is the reading the solver's equations need (equations `PACT-*` in
`equations.yaml`, from `equilibrium_model.solve`):

| role | where | what it needs |
|---|---|---|
| stock | growth `A exp(g chi dt (1 - A/Kmax))`; seizure `A - cS + (1 - c_w) H`; reinvested trade `+ sigma trade dt`; defence D compared with A | capacity that compounds and changes hands |
| flow | AI payoff `u(A + sigma trade) dt`; human welfare `(1 + (1 - sigma) trade / N) dt`; trade `gam min(A, H)` per year | A's and H's yearly output, at rate 1/yr |
| whole economy | human welfare per year is H's output; trade is a share of "the smaller partner's economy"; the denial reserve kills a share d of "Earth capacity" | H is the economy, not a sector |

Without the rate the flow equations add EIU to EIU/yr; `make units-check` shows it (`PACT-AI-FLOW`).

**Rejected readings.**

| reading | why rejected | kept as |
|---|---|---|
| industry (manufacturing, mining, utilities, construction) | the solver uses H as the whole economy (welfare, trade); industry is 25.4% of world value added (2024), so welfare would lose three quarters | the unit's name only |
| primary energy (19.6 TW) | a flow; no solver equation uses energy; energy per unit of output differs off Earth | `CV-EIU-TO-PRIMARY-POWER`, an energy-intensity estimate (Metzger docking, Kmax "Dyson-scale") |
| GDP (USD/yr) | a flow in money at a price base; A and H are stocks; the solver has no prices; a money index drifts from capacity under large relative price changes | `CV-GWP-TO-EIU-OUTPUT`, the measured scale of the output rate |

**GATE's USD output.** One EIU/yr = 2024 world GDP at market exchange rates, current US$, 1.117e14
USD/yr (World Bank WDI, read in primary form; `EV-WB-WDI-GDP-2026`). The factor is 8.96e-15 EIU/USD,
bounded 8.45e-15 to 1.06e-14 by reference year 2023 to 2025 and price base (current or constant 2015
US$). PPP (about 2.0e14) is excluded because GATE's own Y(0) = 1.10e14 lies in the market-rate band.
So GATE's Default step 10 GWP of 2.51e15 USD/yr reads as about 22 EIU/yr (21 to 27). The conversion maps
units only and stays **uncoupled**: GATE's Y is Earth's output, which the pact freezes at H = 1, and a
projected real-USD path is a quantity index that need not track capacity once automation moves relative
prices.

**What changes and what does not.** No parameter value, solver output or result changes (the solver is
homogeneous in its unit). The definition fixes what the conversions to energy, mass and money mean, and
the mode contract now books A to `industrial_capacity` with its output rate (`systems/modes.yaml`
0.3.0).

## Recheck after #12 and #14 (#42)

[[ai gen]] 2026-10-25. The METR (#12) and AI Futures (#14) replications have landed. This section
rechecks the bridge against them. Result: **no link from time horizon to developer time to research output is
identified.** Each link stays unidentified, uncoupled and unused, so the toy's coding speed lam stays a
bounded scenario. A link would count as identified only with an evidence record and a stated conversion.

**Native units.** Every adapter quantity of `AD-METR` and `AD-AIFM` in `systems/modes.yaml` now has a
dictionary entry in the replication's own unit:

| adapter quantity | dictionary | unit | evidence status |
|---|---|---|---|
| METR 50% / 80% task time horizon | QTY-METR-HORIZON, QTY-METR-HORIZON-P80 | min (human expert minutes, METR's file; the contract writes human-hours) | observed_primary (`EV-METR-TH*`) |
| METR realized developer task time ratio | QTY-DEV-TIME-RATIO | 1 (time with AI / without; above 1 is a slowdown) | observed_secondary (`EV-METR-RCT-2025`, a blog report; paper not read) |
| AIFM progress | QTY-AIFM-PROGRESS (was QTY-AIFM-ECI) | OOM: log10 of cumulative effective FLOP at 2025.13 efficiency | source_model_output |
| AIFM software efficiency | QTY-SOFTWARE-EFFICIENCY | OOM (was a multiplier); SE = 0 at 2025.13 | source_model_output |
| AIFM research output (rate of SE) | QTY-RESEARCH-OUTPUT | OOM/yr (was ln/yr); 1 OOM/yr = ln 10 /yr | source_model_assumption (calibrated to 1 OOM/yr at 2024) |
| AIFM milestones | QTY-AIFM-MILESTONE | yr (decimal year) | source_model_output |
| AIFM automation fraction, AI research taste | QTY-AIFM-AUTOMATION-FRACTION, QTY-AIFM-AI-TASTE | 1 (fraction of coding tasks; SDs of the human taste distribution) | source_model_output |
| AIFM human coding labor | QTY-AIFM-HUMAN-CODING-LABOR | FTE (own bookkeeping dimension; no hours per FTE stated) | source_model_assumption |
| AIFM inference compute, training capacity | QTY-AIFM-INFERENCE-COMPUTE, QTY-AIFM-TRAINING-CAPACITY | H100e = 4e14 FLOP/s (AIFM's convention: nameplate times 0.4) | source_model_assumption |

The last three are named in the dictionary but not linked by `adapter_quantity`: they book to stock or flow
ledgers, and the stock/flow rule needs the contract quantity to declare its kind, which `AD-AIFM` does not yet
do. The AIFM conventions are in `EV-UNITS-AIFM-CONVENTIONS`, read from the code at `1c40ecdb`.

**The links.**

| link | status | why |
|---|---|---|
| horizon to developer time (`CV-HORIZON-TO-DEV-TIME`) | unidentified | One usable paired point: the 2025 RCT measured a ratio of 1.19 (CI 1.02 to 1.39) while the models used had TH1.0 p50 of 29 and 59 minutes (as published 2025-03-19). One point gives no slope, and the sign runs against the naive reading. The 2026 follow-up is unreliable by METR's own account (selection, concurrency). The task populations differ: 38% of agent PRs passed tests, none was mergeable as-is (`EV-METR-ALGO-2025`). The horizon trend itself has holdout verdict "not established" (#12). |
| developer time to research output (`CV-DEV-TIME-TO-RESEARCH`) | unidentified | AIFM gives a form, not an estimate: CES of human and AI coding labor, then CES with experiment compute, times taste, into a research stock, SE = r log10(RS/RS_0). Its parameters are elicited or calibrated. Feedback on and off differ by under 0.1 OOM before 2026, so history cannot tell them apart (#14). Its input is a serial labor multiplier of one project, not a developer's time ratio, and neither source converts one to the other. There is no review or integration stage, and the repository holds no observation of research output. |
| inference compute to agent labor (`CV-INFERENCE-TO-AGENT-LABOR`) | unidentified | AIFM maps inference H100e straight to AI coding labor with an elicited efficiency slope, never through agent-hours. |
| AIFM FTE to person-hours (`CV-AIFM-FTE-TO-PERSON-HOURS`, new) | unidentified | No hours per FTE are stated. Nothing needs the factor, so none is set. |
| AIFM progress to effective FLOP (`CV-OOM-TO-FLOP`) | unidentified | The reference is now known (1 FLOP at 2025.13 efficiency), but logE is cumulative over all training capacity and QTY-EFFECTIVE-COMPUTE is one run. Mapping one to the other needs a run-length assumption. |
| METR p80 to AIFM progress (`CV-NO-HORIZON-TO-AIFM-PROGRESS`, new) | forbidden | AIFM's present horizon level is fitted to METR's p80. Feeding METR back in would count the same observation twice. |

AIFM's elicited serial coding uplift (2.0 at 2026.578; 80% range 1.25 to 5) and METR's measured ratio of 1.19
(a 0.84x speed) describe different things at different dates: a project-level serial labor multiplier in
mid-2026, and the issue time of experienced developers in early 2025. They are recorded side by side. Neither
is a check on the other.

**Contract changes this recheck would suggest** (not made here; `systems/modes.yaml` belongs to #61/#47/#35):
`AD-METR` horizons in minutes, METR's unit; `kind` on the three AIFM input quantities, so they can be linked
by `adapter_quantity`; and booking AIFM's software efficiency, a level in OOMs, to a state, with its rate
(OOM/yr) booked to `research_output`, a flow. Today the level is booked to the flow.

## Box 5: four things kept apart

| concept | what it is | contract element | example |
|---|---|---|---|
| CL-BASIC-CHIPS | the industry makes chips for its own machines, any node | `dependencies` (chips for industrial control) | Metzger Gen 5.0, about 1.6e-6 EIU |
| CL-LEADING-EDGE-FAB | leading-edge chips with no Earth input | `dependencies` (leading-edge compute) | the solver's A_close = 0.1 EIU, about 6e4 times larger |
| CL-RESOURCE-OWNERSHIP | who holds energy, materials, capital, compute | `external_resources`, holder shares | the solver's A; trace `holders` |
| CL-EFFECTIVE-SOVEREIGNTY | a derived view, not a quantity | `MODE-SOVEREIGN` | needs objective selection and control as well; "complete material independence" is under its `not_implied` |

None implies another. The solver merges the first two (one threshold, with chi0 below it) and treats
the third as given; the toy below keeps basic and leading-edge chips separate.

## Box 4 and 6: the coupling toy

One-year steps; capital K, energy capacity E and compute C are each measured in the EIU of output
they support. Output is nu min(K, E, (1 - phi) C). New capacity needs investment (s Y), design and
integration throughput D = D_h + lam phi C (the only place coding speed lam enters), and, for each
factor, its own physical cap: energy deployment rate r_E and resource E_max, chip supply from an import
quota, basic local chips once K passes a small threshold, and unlimited chips after leading-edge
closure. With every cap slack the toy equals the solver's growth law with chi = 1 (an exact reduction,
used as a check). Results (`results/coupling_toy.md`):

- **Limiting case (box 6).** With energy deployment capped at 10%/yr, output grows at ln 1.1 = 0.095/yr
  for lam = 2, 8 or 64; the paths are identical. The same holds under a chip import quota and under an
  energy resource cap. Faster coding raises growth only while design throughput binds (lam below
  lam* = 5.45/yr in this parameterization), and only up to the next physical cap.
- **chi0 is not a constant.** Under a fixed chip quota the growth rate falls from 0.067/yr in the first
  five years to 0.020/yr in the last five (chi_eff 0.19 to 0.06), because compute then grows linearly.
  The solver's constant chi0 = 0.15 is a different mechanism. Basic local chips at Metzger scale lift
  the late rate to 0.079/yr long before leading-edge closure.
- None of these numbers is an estimate; the toy shows which couplings can matter and which cannot.

## Findings

- **F1. The g citation was wrong, and g is not a source-model value.** Fixed: PARAMS basis text,
  register role (`source_model_assumption` to `project_assumption`), `AS-GCITE` note, evidence record.
  See `metzger/RECHECK.md`.
- **F2. The solver's A is a stock, but the contract books it as a flow.** `AD-PACT` mapped "AI capacity A"
  to `industrial_output`; the solver uses A as capacity (growth, the prize) and its output as a flow
  (payoff, trade per year). The implicit factor is one EIU of output per EIU of capacity per year
  (`CV-CAPACITY-TO-OUTPUT`). *Resolved in #39:* A is booked to `industrial_capacity` (a stock) with an
  explicit output rate, and both checkers enforce the distinction.
- **F3. The EIU has no single definition.** The solver says "Earth's industry"; the Metzger docking
  reads it as world primary energy (19.6 TW); a GDP bridge to GATE's output would read it as world
  output. These differ in what they count. *Resolved in #39:* `DEF-EIU` (section above);
  `CV-GWP-TO-EIU-OUTPUT` is now a measured, uncoupled scale estimate.
- **F4. No identified path from coding capability to industrial growth exists in the repository.**
  Horizon to developer time, developer time to research output, and inference compute to agent labor
  are all unidentified. *Rechecked in #42 after #12 and #14 landed:* still unidentified, with the
  reasons in "Recheck after #12 and #14". The toy's lam is therefore a bounded scenario and the toy is not
  coupled to the solver.
- **F5. One loop, one owner.** epoch-gate/INTERFACES.md requires that compute investment and
  software efficiency each have a single owning model when GATE and AI Futures are coupled. The
  dictionary keeps both eFLOP quantities relative to their own base (`QTY-EFFECTIVE-COMPUTE` note).

## Not done in this milestone

- World energy is still read from secondary summaries. World GDP is read in primary form (#39), but only
  as a scale at the reference year; no projected path is converted to capacity.
- No version of record of Metzger et al. was compared (publisher page blocked).
- The toy is not run through the pact solver, and its bottleneck parameters are not tied to physical
  data (e.g. radiator mass, launch cadence in `physics_economics.md`).
- METR and AIFM units were rechecked in #42 (section above). Three AIFM input quantities are not linked by
  `adapter_quantity` until the contract declares their kind. The contract's METR horizon unit (human-hours)
  and its booking of AIFM software efficiency (a level, booked to a flow) are left for the contract's owners.
  `make units-check` fails on any unit or name change in `systems/modes.yaml`.
