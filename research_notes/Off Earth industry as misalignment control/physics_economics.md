# Physics and economics of off-Earth vs Earth industry (energy, heat, gravity well, materials, growth)

Research notes, compiled 2026-10-16. All arithmetic is shown inline so it can be checked; constants are from NASA fact sheets unless stated. Labels used: **[consensus]** = textbook physics or broadly agreed engineering; **[modelled]** = a published model or company projection; **[speculative]** = long-horizon extrapolation; **[my calc]** = my own arithmetic from cited inputs.

## 1. Energy: how much better is sunlight off Earth, and do Earth's non-solar sources erase the gap?

### Takeaway
Per square metre of collector, a near-continuously lit orbit yields roughly 5 to 10 times the annual energy of a good-to-average ground site (Google says "up to 8x"; Forethought models 3 to 5x vs a strong terrestrial site). At the scale that matters for a machine civilization the gap is far larger: Earth intercepts only about 4.5e-10 of the Sun's output, and humanity uses about 19 TW, roughly 5e-14 of it. Fission/fusion remove Earth's *fuel* limit but not its *heat-rejection* limit: a planet can only radiate so much, which caps Earth-based power at roughly 1e17 W even for a civilization that does not care about the biosphere.

### Cited Findings
- Solar luminosity 3.828e26 W; solar constant at 1 AU 1361 W/m² — [NASA Sun fact sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/sunfact.html); [NASA Earth fact sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html). **[consensus]**
- Mercury's mean solar irradiance is about 9,083 W/m², 6.67 times Earth's — [NASA Mercury fact sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/mercuryfact.html). **[consensus]**
- Global-mean solar radiation absorbed at Earth's surface is about 161 W/m² (of 341 W/m² incident at top of atmosphere, averaged over the sphere) — [Trenberth, Fasullo & Kiehl 2009, BAMS](https://doi.org/10.1175/2008BAMS2634.1). **[consensus]**
- World primary energy in 2024 was 592 EJ (Energy Institute Statistical Review 2025, 74th ed.); the 2026 edition reports total energy supply above 600 EJ in 2025 (+1.7%). The 2025 edition changed methodology to total energy supply, so cross-edition comparisons are not exact — [DieselNet summary of 2025 Review](https://dieselnet.com/news/2025/06energyreview.php); [DieselNet on 2026 Review](https://dieselnet.com/news/2026/07energyreview.php). **[consensus]**
- Google Research (Project Suncatcher, Nov 2025): "in the right orbit, a solar panel can be up to 8 times more productive than on Earth", using a dawn-dusk sun-synchronous LEO with near-constant sunlight; Google also notes the Sun emits more than 100 trillion times humanity's total electricity production — [Google Research blog](https://research.google/blog/exploring-a-space-based-scalable-ai-infrastructure-system-design/). **[modelled]**
- Forethought (Parrack & Moorhouse, 22 May 2026) assumes 95% capacity factor in dawn-dusk SSO vs 28% (Baseline A) and 32% (Baseline B) for terrestrial off-grid solar sites, giving roughly 3 to 5 times the energy of an equivalent terrestrial site; it also assumes 8%/yr panel degradation in orbit over a 5-year life — [Forethought](https://www.forethought.org/research/will-we-really-put-data-centers-in-space). **[modelled]**
- Forethought's terrestrial off-grid baselines for always-on data-center power: 100% renewable with batteries about $20,307 per kW-continuous (LCOE $463/MWh, batteries ~69% of cost); solar plus gas about $5,590/kW (LCOE $128/MWh). Space solar reaches parity with present-day off-grid terrestrial power at about $250/kg launch, and becomes cheaper than any current terrestrial source (about $25 to 45/MWh) at about $50/kg — [Forethought](https://www.forethought.org/research/will-we-really-put-data-centers-in-space). **[modelled]**
- Lunar surface solar: Metzger et al. assume a polar site gives power for about 70% of a lunation, but equatorial sites only about 40%, and show industry growth is very sensitive to this duty cycle — [Metzger et al. 2013, arXiv:1612.03238](https://arxiv.org/abs/1612.03238). **[modelled]**
- Waste heat: Chaisson (Eos 2008) argued that waste heat from any non-solar energy source could, with ~2%/yr growth, produce ~3 °C of warming on a timescale of a few centuries (one secondary summary: ~8 doublings, ~280 years) independent of greenhouse gases; critics note the projection assumes continued inefficiency and long extrapolation — [Chaisson 2008, Harvard DASH](https://dash.harvard.edu/entities/publication/73120379-1f27-6bd4-e053-0100007fdf3b); [Buchanan commentary](https://markbuchanan.substack.com/p/the-second-warming-problem-finally). **[speculative for the long-run number; the physics is consensus]**
- Current anthropogenic effective radiative forcing (1750 to 2019) is about 2.72 W/m², and best-estimate climate sensitivity is about 3 °C per CO2 doubling (~3.9 W/m²) — [IPCC AR6 WG1](https://www.ipcc.ch/report/ar6/wg1/chapter/summary-for-policymakers/). **[consensus]**

**Calculations [my calc]:**
- Earth's cross-section: π × (6.371e6 m)² = 1.275e14 m². Intercepted sunlight: 1.275e14 × 1361 = **1.735e17 W**. Fraction of Sun: 1.735e17 / 3.828e26 = **4.53e-10**.
- Solar absorbed at the surface: 161 W/m² × 5.10e14 m² = **8.2e16 W**.
- Human primary power: 592 EJ / 3.156e7 s = **18.8 TW (2024)**; ~19.0 TW for 2025. That is 2.3e-4 of surface-absorbed sunlight and 4.9e-14 of the Sun.
- Global-mean anthropogenic waste-heat flux: 18.8e12 W / 5.10e14 m² = **0.037 W/m²**, about 1.4% of today's 2.72 W/m² greenhouse-era forcing. Waste heat alone reaches 1 W/m² at about **510 TW** (27 times today); at ~0.77 K per W/m² that is roughly 0.8 K of extra warming.
- Annual energy per m² of collector: orbit at 99% illumination = 1361 × 8760 × 0.99 = **11,800 kWh/m²/yr** (before cell efficiency). A good desert site receives roughly 2,000 to 2,500 kWh/m²/yr of global horizontal irradiance (ratio ~5x; this site value is from general knowledge, not fetched this session); the global-mean surface value is 161 × 8.76 = 1,410 kWh/m²/yr (ratio ~8x), matching Google's "up to 8x".
- Important nuance: solar energy collected *on* Earth adds almost no net heat (it was going to be absorbed anyway, apart from albedo changes). Only fission, fusion, geothermal and fossil sources add heat. So the climate ceiling bites on non-solar sources.
- **Earth's hard ceiling as a radiator.** Treat the whole surface (5.1e14 m²) as a blackbody (crude; ignores greenhouse effect, so it is an upper bound on what can be radiated at a given surface temperature): σT⁴ × area = 2.3e17 W at 300 K, 4.3e17 W at 350 K, 7.4e17 W at 400 K. Subtract ~1.2e17 W of absorbed sunlight and the most internal (fusion/fission) power Earth can dump is roughly **1e17 W at 300 K to 6e17 W at 400 K**. That is about 5,000 to 30,000 times today's human use, but only about 1e-9 of solar output. Fusion therefore does not erase the solar argument at civilizational scale; it moves Earth's ceiling from "sunlight on the surface" (~1e17 W) to "what the planet can radiate" (also ~1e17 W).

### Inferences
- The energy advantage of space is modest (5 to 10x) per panel but astronomical (~1e9x) in total available power. For a near-term AI the first number matters; for a long-horizon maximizer the second dominates.
- Fusion on Earth would let a civilization reach perhaps 1e15 to 1e16 W before waste heat makes Earth much hotter, and ~1e17 W before it becomes hostile even to machines. Inference: an AI expecting fusion would still find Earth's ceiling ~9 orders of magnitude below the Sun's output.
- What would show this wrong: if radiator mass in space proved so high that delivered compute per kg of launched or space-made hardware never beat Earth (see section 2), the space energy advantage would not translate into a compute advantage.

### Gaps
- I did not fetch a primary source for ground-site irradiance (e.g., NREL/Global Solar Atlas) or for US utility-PV capacity factors (EIA ~24%); the ~2,000 to 2,500 kWh/m²/yr desert value above is from general knowledge.
- I did not find the W/m² figure in Chaisson's paper itself.

## 2. Heat rejection: the strongest physical counterargument

### Takeaway
In vacuum all waste heat must be radiated. At chip-friendly temperatures (20 to 80 °C) a two-sided radiator rejects only about 0.6 to 1.5 kW per m², so a 1 MW compute module needs roughly 650 to 2,500 m² of radiator. With ISS-era hardware (~13 W/kg) that is ~77 tonnes per MW, which would sink orbital compute; with proposed lightweight designs (90 to 350 W/kg) it falls to 3 to 11 t/MW. Earth cools 1 MW by evaporating about 38 m³ of water a day, at a cost of ~7 to 10% of electricity. Radiator mass is the single biggest disputed parameter in the orbital-compute case.

### Cited Findings
- WEF (June 2026), using Starcloud's white-paper figures: a two-sided radiator at ~20 °C emits roughly 633 W/m², so 1 MW needs about 1,600 m²; scaling ISS-style hardware to 1 MW implies ~100 t of radiators vs ~10 t of compute racks — [WEF](https://www.weforum.org/stories/2026/06/space-data-centres-cooling/). **[modelled]**
- IEEE Spectrum: thermal-coating degradation may require at least 40% more radiator area, and radiators plus solar arrays can be 65 to 70% of satellite mass — [IEEE Spectrum](https://spectrum.ieee.org/orbital-data-centers-heat). **[modelled]**
- Forethought: ISS-era radiators ~13 W/kg; proposed system-level designs 163 to 346 W/kg; Hi-K composite tests suggest ~90 W/kg. Running coolant at 25 to 45 °C raises heat rejection per m² 2.7 to 3.5x. Radiators modelled as 8% (median) to 14% (conservative) of system mass, up to 60% in pessimistic cases, and only 2 to 5% of total cost. Worst case (ISS radiators at $250/kg launch) adds >$8B per GW, vs ~$3B/GW for terrestrial cooling. Google and Meta spend ~7 to 10% of electricity and 15 to 20% of facility capex on cooling — [Forethought](https://www.forethought.org/research/will-we-really-put-data-centers-in-space). **[modelled]**
- Turyshev (arXiv:2604.27197, Apr 2026): a 1 MW IT orbital data center needs ~2.5e3 m² of radiator and ~5.6e3 m² of PV; PV + storage + radiator ≈ 29.4 kg/kW, and with fixed spacecraft mass the total is 34 to 59 kg/kW — [arXiv:2604.27197](https://arxiv.org/abs/2604.27197). **[modelled]**
- SpaceComputer (vendor blog): radiative rejection is "brutal" at gigawatt scale but a manageable trade at ~100 kW; flight data suggest power delivery, not cooling, currently throttles compute in orbit — [SpaceComputer blog](https://blog.spacecomputer.io/orbital-data-center-cooling-vs-power/). **[vendor opinion]**

**Calculations [my calc]** (Stefan–Boltzmann, emissivity 0.9, ignoring absorbed Earth IR/albedo and sunlight, so these are optimistic):
| Radiator temp | W/m² per side | m² per MW (two-sided) |
|---|---|---|
| 293 K (20 °C) | 376 | 1,330 |
| 300 K (27 °C) | 413 | 1,210 |
| 330 K (57 °C) | 605 | 830 |
| 350 K (77 °C) | 766 | 650 |
| 400 K (127 °C) | 1,306 | 380 |
| 500 K (227 °C) | 3,189 | 160 |
- Radiator mass per MW: 13 W/kg → 77 t; 90 W/kg → 11 t; 163 W/kg → 6.1 t; 346 W/kg → 2.9 t.
- Earth comparison: evaporating water (latent heat 2.26 MJ/kg) removes 1 MW with 0.44 kg/s ≈ 38 m³/day; an air or water loop needs no mass delivered to orbit at all.
- Because radiated power scales with T⁴, hotter-running hardware (e.g., power electronics, smelters, wide-bandgap chips) benefits enormously: going from 300 K to 500 K cuts radiator area ~7.7x. Industrial processes that run hot (metal refining) are far less radiator-limited than ~300 K silicon.

### Inferences
- Heat rejection does not refute the off-Earth case, but it converts it from "free energy" to "energy at the cost of ~1 to 10 t of radiator per MW". Whether that is cheap depends on whether radiators are launched from Earth (expensive) or made in space from aluminium/regolith (potentially cheap; see section 4).
- A machine civilization optimizing for space would likely redesign compute to run hotter. That is an inference, not something any cited source demonstrates.
- Earth retains a real advantage here: a free, massive convective/evaporative heat sink. This is the strongest physics argument for Earth-based compute at small-to-medium scale.

### Gaps
- No flight-proven deployable radiator at the ~MW scale exists yet; all specific-power numbers above 13 W/kg are projections.

## 3. Gravity well and launch cost

### Takeaway
Earth's gravity well is about 22 times deeper than the Moon's in energy terms (62.6 vs 2.8 MJ/kg to escape), and the rocket equation turns the ~9.4 km/s to LEO into a propellant mass ratio of ~8 to 16. Yet the *energy* to reach LEO is only ~9.5 kWh/kg (under $1 of electricity), so launch cost is a vehicle-reuse problem, not an energy problem. Launch prices have fallen from ~$10,000/kg (c. 2009 to 2011) to ~$1,500 to 3,400/kg today, and credible models put fully reused Starship at ~$100/kg or below in the 2030s. Even so, lifting enough hardware to exceed Earth's 19 TW from Earth alone would take millions of launches; off-Earth manufacturing is required for that crossover.

### Cited Findings
- Escape velocities: Earth 11.19 km/s, Moon 2.38 km/s, Mercury 4.25 km/s — [NASA Earth](https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html), [Moon](https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html), [Mercury](https://nssdc.gsfc.nasa.gov/planetary/factsheet/mercuryfact.html) fact sheets. **[consensus]**
- Metzger et al. (2013): launch to LEO was "typically on the order of $10,000" per kg (citing FAA 2009, Perez 2011); landing 1 kg near the lunar poles needs about 4 kg in LEO; so a 100 t lunar seed replicator would have cost ~$4B in LEO launch alone, and a 12 t seed ~$0.5B — [Metzger et al., arXiv:1612.03238](https://arxiv.org/abs/1612.03238). **[modelled, 2013 prices]**
- Falcon 9's published price is $74M for up to ~22,000 kg to LEO; Turyshev calculates that orbital data centers need combined launch-plus-build cost of $250 to 1,000/kg to compete with terrestrial benchmarks of $10k to $40k per kW, 3.4 to 13.5 times below the Falcon 9 dedicated launch price alone — [arXiv:2604.27197](https://arxiv.org/abs/2604.27197). **[modelled]**
- Forethought uses ~$1,500/kg as present-day launch cost and models Starship $/kg by reuse level: expendable ~$475; booster reuse ~$228; early full reuse ~$93; Falcon-like ~$51; better-than-Falcon ~$32; bullish ~$19; practical floor ~$10 to 13/kg. Orbital data centers reach cost parity with terrestrial at ~$100/kg (median). The FAA cap of 145 Starship launches/yr equals only ~0.5 GW/yr of orbital compute — [Forethought](https://www.forethought.org/research/will-we-really-put-data-centers-in-space). **[modelled]**
- Google projects launch prices may fall below $200/kg by the mid-2030s on a sustained learning curve, at which point launch plus operation could be roughly comparable to terrestrial data-center energy costs per kW-year — [Google Research](https://research.google/blog/exploring-a-space-based-scalable-ai-infrastructure-system-design/); [arXiv:2511.19468](https://arxiv.org/abs/2511.19468). **[modelled]**

**Calculations [my calc]:**
- Specific energy to escape (GM/R): Earth 62.6 MJ/kg; Mercury 9.0 MJ/kg; Moon 2.8 MJ/kg (Earth/Moon ratio ≈ 22).
- Specific energy of a 400 km orbit: ½(7.8 km/s)² + g·h ≈ 34 MJ/kg ≈ **9.5 kWh/kg**. At $0.05 to 0.10/kWh that is $0.50 to 0.95 per kg; even at 1% end-to-end efficiency it is <$100/kg. The cost floor is set by vehicle hardware and propellant logistics, not physics.
- Rocket equation, Δv 9.4 km/s: mass ratio 15.5 at Isp 350 s, 8.4 at Isp 450 s. From the Moon (Δv ~2.4 km/s): 2.0 and 1.7. A lunar mass driver uses electricity and no propellant at all.
- Falcon 9 list: $74M / 22,000 kg ≈ **$3,360/kg**.
- **Launching Earth-scale power from Earth:** 19 TW × 40 kg/kW (Turyshev's mid-range) = 7.6e11 kg (760 Mt). At 150 t per Starship that is **~5 million launches**: about 500 years at 10,000 launches/yr (Forethought's 2028 fast scenario), 50 years at 100,000/yr. The orbital energy for that mass (7.6e11 kg × 34 MJ/kg = 2.6e19 J) is only ~4% of one year of world primary energy, so energy is not the limit; launch cadence and manufacturing are.

### Inferences
- The gravity well is a near-term cost wall (launch is still ~$1,500 to 3,400/kg) but not a fundamental one; reusability has already cut prices several-fold since 2013 and models point to another 10 to 100x.
- Exceeding Earth's total energy use *off-Earth* is not plausible by launching hardware from Earth. It needs lunar/asteroid manufacturing, where the ~22x shallower well and propellant-free mass drivers matter. This is the actual crossover mechanism.

### Gaps
- No independent audit of SpaceX's internal Falcon 9 or Starship marginal costs; the $1,500/kg "present" figure is Forethought's assumption.
- Lunar mass-driver cost and throughput: no recent primary source fetched this session.

## 4. Materials and self-replicating industry

### Takeaway
Earth's decisive advantage is concentrated feedstock: ores enriched by hydrothermal and biological processes, abundant liquid water, and an atmosphere usable as chemical feedstock and coolant. Off-Earth materials are vast but dilute or unprocessed. The serious literature argues this can be overcome by self-replicating or "bootstrapping" industry: Metzger et al. (2013) model a lunar industry seeded with ~12 t landed over ~20 years that grows to 156 t (or up to 40,000 t with 41 t launched), then grows ~3x per year. These are models, not demonstrations; no closed-loop space factory has flown.

### Cited Findings
- Metzger, Muscatello, Mueller & Mantovani (J. Aerospace Eng. 2013): bootstrapping "can be achieved with as little as 12 metric tons (MT) landed on the Moon during a period of about 20 years"; end-of-bootstrap assets 156 t with 60 humanoid robots, or up to 40,000 t with 100,000 robots if 41 t total is launched; "within another few decades with no further investment, it can have millions of times the industrial capacity of the United States" — [arXiv:1612.03238](https://arxiv.org/abs/1612.03238). **[modelled/speculative]**
- Same paper: the industry starts sub-replicating and evolves toward full closure via a technology spiral; successive generations target 90%, 95%, 99% and 100% local manufacture of electronics; generation lengths ~2 years at baseline; a 300 kg printer at 0.1 kg/h and 70% duty cycle has a "specific reproduction" time of ~3 months, but with a crudeness factor of 2.5, Gen 1.0 takes 7.5 months to make Gen 2.0 even in the limit of many printers — [arXiv:1612.03238](https://arxiv.org/abs/1612.03238). **[modelled]**
- Same paper, on prior work: the NASA 1980 study used a straw-man self-replicator of 100 t (including 12 t of paving robots and 4.4 t of mining robots), and Freitas & Zachary (1981) also used 100 t per replica — [arXiv:1612.03238](https://arxiv.org/abs/1612.03238); original study: [NASA CP-2255, Advanced Automation for Space Missions (1980/1982)](https://ntrs.nasa.gov/citations/19830007077). Freitas & Merkle's survey of the field: [Kinematic Self-Replicating Machines (2004)](http://www.molecularassembler.com/KSRM.htm). **[historic models]**
- Same paper: the asteroid belt "has everything necessary": water, carbon, silicates, metals, oxygen; lunar polar ices are limited so industry should move to asteroids quickly — [arXiv:1612.03238](https://arxiv.org/abs/1612.03238). **[modelled]**
- Planet masses: Earth 5.97e24 kg, Mercury 3.30e23 kg, Moon 7.35e22 kg — NASA fact sheets ([Earth](https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html), [Mercury](https://nssdc.gsfc.nasa.gov/planetary/factsheet/mercuryfact.html), [Moon](https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html)). **[consensus]**

**Calculations [my calc]:**
- Gravitational binding energy (uniform-sphere approximation, 3GM²/5R): Mercury ≈ 1.8e30 J; Earth ≈ 2.2e32 J. At full solar output (3.8e26 W), unbinding Mercury costs ~1.3 hours of the Sun's output; Earth ~6.8 days. Earth is ~18x Mercury's mass but ~125x harder to unbind.

### Inferences
- Earth's material advantages (concentrated ores, water, air, existing refineries and fabs) are decisive during bootstrap and especially for semiconductors, which need extreme purity and complex supply chains. Space advantages (no weather, vacuum processing, unlimited area, sunlight) dominate once closure is achieved.
- The hardest step is semiconductor closure. Metzger's model defers it by importing electronics from Earth for several generations. That dependency is exactly why Earth's industry matters most early (section 8).
- Long run: Earth is the largest rocky body in the inner Solar System. A civilization that disassembles planets for mass would eventually find Earth valuable as material, despite its deep well. This cuts against "an AI would simply leave Earth alone." **[speculative]**

### Gaps
- I did not fetch Lewis, *Mining the Sky*, or quantitative regolith/asteroid composition data (e.g., metal fractions in M-type asteroids, lunar ilmenite, polar ice inventories).
- No source found on realistic achieved closure fractions for any real in-situ manufacturing system.

## 5. Radiation, micrometeoroids and hardware lifetime

### Takeaway
At ~550 to 650 km, with modest shielding, commercial AI accelerators appear to survive a 5-year mission. Google's Trillium TPU showed HBM irregularities only after ~2 krad vs an expected ~750 rad, and no hard failures up to 15 krad. Because chips become obsolete in about 5 years anyway, radiation is not the binding constraint in LEO. Higher orbits (~800 km and above) have 10x higher dose. Debris and congestion are growing concerns but not yet showstoppers.

### Cited Findings
- Google tested Trillium v6e TPUs under a 67 MeV proton beam: HBM irregularities appeared after 2 krad(Si), nearly 3x the expected shielded 5-year dose of 750 rad(Si); no hard failures up to 15 krad(Si) on one chip — [Google Research](https://research.google/blog/exploring-a-space-based-scalable-ai-infrastructure-system-design/). **[measured, small sample]**
- Forethought: dose ~150 rad/yr at 550 km, ~50 rad/yr at 400 km, ~1 to 2 krad/yr at 800 km; 20 mm shielding costs ~$100k at $250/kg vs ~$9M of chips; annualized compute loss modelled at ~9%/yr (from Meta's observed terrestrial failure rate), ~38% over 5 years; effective module life ~5 years, driven by chip obsolescence; uncorrectable memory errors ~0.01 to 0.1 per GPU-year — [Forethought](https://www.forethought.org/research/will-we-really-put-data-centers-in-space). **[modelled]**
- Starlink: zero confirmed debris failures over ~27,000 satellite-years; ~35 to 40 avoidance manoeuvres per satellite per year — [Forethought](https://www.forethought.org/research/will-we-really-put-data-centers-in-space). **[reported]**
- An Nvidia A6000 GPU failed during the Starcloud-1 launch; an H100 operated in orbit — [Dealroom](https://app.dealroom.co/news/note/you-can-just-do-things-building-ai-data-centres-in-orbit). **[reported]**

### Inferences
- On Earth, failed hardware is swapped by technicians; in orbit it is written off. That favors Earth for anything needing maintenance until robotic servicing exists. For an AI with capable robots, this advantage shrinks.
- Earth's atmosphere and magnetosphere are free shielding. Off LEO (cislunar, asteroid belt, Mercury) dose rises sharply, so deep-space industry needs either shielding mass (cheap if made locally) or rad-hard designs.

### Gaps
- No fleet-scale in-orbit failure data for AI accelerators; all evidence is small-sample.

## 6. Current orbital-compute efforts as evidence (as of Oct 2026)

### Takeaway
Serious capital is now flowing (Google, SpaceX/xAI, Starcloud, China), but deployed orbital compute is still at the kilowatt-to-small-cluster scale. Company economics rely on launch costs of $40 to 200/kg that do not yet exist. Independent analyses (Turyshev; Forethought; IEEE Spectrum; WEF) conclude it is technically feasible but not yet competitive. Forethought expects it to be a negligible share before 2030 but possibly most *new* compute in the 2030s.

### Cited Findings
- **Google Project Suncatcher** (announced 4 Nov 2025; paper arXiv:2511.19468, v2 June 2026): 81-satellite clusters within ~1 km radius at ~650 km in dawn-dusk SSO; bench demo of 800 Gbps each way (1.6 Tbps) optical inter-satellite link; two prototype satellites with Planet "by early 2027" — [Google Research](https://research.google/blog/exploring-a-space-based-scalable-ai-infrastructure-system-design/); [arXiv:2511.19468](https://arxiv.org/abs/2511.19468). One secondary report says a first 4-TPU test satellite was to launch 1 Oct 2026 on Transporter-18; I could not confirm it launched — [AI Weekly](https://aiweekly.co/node/15602) (conflicts with Google's "early 2027" wording; unverified).
- **Starcloud**: white paper claims a 40 MW cluster costs ~$167M over 10 years on Earth (mostly $140M of energy at $0.04/kWh) vs ~$8.2M in orbit, assuming a single launch at ~$39/kg. Critics note it excludes common costs (servers, enclosures) and that the hardware would need up to ~22 launches, not one — [Blocks & Files](https://www.blocksandfiles.com/architecture/2025/10/23/starcloud-pitches-orbital-datacenters-as-cheaper-cooler-and-cleaner/1597295); [Feedbagel analysis](https://feedbagel.com/post/feasibility-analysis-of-starclouds-82-million-space-data-centre-in-one-starship-). Starcloud-1 (Nov 2025) flew an H100 and trained a small NanoGPT model and ran Gemma in orbit; Starcloud-2 was planned for Oct 2026; an Aug 2026 round of $250M at a $2.3B valuation targets an 88,000-satellite, 20 GW constellation — [Dealroom](https://app.dealroom.co/news/note/you-can-just-do-things-building-ai-data-centres-in-orbit); [W.Media](https://w.media/starcloud-plans-to-scale-data-centers-in-space-at-us-2-3-billion-valuation/). **[company claims]**
- **SpaceX/xAI**: FCC filing on 30 Jan 2026 for up to 1 million satellites at ~500 to 2,000 km for solar-powered orbital data centers, with few cost or schedule details; filed amid reported SpaceX–xAI merger talks — [Engadget](https://www.engadget.com/science/space/spacex-wants-to-launch-a-constellation-of-a-million-satellites-to-power-ai-needs-175607771.html); [Fortune](https://www.fortune.com/2026/02/01/spacex-fcc-approval-filing-data-center-constellation-space-construction-ai). Musk has said space will be the lowest-cost AI compute within "two years, maybe three"; Forethought adjusts that to 3 to 5 years — [Forethought](https://www.forethought.org/research/will-we-really-put-data-centers-in-space). **[company claims]**
- **China "Three-Body Computing Constellation"** (Zhejiang Lab + ADA Space): first 12 satellites launched 14 May 2025 on a Long March 2D; planned 2,800 satellites; target 1,000 POPS, with the first 12 rated ~5 POPS; up to 100 Gbps laser links — [Live Science](https://www.livescience.com/space/space-exploration/china-is-building-a-constellation-of-ai-supercomputers-in-space-and-just-launched-the-first-pieces). **[official claims, unverified]**
- **Forethought scenarios**: slow, ~4 GW of orbital compute in 2031; fast, up to 100 GW by end-2030 (needs rapid reuse by 2027 and 10,000+ launches in 2028); vs ~100 GW terrestrial buildout forecast by 2030. Chip production, not launch, is likely the eventual bottleneck. Per-GW 5-year cost: Earth grid $37.6B; orbital $48.2B at $250/kg, $35.0B at $100/kg, $30.3B at $50/kg — [Forethought](https://www.forethought.org/research/will-we-really-put-data-centers-in-space). **[modelled]**
- **Turyshev**: credible early uses are space-native preprocessing and comms-integrated edge compute; general compute for Earth users works only with low communication intensity, high utilization, long life and very low launch-plus-build cost — [arXiv:2604.27197](https://arxiv.org/abs/2604.27197). **[modelled]**

### Inferences
- The market is treating orbit as an *energy and permitting* escape valve for terrestrial compute, not yet as industry. That is consistent with the user's hypothesis but at a ~5x energy advantage, not ~1e9x.
- The current wave still depends entirely on Earth's industrial base (chips, launch vehicles, solar cells). It is evidence that the off-Earth step starts from Earth.

### Gaps
- Blue Origin and Aetherflux orbital-compute plans: not found in this session's searches.
- Status of Starcloud-2 and Suncatcher prototype launches as of mid-Oct 2026: unconfirmed.

## 7. Growth dynamics: when could off-Earth energy exceed Earth's?

### Takeaway
Crossover is a matter of doublings, and doubling time depends on whether growth is launch-limited (Earth-fed) or self-replicating (space-fed). From a plausible ~4 GW of orbital power in the early 2030s, off-Earth capacity needs ~12 doublings to exceed humanity's 19 TW, ~24 to exceed all sunlight absorbed by Earth's surface, and ~56 to capture the whole Sun. Launch-limited growth probably cannot get there in under a century. Self-replicating industry with 0.5 to 2 year doubling times could pass Earth's total energy use in ~6 to 25 years after closure and Earth's total sunlight within a few decades. These are speculative extrapolations.

### Cited Findings
- Metzger et al.: a Gen 5.0 lunar industry using 1e15 J/yr, growing 3x per year, would exceed total US energy use (1e20 J/yr) within 11 more years, exceed it a million-fold 12 years later, and a billion-fold a decade after that — [arXiv:1612.03238](https://arxiv.org/abs/1612.03238). **[speculative]**
- Armstrong & Sandberg ("Eternity in six hours", Acta Astronautica 2013), per secondary summaries: Mercury disassembled with collectors of ~1/3 efficiency, 1/10 of energy used to launch material, half of Mercury's mass used, 5-year processing cycles, seeded by ~1 km² of panels; Mercury disassembled in ~31 years, with most mass harvested in the last ~4 years — [LessWrong summary (2022)](https://www.lesswrong.com/posts/DvQ7cYxhnrZtWngvW/how-to-take-over-the-universe-in-three-easy-steps). Commentators argue the 5-year cycle is deliberately conservative — [Manifold discussion](https://manifold.markets/IsaacKing/will-the-moon-still-exist-on-march). **[speculative; primary not fetched]**
- Forethought: Earth-launched orbital compute ~4 GW (slow) to ~100 GW (fast) by ~2030 to 2031; FAA cap of 145 Starship launches/yr ≈ 0.5 GW/yr — [Forethought](https://www.forethought.org/research/will-we-really-put-data-centers-in-space). **[modelled]**

**Calculations [my calc]:**
- Metzger's 1e15 J/yr = 31.7 MW. 3x/yr = doubling time ln2/ln3 = 0.63 yr. 1e15 × 3¹¹ = 1.8e20 J/yr ≈ 5.6 TW, consistent with "exceeds US" (~1e20 J/yr ≈ 3.2 TW) in 11 years.
- Doublings needed from a 4 GW start: to 18.8 TW (world primary) **12.2**; to 8.2e16 W (surface sunlight) **24.3**; to 1.7e17 W (all sunlight Earth intercepts) **25.4**; to 3.8e26 W (Sun) **56.4**. From 100 GW: 7.6, 19.6, 20.7, 51.8.
- Time to exceed world energy from 4 GW: 12.2 doublings × T_d. T_d = 0.63 yr (Metzger) → ~8 yr; 1 yr → ~12 yr; 2 yr → ~24 yr. To exceed Earth's intercepted sunlight: 25.4 × T_d → ~16, 25 or 51 yr.
- Launch-limited path: section 3 shows ~5 million Starship launches to put 19 TW of Earth-built hardware in orbit; Earth-fed growth is linear in launch cadence, not exponential.
- Plausible window [speculative]: if lunar/asteroid closure arrives in the 2040s to 2050s, off-Earth energy could pass Earth's total in the 2050s to 2070s and Earth's total sunlight before ~2100. Under faster AI-driven timelines (month-scale doublings) both thresholds could be crossed within a few years of closure.

### Inferences
- The crossover date is dominated by *when closure happens*, not by doubling time once it starts: after closure, the difference between 0.5-year and 2-year doublings is decades, but before closure growth is pinned to Earth launch.
- What would show this wrong: if closure of semiconductor fabrication off-Earth proves infeasible for decades, off-Earth growth stays Earth-fed and roughly linear, and Earth stays dominant far longer.

### Gaps
- Armstrong & Sandberg primary paper not fetched (FHI site unreachable); figures above come from secondary summaries.
- No empirical doubling time exists for any self-replicating macroscopic factory; all values are assumptions.

## 8. Bootstrap phase: how much is Earth's industry worth to an expanding AI, early vs late?

### Takeaway
In exponential growth, a head start in seed size is worth log₂(size ratio) × doubling time. Earth's ~19 TW industrial base is ~600,000 times a Metzger-scale 32 MW lunar industry, worth ~19 doublings: ~12 years at 0.63-year doubling, ~1.6 years at month-scale doubling. Earth's leverage is therefore large early and shrinks toward negligible (~1e-9 of Solar System energy) once off-Earth industry is self-sustaining. Earth's value as a launch pad, chip fab and seed persists until off-Earth semiconductor closure.

### Cited Findings
- Metzger et al. rely on Earth for electronics through several generations (90% → 100% local electronics only by later generations) and on teleoperation from Earth early on — [arXiv:1612.03238](https://arxiv.org/abs/1612.03238). **[modelled]**
- Forethought: chip production, not launch, is the likely eventual bottleneck for orbital compute — [Forethought](https://www.forethought.org/research/will-we-really-put-data-centers-in-space). **[modelled]**
- All current orbital compute (Starcloud, Suncatcher, Three-Body) uses Earth-made chips and Earth-launched hardware — sources in section 6.

**Calculations [my calc]:**
- Head start in doublings: log₂(19e12 W / 31.7e6 W) = log₂(6.0e5) = **19.2 doublings**. Time-equivalent: 12 yr (T_d 0.63 yr), 19 yr (1 yr), 1.6 yr (1 month).
- Other ratios: seed 1,000x larger → 10 doublings; 1e5x → 16.6; 1e8x → 26.6.
- Long-run value of Earth: its energy share is ≤4.5e-10 of solar output (intercepted sunlight) or ~1e-9 even with fusion run to the planet's radiative limit (section 1). Its mass share is non-trivial for the inner Solar System (Earth ≈ 18x Mercury).

### Inferences
- **Early (pre-closure):** Earth is the *only* place to make advanced chips, launch vehicles and solar cells. An AI seeking off-Earth expansion gains most by *using* Earth's industry (cooperatively or not) during this phase. Physics does not make Earth irrelevant in the bootstrap; it makes Earth the bottleneck input.
- **Late (post-closure):** Earth is worth ~1e-9 of available energy and a modest fraction of inner-system mass. Seizing it buys at most a few doublings of head start, which at month-scale doubling is weeks to months. Inference: a late-stage expander would gain little energetically from seizing Earth. But it would also lose little by doing so, so the decision would turn on non-physical factors: conflict cost, human interference risk, goal content.
- The user's hypothesis is strongest for the late phase and weakest for the bootstrap phase, which is exactly when a misaligned AI would have to decide how to treat humans.

### Gaps
- No source quantifies the cost of conflict vs cooperation for an AI during bootstrap; this is outside physics and depends on strategic modelling (likely covered by other researchers).

## 9. Overall verdict: is off-Earth so much more compelling that a capable AI would prefer expanding off-Earth over seizing Earth?

### Takeaway
On long-run physics the user is right by a huge margin: ~1e9x more energy, shallower wells, unlimited area, no biosphere constraint. Even fusion cannot lift Earth past ~1e17 W because the planet can only radiate so much. In the near term (now to roughly the 2040s) Earth dominates on materials, chip fabs, cooling, maintenance and existing industry, and orbit offers only ~5 to 10x better sunlight at a heavy radiator-and-launch penalty. The crossover is gated by off-Earth manufacturing closure, especially semiconductors, not by energy. So a capable AI's incentive to control Earth's industry peaks during the bootstrap phase and decays afterward. "Off-Earth is better" does not imply "leave Earth alone early."

### Cited Findings
- Off-Earth energy advantage per panel ~3 to 8x — [Google Research](https://research.google/blog/exploring-a-space-based-scalable-ai-infrastructure-system-design/); [Forethought](https://www.forethought.org/research/will-we-really-put-data-centers-in-space).
- Orbital compute is not yet cost-competitive and needs ≤$100 to 200/kg launch — [Forethought](https://www.forethought.org/research/will-we-really-put-data-centers-in-space); [arXiv:2604.27197](https://arxiv.org/abs/2604.27197); [Google](https://research.google/blog/exploring-a-space-based-scalable-ai-infrastructure-system-design/).
- Self-replicating space industry can in principle outgrow Earth within decades of closure — [Metzger et al.](https://arxiv.org/abs/1612.03238) (modelled/speculative).

### Inferences
- **Where Earth keeps advantages:** (1) concentrated ores, water, atmosphere; (2) free convective/evaporative cooling (radiators cost ~1 to 10 t/MW in space); (3) the only semiconductor and launch supply chain; (4) shielding and maintainability; (5) low latency to human users (irrelevant to a machine civilization). Advantages 1 and 2 are permanent but shrink in relative importance as scale grows; 3 and 4 are temporary.
- **Crossover timescales (speculative):** orbital compute cost parity ~2030s if launch reaches ~$100/kg; off-Earth energy above 19 TW requires closure plus ~12 doublings (likely 2050s to 2070s on human-paced timelines, potentially years after closure on AI-paced timelines); off-Earth energy above Earth's total sunlight ~13 doublings later.
- **Strongest counterarguments to the hypothesis:** (a) the bootstrap dependency on Earth (section 8); (b) "prefer off-Earth" is not exclusive: a maximizer can do both, and Earth's marginal value, though tiny relative to the Sun, is not zero; (c) eventually Earth is valuable as mass for megastructures; (d) radiator mass and semiconductor closure may delay the crossover by decades.
- **What result would show the "off-Earth dominates" conclusion wrong:** sustained failure to get radiator specific power above ~100 W/kg, *and* failure to close semiconductor manufacturing off-Earth, would keep space growth Earth-fed and linear, leaving Earth the dominant industrial site for a long time.

### Gaps
- No quantitative literature found that directly models an AI's choice between seizing Earth and expanding off-Earth with these physical parameters; the comparison above is my synthesis.
