# HANDOFF: equilibrium model of Cole's clarified pact

Written 2026-10-16 by the session that built it. Nothing is committed. Status: rounds 1 and 2 are `implemented` and `verified`, not `human_validated`. Round 2 was run and checked by session 2 (section 7); section 6 is the original TODO, now done.

## 0. Correction to the parent session's brief

The two "open bugs" named in the handoff request were found and **fixed** before the full run. The final round-1 outputs were produced after the fixes. See section 3 for what each was and where the fix lives.

## 1. Architecture and how to run

Everything is in this folder (`model/`). The earlier one-sided model (`offearth_model.py`, `run_analysis.py`, `results/results.md`) is untouched and still runs; its baseline M_ever = −0.962 matches `decision_model.md`.

**`equilibrium_model.py`** (numpy only)
- `PARAMS` holds every parameter: baseline, range, scale, meaning and basis.
- `solve(pb, N, T_H, nA, nF, sel, store, terminal)` (line 260) does backward induction on a stochastic game.
  - State: AI capacity A on a log grid (default 160 points), Earth fab level F (6 points, interpolated), mode (0 pact; 1 collapsed without chips; 2 collapsed with chips), k public covert programmes (0..N).
  - Each period the AI moves first: C cooperate, X exit, S strike, P police. Then enforcement, then the N states' simultaneous stage game (`stage`, line 407; pure equilibria are enumerated, with a regret-minimising mixed fallback that was never triggered). Then the rival-birth draw, then growth.
  - Everything is vectorised over a batch axis B, so one call solves many parameter sets.
  - Indicator recursions (`IND`) give P(strike ever), P(seized), P(rival), mean strike year, P(exit) and similar without storing policies.
  - It returns the t = 0 values at (A0, F = 1, pact, k = 0) and `act0`, the AI's tie-broken opening move.
- `simulate(res, bi, M, T)` (line 749) runs a forward Monte Carlo on stored policies. It needs `store=True` (memory heavy, so use batches of 8 or fewer).
- Closed forms: `cap_strike_gap` (line 852) is the exact discrete gap at saturation. `cap_condition_terms` (876) is the first-order per-year terms. `eps_star_cap` and `eps_star_cap_exact` (905, 913) were added in round 2.

**`run_equilibrium.py`**
- `python3 run_equilibrium.py` runs the full round 1: about 52 minutes on this laptop. It writes `results/equilibrium_tables.md`, `results/equilibrium_summary.json` and `figures/eq_*.png` (six figures).
- `--quick` is a smoke test only, but it **overwrites the same output files**, so re-run the full version afterwards.
- `--round2` runs only R1–R4 and writes `results/equilibrium_round2_tables.md`. It has never been run (section 6).
- `results/equilibrium.md` is hand-written from the tables. It is complete for round 1.
- Speed: about 3–5 s per parameter set at nA = 160, T_H = 300, batched.

## 2. What is verified (round 1, from `results/equilibrium_tables.md`)

1. **No growth, no threat:** the AI's value equals flow/(1 − δ) to within 5e-8. Human welfare matches to within 7e-7.
2. **Growth path, no threat, no strikes, against a direct path sum:** 5.9% level error at nA = 160 (0.3% at 240, 2.5% at 400). This is interpolation error in the value level. Outcome classes are stable across grids (item 5).
3. **Saturation closed form `cap_strike_gap`:** 0 of 41 trade-share values disagree with the solver on strike or no strike, and both put the threshold at σ* = 0.425.
4. **Growth-stage closed form (G):** the strike threshold in denial credibility q is 0.500 in the solver and 0.528 in the closed form, which is within one grid step.
5. **Robustness:** opening move and outcome class are identical at nA = 120/160/240, at T_H = 150/300/600, and with a "seized" instead of "peace" terminal value. P(rival) depends on the horizon, so it is always reported as "within 300 years".
6. **Monte Carlo against backward recursion:** within 0.6 percentage points.
7. **Round-2 regression:** with all new parameters at their defaults, S1, S7, S14 and S16 reproduce round-1 numbers exactly.

## 3. Bugs: fixed, and still open

