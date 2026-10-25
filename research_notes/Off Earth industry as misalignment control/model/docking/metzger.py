"""Docking 3: Metzger, Muscatello, Mueller & Mantovani (arXiv:1612.03238) lunar bootstrap against our growth law.

Metzger et al. publish a spreadsheet model (not released) and its outputs as charts. Their Fig. 2 (asset mass by
generation, generations 2 years apart) is the only growth curve in the paper. The numbers below were READ OFF that
figure by eye from a 300-dpi render of page 12 (log axis, about 90 px per decade), so each is good to roughly
+/-15%. Text values used as anchors: reduced case ends at 156 t (abstract, matches the figure); Gen 5.0 uses 1e15
J/yr and then grows 3x per year (p. 16); generations are 2 years apart (Fig. 2 caption).

Our growth law (equilibrium_model.solve, `grow`): A_{t+1} = A_t exp(g chi (1 - A_t / Kmax)), dt = 1 year,
chi = 1 with leading-edge chips (Earth fabs before closure, or own fabs after A >= A_close), chi0 = 0.15 without.

Unit bridge (an assumption, stated in docking.md): capacity measured by energy use. Metzger Gen 5.0 = 1e15 J/yr
= 31.7 MW; Earth's industry = 1 unit = 19.6 TW (2023 primary energy, cited in decision_model.md). So Gen 5.0
(max case, ~6,600 t) is about 1.6e-6 Earth units, i.e. about 2.4e-10 Earth units per tonne of assets.
"""
import math

import numpy as np

from _common import save, md_table, MODEL
import equilibrium_model as em

GEN = ["1.0", "2.0", "2.5", "3.0", "4.0", "5.0", "6.0"]
T = np.arange(7) * 2.0
MAX_T = np.array([6.9, 41, 219, 434, 1440, 6600, 23500])      # tonnes, read off Fig. 2 (solid squares)
RED_T = np.array([6.9, 20, 71, 83, 60, 192, 154])             # tonnes, read off Fig. 2 (open squares)
EARTH_W = 19.6e12
GEN5_W = 1e15 / (365.25 * 86400)
UNIT_PER_T = GEN5_W / EARTH_W / MAX_T[5]


def fit_rate(t, y):
    k, b = np.polyfit(t, np.log(y), 1)
    return float(k)


def our_path(A0, years, g, chi_pre, A_close, Kmax=1e9):
    """Exactly the solver's growth step, iterated along one deterministic path."""
    A = [A0]
    for _ in range(int(years)):
        a = A[-1]
        chi = 1.0 if a >= A_close else chi_pre
        A.append(a * math.exp(g * chi * max(0.0, 1 - a / Kmax)))
    return np.array(A)


