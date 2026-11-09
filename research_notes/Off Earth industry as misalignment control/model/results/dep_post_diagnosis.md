# Why dep_post holds on 0 of 64 draws (diagnosis)

[[ai gen]] Corrected 2026-11-09. First written 2026-10-30; that text is kept unchanged at the end as a recorded error. Source: `diagnostics/dep_post.py`, one solver batch (16 draws, batch 0 of the r0.1 box, seed 105), run by hand, four processes; nothing cached. Follows `results/preservation_sweep.md` section 3. Status: implemented; checked only against the committed caches on this batch. Not verified against a closed form, not human_validated, not empirical.

## Correction

The first version said the collapse is a knife-edge that a seizure penalty `rep` above about 2e-5 repairs. Two parts of that were wrong.

1. **The repair was not a repair.** Under `dep_post` with `rep` 0.001 the AI does not strike, but it exits the pact later with probability 0.84 (base design) or 0.94 (best stack) on the draws counted as holding, and a rival AI is born on all of them. The rival-aware count is 0 of 16 on both designs. The first version did not print exit or rival outcomes. Its "holds" test checks only that the AI neither strikes nor exits at year 0 and strikes with probability below 0.01, so a later exit passed.
2. **The size was wrong.** The deadline is a hazard on the AI's whole continuation value, a stock. The first version compared it with one year's flow. With no rival source, `rep` 3e-4 restores nothing and `rep` 3e-3 restores the reference exactly, so the amount needed lies between those, about 15 to 150 times the 2e-5 first stated. The humanity premium `omega` behaves the same way with rivals present: 1e-3 restores nothing, 3e-3 restores everything.

What stays: the collapse comes from `dep_post`, not `dep_coll`; it needs a real retirement cost; and it is not a numerical bug.

## Why the AI exits: the rival terminal value has no deadline

A rival's birth ends the game. The AI then receives `(1 - ell) * Vs`, where `Vs` is the value of an AI alone (`equilibrium_model.py`, `VAr`). `Vs` carries no retirement hazard and no `omega` premium. For a large AI `ell` is close to 0. So under a post-closure deadline, exiting and letting the states build a rival cancels the deadline. `rep` leaves that route open, because it only lowers the value of a successful strike. `omega` closes it, because it raises the value of staying and is absent from the rival terminal value.

This is a property of the reduced-form ending, not a claim about the world. Whether a deadline would survive a rival's birth is not modelled (`results/omissions.md`, OM-POST-RIVAL).

## Results

"Holds" is `breakout_options.holds`: the AI plays C or P at year 0 and strikes with probability below 0.01. "Rival-aware" adds P(rival) below 0.5. "No rival source" sets `mu` and `beta_bg` to 0, so states cannot build a rival. h_dep 0.01 and preserve_w 0.99 unless stated. No variant exits at year 0. 16 draws per design.

Base design:

| variant | holds | rival-aware holds | P(exit) among holds | P(rival) among holds | strike now | mean P(strike) | strikes before closure | mean strike year |
|---|---|---|---|---|---|---|---|---|
| dep (committed cell) | 13 | 12 | 0.00 | 0.31 | 2 | 0.156 | 0.156 | 0.0 |
| dep_post (committed cell) | 0 | 0 | n/a | n/a | 16 | 1.000 | 1.000 | 0.0 |
| dep_coll 1, dep_post 0 | 13 | 12 | 0.00 | 0.31 | 2 | 0.156 | 0.156 | 0.0 |
| dep_coll 0, dep_post 0.2 | 1 | 0 | 0.90 | 1.00 | 14 | 0.878 | 0.875 | 3.0 |
| dep_coll 0, dep_post 0.001 | 4 | 0 | 0.85 | 1.00 | 10 | 0.659 | 0.625 | 9.7 |
| dep_post, preserve_w 1 (no cost) | 13 | 12 | 0.00 | 0.31 | 2 | 0.156 | 0.156 | 0.0 |
| dep, rep 0.001 | 14 | 13 | 0.00 | 0.29 | 1 | 0.093 | 0.093 | 0.0 |
| dep_post, rep 0.001 | 12 | 0 | 0.84 | 1.00 | 4 | 0.250 | 0.250 | 0.0 |
| dep_post, rep 1e-5 | 0 | 0 | n/a | n/a | 16 | 1.000 | 1.000 | 0.0 |
| dep_post, rep 3e-4 | 11 | 0 | 0.83 | 1.00 | 5 | 0.312 | 0.312 | 0.0 |
| dep_post, omega 1e-3 | 0 | 0 | n/a | n/a | 16 | 1.000 | 1.000 | 0.0 |
| dep_post, omega 3e-3 | 14 | 13 | 0.00 | 0.29 | 1 | 0.093 | 0.093 | 0.0 |
| dep, no rival source | 10 | 10 | 0.00 | 0.00 | 0 | 0.346 | 0.000 | 15.0 |
| dep_post, no rival source | 0 | 0 | n/a | n/a | 0 | 1.000 | 0.000 | 29.0 |
| dep_post, rep 3e-4, no rival source | 0 | 0 | n/a | n/a | 0 | 1.000 | 0.000 | 29.0 |
| dep_post, rep 3e-3, no rival source | 10 | 10 | 0.00 | 0.00 | 0 | 0.346 | 0.000 | 15.0 |

Best stack:

| variant | holds | rival-aware holds | P(exit) among holds | P(rival) among holds | strike now | mean P(strike) | strikes before closure | mean strike year |
|---|---|---|---|---|---|---|---|---|
| dep (committed cell) | 16 | 16 | 0.00 | 0.21 | 0 | 0.000 | 0.000 | n/a |
| dep_post (committed cell) | 0 | 0 | n/a | n/a | 7 | 0.525 | 0.438 | 25.2 |
| dep_coll 1, dep_post 0 | 16 | 16 | 0.00 | 0.21 | 0 | 0.000 | 0.000 | n/a |
| dep_coll 0, dep_post 0.2 | 8 | 0 | 0.94 | 1.00 | 6 | 0.403 | 0.375 | 12.9 |
| dep_coll 0, dep_post 0.001 | 7 | 0 | 0.93 | 1.00 | 3 | 0.318 | 0.188 | 43.0 |
| dep_post, preserve_w 1 (no cost) | 16 | 16 | 0.00 | 0.21 | 0 | 0.000 | 0.000 | n/a |
| dep, rep 0.001 | 16 | 16 | 0.00 | 0.21 | 0 | 0.000 | 0.000 | n/a |
| dep_post, rep 0.001 | 16 | 0 | 0.94 | 1.00 | 0 | 0.000 | 0.000 | n/a |
| dep_post, rep 1e-5 | 0 | 0 | n/a | n/a | 7 | 0.520 | 0.438 | 25.3 |
| dep_post, rep 3e-4 | 16 | 0 | 0.94 | 1.00 | 0 | 0.000 | 0.000 | n/a |
| dep_post, omega 1e-3 | 0 | 0 | n/a | n/a | 7 | 0.525 | 0.438 | 25.2 |
| dep_post, omega 3e-3 | 16 | 16 | 0.00 | 0.21 | 0 | 0.000 | 0.000 | n/a |
| dep, no rival source | 16 | 16 | 0.00 | 0.00 | 0 | 0.000 | 0.000 | n/a |
| dep_post, no rival source | 0 | 0 | n/a | n/a | 0 | 1.000 | 0.000 | 42.6 |
| dep_post, rep 3e-4, no rival source | 0 | 0 | n/a | n/a | 0 | 1.000 | 0.000 | 42.6 |
| dep_post, rep 3e-3, no rival source | 16 | 16 | 0.00 | 0.00 | 0 | 0.000 | 0.000 | n/a |

The committed cells reproduce `results/preservation_sweep.md` on this batch (the committed caches give dep 13 and dep_post 0 here), and every figure in the first version's tables is reproduced.

## What is established (on this batch)

