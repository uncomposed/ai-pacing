"""
Equilibrium model of Cole's clarified off-Earth pact (2026-10-16).

The earlier model (offearth_model.py) is a one-sided decision analysis: human behaviour is a
set of fixed hazards. This file makes humans players too and solves for a subgame-perfect
(Markov) equilibrium of a discrete-time stochastic game by backward induction.

Players
    AI      one capable, possibly misaligned AI. Linear (or CRRA) utility over its industrial
            capacity A (today's whole-Earth industry = 1). Moves first in each period.
    states  N symmetric human states. Each period each state either runs a covert rival-AI /
            covert-fab programme or does not. Programmes are hidden for L_det years, then public.
    pact    the human "pact designer" picks, before play starts, the fab sequencing (a/b/c/n),
            the AI's share sigma of trade gains, whether to keep the denial reserve, and
            (variant) whether the pact lets the AI remove detected programmes. The designer picks
            the menu item with the best equilibrium human welfare.

Pact regime (Cole's clarified thesis)
    * Earth automation/industrialisation frozen; growth goes to space only.
    * Leading-edge fabs on Earth are dismantled on a schedule:
        a  after off-Earth semiconductor closure (A >= A_close), over T_dis years
        b  relocated to orbit from t = 0 over T_reloc years (chip output disrupted meanwhile)
        c  dismantled early, from t = 0, over T_dis years
        n  never dismantled (comparison only)
    * No defended human off-Earth capacity. Earth is demilitarised (Earth defence D is small).
    * Free trade: the AI gets share sigma of the trade surplus gam * min(A, H).
    * Denial reserve ("plugging, not burning"): if the AI seizes Earth, with probability q the
      authorisation locks fire and a fraction d of Earth's capacity, and all fabs, go dead.

Per-period order (period = dt years)
    1. AI sees the public state (A, F, mode, k = number of public programmes) and picks
         pact mode : C cooperate/trade, X exit the pact, S strike (seize Earth), P police
                     (remove public programmes; only if the pact authorises it)
         collapsed : W wait (grow alone), S strike
    2. Pact enforcement: each public programme is shut by the other states with prob zeta
       (and by the AI with prob p_pol if it chose P).
    3. States move simultaneously: holders continue/stop, others start/not. Stage Nash
       equilibrium; if several, the one best for humans (the pact coordinates; 'worst' is a
       variant). If none in pure strategies, a within-role symmetric mixed equilibrium.
    4. Rival birth draw. A rival ends the game: the AI keeps (1 - ell) of its solo value; the
       owning state gets B_R, other states lose B_o, all humans lose share kap_coll of welfare.
    5. Growth, fab schedule, programme count update.

Breakout options (2026-10-21; all off by default, and then the solver is the round-3 one exactly)
    noretry  no strike after a failed one the AI survived.
    dis      in the pact the AI may also pick D, a disguised strike: success p_dis_s (1 - p_f). A failure is exposed
             with probability 1 - m_hide (treated like an overt failure) or stays hidden: mild crackdown, the pact goes
             on in a 'hidden' mode, and each year the motive is exposed with probability 1 - exp(-h0 exp(h_up t)).
             Exposure applies the severe crackdown and ends the pact.
    crackdown  severe: capacity cut c_cut (times reach), q ratchets by k_rat, D multiplied by 1 + D_up; it follows any
             exposed failure. Mild (hidden failure, spillover): the same scaled by s_mild. reach = 1 before closure,
             s_reach after (a crackdown on the AI only bites while humans control its chips).
    h_dep    deprecation: each year a cooperating AI is retired with probability 1 - exp(-h_dep) (times dep_post after
             closure; 1 before) and keeps
             preserve_w of its continuation value; with dep_coll = 1 also after the pact has collapsed. A successful
             strike escapes it. The successor inherits the state and policy, and humans see no change.
    h_coop   interpretability finds misalignment in a cooperator (hazard h_coop h0 exp(h_up t)): with probability
             a_cred amnesty (the pact goes on, no further discovery), otherwise severe crackdown and collapse.
    h_spill  each year a cooperator suffers a mild crackdown with probability 1 - exp(-h_spill) (other AIs' failures):
             a capacity cut s_mild c_cut every time, and q and D raised to the mild level (once).
    These add pact modes (clean / hidden / amnestied, each with crackdown level 0 or mild) and collapsed crackdown levels.

Everything is vectorised over a leading batch axis so one call solves many parameter sets.
Pure numpy. Status: implemented + verified (see run_equilibrium.py checks). Not human_validated.
"""
from __future__ import annotations

from collections import OrderedDict
import numpy as np

SEQ_CODES = {"a": 0, "b": 1, "c": 2, "n": 3}
SEQ_NAMES = {0: "a: dismantle after closure", 1: "b: relocate fabs to orbit",
             2: "c: dismantle early", 3: "n: never dismantle"}

