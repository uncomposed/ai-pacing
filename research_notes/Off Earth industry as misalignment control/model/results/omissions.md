# Omission matrix (issue #9)

[[ai gen]] Generated from `omissions.yaml` by `python3 tools/omissions_tool.py render`; `make check` fails if this file is stale. The YAML is authoritative. Statuses: `implemented_tested` (a bounded variant exists and is tested), `excluded_scoped` (left out, with the claim scope narrowed), `unresolved` (not tested; the dependent claim is narrowed). No entry is empirical validation.

## Summary

| ID | omission | status | assumptions | conclusions it could change |
|---|---|---|---|---|
| OM-RENEG-UP | Upward renegotiation: humans may raise the AI's terms (pay from their own industry) to buy off a strike | implemented_tested | AS-FIXEDTERMS | AR-H1, AR-H8, Q13 |
| OM-RENEG-DOWN | Downward renegotiation without commitment: humans squeeze the AI as they get stronger | implemented_tested | AS-NOEXPLOIT, AS-FIXEDTERMS | AR-H12, AR-H8, D18, Q13 |
| OM-HUMAN-FIRST | Human preventive action: humans may try to shut down (or cut off) a cooperating AI | implemented_tested | AS-NOFIRSTSTRIKE | AR-H1, AR-H8, AR-H9, D18, Q13 |
| OM-LEARNING | Human learning after a failed strike (D18 check carried over from #3) | implemented_tested | AS-CRACKDOWN, AS-FREERETRY | AR-H11, AR-H13, D18, H10 |
| OM-TIGHTEN | Improving human control over time (caught excursions by other systems tighten the regime) | implemented_tested | AS-NOEXPLOIT, AS-TESTSWITCHES | AR-H12, AR-H3, D18, H10 |
| OM-DEFENSIVE-ASSETS | Defensive human assets (defended capacity, an aligned AI on the human side) | unresolved | AS-NOALLY, AS-DENIAL | AR-H5, AR-H7, AR-H8 |
| OM-HETEROGENEITY | State heterogeneity and asymmetric state power | unresolved | AS-STATES | AR-H4, AR-H8 |
| OM-PRIVATE-INFO | Private information (AI type, state programmes, strike odds) | unresolved | AS-COMPLETEINFO | AR-H1, AR-H8, AR-H11 |
| OM-SELECTION-STAGE | Alternative equilibrium selection in the states' stage game (human-worst instead of human-best) | implemented_tested | AS-SELECTION | AR-H1, AR-H8 |
| OM-SELECTION-STRATEGIES | Non-Markov strategies (triggers, reputation) and multiple equilibria of the whole game | unresolved | AS-SELECTION, AS-REPUTATION | AR-H1, AR-H8, Q13 |
| OM-AI-OBJECTIVE | Alternative AI objectives and beliefs (goal uncertainty, risk aversion, incoherence, value on humans) | unresolved | AS-COHERENT-EU, AS-POWERSEEK, AS-DISCOUNT | AR-H1, AR-H6, AR-H9, AR-H11 |
| OM-POST-RIVAL | Post-rival dynamics (a rival's birth is a terminal reduced form) | unresolved | AS-RIVAL-HOLDS, AS-ELLINF, AS-RATIO | AR-H5, AR-H10, AR-H8 |
| OM-MULTI-AGENT | Multiple agents and coalitions (copies, swarms, several AIs) | unresolved | AS-SINGLE-AI, AS-NOALLY | AR-H1, AR-H9, AR-H10, AR-H11, D18 |
| OM-LAB-SYSTEMS | Sovereign-capable systems inside labs (before the solver's t = 0) | excluded_scoped | AS-A0, AS-SINGLE-AI | AR-H1, AR-H9, D18, Q13 |

## Findings and narrowed claims

### OM-RENEG-UP: Upward renegotiation: humans may raise the AI's terms (pay from their own industry) to buy off a strike

- **Status:** `implemented_tested`. Issue items: renegotiation_up.
- **Variant:** `variants/bargaining.py`; results `results/variants/bargaining.json`, `results/variants/tables.md`; tests `tests/test_variants.py::Bargaining::test_fixed_terms_is_the_baseline_recursion`, `tests/test_variants.py::Bargaining::test_renegotiation_buys_off_prize_only_strikes`, `tests/test_variants.py::Bargaining::test_no_bargain_when_harvest_dominates`.
- **Finding:** In the reduced saturation game (fixed regime = the baseline recursion, strike year 165 with the eroding reserve), upward renegotiation removes the prize-only strikes: eroding reserve (fixed terms strike at year 165) and no reserve (strike at year 0) both stay at peace, at a transfer of 0.27 and 0.39 a year against a pie of 1.5. It does nothing for the harvest world, where no bargain exists (AI lock-in 500 a year). Confirms docking.md 5 items 1 and 2 in an executable game.
- **Narrowed claim:** Strikes driven only by the prize (S6, denial erosion) are conclusions about fixed pact terms, not about the pact's feasibility; any statement that the reserve or its erosion 'breaks the pact' holds only under AS-FIXEDTERMS. Threat- and harvest-driven strikes are unaffected.

### OM-RENEG-DOWN: Downward renegotiation without commitment: humans squeeze the AI as they get stronger

- **Status:** `implemented_tested`. Issue items: renegotiation_down.
- **Variant:** `variants/bargaining.py`; results `results/variants/bargaining.json`, `results/variants/tables.md`; tests `tests/test_variants.py::Bargaining::test_existence_versus_credible_implementation`.
- **Finding:** Closing-window world (the reserve upgrades from q 0.45 to 0.9 in year 20): a bargain exists in every year (surplus at least 1.39 a year), yet with renegotiation and no commitment the AI strikes preventively in year 19 and human welfare falls from 45.7 (fixed terms) to 20.4. Fixed terms and a committed constant transfer (0.115 a year, welfare 46.9) both keep the peace. So existence of a bargain and its credible implementation come apart exactly when human strength jumps (commitment gap 4.1 a year in year 19). With a slowly eroding reserve the sign reverses: two-sided renegotiation keeps the peace and raises human welfare (50.5 against 45.4).
- **Narrowed claim:** AR-H12 ('a closing window never pulls an AI strike earlier') holds only while humans do not exploit their rising strength (AS-NOEXPLOIT) or can commit to terms; under renegotiation without commitment a fast enough rise in human control produces a preventive AI strike. D18's valence stays unresolved and now has a stated condition. Whether renegotiation helps humans reverses with the direction of the power shift.

### OM-HUMAN-FIRST: Human preventive action: humans may try to shut down (or cut off) a cooperating AI

- **Status:** `implemented_tested`. Issue items: human_preventive_action, d18_humans_strike_first.
- **Variant:** `variants/preventive.py`; results `results/variants/preventive.json`, `results/variants/tables.md`; tests `tests/test_variants.py::ReducedGame::test_r6c_cell_matches_full_solver`, `tests/test_variants.py::ReducedGame::test_saturated_start_matches_closed_form`, `tests/test_variants.py::ReducedGame::test_switches_off_are_identities`, `tests/test_variants.py::ReducedGame::test_reproduces_committed_json`.
- **Finding:** Reduced bootstrap game (baseline limit matches the full solver's R6c brackets in 4 of 5 cells and the saturation closed form). Where the pact holds, humans never use the option and nothing changes. Where the AI would strike at closure (weak reserve), humans strike first at year 0 (success 0.3): conflict moves from year 15.5 to year 0, P(seizure) falls from 1 to 0.35 and human welfare rises (13.2 to 22.0). Where the AI would strike late to harvest Earth (year 79), the same option makes humans strike at year 0 and lowers their welfare (36.6 to 22.0): they cannot commit not to use it while their window closes. Where early failure is survivable or retries are free, the option deters the AI entirely (P(strike) 1 to 0) and is never used. An option to end the pact (cut chips) without any shutdown capability makes the AI strike at year 0 instead of at closure.
- **Narrowed claim:** AR-H9 ('the AI waits during the bootstrap') holds only when humans have no preventive option or the AI would not strike anyway; a human option to end the pact or shut the AI down can move a closure-time strike to year 0. The effect of human preventive capability on human welfare has no fixed sign: it reverses between AIs that would strike soon and AIs that would strike late. AR-H1 at the baseline is unaffected in this reduced game.

### OM-LEARNING: Human learning after a failed strike (D18 check carried over from #3)

- **Status:** `implemented_tested`. Issue items: d18_learning_after_failed_strike.
- **Variant:** `variants/preventive.py`; results `results/variants/preventive.json`, `results/variants/tables.md`; tests `tests/test_variants.py::ReducedGame::test_reproduces_committed_json`, `tests/test_variants.py::ReducedGame::test_switches_off_are_identities`.
- **Finding:** After a failed strike humans raise the reserve's firing probability and their shutdown odds by one level. In no structure did this pull a strike earlier or start a 'strike now' spiral: strike timing and the first strike's probability are unchanged, because learning acts only after a failure. It lowers P(seizure) where a failed AI survives to retry (1 to 0.81 with a weak reserve, 1 to 0.71 with survivable early failure) and does nothing where the first strike is fatal or decisive. Failed strikes still come paired with eventual seizures.
- **Narrowed claim:** Learning after a failed strike is a damage limiter on retries, not a deterrent of the first strike, in this model; it supports AR-H13's 'options acting only after a failed strike change little' and gives no support to a warning-shot benefit of D18. H10's deterrence channel (others' excursions tightening the regime) is the separate OM-TIGHTEN entry.

### OM-TIGHTEN: Improving human control over time (caught excursions by other systems tighten the regime)

- **Status:** `implemented_tested`. Issue items: improving_human_control.
- **Variant:** `variants/preventive.py`; results `results/variants/preventive.json`, `results/variants/tables.md`; tests `tests/test_variants.py::ReducedGame::test_switches_off_are_identities`, `tests/test_variants.py::ReducedGame::test_reproduces_committed_json`.
- **Finding:** An exogenous tightening hazard (5 % a year; each step raises q and shutdown odds by 0.2) removes strikes without pulling them earlier in the reduced bootstrap game (P(strike) 1 to 0.64 with a weak reserve and 1 to 0.46 with survivable early failure; conditional strike year 15.5 to 15.4). It changes nothing where the AI strikes at year 0 or harvests late. With fixed terms this agrees with AR-H12; under downward renegotiation without commitment (OM-RENEG-DOWN) the same improvement produces a preventive strike.
- **Narrowed claim:** 'Improving human control stabilises' is conditional: true here with fixed terms and with control acting on the reserve; reversed when improving control lets humans cut the AI's terms without commitment. No unconditional sign is claimed.

### OM-DEFENSIVE-ASSETS: Defensive human assets (defended capacity, an aligned AI on the human side)

- **Status:** `unresolved`. Issue items: defensive_human_assets.
- **Design note:** `variants/actor_structures.yaml` AST-ALIGNED-ALLY.
- **Next step:** Make Earth's defence D a state that a human-controlled defender raises over time (contract entity with host STATE), with its own control failures, and rerun the R6 needed-q grid. Only D multipliers exist today (robust design levers), which is a parameter, not an actor.
- **Finding:** Not tested. Defence enters only as the fixed parameter D (and the D_mult design lever).
- **Narrowed claim:** AR-H7 ('early security needs near-total unplugging') and AR-H5 are statements about a pact with a demilitarised Earth and no human-aligned AI; they say nothing about pacts with defended human assets.

### OM-HETEROGENEITY: State heterogeneity and asymmetric state power

- **Status:** `unresolved`. Issue items: state_heterogeneity.
- **Design note:** `variants/actor_structures.yaml` AST-HETEROGENEOUS-STATES.
- **Next step:** Two-state solver run with unequal B_R and welfare shares (the stage game already enumerates per-state actions); report the per-state welfare split as the distributional measure the reduced games cannot give.
- **Finding:** Not tested. The reduced games use one aggregate human actor, so they report AI-versus-humans distribution only.
- **Narrowed claim:** AR-H4's threshold (private gain below about 8 years of welfare) is for N = 2 symmetric states; no claim about which state gains or loses under any variant is made.

### OM-PRIVATE-INFO: Private information (AI type, state programmes, strike odds)

- **Status:** `unresolved`. Issue items: private_information.
- **Next step:** Two-type AI (striker or cooperator) with a human belief updated by observed behaviour in the reduced bootstrap game; test whether screening by a shutdown threat separates types or pools them.
- **Finding:** Not tested beyond the misjudged-odds test (pf_bel), in which humans still know the AI's type.
- **Narrowed claim:** All equilibrium claims assume common knowledge of types; signalling and screening are outside them.

### OM-SELECTION-STAGE: Alternative equilibrium selection in the states' stage game (human-worst instead of human-best)

- **Status:** `implemented_tested`. Issue items: equilibrium_selection.
- **Variant:** `variants/run_variants.py`; results `results/variants/selection.json`, `results/variants/tables.md`; tests `tests/test_variants.py::Selection::test_best_selection_reproduces_round1`.
- **Finding:** Full solver, 25 named scenarios, selection 'worst' (an existing solver option): S1 baseline and every scenario that cooperated with no likely rival are unchanged. Three scenarios flip from cooperate to strike now: S4 (never dismantle), S14 (rival stays dangerous, survivable seizure) and S16 (harvest). In each, the human-best equilibrium was one where a rival AI was likely (P(rival) 0.95, 0.16, 0.66).
- **Narrowed claim:** AR-H1 is robust to stage-game selection at the baseline. Outcomes in worlds where cooperation coexists with a likely rival depend on the states coordinating on the human-best equilibrium and are stated conditionally.

### OM-SELECTION-STRATEGIES: Non-Markov strategies (triggers, reputation) and multiple equilibria of the whole game

- **Status:** `unresolved`. Issue items: equilibrium_selection.
- **Next step:** Grim-trigger check in the reduced saturation game: is peace sustainable by punishment where the Markov equilibrium strikes (eroding reserve, fixed terms)? Small and analytical; not done in this pass.
- **Finding:** Not tested. All results are Markov perfect equilibria with ties broken toward peace.
- **Narrowed claim:** Every result is conditional on Markov strategies; 'no equilibrium with peace' is never claimed.

### OM-AI-OBJECTIVE: Alternative AI objectives and beliefs (goal uncertainty, risk aversion, incoherence, value on humans)

- **Status:** `unresolved`. Issue items: ai_objective_beliefs.
- **Next step:** The cheapest discriminating run is goal uncertainty in the reduced saturation game (an AI that values oversight with some probability, Clark 4.5); eta, omega and pf_bel are already swept in the full solver.
- **Finding:** Partly covered by existing sweeps (eta, omega, pf_bel); goal uncertainty and incoherence are not represented.
- **Narrowed claim:** Results are for a coherent, risk-neutral (eta 0 baseline) expected-utility maximiser with correct beliefs except where pf_bel is varied.

### OM-POST-RIVAL: Post-rival dynamics (a rival's birth is a terminal reduced form)

- **Status:** `unresolved`. Issue items: post_rival_dynamics.
- **Design note:** `variants/actor_structures.yaml` AST-RIVAL-AIS.
- **Next step:** Replace the terminal rival payoff with a continuation game between two AIs (contract entities, no merged capacity), starting with a two-AI saturation bargaining game built on variants/bargaining.py.
- **Finding:** Not tested. The selection check shows several holds rest on equilibria with a likely rival.
- **Narrowed claim:** 'The pact holds' counts only AI strikes (AS-RIVAL-HOLDS); nothing is claimed about what happens after a rival exists.

### OM-MULTI-AGENT: Multiple agents and coalitions (copies, swarms, several AIs)

- **Status:** `unresolved`. Issue items: multi_agent_coalitions.
- **Design note:** `variants/actor_structures.yaml` AST-COPIES.
- **Next step:** Implement AST-COPIES in the reduced bootstrap game: n parallel attempts with correlated success and a per-copy kill rule, with capability shared by the weights and never summed. Scaling A is ruled out (AD-PACT unsupported extrapolation).
- **Finding:** Not tested. A design note maps the structures onto the mode contract (variants/actor_structures.yaml).
- **Narrowed claim:** All results are for one AI. The 'failed early strike is fatal' logic behind AR-H9 assumes a single key; it is not claimed for collectives.

### OM-LAB-SYSTEMS: Sovereign-capable systems inside labs (before the solver's t = 0)

- **Status:** `excluded_scoped`. Issue items: sovereign_capable_lab_systems.
- **Design note:** `variants/actor_structures.yaml` AST-LAB-CAPABLE.
- **Reason:** The solver has no lab, no development phase and no custody; the mode contract marks AD-PACT unsupported for MODE-HUMAN-LAB and MODE-SOVEREIGN-CAPABLE. Representing lab systems needs the development adapters (#13, #14), not a variant of this game.
- **Scope:** Conclusions apply only downstream of T-AUTHORIZED-AUTONOMY or T-LOSS-OF-CONTROL, to a partial MODE-SOVEREIGN entity with critical chip dependence until closure.
- **Finding:** Excluded by scope; the design note records what a variant would need.
- **Narrowed claim:** No result here transfers to systems still hosted by a lab; D18 and Q13 evidence from this model concerns a post-autonomy AI only.

## Variant selection

| variant | chosen | discriminates | reason |
|---|---|---|---|
| variants/bargaining.py | yes | Fixed-terms artefact versus commitment problem versus empty bargaining range (AR-H8, AR-H12, D18, Q13) | Saturation is where docking.md 5 computed Powell's terms from model quantities, so a one-dimensional time recursion whose fixed regime is exactly the baseline recursion can test renegotiation in both directions in under a second. Five worlds were chosen to span the three bargaining cases (existing and credible, existing but not credible, absent). |
| variants/preventive.py | yes | Whether a human first strike, learning or tightening stabilises or destabilises (D18, AR-H9, AR-H12, AR-H13) | The bootstrap is where humans are the declining side (Powell's preventive-war case). A stripped copy of the baseline game in its no-rival limit keeps the strike terms and growth, docks to the solver's R6c brackets, and adds one human move and one control state. Six structures differ in what the AI would do without the new options (hold, strike at closure, strike at year 0, strike late), which is what decides the sign. |
| variants/run_variants.py | yes | Whether conclusions depend on the human-best stage-equilibrium selection (AR-H1, AR-H8) | An existing solver option (sel='worst'); no code change; about 7 minutes on the 25 named scenarios. |
| human move inside equilibrium_model.solve | no | Same as variants/preventive.py, with rivals and states | Deferred: #9's rule is to select bounded variants before expanding the full solver, and the reduced game already shows the sign of the effect depends on structure. Worth doing for the structures where the sign matters. |
| two-AI solver | no | Coalitions and post-rival dynamics | Needs the actor-structure design (variants/actor_structures.yaml) agreed first; too large for this pass. |
| Bayesian stage game | no | Private information | Large change to the stage game; the reduced two-type game (OM-PRIVATE-INFO next step) comes first. |
| ensemble over structures | no | none | #9's stopping rule: keep conditional conclusions rather than average over invented model probabilities. |

## Actor structures through the mode contract (design only)

| ID | structure | entities (kind) | transitions | omission |
|---|---|---|---|---|
| AST-BASELINE | One sovereign AI, unitary symmetric states (the solver as it is) | AI (agent_instance), STATE-1 (state), STATE-2 (state) | T-DEGRADATION, T-RECOVERY, T-COMMITMENT-LAPSE, T-RECONTAIN |  |
| AST-COPIES | Many running copies of one set of weights (a swarm), coordinating | WEIGHTS (model_weights), SWARM (agent_collective) | T-LOSS-OF-CONTROL, T-DEGRADATION, T-RECONTAIN | OM-MULTI-AGENT |
| AST-RIVAL-AIS | Several AIs with different weights and goals (possible AI coalitions) | AI-1 (agent_instance), AI-2 (agent_instance) | T-NEGOTIATED-CONSTRAINT, T-COMMITMENT-LAPSE, T-DEGRADATION | OM-POST-RIVAL |
| AST-ALIGNED-ALLY | A human-aligned AI defending humans (defensive human asset) | AI (agent_instance), DEFENDER (agent_instance), STATE-1 (state) | T-DELEGATE, T-RESTRICT, T-RECONTAIN | OM-DEFENSIVE-ASSETS |
| AST-LAB-CAPABLE | A sovereign-capable system still inside a lab (before the solver's t = 0) | LAB (lab), SYS (agent_instance) | T-DELEGATE, T-RESTRICT, T-LOSS-OF-CONTROL, T-AUTHORIZED-AUTONOMY | OM-LAB-SYSTEMS |
| AST-HETEROGENEOUS-STATES | Asymmetric states with private information about their programmes | AI (agent_instance), STATE-BIG (state), STATE-SMALL (state) | T-COMMITMENT-LAPSE | OM-HETEROGENEITY |