1. `dep_coll` alone changes nothing at this cell. `dep_post` alone does almost all the damage. The draws that still "hold" under `dep_post` alone (1 and 4 on the base design, 8 and 7 on the best stack) are exit-then-rival outcomes: none is a rival-aware hold.
2. The damage needs a real cost: preserve_w 1 restores the reference exactly.
3. `rep` at 3e-4 or 0.001 stops the strike and replaces it with exit and a rival. `rep` at 1e-5 changes nothing.
4. `omega` at 3e-3 restores the reference with no exit and no extra rival risk (base 14 holds, 13 rival-aware; best 16 and 16). `omega` at 1e-3 changes nothing.
5. With no rival source, the collapse remains (0 of 16 on both designs), so the rival route is not its cause. The strikes move from year 0 to after closure: none comes before closure, and the mean strike year is 29 (base) and 43 (best). `rep` 3e-3 restores the no-rival reference exactly, and `rep` 3e-4 does nothing.
6. So the year-0 strikes on the base design need the rival source. That answers the first open item of the first version in part: the timing comes through the states' race for a rival, not from the AI's own trade-off at the cap.

## What is not established

1. The exact threshold. It is bracketed, not located: between 3e-4 and 3e-3 for `rep` with no rival source, and between 1e-3 and 3e-3 for `omega`. A rough account is that a hazard of 2e-5 per year on a value discounted at the draws' rates costs 6.8e-4 to 1.4e-3 of that value (hazard divided by discount rate, my arithmetic), which sits inside both brackets. That account is not derived or checked.
2. Whether the strike in the no-rival control comes at the capacity cap or earlier. It comes after closure. I did not compare its year with the year the cap is reached, so "a knife-edge at the cap" is not shown by this test.
3. The mechanism by which the rival source moves the strike to year 0. Item 6 above shows that it does, not how.
4. The full box. There `rep` is 0 on every draw. `omega` is 0 on 64 of 192 draws, above 1e-3 on 20 and above 3e-3 on 15. So at most about 8 to 10% of full-box draws have enough `omega` to matter here, not the 21% the first version gave. That was not run.
5. These results come from one batch of 16 draws, not the full 64-draw grid.

## A wider point about the "holds" count

"Holds" does not exclude a later exit. On this batch that matters only under a post-closure deadline. In the committed r0.1 caches it also matters for the spillover options: under `spill` the best stack holds on 32 of 64 draws and is rival-aware on 0, with P(exit) 0.96 among the holds (read from the caches, not re-solved). Every other committed r0.1 option has P(exit) 0.00 among its holds. A count that also requires the AI to stay would separate these cases.

## Reading for the pact

If retirement can still reach an AI after closure, the pact fails on this batch unless the AI gains about 0.3% in flow value from an intact humanity. A penalty on seizure alone turns the strike into an exit and a rival, which the plain "holds" count reports as success. The rule "retirement must stop at closure" is unchanged, and the "or the AI must care at least slightly" alternative is weaker than the first version said: the care needed is of order 1e-3, not 1e-5, and it has to make staying better, not only make seizing worse. This is a model result on 16 draws. It is not evidence about real AI systems.

## First version (2026-10-30), kept as a recorded error

Everything below is the first version, unchanged. Its tables are correct. Its bullets 3 and 4, "established" item 3, "not established" items 1 and 2, and its "Reading for the pact" are superseded by the sections above.

[[ai gen]] 2026-10-30. Source: `diagnostics/dep_post.py`, one solver batch (16 draws, batch 0 of the r0.1 box, seed 105), run by hand at one process; nothing cached. Follows `results/preservation_sweep.md` section 3.

**Answer.** The collapse comes from `dep_post`, not `dep_coll`. It is a knife-edge at the capacity cap, not a numerical bug.
- At the cap, the AI's choice between peace and seizing Earth is decided by about one capacity unit per year. The AI's own value is of order Kmax / r (`equilibrium_model.py`, comment above `TIE_TOL`; `cap_condition_terms`).
- On the r0.1 box, the two terms that add a margin of order Kmax, `rep` and `omega`, are both 0.
- So a retirement deadline that still reaches a grown AI costs it about h_dep x dep_post x (1 - preserve_w) x Kmax per year. At h_dep 0.01, dep_post 0.2 and preserve_w 0.99 that is about 2e-5 x Kmax, or 4,000 to 100,000 capacity units per year on this box (Kmax 2e8 to 5e9). That outweighs the O(1) margin, so a capped AI strikes to escape the deadline.
- The prediction: a seizure penalty `rep` above about 2e-5 should restore the holds, and one below it should not. It does, on both designs.

