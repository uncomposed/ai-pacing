# Why dep_post holds on 0 of 64 draws (diagnosis)

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
