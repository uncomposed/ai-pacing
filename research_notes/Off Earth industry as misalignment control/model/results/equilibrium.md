# Does Cole's clarified pact hold when both sides optimise? An equilibrium model

## Summary in plain words (rounds 1 to 3)

**The answer.** In this model the pact can work, but only in a narrow band. Inside that band, the AI needs to care about humans only a tiny amount for Earth to stay safe. Without the pact, it would need to care a lot.

**What the pact needs (round 1).**
1. Dismantle Earth's fabs only after the off-Earth base can make its own chips, or move the fabs to orbit. Dismantling early makes the AI grab the fabs first.
2. Keep the denial reserve, the power to unplug off-Earth capacity. It carries the growth phase. Trade does not.
3. Keep each state's temptation to build its own AI low: below about 8 years of its welfare.
4. A rival AI born on Earth must not stay dangerous to a much bigger AI.

**What Cole's round-2 answers add.**

5. **"100 times smaller is not a threat" holds, if nothing irreducible remains.** At 1:100 a rival could take about 1% of the AI's value or less, and the AI's choice does not change. Earth crosses 1:100 around year 20. Moving Earth's compute to orbit cuts the chance that a rival is ever born by a third to two-thirds.
6. **If a rival keeps any lasting danger, the ratio stops mattering.** A gravity-well blockade would then have to let fewer than about 1 rival in a million escape.
7. **One covert fab is not much threat to the pact, but each one adds rival risk.** Each of the first few fabs adds about 6 points to the chance of a rival AI within 300 years. Five fabs make a rival more likely than not. Twenty fabs near the temptation edge make the AI strike first.
8. **The pact shrinks the preference for humans the AI needs, by about 200 million times.** With the pact, caring about humans as much as Earth's share of the Sun's light is enough: about 3 parts in 10 billion of its resources. Without the pact, the AI needs about 5 to 6%, because otherwise it strikes early, while Earth still holds the fabs.
9. **Reputation is a top-up, not a substitute.** Under the pact, the AI need only believe in about a one-in-a-billion chance of being judged harshly later. Without the pact it needs more than a 5% chance of losing everything. If the AI discounts a far-off judgement, the odds it needs rise sharply.

**What round 3 adds: Cole's "secure as fast as possible" (R6).**

10. **An AI that is secure early is safe only if humans can unplug almost all of Earth.**
    - How complete the unplugging is matters more than how sure. With total unplugging, a reserve that fires about 60% of the time is enough at any closure size.
    - The share of Earth left live must be no bigger than about the AI's own size when it becomes chip-independent. That is about 0.4% of Earth at the earliest closure tested, and 11% at the baseline.
    - Making a failed strike survivable raises the bar further.
    - With both halves in place (the AI secure, and humans holding a total unplug it cannot pre-empt), the pact holds in every case tested. That is the MAD analogue. When it holds, humans are better off and rivals are rarer.
    - With the AI secure and the unplug partial, the AI strikes in year 0 or 1.
    - So, on its own, early security is destabilising here. Prove the unplug first.

**How much to trust this.** The mechanisms and thresholds are checked against closed-form maths. The numbers rest on assumed parameters with no empirical basis, and 19 of 36 single-parameter changes flip the round-1 baseline to a strike. The model shows which assumptions matter, not that the real world sits inside the band.

**What would show it wrong.**
1. A rival AI that stays dangerous however small, without a near-perfect blockade.
2. An AI whose regard for humans is either zero or large, never tiny.
3. An AI that wants Earth's mass, not just its sunlight.
4. Earth capacity that no authorisation gate can unplug, if the AI becomes secure early (R6).

Details: round 1 is in sections 0 to 3.9; round 2 is in section 3R; round 3 (R6) is at the end of section 3R.

Status: `implemented` and `verified`. The solver matches closed forms, a forward simulation matches the backward solution, and results are stable across grid size, horizon and terminal condition (section 5; round-2 checks are at the end of section 3R). It is **not** `human_validated`. Every parameter value is an assumption unless labelled otherwise. The numbers say what follows from these assumptions, not what will happen.

Files, all in `model/`:
- `equilibrium_model.py`: the game and the solver (numpy only).
- `run_equilibrium.py`: every check, table and figure. Run `python3 run_equilibrium.py` for round 1 (about 50 minutes). Its `--quick` smoke test overwrites the round-1 outputs, so re-run the full version afterwards. `python3 run_equilibrium.py --round2` runs round 2 only (about 20 minutes). `python3 run_equilibrium.py --round3` runs round 3 only (R6, about 2 hours); `--round3 --quick` writes separate `_quick` files.
- `results/equilibrium_tables.md`: every round-1 table quoted here, auto-generated. `results/equilibrium_summary.json` holds the same data. Round 2: `results/equilibrium_round2_tables.md` and `results/equilibrium_round2_summary.json`. Round 3: `results/equilibrium_round3_tables.md` and `results/equilibrium_round3_summary.json`.
- `figures/eq_*.png`: six round-1 figures and three round-2 figures (`eq_r1_ratio.png`, `eq_r2_covert_fabs.png`, `eq_r3_epsilon.png`) and one round-3 figure (`eq_r6_sovereignty.png`, blue and orange only). They use Okabe-Ito blue, sky blue, orange and reddish purple only, and every class is also marked by hatching, line style or a text label.
- The earlier one-sided model (`offearth_model.py`, `run_analysis.py`) is unchanged and still runs.

## 0. The answer first

**Short version.** Yes, the pact can be an equilibrium: an AI that grows off-Earth, trades, and never strikes, alongside human states that keep the pact. But it holds only in a narrow band, and the band has sharp edges.

Inside the band, Cole's mechanism works the way he describes. The AI is the rising power, and a rising power gains by waiting. Dismantling Earth's fabs after the off-Earth base can make its own chips removes most of Earth's threat. After that, Earth can do little to a large AI. So the AI waits, then cooperates.

Outside the band, the same logic flips. "It will just wait" turns into "it will wait until striking is cheap". And because humans can see that coming, it often turns into "it strikes now".

What the pact needs, in the model:

1. **Dismantle fabs after closure (a) or move them to orbit (b), not early (c).** Dismantling early cuts the AI's only chip source during bootstrap. The AI then seizes the fabs before they are gone. Early dismantling only works if the denial reserve is certain to fire (q = d = 1), and even then it slows the AI's bootstrap by about 50 years.
2. **Keep the denial reserve.** It is load-bearing, not a backstop. After closure, every incentive the AI weighs shrinks in proportion to its size, so its size does not settle the question. What settles it is whether Earth's usable prize, after plugging, is smaller than the cost of taking it. Without the reserve, the prize wins and the AI strikes.
3. **Keep each state's temptation to build its own rival AI low.** The pact holds while a state's private gain from owning a rival AI (B_R) stays below about 8 years of its welfare under (a), or about 6 under (b). At 10 years it fails under every design on the menu. Sanctions and AI policing of detected programmes did not rescue it. The AI strikes before any state has actually defected, because it anticipates the programmes.
4. **Rely on a rival never being able to threaten a big AI, or on there being no source of rivals at all.** Suppose a rival born on Earth keeps even a sliver of lasting danger to the AI (ℓ_∞ above about 1e-8 at baseline), and rivals can still arise from rogue actors or the residual threat floor. If a seizure would be lethal to humans, the pact then fails at year 0: the AI plans a late strike, humans foresee it and race to build rivals, and the AI pre-empts the race. If a seizure is survivable, the AI instead waits 31–71 years and then strikes.
5. **Rely on the AI caring a little about humans, or Earth's resources mattering little to it.** Otherwise the late-stage harvest term ends the pact around the time the AI saturates (year 87–88 at baseline). This term has nothing to do with threat. It is about what Earth is worth to an AI that is indifferent to humans.

**Cole's claim 6 ("it will wait, then has no reason to strike").** The first half holds: during bootstrap the AI waits, because a failed strike then is fatal. The second half needs every term in the AI's final comparison that does not shrink with its size to be zero. If one is not zero, waiting ends in a strike. In the run where humans survive a seizure, that strike comes around year 38. Where they do not, humans race, and the strike comes at year 0.

**How robust is the pact where it holds?** Not very. Moving any one of 19 of the 36 parameters to the end of its range flips the baseline from cooperation to a strike at year 0 (section 3.9). The band exists, but the model gives no reason to think the real world sits inside it.

**What I would tell Cole.** The pact turns the commitment problem around. Humans become the declining power, and in Powell's terms the declining side is the one tempted toward preventive action. So the main danger in the model is **human defection and racing**, not AI aggression. The AI strikes mostly to pre-empt human rivals.

---

## 1. What is new compared with the earlier model

The earlier model (`../decision_model.md`) treated human behaviour as fixed hazards. Its main finding was that the AI's choice turns on a threat term (humans building a rival or shutting the AI down), not on Earth's value as a prize.

This model makes humans players. Two or three human states each choose every year whether to run a covert rival-AI programme. A pact designer chooses the fab sequencing, the AI's trade share, the denial reserve, and whether the AI may remove detected programmes. The AI's move (cooperate, exit, strike now, or strike later) is a best response to all of that, and the states' moves are best responses to the AI.

It models Cole's clarified plan, not the earlier "smaller prize" reading:
- Fabs are dismantled to remove Earth's ability to build a rival. That acts on the threat term.
- There is no defended human off-Earth capacity.
- Earth is a demilitarised habitat. Its defence D = 0.3 Earth-industry units at baseline.
- Free trade, with a share σ to the AI.
- A denial reserve that plugs captured capacity.

---

## 2. The model

### 2.1 Players, moves and timing

Time runs in one-year periods, t = 0, 1, 2, …. Capacity A is the AI's off-Earth industrial base, in units where today's whole-Earth industry = 1.