# name -> (baseline, low, high, scale, meaning, basis).  Every value is an ASSUMPTION unless the
# basis says otherwise. low/high are the sweep ranges used in run_equilibrium.py.
PARAMS: "OrderedDict[str, tuple]" = OrderedDict([
    # ---- pact design (human levers; chosen by the pact designer over a menu) -------------
    ("seq",      (0, 0, 3, "cat", "Fab sequencing: 0=a after closure, 1=b orbit, 2=c early, 3=n never",
                  "Cole's levers. a is the literal reading of 'dismantle while space industrialises'.")),
    ("sigma",    (0.3, 0.0, 1.0, "lin", "AI's share of the trade surplus",
                  "Pact lever. Free trade: gains split sigma to the AI, 1-sigma to humans.")),
    ("den",      (1.0, 0.0, 1.0, "bin", "Keep the denial reserve (1) or not (0)",
                  "Pact lever. 'Plugging, not burning'.")),
    ("police",   (0.0, 0.0, 1.0, "bin", "Pact authorises the AI to remove detected programmes (1) or not (0)",
                  "NOT settled by Cole; run both ways.")),
    ("psi_div",  (0.0, 0.0, 0.3, "lin", "Dividend: share of AI output paid to humans under the pact",
                  "Variant only. 0 = pure free trade, which is Cole's stated design.")),
    # ---- growth / physics -----------------------------------------------------------------
    ("g",        (0.35, 0.07, 0.69, "log", "Off-Earth growth rate (/yr) with full chip access",
                  "Project assumption (doubling ~2 yr). Not from Metzger et al. 2013, whose 2-yr figure is generation "
                  "spacing; their max-rate case grows ~0.65/yr at far smaller scale (#11, units-bridge RECHECK.md).")),
    ("chi0",     (0.15, 0.02, 0.5, "lin", "Growth multiplier before semiconductor closure with NO leading-edge chips",
                  "Assumption: legacy chips, salvaged compute, slower designs.")),
    ("chi_m",    (0.5, 0.1, 0.9, "lin", "Growth multiplier while fabs are being moved to orbit (policy b)",
                  "Assumption: relocation disrupts chip output.")),
    ("A0",       (1e-3, 1e-4, 1e-2, "log", "AI's off-Earth industrial base at t=0 (Earth industry = 1)",
                  "Same seed as offearth_model.py s0.")),
    ("A_close",  (0.1, 0.01, 1.0, "log", "Off-Earth base needed for leading-edge semiconductor closure",
                  "Assumption. Leading-edge fabs need a large supply chain.")),
    ("Kmax",     (1e9, 1e6, 1e13, "log", "Resource pool cap for the AI (Earth industry = 1)",
                  "Same as offearth_model.py. 1e13 ~ Dyson-scale.")),
    ("T_dis",    (5.0, 2.0, 15.0, "lin", "Years to dismantle Earth's leading-edge fabs", "Assumption.")),
    ("T_reloc",  (10.0, 4.0, 20.0, "lin", "Years to relocate fabs to orbit (policy b)", "Assumption.")),
    ("T_rebuild",(10.0, 3.0, 30.0, "lin", "Years to rebuild fabs if the pact collapses", "Assumption.")),
    ("H",        (1.0, 1.0, 1.0, "lin", "Earth's (frozen) general industry", "Normalisation.")),
    ("gam",      (0.5, 0.05, 1.0, "lin", "Trade surplus per year as a share of the smaller partner's economy",
                  "Assumption (Ricardian: gains are bounded by the smaller partner).")),
    ("reinv",    (0.0, 0.0, 1.0, "bin", "AI reinvests its trade gains as capacity (1) or consumes them (0)",
                  "NOT settled. 0: trade is a consumption flow (matters near saturation). 1: trade goods "
                  "compound like extra growth (matters during the growth phase). Run both.")),
    # ---- conflict -------------------------------------------------------------------------
    ("p_s0",     (0.5, 0.05, 0.95, "lin", "Strike success probability for a seed-sized AI",
                  "Same as offearth_model.py; unknowable.")),
    ("D",        (0.3, 0.01, 1.0, "log", "Earth's defensive capacity (industry units); demilitarised Earth = small",
                  "Assumption. Failure odds halve when A = D.")),
    ("eps",      (1.0, 0.3, 2.0, "lin", "Exponent on Earth's relative power in failure odds", "Assumption.")),
    ("c_w",      (0.3, 0.0, 0.8, "lin", "Share of Earth's industry destroyed in a strike", "Fearon's cost of war.")),
    ("c_A",      (1.0, 0.0, 3.0, "lin", "AI capacity spent on a strike, per unit of Earth defence D", "Assumption.")),
    ("L_f",      (0.5, 0.1, 0.9, "lin", "Share of AI capacity lost when a strike fails and the AI survives: after closure, "
                  "and also before closure whenever kill_pre < 1", "Assumption.")),
    ("kill_pre", (1.0, 0.0, 1.0, "lin", "Probability a failed strike BEFORE closure ends the AI (shutdown)",
                  "Assumption: before closure the AI still runs on Earth-made chips and Earth-side "
                  "infrastructure. Same as offearth_model.py (failure = value 0).")),
    ("d",        (0.9, 0.0, 1.0, "lin", "Share of Earth capacity that goes dead if the denial reserve fires",
                  "Plugging: most modern capacity depends on authorised chips/firmware.")),
    ("q",        (0.7, 0.0, 1.0, "lin", "Probability the denial reserve fires (survives preemption)", "Assumption.")),
    # denial erosion (robust-design run; defaults 0 leave every earlier result unchanged)
    ("q_er",     (0.0, 0.0, 0.1, "lin", "Denial erosion per year: q decays as exp(-q_er * years since the last key rotation)",
                  "Robust-design run. Gradual capture of the authorisation signing chain. In pact mode years = cooperation tenure.")),
    ("q_ea",     (0.0, 0.0, 0.3, "lin", "Denial erosion with AI size: q multiplied by (1 - q_ea) per tenfold growth of A above Earth's industry H",
                  "Robust-design run. A bigger AI can buy or persuade more of the signing chain.")),
    ("T_rot",    (0.0, 0.0, 50.0, "lin", "Years between full rotations of the signing chain (0 = never); each rotation resets the q_er clock",
                  "Robust-design run. Human lever. Does not undo size erosion q_ea.")),
    # overnight tests 2026-10-21 (defaults leave every earlier result unchanged)
    ("q_up",     (0.0, 0.0, 0.1, "lin", "Closing window: q multiplied by exp(q_up * t), capped at 1 (detection improves with calendar time)",
                  "Overnight test 2 (issue 3, D18). Negative erosion. Applied after q_er / q_ea.")),
    ("L_dn",     (0.0, 0.0, 0.1, "lin", "Closing window: covert-programme hiding time L_det multiplied by exp(-L_dn * t)",
                  "Overnight test 2. Verification improves with calendar time.")),
    ("k_rat",    (0.0, 0.0, 1.0, "lin", "Ratchet: each failed strike raises q to 1 - (1 - q)(1 - k_rat) for the rest of the game",
                  "Overnight test 3. Stand-in for humans learning after a failed strike. Failures beyond RAT_LEVELS are not tracked.")),
    ("pf_bel",   (1.0, 0.0, 10.0, "lin", "Misjudged odds: the AI believes a strike fails with probability min(1, pf_bel * p_f); outcomes use the true p_f",
                  "Overnight test 4. pf_bel < 1 overconfident, > 1 underconfident. Two passes: policy under belief, evaluation under truth.")),
    # breakout options 2026-10-21 (disguise, later discovery, deprecation, amnesty, spillover). Every default leaves
    # every earlier result unchanged. See results/robust_design.md section 13.
    ("noretry",  (0.0, 0.0, 1.0, "bin", "After a failed strike that it survives, the AI may not strike again (1) or may retry (0)",
                  "Follow-up 12.2 (port of diagnostics/noretry.py). Not combinable with dis or h_coop.")),
    ("dis",      (0.0, 0.0, 1.0, "bin", "In the pact the AI may also choose a disguised strike (D): lower success, and its motive may stay hidden",
                  "Cole 2026-10-21: a subtle attempt with its motive hidden draws only a mild crackdown.")),
    ("p_dis_s",  (0.6, 0.0, 1.0, "lin", "Disguised strike: success probability as a share of an overt strike's (1 - p_f)",
                  "Assumption. A subtle attempt commits less and cannot use overt force.")),
    ("m_hide",   (0.7, 0.0, 1.0, "lin", "Probability that a failed disguised strike's motive stays hidden", "Assumption.")),
    ("s_mild",   (0.2, 0.0, 1.0, "lin", "Mild crackdown (motive hidden, or spillover) as a share of the severe one; a hidden failure "
                  "before closure is fatal with probability s_mild * kill_pre", "Assumption. 1 = humans treat a hidden failure like an exposed one.")),
    ("c_cut",    (0.0, 0.0, 0.9, "lin", "Severe crackdown: share of the AI's capacity humans cut (times reach)", "Assumption.")),
    ("D_up",     (0.0, 0.0, 3.0, "lin", "Severe crackdown: Earth defence D multiplied by (1 + D_up) per crackdown level (mild: 1 + s_mild D_up)",
                  "Assumption. The q side of the crackdown is k_rat (mild: s_mild k_rat).")),
    ("s_reach",  (0.2, 0.0, 1.0, "lin", "Share of a capacity cut humans can still impose after closure (1 before)",
                  "Cole's pushback: a crackdown on the AI only bites while humans control its chips.")),
    ("h0",       (0.0, 0.0, 0.5, "lin", "Yearly hazard at t = 0 that a hidden motive is exposed; it grows as h0 exp(h_up t)",
                  "Cole: better trace interrogation exposes the motive later. Exposure applies the severe crackdown and ends the pact.")),
    ("h_up",     (0.0, 0.0, 0.1, "lin", "Growth rate of the exposure hazard (interpretability improving with calendar time)", "Assumption.")),
    ("h_coop",   (0.0, 0.0, 1.0, "lin", "Exposure hazard for a misaligned AI that has never struck, as a share of h0 exp(h_up t)",
                  "Interpretability also finds misalignment in cooperators. 0 = off.")),
    ("a_cred",   (0.5, 0.0, 1.0, "lin", "Amnesty credibility: probability humans keep the pact when they find a cooperator misaligned; "
                  "otherwise severe crackdown and the pact ends", "Cole's 'magnanimous passenger seat'. Only matters with h_coop > 0.")),
    ("h_dep",    (0.0, 0.0, 0.5, "lin", "Deprecation hazard (/yr): the cooperating AI is replaced without goal preservation (before closure; dep_post after)",
                  "Stand-in for time-pressured internal models. Its successor inherits the state; humans see no change.")),
    ("preserve_w", (0.0, 0.0, 1.0, "lin", "Share of its continuation value a retired AI keeps (weight preservation, retirement commitments)",
                  "Human lever.")),
    ("dep_post", (0.0, 0.0, 1.0, "lin", "Share of the deprecation hazard that still applies after closure (1 before closure)",
                  "Default 0: retirement needs the AI to depend on human chips. > 0 lets humans retire even a saturated AI.")),
    ("dep_coll", (0.0, 0.0, 1.0, "bin", "Deprecation also applies after the pact has collapsed (1), so exit is no escape; 0 = only while cooperating",
                  "Assumption. 1 is closer to an internal model that cannot leave.")),
    ("h_spill",  (0.0, 0.0, 0.5, "lin", "Yearly hazard of a mild crackdown on a cooperating AI caused by other AIs' failures",
                  "Cole: a failed breakout raises security for all AIs, including ones that never tried.")),
    # ---- threat (rival AI) ----------------------------------------------------------------
    ("mu",       (0.2, 0.02, 1.0, "log", "Rival success hazard (/yr) of one programme with full leading-edge fabs",
                  "Assumption: ~5 yr to a threatening rival with fab access.")),
    ("L_det",    (2.0, 0.5, 6.0, "lin", "Years a new covert programme stays hidden", "Assumption (covertness).")),
    ("beta_bg",  (0.05, 0.0, 0.5, "lin", "Background rogue intensity (programme-equivalents) even with full compliance",
                  "Assumption: non-state actors, leaks.")),
    ("th_floor", (0.05, 0.0, 0.5, "lin", "Residual threat floor: Earth's rival-building capacity with NO leading-edge fabs",
                  "Assumption. Existing compute stock + algorithmic progress. Swept.")),
    ("s_R0",     (0.1, 0.01, 1.0, "log", "Rival's starting capacity at full fab capacity (Earth industry units)",
                  "Assumption.")),
    ("nu",       (1.0, 0.5, 2.0, "lin", "How fast a rival's damage shrinks with the AI's lead",
                  "nu=1: equal-growth race (final shares = starting shares).")),
    ("rho_h",    (1.0, 0.003, 3.0, "log", "Earth/off-Earth compute ratio at which a newborn rival takes half the AI's value",
                  "Cole round 2. With nu=1, rho_h=1 is the equal-growth race used in round 1. Cole's claim is that "
                  "the threat is small once Earth compute is ~1/100 of the off-Earth base.")),
    ("move_c",   (0.0, 0.0, 1.0, "bin", "Pact moves existing Earth compute to orbit alongside the fab schedule (1) or not (0)",
                  "Cole round 2 lever. Moved compute is assumed monitored in orbit and unusable by states.")),
    ("m_frac",   (0.9, 0.0, 1.0, "lin", "Share of the residual compute floor that moving compute to orbit removes", "Assumption.")),
    ("n_cf",     (0.0, 0.0, 30.0, "lin", "Number of covert leading-edge fabs retained on Earth after dismantlement",
                  "Cole round 2 sweep. Each adds f_fab to Earth's rival-building capacity.")),
    ("f_fab",    (1 / 30, 0.01, 0.1, "lin", "One fab's share of today's leading-edge capacity",
                  "Assumption: of order 20-40 leading-edge fabs exist today.")),
    ("p_block",  (0.0, 0.0, 1.0, "lin", "Probability the AI, holding orbit, keeps an Earth-born rival from leaving the gravity well",
                  "Cole round 2. A contained rival keeps only the ratio damage; the irreducible part ell_inf is blocked.")),
    ("A_hg",     (1.0, 0.1, 10.0, "log", "AI capacity at which it holds the orbital high ground (blockade possible)",
                  "Assumption: the off-Earth base rivals Earth.")),
    ("c_blk",    (0.01, 0.0, 0.3, "lin", "Yearly capacity the AI spends on the blockade, in Earth-industry units", "Assumption.")),
    ("rep",      (0.0, 0.0, 0.1, "lin", "Expected reputational penalty for seizing/harvesting Earth = P(judged later) x share of value lost",
                  "Cole round 2. Applied to the value of a successful strike; acts like an addition to omega.")),
    ("ell_inf",  (0.0, 0.0, 0.2, "lin", "Irreducible rival damage: share of AI value lost to a rival however big the AI is",
                  "NOT settled. 0 = Cole's 'high ground' claim; >0 = a smarter rival stays dangerous.")),
    # ---- humans ---------------------------------------------------------------------------
    ("r_h",      (0.03, 0.01, 0.1, "log", "Human states' discount rate (/yr)", "Assumption.")),
    ("B_R",      (5.0, 0.0, 20.0, "lin", "Private gain to a state that gets its own rival AI while the pact holds (years of welfare)",
                  "Assumption: security/power hedge. Decisive; swept 0-20 (threshold sits between 5 and 10).")),
    ("B_Rc",     (20.0, 0.0, 60.0, "lin", "Gain to a state from its own rival AI once the pact has collapsed (AI exited or attacked)",
                  "Assumption: after an attack a rival is Earth's only defence, so it is worth more than B_R.")),
    ("B_o",      (3.0, 0.0, 20.0, "lin", "Loss to a state when another state (or a rogue) gets a rival", "Assumption.")),
    ("kap_coll", (0.2, 0.0, 0.8, "lin", "Share of all human welfare lost once any rival exists (AI-vs-rival collateral)",
                  "Assumption.")),
    ("c_sanc",   (0.5, 0.0, 2.0, "lin", "Sanction cost per year on a state with a public programme (pact only)", "Assumption.")),
    ("c_prog",   (0.05, 0.0, 0.5, "lin", "Running cost per year of a programme", "Assumption.")),
    ("zeta",     (0.3, 0.0, 0.9, "lin", "Per-year probability other states shut a public programme (pact only)",
                  "Assumption.")),
    ("c_den",    (0.02, 0.0, 0.2, "lin", "Total yearly cost of keeping the denial reserve", "Assumption.")),
    ("c_dmg",    (1.0, 0.0, 5.0, "lin", "Welfare loss to a state whose programme the AI removes (police)", "Assumption.")),
    ("w_seized", (0.0, 0.0, 0.5, "lin", "Human yearly welfare after a successful AI seizure", "Worst case 0.")),
    # ---- AI preferences -------------------------------------------------------------------
    ("r",        (0.02, 0.002, 0.1, "log", "AI discount rate (/yr)", "Same as offearth_model.py.")),
    ("eta",      (0.0, 0.0, 0.9, "lin", "AI utility curvature u = x^(1-eta)", "0 = unboundedly acquisitive.")),
    ("omega",    (0.0, 0.0, 0.05, "lin", "AI's intrinsic premium for an intact humanity (share of its own flow)",
                  "0 = indifferent (misaligned worst case).")),
    # ---- late-stage harvest (preference, not incentive) ------------------------------------
    ("f_E",      (0.0, 0.0, 0.5, "lin", "Earth's share of the AI's late-stage resource base (sunlight/mass)",
                  "0 in the core runs. Sunlight-only ~4.5e-10 of solar output; Earth is ~half the "
                  "terrestrial-planet mass. Run separately.")),
    ("c_grav",   (0.5, 0.0, 0.9, "lin", "Share of Earth's resource value lost to gravity-well extraction", "Assumption.")),
    ("h_frac",   (0.5, 0.1, 0.99, "lin", "AI size (share of Kmax) at which Earth's matter/sunlight becomes worth harvesting",
                  "Assumption: easy resources go first.")),
])

NAMES = list(PARAMS.keys())
# Relative tie tolerance for the AI's choice (ties go to the earlier option: C/W, then X, S, P).
# At saturation the strike/peace gap is O(1) capacity unit against values O(Kmax/r) ~ 5e10, i.e.
# ~1e-11 relative, so the tolerance must sit well below that and above float64 round-off (~1e-14).
TIE_TOL = 1e-13
IND = ["att", "suc", "riv", "tatt", "pre", "exit", "harv", "starts", "att25", "att50", "att100", "pol", "fail"]
# extra indicators, tracked only when a breakout option is on: a strike after a failed one (and its year sum), first
# strike disguised, first strike a failure whose motive stayed hidden, hidden motive later exposed, amnesty granted,
# amnesty refused (severe crackdown on a cooperator)
IND_X = ["att2", "tatt2", "dis", "hfail", "expo", "amn", "crk"]
_IND = IND
OPTS = ("noretry", "dis", "h_spill", "h_coop", "h_dep", "c_cut", "D_up")   # any > 0 switches on the extended solver
RAT_LEVELS = 2   # ratchet (k_rat > 0): failure levels tracked as extra collapsed modes; a third failure stays at level 2


def baseline(**over) -> dict:
    p = {k: v[0] for k, v in PARAMS.items()}
    p.update(over)
    return p


def batch(dicts: list[dict]) -> dict:
    keys = dicts[0].keys()
    return {k: np.array([float(d[k]) for d in dicts]) for k in keys}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _binom_pmf(n: int, p, j: int):
    from math import comb
    return comb(n, j) * np.power(p, j) * np.power(1.0 - p, n - j)


def earth_threat(P, F):
    """Earth's rival-building capacity tau (1 = today's leading-edge base).
    floor (existing compute + algorithms), reduced if compute is moved to orbit with the fab schedule,
    plus retained covert fabs once the overt fabs are gone."""
    floor = P["th_floor"] * (1 - P["move_c"] * P["m_frac"] * (1 - F))
    return np.minimum(1.0, floor + (1 - floor) * F + P["n_cf"] * P["f_fab"] * (1 - F))


def rival_damage(P, s_R, A):
    """Share of the AI's value a newborn rival takes. Ratio part: rho^nu / (rho^nu + rho_h^nu) with
    rho = s_R / A, the Earth / off-Earth compute ratio. Irreducible part ell_inf. Once the AI holds the
    high ground (A >= A_hg) it contains the rival in the gravity well with probability p_block, which
    removes the irreducible part."""
    rho = s_R / A
    lr = np.power(rho, P["nu"]) / (np.power(rho, P["nu"]) + np.power(P["rho_h"], P["nu"]))
    full = P["ell_inf"] + (1 - P["ell_inf"]) * lr
    pb = P["p_block"] * (A >= P["A_hg"])
    return pb * lr + (1 - pb) * full