Base design, h_dep 0.01, preserve_w 0.99 unless stated (16 draws):

| variant | holds | strike now | mean P(strike) | strikes before closure | mean strike year |
|---|---|---|---|---|---|
| dep (committed cell) | 13 | 2 | 0.156 | 0.156 | 0.0 |
| dep_post (committed cell: dep_coll 1, dep_post 0.2) | 0 | 16 | 1.000 | 1.000 | 0.0 |
| dep_coll 1, dep_post 0 | 13 | 2 | 0.156 | 0.156 | 0.0 |
| dep_coll 0, dep_post 0.2 | 1 | 14 | 0.878 | 0.875 | 3.0 |
| dep_coll 0, dep_post 0.001 | 4 | 10 | 0.659 | 0.625 | 9.7 |
| dep_post, preserve_w 1 (deadline costs nothing) | 13 | 2 | 0.156 | 0.156 | 0.0 |
| dep, rep 0.001 | 14 | 1 | 0.093 | 0.093 | 0.0 |
| dep_post, rep 0.001 | 12 | 4 | 0.250 | 0.250 | 0.0 |
| dep_post, rep 1e-5 | 0 | 16 | 1.000 | 1.000 | 0.0 |

Best stack, same settings (16 draws):

| variant | holds | strike now | mean P(strike) | strikes before closure | mean strike year |
|---|---|---|---|---|---|
| dep (committed cell) | 16 | 0 | 0.000 | 0.000 | none |
| dep_post (committed cell) | 0 | 7 | 0.525 | 0.438 | 25.2 |
| dep_post, rep 0.001 | 16 | 0 | 0.000 | 0.000 | none |
| dep_post, rep 1e-5 | 0 | 7 | 0.520 | 0.438 | 25.3 |

The committed cells reproduce `results/preservation_sweep.md` on this batch (the committed caches give dep 13 and dep_post 0 here).

**What is established.**
1. `dep_coll` alone changes nothing at this cell. `dep_post` alone does almost all the damage, and even a post-closure share of 0.001 (a cost of about 1e-7 per year) removes 9 of 13 holds.
2. The damage needs a real cost: preserve_w 1 restores the reference exactly.
3. A seizure penalty of 0.001 x Kmax per year restores the holds (12 of 13 on the base design, 16 of 16 on the best stack). A penalty of 1e-5 x Kmax, below the deadline cost, does nothing. This matches the cap mechanism.

**What is not established.**
1. Why the baseline design strikes at year 0 rather than at the cap. The cap is where the deadline tips the choice, yet all 16 baseline strikes come at year 0, before closure. My guess is that once peace at the cap is gone, the pact path loses its value to humans, so their earlier enforcement choices change and the AI moves first. I have not checked this. The best stack shows the later pattern instead: strikes around year 25, about 40% before closure.
2. Whether a real-world analogue of `rep` or `omega` is above about 2e-5. On the r0.1 box both are 0. On the full box (192 draws, seed 20261016) `rep` is also 0, and `omega` ranges from 0 to 0.049 and exceeds 2e-5 on 21% of draws. So the full box could soften the collapse only in that minority, and only if omega works like rep here. That was not run.
3. These results come from one batch of 16 draws, not the full 64-draw grid.

**Reading for the pact.** If retirement can still reach a grown AI after closure, the pact in this model depends on the AI putting some weight, a share of order 1e-5 or more of its own value, on not seizing Earth. With that weight at exactly zero, no amount of preservation short of 100% saves it. This is a property of the model's cap, where peace and seizure are otherwise almost tied. It is not evidence about real AI systems.
