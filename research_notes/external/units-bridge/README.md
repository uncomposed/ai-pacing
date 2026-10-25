# Units and evidence bridging AI research progress to industrial growth and chip autonomy (#11)

[[ai gen]] 2026-10-25. Status: first milestone. Machinery, an audit and a toy; nothing here is
empirical validation, and nothing is coupled into the pact solver.

| kind of result | status |
|---|---|
| Source replication | Metzger Fig. 2 re-digitized from the arXiv manuscript's raster; rates reproduce the docking's within 0.01/yr. No other source model is replicated here (METR, GATE and AI Futures belong to #12, #13, #14). |
| Numerical correctness | Every declared conversion and 17 equations pass a dimensional check; derived factors are recomputed; the toy reduces to the solver's unchanged growth law (relative 2e-12). |
| Empirical validation | None. No conversion is fitted to data. The one measured scale (world primary energy) is read only in secondary summaries. |

## Files

| file | what |
|---|---|
| `quantities.yaml` | Quantity dictionary: units, dimensions, observables, mode-contract mapping, evidence status. Covers capability metrics, research labor and output, software efficiency, training and inference compute, energy, physical capital and output, supply-chain closure, external control. Also the four closure and sovereignty concepts (box 5). |
| `conversions.yaml` | Every cross-model conversion: units, form, mechanism, delay, constraints, evidence status, coupled or not. Classes separate normalizations and identities from empirical scale estimates, bounded scenarios, unidentified links and forbidden ones. |
| `equations.yaml` | The solver's growth law, the Metzger energy bridge and the toy's equations, with symbol units, for the dimensional check. |
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
- **F2. The solver's A is a stock, but the contract books it as a flow.** `AD-PACT` maps "AI capacity A"
  to `industrial_output`; the solver uses A as capacity (growth) and as a flow (trade per year, the
  prize). The implicit factor is one EIU of output per EIU of capacity per year
  (`CV-CAPACITY-TO-OUTPUT`). Proposed: state it in the contract or book A to a capital stock.
- **F3. The EIU has no single definition.** The solver says "Earth's industry"; the Metzger docking
  reads it as world primary energy (19.6 TW); a GDP bridge to GATE's output would read it as world
  output. These differ in what they count. `CV-GWP-TO-EIU-OUTPUT` stays unidentified until one is chosen.
- **F4. No identified path from coding capability to industrial growth exists in the repository.**
  Horizon to developer time, developer time to research output, and inference compute to agent labor
  are all unidentified (#12, #14). The toy's lam is therefore a bounded scenario and the toy is not
  coupled to the solver.
- **F5. One loop, one owner.** epoch-gate/INTERFACES.md requires that compute investment and
  software efficiency each have a single owning model when GATE and AI Futures are coupled. The
  dictionary keeps both eFLOP quantities relative to their own base (`QTY-EFFECTIVE-COMPUTE` note).

## Not done in this milestone

- No empirical scale estimate is read in primary form (world energy comes from secondary summaries).
- No version of record of Metzger et al. was compared (publisher page blocked).
- The toy is not run through the pact solver, and its bottleneck parameters are not tied to physical
  data (e.g. radiator mass, launch cadence in `physics_economics.md`).
- Adapter quantities for METR (#12) and AI Futures (#14) still cite the contract's README-level
  entries; when those replications land, their units must be rechecked here (`make units-check` fails on
  any unit or name change in `systems/modes.yaml`).