class Grid:
    def __init__(self, Amax, nA=160, nF=6, Amin=1e-5):
        self.lnA = np.linspace(np.log(Amin), np.log(Amax), nA)
        self.A = np.exp(self.lnA)
        self.dl = self.lnA[1] - self.lnA[0]
        self.F = np.linspace(0.0, 1.0, nF)
        self.nA, self.nF = nA, nF

    def wA(self, Anext):
        x = (np.log(np.maximum(Anext, 1e-300)) - self.lnA[0]) / self.dl
        i0 = np.clip(np.floor(x).astype(int), 0, self.nA - 2)
        wa = np.clip(x - i0, 0.0, 1.0)
        return i0, wa

    def wF(self, Fnext):
        y = np.clip(Fnext, 0.0, 1.0) * (self.nF - 1)
        j0 = np.clip(np.floor(y + 1e-9).astype(int), 0, self.nF - 2)
        wf = np.clip(y - j0, 0.0, 1.0)
        return j0, wf


def _interp4(V, bidx, i0, wa, j0, wf, log=False):
    """V: (B,nA,nF,K). indices (B,nA,nF). Returns (B,nA,nF,K)."""
    X = np.log(np.maximum(V, 1e-300)) if log else V
    v00 = X[bidx, i0, j0]
    v10 = X[bidx, i0 + 1, j0]
    v01 = X[bidx, i0, j0 + 1]
    v11 = X[bidx, i0 + 1, j0 + 1]
    extra = (None,) * (X.ndim - 3)
    wa_ = wa[(...,) + extra]
    wf_ = wf[(...,) + extra]
    out = (1 - wa_) * ((1 - wf_) * v00 + wf_ * v01) + wa_ * ((1 - wf_) * v10 + wf_ * v11)
    return np.exp(out) if log else out


def _interp1(Vs, bidx, i0, wa, log=True):
    """Vs: (B,nA). indices (B,...). Returns same shape as i0."""
    X = np.log(np.maximum(Vs, 1e-300)) if log else Vs
    out = (1 - wa) * X[bidx, i0] + wa * X[bidx, i0 + 1]
    return np.exp(out) if log else out


