# Overlap with GATE (#13): avoiding double counting

[[ai gen]] Written 2026-10-25. The AIFM side is read from the code at commit `1c40ecdb`
and the runs in `results/`. The GATE side comes from #13's replication
(`../epoch-gate/`, especially `INTERFACES.md` and `MODES.md`). Nothing here has been run
as a coupled model. The coupling itself is issue #35; this note only fixes the AIFM side
of the five loops that `../epoch-gate/INTERFACES.md` names, under the same names and in
the same order, so #35 can pair them.

## The two models in one table

| | AIFM (pinned, run here) | GATE (per #13) |
|---|---|---|
| who allocates | nobody: labor and compute are exogenous forecasts | a social planner maximising household utility |
| compute | input series in H100e (training, inference, experiment), exogenous | endogenous stock Q (FLOP/year) funded from output |
| software efficiency | endogenous: `SE = r_software log10(RS/RS_0)`, research stock driven by AI-augmented research effort | endogenous S(t) driven by R&D *spending* |
| research automation | the core loop: coding automation and AI research taste raise research effort | none: AI raises output through digital workers in production; R&D is funded in dollars |
| capability scale | cumulative effective compute `logE` (OOMs); milestones are thresholds on it or on taste | largest training run in eFLOP; task coverage f with a full-automation threshold |
| labor | human coding FTEs; AI coding labor derived internally from inference compute | human workers; digital workers derived from runtime compute |

## The five loops, from the AIFM side

### 1. Compute investment feedback

AIFM has **no** compute-investment loop: `training_H100e`, `inference_H100e` and
`experiment_H100e` are read from `inputs/input_data.csv` and never respond to anything
the model computes (`progress_rate.py`, `progress_model/README.md` "Modeling
assumptions"). The forecasts already embed someone's investment beliefs. So the risk is
not two live loops but *one live loop plus a forecast that already contains its
answer*: using GATE's endogenous compute and AIFM's series together counts compute growth
twice. If GATE owns this loop, AIFM's three compute series must be *replaced* by GATE's
(after resolving GATE's training/runtime units, INTERFACES.md E7, and splitting out an
experiment-compute share GATE does not have), not multiplied by them.

### 2. Software efficiency

Both models make it endogenous, through different drivers (AIFM: research effort with AI
automation and taste; GATE: R&D spending). Applying `10^SE` from AIFM and S from GATE to
the same effective-compute number counts the same algorithmic progress twice. One model
owns software efficiency in a coupled run; the other takes it as an input with its own
loop switched off. AIFM's `SE` is display-rebased to zero at 2025.13
(`TRAINING_COMPUTE_REFERENCE_YEAR`), GATE's S to 1 at the start of 2025: a re-basing is
needed even for a comparison run.

### 3. Automation of research (research automation vs R&D spending)

This is AIFM's central mechanism and absent from GATE. The double count arises if AIFM's
research speed-up is fed into GATE as faster S (or H) growth *and* GATE's extra output is
also spent on R&D: the same acceleration then enters once as automated research labor and
once as spending. `results/feedback_off.json` gives the size of AIFM's channel at default
parameters: switching it off moves ASI from 2028.9 to 2036.4 at the same progress level
and AC from 2027.8 to 2028.1, so most of AIFM's near-term path is the exogenous compute
forecast (loop 1), and most of its takeoff compression is this loop.

### 4. Effective-compute milestones vs task coverage (capability milestones)

AIFM maps cumulative effective compute to automation fraction, research taste and
milestones (AC, SAR, TED-AI, ASI). GATE maps effective compute to task coverage with a
full-automation threshold. They are rival mappings of the same capability assumption.
Using one model's milestone dates to set the other's capability state counts the
assumption twice. Note that AIFM's scale is *cumulative* effective compute (a stock);
GATE's largest training run is a single run. A bridge must say which, and integrate
rather than equate (#11). Treat the two as alternatives and compare.

### 5. Digital workers vs agent labor

AIFM derives AI coding labor from its inference-compute input and never takes agent
labor as an input (corrected `AD-AIFM` entry: inputs `human_labor`, `compute_inference`,
`compute_training`). GATE derives digital workers from runtime compute. Adding AIFM's AI
coding labor to GATE's production, or GATE's digital workers to AIFM's research, counts
the same inference compute twice; the contract's `derived_from` rule rejects it once both
are declared as inputs of one adapter.

## Ownership if the two are coupled (for #35)

| loop | owner | the other model |
|---|---|---|
| 1 compute investment | GATE, if a macro budget is wanted; otherwise AIFM's forecast | takes the compute path as input |
| 2 software efficiency | AIFM, if AI-research feedback is wanted | takes the efficiency multiplier as input, own loop off |
| 3 research automation | AIFM (GATE has none) | GATE's R&D spending must not also be accelerated by it |
| 4 capability mapping | neither: compare as rivals | |
| 5 AI labor | the model that owns the inference/runtime compute it is derived from | never both |

This matches the rule in `../epoch-gate/INTERFACES.md`. The AIFM facts above replace that
file's README-level statements about AI Futures; INTERFACES.md itself is not edited here.

## Experiment compute

AIFM's experiment compute (10x inference compute in the default series) has no
counterpart in GATE and no accounting quantity in the mode contract. Any GATE-to-AIFM
compute bridge must say where it comes from.
