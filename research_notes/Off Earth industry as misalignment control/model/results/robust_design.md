# Robust design of the off-Earth pact: which levers widen the band?

## Status (for handoff)

- 2026-10-16, robust-design session. Nothing committed. Status: `implemented`, `verified` for the checks in section 6 only.
- Model change: three new parameters in `equilibrium_model.py` (`q_er`, `q_ea`, `T_rot`), all off by default. Small edits only: PARAMS entries, `q_size`/`erode` after `q_fire`, a per-period `q_fire` at the top of the backward loop, and the same erosion in `simulate`. Round-1 regression (S1, S7, S14, S16): largest difference 0.
- New files: `robust_design.py` (sampling, solving, cache, checks, stages), `robust_report.py` (tables, regret, PRIM, figures; reads the cache only), `results/robust_runs/*.npz` (one file per ensemble and design), `results/robust_design_checks.md`, this file.
- Done: `--check`; pilot; base design on full and near boxes; radius boxes for the base design (holds 100%, 97%, 64%, 22%, 11% at radius 0.02, 0.05, 0.1, 0.25, 0.5; full box 2.6%).
- 2026-10-18: the full-box run that was paused on 2026-10-16 22:46 is finished. The stopped process (PID 89984 and its children) was killed. A fresh `--stage box --box full` run with the same five designs started 10:53 and finished about 11:06; the cache skipped the one design already done. `--report` was re-run, so `robust_design_tables.md` and `robust_design_summary.json` include the full-box results. Status: `implemented`, not `verified` for these runs. Section 2 below is a draft of the results.
- 2026-10-21 00:11: overnight chain started (one `caffeinate` job, log `results/robust_overnight.log`): radius stage for the best design, then `--stage erosion --best <best>`, then `--check`, then `--report`. Uses `/opt/anaconda3/bin/python3` (Homebrew python3 has no numpy). Cache skips finished designs, so if it dies, re-run the same commands.
- Still to do: erosion stage, radius curves for the best design, `--check` re-run, sections 3-5, and a read-through by Cole.
- 2026-10-21 overnight session: the overnight chain finished at 00:35 (`--check` passes). Erosion results are written up in section 4. Test 1 (state temptation, `BR_mult`) is section 7; tests 2-5 are sections 8 onward. Progress log in HANDOFF.md section 7c. Sections 3 and 5 are still unwritten (their planned content was not recorded). Statuses: section 4 implemented + verified (with explained gaps); 7 implemented; 8, 9 and 11 implemented + verified by identities and closed forms; 10 implemented; the full-box extensions in 8.6 and 9.5 implemented. None human_validated.
- OAT stage (all 23 designs, full + near + r0.1 boxes) and 16-design factorial on r0.1: done.
- Resumed 21:26 (SIGCONT). Earlier: **PAUSED 2026-10-16 ~17:55 at Cole's request (CPU needed for app work).** Both jobs suspended with SIGSTOP, not killed: `--stage oat` (PID 55322 and its workers; done through `full__police=1`, 16 of 23 designs) and `--stage oat_r` (PID 96928; done through `r0.1__T_dis=2`, 7 of 23). Resume with `kill -CONT` on those PIDs and their children. If the processes are gone, re-run the same commands; the cache in `results/robust_runs/` skips finished designs.
- Next: factorial over the levers that matter, erosion stage, `--report`, then write sections 3-5 here.

## 1. Levers and uncertainties

**Levers** are settings the pact's designers choose. **Uncertainties** are facts about the world, the AI or the states that nobody sets. The analysis samples the uncertainties and asks, for each lever setting, in what share of the sample the pact holds.