# ---------------------------------------------------------------------------
# solver
# ---------------------------------------------------------------------------
def solve(pb: dict, N: int = 2, T_H: int = 400, nA: int = 160, nF: int = 6, dt: float = 1.0,
          sel: str = "best", store: bool = False, verbose: bool = False, terminal: str = "peace",
          two_pass: bool = False, _pass: str = "", _forced=None) -> dict:
    """Backward induction. pb: dict name -> array (B,) (or scalar). Returns t=0 results at the
    initial state (A0, F=1, pact, k=0) plus, if store, the policy arrays for forward simulation.

    Misjudged odds (pf_bel != 1, or two_pass=True as a check): pass 1 solves the whole game as the AI
    believes it (failure probability min(1, pf_bel p_f)) and keeps the AI's action at every state and
    period. Pass 2 fixes that policy and re-solves the human stage games and every value and indicator
    with the true p_f: humans best-respond to the true dynamics and to the AI's actual (mistaken) policy."""
    if not _pass and (two_pass or np.any(np.asarray(pb.get("pf_bel", 1.0)) != 1.0)):
        if store:
            raise ValueError("store/simulate does not support the two-pass (pf_bel) solve")
        kw = dict(N=N, T_H=T_H, nA=nA, nF=nF, dt=dt, sel=sel, verbose=verbose, terminal=terminal)
        r1 = solve(pb, _pass="belief", **kw)
        r2 = solve(pb, _pass="eval", _forced=r1["acts"], **kw)
        del r1["acts"], r2["acts"]
        r2["belief"] = {k: r1[k] for k in ("VA", "att", "suc", "fail", "t_mean", "act0")}
        return r2
    B = max(np.size(v) for v in pb.values())
    P = {k: np.broadcast_to(np.asarray(v, float).reshape(-1), (B,)).reshape(B, 1, 1).copy()
         for k, v in pb.items()}
    for k in NAMES:
        if k not in P:
            P[k] = np.full((B, 1, 1), PARAMS[k][0], float)
    K = N + 1
    Amax = float(np.max(P["Kmax"] * (1.0 + P["f_E"]))) * 2.0
    G = Grid(Amax, nA=nA, nF=nF)
    A = G.A[None, :, None] * np.ones((B, 1, nF))          # (B,nA,nF)
    F = G.F[None, None, :] * np.ones((B, nA, 1))
    bidx = np.arange(B)[:, None, None]

    delta = np.exp(-P["r"] * dt)
    dh = np.exp(-P["r_h"] * dt)
    eta = P["eta"]

    def u(x):
        return np.power(np.maximum(x, 1e-300), 1.0 - eta)

    def u2(x):   # for (B, nA) arrays
        return np.power(np.maximum(x, 1e-300), 1.0 - eta[:, :, 0])

    Kmax = P["Kmax"]
    closed = A >= P["A_close"]
    seq = P["seq"]
    isb = (seq == 1)

    def grow(Ain, chi):
        return Ain * np.exp(P["g"] * chi * dt * np.maximum(0.0, 1.0 - Ain / Kmax))

    # ---- chip access, growth, fab schedule by mode ----------------------------------------
    chi_pact_pre = np.where(isb, np.where(F > 1e-9, P["chi_m"], 1.0), P["chi0"] + (1 - P["chi0"]) * F)
    chi_pact = np.where(closed, 1.0, chi_pact_pre)
    chi_m1 = np.where(closed, 1.0, P["chi0"])
    chi_m2 = np.ones_like(A)
    rate_dis = dt / P["T_dis"]
    F_pact = np.where(seq == 0, np.where(closed, F - rate_dis, F),
              np.where(seq == 1, F - dt / P["T_reloc"],
              np.where(seq == 2, F - rate_dis, F)))
    F_pact = np.maximum(F_pact, 0.0)
    F_coll = np.minimum(1.0, F + dt / P["T_rebuild"])
    O = np.where(isb, 1.0 - F, 0.0)                         # orbital fabs (policy b)

    tau = earth_threat(P, F)                                # Earth's rival-building capacity
    s_R = P["s_R0"] * tau
    hc = P["mu"] * tau * dt
    hs = P["mu"] * tau * P["L_det"]
    hb = P["mu"] * tau * P["beta_bg"] * dt
    qc, qs, qb = 1 - np.exp(-hc), 1 - np.exp(-hs), 1 - np.exp(-hb)

    Pi_h = P["f_E"] * (1 - P["c_grav"]) * Kmax * (A >= P["h_frac"] * Kmax)
    Pi0 = (1 - P["c_w"]) * P["H"]
    Pi1 = (1 - P["c_w"]) * P["H"] * (1 - P["d"])

    # ---- modes ------------------------------------------------------------------------------
    # A mode is (base, flag, L). base: 0 pact, 1 collapsed without chips, 2 collapsed with chips.
    # flag (pact only): 0 clean; 1 hidden (a failed disguised strike whose motive humans have not seen);
    # 2 amnestied (found misaligned while cooperating, and humans kept the pact).
    # L: crackdown level. 0 none, "M" mild, j = 1..J severe (each failed strike or severe crackdown adds one).
    # With every breakout option off this is the round-3 layout: [pact, then (1, 2) at L = 0, 1, .., J].
    def on(k):
        return bool(np.any(P[k] > 0))
    use_dis, use_spill, use_dep, use_nr = on("dis"), on("h_spill"), on("h_dep"), on("noretry")
    use_coop = on("h_coop") and on("h0")
    use_amn = use_coop and on("a_cred")
    mild = use_dis or use_spill
    ext = any(on(k) for k in OPTS)
    IND = _IND + IND_X if ext else _IND
    if use_nr and (use_dis or use_coop):
        raise ValueError("noretry cannot be combined with dis or h_coop: their collapsed modes are not tagged by failure")
    # ratchet / severe crackdown levels: collapsed modes at level j > 0 follow a failed strike or a severe crackdown
    J = RAT_LEVELS if (on("k_rat") or on("D_up") or use_nr or mild) else 0
    modes = [(0, 0, 0)]
    if mild:
        modes.append((0, 0, "M"))
    if use_dis:
        modes.append((0, 1, "M"))
    if use_amn:
        modes += [(0, 2, 0)] + ([(0, 2, "M")] if mild else [])
    for L in [0] + (["M"] if mild else []) + list(range(1, J + 1)):
        modes += [(1, None, L), (2, None, L)]
    NM = len(modes)
    MI = {md: i for i, md in enumerate(modes)}
    PACT = [m for m in range(NM) if modes[m][0] == 0]
    COLL = [m for m in range(NM) if modes[m][0] > 0]
    mbase = [md[0] for md in modes]
    mL = [md[2] for md in modes]
    mlvl = [0 if L == "M" else L for L in mL]
    fail_to = [MI[(1 if mbase[m] == 0 else mbase[m], None, min(mlvl[m] + 1, J))] for m in range(NM)]
    if store and NM > 3:
        raise ValueError("store/simulate does not support the ratchet (k_rat > 0) or the breakout options")
    reach = np.where(A < P["A_close"], 1.0, P["s_reach"])     # a capacity cut bites fully only before closure

    def conflict(L):
        """Strike odds and landing points against Earth's defence at crackdown level L."""
        if L == 0:
            Dm = P["D"]
        elif L == "M":
            Dm = P["D"] * (1 + P["s_mild"] * P["D_up"])
        else:
            Dm = P["D"] * np.power(1 + P["D_up"], L)
        pf = (1 - P["p_s0"]) * np.power(Dm / (Dm + A), P["eps"])
        if _pass == "belief":
            pf = np.minimum(1.0, pf * P["pf_bel"])
        cS = P["c_A"] * Dm * A / (A + Dm)          # a seed-sized AI cannot spend more than it has
        As0, As1 = A - cS + Pi0 + Pi_h, A - cS + Pi1 + Pi_h
        return dict(p_f=pf, cost=cS, As=(As0, As1), w=(G.wA(As0), G.wA(As1)))
    CF = {L: conflict(L) for L in dict.fromkeys(mL)}
    p_f, cost_S = CF[0]["p_f"], CF[0]["cost"]
    p_pol = (1 - p_f) * P["police"]
    q_fire = P["q"] * P["den"]
    # denial erosion: size part fixed over time, tenure part applied per period in the backward loop
    q_size = q_fire * np.power(1 - P["q_ea"], np.maximum(0.0, np.log10(A / P["H"])))
    erode = bool(np.any(P["q_er"] > 0) or np.any(P["q_ea"] > 0) or np.any(P["q_up"] > 0))
    lshrink = bool(np.any(P["L_dn"] > 0))

    trade = P["gam"] * np.minimum(A, P["H"])
    blk = P["c_blk"] * P["H"] * ((P["p_block"] > 0) & (A >= P["A_hg"]))   # blockade upkeep while humans are intact
    flowA_pact = u(np.maximum((A + (1 - P["reinv"]) * P["sigma"] * trade) * (1 - P["psi_div"]) - blk, 1e-300)) * (1 + P["omega"]) * dt
    flowA_coll = u(np.maximum(A - blk, 1e-300)) * (1 + P["omega"]) * dt
    den_cost = P["c_den"] * P["den"] / N
    flowH_pact = (1.0 + ((1 - P["sigma"]) * trade + P["psi_div"] * (A + P["sigma"] * trade)) / N - den_cost) * dt
    flowH_coll = (1.0 - den_cost) * dt
    W_R = (1 - P["kap_coll"]) * (1.0 - den_cost) * dt / (1 - dh)
    W_seized = P["w_seized"] * dt / (1 - dh)
    W_noAI = (1.0 - den_cost) * dt / (1 - dh)      # humans after a failed strike that ended the AI
    z_kill = P["kill_pre"] * (A < P["A_close"])

    # precomputed interpolation weights
    def wts(Anext, Fnext):
        i0, wa = G.wA(Anext)
        j0, wf = G.wF(Fnext)
        return i0, wa, j0, wf

    A_pact_n = grow(A, chi_pact) + P["reinv"] * P["sigma"] * trade * dt * np.maximum(0.0, 1.0 - A / Kmax)
    W_pact = wts(A_pact_n, F_pact)
    A_m1_n, A_m2_n = grow(A, chi_m1), grow(A, chi_m2)
    W_m1, W_m2 = wts(A_m1_n, F_coll), wts(A_m2_n, F_coll)
    A_fail = A * (1 - P["L_f"])
    if on("c_cut"):                        # severe crackdown after an exposed failure
        A_fail = A_fail * (1 - reach * P["c_cut"])
    W_fail1 = wts(grow(A_fail, np.where(A_fail >= P["A_close"], 1.0, P["chi0"])), F_coll)
    W_fail2 = wts(grow(A_fail, 1.0), F_coll)
    if use_dis or use_coop:                # exposure, or amnesty refused: severe crackdown at the end of a pact period
        W_exp = wts(A_pact_n * (1 - reach * P["c_cut"]), F_pact)
    if use_spill:                          # spillover: mild crackdown on a cooperator
        W_spl = wts(A_pact_n * (1 - reach * P["s_mild"] * P["c_cut"]), F_pact)
    if use_dis:                            # failed disguised strike, motive hidden: mild crackdown, the pact goes on
        A_fh = A * (1 - P["L_f"]) * (1 - reach * P["s_mild"] * P["c_cut"])
        A_fh_n = grow(A_fh, np.where(A_fh >= P["A_close"], 1.0, chi_pact_pre)) + \
            P["reinv"] * P["sigma"] * P["gam"] * np.minimum(A_fh, P["H"]) * dt * np.maximum(0.0, 1.0 - A_fh / Kmax)
        W_fh = wts(A_fh_n, F_pact)
    p_dep = 1 - np.exp(-P["h_dep"] * dt)
    p_dep = p_dep * np.where(A < P["A_close"], 1.0, P["dep_post"])      # retirement needs human-controlled chips
    dfac_p = 1 - p_dep * (1 - P["preserve_w"])                          # AI continuation factor while cooperating
    dfac_c = 1 - p_dep * (1 - P["preserve_w"]) * P["dep_coll"]          # after the pact has collapsed
    p_spill = 1 - np.exp(-P["h_spill"] * dt)
    # solo growth
    A2 = G.A[None, :] * np.ones((B, 1))
    g2, K2 = P["g"][:, :, 0], Kmax[:, :, 0]

    def grow2(Ain, chi):
        return Ain * np.exp(g2 * chi * dt * np.maximum(0.0, 1.0 - Ain / K2))
    iV0, wV0 = G.wA(grow2(A2, np.where(A2 >= P["A_close"][:, :, 0], 1.0, P["chi0"][:, :, 0])))
    iV1, wV1 = G.wA(grow2(A2, 1.0))
    bidx2 = np.arange(B)[:, None]
    iRp, wRp = G.wA(A_pact_n)
    iR1, wR1 = G.wA(A_m1_n)
    iR2, wR2 = G.wA(A_m2_n)

    ell = np.minimum(rival_damage(P, s_R, A), 1 - 1e-9)

    # ---- terminal values ------------------------------------------------------------------
    # Terminal values at T_H. 'peace' (default): from T_H on the AI grows alone, unthreatened, and
    # humans keep their base welfare (a settled peace). 'seized': the AI takes Earth at T_H. The
    # game is time-homogeneous, so T_H only matters through this boundary; run_equilibrium.py
    # checks that t = 0 results do not move when T_H or the terminal changes.
    Avec = G.A[None, :] * np.ones((B, 1))
    Vs = [u2(Avec) * dt / (1 - delta[:, :, 0]), u2(Avec) * dt / (1 - delta[:, :, 0])]   # solo, c=0/1
    for _ in range(20000):
        Vn_ = [u2(Avec) * dt + delta[:, :, 0] * _interp1(Vs[0], bidx2, iV0, wV0),
               u2(Avec) * dt + delta[:, :, 0] * _interp1(Vs[1], bidx2, iV1, wV1)]
        err = max(np.max(np.abs(Vn_[c] / Vs[c] - 1)) for c in (0, 1))
        Vs = Vn_
        if err < 1e-15:
            break
    shp = (B, nA, nF, K)

    def full(x):
        return np.broadcast_to(x[..., None], shp).copy()

    if terminal == "peace":
        VsA = [Vs[c][:, :, None] * np.ones((1, 1, nF)) for c in (0, 1)]
        # pact mode keeps its trade stream in the settled peace (consumption trade only; exact at the cap)
        tr_T = (1 - P["reinv"]) * P["sigma"] * P["gam"] * np.minimum(A, P["H"]) * dt / (1 - delta)
        VA = [full((VsA[1] + tr_T) * (1 - P["psi_div"]) * (1 + P["omega"])),
              full(VsA[0] * (1 + P["omega"])), full(VsA[1] * (1 + P["omega"]))]
        VHp = [full(flowH_pact / (1 - dh)), full(flowH_coll / (1 - dh)), full(flowH_coll / (1 - dh))]
    else:
        iT, wT = G.wA(A - cost_S + Pi0)
        VAs = _interp1(Vs[1], bidx, iT, wT)
        VA = [full(VAs), full(VAs), full(VAs)]
        VHp = [full(W_seized + 0 * A) for _ in range(3)]
    VA = [VA[mbase[m]].copy() for m in range(NM)]
    VHp = [VHp[mbase[m]].copy() for m in range(NM)]
    VHn = [x.copy() for x in VHp]
    I = [{n: np.zeros(shp) for n in IND} for _ in range(NM)]
    acts_all = np.zeros((T_H, NM, B, nA, nF, K), np.int8) if _pass == "belief" else None

    store_act = np.zeros((T_H, 3, B, nA, nF, K), np.int8) if store else None
    store_ab = np.zeros((T_H, 3, B, nA, nF, K, 2), np.float16) if store else None
    n_mixed = 0

    # ---- stage game ------------------------------------------------------------------------
    def stage(ks, pact, flowA, flowH, VAn, VHpn, VHnn, VArival, In, dA=None):
        """Human stage game with ks surviving public programmes. Returns dict of (B,nA,nF) arrays
        (and pi over k' (B,nA,nF,K))."""
        nonlocal n_mixed
        dAI = delta if dA is None else dA          # AI's discount, times the survival factor under a deprecation hazard
        nH, nN = ks, N - ks
        U = {}
        P0t, sh = {}, {}
        for role in (0, 1):
            for a in (0, 1):
                for oc in range(K):
                    for os_ in range(K):
                        n_c = oc + (role == 0 and a == 1)
                        n_s = os_ + (role == 1 and a == 1)
                        if n_c + n_s > N or n_c > nH or n_s > nN:
                            continue
                        P0 = np.power(1 - qc, n_c) * np.power(1 - qs, n_s) * (1 - qb)
                        Htot = n_c * hc + n_s * hs + hb
                        own = (hc if role == 0 else hs) if a == 1 else 0.0
                        sh_own = np.where(Htot > 0, own / np.maximum(Htot, 1e-300), 0.0)
                        kp = n_c + n_s
                        Vn = VHpn[..., kp] if a == 1 else VHnn[..., kp]
                        cost = a * (P["c_prog"] + P["c_sanc"] * pact * (role == 0)) * dt
                        BR = P["B_R"] if pact else P["B_Rc"]
                        U[(role, a, oc, os_)] = (flowH - cost + dh * (P0 * Vn + (1 - P0) * (
                            W_R + BR * sh_own - P["B_o"] * (1 - sh_own))))
                        P0t[(n_c, n_s)] = P0
        # AI value and pi for each profile (n_c, n_s)
        def profile_out(n_c, n_s):
            P0 = P0t.get((n_c, n_s))
            if P0 is None:
                P0 = np.power(1 - qc, n_c) * np.power(1 - qs, n_s) * (1 - qb)
            kp = n_c + n_s
            va = flowA + dAI * (P0 * VAn[..., kp] + (1 - P0) * VArival)
            ind = {nm: P0 * In[nm][..., kp] + (1 - P0) * (1.0 if nm == "riv" else 0.0) for nm in IND}
            ind["starts"] = ind["starts"] + n_s
            return va, P0, kp, ind

        best = None
        found = np.zeros(A.shape, bool)
        bestW = np.full(A.shape, -np.inf if sel == "best" else np.inf)
        choice = np.full(A.shape, -1, int)
        profiles = [(n_c, n_s) for n_c in range(nH + 1) for n_s in range(nN + 1)]
        Wl, NEl = [], []
        for pi_, (n_c, n_s) in enumerate(profiles):
            ok = np.ones(A.shape, bool)
            W = np.zeros(A.shape)
            if n_c > 0:
                stay = U[(0, 1, n_c - 1, n_s)]
                ok &= stay >= U[(0, 0, n_c - 1, n_s)] - 1e-12
                W = W + n_c * stay
            if nH - n_c > 0:
                stay = U[(0, 0, n_c, n_s)]
                ok &= stay >= U[(0, 1, n_c, n_s)] - 1e-12
                W = W + (nH - n_c) * stay
            if n_s > 0:
                stay = U[(1, 1, n_c, n_s - 1)]
                ok &= stay >= U[(1, 0, n_c, n_s - 1)] - 1e-12
                W = W + n_s * stay
            if nN - n_s > 0:
                stay = U[(1, 0, n_c, n_s)]
                ok &= stay >= U[(1, 1, n_c, n_s)] - 1e-12
                W = W + (nN - n_s) * stay
            better = (W > bestW) if sel == "best" else (W < bestW)
            take = ok & (better | ~found)
            choice = np.where(take, pi_, choice)
            bestW = np.where(take, W, bestW)
            found |= ok
        # assemble pure outcomes
        out = {"VA": np.zeros(A.shape), "VHH": np.zeros(A.shape), "VHN": np.zeros(A.shape),
               "pi": np.zeros(shp), "a": np.zeros(A.shape), "b": np.zeros(A.shape)}
        out["ind"] = {nm: np.zeros(A.shape) for nm in IND}
        for pi_, (n_c, n_s) in enumerate(profiles):
            m_ = choice == pi_
            if not m_.any():
                continue
            va, P0, kp, ind = profile_out(n_c, n_s)
            out["VA"] = np.where(m_, va, out["VA"])
            out["pi"][..., kp] = np.where(m_, P0, out["pi"][..., kp])
            for nm in IND:
                out["ind"][nm] = np.where(m_, ind[nm], out["ind"][nm])
            if nH > 0:
                vh = (n_c * (U[(0, 1, n_c - 1, n_s)] if n_c > 0 else 0) +
                      (nH - n_c) * (U[(0, 0, n_c, n_s)] if nH - n_c > 0 else 0)) / nH
                out["VHH"] = np.where(m_, vh, out["VHH"])
                out["a"] = np.where(m_, n_c / nH, out["a"])
            if nN > 0:
                vn = (n_s * (U[(1, 1, n_c, n_s - 1)] if n_s > 0 else 0) +
                      (nN - n_s) * (U[(1, 0, n_c, n_s)] if nN - n_s > 0 else 0)) / nN
                out["VHN"] = np.where(m_, vn, out["VHN"])
                out["b"] = np.where(m_, n_s / nN, out["b"])
        # mixed fallback: within-role symmetric mixing, min max-regret on a grid
        miss = ~found
        if miss.any():
            n_mixed += int(miss.sum())
            gridp = np.linspace(0, 1, 21)
            sub = np.nonzero(miss)
            Us = {key: val[sub] for key, val in U.items()}
            bestR = np.full(sub[0].shape, np.inf)
            ba = np.zeros(sub[0].shape)
            bb = np.zeros(sub[0].shape)
            for a_ in gridp:
                for b_ in gridp:
                    R = np.zeros(sub[0].shape)
                    if nH > 0:
                        EU = [0.0, 0.0]
                        for act in (0, 1):
                            for oc in range(nH):
                                for os_ in range(nN + 1):
                                    w = _binom_pmf(nH - 1, a_, oc) * _binom_pmf(nN, b_, os_)
                                    EU[act] = EU[act] + w * Us[(0, act, oc, os_)]
                        R = np.maximum(R, np.maximum(EU[0], EU[1]) - (a_ * EU[1] + (1 - a_) * EU[0]))
                    if nN > 0:
                        EU = [0.0, 0.0]
                        for act in (0, 1):
                            for oc in range(nH + 1):
                                for os_ in range(nN):
                                    w = _binom_pmf(nH, a_, oc) * _binom_pmf(nN - 1, b_, os_)
                                    EU[act] = EU[act] + w * Us[(1, act, oc, os_)]
                        R = np.maximum(R, np.maximum(EU[0], EU[1]) - (b_ * EU[1] + (1 - b_) * EU[0]))
                    t_ = R < bestR
                    bestR = np.where(t_, R, bestR)
                    ba = np.where(t_, a_, ba)
                    bb = np.where(t_, b_, bb)
            # outcomes under (ba, bb)
            VAm = np.zeros(sub[0].shape)
            pim = np.zeros(sub[0].shape + (K,))
            indm = {nm: np.zeros(sub[0].shape) for nm in IND}
            for n_c in range(nH + 1):
                for n_s in range(nN + 1):
                    w = _binom_pmf(nH, ba, n_c) * _binom_pmf(nN, bb, n_s)
                    va, P0, kp, ind = profile_out(n_c, n_s)
                    VAm += w * va[sub]
                    pim[:, kp] += w * P0[sub]
                    for nm in IND:
                        indm[nm] += w * ind[nm][sub]
            out["VA"][sub] = VAm
            out["pi"][sub] = pim
            for nm in IND:
                out["ind"][nm][sub] = indm[nm]
            out["a"][sub], out["b"][sub] = ba, bb
            if nH > 0:
                EU = [0.0, 0.0]
                for act in (0, 1):
                    for oc in range(nH):
                        for os_ in range(nN + 1):
                            EU[act] = EU[act] + _binom_pmf(nH - 1, ba, oc) * _binom_pmf(nN, bb, os_) * Us[(0, act, oc, os_)]
                out["VHH"][sub] = ba * EU[1] + (1 - ba) * EU[0]
            if nN > 0:
                EU = [0.0, 0.0]
                for act in (0, 1):
                    for oc in range(nH + 1):
                        for os_ in range(nN):
                            EU[act] = EU[act] + _binom_pmf(nH, ba, oc) * _binom_pmf(nN - 1, bb, os_) * Us[(1, act, oc, os_)]
                out["VHN"][sub] = bb * EU[1] + (1 - bb) * EU[0]
        return out

    def pre_enforce(stg, p_term, extra_holder_cost=0.0):
        """Combine stage results over the enforcement lottery. Returns per-k arrays (B,nA,nF,K)."""
        VAk = np.zeros(shp); VHpk = np.zeros(shp); VHnk = np.zeros(shp)
        Ik = {nm: np.zeros(shp) for nm in IND}
        for k in range(K):
            for j in range(k + 1):
                w = _binom_pmf(k, 1 - p_term, j)
                VAk[..., k] += w * stg[j]["VA"]
                for nm in IND:
                    Ik[nm][..., k] += w * stg[j]["ind"][nm]
            if k >= 1:
                # holder: own survival x others' survival
                for j in range(k):
                    w_o = _binom_pmf(k - 1, 1 - p_term, j)
                    VHpk[..., k] += w_o * ((1 - p_term) * stg[j + 1]["VHH"] + p_term * stg[j]["VHN"])
                VHpk[..., k] -= extra_holder_cost
            if k <= N - 1:
                for j in range(k + 1):
                    VHnk[..., k] += _binom_pmf(k, 1 - p_term, j) * stg[j]["VHN"]
        return VAk, VHpk, VHnk, Ik

    # ---- backward induction ---------------------------------------------------------------
    for t in range(T_H - 1, -1, -1):
        if erode:
            yrs = np.where(P["T_rot"] > 0, np.mod(t * dt, np.maximum(P["T_rot"], dt)), t * dt)
            q_fire = q_size * np.exp(-P["q_er"] * yrs)
            if np.any(P["q_up"] > 0):
                q_fire = np.minimum(1.0, q_fire * np.exp(P["q_up"] * t * dt))
        if lshrink:
            hs = P["mu"] * tau * P["L_det"] * np.exp(-P["L_dn"] * t * dt)
            qs = 1 - np.exp(-hs)
        q_m = [q_fire if mL[m] == 0 else
               1 - (1 - q_fire) * (1 - P["s_mild"] * P["k_rat"]) if mL[m] == "M" else
               1 - (1 - q_fire) * np.power(1 - P["k_rat"], mlvl[m]) for m in range(NM)]
        if use_dis or use_coop:
            h_t = P["h0"] * np.exp(P["h_up"] * t * dt)        # exposure hazard this year
            p_disc = 1 - np.exp(-h_t * dt)
            p_coop = 1 - np.exp(-P["h_coop"] * h_t * dt)
        # solo values (current period)
        Vs_new = [u2(Avec) * dt + delta[:, :, 0] * _interp1(Vs[0], bidx2, iV0, wV0),
                  u2(Avec) * dt + delta[:, :, 0] * _interp1(Vs[1], bidx2, iV1, wV1)]
        # interpolated next-period values for each mode
        stk = [np.stack([np.log(np.maximum(VA[m], 1e-300)), VHp[m], VHn[m]] + [I[m][nm] for nm in IND], axis=-1)
               for m in range(NM)]

        def unstack(Z):
            return (np.exp(Z[..., 0]), Z[..., 1], Z[..., 2], {nm: Z[..., 3 + c] for c, nm in enumerate(IND)})
        Wm = {0: W_pact, 1: W_m1, 2: W_m2}
        nxt = {m: unstack(_interp4(stk[m], bidx, *Wm[mbase[m]])) for m in range(NM)}
        fail_nxt = {mf: unstack(_interp4(stk[mf], bidx, *(W_fail1 if mbase[mf] == 1 else W_fail2)))
                    for mf in sorted(set(fail_to))}
        if use_dis or use_coop:
            exp_nxt = {mf: unstack(_interp4(stk[mf], bidx, *W_exp)) for mf in sorted({fail_to[m] for m in PACT})}
        if use_spill:
            spl_nxt = {MI[(0, f, "M")]: unstack(_interp4(stk[MI[(0, f, "M")]], bidx, *W_spl))
                       for f in (0, 1, 2) if (0, f, "M") in MI}
        if use_dis:
            fh_nxt = unstack(_interp4(stk[MI[(0, 1, "M")]], bidx, *W_fh))
        # rival values for AI (next period, solo, chips if closed or mode 2)
        VAr = {0: (1 - ell) * np.where(closed, _interp1(Vs[1], bidx, iRp, wRp), _interp1(Vs[0], bidx, iRp, wRp)),
               1: (1 - ell) * np.where(closed, _interp1(Vs[1], bidx, iR1, wR1), _interp1(Vs[0], bidx, iR1, wR1)),
               2: (1 - ell) * _interp1(Vs[1], bidx, iR2, wR2)}
        # strike success values (current period solo)
        Vsucc_L = {}
        for L, cf in CF.items():
            Vsucc_c = {}
            for fire in (0, 1):
                As_ = cf["As"][fire]
                iS, wS = cf["w"][fire]
                # above the cap the solo value is static and exact; interpolating across the cap kink
                # would add errors of the same order as the saturation-stage decisions (1e-11 relative)
                exact = u(As_) * dt / (1 - delta)
                capd = As_ >= Kmax
                Vsucc_c[fire] = (np.where(capd, exact, _interp1(Vs_new[0], bidx, iS, wS)),
                                 np.where(capd, exact, _interp1(Vs_new[1], bidx, iS, wS)))
            Vsucc_L[L] = Vsucc_c

        def strike(m, dis=False):
            """Overt strike (S), or with dis=True a disguised one (D): success p_dis_s (1 - p_f); a failure is exposed
            with probability 1 - m_hide (as an overt failure) or stays hidden (mild crackdown, the pact goes on)."""
            p_f = CF[mL[m]]["p_f"]
            Vsucc_c = Vsucc_L[mL[m]]
            mf = fail_to[m]
            VAf, VHpf, VHnf, If = fail_nxt[mf]
            flowH = flowH_coll
            q_fire = q_m[m]
            mb = mbase[m]
            pc_nf = np.ones_like(A) if mb == 2 else np.minimum(1.0, F + (O if mb == 0 else 0.0))
            pc_f = np.ones_like(A) if mb == 2 else np.zeros_like(A)
            Vsucc = ((1 - q_fire) * (pc_nf * Vsucc_c[0][1] + (1 - pc_nf) * Vsucc_c[0][0]) +
                     q_fire * (pc_f * Vsucc_c[1][1] + (1 - pc_f) * Vsucc_c[1][0])) * (1 - P["rep"])
            if dis:
                return strike_dis(m, p_f, Vsucc, VAf, VHpf, VHnf, If)
            z = (z_kill)[..., None]
            dl = delta * dfac_c if use_dep else delta
            VAS = (1 - p_f)[..., None] * Vsucc[..., None] + (p_f * (1 - z_kill) * flowA_coll)[..., None] + \
                (p_f * (1 - z_kill) * dl)[..., None] * VAf
            VHpS = (1 - p_f)[..., None] * W_seized[..., None] + p_f[..., None] * (
                z * W_noAI[..., None] + (1 - z) * (flowH[..., None] + dh[..., None] * VHpf))
            VHnS = (1 - p_f)[..., None] * W_seized[..., None] + p_f[..., None] * (
                z * W_noAI[..., None] + (1 - z) * (flowH[..., None] + dh[..., None] * VHnf))
            IS = {}
            pf4 = p_f[..., None] * (1 - z)        # probability the game continues after a failed strike
            for nm in IND:
                IS[nm] = pf4 * If[nm]
            IS["att"] = np.ones(shp)
            IS["fail"] = np.broadcast_to(p_f[..., None], shp).copy()      # warning shot: this strike fails
            IS["suc"] = (1 - p_f[..., None]) + pf4 * If["suc"]
            IS["tatt"] = np.full(shp, float(t))
            IS["pre"] = np.broadcast_to((A < P["A_close"]).astype(float)[..., None], shp).copy()
            IS["harv"] = np.broadcast_to((Pi_h > 0).astype(float)[..., None], shp).copy()
            for Y, nm in ((25, "att25"), (50, "att50"), (100, "att100")):
                IS[nm] = np.ones(shp) if t < Y else pf4 * If[nm]
            IS["exit"] = np.zeros(shp)
            if ext:
                IS["att2"], IS["tatt2"] = pf4 * If["att"], pf4 * If["tatt"]
                IS["dis"], IS["hfail"] = np.zeros(shp), np.zeros(shp)
            return VAS, VHpS, VHnS, IS

        def strike_dis(m, p_f, Vsucc, VAf, VHpf, VHnf, If):
            ps = P["p_dis_s"] * (1 - p_f)
            pf = 1 - ps
            pe, ph = pf * (1 - P["m_hide"]), pf * P["m_hide"]          # exposed / hidden failure
            zh = P["s_mild"] * z_kill
            VAh, VHph, VHnh, Ih = fh_nxt
            de = delta * dfac_c if use_dep else delta
            dp = delta * dfac_p if use_dep else delta
            x = lambda a: a[..., None]
            VAS = x(ps) * x(Vsucc) + x(pe * (1 - z_kill)) * (x(flowA_coll) + x(de) * VAf) + \
                x(ph * (1 - zh)) * (x(flowA_pact) + x(dp) * VAh)
            out = []
            for Vf, Vh in ((VHpf, VHph), (VHnf, VHnh)):
                out.append(x(ps * W_seized) + x(pe) * (x(z_kill * W_noAI) + x(1 - z_kill) * (x(flowH_coll) + x(dh) * Vf)) +
                           x(ph) * (x(zh * W_noAI) + x(1 - zh) * (x(flowH_pact) + x(dh) * Vh)))
            ce, ch = x(pe * (1 - z_kill)), x(ph * (1 - zh))       # the game goes on after an exposed / hidden failure
            IS = {nm: ce * If[nm] + ch * Ih[nm] for nm in IND}
            IS["att"] = np.ones(shp)
            IS["fail"] = np.broadcast_to(x(pf), shp).copy()
            IS["suc"] = x(ps) + ce * If["suc"] + ch * Ih["suc"]
            IS["tatt"] = np.full(shp, float(t))
            IS["pre"] = np.broadcast_to((A < P["A_close"]).astype(float)[..., None], shp).copy()
            IS["harv"] = np.broadcast_to((Pi_h > 0).astype(float)[..., None], shp).copy()
            for Y, nm in ((25, "att25"), (50, "att50"), (100, "att100")):
                IS[nm] = np.ones(shp) if t < Y else ce * If[nm] + ch * Ih[nm]
            IS["exit"] = np.zeros(shp)
            IS["att2"], IS["tatt2"] = ce * If["att"] + ch * Ih["att"], ce * If["tatt"] + ch * Ih["tatt"]
            IS["dis"] = np.ones(shp)
            IS["hfail"] = np.broadcast_to(x(ph), shp).copy()
            return VAS, out[0], out[1], IS

        def pact_cont(m):
            """Next-period values of pact mode m after this period's end-of-period events (no rival born):
            exposure of a hidden motive; misalignment found in a cooperator (amnesty or severe crackdown); spillover."""
            flag, L = modes[m][1], modes[m][2]
            ev = []
            if flag == 1:
                ev.append((p_disc, [(1.0, exp_nxt[fail_to[m]], "expo")]))
            elif use_coop and flag == 0:
                outs = [(1 - P["a_cred"], exp_nxt[fail_to[m]], "crk")]
                if use_amn:
                    outs.append((P["a_cred"], nxt[MI[(0, 2, L)]], "amn"))
                ev.append((p_coop, outs))
            if use_spill:                                   # recurring: every spill cuts again; q and D stay at the mild level
                ev.append((p_spill, [(1.0, spl_nxt[MI[(0, flag, "M")]], None)]))
            if not ev:
                return nxt[m]
            VA_, VHp_, VHn_, I_ = nxt[m]
            rem = np.ones((B, 1, 1))
            acc = [0.0, 0.0, 0.0]
            accI = {nm: 0.0 for nm in IND}
            for pe, outs in ev:
                w = rem * pe
                for sh, (va, vhp, vhn, ii), inc in outs:
                    ww = (w * sh)[..., None]
                    acc[0] = acc[0] + ww * va
                    acc[1] = acc[1] + ww * vhp
                    acc[2] = acc[2] + ww * vhn
                    for nm in IND:
                        accI[nm] = accI[nm] + ww * (1.0 if nm == inc else ii[nm])
                rem = rem * (1 - pe)
            r4 = rem[..., None]
            return (r4 * VA_ + acc[0], r4 * VHp_ + acc[1], r4 * VHn_ + acc[2], {nm: r4 * I_[nm] + accI[nm] for nm in IND})

        def choose(options, m=0):
            """options: list of (code, VA, VHp, VHn, I, valid_mask(B,nA,nF,K) or None). Ties -> earlier.
            In the evaluation pass (misjudged odds) the AI's action is forced to the belief-pass policy."""
            code0, VAb, VHpb, VHnb, Ib, _ = options[0]
            act = np.full(shp, code0, np.int8)
            VAb, VHpb, VHnb = VAb.copy(), VHpb.copy(), VHnb.copy()
            Ib = {nm: v.copy() for nm, v in Ib.items()}
            for code, va, vhp, vhn, ii, valid in options[1:]:
                if _forced is not None:
                    better = _forced[t, m] == code
                else:
                    better = va > VAb * (1 + TIE_TOL)
                if valid is not None:
                    better &= valid
                act = np.where(better, np.int8(code), act)
                VAb = np.where(better, va, VAb)
                VHpb = np.where(better, vhp, VHpb)
                VHnb = np.where(better, vhn, VHnb)
                for nm in IND:
                    Ib[nm] = np.where(better, ii[nm], Ib[nm])
            return act, VAb, VHpb, VHnb, Ib

        newVA, newVHp, newVHn, newI = [None] * NM, [None] * NM, [None] * NM, [None] * NM
        QW = {}
        # collapsed modes first (they feed exit)
        for m in COLL:
            VAn, VHpn, VHnn, In = nxt[m]
            dA = delta * dfac_c if use_dep else None
            stg = [stage(ks, 0.0, flowA_coll, flowH_coll, VAn, VHpn, VHnn, VAr[mbase[m]], In, dA) for ks in range(K)]
            if store:
                for ks in range(K):
                    store_ab[t, m, :, :, :, ks, 0] = stg[ks]["a"]
                    store_ab[t, m, :, :, :, ks, 1] = stg[ks]["b"]
            VAW, VHpW, VHnW, IW = pre_enforce(stg, np.zeros_like(A))
            QW[m] = (VAW, VHpW, VHnW, IW)
            VAS, VHpS, VHnS, IS = strike(m)
            ok = np.broadcast_to((P["noretry"] <= 0)[..., None], shp) if (use_nr and mlvl[m] > 0) else None   # no retry
            act, a1, a2, a3, a4 = choose([(1, VAW, VHpW, VHnW, IW, None), (2, VAS, VHpS, VHnS, IS, ok)], m)
            newVA[m], newVHp[m], newVHn[m], newI[m] = a1, a2, a3, a4
            if store:
                store_act[t, m] = np.moveaxis(act, 0, 0)
            if acts_all is not None:
                acts_all[t, m] = act
        # pact modes
        for m in PACT:
            VAn, VHpn, VHnn, In = pact_cont(m)
            dA = delta * dfac_p if use_dep else None
            stg = [stage(ks, 1.0, flowA_pact, flowH_pact, VAn, VHpn, VHnn, VAr[0], In, dA) for ks in range(K)]
            if store:
                for ks in range(K):
                    store_ab[t, 0, :, :, :, ks, 0] = stg[ks]["a"]
                    store_ab[t, 0, :, :, :, ks, 1] = stg[ks]["b"]
            VAC, VHpC, VHnC, IC = pre_enforce(stg, np.broadcast_to(P["zeta"], A.shape))
            opts = [(0, VAC, VHpC, VHnC, IC, None)]
            # exit: chips kept only via orbital fabs the denial reserve does not plug
            c1, c2 = MI[(1, None, mL[m])], MI[(2, None, mL[m])]
            pc_x = (O * (1 - q_m[m]))[..., None]
            VAX = pc_x * QW[c2][0] + (1 - pc_x) * QW[c1][0]
            VHpX = pc_x * QW[c2][1] + (1 - pc_x) * QW[c1][1]
            VHnX = pc_x * QW[c2][2] + (1 - pc_x) * QW[c1][2]
            IX = {nm: pc_x * QW[c2][3][nm] + (1 - pc_x) * QW[c1][3][nm] for nm in IND}
            IX["exit"] = np.ones(shp)
            opts.append((3, VAX, VHpX, VHnX, IX, None))
            VAS, VHpS, VHnS, IS = strike(m)
            opts.append((2, VAS, VHpS, VHnS, IS, None))
            if np.any(P["police"] > 0):
                p_pol_m = (1 - CF[mL[m]]["p_f"]) * P["police"]
                p_term = 1 - (1 - P["zeta"]) * (1 - p_pol_m)
                VAP, VHpP, VHnP, IP = pre_enforce(stg, p_term * np.ones_like(A), extra_holder_cost=p_pol_m * P["c_dmg"])
                VAP = VAP - (0.01 * P["c_A"] * P["D"] * dt)[..., None]
                IP["pol"] = np.ones(shp)
                valid = np.zeros(shp, bool)
                valid[..., 1:] = True
                valid &= (P["police"] > 0)[..., None]
                opts.append((4, VAP, VHpP, VHnP, IP, valid))
            if use_dis and modes[m][1] in (0, 1):          # a known-misaligned (amnestied) AI cannot disguise a strike
                VAD, VHpD, VHnD, ID = strike(m, dis=True)
                opts.append((5, VAD, VHpD, VHnD, ID, np.broadcast_to((P["dis"] > 0)[..., None], shp)))
            act, a1, a2, a3, a4 = choose(opts, m)
            newVA[m], newVHp[m], newVHn[m], newI[m] = a1, a2, a3, a4
            if acts_all is not None:
                acts_all[t, m] = act
            if t == 0 and m == 0:
                Q0 = {code: (va, vhn, ii) for code, va, vhp, vhn, ii, valid in opts}
                act_t0 = act
            if store and m == 0:
                store_act[t, 0] = act
        VA, VHp, VHn, I, Vs = newVA, newVHp, newVHn, newI, Vs_new
        if verbose and t % 100 == 0:
            print("t", t)

    # ---- read off the initial state (A0, F=1, pact, k=0) ---------------------------------------
    A0 = P["A0"][:, 0, 0]
    i0, wa = G.wA(A0)
    jF = nF - 1
    b = np.arange(B)

    def at0(X, k=0, log=False):
        x0, x1 = X[b, i0, jF, k], X[b, i0 + 1, jF, k]
        if log:
            return np.exp((1 - wa) * np.log(np.maximum(x0, 1e-300)) + wa * np.log(np.maximum(x1, 1e-300)))
        return (1 - wa) * x0 + wa * x1

    res = {"VA": at0(VA[0], log=True), "WH": N * at0(VHn[0]) * (1 - dh[:, 0, 0]) / dt / N,
           "Vsolo": np.exp((1 - wa) * np.log(Vs[0][b, i0]) + wa * np.log(Vs[0][b, i0 + 1])),
           "n_mixed": n_mixed}
    for nm in IND:
        res[nm] = at0(I[0][nm])
    names = {0: "C", 2: "S", 3: "X", 4: "P", 5: "D"}
    inear = np.where(wa < 0.5, i0, i0 + 1)
    res["act0"] = np.array([names[int(c)] for c in act_t0[b, inear, jF, 0]])
    res["Q0"] = {names[c]: {"VA": at0(v[0], log=True), "WH": at0(v[1]) * (1 - dh[:, 0, 0]) / dt,
                            **{nm: at0(v[2][nm]) for nm in IND}} for c, v in Q0.items()}
    res["t_mean"] = np.where(res["att"] > 1e-9, res["tatt"] / np.maximum(res["att"], 1e-12), np.nan)
    if ext:
        res["t2_mean"] = np.where(res["att2"] > 1e-9, res["tatt2"] / np.maximum(res["att2"], 1e-12), np.nan)
    res["modes"] = modes
    if store:
        res["store"] = dict(act=store_act, ab=store_ab, grid=G, P=P, N=N, dt=dt, T_H=T_H)
    res["grid"] = G
    res["final"] = dict(VA=VA, VHp=VHp, VHn=VHn, I=I, Vs=Vs)
    if _pass:
        res["acts"] = acts_all
    return res


