# Metzger et al. 2013: source, version and growth-rate citation, rechecked

[[ai gen]] 2026-10-25, issue #11 box 1. Status: source read in primary form (the arXiv manuscript);
the figure re-digitized by a script; no empirical claim. Evidence record: `EV-METZGER-2013` in
`evidence/records.yaml` (updated in this change).

## Source and version

| item | finding | how checked |
|---|---|---|
| Version of record | Metzger, Muscatello, Mueller, Mantovani, "Affordable, Rapid Bootstrapping of the Space Industry and Solar System Civilization", *J. Aerospace Eng.* 26(1):18-29, January 2013, doi:10.1061/(ASCE)AS.1943-5525.0000236 | Crossref API, 2026-10-25 (published-print 2013-01; DOI registered 2012-04-02) |
| Version read | arXiv:1612.03238v1, posted 2016-12-10, the only arXiv version. Pages stamped "Preprint. To appear in Journal of Aerospace Engineering"; PDF created 2012-03-30. sha256 `637bd611...e171bc62` | arxiv.org abstract page and PDF |
| Discrepancy | arXiv's journal-ref says "26.2"; Crossref says issue 1 | both pages |
| Not compared | the published version on ascelibrary.org (HTTP 403 from this environment). Differences between the accepted manuscript and the version of record are unknown | |
| Licence | arXiv non-exclusive distribution licence; the PDF is not vendored, only fetched by hash | abstract page |

The register and docs cited "Metzger et al. 2013" correctly as to year. The model's earlier citation
said nothing about which version was read; it was this manuscript.

## What the source says about growth

- Fig. 2 caption: "Growth of lunar industry by generations in **2-year intervals**." Seven points
  (Gen 1.0, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0), so 12 years from seed to Gen 6.0.
- p. 11: "each basic set of assets creates **two or fewer new sets per year**" (a gross replication
  bound of at most 3x per year, before retirements and set-asides); manufacturing rate 0.5 kg/h per
  unit, "a high estimate"; the second case halves it and plateaus near 100 t until closure.
- p. 16: Gen 5.0 uses 10^15 J per year; "Multiplying this by a factor of 3 per year" is an
  illustration in the discussion, not a modelled case.
- Abstract: "156 MT with 60 humanoid robots, or as high as 40,000 MT with as many as 100,000 humanoid
  robots". Fig. 2 shows about 23,100 t (and, as read by eye in the docking, about 47,000 robonauts) at Gen 6.0 for the max case. Still
  unresolved (docking.md 7 item 5).
- p. 8-9: local chips from Gen 5.0, "adequate for 'appropriate technology'", lacking Earth's
  transistor density; leading-edge parity is "not modeled here".

## Re-digitization of Fig. 2

The by-eye reading (docking, 2026-10-21) was redone from the figure's embedded 781 x 477 raster by
marker detection (`digitize_fig2.py`; output `fig2_digitized.json`). Axis: six decade gridlines,
68.4 px per decade, so one pixel is 3.4%. Check: the reduced case ends at 150.8 t against the
abstract's 156 t (one pixel).

| generation | 1.0 | 2.0 | 2.5 | 3.0 | 4.0 | 5.0 | 6.0 |
|---|---|---|---|---|---|---|---|
| max case, pixels (t) | 7.2 | 39.9 | 214.7 | 421.0 | 1367.6 | 6434 | 23123 |
| max case, by eye (t) | 6.9 | 41 | 219 | 434 | 1440 | 6600 | 23500 |
| reduced case, pixels (t) | 7.2 | 20.0 | 71.9 | 82.3 | 58.7 | 190.9 | 150.8 |
| reduced case, by eye (t) | 6.9 | 20 | 71 | 83 | 60 | 192 | 154 |

All by-eye values are within 5% of the pixel values, so the docking's ±15% was conservative.

| rate (ln per year) | pixels | by eye |
|---|---|---|
| max case, Gen 1.0 to 6.0 (fit) | 0.647 (doubling 1.07 yr) | 0.651 |
| max case, Gen 4.0 to 6.0 (fit) | 0.707 | 0.698 |
| max case, per interval | 0.86, 0.84, 0.34, 0.59, 0.77, 0.64 | |
| reduced case plateau, Gen 2.5 to 5.0 | 0.130 | 0.133 |

Mass grows about 3.65x per 2-year generation in the max case. The docking's numbers stand.

## Correction to the growth-rate citation

`PARAMS["g"]` said "doubling ~2 yr; Metzger et al. 2013". That is wrong in two ways:

1. The 2 years in Metzger is generation spacing, not a doubling time (`CV-NO-GENSPACING-AS-DOUBLING`
   in `conversions.yaml` now forbids that reading).
2. g = 0.35 is not a Metzger number at all. His modelled max case grows at about 0.65/yr; g is about
   half of that. His model covers 7 t to about 23,000 t, which is 2e-9 to 6e-6 Earth-industry units
   under the docking's energy bridge (itself a scenario, `CV-METZGER-T-TO-EIU`), while the pact starts
   at A0 = 1e-3 and closes at 0.1. Carrying his rate over is a scale extrapolation with no identified
   mechanism (`CV-METZGER-RATE-TO-G`, unidentified).

Changes made: the PARAMS basis text now says "Project assumption (doubling ~2 yr). Not from Metzger
et al. 2013, whose 2-yr figure is generation spacing; their max-rate case grows ~0.65/yr at far smaller
scale". The role of `g` in `assumptions.yaml` changes from `source_model_assumption` to
`project_assumption` (role counts in `docs/evidence-protocol.md` updated); AS-GROWTH-G and AS-GCITE
keep their Metzger evidence links as a comparison. The swept range 0.07 to 0.69/yr is unchanged and
remains the bounded scenario in use; Metzger's 0.65 sits near its top. No model output changes: only
a description string changed.

## Conversion uncertainty, kept separate

- Digitization: about ±3.4% per point (one pixel); rate fits move by less than 0.01/yr.
- Source model form: not quantified by the source (printer speed "a high estimate").
- Energy bridge to Earth-industry units: `CV-EIU-TO-PRIMARY-POWER` (18.8 to 19.7 TW per EIU across
  two Energy Institute editions, read only in secondary summaries) and `CV-METZGER-T-TO-EIU` (2.51e-10
  EIU per tonne from Gen 5.0's energy per tonne, used with a factor-10 scenario band each way and never
  coupled into the solver).