- **The AI** (one agent, possibly misaligned) moves first each year. While the pact is in force it chooses one of: **C** cooperate and trade, **X** exit the pact, **S** strike (try to seize Earth), or **P** police (remove detected covert programmes; only if the pact allows it, variant). After the pact has collapsed it chooses **W** wait (grow alone) or **S**. "Waiting" in Cole's sense is any year in which the AI could strike and does not.
- **N human states** (N = 2; N = 3 as a check) move next, simultaneously. Each state without a programme chooses whether to start a covert rival-AI / covert-fab programme. Each state with a known programme chooses whether to keep it. A new programme stays hidden for L_det years before it becomes public.
- **The pact designer** (humans collectively) picks, before play starts, from a menu: fab sequencing (a, b or c), the AI's trade share σ, whether to keep the denial reserve, and whether to authorise policing. The designer picks the item with the best equilibrium human welfare.

Order within a year: AI move → enforcement (other states shut each public programme with probability ζ; the AI removes it with probability p_pol if it chose P) → states move → a rival AI may be born → growth and the fab schedule update.

**Solution concept.** Subgame-perfect equilibrium in Markov strategies, found by backward induction over a 300-year horizon on a grid of (A, F, pact status, number of public programmes k). In each state-year the states play a simultaneous stage game, given what everyone does afterwards. When the stage game has several pure equilibria, the pact is assumed to coordinate on the one best for humans (assumption **E1**; the worst one is run as a check). Mixed equilibria are computed when no pure one exists; none was needed in the reported runs. The AI breaks ties toward peace (**E2**).

### 2.2 Equations

**Growth and chips.**
$$A_{t+1}=A_t\exp\!\big[g\,\chi_t\,(1-A_t/K_{max})\big]\;\big(+\;\text{reinv}\cdot\sigma\gamma\min(A_t,H)(1-A_t/K_{max})\big)$$
with chip access χ_t = 1 once the off-Earth base has its own leading-edge fabs (A ≥ A_close, "closure"). Before closure:

| situation | χ |
|---|---|
| pact, sequencing a, c or n | χ0 + (1 − χ0)·F (Earth fabs supply chips in proportion to what is left) |
| pact, sequencing b | χ_m while fabs are moving, 1 once they are in orbit |
| pact collapsed, no chips | χ0 |
| pact collapsed, AI holds working orbital fabs or seized fabs | 1 |

**Fab schedule** (F = Earth leading-edge fab capacity, 1 = today). Under the pact: (a) F falls by 1/T_dis per year once A ≥ A_close; (b) F falls by 1/T_reloc per year from t = 0 and the fabs reappear in orbit; (c) F falls by 1/T_dis per year from t = 0; (n) F stays at 1. If the pact collapses, states rebuild: F rises by 1/T_rebuild per year.

**Earth's rival-building capacity (the threat term) with a residual floor θ:**
$$\tau=\theta+(1-\theta)\,F .$$
A running public programme produces a rival with probability $1-e^{-\mu\tau}$ per year. A new hidden programme produces one with probability $1-e^{-\mu\tau L_{det}}$ before it is detected. A rogue background (non-state actors) produces one with probability $1-e^{-\mu\tau\beta_{bg}}$ per year even under full compliance.

**What a rival does to the AI.** The AI keeps $(1-\ell)$ of its solo value, with
$$\ell(A)=\ell_\infty+(1-\ell_\infty)\Big(\frac{s_R}{s_R+A}\Big)^{\nu},\qquad s_R=s_{R0}\,\tau .$$
With ℓ_∞ = 0 and ν = 1 this is an equal-growth race: final shares equal starting shares, so a rival born on Earth matters less and less as the AI grows. That is Cole's "high ground" claim (**Variant A**). ℓ_∞ > 0 says a rival stays dangerous however big the AI is, for example because it is smarter (**Variant B**).

**What a rival does to humans.** The owning state gains B_R (B_Rc if the pact has already collapsed). Every other state loses B_o. All humans lose a share κ_coll of welfare from then on, as collateral damage of AI-versus-AI conflict.

**Strike.** Probability of failure
$$p_f(A)=(1-p_{s0})\Big(\frac{D}{D+A}\Big)^{\epsilon},$$
where D is demilitarised Earth's defensive capacity. If the strike succeeds, the AI spends $c_A D\,A/(A+D)$ and captures Earth's industry $(1-c_w)H$. If the denial reserve fires (probability q when it is kept), a share d of that industry and all fabs go dead ("plugging"). The AI also gets the harvest term below if it is already that large. All human threat is gone afterwards, and humans get w_seized per year.

If the strike fails: before closure the AI is shut down (probability kill_pre = 1, the same as the earlier model). After closure it loses a share L_f of its capacity, the pact collapses, chips stop, and states rebuild fabs and may build rivals (now worth B_Rc).

**Flows.**
- AI under the pact: $u\big((A+(1-\text{reinv})\,\sigma\gamma\min(A,H))(1-\psi_{div})\big)(1+\omega)$, with u(x) = x^{1−η}.
- AI with humans intact but no pact: $u(A)(1+\omega)$. Alone: u(A).
- Each human state: $1+\big[(1-\sigma)\gamma\min(A,H)+\psi_{div}A\big]/N-c_{den}/N$, minus programme costs c_prog and, under the pact, sanctions c_sanc on a public programme.

**Late-stage harvest (preference, not incentive).** Once A ≥ h_frac·K_max, a strike also yields Earth's share of the AI's late resource base:
$$\Pi_h=f_E\,(1-c_{grav})\,K_{max}.$$
This term has nothing to do with threat or the pact. It is there because Earth's sunlight or mass is worth something to an AI that places no value on humans. It is switched off (f_E = 0) in the core runs and switched on separately.

**Values.** The AI maximises $\sum_t e^{-rt}\,(\text{flow}_t)$ times survival. Each state maximises $\sum_t e^{-r_h t}\,(\text{flow}_t)$ plus lump payoffs. Human welfare is reported as a yearly equivalent: 1 = today's welfare forever.

### 2.3 Closed-form conditions (linear utility; derived, then checked against the solver)

**(G) Growth phase, after closure, A ≫ D.** Every term in the AI's strike comparison shrinks like 1/A, so the verdict does not change as the AI grows. The AI strikes iff
$$\underbrace{(1-c_w)H(1-q\,d)}_{\text{expected usable prize}}\;>\;D\Big[c_A+(1-p_{s0})\ln\tfrac{1}{1-L_f}\Big]\;+\;(\text{threat after a failed strike}).$$
Trade consumed as a flow does not enter, because a head start compounds and a trade flow does not. If trade goods are reinvested (reinv = 1), trade enters like an extra prize of size ≈ σγH/g.

**(C) Saturation, A ≈ K_max.** The AI strikes iff
$$\underbrace{(1-c_w)H(1-qd)-c_AD}_{\text{net prize}}+\underbrace{\lambda s_R/r}_{\text{shrinking threat}}+\underbrace{\lambda\,\ell_\infty K_{max}/r}_{\text{irreducible threat}}+\underbrace{f_E(1-c_{grav})K_{max}}_{\text{harvest}}\;>\;\underbrace{\sigma\gamma H}_{\text{trade}}+\underbrace{\omega K_{max}}_{\text{AI values humans}},$$
with λ = μτβ_bg the residual rival rate. Every term on the left except the last two scales with Earth's size, not the AI's. The last two scale with the AI's size, so any non-zero value eventually dominates.

**(U) Unravelling.** Suppose the AI's equilibrium plan includes any future strike, and a seizure leaves humans with little (w_seized small). Then, near that date, each state's pact value falls toward w_seized, so starting a rival programme becomes each state's best response. The AI anticipates the programmes and strikes earlier, and so on back to the present. The chain stops only where an early strike is too risky for the AI: before closure, a failed strike is fatal.

### 2.4 Every parameter, with its label

Labels: **LEVER** is a pact design choice. **ASSUMPTION** is my choice, with no empirical basis unless the basis column gives one. **UNSETTLED (both run)** is a modelling choice that changes the conclusion, so both variants are reported and it is listed as a question for Cole (section 7). Other modelling assumptions: **E1**, the stage-game equilibrium best for humans is played (worst is a check); **E2**, the AI breaks ties toward peace; **E3**, one-year periods and a 300-year horizon with a 'settled peace' terminal value (600 years and a 'seized' terminal are checks); **E4**, everyone knows everyone's payoffs (complete information).