**Fixed** (each changed results before its fix):
1. **Terminal value froze A.** This faked strikes near the horizon. Fix: a "peace" terminal equal to the converged solo-growth value (around line 375).
2. **The pact-mode terminal omitted trade.** (The parent's "trade dependence missing from peace value".)
   - Symptom: at saturation the peace value grew by only one period of trade as σ rose, so the solver struck for every σ.
   - Cause: the last period struck (terminal value below the strike value), humans raced in anticipation, and that unravelled back to t = 0.
   - Fix: `tr_T` adds the trade stream to the pact terminal value (line 390).
3. **Tie tolerance too coarse** (the parent's "strike-branch batch-versus-closed-form mismatch").
   - Symptom: the solver and the closed form disagreed at saturation.
   - Cause: the tolerance was 1e-9 relative, while saturation gaps are about 1e-11. Also, `run_equilibrium.act0` picked the max of `Q0` values instead of the solver's own choice.
   - Fix: `TIE_TOL = 1e-13` (line 172) and `res["act0"]`.
4. **Interpolation across the saturation kink.** The fire-branch strike landed below the cap grid point, and log-linear interpolation between a growing point and a static point added about 2.5 units, which is the size of the gap being decided. Fix: the exact u(A)/(1 − δ) for A ≥ K_max (line 607).
5. **Solo-value convergence tolerance** loosened values by up to 5e-11. Fix: `err < 1e-15` (line 380).
6. **Strike cost capped at 0.5A**, which made post-closure strikes artificially cheap. Fix: c_A·D·A/(A + D).
7. **B_R did two jobs.** It is now split into B_R (pact-time gain) and B_Rc (gain after the pact has collapsed).
8. **A failed strike was retryable at no cost**, which led to strikes everywhere. Fix: `kill_pre`, under which a failed strike before closure is fatal.

**Still open** (none blocks round 1):
1. The 5.9% interpolation level error (verification item 2). It affects AI value levels, not checked decisions. Mid-growth decisions (A from about 1e2 to 1e8) are not individually checked against a closed form.
2. The fab level F has 6 grid points. The relocation and rebuilding rates are approximated (smoothed curves in `eq_sequencing.png`).
3. Moved compute (round 2, `earth_threat`, line 195) is tied to the fab-schedule variable F, so it would "un-move" if fabs are rebuilt after a pact collapse. This is untested.

## 4. Results I trust (round 1)

1. The pact can be an equilibrium (AI cooperates, states comply), but only with all of these:
   - the denial reserve is kept;
   - sequencing (a) dismantle after closure, or (b) relocate fabs to orbit;
   - state temptation B_R below about 8 years of welfare under (a) or 6 under (b);
   - ℓ_∞ = 0, or no source of rivals at all.
2. **(c) early dismantling fails at every B_R and floor tested** (use-it-or-lose-it strike for chips). It holds only with certain, complete denial (q = d = 1), and then the bootstrap is about 50 years slower (closure at year 63 instead of 14).
3. **"It will wait."** True during bootstrap, because a failed early strike is fatal. After closure, the pact holds only if three terms are all zero or negative: the net prize after plugging, the irreducible threat ℓ_∞, and the harvest term. Otherwise:
   - if humans survive a seizure, the AI waits 31–71 years and then strikes (S14: year 38);
   - if seizure is lethal, humans race and the AI strikes at year 0.
4. **Trade barely binds** (σ from 0 to 1 changes no outcome). The denial reserve carries the growth phase. A tribute is worse than trade (S23).
5. **The harvest boundary** f_E(1 − c_grav)K > σγH + ωK matches the solver; the harvest comes around year 87–88.
6. **Fragile:** 19 of 36 one-at-a-time moves flip baseline cooperation to "strike now".

Trust level: these numbers depend on assumed parameter values with no empirical basis (B_R, ℓ_∞, w_seized, p_s0, D, q). The mechanisms and closed-form boundaries are more robust than the levels.

**Not yet trusted:** anything from round 2 (not run). The early closed-form check in section 6 is first order only.

## 5. Modelling decisions

1. **TIE_TOL = 1e-13 relative.** At K_max = 1e9, values are about 5e10 and saturation gaps are O(1), so the tolerance must sit above float64 round-off (about 1e-14) and below 1e-11.
2. **Saturation handled exactly:** solo value u(A)/(1 − δ) above the cap (line 607).
   - The parent's suggestion (report saturation analytically, don't fight precision) is consistent with this: `cap_condition_terms` is the analytic tool, and the solver now agrees with it.
   - At K_max ≥ 1e13, trade and prize terms fall below float precision. Use the closed form there.
3. **Equilibrium selection:** the human-best stage equilibrium (the pact coordinates), with "worst" as a check. The AI breaks ties toward peace. Markov strategies only.
4. **Terminal value "peace":** solo growth plus the trade stream at T_H = 300. Results are stable to "seized" and to T_H = 600.
5. **Failure is fatal before closure** (`kill_pre = 1`); after closure it costs L_f and collapses the pact.
6. **Unsettled, so both variants were run** (questions for Cole in `equilibrium.md` §7):
   - ℓ_∞ (does a rival stay dangerous?);
   - w_seized (is a seizure lethal to humans?);
   - police (may the AI remove covert fabs?);
   - reinv (is trade consumed or reinvested?);
   - kill_pre (is a failed early strike really fatal?);
   - f_E (harvest).

## 6. Remaining TODO (Cole's round-2 answers: not done)

**Code already added this session, before the stop** (not run beyond the regression check in §2 item 7):
- **New parameters** (defaults leave round 1 unchanged): `rho_h`, `move_c`, `m_frac`, `n_cf`, `f_fab`, `p_block`, `A_hg`, `c_blk`, `rep`.
- **New helpers:**
  - `earth_threat` (line 195): floor reduced by moving compute; plus covert fabs times f_fab.
  - `rival_damage` (line 203): ratio damage ρ^ν/(ρ^ν + ρ_h^ν) with ρ = s_R/A; ℓ_∞ blocked with probability p_block once A ≥ A_hg.
- **Changes inside `solve`:**
  - blockade upkeep in the AI's flows (line 324);
  - `rep` multiplies the value of a successful strike (line 619).
- **Closed forms** updated for the new terms, plus `eps_star_cap` and `eps_star_cap_exact`.
- **Analyses:** `run_equilibrium.py` has `r1_compute_ratio`, `r2_covert_fabs`, `r3_r4_preference` and `round2()` (lines 589–760), with SQ = status quo (seq n, no denial, D = 1). They have never been executed, not even as a smoke test.

TODO, in order:
1. Smoke-test: `python3 run_equilibrium.py --round2 --quick`. It writes round-2 files only.
2. Full run: `python3 run_equilibrium.py --round2`. The estimated runtime is 25–40 minutes; I didn't measure it. Check every table.
3. **Cole's 100x compute-ratio threshold (R1):** ratio damage at 1:100 for ν = 1, 2, 3; the year the S1 path crosses 1:100 with and without moving compute; the blockade test with closed-form escape probability leak* (the largest escape chance that avoids a late strike).
   - Expectation from the closed form: leak* is about 1e-6 for ℓ_∞ = 0.01, so the gravity-well blockade must be nearly perfect.
4. **Covert fabs 0 / 1 / several (R2):** n_cf ∈ {0, 1, 2, 3, 5, 10, 20, 30} against B_R, and again in the ℓ_∞ world with no other rival source.
5. **Minimum ω with versus without the pact (R3):** solver grid over ω, for pact and status quo, with sunlight f_E = 4.5e-10 and 1e-9 (c_grav = 0).
   - First-order saturation closed form, checked by hand this session: pact ε* ≈ 2.7e-10 at f_E = 4.5e-10 (8.3e-10 at 1e-9). Status quo, H = 1: ≈ 1.2e-10. With ℓ_∞ = 0.01: pact 2.5e-4, status quo 4.9e-3.
   - So **at saturation the pact does not lower ε* when ℓ_∞ = 0**; the harvest term dominates. Any large reduction must come from the growth phase, where the status quo AI strikes early. The R3 solver grid is meant to measure that; it is not yet measured.
6. **Reputation break-even (R4):** treat the expected penalty p·Φ as an addition to ω, so p* = ε*/Φ, against the 4.5e-10 to 1e-9 cost of sparing Earth. R4 includes a solver check at 0.3× and 3× ε*.
7. Add named results R1–R4 to `results/equilibrium.md`. Round 1 there is already final. Then update the shared note `side-session-notes/.../equilibrium-model-notes.md`.

## 7. Round-2 progress log (session 2, 2026-10-16)

- Step 1 done. `--round2 --quick` ran without a crash (292 s). No code fix was needed in the model. Round-1 regression re-checked after the runner edits: S1, S7, S14, S16 match `equilibrium_summary.json` with max abs diff 0.
- Runner edits (`run_equilibrium.py`, round-2 functions only): R1d adds escape points at 0.3x and 3x the closed-form leak*; R2b adds B_R = 7.5 (covert fabs add capacity tau only, so with no rogue source they matter only through state temptation); R3 adds strike year at epsilon = 0 and a 10x finer pass inside each bracket; R4 reports a p* bracket, marks p* > 1 "unreachable", and checks rep in the solver for every case.
- Quick-mode readings (not for quoting): leak* = 7.2e-7, solver flips between 1e-6 and 1e-8; R3 pact eps* in [1e-10, 3.2e-10] vs closed form 2.7e-10; status quo eps* in [0.03, 0.1] vs saturation closed form 1.2e-10, so the growth phase dominates the status quo.
- Step 2 started: full `--round2` running in the background (log in the session's $TMPDIR/r2full.log).
- Closed forms (full precision): leak* 7.24e-7 first order, 7.35e-7 exact. eps* exact: pact 2.69e-10 (f_E 4.5e-10), 8.33e-10 (1e-9); status quo 1.23e-10; pact ell_inf 0.01: 2.47e-4; status quo ell_inf 0.01: 4.93e-3.
- Investigated (quick mode): pact + ell_inf=0.01 solver eps* [3.6e-4, 4.1e-4] vs closed form 2.5e-4. Not the dismantling window (T_dis 2 and 5 give the same threshold; strike at year 38 with w_seized 0.9). Cause: a rival destroys a share of the AI's whole continuation value, which mid-growth is a larger multiple of current flow than at saturation, while omega is a share of current flow. Test with th_floor = 1 (threat independent of fabs), w_seized 0.9: saturated start (A0 = 0.999e9) flips between 4.5e-3 and 5.5e-3 = closed form 4.93e-3; growth start (A0 = 1e-3 or 1e3) flips between 1.2e-2 and 2e-2. So the saturation closed form is a lower bound whenever a threat term is active. Not a bug.
- Steps 2-3 done. Full `--round2` ran in 1218 s. All tables checked against closed forms:
  - R1d: solver flips between escape 1e-6 and 2.2e-7 (both w_seized), closed form leak* 7.35e-7. Agrees.
  - R3 pact f_E 4.5e-10: [2.4e-10, 2.8e-10] vs 2.69e-10. Agrees.
  - R3 pact f_E 1e-9: [6.8e-10, 7.7e-10] vs 8.33e-10 at nA 160 (8% low, within one fine step). Re-checked at nA 240 and 400: flips in [8.0e-10, 8.3e-10]. Interpolation error, converges to the closed form.
  - R3 status quo: [0.053, 0.060] (strike at year 0) vs saturation closed form 1.2e-10. Growth phase dominates, as expected.
  - R3 pact ell_inf 0.01: [4.1e-4, 4.6e-4] vs 2.5e-4. Growth-phase lower bound effect (see above).
  - R4 check: rep at 0.3x eps* leaves P(strike) unchanged, at 3x gives 0, in all 6 cases. rep behaves like omega.
- Plot fixes (R1 label, R2 title and label, R3 colours and legend) made in the runner; a second full run regenerates figures (tables should be identical). Next: write R1-R4 and the summary into equilibrium.md.
- Step 4-5 done: R1-R4 written into `results/equilibrium.md` section 3R (with numbers, verdicts, "what would show this wrong" and a checks list); section 7 updated (Q1, Q4 revised; Q7-Q10 new); plain-language summary added at the top; file list updated.
- Second full run (after the plot fixes) reproduced the round-2 tables exactly (0 diff lines). R3 figure regenerated alone after moving its band label.
- No result changed a round-1 conclusion. Open for Cole: questions 7-10 in section 7. Not computed: the mass-based harvest case for R3 (only sunlight).

## 7b. Round-3 progress log (R6 session, 2026-10-16)

- No R5 session or `--round3` flag existed, so this session created `--round3` (`round3()` in `run_equilibrium.py`; R5 can be added to it). It writes `results/equilibrium_round3_tables.md`, `results/equilibrium_round3_summary.json` and `figures/eq_r6_sovereignty.png`. `--round3 --quick` writes `_quick` files only, so it never overwrites the full run. Round-1 and round-2 outputs are not touched.
- New closed forms at the end of `equilibrium_model.py` (pure functions, solver unchanged): `growth_terms`, `qd_star_growth` (linear (G) with the exact cost c_A D A/(A+D) and exact p_f), `growth_gap_power` and `q_star_power` (the same comparison without linearising: value grows like A^(r/g) before the cap).
- First finding from the closed forms: at small A_close the linear (G) is wrong. The prize is hundreds of times the AI's size, and with g = 0.35 > r = 0.02 a prize X is worth only ((A - cost + X)/A)^(r/g), about 15 years of head start. Power form needs q of about 0.4-0.6 at d = 1, while linear (G) says q*d of about 0.99. q and d also stop being interchangeable: with q = 1 the power form needs d >= 0.996 at A_close = 0.003.
- Smoke test `--round3 --quick` ran (17 min, no crash). Quick readings then drove three closed-form fixes; the runner was then rewritten (R6a-R6e) and the stale `_quick` outputs deleted.
- Gap 1 (solver q* below the power form by up to 0.034 at A_close = 0.003): not trade (trade share is about 5e-10 of the AI's value) and not interpolation at the closure kink (shifting A0 and nA = 400 change nothing). Cause: with d = 1 a successful strike costs a small AI c_A D A/(A+D), nearly all of A, so it lands below A_close and regrows at chi0 g. The solver models this; the closed form did not. Fix: `landing_factor` applies the same slow-regrowth rule to every landing point (success and failure). After the fix the power form, worst over the AI's yearly sizes after closure, matches the quick-mode clean solver within 0.005 at every A_close and L_f below 0.9.
- Gap 2 (L_f = 0.9: solver 0.334 at every A_close vs saturation closed form 0.357): saturation binds there, not growth. `cap_strike_gap` treats the failure branch as negligible, but with eps = 1, p_f A stays (1 - p_s0) D = 0.15 at any size. Checks: eps = 3 gives solver 0.357 = closed form; A0 = 3e9, L_f = 0.1 gives 0.334 vs 0.336 with a permanent-loss estimate. Fix: `cap_gap_fail` adds the failure branch with logistic regrowth; it gives 0.331 at L_f = 0.9.
- "At the moment of closure" is not the binding moment when L_f is large: a failure right at closure drops the AI below closure, so it waits until A >= A_close/(1 - L_f). The closed form therefore takes the worst yearly size after closure, then the max with saturation.
- Full `--round3` started (log in the session's $TMPDIR/r3full.log).
- Full `--round3` ran in 6858 s (1 h 54 min). Checked every table against the closed forms:
  - R6c (needed q, d = 1): closed form within one bisection step (0.004) of the mu = 0 solver in all 30 cells, including the saturation-bound L_f = 0.9 (0.331 vs [0.332, 0.336]).
  - R6d (largest 1 - d, q = 1): up to about 25% off at nA 160, either direction. Re-run of 5 cells at nA 400 and 800: four converge within about 3% (interpolation; d moves the landing point continuously, q does not). The fifth (A_close 0.01, L_f 0.3) stays at 0.032-0.034 vs 0.028: a failure lands 1% below closure, and the solver charges a whole year at chi0 g where the continuous closed form charges 0.19 years. A discrete-year closed form gives 0.035. Explained, not a bug.
  - R6e (full model): q* within about 0.02 of the closed form at small A_close, up to 0.05 higher at A_close = 1 (rival threat during the longer bootstrap). 1 - d* is larger than the closed form at L_f 0.5 and 0.9 (a failed strike also brings back fabs and racing).
  - R6a: only "cooperate" and "strike now" occur. Strike now = year 0-1, pre-closure, via unravelling (U), even at w_seized 0.9; with B_R = 0 the same AI waits and strikes at closure (about year 3.6).
- Figure fixed (legend moved below, y range) and redrawn from the JSON with `--round3 --r6-figure` (no re-solve).
- R6 written into `results/equilibrium.md` (end of section 3R, before section 4), with summary point 10 at the top, one new "what would show it wrong" item and updated file lists. Status: implemented + verified, not human_validated. Nothing committed. Round-1 and round-2 outputs untouched.
- Not done: no R5 exists yet; `round3()` is ready for it. The R6 solver brackets are at nA 160; 1 - d is only good to about 25% at small A_close (see above).

## 7c. Overnight tests (2026-10-21)

Summary [[ai gen]] (03:20; everything in the brief ran, nothing committed, no cached run deleted).

What ran: erosion write-up, test 1 (state temptation) comparison, tests 2 to 5, plus full-box runs of tests 2 and 4. Write-ups are sections 4 and 7 to 11 of `results/robust_design.md`.

Verified (checked against closed forms or identities):
1. Code change, all new options off by default: round-1 regression difference 0, and `--check` output identical before and after. Re-solving cached ensembles with the new code reproduces them exactly.
2. Erosion: baseline-world thresholds and strike years match the saturation closed form. Ensemble mismatches came mostly from the closed form, which ignored the failure branch; a few horizon-edge draws remain.
3. Test 2, closing window: three checks pass.
4. Test 4, misjudged odds: belief equal to truth reproduces the normal solve exactly.
5. Test 3, ratchet: continuity and identity checks pass.

Only implemented: test 1, test 5, and the full-box extensions.

Findings:
1. State temptation is not the biggest lever near the baseline (2 draws of 64, against 15 to 20 for the reserve, defence and d levers). On the full box it is the best single lever, but every gap there is 1 to 4 draws.
2. A closing window never pulled a strike earlier from a normal start. It removes strikes instead: plus 15 to 17 draws near the baseline, nothing on the full box.
3. Overconfidence wrecks the baseline design near the baseline (41 holding draws become 12, or 1). The extra strikes come at year 0 and half fail. The best stack is immune there.
4. Warning shots come paired with seizures: about one success per failure, and failures cost humans little.
5. The ratchet barely matters. Softening the failure penalty does create early strikes.
6. Correlated reserves: the second reserve is worth 3 of 192 full-box draws on the best stack, and nothing near the baseline.

What to look at first:
1. The "holds" test ignores rival AIs. In tests 1 and 4, "extra holds" were mostly worlds where a rival is born, and human welfare fell. Consider counting a likely rival as failure.
2. The retry artefact: any non-fatal early failure means "strike now" in every world. It dominates tests 2 to 4 wherever it appears.
3. The two faster-detection draws (L_dn) that flipped to "strike now" are not diagnosed.

Progress log (newest last):
- 00:43 Session started. Test 1 (BR_mult) was running (log `results/robust_test1_BR.log`). No edits to `equilibrium_model.py` or `robust_design.py` until it prints TEST1 DONE.
- 00:50 Step 1(a) erosion check. Deterministic baseline-world rows agree with the saturation closed form (q_ea threshold 0.063: holds at 0.06, strikes at 0.07, both worlds; q_er 0.002 strike year 299 = closed form 299; 0.005: 161 vs 160). The r0.1 ensembles: every draw the pact LOSES to erosion is explained by the closed form for the plain q_er runs (16 of 16 at 0.003, 27 of 27 at 0.01, 40 of 40 at 0.03). But there are draws where the closed form says a saturated AI should strike and the solver says the pact holds (1 to 11 per run). Diagnosing (scratch script; log `results/overnight_diag_contra.log`). First finding: draw 4 (q_ea 0.03) sits within 0.015 of its threshold q*, and its solver gap moves by about 0.1 per year when only the batch's grid top changes, so it is a marginal draw.
- 00:55 Test 1 finished (TEST1 DONE at 00:54). Paired comparison done (scratch script); write-up below in `robust_design.md` section 7.
- 00:58 `robust_report.py` edited (allowed: not one of the two locked files): test variants (BR_mult, q_up, L_dn, k_rat, pf_bel, L_f, kill_pre, w_seized, fractional q_red) are kept out of the lever regret pool and the best-design pick and get their own table T. Without this, adding BR_mult designs changed other designs' regret numbers and the "best" pick. Also: erosion scenarios are no longer eligible as the "best r0.1 design" (they were, before), and the E-ens table splits q_er and q_ea so the q_ea columns are labelled correctly. `--report` re-run: every lever table is unchanged apart from the order of tied rows.
- 01:10 Erosion diagnosis done. The draws where the saturation closed form said "strike" but the solver said "holds" come from the closed form, not the solver: it ignored the failure branch, which matters when eps < 1 (expected loss p_f A grows with A; draw 4 has eps 0.86, p_f A = 2.1). With a failure branch added (failed strike costs L_f A, ends trade, AI regrows alone) the contradictions fall from 1-11 per run to 0-8, and 11 of the 15 left have closed-form strike years of 264-299, right at the horizon (the others: 106, 176, 234, 249). Draw 4's solver threshold is 0.45 against 0.505 (failure-branch closed form). Separately: `act0` is read at the nearest grid point, which for draw 4 sits 9% below the cap, so act0 can disagree with the interpolated values there. Neither changes a decision outside such marginal draws. Scripts: scratchpad `erosion_check.py`, `erosion_check2.py`, `cf_fail.py`, `diag_*.py`.
- 01:01 Code change for tests 2-4 (checks finished 01:12) in `equilibrium_model.py` (all off by default): `q_up`, `L_dn` (closing window), `k_rat` with `RAT_LEVELS = 2` extra collapsed-mode levels (ratchet), `pf_bel` with a two-pass solve (misjudged odds), and a new indicator `fail` (P a chosen strike fails = warning shot). `simulate` gets q_up and L_dn; it refuses the ratchet and two-pass. `robust_design.py`: `fail` added to KEEP only. Checks after the change: round-1 regression max abs diff 0 (S1 C, S7 S, S14 C, S16 C); `--check` output identical to before; two-pass with pf_bel = 1 equals the one-pass solve exactly (max rel diff 0, same act0, 7 cases); ratchet with k_rat = 1e-12 equals k_rat = 0 to 4e-14; q = 1 with q_up 0.05 equals q = 1 exactly; L_dn with no rival hazard changes nothing; saturated start: q_up 0, 0.01, 0.05 all keep the strike threshold at q 0.38 (closed form 0.389) and only move strikes earlier.
- 01:18 New runner `overnight_tests.py` (tests 2-5; writes `results/overnight_<test>[_quick].json` and `_tables.md`; ensembles go through the robust_design cache). Test 2 smoke (`--quick`) ran in 150 s, no crash. First readings: in worlds where the AI strikes at year 0 (unravelling), a rising q changes nothing; on the r0.1 box q_up 0.01 stops 15 of the baseline design's strikers and makes none earlier. Added three "late strike" worlds (eroding keys, harvest motive, weak reserve with no state temptation), because a timing shift cannot show where strikes already happen at year 0. Full test 2 launched 01:20 (log `results/overnight_test2.log`).
- 01:25 Write-ups added to `results/robust_design.md`: section 4 (erosion) and section 7 (test 1).
- 01:38 Test 2 full run done (18 min; tables `results/overnight_test2_tables.md`). Extra probe of survivable-early-failure worlds in `results/overnight_test2_extra.log`. Test 4 smoke done (15 min, identity check: forced two-pass with belief = truth reproduces the one-pass solve exactly, 20 worlds). Full test 4 launched 01:43 (log `results/overnight_test4.log`); test 3 smoke launched alongside with 3 workers.
- 02:05 Test 2 written up (`robust_design.md` section 8). Test 4 full and test 3 smoke still running; early readings (not yet checked): on the r0.1 box an overconfident AI (believes failure is 4x less likely) leaves the baseline design holding on 1 of 64 draws, an underconfident one (2x, 4x) on 61 and 63; ratchet k_rat 0.9 raises the baseline design from 41 to 46 of 64; with kill_pre 0 nothing holds, ratchet or not.
- 02:15 Test 4 full done (22 min). Identity check passed (20 worlds, difference 0). Written up as `robust_design.md` section 9. Welfare decomposition in `results/overnight_test4_decomp.log`. Running now: test 3 full (5 workers, log `results/overnight_test3.log`), test 5 (3 workers, `results/overnight_test5.log`), and the r0.1 truth runs with the new `fail` indicator (`results/overnight_test4_truthfail.log`) so the warning-shot rate at belief = truth can be filled in.
- 02:40 Test 5 done (32 min, 3 workers) and written up (`robust_design.md` section 10). Test 3 deterministic stage done (756 sets, 28 min); its ensemble stage is running.
- 02:45 `robust_report.py`: fractional q_red (test 5) now also counts as a test variant. `--report` re-run, exit 0; table A unchanged; the best-stack regret on the full box is unchanged (mean 0.0233, max 0.551, best on 53). Table B (full) now also lists the best stack without the second reserve (from test 5). By-product of the earlier overnight chain, now in table D: the best stack holds on 100, 100, 98, 72 and 39% of draws at radius 0.02, 0.05, 0.1, 0.25 and 0.5 (8% full box); 50% radius 0.40 against 0.14 for the baseline design.
- 02:46 Extension launched (not in the brief's list, cheap): tests 2 and 4 on the full box (q_up 0.01; pf_bel 0.5, 1, 2; baseline design and best stack). Log `results/overnight_fullbox_ext.log`.
- 02:50 Test 3 full done (38 min). Continuity check passed (24 cases, 7.7e-7). Written up as `robust_design.md` section 11. Main points: the ratchet's own effect is small (2 of 252 cells per strength; +4 / +5 draws on the r0.1 box, none lost); softening the failure penalty with the ratchet off does create early strikes (baseline world: strike now once L_f is 0.3 or less).
- 03:18 Full-box extension done (tests 2 and 4; 7 runs, 36 min). Added as `robust_design.md` 8.6 and 9.5. Re-solving the full-box baseline with the new code reproduces the cached run exactly.
- 03:22 Final: `--report` re-run (exit 0); `--check` re-run, output identical to the start of the night. Nothing is running. Files added tonight: `overnight_tests.py`; `results/overnight_test{2,3,4,5}.json` and `_tables.md` (plus `_quick` smoke versions); logs `results/overnight_*.log`; new cached runs in `results/robust_runs/` (q_up, L_dn, k_rat, pf_bel, kill_pre=0, fractional q_red). Files edited: `equilibrium_model.py`, `robust_design.py` (KEEP only), `robust_report.py`, `results/robust_design.md`, this file. Backups of the three code files as they were before tonight's edits are in the session scratchpad only.

## 7d. Follow-up on the three open items (2026-10-21 afternoon)

[[ai gen]] Write-up: `results/robust_design.md` section 12. Scripts and outputs: `diagnostics/` (run from `model/`). No change to `equilibrium_model.py`, `robust_design.py` or the cache. Status: implemented + verified by identity checks; not human_validated.

1. Rival-aware holds: near the baseline the best stack is unaffected (63 to 62 of 64). On the full box most "holds" are rival worlds (best stack 15 to 4 of 192; pf_bel 2 61 to 7). Moving fabs to orbit (seq b) gains in rank because it lowers rival odds.
2. Retry artefact: real, and the whole cause in the baseline world (with retries blocked the pact holds at every kill_pre). It is a small part of the full-box failure (best stack 15 to 24 holds; 135 of 192 still strike at year 0). Correction: the pact holds in the baseline world down to kill_pre 0.4, so "any non-fatal failure means strike now everywhere" was too strong.
3. The two L_dn draws: rival risk was the deterrent. No rival risk gives a strike at closure, some gives a strike now, more gives cooperation with a likely rival. Faster detection moves them from the third case to the second. Knife-edge on the grid.

Decisions for Cole: (a) does a likely rival count as failure? (b) should a NORETRY option go into the model?

## 8. Continuous integration (GitHub Actions, added 2026-10-21)

[[ai gen]] Status: `implemented`; the commands were `verified` locally on the laptop; neither workflow has run on GitHub yet. Both workflows use only GitHub's free standard runners (the repo is public). They need no secrets, use a read-only token and pin every action by commit SHA. Versions are pinned in `.github/requirements-ci.txt`: Python 3.12.7, numpy 1.26.4 and matplotlib 3.9.2, the laptop's versions.

**What runs where**
1. `.github/workflows/check.yml` runs on every pull request and every push to main (Ubuntu 24.04).
   - `make check` at the repo root, with `LANG` and `LC_ALL` set to C.UTF-8.
   - `python robust_design.py --check`. This includes the round-1 regression (S1, S7, S14, S16 against `equilibrium_summary.json`).
   - `python ci_sims.py compare-checks`. The new `robust_design_checks.md` must match the committed copy exactly, apart from its run-time line and the three error measures below. The JSON must match exactly, apart from floats within 1e-9 relative, and those are still listed. Any other difference fails the check.
   - Error measures are judged by threshold, not by equality (2026-10-25). `reg_maxdiff` (largest difference from `equilibrium_summary.json`) and the two identity differences are solver-versus-reference errors, so CPU rounding moves them: run 40215844769 got 1.1e-12 against the laptop's 0. `robust_design.py --check` exits 1 if any exceeds its `CHECK_TOL` threshold (1e-9, about 1000 times that noise and far below the 3 significant figures reported). `compare-checks` masks those numbers out of the comparison and applies the same thresholds, even if the committed copy is regenerated. `tests/test_check_tolerances.py` covers both, and runs in `make check`.
   - `python ci_sims.py repro` re-solves one cached ensemble (r0.1 box, base design, 64 draws) on the runner and compares it with the laptop cache, draw by draw. The job fails if any outcome changes (`act0`, or `holds`), and every changed draw is printed in the job summary.
2. `.github/workflows/sims.yml` runs only when started by hand, plus a weekly reproducibility run (Mondays 06:17 UTC: it re-solves `full__base` in 4 shards and compares it with the cache).
   - The ensemble stages (box, oat_r, radius, factorial, ensemble, oat, pilot) are split into a matrix: one job per run and shard. A shard is a share of the solver batches, solved exactly as `run_design` solves them, so a merged run equals an unsplit run on the same machine. Each job has a 350-minute limit, under GitHub's 6-hour cap.
   - The erosion and overnight-test stages run whole, in one job each.
   - A final job merges the shards, runs `robust_design.py --report` and uploads one artifact, `sims-results-<run id>`. It holds every new or changed file under `model/`, plus `ci_manifest.json` (commit, Python, numpy, OS and runner image for every shard).
   - **Nothing is committed.** Download the artifact, review it, copy the files into `model/` and commit them yourself.

**Starting a simulation run**
- In the browser: Actions tab, then `sims`, then "Run workflow". Pick the branch, the stage, the designs (a JSON list of lever dicts) and the number of shards.
- From a terminal, with the GitHub CLI:

```bash
gh workflow run sims.yml --ref main -f stage=box -f box=full -f designs='[{"seq": 1}, {"q_red": 2}]' -f shards=4
```

```bash
gh run watch
```

```bash
gh run download --name sims-results-RUN_ID
```

- `force=true` re-solves runs that are already cached and compares them with the cache, without overwriting it. Use it to test whether runner results match the laptop.
- `runner=macos-15` solves on Apple-silicon runners, which are closer to the laptop. On a public repo they are also free, but fewer can run at once.
- Locally, the same steps are `python3 ci_sims.py plan | solve | merge | repro` (see its docstring).

**Rules and known limits**
- An already-cached run is never overwritten. A re-solve that differs from the cache is reported, never hidden.
- Cross-platform floats: Linux x86-64 numpy and macOS arm64 numpy can differ in the last bits of `exp` and `log`. A draw that sits on a knife edge can then flip its outcome. The first real GitHub run will show whether this happens. If it does, the job summary lists each flipped draw with its strike probability on both machines. Decide then whether the cache should be re-solved on one platform. Do not loosen the check.
- The cache name does not record the ensemble size. A non-default `n_full` or `n_near` therefore writes to its own folder (`results/robust_runs_nfull…`), and `--report` is skipped for it. The name is only an address; reuse is decided by the run manifest (section 8b).
- GitHub turns off scheduled workflows in a public repo after 60 days with no repository activity. Re-enable the workflow in the Actions tab if that happens.

## 8b. Run identity for caches and shards (issue #6, 2026-10-25)

[[ai gen]] Status: `implemented`; `verified` by `tests/test_run_identity.py` (24 deterministic tests with a stand-in solver) and one reproducibility run in the pinned environment. Nothing `human_validated`. No committed output was regenerated.

**Problem fixed.** `run_design`, `breakout_options.run_ens` and `ci_sims.cached` found a cache by name and reused it. Only the draw count was checked, and only in `ci_sims`. A same-sized change to the draws, the seed, the ranges, the solver or the settings would silently reuse old output. Shard merges kept part metadata but did not check it.

**Run manifest** (`run_identity.py`). Every new cache is `<tag>.npz` plus `<tag>.manifest.json`. A cache is reused only if all seven identity parts match:
1. the ordered draws (SHA-256 of every value);
2. the sampling definition (box, n, seed, ranges, FIXED, NEAR_FRAC, sampler source, the baselines the boxes centre on);
3. the design (every lever after defaults, plus options, plus a hash of the solver's actual inputs);
4. the numerics (T_H, nA, N, batch size and batch membership, STRIKE_TOL);
5. the solver source (`equilibrium_model.py` and each wrapper on the solving path, after dropping comments);
6. the dependencies (numpy version, Python major.minor);
7. the output schema.

The machine (OS, CPU, commit, runner) is recorded but is not part of the identity: `ci_sims.py repro` measures cross-platform drift instead. Every load checks the .npz bytes against the manifest's SHA-256 and compares the identity part by part. A mismatch stops the run and names the parts that differ. Nothing is overwritten. `robust_report.py`, the breakout report and the diagnostics read caches through `run_identity.load_for_read`.

**Shards.** `ci_sims.py solve` writes a shard manifest for each part, holding the identity, the shard and `of`, the intended draw indices, the environment and the part's SHA-256. `merge` refuses a part if:
- it has no manifest, or its bytes were changed;
- it was solved for another identity;
- a shard is duplicated or missing, or the parts use different `of`;
- a part holds draws other than its shard's batches;
- the parts come from different platforms (OS/CPU/numpy).

`assemble` still checks that the indices are disjoint and complete. A merged run's manifest lists its shards.

**Legacy caches.** The 260 committed .npz files predate manifests. `results/cache_provenance.json` (summary: `results/cache_provenance.md`) pins each file's SHA-256 and classifies it:
- `legacy_unverified` (116): the name maps to a current request, and the draw count and fields match;
- `legacy_older_schema` (136): the same, but the file lacks `fail`;
- `reference_patched_solver` (8): `diagnostics/out`.

None is relabelled as verified. Each legacy entry records the identity its request had when the inventory was taken (pinned venv: Python 3.12, numpy 1.26.4). A later change to the draws, solver, settings or numpy therefore still refuses reuse; changes made *before* the inventory cannot be detected. `RD_REQUIRE_VERIFIED=1` refuses all legacy caches, which suits new calibration or external-model experiments. `python3 run_identity.py inventory --check` (in `make check`) fails if a cache file has neither a valid manifest nor a matching inventory entry, or if a recorded legacy file has gone missing.

**Consequence.** Reusing legacy caches for *solving* now needs Python 3.12 and numpy 1.26.4 (the pinned CI environment). Elsewhere `run_design` refuses them and asks for a re-solve into another `--runs-dir`. Reading them for reports works anywhere and prints a count of legacy files read.

## 9. Assumption register and breakout results (2026-10-21 evening)

[[ai gen]] Status: `implemented`; the register check is `verified` by its own tests; nothing `human_validated`.

**Register.** `assumptions.yaml` has 49 entries covering all 83 PARAMS. `tools/assumptions_tool.py check` runs in `make check` and fails when a PARAMS entry is missing, when a Cole answer that favours the pact has no recorded ablation, when an encoded value drifts from its PARAMS baseline, or when `human_validated` is set without Cole. `make assumptions-report` writes the ranked list (copy in `results/assumptions_report.md`). It is a separate file rather than part of `systems/model.json`, because that file is the AI Pacing governance model with a strict schema and no place for parameters or ablations.

**Breakout run** (GitHub Actions 39637590689; write-up `results/robust_design.md` 13.5 to 13.7). Any recurring cost on a cooperating AI that a strike escapes (deadline, discovery without certain amnesty, spillover) breaks the pact at year 0 with coin-flip strikes. Options acting only after a failed strike change little. A bug in the "crackdown only" and spillover world-sweep rows (they lost their capacity cut) is fixed and the sweeps re-run (13.6 item 4, 13.8).

**Recommended next ablations** (ranked by how much a headline claim depends on them and how cheap they are):
1. ~~chi0 from 0.5 to 1~~ **Done** (robust_design.md 13.8): Cole's direction is right; at chi0 1 the baseline design loses 9 of 41 near-baseline holds, and the best stack none (full box 15 to 10). My earlier PRIM-based "higher chi0 helps" was wrong.
2. **A human-chosen preventive strike or shutdown on a cooperating AI** (Cole's guess (c)). Needs a model change (a human move). Three stand-ins (deadline, discovery, spillover) all break the pact, so this is probably the largest unmodelled risk to H1 and H9.
3. **Two-sided Powell renegotiation** (Cole's guess (b)). Upward (humans pay to buy off prize-only strikes) is expected to help. Downward (humans squeeze the AI as they get stronger; AS-NOEXPLOIT, never ablated) is expected to hurt, by the same mechanism as item 2. Needs a model change. Run the downward side first.
Not recommended next, though ranked first by the register: the swarm (AS-SINGLE-AI). No cheap stand-in represents many coordinating agents faithfully; it needs a design discussion first.