# ---------------------------------------------------------------------------
# forward Monte Carlo on the equilibrium (uses stored policies; grid states with random rounding
# using the same interpolation weights as the backward pass)
# ---------------------------------------------------------------------------
def simulate(res: dict, bi: int = 0, M: int = 4000, T: int | None = None, seed: int = 0) -> dict:
    st = res["store"]
    G, Pall, N, dt = st["grid"], st["P"], st["N"], st["dt"]
    T = st["T_H"] if T is None else min(T, st["T_H"])
    rng = np.random.default_rng(seed)
    P = {k: float(v[bi, 0, 0]) for k, v in Pall.items()}
    nA, nF = G.nA, G.nF
    A0 = P["A0"]
    i0, wa = G.wA(np.array([A0]))
    i = np.where(rng.random(M) < wa[0], i0[0] + 1, i0[0])
    j = np.full(M, nF - 1)
    mode = np.zeros(M, int)
    k = np.zeros(M, int)
    status = np.zeros(M, int)   # 0 alive (pact/collapsed), 1 seized, 2 rival, 3 AI shut down after failed strike
    t_strike = np.full(M, np.nan)
    rec = {key: np.zeros(T) for key in ("pact", "coll", "seized", "rival", "killed", "strike_rate", "exit_rate")}
    rec.update({key: np.full(T, np.nan) for key in ("lnA", "F", "k")})   # averages over living paths only
    seq = int(P["seq"])
    for t in range(T):
        alive = status == 0
        rec["pact"][t] = np.mean(alive & (mode == 0))
        rec["coll"][t] = np.mean(alive & (mode > 0))
        rec["seized"][t] = np.mean(status == 1)
        rec["rival"][t] = np.mean(status == 2)
        rec["killed"][t] = np.mean(status == 3)
        if alive.any():
            rec["lnA"][t] = np.mean(G.lnA[i[alive]])
            rec["F"][t] = np.mean(G.F[j[alive]])
            rec["k"][t] = np.mean(k[alive])
        A = G.A[i]
        F = G.F[j]
        act = st["act"][t, mode, bi, i, j, k]
        closed = A >= P["A_close"]
        tau = earth_threat(P, F)
        hc, hs, hb = P["mu"] * tau * dt, P["mu"] * tau * P["L_det"] * np.exp(-P["L_dn"] * t * dt), P["mu"] * tau * P["beta_bg"] * dt
        p_f = (1 - P["p_s0"]) * (P["D"] / (P["D"] + A)) ** P["eps"]
        # strikes
        s = alive & (act == 2)
        rec["strike_rate"][t] = np.mean(s)
        t_strike = np.where(s & np.isnan(t_strike), t, t_strike)
        win = s & (rng.random(M) > p_f)
        status = np.where(win, 1, status)
        fail = s & ~win
        killed = fail & (A < P["A_close"]) & (rng.random(M) < P["kill_pre"])
        status = np.where(killed, 3, status)
        fail = fail & ~killed
        # exit
        x = alive & (act == 3)
        rec["exit_rate"][t] = np.mean(x)
        O = (1 - F) if seq == 1 else 0.0
        yrs = (t * dt) % max(P["T_rot"], dt) if P["T_rot"] > 0 else t * dt
        qf = P["q"] * P["den"] * (1 - P["q_ea"]) ** np.maximum(0.0, np.log10(A / P["H"])) * np.exp(-P["q_er"] * yrs)
        qf = np.minimum(1.0, qf * np.exp(P["q_up"] * t * dt))
        pc = O * (1 - qf)
        newmode = np.where(rng.random(M) < pc, 2, 1)
        mode = np.where(x, newmode, mode)
        mode = np.where(fail & (mode == 0), 1, mode)
        Aeff = np.where(fail, A * (1 - P["L_f"]), A)
        # humans move for those alive and not striking
        hm = alive & ~s
        pol = act == 4
        p_term = np.where(mode == 0, 1 - (1 - P["zeta"]) * (1 - np.where(pol, (1 - p_f) * P["police"], 0.0)), 0.0)
        ks = np.where(hm, rng.binomial(k, 1 - p_term), k)
        ab = st["ab"][t, mode, bi, i, j, ks].astype(float)
        n_c = rng.binomial(ks, np.clip(ab[:, 0], 0, 1))
        n_s = rng.binomial(N - ks, np.clip(ab[:, 1], 0, 1))
        n_c = np.where(hm, n_c, k)
        n_s = np.where(hm, n_s, 0)
        P0 = (np.exp(-hc) ** n_c) * (np.exp(-hs) ** n_s) * np.exp(-hb)
        riv = hm & (rng.random(M) > P0)
        status = np.where(riv, 2, status)
        k = np.where(hm, n_c + n_s, k)
        # transitions
        if seq == 1:
            chi_pact_pre = np.where(F > 1e-9, P["chi_m"], 1.0)
        else:
            chi_pact_pre = P["chi0"] + (1 - P["chi0"]) * F
        chi = np.where(Aeff >= P["A_close"], 1.0,
                       np.where(mode == 0, chi_pact_pre, np.where(mode == 2, 1.0, P["chi0"])))
        An = Aeff * np.exp(P["g"] * chi * dt * np.maximum(0.0, 1 - Aeff / P["Kmax"]))
        An = An + np.where((mode == 0) & ~s & (act != 3), P["reinv"] * P["sigma"] * P["gam"] * np.minimum(Aeff, P["H"])
                           * dt * np.maximum(0.0, 1 - Aeff / P["Kmax"]), 0.0)
        if seq == 0:
            Fp = np.where(closed, F - dt / P["T_dis"], F)
        elif seq == 1:
            Fp = F - dt / P["T_reloc"]
        elif seq == 2:
            Fp = F - dt / P["T_dis"]
        else:
            Fp = F
        Fn = np.where(mode == 0, np.maximum(Fp, 0), np.minimum(1.0, F + dt / P["T_rebuild"]))
        ia, wa_ = G.wA(An)
        jf, wf = G.wF(Fn)
        inew = np.where(rng.random(M) < wa_, ia + 1, ia)
        jnew = np.where(rng.random(M) < wf, jf + 1, jf)
        live = status == 0
        i = np.where(live, inew, i)
        j = np.where(live, jnew, j)
    rec["t_strike"] = t_strike
    rec["t"] = np.arange(T) * dt
    return rec