def main():
    p = em.baseline()
    g, chi0, A0, A_close = p["g"], p["chi0"], p["A0"], p["A_close"]
    out = {}
    r_all = fit_rate(T, MAX_T)
    r_late = fit_rate(T[4:], MAX_T[4:])
    r_red_plateau = fit_rate(T[2:6], RED_T[2:6])
    post = math.log(3.0)
    out["rates"] = dict(max_all=r_all, max_gen4_6=r_late, red_plateau_gen25_5=r_red_plateau, metzger_post_closure=post,
                        ours_g=g, ours_g_range=[em.PARAMS["g"][1], em.PARAMS["g"][2]], ours_chi0_g=chi0 * g)
    rows = [["Metzger max case, Gen 1.0 to 6.0 (fit)", f"{r_all:.2f}", f"{math.log(2) / r_all:.2f}"],
            ["Metzger max case, Gen 4.0 to 6.0 (fit)", f"{r_late:.2f}", f"{math.log(2) / r_late:.2f}"],
            ["Metzger after Gen 5.0, '3x per year' (text)", f"{post:.2f}", f"{math.log(2) / post:.2f}"],
            ["Metzger reduced case, plateau Gen 2.5 to 5.0 (fit)", f"{r_red_plateau:.2f}", f"{math.log(2) / max(r_red_plateau, 1e-9):.1f}"],
            ["ours, g with chips (baseline)", f"{g:.2f}", f"{math.log(2) / g:.2f}"],
            ["ours, g range swept", f"{em.PARAMS['g'][1]:.2f} to {em.PARAMS['g'][2]:.2f}",
             f"{math.log(2) / em.PARAMS['g'][2]:.1f} to {math.log(2) / em.PARAMS['g'][1]:.1f}"],
            ["ours, chi0 g without leading-edge chips", f"{chi0 * g:.3f}", f"{math.log(2) / (chi0 * g):.1f}"]]
    print("\n## Growth rates (per year, continuous)\n")
    print(md_table(rows, ["source", "rate /yr", "doubling (yr)"]))
    # scale bridge
    A_seed = MAX_T[0] * UNIT_PER_T
    A_gen5 = MAX_T[5] * UNIT_PER_T
    A_gen6 = MAX_T[6] * UNIT_PER_T
    yrs_seed_to_A0 = {lab: math.log(A0 / A_seed) / r for lab, r in (("ours g", g), ("Metzger max fit", r_all), ("Metzger 3x/yr", post))}
    yrs_A0_to_close = {lab: math.log(A_close / A0) / r for lab, r in (("ours g, chips", g), ("ours chi0 g", chi0 * g),
                                                                          ("Metzger 3x/yr", post))}
    out["scale"] = dict(unit_per_tonne=UNIT_PER_T, A_seed=A_seed, A_gen5=A_gen5, A_gen6=A_gen6, A0=A0, A_close=A_close,
                        A0_tonnes=A0 / UNIT_PER_T, A_close_tonnes=A_close / UNIT_PER_T,
                        ratio_Aclose_to_gen5=A_close / A_gen5, yrs_seed_to_A0=yrs_seed_to_A0, yrs_A0_to_close=yrs_A0_to_close)
    print("\n## Scale bridge (energy-based, assumption)\n")
    print(md_table([["Metzger seed, Gen 1.0", f"{MAX_T[0]:.0f} t", f"{A_seed:.1e}"],
                    ["Metzger Gen 5.0 (local chips, max case)", f"{MAX_T[5]:.0f} t", f"{A_gen5:.1e}"],
                    ["Metzger Gen 6.0 (max case)", f"{MAX_T[6]:.0f} t", f"{A_gen6:.1e}"],
                    ["ours A0", f"{A0 / UNIT_PER_T:.1e} t", f"{A0:.0e}"],
                    ["ours A_close (leading-edge closure)", f"{A_close / UNIT_PER_T:.1e} t", f"{A_close:.0e}"]],
                   ["point", "asset mass", "Earth-industry units"]))
    print("\nyears from Metzger seed to our A0:", {k: round(v, 1) for k, v in yrs_seed_to_A0.items()})
    print("years from our A0 to our A_close:", {k: round(v, 1) for k, v in yrs_A0_to_close.items()})
    # our growth law started at Metzger's seed, both regimes
    yrs = np.arange(0, 41)
    paths = {
        "ours, g = 0.35, chips (chi = 1)": our_path(A_seed, 40, g, 1.0, 0.0),
        "ours, g = 0.35, no chips (chi0) below A_close": our_path(A_seed, 40, g, chi0, A_close),
        "ours, g = 0.69 (top of range), chips": our_path(A_seed, 40, em.PARAMS["g"][2], 1.0, 0.0),
    }
    out["paths_t12"] = {k: float(v[12] / UNIT_PER_T) for k, v in paths.items()}
    out["metzger_t12"] = dict(max=float(MAX_T[6]), red=float(RED_T[6]))
    print("\nmass at year 12 starting from Metzger's 6.9 t seed (t):", {k: f"{v:.0f}" for k, v in out["paths_t12"].items()},
          "Metzger max", MAX_T[6], "reduced", RED_T[6])
    # figure
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    BLUE, ORANGE, GREY = "#0072B2", "#E69F00", "#555555"
    fig, ax = plt.subplots(figsize=(7.5, 4.6), dpi=150)
    ax.semilogy(T, MAX_T, "s", color=BLUE, ms=8, label="Metzger Fig. 2, max rate (read off chart)")
    ax.semilogy(T, RED_T, "s", color=BLUE, ms=8, mfc="white", mew=2, label="Metzger Fig. 2, reduced rate")
    ax.semilogy(yrs, paths["ours, g = 0.35, chips (chi = 1)"] / UNIT_PER_T, "-", color=ORANGE, lw=2,
                label="ours, g = 0.35 with chips")
    ax.semilogy(yrs, paths["ours, g = 0.69 (top of range), chips"] / UNIT_PER_T, "--", color=ORANGE, lw=2,
                label="ours, g = 0.69 (top of swept range)")
    ax.semilogy(yrs, paths["ours, g = 0.35, no chips (chi0) below A_close"] / UNIT_PER_T, ":", color=GREY, lw=2,
                label="ours, chips denied (chi0 = 0.15)")
    ax.set_xlim(0, 25)
    ax.set_ylim(1, 1e9)
    ax.set_xlabel("years from a 6.9 t lunar seed")
    ax.set_ylabel("asset mass (t); 1 t ~ 2.4e-10 Earth industry")
    ax.grid(True, which="major", color="#dddddd", lw=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.text(12.4, MAX_T[6], "Metzger max", color="#222222", fontsize=8, va="center")
    ax.text(12.4, RED_T[6], "Metzger reduced", color="#222222", fontsize=8, va="center")
    ax.legend(fontsize=7.5, frameon=False, loc="upper left")
    ax.set_title("Bootstrap growth: Metzger et al. 2013 vs our growth law", fontsize=10)
    fig.tight_layout()
    path = MODEL + "/figures/dock_metzger.png"
    fig.savefig(path)
    print("figure:", path)
    print("wrote", save("metzger", out))


if __name__ == "__main__":
    main()
