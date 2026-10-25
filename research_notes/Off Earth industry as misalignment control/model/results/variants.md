# Strategic omissions: bargaining, human preventive action, actor structures (issue #9)

[[ai gen]] Written 2026-10-25 by a Claude session (branch `claude/strategic-omissions`). Code: `model/variants/`.
Numbers: `results/variants/tables.md` (generated) and `results/variants/*.json`. Matrix: `omissions.yaml`, rendered as
`results/omissions.md`.

**Status.** First milestone. `implemented` throughout; the reduced games' baseline limits are `verified` against the
full solver and its closed forms (section 1). Nothing is `human_validated` and nothing is empirical: every number is a
model consequence of assumed parameters. `equilibrium_model.py` is unchanged and is the explicit baseline; the
variants import it read-only. `robust_design.py` and `ci_sims.py` were not touched.

## Summary

1. **Fixed terms are doing two opposite jobs.** In a Powell-style saturation game built from the solver's own
   quantities, upward renegotiation removes the prize-only strikes (eroding reserve, no reserve), as docking.md 5
   predicted. But fixed terms are also a commitment device: when humans' reserve jumps from q 0.45 to 0.9, a bargain
   exists in every year, yet renegotiation without commitment makes the AI strike the year before the upgrade, and
   human welfare falls from 45.7 to 20.4. Fixed or committed terms keep the peace. Whether renegotiation helps
   humans reverses with the direction of the power shift.