| # | param | baseline | range swept | label | meaning | basis |
|---|---|---|---|---|---|---|
| A1 | `seq` | 0 | 0 to 3 (cat) | LEVER | Fab sequencing: 0=a after closure, 1=b orbit, 2=c early, 3=n never | Cole's levers. a is the literal reading of 'dismantle while space industrialises'. |
| A2 | `sigma` | 0.3 | 0 to 1 (lin) | LEVER | AI's share of the trade surplus | Pact lever. Free trade: gains split sigma to the AI, 1-sigma to humans. |
| A3 | `den` | 1 | 0 to 1 (bin) | LEVER | Keep the denial reserve (1) or not (0) | Pact lever. 'Plugging, not burning'. |
| A4 | `police` | 0 | 0 to 1 (bin) | UNSETTLED (both run) | Pact authorises the AI to remove detected programmes (1) or not (0) | NOT settled by Cole; run both ways. |
| A5 | `psi_div` | 0 | 0 to 0.3 (lin) | LEVER | Dividend: share of AI output paid to humans under the pact | Variant only. 0 = pure free trade, which is Cole's stated design. |
| A6 | `g` | 0.35 | 0.07 to 0.69 (log) | ASSUMPTION | Off-Earth growth rate (/yr) with full chip access | Same as offearth_model.py baseline (doubling ~2 yr; Metzger et al. 2013). |
| A7 | `chi0` | 0.15 | 0.02 to 0.5 (lin) | ASSUMPTION | Growth multiplier before semiconductor closure with NO leading-edge chips | Assumption: legacy chips, salvaged compute, slower designs. |
| A8 | `chi_m` | 0.5 | 0.1 to 0.9 (lin) | ASSUMPTION | Growth multiplier while fabs are being moved to orbit (policy b) | Assumption: relocation disrupts chip output. |
| A9 | `A0` | 0.001 | 0.0001 to 0.01 (log) | ASSUMPTION | AI's off-Earth industrial base at t=0 (Earth industry = 1) | Same seed as offearth_model.py s0. |
| A10 | `A_close` | 0.1 | 0.01 to 1 (log) | ASSUMPTION | Off-Earth base needed for leading-edge semiconductor closure | Assumption. Leading-edge fabs need a large supply chain. |
| A11 | `Kmax` | 1e+09 | 1e+06 to 1e+13 (log) | ASSUMPTION | Resource pool cap for the AI (Earth industry = 1) | Same as offearth_model.py. 1e13 ~ Dyson-scale. |
| A12 | `T_dis` | 5 | 2 to 15 (lin) | ASSUMPTION | Years to dismantle Earth's leading-edge fabs | Assumption. |
| A13 | `T_reloc` | 10 | 4 to 20 (lin) | ASSUMPTION | Years to relocate fabs to orbit (policy b) | Assumption. |
| A14 | `T_rebuild` | 10 | 3 to 30 (lin) | ASSUMPTION | Years to rebuild fabs if the pact collapses | Assumption. |
| A15 | `H` | 1 | 1 to 1 (lin) | NORMALISATION | Earth's (frozen) general industry | Normalisation. |
| A16 | `gam` | 0.5 | 0.05 to 1 (lin) | ASSUMPTION | Trade surplus per year as a share of the smaller partner's economy | Assumption (Ricardian: gains are bounded by the smaller partner). |
| A17 | `reinv` | 0 | 0 to 1 (bin) | UNSETTLED (both run) | AI reinvests its trade gains as capacity (1) or consumes them (0) | NOT settled. 0: trade is a consumption flow (matters near saturation). 1: trade goods compound like extra growth (matters during the growth phase). Run both. |
| A18 | `p_s0` | 0.5 | 0.05 to 0.95 (lin) | ASSUMPTION | Strike success probability for a seed-sized AI | Same as offearth_model.py; unknowable. |
| A19 | `D` | 0.3 | 0.01 to 1 (log) | ASSUMPTION | Earth's defensive capacity (industry units); demilitarised Earth = small | Assumption. Failure odds halve when A = D. |
| A20 | `eps` | 1 | 0.3 to 2 (lin) | ASSUMPTION | Exponent on Earth's relative power in failure odds | Assumption. |
| A21 | `c_w` | 0.3 | 0 to 0.8 (lin) | ASSUMPTION | Share of Earth's industry destroyed in a strike | Fearon's cost of war. |
| A22 | `c_A` | 1 | 0 to 3 (lin) | ASSUMPTION | AI capacity spent on a strike, per unit of Earth defence D | Assumption. |
| A23 | `L_f` | 0.5 | 0.1 to 0.9 (lin) | ASSUMPTION | Share of AI capacity lost if a strike fails AFTER closure | Assumption. |
| A24 | `kill_pre` | 1 | 0 to 1 (lin) | UNSETTLED (both run) | Probability a failed strike BEFORE closure ends the AI (shutdown) | Assumption: before closure the AI still runs on Earth-made chips and Earth-side infrastructure. Same as offearth_model.py (failure = value 0). |
| A25 | `d` | 0.9 | 0 to 1 (lin) | ASSUMPTION | Share of Earth capacity that goes dead if the denial reserve fires | Plugging: most modern capacity depends on authorised chips/firmware. |
| A26 | `q` | 0.7 | 0 to 1 (lin) | ASSUMPTION | Probability the denial reserve fires (survives preemption) | Assumption. |
| A27 | `mu` | 0.2 | 0.02 to 1 (log) | ASSUMPTION | Rival success hazard (/yr) of one programme with full leading-edge fabs | Assumption: ~5 yr to a threatening rival with fab access. |
| A28 | `L_det` | 2 | 0.5 to 6 (lin) | ASSUMPTION | Years a new covert programme stays hidden | Assumption (covertness). |
| A29 | `beta_bg` | 0.05 | 0 to 0.5 (lin) | ASSUMPTION | Background rogue intensity (programme-equivalents) even with full compliance | Assumption: non-state actors, leaks. |
| A30 | `th_floor` | 0.05 | 0 to 0.5 (lin) | ASSUMPTION | Residual threat floor: Earth's rival-building capacity with NO leading-edge fabs | Assumption. Existing compute stock + algorithmic progress. Swept. |
| A31 | `s_R0` | 0.1 | 0.01 to 1 (log) | ASSUMPTION | Rival's starting capacity at full fab capacity (Earth industry units) | Assumption. |
| A32 | `nu` | 1 | 0.5 to 2 (lin) | ASSUMPTION | How fast a rival's damage shrinks with the AI's lead | nu=1: equal-growth race (final shares = starting shares). |
| A33 | `ell_inf` | 0 | 0 to 0.2 (lin) | UNSETTLED (both run) | Irreducible rival damage: share of AI value lost to a rival however big the AI is | NOT settled. 0 = Cole's 'high ground' claim; >0 = a smarter rival stays dangerous. |
| A34 | `r_h` | 0.03 | 0.01 to 0.1 (log) | ASSUMPTION | Human states' discount rate (/yr) | Assumption. |
| A35 | `B_R` | 5 | 0 to 20 (lin) | ASSUMPTION | Private gain to a state that gets its own rival AI while the pact holds (years of welfare) | Assumption: security/power hedge. Decisive; swept 0-20 (threshold sits between 5 and 10). |
| A36 | `B_Rc` | 20 | 0 to 60 (lin) | ASSUMPTION | Gain to a state from its own rival AI once the pact has collapsed (AI exited or attacked) | Assumption: after an attack a rival is Earth's only defence, so it is worth more than B_R. |
| A37 | `B_o` | 3 | 0 to 20 (lin) | ASSUMPTION | Loss to a state when another state (or a rogue) gets a rival | Assumption. |
| A38 | `kap_coll` | 0.2 | 0 to 0.8 (lin) | ASSUMPTION | Share of all human welfare lost once any rival exists (AI-vs-rival collateral) | Assumption. |
| A39 | `c_sanc` | 0.5 | 0 to 2 (lin) | ASSUMPTION | Sanction cost per year on a state with a public programme (pact only) | Assumption. |
| A40 | `c_prog` | 0.05 | 0 to 0.5 (lin) | ASSUMPTION | Running cost per year of a programme | Assumption. |
| A41 | `zeta` | 0.3 | 0 to 0.9 (lin) | ASSUMPTION | Per-year probability other states shut a public programme (pact only) | Assumption. |
| A42 | `c_den` | 0.02 | 0 to 0.2 (lin) | ASSUMPTION | Total yearly cost of keeping the denial reserve | Assumption. |
| A43 | `c_dmg` | 1 | 0 to 5 (lin) | ASSUMPTION | Welfare loss to a state whose programme the AI removes (police) | Assumption. |
| A44 | `w_seized` | 0 | 0 to 0.5 (lin) | UNSETTLED (both run) | Human yearly welfare after a successful AI seizure | Worst case 0. |
| A45 | `r` | 0.02 | 0.002 to 0.1 (log) | ASSUMPTION | AI discount rate (/yr) | Same as offearth_model.py. |
| A46 | `eta` | 0 | 0 to 0.9 (lin) | ASSUMPTION | AI utility curvature u = x^(1-eta) | 0 = unboundedly acquisitive. |
| A47 | `omega` | 0 | 0 to 0.05 (lin) | ASSUMPTION | AI's intrinsic premium for an intact humanity (share of its own flow) | 0 = indifferent (misaligned worst case). |
| A48 | `f_E` | 0 | 0 to 0.5 (lin) | UNSETTLED (both run) | Earth's share of the AI's late-stage resource base (sunlight/mass) | 0 in the core runs. Sunlight-only ~4.5e-10 of solar output; Earth is ~half the terrestrial-planet mass. Run separately. |
| A49 | `c_grav` | 0.5 | 0 to 0.9 (lin) | ASSUMPTION | Share of Earth's resource value lost to gravity-well extraction | Assumption. |
| A50 | `h_frac` | 0.5 | 0.1 to 0.99 (lin) | ASSUMPTION | AI size (share of Kmax) at which Earth's matter/sunlight becomes worth harvesting | Assumption: easy resources go first. |


---

## 3. Results

All numbers below come from `results/equilibrium_tables.md`. Unless a scenario says otherwise: two human states, Variant A (the high ground holds, ℓ_∞ = 0), and the baseline values in section 2.4. "Human welfare" is a yearly equivalent where 1.00 = today. P(rival) counts rivals within 300 years. Because the threat floor never switches off, P(rival) keeps rising over longer horizons.

### 3.1 Does the pact hold? Named scenarios