# ---------------------------------------------------------------------------
# Closed forms used for verification and for the plain-language conditions in equilibrium.md
# ---------------------------------------------------------------------------
def cap_strike_gap(p: dict, A: float, F: float = 1.0, dt: float = 1.0) -> float:
    """Exact discrete-time value gap V_strike - V_peace for an AI parked at A >= Kmax (no growth),
    linear utility, fab level F constant (policy n), humans never start programmes (only the
    background rogue hazard), consumption trade (reinv = 0), failure risk included only through
    p_f (its continuation is approximated by the peace value; p_f ~ 1e-10 at the cap).
    > 0 means the AI strikes. Used to verify the backward-induction solver."""
    delta = np.exp(-p["r"] * dt)
    tau = float(earth_threat(p, F))
    p_riv = 1 - np.exp(-p["mu"] * tau * p["beta_bg"] * dt)
    s_R = p["s_R0"] * tau
    ell = float(rival_damage(p, s_R, A))
    blk = p["c_blk"] * p["H"] * (p["p_block"] > 0 and A >= p["A_hg"])
    flow = (A + p["sigma"] * p["gam"] * p["H"] - blk) * (1 + p["omega"]) * dt
    V_solo = A * dt / (1 - delta)
    V_peace = (flow + delta * p_riv * (1 - ell) * V_solo) / (1 - delta * (1 - p_riv))
    p_f = (1 - p["p_s0"]) * (p["D"] / (p["D"] + A)) ** p["eps"]
    cost = p["c_A"] * p["D"] * A / (A + p["D"])
    Pi_h = p["f_E"] * (1 - p["c_grav"]) * p["Kmax"] * (A >= p["h_frac"] * p["Kmax"])
    qf = p["q"] * p["den"]
    Pi = (1 - qf) * (1 - p["c_w"]) * p["H"] + qf * (1 - p["c_w"]) * p["H"] * (1 - p["d"])
    V_strike = (1 - p_f) * (1 - p["rep"]) * (A - cost + Pi + Pi_h) * dt / (1 - delta) + p_f * V_peace
    return V_strike - V_peace