2. **Human preventive action has no fixed sign** (default grid; several readings change when the cap is resolved, section 1, issue #51). In a reduced bootstrap game that reproduces the full solver's R6c
   thresholds in 4 of 5 cells: where the pact holds, a human shutdown option is never used and changes nothing. Where
   the AI would strike at closure, humans strike first at year 0 and gain (P(seizure) 1 to 0.35, welfare 13.2 to
   22.0). Where it would strike late to harvest Earth, humans also strike first at year 0 and lose (welfare 36.6 to
   22.0): they cannot commit not to use the option while their window closes. Where a failed AI survives, the option
   deters the AI completely and is never used.
3. **D18's two checks** (default grid; see section 1, issue #51). Human learning after a failed strike never pulled a strike earlier and never produced a
   "strike now" spiral; it limits retries (P(seizure) 1 to 0.71-0.81) and does not deter the first strike. Humans
   striking first does pull conflict to year 0 wherever the AI would otherwise strike later (item 2). Improving human
   control removes strikes without pulling them earlier under fixed terms, and causes a preventive strike under
   renegotiation without commitment (item 1). D18's valence stays unresolved, now with stated conditions.
4. **Equilibrium selection.** The full solver's human-worst stage-equilibrium selection leaves S1 unchanged; S4, S14
   and S16 flip to "strike now", and each had a likely rival under human-best selection.
5. **Actor structures** (swarms, several AIs, an aligned ally, lab systems, unequal states) are stated through the mode
   contract in `variants/actor_structures.yaml`, checked against `systems/modes.yaml`. None is implemented.

## 1. Baselines and checks

**Bargaining game** (`variants/bargaining.py`). One period a year; AI parked just below the cap (A = 0.999e9, the
docking erosion world); humans one aggregate actor. Strike values are those of `docking/powell.py`'s
`stop_year_fail`, written net of the AI's own output. Regimes: `fixed` (sigma gam H = 0.15 a year for ever),
`reneg_up` (humans may pay up to H(1 + gam) = 1.5 a year), `reneg_down` (may cut to 0), `reneg_two_sided`, and
`committed` (one constant transfer chosen at t = 0 and binding). Diagnostics are computed once per world: a bargain
*exists* in a year if the surplus B - (1 - delta) Phi_A - (1 - delta_h) Phi_H is non-negative; it is *credible
without commitment* only if the commitment gap Phi_A(t) - delta max(Phi_A(t+1), 0) - x_max is never positive.

- Check: `fixed` in the eroding-reserve world strikes in year 165, equal to the closed form with failure branch and
  to the full solver (`docking/out/powell.json`; test `test_fixed_terms_is_the_baseline_recursion`).

**Reduced bootstrap game** (`variants/preventive.py`). The baseline game in its no-rival limit (R6_CLEAN: mu = 0,
B_R = 0): one AI on a log grid in A, pact and collapsed modes, the solver's strike odds, costs, landing rules,
kill_pre and free retries. AI values are carried as excess over exact solo-growth path sums, so saturation-stage gaps
of O(1) on values of 5e10 are not lost to interpolation. Added: a human move (shutdown attempt, success
sh x D_s/(D_s + A); a failed attempt ends the pact), a control level c (raises q and shutdown odds by 0.2 a level),
learning (c + 1 after a failed AI strike) and exogenous tightening (c + 1 with probability 1 - exp(-0.05) a year).

| check (H1 in tables.md) | reduced game | reference |
|---|---|---|
| R6c, A_close 0.003, L_f 0.5 | [0.5000, 0.5039] | solver [0.5000, 0.5039] |
| R6c, A_close 0.1, L_f 0.1 | [0.5898, 0.5938] | solver [0.5898, 0.5938] |
| R6c, A_close 0.1, L_f 0.5 | [0.4805, 0.4844] | solver [0.4844, 0.4883] (one bisection step) |
| R6c, A_close 1, L_f 0.5 | [0.4453, 0.4492] | solver [0.4453, 0.4492] |
| R6c, A_close 0.03, L_f 0.9 | [0.1914, 0.1953] | solver [0.3320, 0.3359]: **disagrees**; stated law 0.563 (below) |
| saturated start, A0 = 1.000001e9 | [0.3506, 0.3516] | closed form 0.3491 |
| saturated start, A0 = 1.5e9 | [0.2852, 0.2861] | closed form 0.2835 |

**The L_f 0.9 cell (issue #51, diagnosed 2026-10-25; numbers from `python3 variants/cap_approach.py`, CI-pinned
venv).** Neither reference is right for the stated growth law. Under A' = A exp(g max(0, 1 - A/Kmax)) the pact path
never crosses Kmax but gets arbitrarily close (Kmax - A shrinks by about 1 - g a year). Within O(1) of Kmax (here
Pi0 - cost = 0.4 units, 4e-10 of Kmax) an unplugged landing lies above the cap and is kept for ever, while a plugged
landing (A - 0.3) lies below it and regrows. The reserve then costs the AI only a transient, and it strikes about 130
years after closure, with Kmax - A below 0.01, unless q > 0.563 (L_f 0.9) to 0.604.
- Full solver: no grid point between 0.874e9 and 1.074e9 (nA 400: 0.952e9, 1.033e9). Next year's size from 0.874e9
  gets weight about 0.21 on the point above the cap, so its AI enters the static region (plugged loss permanent) by
  interpolation; [0.332, 0.336] is the static threshold. Re-run at nA 160 and 400: strikes at q 0.332, not at 0.336
  to 0.6.
- Reduced game: its last point below the cap is Kmax (1 - 1e-6), 1000 units below; the AI is interpolated back onto
  it and never gets within O(1) of Kmax, so [0.191, 0.195] is the growth-phase threshold (r6_closed q_path 0.198).
  The `_grid` comment calling the cap a kink "the path from below never reaches" was wrong and is corrected.
- Grid-free reference `variants/cap_approach.py` (optimal stopping along the exact path; failure branch without
  retry). The reduced game with `cap_pts=20` (points at Kmax (1 - 10^-k), k = 1..13) converges to it:

| A_close | L_f | full solver (committed) | reduced game, default | reduced game, cap_pts 20 | grid-free path |
|---|---|---|---|---|---|
| 0.003 | 0.5 | [0.5000, 0.5039] | [0.5000, 0.5039] | [0.5898, 0.5938] | 0.5903 |
| 0.1 | 0.1 | [0.5898, 0.5938] | [0.5898, 0.5938] | [0.5977, 0.6016] | 0.5988 |
| 0.1 | 0.5 | [0.4844, 0.4883] | [0.4805, 0.4844] | [0.5898, 0.5938] | 0.5903 |
| 1 | 0.5 | [0.4453, 0.4492] | [0.4453, 0.4492] | [0.5898, 0.5938] | 0.5903 |
| 0.03 | 0.9 | [0.3320, 0.3359] | [0.1914, 0.1953] | [0.5625, 0.5664] | 0.5633 |

So the four "agreeing" cells agree because both grids miss the same region. Over all 30 R6c cells the grid-free
threshold is above the committed solver bracket in 26 (all but L_f 0.05 at A_close <= 0.1). Nothing was regenerated:
the R6c tables stand as solver output, and results/variants/*.json as the default-grid run. Whether the law should be
taken literally within 1e-11 of the cap (or the cap treated as absorbing, as the solver and closed forms effectively
do) is a modelling decision for the owner; the solver is not changed here.

**Scope of the reduced game, narrowed.** With the default grid it reproduces the solver's discretisation, blind spot
included; it does not resolve the stated law near the cap. Section 3 readings that depend on what the AI would do
near the cap change with `cap_pts` 20 (40 identical; `cap_approach.structure_sensitivity`, not committed): late
harvest strikes in year 130, not 79, and shutdown 0.3 is no longer used (welfare 21.9 -> 39.9); weak survivable and
retry now are no longer deterred by a shutdown option, humans strike at year 0 (welfare 40.9 -> 10.4 to 19.6);
learning no longer limits retries (P(seizure) 0.81 / 0.71 -> 1); tightening raises P(seizure) by 0.02 to 0.03.
Summary items 2 and 3 hold for the default grid only.

## 2. Bargaining: existence versus credible implementation

Per year, x_max = 1.5 (B1, B2 in tables.md).

| world | bargain exists every year | commitment problem | fixed | reneg_up | reneg_two_sided | committed |
|---|---|---|---|---|---|---|
| baseline (q 0.7) | yes | no | peace, 45.7 | peace, 45.7 | peace, 50.8 | peace, 50.8 |
| eroding reserve (q_er 0.005) | yes | no | strike yr 165, 45.4 | peace, 45.7 | peace, 50.5 | strike yr 114, 46.5 |
| closing window (q 0.45 to 0.9 in yr 20) | yes | **yes** (yr 19) | peace, 45.7 | peace, 45.7 | **strike yr 19**, 20.4 | peace, 46.9 |
| no reserve (S6) | yes | no | strike yr 0, 0 | peace, 37.4 | peace, 37.4 | peace, 37.4 |
| harvest (S16) | **no** | yes | strike yr 0 | strike yr 0 | strike yr 0 | strike yr 0 |

(Entries: outcome, human welfare at r_h = 0.03.) Readings:

1. *Bargain exists and is credible* (eroding reserve, no reserve): the strike is a fixed-terms artefact; any regime
   that lets humans pay removes it.
2. *Bargain exists but is not credible without commitment* (closing window): humans who will squeeze the AI after the
   upgrade cannot pay enough before it (gap 4.1 a year in year 19), so the AI strikes preventively. Fixed terms are
   themselves a commitment and keep the peace; so does a committed transfer of 0.115 a year, which humans prefer
   (46.9 against 45.7). This is Powell's declining-side war with the AI as the declining side.
3. *No bargain* (harvest): nothing Earth can pay matches a lock-in of 500 a year.
4. *Measures disagree.* With the eroding reserve, the committed constant transfer that maximises discounted human
   welfare (0.08) accepts a lethal seizure in year 114: higher welfare at r_h = 0.03, lower control retention. Down-only
   renegotiation is better on welfare and worse on timing for the same reason. This is why the measures are reported
   separately (B3).

## 3. Human preventive action, learning and tightening

Six structures (what the AI would do without the new options) by seven policies (H2, H3 in tables.md):

| structure | none | shutdown 0.3 | end pact only | learn | tighten |
|---|---|---|---|---|---|
| holds (q 0.7) | no strike, 40.9 | unused, 40.9 | unused, 40.9 | 40.9 | 40.9 |
| weak reserve (q 0.45) | AI yr 15.5, seize 1, 13.2 | humans yr 0, seize 0.35, 22.0 | AI yr 0, seize 0.50, 16.9 | seize 0.81, 16.8 | P(strike) 0.64, 23.6 |
| weak, survivable early failure | AI yr 15.5, seize 1, 13.2 | **deterred**, 40.9 | AI yr 0, seize 0.67, 11.4 | seize 0.71, 18.8 | P(strike) 0.46, 28.4 |
| retry now (kill_pre 0.2) | AI yr 0, seize 0.83, 6.2 | **deterred**, 40.9 | unchanged | unchanged | unchanged |
| late harvest (f_E 1e-8) | AI yr 79, seize 1, 36.6 | humans yr 0, seize 0.35, **22.0** | unused | unchanged | unchanged |
| survivable seizure (w 0.9) | AI yr 15.5, 31.9 | humans yr 0, 32.7 | AI yr 0, 32.1 | 32.3 | 35.2 |

(Human welfare last in each cell.) Readings, each measure kept separate:

- **Strike timing.** Every human option that is used moves open conflict to year 0. Learning and tightening never
  pull a strike earlier (conditional strike year 15.5 against 15.4).
- **Successful harm and control retention.** Shutdown capability and tightening lower P(seizure) wherever the AI would
  strike; learning lowers it only where a failed AI survives to retry.
- **Human welfare.** Reverses across structures for the shutdown option (better with a closure-time striker, worse with
  a late harvester) and for ending the pact (better with fatal early failure, worse with survivable early failure).
- **Distribution.** No option raises the AI's value. Humans gain in most cells and are unaffected in some; in two
  (late-harvest shutdown, pact exit with survivable early failure) both sides lose.
- **Deterrence without use.** Where a failed strike leaves the AI alive (weak survivable, retry now), a 10 % shutdown
  capability is enough to stop the AI striking at all: it removes the free retry (AS-FREERETRY) rather than
  threatening the first strike.

Policy-ranking reversals found (H3): shutdown 0.3 and shutdown 0.3 + tighten reverse on human welfare (better in four
structures, worse in late harvest) and on timing; end-pact-only reverses on welfare (weak reserve and survivable
seizure against weak survivable). The assumptions that decide the sign are when the AI would strike without the option
(closure versus late), whether an early failure is fatal (kill_pre), and the humans' discount rate against the date
of the AI's strike.

## 4. Equilibrium selection (full solver)

`variants/run_variants.py selection` re-solves the 25 named scenarios with `sel='worst'` (412 s). The `best` column
reproduces `equilibrium_summary.json` exactly (test `test_best_selection_reproduces_round1`). Changed: S4 (never
dismantle), S14 (rival stays dangerous, survivable seizure) and S16 (harvest) go from cooperate to strike now, with
human welfare falling from 0.99, 0.97, 0.99 to 0.49, 0.95, 0.49. Their human-best equilibria all had a likely rival
(P(rival) 0.95, 0.16, 0.66). S1 and the other cooperating scenarios are unchanged.

## 5. Actor structures through the mode contract

`variants/actor_structures.yaml` states six structures as contract entities (kinds, hosts, dimension levels,
transitions) and what a solver variant would need: AST-COPIES (one set of weights, many coordinating copies: shared
capability, separate attempts, per-copy kill rule), AST-RIVAL-AIS (several AIs, coalitions as commitments, rival birth
no longer terminal), AST-ALIGNED-ALLY (a human-controlled defender from which Earth's defence D is derived),
AST-LAB-CAPABLE (a sovereign-capable lab system before t = 0; AD-PACT unsupported, so excluded by scope) and
AST-HETEROGENEOUS-STATES. `tools/omissions_tool.py` rejects any entity kind, dimension, level, host or transition the
contract does not declare and any field outside the contract, so no capacity multiplier can stand in for a structure.

## 6. What this does not show

- No result is empirical, and the reduced games are not the full solver: no rivals, no state racing, one aggregate
  human actor (so no between-state distribution), Markov strategies, complete information.
- The bargaining game sits at saturation only; renegotiation during the bootstrap is not modelled.
- Control effects (0.2 a level, 5 % a year) and shutdown odds (0.1, 0.3) are illustrative choices, not estimates.
- The L_f 0.9 discrepancy in section 1 is unexplained.
- Seven omissions are unresolved and one is excluded by scope; `results/omissions.md` gives the narrowed claim for each.

## 7. How to run

From `model/`: `python3 variants/run_variants.py` (bargaining and reduced game, about 2 minutes including the
baseline checks), `python3 variants/run_variants.py selection` (full solver, about 7 minutes),
`python3 variants/run_variants.py tables` (re-render only). Fast tests: `python3 tests/test_variants.py` (about 5 s)
and, from the repo root, `python3 test/omissions_tool_test.py`; both run in `make check`, as does
`python3 tools/omissions_tool.py check`. After editing `omissions.yaml`, run `make omissions-render`.