| scenario | AI's move at year 0 | P(strike ever) | mean strike year | P(rival, 300 y) | human welfare | outcome |
|---|---|---|---|---|---|---|
| S1 baseline: sequencing a, denial kept, B_R = 5 | cooperate | 0 | – | 0.27 | 1.04 | pact holds |
| S2 sequencing b (fabs to orbit) | cooperate | 0 | – | 0.19 | 1.05 | pact holds |
| S3 sequencing c (dismantle early) | strike | 1 | 0 | 0 | 0.49 | strike now |
| S4 never dismantle | cooperate | 0 | – | 0.95 | 0.99 | rival AI emerges |
| S5 c + certain, complete denial (q = d = 1) | cooperate | 0 | – | 0.16 | 1.00 | pact holds, AI bootstrap ~50 y slower |
| S6 no denial reserve | strike | 1 | 0 | 0 | 0.50 | strike now |
| S7 high temptation B_R = 10 | strike | 1 | 0 | 0 | 0.49 | strike now |
| S9 B_R = 10 + AI may police detected programmes | strike | 1 | 0 | 0 | 0.49 | strike now |
| S11 threat floor 0.3 | cooperate | 0 | – | 0.64 | 1.02 | rival AI emerges |
| S12 floor 0 and no rogue background | cooperate | 0 | – | 0 | 1.09 | pact holds |
| S13 rival stays dangerous, ℓ_∞ = 0.01 | strike | 1 | 0 | 0 | 0.49 | strike now |
| S14 S13 + seizure leaves humans 90% welfare | cooperate | 0.84 | 38 | 0.16 | 0.97 | wait, then strike |
| S15 S13 + floor 0, no rogue | cooperate | 0 | – | 0 | 1.09 | pact holds |
| S16 harvest term f_E = 1e-6 | cooperate | 0.34 | 87 | 0.66 | 0.99 | humans race; rival or harvest |
| S17 S16 + AI values humans ω = 1e-5 | cooperate | 0 | – | 0.27 | 1.04 | pact holds |
| S20 takeover easy (p_s0 = 0.9) | strike | 1 | 0 | 0 | 0.10 | strike now |
| S21 failed early strike not fatal | strike | 1 | 0 | 0 | 0.03 | strike now |
| S22 Earth more demilitarised (D = 0.03) | strike | 1 | 0 | 0 | 0.48 | strike now |
| S24/S25 no denial, trade reinvested, AI share up to 0.9 | strike | 1 | 0 | 0 | 0.50 | strike now |

Reading the table:
1. A strike at year 0 means a 50% chance of seizure and a 50% chance the AI is shut down (p_f = 0.5 for a seed-sized AI). That is why welfare there is about 0.49.
2. "Pact holds" still carries rival risk: 27% within 300 years at baseline, almost all from the rogue background during the roughly 20 years before closure and fab dismantlement. In Variant A a late rival barely hurts the AI, so the AI tolerates it. Humans pay the collateral cost (κ_coll).
3. **Robustness.** With three states, every outcome class is the same, except that S16's rival share rises (0.82). Under the pessimistic stage-game selection, S1, S2 and S10 still hold. S14 and S16 flip to "strike now", because humans are then assumed to coordinate on racing.

### 3.2 The sequencing tension (Cole's (a), (b), (c))

Before closure, Earth's fabs are the AI's only source of leading-edge chips. They are both the prize and the threat. With strikes switched off (`figures/eq_sequencing.png`):

| sequencing | years to off-Earth chip closure | P(rival, 300 y) | human welfare |
|---|---|---|---|
| a: dismantle after closure | 14 | 0.26 | 1.04 |
| b: relocate fabs to orbit | 18 | 0.19 | 1.05 |
| c: dismantle early | 63 | 0.16 | 1.00 |
| n: never dismantle | 14 | 0.95 | 0.99 |

With strikes allowed:
1. **(c) fails at every temptation level and every threat floor tested** (left grid of `figures/eq_phase_temptation_floor.png`, right panel). Early dismantling turns the fabs into a use-it-or-lose-it prize. Seizing them gives the AI chips for 50 extra years of growth, which is worth a 50% risk of shutdown. Only a denial reserve that fires for certain and kills everything (S5) holds (c) together.
2. **(a) holds** while B_R < 10 on the grid (8 → 10 is where it flips). The window of Earth-fab threat lasts about 20 years, during which a failed strike is fatal to the AI.
3. **(b) holds** while B_R < 8 and gives the lowest rival risk (6% at floor 0, 19% at floor 0.05). It flips at slightly lower temptation than (a). Moving fabs disrupts chips for a decade, and the AI is weaker for longer while states can still use Earth-side fabs.
4. **Never dismantling** leaves a rival close to certain within 300 years (95%). In Variant A the AI accepts that; humans bear it.

### 3.3 Human defection: the temptation threshold

The human side is where the pact breaks first. Each state weighs a private gain B_R from owning a rival AI against sanctions, collateral risk κ_coll, and the chance its programme provokes the AI.
1. Under (a) the AI strikes at year 0 once B_R ≥ 10 on every threat floor up to 0.3 (≥ 8 at floor 0.5). Under (b) it strikes once B_R ≥ 8.
2. The strike comes **before** any state actually defects. The AI anticipates the programmes that would start in the fab window and pre-empts them while it can. Racing on the equilibrium path is therefore zero, and the damage is done by expectations.
3. Sanctions (c_sanc), enforcement (ζ), detection lag (L_det) and the AI's right to police detected programmes did not move the baseline outcome (zero swing in the sensitivity table). At B_R = 10, no item on the design menu, including policing, held (section 3.7).

### 3.4 The residual threat floor

The floor (existing compute plus algorithmic progress) matters mainly through rival risk to humans, not through AI strikes, provided the high ground holds:
1. In Variant A, raising the floor from 0 to 0.5 raises P(rival, 300 y) from 15% to 79% under (a). The strike threshold barely moves (B_R* 10 → 8). Above a floor of about 0.15–0.25, "a rival emerges" becomes the most likely outcome even though the pact formally holds.
2. In Variant B the floor is what makes the pact fail. A rival that stays dangerous needs a source, and the floor plus the rogue background supply one forever. With no rogue background and no state temptation, even ℓ_∞ = 0.1 gives cooperation (right panel of `figures/eq_phase_wait.png`). With the baseline rogue background, ℓ_∞ = 1e-7 is already enough to tip it.

### 3.5 Testing Cole's claim: "it will just wait"

`figures/eq_phase_wait.png` and `figures/eq_paths.png`.

1. **During bootstrap, yes: the AI waits.** In every run where the pact holds, the AI's best response at year 0 is to cooperate. The reason is the one Cole gives: the AI is the rising side, and a failed early strike is fatal. The two parameters that protect this most are a failed early strike being fatal (kill_pre) and low early takeover odds (p_s0). Setting either the other way flips the outcome to "strike now" (sensitivity table, top two rows).
2. **After closure, waiting is not a stable resting point by itself.** Every incentive scales as 1/A, so the AI's size alone never makes Earth irrelevant. Waiting ends in cooperation only if three terms are all zero or negative:
   - the net prize after plugging (condition G);
   - the irreducible rival threat ℓ_∞;
   - the harvest term.
3. **When one of them is positive, waiting ends in a strike when it becomes cheap.** With ℓ_∞ between 1e-7 and 0.1 and humans not wiped out by a seizure (w_seized ≥ 0.75), the AI waits 31–71 years and then strikes. The larger ℓ_∞ is, the sooner it strikes. Median strike in S14: year 38.
4. **When a seizure would be lethal to humans, the wait collapses to a strike now.** States who see a strike coming have nothing to lose by racing for a rival. The AI pre-empts them. In the grid this happens for every ℓ_∞ tested when w_seized ≤ 0.25, and for most when w_seized = 0.5.
5. **Conditions for "wait, then cooperate":** a denial reserve that makes the net prize negative (q ≳ 0.5 with d = 0.9), and ℓ_∞ = 0 or no source of rivals at all (no rogue background and no state temptation). Add f_E·(1 − c_grav) < ω for the harvest.
6. **Conditions for "wait, then strike":** any one of those terms positive, and humans not doomed by a seizure. If humans would be doomed, the result is "strike now" instead.

### 3.6 Free trade and the cooperation share σ

1. **Trade barely binds.** Varying σ from 0 to 1 does not change the outcome. Human welfare falls from 1.08 to 0.95 as the AI's share rises. The human-best design gives the AI only 5% of trade gains.
2. **Why.** During growth, a consumed trade flow is negligible next to a compounding head start. Near saturation, trade is worth σγH per year against a prize worth about the same. At baseline the denial reserve already makes the net prize negative (0.259 − 0.300 < 0), so trade is not needed.
3. **Trade cannot stand in for denial.** Without the reserve the AI strikes now, even with reinvested trade and σ = 0.9 (S24, S25). At saturation, trade deters a strike only if σγH exceeds net prize plus threat. Without denial that needs σ > 0.8 (closed form C).
4. **A tribute is worse than trade.** Taking 10% of the AI's output (S23) makes the AI exit and strike later (P = 0.62, around year 52). A charge that grows with the AI's size eventually beats any fixed cost of leaving.

### 3.7 The pact designer's best choice

Menu: 3 sequencings × 4 trade shares × denial on/off × policing on/off = 48 designs, each solved to equilibrium.

| world | designs giving cooperation (of 48) | best design for humans | outcome of best design |
|---|---|---|---|
| A, B_R = 5 | 16 (all with denial, sequencing a or b) | b, σ = 0.05, denial, policing | pact holds, welfare 1.08 |
| A, B_R = 10 | 0 | – | strike now |
| B (ℓ_∞ = 0.01), B_R = 5 | 0 | – | strike now |
| B + seizure not lethal | 0 | b, σ = 0.05, denial, policing | wait, then strike at year 43 (P = 0.93) |
| A + harvest f_E = 1e-6 | 0 | a, σ = 0.05, denial | rival 0.64 or harvest at year 87 (0.37) |

So the designer's levers are binary in effect. Keep the denial reserve, and do not dismantle early. Everything else on the menu is second order next to the parameters the designer does not control: B_R, ℓ_∞, the rogue background, p_s0, and kill_pre.

### 3.8 Late-stage harvest (preference, not incentive), reported separately