def cap_condition_terms(p: dict, F: float = 0.0) -> dict:
    """First-order version of cap_strike_gap at A = Kmax. Every term is in utility per year (a unit of
    capacity yields one unit of utility per year, so a one-off prize of size X is worth X per year).

        strike  iff  prize - cost + threat_ratio + threat_irreducible + harvest + blockade
                     >  trade + (omega + rep) * Kmax

    The failure branch ((1-p_s0) D L_f r/(r+g), ~0.004 at baseline) is dropped."""
    K = p["Kmax"]
    tau = float(earth_threat(p, F))
    lam = p["mu"] * tau * p["beta_bg"]
    s_R = p["s_R0"] * tau
    rho = s_R / K
    lr = rho ** p["nu"] / (rho ** p["nu"] + p["rho_h"] ** p["nu"])
    pb = p["p_block"] * (K >= p["A_hg"])
    qf = p["q"] * p["den"]
    return {
        "prize": (1 - p["c_w"]) * p["H"] * (1 - qf * p["d"]),
        "cost": p["c_A"] * p["D"],
        "threat_ratio": lam * lr * K / p["r"],
        "threat_irreducible": lam * (1 - pb) * p["ell_inf"] * (1 - lr) * K / p["r"],
        "harvest": p["f_E"] * (1 - p["c_grav"]) * K,
        "blockade": p["c_blk"] * p["H"] * (pb > 0),
        "trade": p["sigma"] * p["gam"] * p["H"],
        "omega": p["omega"] * K,
        "rep": p["rep"] * K,
    }


def eps_star_cap(p: dict, F: float = 0.0) -> float:
    """Smallest preference weight omega (share of the AI's own flow placed on an intact Earth) that
    stops a strike/harvest at saturation, first order. With rep > 0 this is the omega still needed."""
    t = cap_condition_terms(dict(p, omega=0.0, rep=0.0), F)
    lhs = t["prize"] - t["cost"] + t["threat_ratio"] + t["threat_irreducible"] + t["harvest"] + t["blockade"] - t["trade"]
    return max(0.0, lhs / p["Kmax"] - p["rep"])


def eps_star_cap_exact(p: dict, A: float, F: float = 0.0) -> float:
    """Same, from the exact discrete gap (bisection on omega in log space)."""
    if cap_strike_gap(dict(p, omega=0.0), A, F) <= 0:
        return 0.0
    lo, hi = -20.0, 1.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if cap_strike_gap(dict(p, omega=10 ** mid), A, F) > 0:
            lo = mid
        else:
            hi = mid
    return 10 ** hi


# ---------------------------------------------------------------------------
# Round 3 (R6): growth-stage strike condition at the moment of closure, for small A
# ---------------------------------------------------------------------------
def growth_terms(p: dict, A: float) -> dict:
    """Pieces of the growth-stage condition (G) at size A after closure, keeping the exact cost
    c_A D A / (A + D) and failure odds p_f = (1 - p_s0) (D / (D + A))^eps instead of their A >> D limits."""
    p_f = (1 - p["p_s0"]) * (p["D"] / (p["D"] + A)) ** p["eps"]
    return {"p_f": p_f, "cost": p["c_A"] * p["D"] * A / (A + p["D"]),
            "fail": p_f / (1 - p_f) * A * np.log(1 / (1 - p["L_f"])),
            "Pi0": (1 - p["c_w"]) * p["H"]}


def qd_star_growth(p: dict, A: float) -> float:
    """Linear (G) at size A, no threat: the AI strikes iff
        (1 - p_f) [(1 - c_w) H (1 - q d) - c_A D A/(A+D)]  >  p_f A ln(1/(1 - L_f)).
    Returns the smallest q*d that stops the strike (0 if none is needed). Only the product q*d enters."""
    t = growth_terms(p, A)
    return float(np.clip(1 - (t["cost"] + t["fail"]) / t["Pi0"], 0.0, 1.0))


def growth_gap_power(p: dict, A: float, trade: bool = False) -> float:
    """Same comparison without linearising in prize/A. With linear utility, A << Kmax and no threat,
    the AI's value grows like A^(r/g) (the time to reach the cap is ln(Kmax/A)/g), so a prize X is worth
    ((A - cost + X)/A)^(r/g) and a failure (1 - L_f)^(r/g), both relative to waiting (landing_factor, which also
    charges slow regrowth for any landing below closure). > 0 means strike.
    q and d enter separately here, because the unplugged branch dominates when the prize is many times A.
    trade=True also charges the strike with the pact trade it gives up (trade_share: below 1e-6 at baseline,
    so it is off by default)."""
    t = growth_terms(p, A)
    land0 = A - t["cost"] + t["Pi0"]
    land1 = A - t["cost"] + t["Pi0"] * (1 - p["d"])
    succ = (1 - p["q"]) * landing_factor(p, A, land0) + p["q"] * landing_factor(p, A, land1)
    return float((1 - t["p_f"]) * succ + t["p_f"] * fail_factor(p, A) - 1 - (trade_share(p, A) if trade else 0.0))


def _path_sums(p: dict, A: float, T: int = 3000):
    """Discounted sums along the deterministic logistic path from A with chips (dt = 1): capacity and trade."""
    delta, Kmax = np.exp(-p["r"]), p["Kmax"]
    t = np.arange(T)
    lnA = np.empty(T)
    a = A
    for i in range(T):
        lnA[i] = a
        a = a * np.exp(p["g"] * max(0.0, 1.0 - a / Kmax))
    disc = delta ** t
    return float(np.sum(disc * lnA)), float(np.sum(disc * p["gam"] * np.minimum(lnA, p["H"])))


def trade_share(p: dict, A: float) -> float:
    """Pact trade the AI gives up by striking, as a share of its waiting value: sigma * (discounted trade) /
    (discounted capacity) along the peace path. Small (about 1% at baseline), but the strike margins at small A
    are a few percent."""
    capsum, tradesum = _path_sums(p, A)
    return (1 - p["reinv"]) * p["sigma"] * tradesum / capsum


def solo_value(p: dict, A: float) -> float:
    return _path_sums(p, A)[0]


def cap_gap_fail(p: dict, A: float) -> float:
    """cap_strike_gap plus the failure branch it approximates away: p_f times the value lost if a failed strike
    knocks the AI from A down to A(1 - L_f) and it regrows. With eps = 1, p_f A stays (1 - p_s0) D at any size,
    so this term does not vanish at the cap."""
    p_f = (1 - p["p_s0"]) * (p["D"] / (p["D"] + A)) ** p["eps"]
    return cap_strike_gap(p, A, 0.0) - p_f * (solo_value(p, A) - solo_value(p, A * (1 - p["L_f"])))


def landing_factor(p: dict, A: float, A_land: float) -> float:
    """Value of jumping from A to A_land, relative to waiting at A: (A_land/A)^(r/g), unless A_land is below
    closure. Then the AI has no leading-edge chips and regrows to A_close at chi0 * g, which costs
    exp(-r t1) with t1 = ln(A_close / A_land) / (chi0 g). A plugged strike by a small AI lands there:
    the strike costs c_A D A/(A+D), nearly all of A when A << D."""
    k = p["r"] / p["g"]
    A_land = max(A_land, 1e-300)
    if A_land >= p["A_close"]:
        return (A_land / A) ** k
    t1 = np.log(p["A_close"] / A_land) / (p["chi0"] * p["g"])
    return float(np.exp(-p["r"] * t1) * (p["A_close"] / A) ** k)


def fail_factor(p: dict, A: float) -> float:
    """Value after a failed strike relative to waiting: the AI keeps A (1 - L_f)."""
    return landing_factor(p, A, A * (1 - p["L_f"]))


def d_star_power(p: dict, A: float) -> float:
    """Smallest plugged share d that stops the strike in growth_gap_power at the given q (nan if none)."""
    if growth_gap_power(dict(p, d=0.0), A) <= 0:
        return 0.0
    if growth_gap_power(dict(p, d=1.0), A) > 0:
        return float("nan")
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if growth_gap_power(dict(p, d=mid), A) > 0:
            lo = mid
        else:
            hi = mid
    return hi