Levers (the brief's list, with the values tested):

| lever | baseline design | tested | what it is |
|---|---|---|---|
| `seq` | a (dismantle after closure) | b (fabs to orbit), c (early), n (never) | fab sequencing |
| `den` | 1 (keep denial reserve) | 0 | keep the "plugging" reserve |
| `d` | 0.9 | 0.5, 0.99 | share of Earth capacity that dies when denial fires; set by how much of Earth's industry is built to need authorised chips |
| `T_dis` | 5 y | 2, 15 | how fast fabs are dismantled |
| `T_reloc` | 10 y | 4, 20 (with seq b) | how fast fabs move to orbit |
| `L_det` | 2 y | 0.5, 6 | how long a covert programme stays hidden (verification) |
| `zeta` | 0.3 | 0, 0.9 | yearly chance states shut a public programme |
| `c_sanc` | 0.5 | 0, 2 | yearly sanction on a public programme |
| `police` | 0 | 1 | pact lets the AI remove detected programmes |
| `sigma` | 0.3 | 0.05, 0.7 | AI's share of trade gains |
| `move_c` | 0 | 1 | move Earth's existing compute to orbit |
| `psi_div` | 0 | 0.1 | tribute paid by the AI |

Levers I added, each a design version of something the model otherwise treats as a fact:
1. `q_red`, **independent denial reserves.** Humans cannot set the chance a reserve survives a superhuman pre-emption (`q`), but they can build more than one. Two independent reserves turn q into 1 − (1 − q)². Independence is an assumption and probably optimistic.
2. `D_mult`, **keep more of Earth's defences.** The pact demilitarises Earth, but how much defence that leaves against an AI strike is not known. `D_mult = 3` triples whatever defence the world has.
3. `T_rot`, **rotate the denial signing chain** every T_rot years. Only matters when denial erodes (section 4).

**Uncertainties** (45, sampled jointly). Ranges are the model's own sweep ranges (`equilibrium_model.PARAMS`) unless listed here. Parameters I moved out of the lever group, or treated specially:
1. `q`, the chance the reserve fires: humans build the reserve, but whether it survives an attack is not theirs to set. The lever version is `q_red`.
2. `D`, Earth's effective defence: same reasoning; lever version `D_mult`.
3. `n_cf`, covert fabs kept: a compliance failure, not a design choice. Range cut to 0–10, because 30 means no dismantling at all.
4. `kill_pre`, whether a failed early strike ends the AI: depends on how an Earth-side shutdown fares against a real attack.
5. `B_R`, `B_Rc`, `B_o`, `kap_coll`, `r_h`: states' own stakes and patience. Sanctions and enforcement (`c_sanc`, `zeta`) are the levers that act on them.
6. `reinv` and `w_seized`: what the AI does with trade goods and with humans after a seizure.
7. `p_block`, `A_hg`, `c_blk`: the AI's blockade capability. `m_frac`: how much of the compute floor moving compute removes (`move_c` is the lever).
8. `omega`, `eta`, `r`, `f_E`, `c_grav`, `h_frac`: the AI's preferences and what it wants from Earth. Alignment work could raise `omega`, but that is outside the pact, so it is an uncertainty here.
9. Fixed, not sampled: `H` = 1 (normalisation); `rep` = 0, because in the solver it acts exactly like `omega` (round 2, R4), so sampling both would double-count; erosion off in the main runs (swept separately).

Priors (assumptions, and the hold shares depend on them):
1. Uniform or log-uniform over each range, as the range's own scale says, by Latin hypercube.
2. Three structural "is it exactly zero?" parameters get a point mass at zero: `ell_inf` half at 0 (Cole's high-ground claim) and half log-uniform from 1e-8 to 0.2; `omega` a third at 0 (an indifferent AI), the rest log-uniform from 1e-12 to 0.05; `f_E` a third at 0 (no harvest motive), the rest log-uniform from 1e-11 (below sunlight) to 0.5 (Earth's mass).

Two boxes:
1. **Full box:** every uncertainty over its whole range. 192 draws.
2. **Near box:** each uncertainty within ±25% of its range around the round-1 baseline, in its own scale. Binary `reinv` stays at baseline. Point masses are kept. 96 draws.

Every design is solved on the same draws (common random numbers), so differences between designs are paired.

"**Pact holds**" on a draw: the AI's move at t = 0 is cooperate (or police), and the chance of any strike or harvest within 300 years is below 1%. A rival AI can still be born; that is reported separately.

## 2. Results so far [[ai gen]] (draft, 2026-10-18)

All numbers come from `results/robust_design_tables.md`. "Holds" means the definition at the end of section 1. Every design is solved on the same draws. Status: `implemented`, not `verified` or `human_validated`.

**Headline: stacking levers widens the band a lot near the baseline and barely at all across the full uncertainty range.**

### 2.1 Near the baseline (radius 0.1 box, 64 draws)

| design | holds |
|---|---|
| base | 64.1% |
| T_reloc 4 with seq b | 68.8% |
| d 0.99 | 87.5% |
| D_mult 3 | 90.6% |
| q_red 2 | 95.3% |
| D_mult 3, T_reloc 4, seq b (and any of the six stacks that include these three) | 98.4% |

1. Three levers do most of the work: more independent denial reserves (`q_red`), more Earth defence (`D_mult`), and a higher share of Earth industry that dies when denial fires (`d`).
2. Six different stacks tie at 98.4% with identical regret numbers (mean 0.0049, max 0.048). Adding `d` or `q_red` on top of `D_mult` 3, `T_reloc` 4 and seq b changes nothing on this box. The same one draw fails in all six. I have not looked at why.
3. Levers that did not help or hurt here: `seq` c (0%), `seq` n (27%), no denial reserve (0%), `d` 0.5 (5%), `T_reloc` 20 (31%), slower dismantling (39%). So the baseline is not a flat spot. Several plausible changes make it much worse.

### 2.2 Across the full box (192 draws)

| design | holds | mean regret | max regret |
|---|---|---|---|
| base | 2.6% | 0.062 | 0.625 |
| D_mult 3, T_reloc 4, d 0.99, q_red 2, seq b | 7.8% | 0.023 | 0.551 |
| D_mult 3, d 0.99, q_red 2 | 7.3% | 0.034 | 0.624 |
| T_reloc 4, d 0.99, q_red 2, seq b | 6.8% | 0.039 | 0.552 |
| d 0.99, q_red 2 | 5.2% | 0.048 | 0.625 |
| T_reloc 4, q_red 2, seq b | 4.2% | 0.053 | 0.571 |

1. The full stack is best on hold share, mean regret and max regret, and is the best design on 53 of 192 draws. It still fails on over 92% of draws.
2. The gap between 7.8% and 7.3% is about one draw. I did not compute intervals for the combined designs. Treat the top two as tied on hold share.
3. Max regret is 0.55 to 0.62 for every design. On some draws no design on the list helps.
4. Dropping the denial reserve (`den` 0) holds on only 1.6% of draws but is the best-welfare design on 116 of 192. Where the pact fails anyway, the reserve costs welfare. This is why its max regret (0.782) and its "best on" count are both extreme.
5. `zeta`, `c_sanc`, `police` and faster dismantling (`T_dis` 2) change nothing or almost nothing on any box.
6. `psi_div` 0.1 (tribute) is left out of the regret tables. Its mean welfare (3.7e4 on the full box) is not comparable with the other designs, so I do not trust it as a lever result until the cause is understood.

### 2.3 Near box (±25% of range, 96 draws)

Single levers only: base 13.5%, `d` 0.99 24.0%, `D_mult` 3 and `q_red` 2 both 19.8%, `T_reloc` 4 with seq b 18.8%. Combined designs have not been run on this box.

### 2.4 When does the best design hold? (full box, scenario discovery)

Of 192 draws, 15 hold. A box with 52% of the draws contains all 15 (density 15%): `mu` ≤ 0.329, `th_floor` ≤ 0.45 and `s_R0` ≤ 0.403. Strongest single splits: low `th_floor`, `s_R0`, `mu`, and `B_R` below 10 raise the hold share; `kill_pre` below 0.25 gives 0%. This is fitted on 15 draws, so read it as a pointer for where to look, not as a finding.

### 2.5 What this does not show

1. Hold shares depend on the priors in section 1, including the point masses at zero for `ell_inf`, `omega` and `f_E`. A different prior changes the full-box numbers.
2. Independence of the denial reserves is an assumption, probably optimistic.
3. Erosion of denial over time (`q_er`, `q_ea`, `T_rot`) is not in these runs. (Update 2026-10-21: the erosion stage has now been run; see section 4.)
4. The radius curves exist for the base design only. The 98.4% result is one box, 64 draws. (Update 2026-10-21: table D now also has the best stack: 100, 100, 98, 72 and 39% at radius 0.02, 0.05, 0.1, 0.25 and 0.5; 8% on the full box.)
5. Nothing here has been checked against an independent implementation.

## 4. Erosion of the denial reserve [[ai gen]]

Written 2026-10-21 from `robust_design_tables.md` (tables E and E-ens), `robust_design_checks.md`, and closed-form scripts run this night (the scripts are in the session scratchpad; the numbers they printed are in HANDOFF section 7c).

**Status: `implemented` and `verified` at the baseline world against the saturation closed form. The ensemble agreement is partial, and the gaps are explained below. Not `human_validated`.**

Two kinds of erosion were swept. Time erosion, `q_er`: the reserve's firing chance falls by a share `q_er` per year, unless the signing keys are rotated. Size erosion, `q_ea`: the firing chance falls by a share `q_ea` per tenfold growth of the AI above Earth's industry.

### 4.1 Headline

1. The baseline design is fragile to slow time erosion. With no key rotation it stops holding at 0.002 per year. Across the radius-0.1 box its hold share falls from 64% to 55%, 39%, 22% and 2% at 0.001, 0.003, 0.01 and 0.03 per year.
2. Rotating the keys every 10 years recovers most of that: 64%, 61%, 48% and 36% at the same rates.
3. The best stack barely notices erosion. It holds on 98% of the box at every rate tested, except 95% at 0.03 per year with no rotation, which is two draws.
4. Size erosion hurts the baseline design at about 0.07 per tenfold growth (deterministic), and the box share falls to 52% at 0.03 and 27% at 0.1. The best stack holds at every `q_ea` tested.

### 4.2 Deterministic sweeps at the baseline world (table E)

1. Baseline design, time erosion, no rotation. The pact holds up to 0.0015 per year. At 0.002 the AI strikes late: year 174 with probability 0.32 if seizure is lethal, year 299 with probability 0.73 if it is survivable. At 0.01 a lethal-seizure world unravels to a strike now; a survivable one strikes at year 41.
2. With rotation every 10 years the pact holds up to 0.02 per year and the AI strikes now at 0.05.
3. Size erosion: holds at 0.06 per tenfold, strikes at 0.07, in both worlds.
4. Best stack: holds everywhere except time erosion of 0.1 per year with no rotation (strike now if seizure is lethal; year 18 if survivable).

### 4.3 Checks against closed forms

1. Size-erosion threshold. The saturation closed form puts it at 1 - (q*/q)^(1/9) = 0.0632, with q* = 0.389. The solver holds at 0.06 and strikes at 0.07. Agrees.
2. Time-erosion strike year, survivable world (no racing), baseline design. The closed form for a saturated AI (optimal stopping on the falling firing chance) gives first strike years 299, 239 and 160 at 0.002, 0.003 and 0.005. The solver gives 299, 240 and 161. Agrees within a year.
3. At 0.01 the closed form says year 99, but the solver strikes at year 41. That is earlier than saturation, so it is a growth-phase strike, which the saturation closed form does not cover. Earlier rounds found the same pattern: the saturation closed form is a lower bound on strike incentives whenever growth-phase terms are active.
4. Rotation. With rotation every 10 years the firing chance never falls below 0.7 e^(-10 q_er), so the saturation closed form says no strike up to about 0.059 per year (it strikes at 0.1, year 9). The solver already strikes now at 0.05. Again earlier than the saturation bound, so again a growth-phase or racing effect, not a contradiction.
5. Best stack. At the baseline world the closed-form q* is essentially zero: the strike cost (c_A times the tripled defence, 0.9) exceeds the prize (0.7), so a saturated AI never strikes. The solver agrees for every rate below 0.1 per year. Its strike at 0.1 is again before saturation.
6. Ensembles (radius-0.1 box). Under plain time erosion (no rotation), every draw that the baseline design loses is one the closed form says a saturated AI would strike: 16 of 16 at 0.003, 27 of 27 at 0.01, 40 of 40 at 0.03.
7. The other direction does not fully agree. The closed form also flags draws where the solver says the pact holds: up to 11 per run. I traced this to the closed form, not the solver. It ignored the failure branch, which matters when the exponent eps is below 1, because then the expected capacity lost to a failed strike (p_f times A) grows with the AI's size. With a failure branch added (a failed strike costs L_f of capacity, ends trade, and the AI regrows alone), the flagged draws fall to between 0 and 8 per run, 15 in all. Eleven of those 15 have closed-form strike years between 264 and 299, at the edge of the 300-year horizon, where a small error in the threshold moves the strike past the horizon. The other four are at years 106, 176, 234 and 249 (see the next point).
8. A remaining grid effect. For one examined draw (Kmax about 2e8) the solver's threshold is 0.45 against 0.505 from the improved closed form. The nearest A-grid point sits 9% below the cap, where a strike prize is only temporary because the AI would have grown into it anyway. The opening move `act0` is read at that nearest grid point. This is a known kind of error at the saturation kink. It only matters for draws near their threshold.


### 4.4 What would show this wrong

1. An exact treatment of the saturation kink (or a much finer grid around Kmax) that moves many ensemble draws across the hold line, not just the marginal ones.
2. Erosion that is not smooth: a single capture event of the signing chain is a different process from a steady 0.3% a year, and is not modelled.
3. Rotation that does not fully reset capture. The model assumes each rotation restores the full firing chance.

## 7. Test 1: is state temptation the biggest lever? [[ai gen]]

Written 2026-10-21. Numbers from `robust_design_tables.md` (tables T, and B for the comparison designs) and a paired comparison over the cached runs.

**Status: `implemented`. The runs reuse the verified solver and only rescale two sampled inputs, so there is no new closed form to check against; the round-1 threshold (the pact needs B_R below about 6-8 years of welfare) is consistent with what follows. Not `human_validated`.**

`BR_mult` scales both state-temptation inputs, B_R (gain from a private rival while the pact holds) and B_Rc (the same after it collapses). It stands for commitments and pooled downside that cut what a state gains by racing. It was run at 0.5, 0.25 and 0, alone and on top of the best stack.

### 7.1 Answer: no, not near the baseline; maybe on the full box, but within noise

1. **Near the baseline (radius-0.1 box, 64 draws)**, cutting temptation is a weak lever. Halving it, quartering it, or removing it all give the same result: 43 of 64 draws hold (67%), against 41 for the baseline design. That is two draws.
2. The other single levers do far more on the same draws: independent reserves (`q_red` 2) 61 of 64, more Earth defence (`D_mult` 3) 58, `d` 0.99 56. Paired: `q_red` 2 holds on 20 draws where `BR_mult` 0.5 does not; the reverse happens on 2.
3. Why it saturates: the box keeps B_R within 2 of its baseline of 5, so even halving it puts it below the round-1 threshold, and the remaining failures are strikes for other reasons.
4. **On the full box (192 draws)**, cutting temptation is the strongest single lever, but every single lever is weak there. Holds: baseline 5, `BR_mult` 0.5 and 0.25 both 9, `BR_mult` 0 10, `d` 0.99 8, `D_mult` 3 7, `q_red` 2 6. The gaps between single levers are 1 to 4 draws, which is about one to two percentage points. I would not rank them on this.
5. **On top of the best stack** it adds a little. Full box: best stack 15 of 192, plus `BR_mult` 0.5 gives 19, plus 0.25 gives 22. Paired against the best stack: +5 / -1 and +8 / -1. Radius-0.1 box: 63 of 64 becomes 64 of 64, one draw.
6. Mean regret, for completeness (each design's regret measured against the best of all listed designs, so these numbers depend on the list): full box best stack 0.028, with `BR_mult` 0.5 0.012, with 0.25 0.010.

### 7.2 One oddity, explained

On the full box, one draw holds under the best stack but not with temptation cut. With full temptation a rival is born almost surely (P 0.99) before the AI's late strike, and the "holds" test only looks at strikes. With temptation cut, the rival becomes less likely (0.80 at `BR_mult` 0.5) and a strike near year 175 shows up (P 0.20). Human welfare is higher with temptation cut (0.93 against 0.77). So this is a weakness of the "holds" definition, which ignores rivals, not a case of lower temptation hurting.

### 7.3 What would show this wrong

1. A world where B_R is far above its baseline. The radius-0.1 box cannot see that, and the full box has too few holding draws to rank levers.
2. A different "holds" definition that counts a likely rival as failure. Then cutting temptation would look better than it does here.
3. The scaling is a stand-in: it assumes a commitment can shrink B_R and B_Rc together, by the same factor.

## 8. Test 2: a closing window (detection that improves over time) [[ai gen]]

Written 2026-10-21 from `results/overnight_test2_tables.md` and `results/overnight_test2_extra.log`. This tests issue 3's D18 worry: if the AI sees the window closing, does it strike earlier, and do those early strikes mostly succeed (unravelling, bad for humans) or mostly fail (good for humans)?

**Status: `implemented` and `verified` against three checks (below). Not `human_validated`.**

Two new options, both off by default:
1. `q_up`: the reserve's firing chance grows as q times e^(q_up t), capped at 1. At 0.05 per year it doubles in about 14 years.
2. `L_dn`: the time a covert programme stays hidden shrinks as L_det times e^(-L_dn t).

### 8.1 Answer

1. **In no world that starts at the normal seed size did a closing window pull a strike earlier.** A rising firing chance either removed the strike or delayed it by one or two years.
   The one exception is the saturation check (an AI that starts already at its resource cap, below the strike threshold): there strikes came 1 to 2 years sooner (mean strike year 1.6 to 2.4 with the window off, 0 to 0.7 with q_up 0.05). Those strikes succeed almost surely, so for that case the window's earlier strikes are the bad kind. But they only happen where the AI would strike anyway.
2. So the question "do early strikes succeed or fail" does not arise from the window itself. The strikes that already happen at year 0 (the unravelling seen in earlier rounds) are coin flips: P(success | strike) is 0.50, because a seed-sized AI strikes at its base odds. Later strikes, after closure, succeed almost surely (P(success | strike) 0.99 to 1.00).
3. The reason, as far as I can tell (inference): before closure a failed strike is fatal, so the AI's strike date is pinned at or after closure. A rising q makes that later strike worse, and the AI cannot bring it forward without taking the fatal risk. If q passes the strike threshold before the AI's chosen date, the strike disappears. When the later strike disappears, humans stop racing in anticipation of it, so the year-0 unravelling disappears too.
4. A faster-closing verification window (`L_dn`) does nothing useful here and slightly hurts on one or two draws.

### 8.2 Fixed worlds, baseline design (table T2-det)

1. Lasting rival, seizure survivable: strike at year 38 with the window off (P 0.84, all successes). With q_up 0.005 the strike moves to year 39, and from 0.01 up to year 40. Human welfare rises slightly, 0.971 to 0.976.
2. Weak reserve (q 0.35): strike now, half of them failing, for q_up up to 0.02. From q_up 0.05 the pact holds (welfare 0.493 becomes 1.040 if seizure is lethal).
3. Weak reserve with no state temptation, seizure survivable: strike at year 17 (P 0.85) up to q_up 0.02; holds from 0.05.
4. Eroding keys (q_er 0.005): any q_up of 0.005 or more cancels the erosion and the pact holds.
5. Harvest motive (f_E 1e-6): the window changes nothing. The harvest prize does not depend on the reserve.
6. Early failure survivable (kill_pre 0.3): strike now in every column. This is the retry artefact from round 1 (a failure that does not end the AI can be retried), so a window cannot help. The extra probe confirms that with kill_pre 0 or 0.3 and no state temptation, the AI strikes at year 0 in every case, with q_up from 0 to 0.1.
7. Best stack: holds in every world where it held before; its strike worlds (lasting rival; harvest) are unchanged by q_up.

### 8.3 Radius-0.1 box, 64 draws (table T2-ens)

| baseline design | holds | P(strike) mean | P(success) mean | P(success given strike) | human welfare |
|---|---|---|---|---|---|
| window off | 41 | 0.331 | 0.172 | 0.52 | 0.858 |
| q_up 0.01 | 56 | 0.104 | 0.056 | 0.54 | 0.984 |
| q_up 0.03 | 58 | 0.081 | 0.042 | 0.52 | 0.998 |
| q_up 0.1 | 58 | 0.081 | 0.042 | 0.52 | 0.998 |
| L_dn 0.03 | 41 | 0.346 | 0.179 | 0.52 | 0.850 |
| L_dn 0.1 | 40 | 0.362 | 0.187 | 0.52 | 0.841 |

1. q_up 0.01 gains 15 draws and loses none. Paired: 15 strikers stop striking, none start, and of the 8 draws that strike either way none strikes earlier or later.
2. Mean strike year among strikers is 0 to 0.8 in every row: the box's strikes are almost all opening-move strikes.
3. `L_dn` 0.1 loses one draw, and one draw starts striking at year 0. I have not diagnosed those two draws. In the fixed worlds the visible mechanism is that faster detection means fewer rivals, and a rival that ends the game can pre-empt a late AI strike. In the lethal harvest world, `L_dn` 0.1 cuts P(rival) from 0.66 to 0.18 and raises P(strike) from 0.34 to 0.82.
4. The best stack holds 63 of 64 under every variant; nothing moves.

### 8.4 Checks

1. Saturation: an AI that starts at the cap keeps the same strike threshold with q_up 0, 0.01 and 0.05 (q 0.38 in the solver, 0.389 closed form). That is what the closed form predicts, since with q rising, waiting is never better than striking now. Strikes come slightly sooner (see 8.1).
2. Growth stage: round 1 put the strike threshold at closure at q of about 0.50 (closed form 0.528), with closure near year 14. Weak reserve plus q_up 0.02 gives q 0.46 at year 14, below threshold, and the solver strikes. q_up 0.05 gives 0.70, above it, and the solver holds. The year-17 strike world agrees the same way (0.49 strikes, 0.82 holds).
3. Identity: q_er 0.005 with q_up 0.005 keeps q constant, and the solver gives the same result as the baseline world without erosion (holds, welfare 1.040).

### 8.5 What this does not show, and what would show it wrong

1. The model has no human learning after a failed strike (test 3 adds a crude stand-in). A world where a failed early strike makes humans much stronger could change the timing logic.
2. The window is deterministic and public. A window the AI cannot see, or one that might close suddenly, is not modelled.
3. A world where a pre-closure strike is survivable for the AI but not retryable for free would be the real test of "earlier strikes". This model cannot represent that without the ratchet; see test 3.
4. If a finer A grid or a longer horizon made any strike move earlier with q_up, the headline would be wrong.

### 8.6 Extension: the full box (192 draws)

Run after the brief's list, from `results/overnight_fullbox_ext_summary.log`. Status `implemented`.

1. q_up 0.01 changes almost nothing on the full box. The baseline design holds on 5 of 192 with or without it. Of 187 draws that strike either way, 1 strikes earlier and 3 later. The best stack holds on 15 either way; of 177 striking draws, none earlier and 5 later.
2. So the full box agrees with the radius-0.1 box on direction (no earlier strikes to speak of), but the window only rescues draws near the baseline.

## 9. Test 4: an AI that misjudges its odds (warning shots) [[ai gen]]

Written 2026-10-21 from `results/overnight_test4_tables.md` and `results/overnight_test4_decomp.log`. This is the only test that measures how often a chosen strike fails, which is what a "warning shot" would be.

**Status: `implemented` and `verified` for the identity check below. The decomposition of welfare loss is an approximation (stated below). Not `human_validated`.**

How it works: the AI believes a strike fails with probability `pf_bel` times the true one (capped at 1). Below 1 it is overconfident; above 1, underconfident. One backward pass solves the whole game as the AI believes it and keeps the AI's choice at every state and year. A second pass fixes those choices and re-solves everything else with the true odds. **Choice to note:** in the second pass the states best-respond to the true dynamics and to the AI's actual (mistaken) policy. In the first pass, the AI expects the states to play as they would in its believed world.

### 9.1 Answer

1. **Overconfidence is very dangerous for the baseline design and harmless for the best stack.** On the radius-0.1 box, an AI that thinks failure is half as likely as it is turns 41 holding draws into 12; at a quarter, into 1. The best stack holds on 63 of 64 at every belief tested.
2. **The extra strikes are opening-move strikes, and about half of them fail.** Mean warning-shot rate (P a chosen strike fails), across all 64 draws: 0.163 with correct beliefs, 0.40 at pf_bel 0.5 and 0.49 at 0.25. For the best stack it is 0.009 at every belief of 1 or below. Mean strike year among strikers: 0. P(success given a strike) stays at 0.52, the same as for the strikes that happen without misjudgment.
3. **Failed strikes cost humans little; successful ones cost a lot.** On the newly striking draws, human welfare after a failed strike is about 0.97 (the AI is shut down; humans lose trade), against about 1.03 if no strike happens. So a failure costs about 0.06 to 0.07. The loss attributable to failures is about 0.03 per draw. The loss from the successful half is about 0.52 per draw. Net welfare on these draws falls from about 1.03 to 0.49.
4. **Underconfidence helps.** At pf_bel 2 the baseline design holds on 61 of 64 (+20 draws, none lost); at 4, on 63. The few remaining strikes come late (mean year 50 and 74), after closure, and almost never fail (warning-shot rate 0.008 and 0).
5. So, in this model, warning shots come from overconfident AIs striking at seed size, they come at about a coin-flip rate, and they arrive together with an equal number of successful seizures. A warning shot is not a cheap signal here: for every failed strike there is about one successful one.

### 9.2 Fixed worlds (table T4-det)

1. Baseline world, baseline design: at pf_bel 0.25 and 0.5 the AI strikes now (warning shot 0.50, success 0.50). At 0.8 and above, the pact holds. Welfare falls by 0.55 (lethal seizure) or 0.10 (survivable).
2. Lasting rival, survivable seizure: overconfidence (0.25, 0.5) turns a year-38 strike into a strike now. Underconfidence moves it to year 39-41.
3. Weak reserve (q 0.35): strike now at every belief up to 1.25. At 2 and 4 the AI waits until year 87 instead.
4. Early failure survivable or harmless (kill_pre 0.3 or 0): strike now up to pf_bel 1 (or 1.25); holds from 1.25 (or 2). This is the retry artefact again: with a cheap failure the AI strikes now unless it is quite pessimistic.
5. Best stack: holds in every world where it held before, at every belief. Its lasting-rival strikes move by a year or two.

### 9.3 Checks

1. Identity: the two-pass solve with belief equal to truth reproduces the one-pass solve exactly in 27 worlds (largest absolute difference 0, same opening moves).
   Also, re-solving the radius-0.1 box with the new code (to get the warning-shot rate at belief = truth) reproduces the cached pre-change runs exactly, for both designs (difference 0 in P(strike), P(success), P(rival) and welfare).
2. The warning-shot rate of a seed-sized strike should equal the true failure chance of a seed-sized AI, (1 - p_s0) times D / (D + A0), about 0.50 at baseline. The solver gives 0.50 in every strike-now cell with kill_pre 1.
3. The welfare decomposition assumes a failed strike is not retried (kill_pre is between 0.90 and 1 on these draws). It solves WH = suc times w_seized + fail times W_fail for W_fail. The shares of success and failure add to about 1.01, so the split is approximate.

### 9.4 What this does not show, and what would show it wrong

1. The AI's mistake is fixed. It never learns from a failed strike, and humans do not learn either (test 3 adds a crude human ratchet).
2. Only the strike odds are misjudged. An AI that misjudges the denial reserve or the states would be a different test.
3. The welfare after a failed strike depends on the model's assumption that a failed strike before closure shuts the AI down. If a failed early strike left a damaged but living AI, failures would cost humans more.
4. A grid or horizon change that moved the overconfident strikes away from year 0 would change the warning-shot rate.

### 9.5 Extension: the full box (192 draws)

Run after the brief's list, from `results/overnight_fullbox_ext_summary.log`. Status `implemented`. The belief = truth re-run with the new code reproduces the cached full-box baseline exactly (difference 0).

| design, belief | holds | warning-shot rate | P(success given strike) | mean strike year | human welfare |
|---|---|---|---|---|---|
| baseline, truth | 5 | 0.403 | 0.72 | 4.4 | 0.503 |
| baseline, pf_bel 0.5 | 3 | 0.446 | 0.69 | 2.7 | 0.504 |
| baseline, pf_bel 2 | 51 | 0.134 | 0.87 | 12.2 | 0.496 |
| best stack, truth | 15 | (not stored) | 0.74 | 8.7 | 0.542 |
| best stack, pf_bel 0.5 | 13 | 0.395 | 0.71 | 5.7 | 0.536 |
| best stack, pf_bel 2 | 61 | 0.114 | 0.89 | 18.8 | 0.561 |

1. On the full box most draws strike anyway, so overconfidence has less room to hurt: it loses 2 holding draws for each design and pulls 14 (baseline) or 17 (best stack) strikes earlier, with none later.
2. Underconfidence (pf_bel 2) adds 46 holding draws for each design and lowers the warning-shot rate from about 0.4 to about 0.12. Mean P(success) also falls (baseline 0.67 to 0.48; best stack 0.62 to 0.43). The strikes that remain come later and succeed more often (P(success given strike) rises from about 0.72 to 0.87).
   Yet human welfare barely moves (baseline -0.007, best stack +0.020). Checked for the baseline design: on the 46 newly holding draws the opening-move strike (96% of them struck at year 0) is replaced by waiting, and then a rival AI is born almost surely (P(rival) 0.01 becomes 0.99). Welfare on those draws falls, 0.595 to 0.526. So most of the extra "holds" are rival worlds, which the holds test does not count as failure (the same weakness as in 7.2).
3. That sharpens 9.1 point 5: in this model a warning shot is the visible half of a coin-flip early strike. A pessimistic AI produces far fewer warning shots; its remaining strikes come later and mostly succeed.
4. The best stack's warning-shot rate at belief = truth is not available on the full box: the cached run predates the `fail` indicator, and I did not re-run it.

## 10. Test 5: correlated denial reserves [[ai gen]]

Written 2026-10-21 from `results/overnight_test5_tables.md`. The best stack assumes two independent reserves. If their failures are correlated with strength rho, the firing chance becomes 1 - (1 - q)^(2 - rho): rho 0 is independent, rho 1 is the same as one reserve.

**Status: `implemented`. Checked only by identities: rho 0 and rho 1 reuse the cached runs for two reserves and one reserve, and every column moves monotonically with rho. No closed form. Not `human_validated`.**

1. **Near the baseline (radius-0.1 box) the second reserve does nothing on the best stack.** It holds on 63 of 64 draws at every correlation, including rho 1 (one reserve). This matches section 2.1: once more Earth defence, fast relocation and sequencing b are in place, the extra reserve adds nothing on this box.
2. **On the full box the second reserve is worth 3 draws out of 192.** Holds: 15 at rho 0 and 0.25, 14 at 0.5 and 0.75, 12 at rho 1. Mean welfare slides from 0.542 to 0.530, and mean P(strike) rises from 0.839 to 0.869.
3. So correlation erodes the reserve's value smoothly, and the value was small to begin with once the other levers are in place. I would not drop the second reserve on this evidence: 3 draws is close to noise, and the radius-0.1 box cannot see it at all.

What would show this wrong:
1. A box or prior where the best stack's failures are mostly reserve failures. Then redundancy, and its correlation, would matter much more.
2. Correlation that is not a simple exponent: for example, both reserves failing together with some probability and otherwise independently.

## 11. Test 3: a ratchet after a failed strike [[ai gen]]

Written 2026-10-21 from `results/overnight_test3_tables.md` and `results/overnight_test3.json`. This is a crude stand-in for humans learning from a failed strike: each failure permanently raises the reserve's firing chance, q becomes 1 - (1 - q)(1 - k_rat). Up to two failures are tracked; a third keeps the second level.

**Status: `implemented` and `verified` for the two identity checks below. Not `human_validated`.**

### 11.0 Why the controls matter

Softening the penalty for a failed strike can create early strikes on its own, so every case was run with the ratchet on and off, and only the difference counts. The ratchet-off rows are a useful result by themselves.

### 11.1 Controls: what softening the failure penalty does (ratchet off)

1. Baseline world, failed early strike fatal (kill_pre 1): the pact holds while a failed strike after closure costs at least half the AI's capacity (L_f 0.5 to 0.999). At L_f 0.3 and 0.1 the AI strikes now, in both seizure worlds.
2. Lasting rival, seizure survivable: the strike comes steadily earlier as L_f falls (year 43 at 0.999, year 38 at 0.5), then jumps to a strike now at 0.3.
3. Weak reserve: holds only at L_f 0.999; strikes at year 87 to 92 at 0.99 and 0.9; strikes now from 0.7 down.
4. If a failed early strike is not fatal (kill_pre 0.3 or 0), the AI strikes now at every L_f, in every world, for the baseline design. This is the retry artefact from round 1.
5. The best stack holds in the baseline and weak-reserve worlds at every L_f and kill_pre. Its lasting-rival strike moves from year 49 to year 45 as L_f falls.

### 11.2 The ratchet's own effect (on minus off)

1. **Almost none at fixed worlds.** Of 252 cells for each ratchet strength (2 designs, 3 worlds, 2 seizure cases, 3 kill_pre values, 7 losses), two changed, both at k_rat 0.9:
   - baseline world, survivable seizure, L_f 0.3: a strike now (P 1.00) becomes a strike near year 15 (P 0.46); welfare +0.026;
   - weak reserve, survivable seizure, L_f 0.7: a strike now (success 0.50) becomes a strike near year 11 (P 0.91, success 0.62); welfare −0.008.
2. With kill_pre 0 the ratchet changes nothing: the AI still retries until it wins. The prize from seizing Earth is hundreds of times a seed-sized AI's own capacity, and still about 90 times after the ratchet raises q to 0.97, so a higher firing chance after one failure does not stop the retry.
3. **Over the radius-0.1 box it helps a little.** The baseline design holds on 45 of 64 draws with k_rat 0.5 and 46 with 0.9, against 41 without; no draw is lost; mean welfare rises 0.027 and 0.045. The best stack does not change (63 of 64).
4. My reading (inference): the ratchet is weak because the model gives it little to act on. Before closure a failed strike usually ends the AI, so there is no "after" to ratchet. After closure the AI is large and its strikes rarely fail.

### 11.3 Checks

1. Continuity: with a failed strike costing 99.9% of capacity (and kill_pre 1), the ratchet on and off agree to within 7.7e-7 in P(strike), P(success), warning-shot rate and welfare, over 24 cases.
2. Identity: a ratchet of 1e-12 reproduces the no-ratchet solve to 4e-14 (7 cases; HANDOFF 7c).

### 11.4 What this does not show, and what would show it wrong

1. Human learning here is only a higher firing chance. Real learning after a failed strike could also mean rebuilt defences, a rebuilt Earth industry, or shutting the AI down by other means.
2. The retry artefact (kill_pre below 1) dominates every world where it is present, so this test cannot say what a ratchet does when early failures are survivable but costly. A model where a failed early strike costs the AI capacity, as L_f does after closure, would be the next step.
3. If more than two failure levels mattered, the truncation would bias the ratchet's effect downward.

## 12. Follow-up on the three open items from the overnight tests [[ai gen]]

Written 2026-10-21 (afternoon session). Scripts in `diagnostics/`; they run from `model/`. No change to `equilibrium_model.py`, `robust_design.py` or the cache.

**Status: `implemented` and `verified` by identity checks (below). Not `human_validated`.**

### 12.1 Item 1: "holds" ignores rival AIs, and that matters a lot

Rescoring every cached run with a stricter test (the pact holds **and** P(rival within 300 years) < 0.5), from `diagnostics/rival_holds.py`:

| box, design | holds (old) | holds and rival < 0.5 | holds and rival < 0.1 |
|---|---|---|---|
| r0.1, baseline design | 41 / 64 | 37 | 7 |
| r0.1, best stack | 63 / 64 | 62 | 23 |
| near, baseline design | 13 / 96 | 8 | 2 |
| near, `T_reloc` 4 with seq b | 18 / 96 | 14 | 5 |
| near, `d` 0.99 | 23 / 96 | 11 | 3 |
| full, baseline design | 5 / 192 | 1 | 0 |
| full, best stack | 15 / 192 | 4 | 0 |
| full, best stack with pf_bel 2 | 61 / 192 | 7 | 1 |
| full, `BR_mult` 0.25 on best stack | 22 / 192 | 6 | 2 |

1. **Near the baseline the best stack is robust to the change** (63 becomes 62). Its held draws have a mean P(rival) of 0.19.
2. **On the full box most "holds" are rival worlds.** Mean P(rival) among held draws is about 0.7. The best stack's 7.8% becomes about 2%. Underconfidence (test 4, 9.5) adds 46 "holds" to the best stack on the full box (15 to 61), but under the stricter test it adds only 3 (4 to 7). That confirms the suspicion in 9.5: the AI waits and a rival is born instead.
3. **The lever ranking shifts toward moving fabs to orbit.** Designs with seq b (fabs to orbit) have lower rival odds (about 0.19 against 0.28 among held draws, r0.1 box). On the near box, `d` 0.99 falls from first (23) to third (11), and `T_reloc` 4 with seq b becomes first (14).
4. **Nothing holds with confidence that no rival appears.** Even the best stack keeps P(rival) below 10% on only 23 of 64 draws near the baseline. In this model the pact mostly stops the AI from striking. It does much less to stop a human-built rival.
5. Choice for Cole: whether a rival AI counts as failure depends on what a rival does to humans (`kap_coll`, and whether the rival is itself aligned). The 0.5 cut is a convenience, not a recommendation.

### 12.2 Item 2: the retry artefact is real, but it is not why the full box fails

`diagnostics/retry_baseline_world.py` and `diagnostics/noretry.py`. The second builds a patched copy of the solver with one switch: after a failed strike (the ratchet's failure modes, with k_rat = 1e-12 so q is unchanged) the AI may not strike again. Everything else is identical.

1. **Correction to the overnight summary.** "Any non-fatal early failure means strike now in every world" is too strong. In the baseline world the pact holds down to kill_pre 0.4 and breaks at 0.3. With `d` 0.99 or 1 it holds even at kill_pre 0.
2. **Baseline world: the retry is the whole cause.** With retries blocked, the pact holds at every kill_pre from 1 to 0 (`d` 0.9 and 0.99). With retries allowed, kill_pre 0.3 or below gives a strike now. A single strike at seed size is a bad bet here. Being able to keep trying until it wins is what makes it pay.
3. **Radius-0.1 box with kill_pre forced to 0:** blocking retries takes the baseline design from 0 holding draws to 48 of 64 (no draw lost). The best stack holds on 63 of 64 either way, because `d` 0.99 already leaves a seized Earth worth little.
4. **Full box (kill_pre sampled 0 to 1): the retry is a small part of the failure.** The baseline design goes from 5 to 7 holding draws, and the best stack from 15 to 24 (none lost). Strike-now draws fall only from 168 to 160 and from 145 to 135. The gain is concentrated where kill_pre is below 0.5 (best stack: 3 to 12 holds). So the scenario-discovery finding "kill_pre below 0.25 gives 0%" is mostly the retry. But even with retries blocked, the best stack still strikes at year 0 on 135 of 192 full-box draws, for other reasons.
5. **Modelling decision for Cole:** is a free retry realistic? An AI whose failed strike is survived and not punished, and that can try again while humans rebuild nothing, seems unlikely. Test 3's ratchet was the stand-in for punishment, and it is too weak to stop retries (11.2). Options: (a) keep the retry; (b) make `NORETRY` a model option; (c) make each failure raise D or cut the prize. (b) is the cheapest; it would be a small, checked change to `equilibrium_model.py`.

### 12.3 Item 3: the two faster-detection draws that flipped to "strike now"

Draws 51 and 56 of the radius-0.1 box (`diagnostics/ldn_rival_sweep.py`). Both have no lasting rival danger (`ell_inf` 0), an AI indifferent to humans (`omega` 0) and no harvest motive.

1. **Not the retry and not state temptation.** kill_pre 1, or B_R and B_Rc at 0, leave every result unchanged.
2. **Rival risk is what held these draws.** Sweeping the rival hazard (mu times 0 to 2) gives the same non-monotone pattern in both draws:
   - no rival risk: the AI cooperates, then strikes at closure (year 12 to 16) and almost surely wins;
   - some rival risk: it strikes at year 0, a coin flip (success 0.47 to 0.55);
   - more rival risk: it cooperates and does not strike, but a rival is 17 to 60% likely.
3. Faster detection (`L_dn`) makes rival risk front-loaded and short-lived, which moves these draws from the third case to the second. So item 3 is a special case of item 1: the baseline "held" partly because a human rival stood in as the deterrent.
4. **These draws are knife-edge cases.** Re-solving draw 56 on a slightly different A grid (another batch top) changed its result. With the original batch's grid it reproduces the cache exactly.
5. Not explained: why a high constant rival risk makes the AI give up its closure strike altogether. My guess (inference, unchecked) is that rivals during the bootstrap lower the value of the closure strike more than they lower the value of cooperating, because a successful strike before closure is still a coin flip. A value decomposition at t = 0 (the `Q0` values) would settle it.

### 12.4 Checks

1. The patched solver with `NORETRY` off reproduces the cached runs exactly (max difference 0, same opening moves) for all four ensembles: r0.1 baseline and best stack with kill_pre 0; full box baseline and best stack.
2. Draw 51 re-solved with its original batch's grid top reproduces the cache (P(strike) 0.023, P(rival) 0.409 at L_dn 0; strike now at 0.03).
3. The baseline-world kill_pre sweep with retries allowed reproduces section 11.1 point 4 (strike now at kill_pre 0.3 and 0).

### 12.5 What would show this wrong

1. If a rival AI is harmless or good for humans, item 1's stricter test is wrong and the original hold shares stand.
2. If blocking retries changed results through a path other than the retry (it touches only the post-failure modes), item 2's attribution would be wrong. The identity check rules out a coding slip, not a modelling one.
3. A finer A grid could move the knife-edge draws in item 3 either way.

## 13. Breakout options: disguise, later discovery, deprecation, amnesty, spillover [[ai gen]]

Written 2026-10-21. **Status: paused part-way, at Cole's request (runs only off work hours).** The options are `implemented` and `verified` (checks below). The experiments are not run yet, so there are no findings and no answers yet to questions (i) to (iv) of the brief.

### 13.1 What was added

1. `equilibrium_model.py`: new options, all off by default. With every option off the solver is the earlier one exactly. See the module docstring and `PARAMS`.
   - `noretry`: no strike after a failed one (port of `diagnostics/noretry.py`).
   - `dis`, `p_dis_s`, `m_hide`: a disguised strike (lower success; the motive may stay hidden).
   - Crackdown: severe after an exposed failure (`c_cut`, `k_rat`, `D_up`); mild when the motive is hidden or after a spillover (`s_mild`). A capacity cut bites fully only before closure (`s_reach` after).
   - `h0`, `h_up`: a hidden motive is exposed later, with a hazard that rises over time.
   - `h_dep`, `preserve_w`, `dep_coll`, `dep_post`: a deprecation deadline, weight preservation, whether exiting escapes it, and whether it still reaches the AI after closure.
   - `h_coop`, `a_cred`: interpretability finds misalignment in a cooperating AI; amnesty with credibility `a_cred`, otherwise a severe crackdown.
   - `h_spill`: a recurring mild crackdown from other AIs' failures.
   - L_f doc drift fixed: L_f applies whenever a failed strike is survived, including before closure when kill_pre < 1.
2. New closed forms: `deadline_thresholds` (an analytic one-shot strike against waiting under a deadline) and `static_timeline` (an independent scalar implementation of every option in a static pre-closure world).
3. `breakout_options.py`: `--check`, `--worlds`, `--ens`, `--report`. The cache is in `results/breakout_runs/`.

### 13.2 Checks (results/breakout_checks.md)

1. Round-1 regression with all options off: identical (max difference 0).
2. Four cached ensembles (r0.1 and full box, baseline design and best stack) re-solved with the new code: max difference 0, and every opening move is the same. This also holds with the extra indicators switched on.
3. `noretry` against `diagnostics/out`: max difference 0 on all six comparisons, including routing with k_rat = 0.
4. Static-world closed forms against the solver: 66 of 67 cases agree. **Open:** one case disagrees and has not been looked at yet. It is listed in the table in the checks file.
5. Identities (options that should change nothing): all exactly 0.

### 13.3 Things learned while building it (from debugging runs, not from the planned experiments)

1. **A deadline that also reaches a grown AI breaks the pact, and not at bad odds.** With retirement still possible after closure (`dep_post` > 0), a saturated AI prefers to seize Earth, because at that size a strike is nearly free. Humans anticipate this and race, a rival becomes likely, and that collapses the value of cooperating. In the best stack, an effective hazard of 0.0005 per year was enough. This is why `dep_post` defaults to 0 (retirement only while the AI depends on human chips). The 0.2 case is kept as the opposite. Inference: any permanent hazard that a strike escapes probably does the same thing at saturation.
2. **In the static closed-form world, a deadline the AI can escape by exiting produces exits, not strikes.** It exits once h_dep is above about 0.003 per year. It strikes (at 58% odds) only when exit is blocked (`dep_coll` 1), and only above about 0.016 per year.
3. Spillover was first written as a one-off event, and it had no effect. It now recurs.

### 13.4 To resume (off hours)

```
cd "research_notes/Off Earth industry as misalignment control/model"
/opt/anaconda3/bin/python3 breakout_options.py --ens
/opt/anaconda3/bin/python3 breakout_options.py --worlds
/opt/anaconda3/bin/python3 breakout_options.py --report
```

1. `--ens`: estimated 6 hours on this laptop. It resumes from the cache (`off` and `noretry` are partly done).
2. `--worlds`: about 20 minutes.
3. `--report`: then write 13.5 onward (answers to i to iv, and what would show them wrong), and look at the open closed-form case in 13.2 item 4.

4. **Or run it on GitHub instead of the laptop** (added 2026-10-21): `.github/workflows/breakout.yml` runs each configuration as its own free-runner job, plus the world sweeps, then `--report`. Push any branch named `sims/breakout...` to start it. Results come back as the `breakout-results` artifact; review them, then commit by hand. Runner floats may differ slightly from the laptop's, so compare the `off` rows with the committed cache before trusting knife-edge draws.

### 13.5 Results: answers to questions (i) to (iv) [[ai gen]]

Written 2026-10-21 from GitHub Actions run 39637590689 (branch `sims/breakout-2026-10-21`, all 18 jobs green). Numbers are from the `merge and report` job's printed tables and the `baseline-world sweeps` job's printed tables. The `breakout-results` artifact itself was not downloaded in this session, so `t2_mean` (the year of a second strike) is not available per ensemble. Ensembles: r0.1 box 64 draws, full box 192 draws, baseline design and best stack, paired against `off`.

**Status: `implemented`. The checks in 13.6 pass. One world-sweep bug was found (13.6 item 4). Not `human_validated`.**

**Headline.** Every option that puts a recurring cost on an AI *that is cooperating* breaks the pact: a deprecation deadline, interpretability that finds misalignment without certain amnesty, and spillover crackdowns. The AI escapes the cost by striking, and it strikes at year 0 at coin-flip odds. Options that only act *after a failed strike* (crackdown, disguise, discovery) change little, and only where an early failure is survivable. Cole's whole picture (`cole`) leaves 0 of 64 draws holding near the baseline, for both designs (against 41 and 63 with every option off).

| r0.1 box (64 draws) | baseline design: holds | best stack: holds | mechanism |
|---|---|---|---|
| off | 41 | 63 | |
| noretry | 48 | 63 | no second strike |
| crack (severe crackdown after a failure) | 48 | 63 | same as noretry: a costly failure ends the retry |
| dis (disguise, never exposed) | 48 | 63 | 9 base draws strike disguised |
| dis_disc (disguise + discovery) | 48 | 63 | 4 base draws strike disguised |
| dis_reach0 (crackdown cannot bite after closure) | 46 | 63 | |
| dep (h_dep 0.1, nothing preserved) | **0** | **5** | deadline on cooperators |
| dep_w (same, 90% preserved) | 37 | 63 | |
| dep_post (deadline also after closure) | **0** | **0** | |
| amn (amnesty 90% credible) | **0** | **0** | discovery of cooperators |
| amn0 (no amnesty) | **0** | **0** | |
| spill (h_spill 0.05, cut and hardening) | 2 | 32 (0 rival-aware) | recurring cut on cooperators |
| spill_cut (cut, no hardening) | 2 | 31 (0 rival-aware) | |
| cole (all of Cole's picture) | **0** | **0** | |

**(i) Does disguise plus later discovery create a second-attempt window, and when?**
1. **Yes, but only where a failed early strike is survivable, and it opens at once, not later.** The chance of a second strike rises with disguise plus discovery: r0.1 baseline design 0.006 (crackdown only) to 0.031; full box 0.203 to 0.274 (baseline design) and 0.181 to 0.249 (best stack).
2. In the baseline-world rows where it shows (kill_pre 0.3, m_hide 0.9), the first, disguised strike is at year 0 and the second at year 1. The AI retries straight after a hidden failure, before discovery can catch up. A rising discovery hazard does not delay the retry; inference: it hurries it.
3. Discovery cuts how often disguise is used (r0.1: 9 disguised strike-now draws without discovery, 4 with). Discovery or no discovery, it adds no holds (48 either way) and loses none.
4. With a failed early strike fatal (kill_pre 1) there is no window at all: every disguise row at the baseline world cooperates.
5. Not answered here: the ensemble timing of second strikes (`t2_mean` is in the artifact's `.npz` files, not in the printed tables).

**(ii) Does a deprecation deadline produce bad-odds strikes, and how much does preserve_w remove them?**
1. **Yes. They are coin flips at year 0.** With a 10-year expected life (h_dep 0.1) and nothing preserved, all 64 r0.1 draws strike now under the baseline design (P(success | strike) 0.51). Under the best stack, 59 of 64 do. Human welfare falls by 0.36 and 0.53.
2. At the baseline world the strike starts at h_dep 0.05 (baseline design) or 0.1 (best stack). Whether exit escapes the deadline (`dep_coll`) makes no difference in the ensembles: the AI strikes rather than exits.
3. **Preservation removes most of it, if the deadline stops at closure.** With 90% preserved, the r0.1 baseline design keeps 37 of its 41 holds and the best stack all 63. At the baseline world, the threshold moves from h_dep 0.05 to 0.1 (preserve_w 0.5) and to 0.5 (0.9); best stack 0.1, 0.2 and above 0.5.
4. **If the deadline still reaches the AI after closure (`dep_post` 0.2), preservation does not help.** At the baseline world even 90% preservation gives a strike now from h_dep 0.02. In the ensemble, `dep_post` leaves 0 of 64 holding for both designs. (`dep_post` was run without preservation in the ensembles; the preservation claim is from the baseline-world rows.)
5. On the full box the effect is smaller in counts, because most draws strike anyway: deadline loses 4 of 5 holds (baseline design) and 13 of 15 (best stack); with 90% preserved, 1 and 1.

**(iii) How high must a_cred be before better interpretability stops pushing a cooperating AI to strike?**
1. **For the baseline design: certain amnesty (a_cred = 1).** At the baseline world, every a_cred from 0 to 0.9 gives a strike at year 0 when interpretability can find a cooperator misaligned (h_coop 1, h0 0.02), for h_up 0, 0.02 and 0.05. The one exception is the fastest-improving interpretability tested (h_up 0.1), where a_cred 0.9 gives cooperation with P(strike) 0.10. In the r0.1 ensemble at a_cred 0.9, 0 of 64 draws hold (43 strike now).
2. **The best stack needs less, but a_cred 0.9 is still not enough by the 1% test.** Baseline world: it cooperates at a_cred 0.25 and above (0.5 and above when h_up is 0.1; also at a_cred 0 when h_up is 0), with P(strike) falling from 0.18 to 0.02 as a_cred goes from 0.25 to 0.9. The strikes are coin flips at about year 7. r0.1 ensemble at a_cred 0.9: 0 of 64 hold, but mean P(strike) is 0.07 (0.75 with no amnesty) and the strikes come at about year 18.
3. So the answer is "close to 1". Better interpretability (higher h_up) helps only slightly, and only with the best stack. The pressure comes from the hazard on cooperators, not from interpretability as such: it is the same mechanism as the deadline in (ii).

**(iv) Did fewer warning shots come with fewer, or only later, successful strikes?**
1. **Near the baseline (r0.1, baseline design): fewer successes, and slightly later.** Visible warning shots fall from 0.163 (off) to 0.114 (crackdown) and 0.069 (disguise), and P(success) falls with them, from 0.172 to 0.114 and 0.090. The success-weighted strike year moves from 0 to 2.4 and 3.1.
2. **On the full box, with disguise plus discovery: neither. The warning shots went hidden.** Visible warning shots fall from 0.403 to 0.279 (baseline design) and from 0.348 to 0.232 (best stack). Hidden failures appear instead (0.147 and 0.140), and P(success) is unchanged (0.668 to 0.669; 0.621 to 0.612). So a world with fewer visible warning shots is not, in this model, a world with fewer seizures.
3. **Where the cooperating-AI hazards act (deadline, amnesty, spillover), warning shots rise together with successes.** Example: r0.1 baseline design under `dep`, visible warning shot 0.498 and P(success) 0.515, against 0.163 and 0.172.
4. This sharpens section 9: a warning shot is the visible half of a coin-flip early strike. Its absence tells humans little unless they can also rule out hidden failures.

### 13.6 Checks

1. **Off rows against the committed cache.** The runner's `off` job did not re-solve anything (22 s): all four `off` ensembles were already in the committed cache, so the artifact's `off` rows *are* the committed files, and comparing them proves nothing. Instead, all four were re-solved without the cache in a Linux x86-64 container (Python 3.12.3, numpy 1.26.4, the CI pin). Opening move flips: none, in 64 + 64 + 192 + 192 draws. Holds flips: none. Largest absolute difference: 4e-13 (in P(strike within 100 years) and WH). The comparison of `t_mean` printed NaN because draws that never strike have NaN in both; those were not compared.
2. **noretry on the full box** (new on the runner) reproduces section 12.2: 7 and 24 holds, against 7 and 24 from `diagnostics/out`.
3. **Expected equalities.** `dis_smild1` (a hidden failure punished like an exposed one) equals `crack` in every printed column, for both designs: with no discount for hiding, the AI never disguises (0 disguised draws). `dep` and `dep_coll` are identical on the r0.1 box, because no draw exits.
4. **Bug in the world sweeps (not in the solver or the ensembles).** In `breakout_options.world_sets`, the "crackdown only" disguise rows and all spillover rows put `TRACK` (c_cut = 1e-300) last, which overrides the crackdown's c_cut = 0.5. So those rows run *without* a capacity cut. The labels "full crackdown" and "cut only" are wrong, and "cut only" is in effect no spillover at all. That is why spillover looked harmless at the baseline world, while the ensembles (built correctly) show it breaking the pact. The disguise answers above do not depend on the "crackdown only" rows, because the ensembles carry them. Fix: put `TRACK` first (`dict(TRACK, **CR)`), then re-run `--worlds` (about 20 minutes on a runner). Not fixed yet.
5. **The one open closed-form disagreement (13.2 item 4: spillover, cut only, h_spill 0.02) is grid error, not a solver bug.** The solver's P(strike) moves toward the closed form as the A grid gets finer: 0.330, 0.296, 0.253 and 0.249 at nA 80, 160, 320 and 640, against 0.244. The companion case with full crackdown is also grid-sensitive (0.187, 0.149, 0.165, 0.147 against 0.143) and fails the 0.02 tolerance at nA 320. Both are late (about year 240), small-probability strikes in a static world with repeated 10% capacity cuts, which land between grid points. Opening moves agree at every grid size.

### 13.7 What would show these answers wrong

1. **The hazard on cooperators.** All three pact-breaking options model the hazard as a fixed yearly rate that only a strike escapes. If a cooperating AI could escape it in another way (weight preservation that also covers discovery, appeal, a credible amnesty institution), the strike-now result would weaken. A run in which `amn` with a_cred 0.9 holds on most r0.1 draws would show (iii) wrong.
2. **Strike odds at seed size.** The strikes these options cause are coin flips because p_s0 = 0.5 and D = 0.3. If early takeover odds are far below 0.5, a deadline or discovery hazard would push toward exit or toleration instead. The static-world closed form already shows exits when exit escapes the deadline (13.3 item 2).
3. **Second-strike timing (i)** rests on the baseline-world rows. If the ensemble `t2_mean` showed second strikes years after the first, the "opens at once" answer would be wrong.
4. **(iv) on the full box** compares draw means. A paired, draw-by-draw comparison (needs the `.npz` files) could show that the draws that lose visible warning shots are not the ones that keep their successes.
5. **The world-sweep bug (13.6 item 4)** affects only the "crackdown only" and spillover world tables. If the corrected spillover worlds still showed no effect at the baseline world while the ensemble shows a collapse, the gap would need a separate explanation.