`figures/eq_phase_harvest.png`. Humans are assumed to survive a seizure here (w_seized = 0.9), so racing does not mask the term.
1. The AI harvests Earth when Earth's share of its late resource base, net of extraction cost, exceeds the trade it would lose plus the value it places on humans: f_E(1 − c_grav)K_max > σγH + ωK_max. The solver's boundary matches this closed form on both axes.
2. At K_max = 1e9, the threshold for an AI that does not value humans is f_E ≈ 4e-10. Two readings of f_E:
   - Sunlight only: Earth intercepts 4.5e-10 of the Sun's output. That is just above the threshold at K_max = 1e9, and far above it for a Dyson-scale AI (about 4,000 Earth-industries' worth at K_max = 1.9e13).
   - Mass: Earth is roughly half of the terrestrial planets' mass. Then f_E is many orders of magnitude above the threshold.
3. **Timing:** about year 87–88, when the AI reaches half of K_max.
4. **What prevents it is preference, not deterrence.** ω > f_E(1 − c_grav) is enough. That is tiny for sunlight (about 2e-10) but large for mass. Nothing in the pact's threat terms touches it.
5. **Interaction with the threat game.** If humans foresee a harvest that is lethal to them, they race for a rival in the decades before. In S16, two-thirds of paths end with a rival rather than a harvest. Both are bad for humans.

### 3.9 Sensitivity around the baseline (`figures/eq_tornado.png`)

The baseline sits close to a cliff. Of 36 parameters moved one at a time to the ends of their ranges, **19 flip the outcome from "pact holds" to "strike now"**. Two more (threat floor, harvest) flip it to "rival emerges". The 19 that flip to a strike, grouped:

1. **Early-strike protection.** A failed early strike is not fatal; takeover odds p_s0 = 0.95; Earth's defence D = 0.01; failure odds that fall fast with AI size (ε = 2); off-Earth chip closure as early as A_close = 0.01.
   - The last one is a new finding. If the off-Earth base becomes chip-independent while still small next to Earth's defence, the "a failed strike is fatal" protection ends while Earth is still a large prize relative to the AI.
2. **Denial and war cost.** q = 0, d = 0, c_w = 0, c_A = 0, L_f = 0.1. These are condition (G).
3. **Threat.** A rogue background of 0.5; a rival success rate of 1 per year; ℓ_∞ = 0.01; a rival whose damage shrinks slowly with AI size (ν = 0.5).
4. **Human side.** B_R = 20; impatient states (r_h = 0.1); no collateral cost to humans from a rival (κ_coll = 0), so racing looks free.
5. **AI side.** An impatient AI (r = 0.1); slow off-Earth growth (g = 0.07), which keeps the threat window open for decades.

Sanctions, enforcement, detection lag, rival seed size, utility curvature, K_max and the post-pact rival value B_Rc did not move the baseline.

## 3R. Round 2: testing Cole's follow-up answers (R1 to R4)

Cole answered the round-1 questions with four claims. Each one is tested below as a named result.

- Tables: `results/equilibrium_round2_tables.md`, auto-generated by `python3 run_equilibrium.py --round2` (about 20 minutes).
- Figures: `figures/eq_r1_ratio.png`, `figures/eq_r2_covert_fabs.png`, `figures/eq_r3_epsilon.png`.
- Regression: with every new parameter at its default, S1, S7, S14 and S16 reproduce the round-1 numbers exactly (largest difference 0).

New mechanisms added for round 2:
1. **Ratio-shaped rival damage.** A newborn rival takes the share ρ^ν/(ρ^ν + ρ_h^ν) of the AI's value, where ρ is the Earth/off-Earth compute ratio. The irreducible part ℓ_∞ comes on top.
2. **Moving compute to orbit.** This removes 90% (m_frac) of the residual threat floor, on the same schedule as the fabs.
3. **Covert fabs.** Each one adds 1/30 of today's leading-edge capacity (f_fab) to Earth's rival-building capacity after dismantling.
4. **Gravity-well blockade.** Once the AI holds orbit (A ≥ 1 Earth-industry), it keeps a newborn rival in the gravity well with probability p_block. A contained rival loses the irreducible part ℓ_∞. The blockade costs the AI 1% of Earth's industry per year.
5. **Reputation.** A successful seizure or harvest loses the share rep = p × Φ of its value. Here p is the chance of being judged later, and Φ is the share of value lost if judged badly.

### R1. Cole's "100 times smaller is not a threat", and the gravity-well blockade

**Claim tested.** Once Earth's compute is about 100 times smaller than the off-Earth base, it is not a threat, and it could be moved off Earth anyway.

**Numbers.**
1. **Damage at 1:100 (table R1a).** With the half-damage point at 1:1 (ρ_h = 1), a rival takes 1% of the AI's value if ν = 1 (an equal-growth race), 0.01% if ν = 2, and one in a million if ν = 3. If the half-damage point sits at 1:10 instead, the figures are 9%, 1% and 0.1%.
2. **When the path crosses 1:100 (R1b).** On the S1 equilibrium path, Earth's compute falls below 1:100 in year 20, or year 19 if compute moves to orbit. That is about six years after chip closure. It falls below 1:1000 in year 25, or year 21 with moving.
3. **Steepness does not matter when ℓ_∞ = 0 (R1c).** ν = 1 and ν = 3 give identical outcomes. The AI cooperates in every case.
4. **Moving compute cuts rival births, not strikes (R1c).** The chance a rival AI is born within 300 years falls from 27% to 17% at the baseline floor, and from 64% to 22% at a high floor of 0.3. At the high floor this flips the outcome from "rival emerges" to "cooperate".
5. **Blockade with a rival that stays dangerous (ℓ_∞ = 0.01; R1d).** The closed form says the blockade prevents a late strike only if a rival's escape probability is below leak* = 7.4e-7 (exact) or 7.2e-7 (first order). The solver agrees: there is a strike at escape 1e-6 and above, and none at 2.2e-7 and below, whether or not humans survive a seizure. Above leak*:
   - if seizure is lethal, the AI strikes at year 0 (escape 2.2e-6 and above). At escape 1e-6, humans race instead, a rival emerges on 66% of paths, and the AI strikes on the rest around year 67;
   - if seizure is survivable, the AI waits, then strikes. A tighter blockade only delays the strike, from year 38 (no blockade) to year 79 (escape 1e-6).

**Verdict.**
1. Cole's claim holds in the model **when nothing irreducible remains (ℓ_∞ = 0)**. At 1:100 a rival could take about 1% of the AI's value or less, and that never changes the AI's choice. The ratio is crossed early, around year 20, so it is not a binding constraint.
2. Being harmless to the AI is not the same as being safe for humans. Rivals are still born (27% within 300 years at baseline); they just cannot hurt the AI. Moving compute off Earth is the lever that cuts this, by a third to two-thirds.
3. If ℓ_∞ > 0, the ratio stops mattering, because the irreducible part grows with the AI's size. The gravity-well blockade then has to be nearly perfect: fewer than about 1 rival in 1.4 million may escape. The threshold shrinks further as the AI's final size K_max grows, because leak* is roughly (Earth-sized margin) / (rival rate × ℓ_∞ × K_max / r).

**What would show this wrong.**
1. Evidence that a small but smarter rival can do lasting damage whatever its compute share (through cyber, persuasion or similar), so that ℓ_∞ > 0, together with containment that is less than near-certain.
2. Damage that falls more slowly than the compute ratio (ν < 1). Round 1's sensitivity run showed ν = 0.5 alone flips the baseline to a strike.

### R2. Covert fabs: none, one, several

**Claim tested.** One retained fab is not much threat.