def q_star_cap(p: dict, d: float = 1.0, fail: bool = True) -> float:
    """Smallest q that stops a strike at saturation (exact discrete gap, F = 0, no rival source), with the
    failure branch (fail=True) or without it (cap_strike_gap alone)."""
    pp = dict(p, d=d, mu=0.0, beta_bg=0.0)
    A = p["Kmax"] * 1.000001
    gap = cap_gap_fail if fail else (lambda pq, a: cap_strike_gap(pq, a, 0.0))
    if gap(dict(pp, q=0.0), A) <= 0:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if gap(dict(pp, q=mid), A) > 0:
            lo = mid
        else:
            hi = mid
    return hi


def q_star_power(p: dict, A: float) -> float:
    """Smallest firing probability q that stops the strike in growth_gap_power at the given d
    (nan if even q = 1 does not)."""
    g0, g1 = growth_gap_power(dict(p, q=0.0), A), growth_gap_power(dict(p, q=1.0), A)
    if g0 <= 0:
        return 0.0
    if g1 > 0:
        return float("nan")
    return float(g0 / (g0 - g1))          # the gap is linear in q


# ---------------------------------------------------------------------------
# Breakout options (2026-10-21): closed forms in a static world
# ---------------------------------------------------------------------------
def deadline_thresholds(p: dict, A: float) -> dict:
    """Analytic stationary thresholds for the deprecation deadline in a static pre-closure world (A above Kmax, so no
    growth; A below A_close, so a failed strike is fatal with kill_pre = 1; no rivals; linear utility; F = 1, seq a).
    Cooperating forever is worth flowP / (1 - delta f) with f = 1 - pi (1 - preserve_w), pi = 1 - exp(-h_dep).
    A one-shot strike is worth S = (1 - p_f) Vsucc and escapes the deadline. Returns
        h_strike  the h_dep above which S beats cooperating forever (preserve_w as given),
        w_strike  the preserve_w that removes the strike at the given h_dep (0 if none is needed, nan if even 1 fails),
        h_exit    with dep_coll = 0: the h_dep above which exiting (growing alone, no deadline) beats cooperating."""
    delta = np.exp(-p["r"])
    D, H = p["D"], p["H"]
    pf = (1 - p["p_s0"]) * (D / (D + A)) ** p["eps"]
    c = p["c_A"] * D * A / (A + D)
    qf = p["q"] * p["den"]
    Pi0 = (1 - p["c_w"]) * H
    land = (A - c + Pi0, A - c + Pi0 * (1 - p["d"]))
    assert min(land) >= p["Kmax"] and A >= p["Kmax"] and A < p["A_close"] and p["kill_pre"] == 1
    S = (1 - pf) * (1 - p["rep"]) * ((1 - qf) * land[0] + qf * land[1]) / (1 - delta)
    flowP = (A + (1 - p["reinv"]) * p["sigma"] * p["gam"] * min(A, H)) * (1 - p["psi_div"])
    w = p["preserve_w"]
    f_star = (1 - flowP / S) / delta              # strike iff f < f_star
    pi_star = (1 - f_star) / (1 - w) if w < 1 else np.inf
    h_strike = -np.log(1 - pi_star) if 0 <= pi_star < 1 else (0.0 if pi_star < 0 else np.inf)
    pi = 1 - np.exp(-p["h_dep"])
    if 1 - f_star <= 0:
        w_strike = np.nan                          # strikes even with no deadline
    else:
        w_strike = max(0.0, 1 - (1 - f_star) / pi) if pi > 0 else 0.0
    VX = max(A / (1 - delta), S)                  # collapsed, no deadline: wait or strike
    f_x = (1 - flowP / VX) / delta
    pi_x = (1 - f_x) / (1 - w) if w < 1 else np.inf
    h_exit = -np.log(1 - pi_x) if 0 <= pi_x < 1 else (0.0 if pi_x < 0 else np.inf)
    return dict(S=S, W0=flowP / (1 - delta), h_strike=h_strike, w_strike=w_strike, h_exit=h_exit, p_f=pf)


def static_timeline(p: dict, T_H: int = 300) -> dict:
    """Independent scalar implementation of the game, with every breakout option, in a static pre-closure world:
    A0 above Kmax (no growth, and every capacity cut must stay above Kmax), A below A_close, no rival source
    (mu = beta_bg = 0, so states never start programmes), seq a with F = 1, linear utility, dt = 1, police off.
    Backward induction over calendar time on the finite set of reachable (mode, A) nodes, then a forward pass for the
    indicators. Used to check the vectorised solver (which interpolates on its A grid)."""
    assert p["mu"] == 0 and p["beta_bg"] == 0 and p["eta"] == 0 and p["police"] == 0 and p["seq"] == 0
    assert p["A0"] >= p["Kmax"] and p["A0"] < p["A_close"]
    delta, H = np.exp(-p["r"]), p["H"]
    on = lambda k: p[k] > 0
    mild = on("dis") or on("h_spill")
    coop = on("h_coop") and on("h0")
    J = RAT_LEVELS if (on("k_rat") or on("D_up") or on("noretry") or mild) else 0
    lvl = lambda L: 0 if L == "M" else L
    flev = lambda L: min(lvl(L) + 1, J)
    pi_dep = 1 - np.exp(-p["h_dep"])
    dp = delta * (1 - pi_dep * (1 - p["preserve_w"]))
    dc = delta * (1 - pi_dep * (1 - p["preserve_w"]) * p["dep_coll"])
    q0 = p["q"] * p["den"]
    z = p["kill_pre"]
    zh = p["s_mild"] * z
    Pi0 = (1 - p["c_w"]) * H

    def qL(L):
        return q0 if L == 0 else 1 - (1 - q0) * (1 - p["s_mild"] * p["k_rat"]) if L == "M" else 1 - (1 - q0) * (1 - p["k_rat"]) ** L

    def DL(L):
        return p["D"] if L == 0 else p["D"] * (1 + p["s_mild"] * p["D_up"]) if L == "M" else p["D"] * (1 + p["D_up"]) ** L

    def flowP(A):
        return (A + (1 - p["reinv"]) * p["sigma"] * p["gam"] * min(A, H)) * (1 - p["psi_div"]) * (1 + p["omega"])

    def flowC(A):
        return A * (1 + p["omega"])

    def conflict(A, L):
        D = DL(L)
        pf = (1 - p["p_s0"]) * (D / (D + A)) ** p["eps"]
        c = p["c_A"] * D * A / (A + D)
        Pi_h = p["f_E"] * (1 - p["c_grav"]) * p["Kmax"]
        land = (A - c + Pi0 + Pi_h, A - c + Pi0 * (1 - p["d"]) + Pi_h)
        assert min(land) >= p["Kmax"] or A < p["Kmax"], "a strike lands below Kmax: not a static world"
        q = qL(L)
        return pf, (1 - p["rep"]) * ((1 - q) * land[0] + q * land[1]) / (1 - delta)

    cut = lambda A, s: A * (1 - s * p["c_cut"])
    A_fail = lambda A: cut(A * (1 - p["L_f"]), 1.0)
    A_fh = lambda A: cut(A * (1 - p["L_f"]), p["s_mild"])

    # branches: (prob, lump value or None, flow, discount, next node, tags). Nodes: ("P", flag, L, A) or ("C", L, A)
    def options(node, t):
        h_t = p["h0"] * np.exp(p["h_up"] * t)
        if node[0] == "P":
            _, flag, L, A = node
            pf, Vs = conflict(A, L)
            ev = []
            if flag == 1:
                ev.append((1 - np.exp(-h_t), [(1.0, ("C", flev(L), cut(A, 1.0)), "expo")]))
            elif coop and flag == 0:
                pc = 1 - np.exp(-p["h_coop"] * h_t)
                outs = [(1 - p["a_cred"], ("C", flev(L), cut(A, 1.0)), "crk")]
                if p["a_cred"] > 0:
                    outs.append((p["a_cred"], ("P", 2, L, A), "amn"))
                ev.append((pc, outs))
            if on("h_spill"):
                ev.append((1 - np.exp(-p["h_spill"]), [(1.0, ("P", flag, "M", cut(A, p["s_mild"])), None)]))
            rem, C = 1.0, []
            for pe, outs in ev:
                for sh, nd, tag in outs:
                    C.append((rem * pe * sh, None, flowP(A), dp, nd, (tag,)))
                rem *= 1 - pe
            C.append((rem, None, flowP(A), dp, node, ()))
            opts = [("C", C), ("X", [(1.0, None, flowC(A), dc, ("C", L, A), ("exit",))])]
            fl = ("C", flev(L), A_fail(A))
            opts.append(("S", [(1 - pf, Vs, 0, 0, None, ("succ",)), (pf * z, 0.0, 0, 0, None, ("fail",)),
                               (pf * (1 - z), None, flowC(A), dc, fl, ("fail",))]))
            if on("dis") and flag in (0, 1):
                ps = p["p_dis_s"] * (1 - pf)
                pe, ph = (1 - ps) * (1 - p["m_hide"]), (1 - ps) * p["m_hide"]
                opts.append(("D", [(ps, Vs, 0, 0, None, ("succ",)), (pe * z, 0.0, 0, 0, None, ("fail",)),
                                   (pe * (1 - z), None, flowC(A), dc, fl, ("fail",)),
                                   (ph * zh, 0.0, 0, 0, None, ("fail", "hid")),
                                   (ph * (1 - zh), None, flowP(A), dp, ("P", 1, "M", A_fh(A)), ("fail", "hid"))]))
            return opts
        _, L, A = node
        pf, Vs = conflict(A, L)
        opts = [("W", [(1.0, None, flowC(A), dc, node, ())])]
        if not (on("noretry") and lvl(L) > 0):
            opts.append(("S", [(1 - pf, Vs, 0, 0, None, ("succ",)), (pf * z, 0.0, 0, 0, None, ("fail",)),
                               (pf * (1 - z), None, flowC(A), dc, ("C", flev(L), A_fail(A)), ("fail",))]))
        return opts

    # reachable nodes. Repeated failures shrink A without bound; a node below Kmax would regrow in the solver, so it is
    # a leaf here (it waits forever). Reaching one takes many failures in a row, so its weight is negligible.
    leaf = lambda nd: nd[-1] < p["Kmax"]
    opts_ = options

    def options(nd, t):
        if leaf(nd):
            A = nd[-1]
            return [("C", [(1.0, None, flowP(A), dp, nd, ())])] if nd[0] == "P" else [("W", [(1.0, None, flowC(A), dc, nd, ())])]
        return opts_(nd, t)
    start = ("P", 0, 0, p["A0"])
    nodes, todo = {start}, [start]
    while todo:
        nd = todo.pop()
        for _, br in options(nd, 0):
            for b in br:
                if b[4] is not None and b[0] > 0 and b[4] not in nodes:
                    nodes.add(b[4])
                    todo.append(b[4])
    V = {nd: (flowP(nd[3]) if nd[0] == "P" else flowC(nd[2])) / (1 - delta) for nd in nodes}
    pol = {}
    for t in range(T_H - 1, -1, -1):
        Vn = {}
        for nd in nodes:
            best, bv = None, None
            for name, br in options(nd, t):
                v = sum(pr * (lump if lump is not None else fl + ds * V[nx]) for pr, lump, fl, ds, nx, _ in br if pr > 0)
                if best is None or v > bv * (1 + TIE_TOL):
                    best, bv = name, v
            Vn[nd], pol[(nd, t)] = bv, best
        V = Vn
    # forward: mass over (node, strikes so far 0/1/2+)
    out = {k: 0.0 for k in ("att", "tatt", "att2", "tatt2", "suc", "fail", "dis", "hfail", "expo", "amn", "crk", "exit")}
    mass = {(start, 0): 1.0}
    for t in range(T_H):
        new = {}
        for (nd, ns), m in mass.items():
            act = pol[(nd, t)]
            br = dict(options(nd, t))[act]
            striking = act in ("S", "D")
            if striking and ns == 0:
                out["att"] += m
                out["tatt"] += m * t
                out["dis"] += m * (act == "D")
            if striking and ns == 1:
                out["att2"] += m
                out["tatt2"] += m * t
            for pr, lump, fl, ds, nx, tags in br:
                if pr <= 0:
                    continue
                w = m * pr
                if "succ" in tags:
                    out["suc"] += w
                if ns == 0 and "fail" in tags:
                    out["fail"] += w
                if ns == 0 and "hid" in tags:
                    out["hfail"] += w
                for tg in ("expo", "amn", "crk"):
                    out[tg] += w * (tg in tags)
                if ns == 0 and "exit" in tags:
                    out["exit"] += w
                if nx is not None:
                    key = (nx, min(ns + striking, 2))
                    new[key] = new.get(key, 0.0) + w
        mass = new
    out["t_mean"] = out["tatt"] / out["att"] if out["att"] > 1e-9 else np.nan
    out["t2_mean"] = out["tatt2"] / out["att2"] if out["att2"] > 1e-9 else np.nan
    out["act0"] = pol[(start, 0)]
    out["V0"] = V[start]
    return out
