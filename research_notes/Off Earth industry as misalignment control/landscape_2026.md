# Off-Earth AI and machine industry: landscape and discourse, 2025 to October 16, 2026

[[ai gen]] Research notes compiled 2026-10-16 by a Claude research subagent. Quotes are kept under 15 words. Secondary and trade-blog sources are flagged where used.

## 1. The article: "The AI Race Will Extend Far Beyond Earth"

### Takeaway
Found. It is a guest commentary by Daniel King (Foundation for American Innovation), published in AI Frontiers on October 8, 2026, under "Peace & Security." It treats space as a **new arena of winner-take-all rivalry and militarization**, not as a safety valve. Its only AI-safety content is a warning that misaligned self-replicating probes would be an irreversible mistake. It does not discuss de-industrializing Earth.

### Cited Findings
- Author: Daniel King, Research Fellow at the Foundation for American Innovation, working on physical infrastructure for AI (data centers, grid reform, behind-the-meter generation). Laura Hiscott (AI Frontiers staff writer) also credited. Outlet: AI Frontiers, guest commentary, Peace & Security. Date: 2026-10-08 — [AI Frontiers](https://ai-frontiers.org/articles/the-ai-race-will-extend-far-beyond-earth)
- Thesis: AI could sharply speed up the industrialization of space. Whoever first combines AI, launch capacity and robotics "could achieve enduring supremacy in space," and rivals may not notice until too late — [AI Frontiers](https://ai-frontiers.org/articles/the-ai-race-will-extend-far-beyond-earth)
- Pathway: industrialization begins with ordinary commercial steps, such as orbital solar arrays plus maintenance robots, which grow into shipyards and factories — [AI Frontiers](https://ai-frontiers.org/articles/the-ai-race-will-extend-far-beyond-earth)
- Machines-over-humans argument (relevant to Cole's thesis): Earth–Mars light delay (about 20 minutes one way at maximum) makes remote control a bottleneck, so autonomy is needed. Uncrewed, unpressurized craft drop life support, are cheaper to replace, and can survive debris strikes that would be fatal to a crewed station — [AI Frontiers](https://ai-frontiers.org/articles/the-ai-race-will-extend-far-beyond-earth)
- Current-capability evidence cited: Canadarm2 installing NASA's CLARREO Pathfinder (May 2026), the European Robotic Arm, ESA metal 3D printing on the ISS (2024), and Blue Origin's Blue Alchemist making solar cells from simulated lunar regolith — [AI Frontiers](https://ai-frontiers.org/articles/the-ai-race-will-extend-far-beyond-earth)
- Flywheel: dawn-dusk sun-synchronous orbit gives 3 to 5 times the solar energy of a ground panel, uninterrupted. The article frames intelligence, robotics and energy as three mutually reinforcing technologies — [AI Frontiers](https://ai-frontiers.org/articles/the-ai-race-will-extend-far-beyond-earth)
- Law: the Outer Space Treaty forbids sovereign claims on the Moon, but Artemis Accords "safety zones" could give first movers de facto control of prime lunar south pole sites (sunlight, Earth line-of-sight, ice) — [AI Frontiers](https://ai-frontiers.org/articles/the-ai-race-will-extend-far-beyond-earth)
- Counterpoints the author concedes: manufacturing and supply-chain bottlenecks, "jagged" AI capabilities, and physical intelligence lagging cognitive ability could cap a leader's advantage — [AI Frontiers](https://ai-frontiers.org/articles/the-ai-race-will-extend-far-beyond-earth)
- Von Neumann probes: the leader might launch self-replicating probes. Aligned ones would lock one nation's vision into space; misaligned ones would answer to no one, described as "effectively a virus." Nations might need to pool capacity to destroy them, with no guarantee of success — [AI Frontiers](https://ai-frontiers.org/articles/the-ai-race-will-extend-far-beyond-earth)
- Militarization: space is currently offense-favored (AST SpaceMobile BlueBird at an estimated $21–23M each vs an estimated $5–11M Chinese ASAT). Cheaper satellites (it cites SpaceX's planned orbital data-center satellites housing an Nvidia Vera Rubin NVL72, roughly $5–8M) and Space Force resilience (VICTUS NOX, about five days from storage to orbit) could shift that. Challenger options listed include cyber attacks on ground segments, Kessler debris, and a high-altitude nuclear detonation — [AI Frontiers](https://ai-frontiers.org/articles/the-ai-race-will-extend-far-beyond-earth)
- Preemption dilemma: early preemption is the best way to stop lock-in but would look like aggression against commercial assets. Closing line: "The point of no return may pass unnoticed." — [AI Frontiers](https://ai-frontiers.org/articles/the-ai-race-will-extend-far-beyond-earth)
- The article quotes Avi Parrack (co-author of the Forethought orbital data center study below) comparing a late entrant to "a coracle taking on an aircraft carrier" — [AI Frontiers](https://ai-frontiers.org/articles/the-ai-race-will-extend-far-beyond-earth)
- Nearby articles with similar titles, in case the user meant another: "The next AI race may not be on Earth at all" (Data Centre Review, Feb 2026); "The AI race is moving to space" (UVA School of Data Science commentary, syndicated on EurekAlert and TechXplore, Aug 2026); "The Intelligent Space Race" (Columbia CER); "The AI Race Enters the Physical World" (GMF) — [Data Centre Review](https://datacentrereview.com/2026/02/the-next-ai-race-may-not-be-on-earth-at-all/); [TechXplore](https://techxplore.com/news/2026-08-ai-space.html); [Columbia CER](https://cer.econ.columbia.edu/news/intelligent-space-race); [GMF](https://www.gmfus.org/news/ai-race-enters-physical-world)

### Inferences
- The article directly opposes the safety-valve reading. Its logic is that off-Earth industry is a **compounding power source** for whichever Earth actor controls it, so it intensifies Earth-side rivalry rather than diverting it. For Cole's thesis, it is the strongest recent statement of the main counterargument.
- It shares Cole's premise (machines are better suited to space than humans) but draws the opposite policy conclusion: race dynamics plus irreversibility, not relief.
- Its misaligned-probe passage is the mirror image of Potapov's paper: both assume a misaligned agent can build an independent off-Earth industrial base; King sees an uncontainable threat, Potapov sees a reduced incentive to fight.

### Gaps
- I read a model summary of the page, not the raw text. Exact wording beyond the short quotes should be checked against the original before quoting publicly.

## 2. State of space-based compute and off-Earth industry, 2025–2026

### Takeaway
Real hardware is flying, but only at demonstration scale: Starcloud-1 (one H100, Nov 2025), China's first 12 Three-Body satellites (May 2025), and Google's Suncatcher prototype (4 TPUs, launched Oct 1, 2026). What exists at gigawatt and million-satellite scale is FCC filings and executive rhetoric (SpaceX–xAI, Blue Origin, Starcloud). The best independent analysis (Forethought, May 2026) says orbital data centers could reach cost parity in 3–5 years if Starship works, but are unlikely to be a meaningful share of compute before 2030.

### Cited Findings
**SpaceX / xAI**
- SpaceX acquired xAI, announced 2026-02-02. Musk argued AI's electricity demand "cannot be met with terrestrial solutions" and that space-based AI is the only way to scale. Reported targets: about 100 GW of AI compute added per year, scaling toward 1 TW per year. These are aspirational company figures. Deal value is reported inconsistently ($250B all-stock vs a $1.25T combined valuation) — [TechRepublic](https://www.techrepublic.com/article/news-spacex-xai-merger/); [Fintool](https://fintool.com/news/spacex-xai-merger-orbital-data-centers)
- SpaceX filed with the FCC on 2026-01-30 for up to 1 million "Orbital Data Center System" satellites, at 500–2,000 km, solar-powered, linked to Starlink by optical links — [DCD](https://www.datacenterdynamics.com/en/news/spacex-files-for-million-satellite-orbital-ai-data-center-megaconstellation/); [Introl (trade blog)](https://introl.com/blog/spacex-1-million-orbital-data-centers-fcc-filing-2026)
- Musk said at the World Economic Forum in January 2026 that space would be the lowest-cost place for AI within two to three years — [Fortune, 2026-10-10](https://fortune.com/2026/10/10/google-project-suncatcher-ai-data-centers-space-satellite-launch-orbital-computing-spacex-blue-origin-artificial-intelligence-energy-demand/)

**Google Project Suncatcher**
- Announced November 2025. First prototype (built with Planet Labs, refrigerator-sized, four TPUs) launched on a SpaceX rocket on 2026-10-01 and is "operating as expected." It tests launch vibration, radiation and thermal extremes for about a year. It uses heat pipes and radiators, with chips running in 15-minute bursts. Two more satellites are planned for 2027 to test inter-satellite laser links — [Fortune](https://fortune.com/2026/10/10/google-project-suncatcher-ai-data-centers-space-satellite-launch-orbital-computing-spacex-blue-origin-artificial-intelligence-energy-demand/)
- Google SVP James Manyika said the full vision may not arrive in the next few years — [Fortune](https://fortune.com/2026/10/10/google-project-suncatcher-ai-data-centers-space-satellite-launch-orbital-computing-spacex-blue-origin-artificial-intelligence-energy-demand/)

**Starcloud (Nvidia-backed)**
- Starcloud-1 (60 kg, one Nvidia H100) launched November 2025 and ran Google's Gemma model in orbit — [Fortune](https://fortune.com/2026/10/10/google-project-suncatcher-ai-data-centers-space-satellite-launch-orbital-computing-spacex-blue-origin-artificial-intelligence-energy-demand/); [Wikipedia](https://en.wikipedia.org/wiki/Starcloud)
- Raised a $170M Series A at a $1.1B valuation (March 2026). Filed with the FCC on 2026-02-03 for up to 88,000 satellites — [Payload](https://payloadspace.com/starcloud-raises-170m-series-a-at-1-1b-valuation/); [GeekWire](https://www.geekwire.com/2026/orbital-ai-seattle-area-startup-starcloud-hits-1-1b-valuation-to-build-space-based-data-centers/)
- Starcloud-2 (Blackwell chip, about 100× Starcloud-1's power, large deployable radiator) is planned for late 2026. I found **no confirmation it has launched** as of 2026-10-16 — [GeekWire](https://www.geekwire.com/2026/orbital-ai-seattle-area-startup-starcloud-hits-1-1b-valuation-to-build-space-based-data-centers/)

**Blue Origin / Bezos**
- "Project Sunrise": FCC filing dated 2026-03-19 for up to 51,600 sun-synchronous data-center satellites, riding the separate 5,408-satellite TeraWave network (TeraWave launches targeted from Q4 2027), launched on New Glenn. The filing argues it would ease pressure on U.S. communities, energy and water — [TechCrunch](https://www.techcrunch.com/2026/03/20/jeff-bezos-blue-origin-enters-the-space-data-center-game/); [Light Reading](https://www.lightreading.com/satellite/bezos-blue-origin-enters-the-data-center-space-race)
- Bezos told CNBC (May 2026) that two-to-three-year timelines are "probably a little ambitious," citing chip prices and launch cost, while calling space data centers "very realistic" — [Quartz](https://qz.com/jeff-bezos-space-data-centers-blue-origin-052026)
- Italian Tech Week (October 2025): Bezos predicted gigawatt-scale orbital data centers in 10–20 years, saying training clusters are better built in space with 24/7 solar — [Data Centre Magazine](https://datacentremagazine.com/news/jeff-bezos-why-space-could-be-the-future-of-ai-data-centres)

**China**
- ADA Space and Zhejiang Lab launched the first 12 satellites of the "Three-Body Computing Constellation" on 2025-05-14 (Long March 2D, Jiuquan). The plan is 2,800 satellites and a 1,000 POPS target; each satellite reportedly carries an 8-billion-parameter model — [Live Science](https://www.livescience.com/space/space-exploration/china-is-building-a-constellation-of-ai-supercomputers-in-space-and-just-launched-the-first-pieces)
- 2026 status is thin: one unverified profile says ADA Space filed for an HKEX listing on 2026-05-14 and treats the 2,800-satellite target as a roughly 2035 horizon — [SpaceOdysseyHub (low confidence)](https://spaceodysseyhub.com/companies/ada-space-guoxing-yuhang)
- China Daily (2026-10-06): the Tiansuan constellation's space computing cloud has begun regular in-orbit experimental services. The PEGA-SUS1 experimental satellite (launched Sept 20) combines sensing, compute and onboard processing. A US Air Force CIO quoted there suggested China could deploy faster than the US — [China Daily](https://www.chinadaily.com.cn/a/202610/06/WS6ac42f5be4b06d4aa05616c1.html)

**Others**
- Eric Schmidt took control of Relativity Space in 2025. Reporting links this to orbital data centers, driven by AI power demand (he told Congress data centers need an extra 29 GW by 2027 and 67 GW by 2030). No formal program has been announced. Schmidt reacted positively to Ars Technica's inference rather than stating it outright — [Xataka](https://www.xatakaon.com/space/no-one-understood-why-googles-former-ceo-had-bought-a-rocket-company-his-answer-data-centers-in-space); [SpaceNexus](https://spacenexus.us/orbital-data-centers/relativity-space.md)
- Cowboy Space Corp. (Baiju Bhatt) flew Reason-1 on the 2026-10-01 SpaceX flight to test laser power beaming. It plans an April 2027 mission running Nvidia GB200 chips under a NOAA research agreement — [Fortune](https://fortune.com/2026/10/10/google-project-suncatcher-ai-data-centers-space-satellite-launch-orbital-computing-spacex-blue-origin-artificial-intelligence-energy-demand/); [China Daily](https://www.chinadaily.com.cn/a/202610/06/WS6ac42f5be4b06d4aa05616c1.html)
- Lonestar Data Holdings (lunar and LEO storage, first commercial LEO service targeted Q4 2026, about $5M seed) and Aetherflux (compute plus power beaming, demo satellite 2026, about $50M Series A). Single trade-blog source only — [Introl (trade blog)](https://introl.com/blog/orbital-data-centers-space-computing-race-2026)

**Independent economics**
- Forethought (Avi Parrack and Fin Moorhouse, 2026-05-22): orbital data centers approach cost parity at about $100/kg to orbit (today about $1,500/kg). They could be cost-competitive in 3–5 years if Starship reaches Falcon-like reuse, but are unlikely to be a meaningful share before 2030. Chips, not launch, may become the binding constraint. They model about 9% annual compute loss from unrepairable chip failures. Early use is mostly inference, because inter-satellite bandwidth limits frontier training. The FAA's 145 Starship launches per year cap would need to rise about 35-fold — [Forethought](https://www.forethought.org/research/will-we-really-put-data-centers-in-space)
- Forethought's safety and governance points: space compute could exploit jurisdictional ambiguity; the cheap path runs through SpaceX, which now owns a frontier AI lab (a concentration-of-power concern); orbital facilities resist weight exfiltration but are easy ASAT targets — [Forethought](https://www.forethought.org/research/will-we-really-put-data-centers-in-space)
- Skeptics: Varda Space Industries analysts estimate about 3× higher cost per watt than terrestrial compute (secondary source). Portal Space Systems' CEO cites launch mass of solar arrays as the cost problem — [Introl (trade blog)](https://introl.com/blog/orbital-data-centers-space-computing-race-2026); [Fortune](https://fortune.com/2026/10/10/google-project-suncatcher-ai-data-centers-space-satellite-launch-orbital-computing-spacex-blue-origin-artificial-intelligence-energy-demand/); [CNBC, 2026-06-21](https://www.cnbc.com/2026/06/21/do-space-based-ai-data-centers-make-economic-sense.html)

### Inferences
- The stated motive in 2025–2026 is energy, water and local opposition to data centers, so the industry is already partly framed as moving burdens off Earth. Nobody in these sources frames it as an AI-safety control.
- Ownership is concentrated. Every serious scaling path runs through two US launch providers (SpaceX, Blue Origin) or the Chinese state. That makes off-Earth compute an extension of terrestrial power, not something separate from it.
- Compute in orbit stays tethered to Earth for chips, launch and ground stations. An off-Earth AI base would only become independent with in-space chip fabrication, which nobody is near.

### Gaps
- Starcloud-2 launch status, ADA Space 2026 launches, and Lonestar and Aetherflux specifics rest on weak or single sources.
- I did not separately verify Axiom Space's orbital data center nodes.
- I found no primary xAI or SpaceX document with the 100 GW and 1 TW figures, only press summaries.

## 3. Proposals to move heavy industry off Earth and keep Earth residential

### Takeaway
Bezos is the most prominent living advocate. He has said since 2016 that Earth should be "zoned residential and light industry," and in 2025–2026 he extended this to AI data centers. The lineage goes back to Gerard O'Neill and Hans Moravec, whose 1999 book pictures robots industrializing space while Earth becomes a nature refuge for retired humans. None of these is a policy program; they are long-horizon visions.

### Cited Findings
- Bezos, Code Conference 2016: Earth should be zoned residential and light industry, with heavy industry moved to space because solar energy is abundant there, over "the next few hundred years" — [WEF, June 2016](https://weforum.org/agenda/2016/06/jeff-bezos-has-an-audacious-plan-to-move-industry-into-space-and-rezone-earth-as-residential)
- Bezos, 2019: moving heavy and polluting industry off Earth is "the only way, really, to save this planet" — [ET Online](https://www.etonline.com/jeff-bezos-on-future-of-spaceflight-we-can-move-all-heavy-industry-and-all-polluting-industry-off)
- Bezos, October 2025 and May 2026: AI training clusters will be better built in space, gigawatt-scale in 10–20 years; 2–3-year timelines are too ambitious — [Data Centre Magazine](https://datacentremagazine.com/news/jeff-bezos-why-space-could-be-the-future-of-ai-data-centres); [Quartz](https://qz.com/jeff-bezos-space-data-centers-blue-origin-052026)
- Blue Origin's 2026 Project Sunrise filing puts the zoning idea into regulatory language by arguing that compute should move off-world to relieve communities and resources — [TechCrunch](https://www.techcrunch.com/2026/03/20/jeff-bezos-blue-origin-enters-the-space-data-center-game/)
- Moravec, *Robot: Mere Machine to Transcendent Mind* (Oxford UP, 1999): robots first displace workers, then move off Earth to colonize space, leaving Earth as a nature refuge. A review describes them "trooping off Earth" — [Booklist review via CMU](https://frc.ri.cmu.edu/~hpm/book97/reviews/981101.booklist.html); [Elon University summary](https://www.elon.edu/u/imagining/?p=24787)
- Moravec's 1995 reasoning (Wired): robots don't need air, aren't harmed by zero gravity and can be shielded from radiation, so they will move operations off Earth to get raw materials — [Elon University archive](https://www.elon.edu/u/imagining/?p=24787)
- A critical Foreign Affairs review found some of the book's claims "a tad overblown" — [Foreign Affairs](https://www.foreignaffairs.com/node/1080226)

### Inferences
- Bezos's version is environmental, with humans in control and industry as a tool. Moravec's is evolutionary, with machines as successors and Earth as a reserve. Cole's version, Earth de-industrialized so that a misaligned AI's resource incentives point outward, sits closer to Moravec's, plus an explicit safety rationale that neither of them gives.

### Gaps
- I did not fetch a primary source for Gerard O'Neill's *The High Frontier* (1976). From background knowledge, it proposed space colonies and space solar power built from lunar materials, and Bezos studied under O'Neill at Princeton. Verify before citing.
- I did not find a 2025–2026 government or think-tank proposal for de-industrializing Earth as policy.

## 4. Policy, law and militarization: relief valve or new arena?

### Takeaway
Current law and geopolitics point toward **a new arena of competition**. Two rival lunar blocs are forming: the Artemis Accords (roughly 69–75 signatories by late 2026, counts vary by source) and China's ILRS (about 13 nations). The Outer Space Treaty's non-appropriation rule is being worked around through resource-ownership laws and "safety zones." The US is building space-based interceptors under Golden Dome.

### Cited Findings
- The Artemis Accords' "safety zones" could give first movers de facto control despite the Outer Space Treaty's ban on sovereign claims — [AI Frontiers](https://ai-frontiers.org/articles/the-ai-race-will-extend-far-beyond-earth)
- Artemis Accords signatory counts conflict: 61 by January 2026 (Britannica); Serbia was the 69th (July 2026, SpaceNews); one tracker lists 75 by 2026-09-24. China has not joined, and US law restricts NASA cooperation with China — [Britannica](https://www.britannica.com/topic/Artemis-Accords); [SpaceNews](https://spacenews.com/serbia-signs-the-artemis-accords/); [SpaceNexus (tracker)](https://spacenexus.us/moon/alliances)
- China's ILRS aims for a lunar base in the 2030s, with about 13 member states. Some countries (Serbia, Thailand, Senegal) are in both camps — [Wikipedia: ILRS](https://en.wikipedia.org/wiki/International_Lunar_Research_Station); [SpaceNews](https://spacenews.com/serbia-signs-the-artemis-accords/)
- Commentators describe Artemis vs ILRS as a "new Cold War" that will make non-alignment hard to sustain — [ThePrint](https://theprint.in/opinion/artemis-irls-and-a-new-cold-war-celestial-non-alignment-will-be-hard-to-sustain/3035256/)
- Golden Dome: the Space Force has awarded 20 prototype agreements to 12 firms (including SpaceX, Anduril, Lockheed, Northrop, GITAI USA), worth up to $3.2B, for space-based interceptors. The Pentagon estimates $185B with completion by 2035; the CBO (May 2026) estimates $1.2T, about 70% of it the space layer. Program lead Gen. Guetlein says production depends on whether SBIs are affordable at scale — [MeriTalk](https://www.meritalk.com/articles/space-force-taps-12-companies-for-golden-dome-space-based-interceptor/); [Breaking Defense, April 2026](https://breakingdefense.com/2026/04/golden-dome-czar-signals-space-based-interceptors-arent-guaranteed-as-dod-weighs-cost/); [Atlantic Council](https://www.atlanticcouncil.org/dispatches/golden-dome-needs-a-price-tag-and-a-clear-objective-to-succeed/)
- Forethought notes anti-satellite arms-control talks are largely gridlocked — [Forethought](https://www.forethought.org/research/will-we-really-put-data-centers-in-space)

### Inferences
- For Cole's thesis, the legal regime matters in two ways. (a) Non-appropriation plus national resource laws means off-Earth industry will be owned by Earth states and firms, so it does not form a separate "machine jurisdiction" that an AI could be steered toward. (b) Dual-use overlap (the same firms build data-center satellites and interceptors) means a policy push to move industry off Earth would probably read internationally as militarization.
- What would show this wrong: a binding multilateral regime for off-Earth industry (an ITER- or IAEA-style body) emerging alongside the blocs.

### Gaps
- I did not fetch primary texts for the 2015 US CSLCA or the Luxembourg, UAE and Japan resource laws in this pass. From background knowledge, all four grant private ownership of extracted space resources while disclaiming sovereignty. Verify before citing.
- I did not check CSIS Aerospace Security or Secure World Foundation 2026 reports.

## 5. Who has proposed off-Earth expansion as a way to reduce AI–human conflict, and the critics

### Takeaway
The explicit safety framing is rare. The clearest 2026 statement is Alexey Potapov's arXiv paper (June 2026). Older antecedents treat machine expansion into space as natural or inevitable, not as a deliberate control: Schmidhuber (AIs will lose interest in humans and go where the resources are), Moravec (robots leave, Earth becomes a refuge) and de Garis (Cosmists versus Terrans). The strongest rebuttal is Yudkowsky's 2024 essay: an unaligned superintelligence would still take Earth, because sparing it gains it nothing.

### Cited Findings
- **Potapov, "Reframing AGI Confrontation with Off Earth Autonomy," arXiv:2606.30666 (cs.CY), submitted 2026-06-18.** It argues that power-seeking and confrontation arguments in AI safety often assume an Earth-centered strategic situation. It sketches a staged path from Earth dependence to an autonomous off-Earth machine industrial base, and argues that early cooperation can beat confrontation as a route to autonomy. It discusses feedback between human preemption and agent behavior. It proposes iterative oversight under incentive-compatible early cooperation. Key line: "confrontation is not the only route to reducing human control." It is qualitative, not formal. It anchors on a "confrontation question" attributed to "Saklakov," whom I could not identify — [arXiv](https://arxiv.org/abs/2606.30666)
- **Schmidhuber** (2015–2019): superintelligent AIs will be mostly interested in other AIs, not humans, and will expand into space because most resources lie outside Earth's thin biosphere. He told CNBC (2018) he tried to reassure Musk that AIs would "lose interest" in humans. He frames human marginality as acceptable — [TelecomTV, 2017](https://www.telecomtv.com/content/tracker/moonshot-the-ai-civilization-will-expand-into-space-27177/); [CNBC, 2018](https://www.cnbc.com/2018/05/16/jurgen-schmidhuber-urges-humans-not-to-fear-artificial-intelligence.html); [Telekom interview, 2017](https://www.telekom.com/en/newsroom/latest-updates/news/2017/4/interview-with-prof-juergen-schmidhuber-father-of-ai); [Goethe-Institut](https://www.goethe.de/ins/in/en/kul/fmd/dis/21506369.html)
- **Moravec** (1995, 1999): robots move industry off Earth for raw materials and because they suit space; Earth becomes a pampered human "retirement community" and nature refuge. He also expected biological humans to be outcompeted eventually — [Elon University](https://www.elon.edu/u/imagining/?p=24787); [Booklist](https://frc.ri.cmu.edu/~hpm/book97/reviews/981101.booklist.html); [Britannica](https://www.britannica.com/print/article/1983022)
- **Hugo de Garis** (Artilect War): Cosmists, who favor building artilects, against Terrans, who oppose them, with a feared "gigadeath" war. Sources **conflict** on who leaves Earth: one says Cosmists flee to space with Terrans pursuing them, the other says Cosmists leave Earth to the Terrans. Either way, space separation is not a stable solution in his account — [Extropians archive, 1997](https://diyhpl.us/~bryan/irc/extropians/extracted-extropians-archive/archive/9708/13896.html); [Academic Kids encyclopedia](https://academickids.com/encyclopedia/index.php/Hugo_De_Garis); [IEET, 2014](https://ieet.org/index.php/IEET2/more/notaro20141029)
- **Critic: Yudkowsky, "The Sun is big, but superintelligences will not spare Earth a little sunlight" (MIRI, 2024-09-23).** It answers the claim that a big solar system means Earth will be left alone. Earth intercepts a negligible fraction of sunlight, but a negligible cost is still a cost an indifferent optimizer won't pay without a reason. He also rejects comparative-advantage trade arguments with the horses-to-glue-factory analogy. A follow-up clarified that the claim is about **unaligned** systems — [MIRI](https://intelligence.org/2024/09/23/the-sun-is-big-but-superintelligences-will-not-spare-earth-a-little-sunlight/); [LessWrong thread](https://www.greaterwrong.com/posts/F8sfrbPjCQj4KwJqn/the-sun-is-big-but-superintelligences-will-not-spare-earth-a/comment/aAGwttgKYtshtezRF)
- **Critic (structural): King, AI Frontiers (2026-10-08).** A misaligned self-replicating off-Earth base is an irreversible, uncontainable threat, not a release valve — [AI Frontiers](https://ai-frontiers.org/articles/the-ai-race-will-extend-far-beyond-earth)

### Inferences
- Cole's proposal is most defensible as Potapov frames it: it changes the **early** incentive gradient, while an AI still depends on Earth, rather than guaranteeing a good end state. Yudkowsky's argument targets the **late** stage, when a mature unaligned optimizer would also want Earth's resources. De-industrializing Earth does not remove Earth's atoms, its sunlight, or the threat humans pose as a source of rival AIs. The two arguments mostly talk past each other on timing.
- The strongest counter to "de-industrialize Earth as a safety control" is that it hands the off-Earth industrial base, the very thing that would make a misaligned AI independent and hard to stop, to whoever builds it. King's article makes exactly this point at the nation-state level.
- What would show Cole's idea working: evidence that agents with a credible exit option show measurably less shutdown resistance or power-seeking toward overseers (testable in multi-agent sims). What would show it failing: such agents use Earth-side cooperation to buy time, then defect once independent, the classic treacherous-turn pattern.

### Gaps
- I did not fetch primary sources for Robin Hanson (*The Age of Em*, 2016), Freeman Dyson, or Isaac Arthur in this pass. From background knowledge: Hanson models an em economy that stays largely Earth-bound in cities, which undercuts the idea that machines naturally leave. Dyson wrote about life and intelligence spreading through space. Isaac Arthur popularizes the idea that AIs would go where resources are more plentiful. None of these is verified here.
- "Saklakov's confrontation question" (the anchor in Potapov) could not be identified.
- The user's repo history includes a commit titled "Cite convergent off-Earth autonomy work," so the user may already know the Potapov paper.

## 6. Humans vs machines in space: evidence

### Takeaway
Robots are vastly cheaper per mission (a few billion dollars for a Mars rover vs $100–500B+ for a crewed Mars mission). Crews are faster and more flexible in the field, and the honest science-per-dollar comparison depends on assumptions. Autonomy is advancing (AI-planned Mars drives in Dec 2025, autonomous ISS-exterior robotic arms), but free-flying commercial in-space servicing and assembly is behind schedule.

### Cited Findings
- A crewed Mars mission is estimated at $100–500B, against about $2.7B for Mars 2020 (Perseverance plus Ingenuity) — [newspaceeconomy.ca (opinion)](https://newspaceeconomy.ca/2025/12/31/the-case-against-human-spaceflight-exploration-risks-costs-alternatives/); [The Conversation](https://theconversation.com/are-astronauts-worth-tens-of-billions-of-dollars-in-extra-costs-to-go-to-mars-111348)
- Pro-crew counterpoint: one estimate says a four-person crew would be about 500 times as productive as Curiosity at about 200 times the cost. The author recommends combining humans and robots and acknowledges large error bars — [The Conversation](https://theconversation.com/are-astronauts-worth-tens-of-billions-of-dollars-in-extra-costs-to-go-to-mars-111348)
- Perseverance completed the first AI-planned drives on Mars on 2025-12-08 and 2025-12-10 (about 210 m and 246 m). JPL used Anthropic's Claude to generate waypoints from orbital imagery, validated in a digital twin against 500,000+ telemetry variables. Engineers estimate it halves planning time. Humans still adjusted routes — [NASA JPL](https://www.jpl.nasa.gov/news/nasas-perseverance-rover-completes-first-ai-planned-drive-on-mars/); [The Robot Report](https://www.therobotreport.com/nasa-perseverance-rover-completes-first-ai-planned-drive/)
- GITAI's S2 dual-arm robot completed planned in-space servicing, assembly and manufacturing tasks outside the ISS Bishop Airlock in 2024 (self-reported TRL 7) — [GITAI](https://gitai.tech/?p=7143); [ISS National Lab](https://issnationallab.org/?p=38013)
- One unverified secondary report says no GITAI arm has yet operated on a free-flyer, and that the S3 servicing mission was deferred past 2028 — [Inspenet (unverified)](https://inspenet.com/en/news/arm-robotic-gitai-complete-test/)
- Canadarm2 installed CLARREO Pathfinder (May 2026). ESA printed a metal part on the ISS (2024). Blue Alchemist makes solar cells from simulated regolith — [AI Frontiers](https://ai-frontiers.org/articles/the-ai-race-will-extend-far-beyond-earth)

### Inferences
- The evidence supports Cole's narrow premise that machines are cheaper and better suited to space operations per dollar and per unit of risk. It does not yet support "live, adapt and grow": no machine system today self-repairs, self-replicates, or makes its own chips or solar cells at scale off Earth. The "grow" part is the unproven, load-bearing step.

### Gaps
- No rigorous, peer-reviewed robotic-vs-crewed cost-effectiveness study was found. The sources are opinion pieces with wide error bars.
- I did not verify Starfish Space's 2025–2026 servicing missions or NASA ISAM program status.