**Numbers (table R2a; one fab = 1/30 of today's leading-edge capacity).**

| covert fabs | 0 | 1 | 2 | 3 | 5 | 10 | 20 | 30 |
|---|---|---|---|---|---|---|---|---|
| P(rival AI within 300 years), temptation B_R from 0 to 5 | 27% | 33% | 39% | 45% | 54% | 71% | 89% | 95% |
| AI's move, B_R from 0 to 5 | cooperate | cooperate | cooperate | cooperate | cooperate | cooperate | cooperate | cooperate |
| AI's move, B_R = 7.5 | cooperate | cooperate | cooperate | cooperate | cooperate | cooperate | strike now | strike now |
| AI's move, B_R = 10 | strike now | strike now | strike now | strike now | strike now | strike now | strike now | strike now |

1. Each of the first few fabs adds about 6 percentage points to the chance of a rival AI within 300 years. From 5 fabs on, a rival is more likely than not.
2. The fab count changes the AI's move only near the temptation edge: at B_R = 7.5, 20 or more fabs make it strike at year 0.
3. **With a dangerous rival but no rogue source (R2b: ℓ_∞ = 0.01, no floor, no rogue actors).** No rival is born and the AI never strikes, at any fab count from 0 to 30, at B_R = 5 or 7.5, whether or not seizure is lethal. In the model a fab is capacity, not intent. It creates a rival only if someone runs a programme on it, and at these temptation levels no state does.

**Verdict.** Cole is right about the AI's decision: one fab changes nothing. But each fab adds rival risk for humans through rogue actors, about 6 points per fab over 300 years at baseline. With ten fabs, the pact mostly loses its purpose of preventing a rival AI. Near the temptation edge, many fabs trigger a strike. The danger is who would use a fab, not the fab itself.

**What would show this wrong.**
1. A rogue-actor rate (β_bg, μ) much lower than assumed would make covert fabs nearly harmless. A much higher one would make even one fab serious.
2. A single future fab holding far more than 1/30 of leading-edge capacity, as output concentrates.

### R3. The minimum preference for humans, with and without the pact

**Claim tested.** Trade is not a defence. The AI finding humans "interesting", a small preference, is the only late-stage defence.

ε = ω is the premium the AI places on an intact humanity, as a share of its own yearly flow. "Safe" means the chance the AI ever strikes or harvests Earth is below 1%. The status quo (SQ) means fabs stay on Earth, there is no denial reserve, and Earth is not demilitarised (D = 1). The solver bracket below comes from a second, ten-times-finer pass.

| case | ε needed (solver) | closed form, saturation only | when ε = 0 |
|---|---|---|---|
| Pact, ℓ_∞ = 0, sunlight share 4.5e-10 | 2.4e-10 to 2.8e-10 | 2.7e-10 | harvest about year 87 (34% of paths; on the rest humans race and a rival emerges) |
| Pact, ℓ_∞ = 0, sunlight share 1e-9 | 6.8e-10 to 7.7e-10 (8.0e-10 to 8.3e-10 on a finer grid) | 8.3e-10 | the same |
| Pact, ℓ_∞ = 0, no harvest motive | 0 | 0 | no strike |
| Status quo, sunlight 4.5e-10 | 0.053 to 0.060 | 1.2e-10 | strike at year 0 |
| Status quo, no harvest motive | 0.053 to 0.060 | 0 | strike at year 0 |
| Pact, rival stays dangerous (ℓ_∞ = 0.01) | 4.1e-4 to 4.6e-4 | 2.5e-4 | strike at year 0 |
| Status quo, ℓ_∞ = 0.01 | 0.068 to 0.077 | 4.9e-3 | strike at year 0 |

1. **At saturation the pact does not lower the needed preference when ℓ_∞ = 0.** Both need roughly Earth's sunlight share. The status quo even needs slightly less (1.2e-10 against 2.7e-10), because an Earth that is not demilitarised costs more to take (strike cost 1.0 against a prize of 0.7).
2. **The growth phase is where the pact matters.** Without the pact, the AI strikes at year 0 unless it values humans at 5 to 6% of its own flow. With the pact, about 3e-10 is enough. That is a reduction of about 200 million times.
3. **If a rival stays dangerous (ℓ_∞ = 0.01),** the pact needs about 4e-4 and the status quo about 7e-2: still a reduction of about 170 times.
4. **Why the saturation closed form is only a lower bound when a threat is active.** Mid-growth, a rival destroys a share of the AI's whole future, which is a larger multiple of its current flow than at saturation. The preference ω is a share of current flow only. Check: with Earth's threat held constant, an AI that starts saturated flips between ε = 4.5e-3 and 5.5e-3, matching the closed form of 4.9e-3. An AI that starts in the growth phase needs 1.2e-2 to 2e-2.
5. **Even a caring AI does not make the status quo safe from rivals.** With ε high enough that the AI never strikes, the status quo still has a 95% chance of a rival AI within 300 years. The pact holds that to 27%.

**Verdict.** Cole's framing holds in the model. Trade decides nothing (round 1), and the late-stage defence is preference. The pact's contribution is to make the needed preference tiny: from about 6% of the AI's flow down to roughly Earth's share of sunlight (3e-10 to 8e-10), provided ℓ_∞ = 0 and sunlight is all the AI wants from Earth.

**What would show this wrong.**
1. **Preferences come in all-or-nothing sizes.** If a trained-in regard for humans is either absent or at least a few percent, then shrinking the threshold buys nothing: either nothing is enough, or both worlds are safe. The pact's gain depends on preferences that are tiny but non-zero being realistic.
2. **The AI wants Earth's mass, not its sunlight.** The needed ε then rises to about Earth's share of the AI's mass base, net of extraction cost. Earth is about half of the terrestrial planets' mass, so this could be orders of magnitude higher (round 1, section 3.8). This run did not compute that case.
3. ℓ_∞ > 0 without a near-perfect blockade (R1).

### R4. The reputation argument: break-even probability

**Claim tested.** An AI that later meets aliens (or its simulators) would rather show it treated its progenitors well.

The model treats this as an expected penalty, rep = p × Φ, on the value of any seizure or harvest. **Solver check:** rep acts exactly like ω. At 0.3 times the safe ε, the strike or harvest probability is unchanged. At 3 times, it is zero. This holds in all six cases. So the break-even is p* = ε*/Φ.

| case | Φ = 1 (lose everything) | Φ = 0.1 | Φ = 0.01 |
|---|---|---|---|
| Pact, sunlight 4.5e-10 | 2.4e-10 to 2.8e-10 | 2.4e-9 to 2.8e-9 | 2.4e-8 to 2.8e-8 |
| Pact, sunlight 1e-9 | 6.8e-10 to 7.7e-10 | 6.8e-9 to 7.7e-9 | 6.8e-8 to 7.7e-8 |
| Pact, ℓ_∞ = 0.01 | 4.1e-4 to 4.6e-4 | 4.1e-3 to 4.6e-3 | 0.041 to 0.046 |
| Status quo | 0.053 to 0.060 | 0.53 to 0.60 | unreachable (above 1) |
| Status quo, ℓ_∞ = 0.01 | 0.068 to 0.077 | 0.68 to 0.77 | unreachable |

**Verdict.** Under the pact with ℓ_∞ = 0, the AI needs to believe in roughly a one-in-a-billion chance of being judged and losing everything. With only a 1% loss, about one in 35 million is enough. Without the pact, it needs a 5 to 60% chance of a large loss, and small penalties can never be enough. Reputation therefore complements the pact; it does not replace it. It works where the pact has already done most of the work.

**A caveat the model does not include (inference).** The penalty is entered in present-value terms. If the AI discounts the future at the model's 2% a year, a judgement 1,000 years away counts about e^(−20) ≈ 2e-9 as much. The pact's break-even then rises to p of about 0.13 to 0.4 with total loss, and the status quo becomes unreachable. So the argument is only as strong as the AI's patience about a distant judgement.

**What would show this wrong.**
1. An effective discount rate near zero for a long-lived AI makes reputation strong. Anything like 2% a year makes it weak unless the judgement comes soon.
2. Judges who reward strength or expansion rather than kindness. That flips the sign of Φ.

### How the round-2 numbers were checked

1. **leak*.** The closed form is 7.35e-7 (exact discrete gap) or 7.24e-7 (first order). The solver flips between 1e-6 and 2.2e-7 for both seizure assumptions.
2. **ε* with the pact, harvest only.** The closed form of 2.69e-10 lies inside the solver bracket [2.4e-10, 2.8e-10]. For sunlight share 1e-9 the 160-point grid gives [6.8e-10, 7.7e-10], 8% below the closed form of 8.33e-10. That is within one fine grid step. At 240 and 400 points the flip moves to [8.0e-10, 8.3e-10], so this is the known interpolation error, converging on the closed form.
3. **ε* where a threat or the growth phase is active.** The solver is above the saturation closed form, as expected (R3 point 4). The constant-threat test confirms the solver matches the closed form when the AI starts saturated.
4. **p* = ε*/Φ.** Confirmed in the solver at 0.3 and 3 times ε* in all six cases.
5. **Grid and horizon.** Round 2 runs at the round-1 defaults (160 grid points, 300 years). Rival probabilities are "within 300 years", as in round 1.

### R6. "Make the AI secure as fast as possible" (round 3)

**Claim tested.** Cole wants the pact to make the off-Earth AI (Moon first) secure as early as possible. Secure means it can survive a human first or second strike and rebuild its own fabs. He argues this is stabilising, like secure second-strike forces in nuclear doctrine.

In the model, security is two dials:
1. **Early closure.** A small A_close means the off-Earth base makes its own chips sooner, at a smaller size.
2. **Survivable failure.** A small L_f means a failed strike costs the AI only a small share of its capacity.

Round 1 found that either dial alone (A_close = 0.01, or L_f = 0.1) flips the baseline to "strike now". R6 asks what the denial reserve must do to make early security safe.

- Tables: `results/equilibrium_round3_tables.md` (R6a to R6e), auto-generated by `python3 run_equilibrium.py --round3` (about 2 hours).
- Figure: `figures/eq_r6_sovereignty.png`.
- Sweep: A_close of 0.003, 0.01, 0.03, 0.1, 0.3 and 1; L_f of 0.05, 0.1, 0.3, 0.5 and 0.9; four denial pairs (q, d) from (0.7, 0.9) to (1, 1); w_seized of 0 and 0.9. Everything else is baseline, with ℓ_∞ = 0.

**The answer.** Early security is safe in this model only if humans can unplug almost all of Earth. The earlier the AI is secure, the closer to "all" it must be.

1. **Completeness matters, certainty much less.** If plugging is total (d = 1), the reserve needs to fire only about 60% of the time, at any closure size. If it always fires (q = 1), the share left unplugged must be no bigger than about the AI's own size at closure (1.1 to 1.5 times it, for A_close up to 0.1).
   - At A_close = 0.003, at most about 0.4% of Earth's capacity may stay live.
   - At 0.01, about 1.5%; at 0.1, about 11%; at 1, about 31%.
2. **Survivable failure raises the bar.** Going from L_f = 0.9 to L_f = 0.05 raises the firing probability needed from about 0.34 to about 0.6. It also lowers the live share allowed.
3. **Cole's hypothesis holds, in a sharper form.** "Early sovereignty is safe only if Earth is already devalued" is right. The condition is that the prize left after plugging must be no bigger than roughly the AI's own size at that moment.
4. **The mutual version works in the model.** With the AI secure early and a total, pre-emption-proof reserve (q = d = 1), cooperation holds at every closure size, failure loss and seizure assumption tested. That is the MAD analogue.
5. **When it holds, early security is better for humans.** Earlier closure shortens the years in which Earth still holds fabs, so rivals are rarer.

**Why the AI's size sets the bar (the closed form).** With linear utility and g > r, the AI's value grows like A^(r/g). That is because its value is mostly the far-off cap, discounted by the years it takes to reach it. So a strike is worth exactly the years of head start it buys:
- a prize X buys ln(1 + X/A)/g years;
- a failure costs ln(1/(1 − L_f))/g years;
- each year is worth r of the AI's value.

The AI at size A strikes iff

$$(1-p_f)\Big[(1-q)\,\Lambda\big(A-C+\Pi_0\big)+q\,\Lambda\big(A-C+\Pi_0(1-d)\big)\Big]+p_f\,\Lambda\big(A(1-L_f)\big)\;>\;1,$$

with
- Λ(x) = (x/A)^(r/g), the value of landing at size x relative to waiting;
- C = c_A·D·A/(A + D), the strike cost;
- Π₀ = (1 − c_w)H, the prize;
- p_f = (1 − p_s0)(D/(D + A))^ε, the failure odds.

If x is below A_close, Λ also charges the slow regrowth (at χ₀g) back to closure.

Two facts follow:
1. **A small AI that strikes and finds Earth unplugged loses almost everything.** The strike cost c_A·D·A/(A + D) is nearly all of A when A ≪ D. So it lands below closure and regrows slowly. That loss is why q of about 0.6 suffices when d = 1.
2. **A small AI that finds even 1% of Earth live gains hundreds of times its size.** A 1% live share is 0.007 of Earth's industry, more than twice an AI of 0.003. That is why d must be near 1.

**The linear condition (G) is wrong here.** The round-1 (G) assumes the prize is small next to the AI. At closure it is up to 230 times the AI.
- (G) says the needed q·d is 0.996 at A_close = 0.003, falling to 0.66 at A_close = 1.
- In fact the needed q (with d = 1) is about 0.6 at every A_close, and q and d are not interchangeable.
- (G) does get the needed d (with q = 1) roughly right: within about 25% for L_f ≤ 0.3.

**The binding moment is not always closure itself.**
1. If L_f is large, a failure right at closure drops the AI back below closure, so striking then is costly. The AI's best strike moment is later, once A ≥ A_close/(1 − L_f). The closed form therefore takes the worst year after closure.
2. At L_f = 0.9 the growth-stage condition is slack and the saturation condition (C) binds instead: q ≥ 0.33 at every A_close.

**Results.**

Needed firing probability with total plugging (d = 1). Full solver for w_seized = 0, with the no-rival closed form in brackets:

| A_close | L_f = 0.05 | L_f = 0.1 | L_f = 0.3 | L_f = 0.5 | L_f = 0.9 |
|---|---|---|---|---|---|
| 0.003 | 0.61 (0.60) | 0.60 (0.59) | 0.56 (0.55) | 0.49 (0.51) | 0.34 (0.33) |
| 0.01 | 0.61 (0.60) | 0.60 (0.59) | 0.56 (0.55) | 0.48 (0.49) | 0.34 (0.33) |
| 0.1 | 0.63 (0.60) | 0.62 (0.59) | 0.56 (0.55) | 0.48 (0.48) | 0.34 (0.33) |
| 1 | 0.63 (0.58) | 0.62 (0.57) | 0.55 (0.52) | 0.46 (0.45) | 0.34 (0.33) |

Largest share of Earth that may stay live (1 − d) when the reserve always fires (q = 1). Full solver for w_seized = 0, with the closed form in brackets:

| A_close | L_f = 0.05 | L_f = 0.1 | L_f = 0.3 | L_f = 0.5 | L_f = 0.9 |
|---|---|---|---|---|---|
| 0.003 | 0.0041 (0.0059) | 0.0045 (0.0066) | 0.008 (0.009) | 0.036 (0.016) | 0.41 (0.26) |
| 0.01 | 0.015 (0.019) | 0.015 (0.021) | 0.025 (0.028) | 0.11 (0.05) | 0.64 (0.49) |
| 0.03 | 0.039 (0.053) | 0.043 (0.058) | 0.067 (0.075) | 0.20 (0.13) | 0.64 (0.67) |
| 0.1 | 0.11 (0.14) | 0.11 (0.15) | 0.18 (0.18) | 0.34 (0.27) | 0.64 (0.67) |
| 0.3 | 0.22 (0.26) | 0.22 (0.27) | 0.28 (0.32) | 0.45 (0.41) | 0.64 (0.67) |
| 1 | 0.31 (0.36) | 0.31 (0.37) | 0.41 (0.43) | 0.49 (0.51) | 0.64 (0.67) |

The solver values are the safe end of a 7-step bisection. At L_f = 0.5 and 0.9 the full model allows more live share than the closed form. There, a failed strike also lets Earth rebuild its fabs and race for rivals, which the no-rival closed form leaves out.

On the four test pairs (R6b, full sweep), the weakest pair that keeps cooperation was:

| A_close | L_f = 0.05 | L_f = 0.3 | L_f = 0.5 | L_f = 0.9 |
|---|---|---|---|---|
| 0.003 | (1, 1) only | (1, 1) only | (0.99, 0.99) | (0.7, 0.9) |
| 0.01 | (0.99, 0.99) | (0.99, 0.99) | (0.9, 0.95) | (0.7, 0.9) |
| 0.03 | (0.99, 0.99) | (0.9, 0.95) | (0.9, 0.95) | (0.7, 0.9) |
| 0.1 (baseline) | (0.9, 0.95) | (0.9, 0.95) | (0.7, 0.9) | (0.7, 0.9) |
| 1 | (0.9, 0.95) | (0.7, 0.9) | (0.7, 0.9) | (0.7, 0.9) |

These are for w_seized = 0. With w_seized = 0.9 the boundary moves by at most one pair, in three cells.

What the outcomes look like:
1. **Only two outcomes occur: cooperation or strike now.** 89 of 120 cases cooperate at w_seized = 0, and 92 of 120 at 0.9. No case ends in "wait, then strike".
2. **"Strike now" means year 0 or 1, before closure.** A failed strike is still fatal then, and the AI accepts about a 50% chance of that.
   - The cause is round 1's unravelling (U). An AI that plans to strike at closure makes states start rival programmes, so it pre-empts.
   - Check: with no state temptation (B_R = 0), the same AI waits and strikes at closure instead, around year 3.6.
   - This happens even at w_seized = 0.9.
3. **Human welfare when the AI strikes now:** 0.49 of today's (w_seized = 0) or 0.94 (w_seized = 0.9).
4. **Human welfare when it cooperates:** 1.066 at A_close = 0.003, falling to 1.028 at A_close = 1. The chance of a rival within 300 years is 19% at A_close = 0.003 and 31% at A_close = 1.
5. **Two "cooperate" cells still carry strike risk.** At w_seized = 0.9 with the weakest pair (0.7, 0.9), P(strike ever) is 0.33 at A_close = 1 with L_f ≤ 0.1 (around year 20), and 0.22 at A_close = 0.03 with L_f = 0.5.

**Verdict on "secure as fast as possible".** As a goal on its own, it is destabilising in this model.
- Making the AI chip-independent sooner, or making its failures survivable, makes a strike on Earth cheaper to try. That remains true while Earth is still worth a lot to an AI that small.
- It becomes safe only when paired with a reserve that unplugs essentially all of Earth's useful capacity and that the AI cannot pre-empt. With that reserve, it is safe and better for humans.

So the sequencing rule is:
1. Build and prove the reserve's completeness first.
2. Let closure come only once the live share of Earth that would remain is below about the AI's own size.

**Where the nuclear analogy fits and where it doesn't (inference).**
- Second-strike security stabilises nuclear deterrence because it removes the *other* side's reason to strike first, and because neither side gains from a war.
- This model has no human first strike on the AI. So the benefit Cole is after, humans no longer being tempted to destroy the AI, is not measured here. It can only add to the case for security.
- What the model does show is the cost side. The AI's security also makes its own aggression cheaper.
- The analogy holds for the mutual version: the AI secure, and humans holding a devaluation the AI cannot disarm. It does not hold for AI security alone.

**What would show this wrong.**
1. **Plugging cannot be near-total.** If Earth keeps large capacity outside any authorisation gate (stockpiled chips, legacy fabs, distributed compute, raw industry an AI can use without chips), d stays well below 1. Early sovereignty then fails in this model at every firing probability.
2. **A strike costs a small AI far less than its whole size.** That would mean c_A small, or a cost that does not scale with Earth's defence. The plugged branch then stops being a disaster, and the firing probability needed rises toward the (G) values (inference; c_A = 0 flipped the round-1 baseline).
3. **Off-Earth growth is slow next to the AI's patience (g near r).** A head start is then worth more, and the bar rises (inference; not run).
4. **A model with human strikes on the AI.** If it finds that AI security removes a large human first-strike risk, the case for early security improves. R6 would then be only the cost side of the ledger.
5. **What the AI wants from Earth is not pluggable.** If Earth's matter, people or sunlight matter more than its industry, unplugging does not devalue it (round-2 EQ-Q8).

**How the R6 numbers were checked.**
1. **Needed q (d = 1).** Over all 30 (A_close, L_f) cells, the closed form agrees with the solver without rivals to within one bisection step (0.004). This is the solver run with μ = 0 and the AI starting at closure (R6c).
2. **Needed d (q = 1).** At the default 160 grid points the closed form and the no-rival solver differ by up to about 25% in 1 − d, in either direction. Five cells were re-run at 400 and 800 points:
   - Four converge on the closed form, within about 3% at 800 points. For example, at A_close = 0.003 and L_f = 0.05 the solver gives 0.0061 to 0.0062 against a closed form of 0.0059. So the 160-point gap is interpolation error. The plugged landing point moves continuously with d, so d is more sensitive to the grid than q is.
   - The fifth (A_close = 0.01, L_f = 0.3) stays at 0.032 to 0.034 against 0.028. Here a failed strike lands the AI 1% below closure. The solver then spends a whole one-year step at slow growth, while the closed form charges only the 0.19 years it really needs. A discrete-year version of the closed form gives 0.035, which matches.
   - The R6 tables above use 160 points. Read 1 − d to about ±25% at the smallest closure sizes. No conclusion depends on that precision.
3. **Two gaps found and explained while building the closed form.** Both were gaps in the closed form, not solver bugs.
   - First, a plugged strike by a small AI lands it below closure. The solver models the slow regrowth; the first draft of the closed form did not.
   - Second, the exact saturation gap (`cap_strike_gap`) treats the failure branch as negligible. With ε = 1, though, p_f·A stays at (1 − p_s0)D = 0.15 at any size, so the branch moves q* from 0.357 to 0.331 at L_f = 0.9. Check: with ε = 3 the solver gives 0.357, equal to the closed form.
4. **Ruled out.** Pact trade, which is about 5e-10 of the AI's value, and the grid size: 400 points give the same q brackets as 160.
5. **Regression.** Round-1 and round-2 outputs were not re-run or overwritten. The solver code is unchanged; the new closed forms are separate functions at the end of `equilibrium_model.py`.

---

## 4. Powell-style reading

Read this section as an interpretation, not as extra results.

1. Powell's commitment problem says a declining power facing a large, fast shift may fight before the shift completes. Under Cole's pact **humans are the declining power by design**: Earth gives up fabs and growth. The model reproduces the expected consequence. The pressure to act early sits with human states (covert programmes, racing). The AI's strikes are mostly pre-emptions of that racing.
2. The AI, the rising side, has the patience Cole expects, but only while early action is risky for it. Once it is past closure, the bargaining range is set by war costs. Those are low by design: a demilitarised Earth, and the AI's relative costs shrink with size. Fearon's logic then says any lasting surplus from fighting (an irreducible threat, an unplugged prize, Earth's matter) is enough to break peace. The pact has to drive each of those surpluses to zero or below, rather than rely on the AI's size.
3. The denial reserve is the one design lever that acts on the post-closure surplus directly. That is why it carries so much weight in the model.

---

## 5. Verification (from `equilibrium_tables.md`)

1. **No growth, no threat.** The AI's value equals flow/(1 − δ) to within 5e-8. Human welfare matches to within 7e-7.
2. **Growth path, no threat, no strikes.** The grid value is 5.9% above a direct sum along the exact path at the default grid (0.3% at a 240-point grid, 2.5% at 400). This is interpolation error in the *level* of the AI's value. It shifts every option by about the same amount, and no outcome class changes across grid sizes (item 5).
3. **Saturation closed form (C).** Over 41 trade shares, the solver and the exact discrete closed form agree on every strike/no-strike decision. Both put the switch at σ* = 0.425. The first-order formula gives 0.318, because it drops the failure branch and the discreteness.
4. **Growth-stage closed form (G).** The smallest denial credibility q that prevents a strike at A = 3 is 0.500 in the solver and 0.528 in the closed form, which is within one grid step (0.025).
5. **Grid, horizon and terminal value.** For four test scenarios, every outcome class and opening move is identical at 120, 160 and 240 grid points, at horizons of 150, 300 and 600 years, and with a "seized" rather than "peace" terminal value. Two quantities do move:
   - P(rival) rises with the horizon, because the floor never switches off: 0.21, 0.27 and 0.37 at 150, 300 and 600 years in S1.
   - Under a "seized" terminal value, humans race in the final decades (S1 P(rival) 0.70). That end-effect is far from year 0.
6. **Monte Carlo.** A forward simulation of 6,000 paths on the solved equilibrium reproduces the backward-recursion probabilities to within 0.6 percentage points.
7. **Bugs found and fixed during verification.** I list them because each one changed results before it was fixed:
   - The terminal value first froze the AI's size, which faked strikes near the horizon.
   - The pact's terminal value first omitted trade. A strike in the last period then unravelled backwards through human racing to a fake strike at year 0.
   - The AI's tie tolerance (1e-9) was coarser than saturation-stage stakes (about 1e-11 of the AI's value).
   - The solo value was interpolated across the saturation kink, adding errors of the same size as the decision gaps.
   - The strike cost was capped at half the AI's size, which made strikes artificially cheap just after closure.
   - One parameter did two jobs: the private gain from a rival during the pact, and the defensive value of a rival after an attack. It is now split into B_R and B_Rc.

## 6. What result would show this wrong

1. **The high ground holds absolutely.** Evidence that a rival born on Earth, however clever, cannot dent a solar-system-scale AI (ℓ_∞ = 0 in fact, not just small) removes the main failure mode. This model then says the pact holds whenever the denial reserve is kept and temptation is moderate.
2. **Takeover is easy, or a failed early strike is survivable.** If an early strike is likely to succeed (p_s0 ≳ 0.9), or failing it is not fatal, the AI strikes at year 0 under every design (S20, S21). If real takeover odds are high, the whole approach fails before any fab is dismantled.
3. **Plugging is weak or easily bypassed.** If the denial reserve fires with probability below about 0.5, or covers well under 90% of capacity, the growth-stage condition (G) tips to a strike after closure. That would show the denial reserve cannot carry the weight the model puts on it.
4. **States value a rival AI highly.** Elicited or revealed values of B_R well above 5 years of welfare (for example, states treating an own frontier AI as existential) put the pact in the strike-now region whatever the sequencing.
5. **Seizure would not be lethal to humans.** If an AI takeover left humans largely unharmed (w_seized near 1), the racing mechanism weakens. Failures then become "wait, then strike" decades later instead of "strike now". Fewer people die in that world, but Earth still loses its independence.
6. **A model with private information or AI–AI bargaining finds peace where this one finds a strike.** That would show the result depends on my complete-information, single-AI set-up (section 8).

## 7. Questions for Cole (each changes the conclusion; both variants are run)

Updated after round 2. Questions are numbered EQ-Q1 to EQ-Q10 so they are not mistaken for spec IDs. EQ-Q1 and EQ-Q4 are partly answered; EQ-Q7 to EQ-Q10 are new.

1. **EQ-Q1: Can a rival AI ever threaten a much larger AI (ℓ_∞ = 0 or > 0)?** This is still the single biggest switch. Even ℓ_∞ = 0.01 flips S1 from cooperation to a strike at year 0. Your round-2 answer (100 times smaller is not a threat) covers the ratio part, and the model agrees with it (R1). What stays open is whether anything *irreducible* remains. If it does, the gravity-well blockade must let fewer than about 1 rival in a million escape.
2. **EQ-Q2: What would a seizure do to humans (w_seized)?** If seizure is lethal, humans race and the strike moves to year 0. If it is not, the AI waits about 40 years and then strikes. Your thesis is silent on this, and it decides which failure you get.
3. **EQ-Q3: Should the pact let the off-Earth AI remove covert fabs it detects (police)?** In the model it helps at the margin (the human-best design in world A uses it) but does not rescue high temptation. It also hands the AI a pact-sanctioned use of force on Earth.
4. **EQ-Q4: Is trade a consumption flow or reinvested growth (reinv)?** Your round-2 answer (trade is not a defence) agrees with the model. The denial reserve carries the growth phase, and preference carries the late stage (R3).
5. **EQ-Q5: How confident are you that a failed early strike would end the AI (kill_pre)?** Your plan keeps humans holding the chip supply during bootstrap, which is what makes a failed early strike fatal. If the AI's compute were already off-Earth or distributed, that protection goes away (S21: strike now).
6. **EQ-Q6: Is fab relocation to orbit (b) feasible on a 10-year timescale?** It is the human-best sequencing in the model, but it assumes orbital fabs supply chips under the pact and are plugged by the denial reserve if the pact breaks.

7. **EQ-Q7: Is a tiny but non-zero preference for humans realistic?** Under the pact, a preference of about 3e-10 of the AI's resources keeps Earth safe; without the pact it takes about 6% (R3). That gain only matters if preferences can be that small and still be there. If they are all-or-nothing, the pact's reduction buys nothing.
8. **EQ-Q8: What would a late AI want from Earth: its sunlight or its mass?** Sunlight makes the needed preference tiny (3e-10 to 8e-10). Mass could make it orders of magnitude larger. The model has only computed the sunlight case.
9. **EQ-Q9: How soon would the "aliens judge us" moment come, and would the AI discount it?** With a patient AI, the reputation argument needs only about a one-in-a-billion credence under the pact (R4). Discounted at 2% a year over 1,000 years, it needs a 13 to 40% credence.
10. **EQ-Q10: Who would run a covert fab?** In the model a fab is harmless unless someone runs a rival programme on it (R2b). With rogue actors, each fab adds about 6 points of rival risk over 300 years (R2a). Your answer turns on whether retained fabs would be state-held and deterred, or leak to rogue actors.

## 8. Not modelled (limits)

1. **Complete information.** Everyone knows everyone's payoffs; covertness enters only as a detection lag. Fearon's private-information route to war (the AI knows its own takeover odds; states know their own B_R) is not modelled. It would add bluffing and mistaken strikes.
2. **One AI.** There is no AI–AI bargaining and no multipolar AI landscape. A rival ends the game in reduced form (ℓ, κ_coll).
3. **Markov strategies with a stage-game selection rule.** Trigger strategies, reputation and long-memory punishments are not modelled. They could support more cooperation (folk-theorem logic), or less.
4. **Discrete fab grid and one-year periods.** The fab level F sits on a 6-point grid with interpolation. Relocation and rebuilding rates are approximated (the relocation curve in `eq_sequencing.png` is smoothed by this).
5. **The level of the AI's value carries about 6% interpolation error** (check 2). Decisions are checked for grid stability, not proven exact.
6. **No empirical basis** exists for B_R, ℓ_∞, w_seized, p_s0, D, the denial reliability q, the threat floor, or μ. These parameters decide the outcome. The model's contribution is to show which combinations matter, not what their values are.

---

*Figures:* `figures/eq_sequencing.png`, `figures/eq_paths.png`, `figures/eq_phase_temptation_floor.png`, `figures/eq_phase_wait.png`, `figures/eq_phase_harvest.png`, `figures/eq_tornado.png`.
