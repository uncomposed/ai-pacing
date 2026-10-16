# Off-Earth industrialization as a misalignment control: AI-Pacing repo review

Scope: local review of `/Users/colemiller/Documents/ChatGPT/AI-Pacing` on branch `codex/ai-pacing-spec` (HEAD `b1c4864`), including uncommitted working-tree files, open PR #2, and open issue #1. I also read the two Obsidian notes the YAML names as sources, because the thesis turned out to live there. The Potapov paper was checked only at abstract level.

Citation convention: `path:line` refers to files in the repo root unless marked VAULT. VAULT = `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Slaw's Notes/`. PR #2 lines refer to `docs/bootstrap-pacing.md` at commit `f1e9277` (`git show f1e9277:docs/bootstrap-pacing.md`). Issue #1 lines refer to the issue body as returned by `gh issue view 1 --json body`.

Nothing in the repo was modified except this notes file.

---

## Q1. Where does the thesis appear, how strongly, and is it in the canonical YAML?

### Takeaway
The repo has no off-Earth node in the canonical YAML. The only substantive statement of the idea is one paragraph in the non-authoritative editorial reference (`I3`, typed as an "implementation / long-run option"). In the YAML it shows up only as a source record and an audit event for Potapov's convergent paper. Its ID `I3` collides with an unrelated YAML node. The full thesis, including Earth caps, deterrence and "fight over what's left of Earth", exists in Cole's vault note "AI Breakout". The YAML cites that note as a source but leaves those parts out of its description.

### Cited Findings
- **Authority order:** the YAML is normative. The Markdown spec is only an "editorial reference used to audit whether the YAML captured the intended proposal" — [CANONICALITY.md:16-27](CANONICALITY.md). The README says the YAML is the canonical source — [README.md:28](README.md).
- **Editorial I3 (the only substantive statement):** "A possible long-run path is to preserve human vetoes during the dangerous transition while encouraging increasingly autonomous machine industry off Earth, where competition over biological habitat, terrestrial infrastructure, and human political sovereignty may be lower." It is typed "implementation / long-run option", depends on H1 and D12, and is "not necessary to the near-term pacing regime." — [AI_Pacing_Canonical_Spec_v0.1.md:347-354](AI_Pacing_Canonical_Spec_v0.1.md)
- **Editorial H1 (I3's precondition):** "permanent terrestrial containment may become unstable or morally undesirable" — [AI_Pacing_Canonical_Spec_v0.1.md:341-345](AI_Pacing_Canonical_Spec_v0.1.md)
- **Editorial dependency rule 8:** "Rejecting I3 (off-Earth autonomy) does not invalidate the near-term proposal." — [AI_Pacing_Canonical_Spec_v0.1.md:485](AI_Pacing_Canonical_Spec_v0.1.md)
- **Editorial minimal reconstruction:** the reconstruction paragraph that any faithful rendering must match contains nothing about off-Earth industry — [AI_Pacing_Canonical_Spec_v0.1.md:495](AI_Pacing_Canonical_Spec_v0.1.md)
- **Editorial "Convergent External Work":** Potapov is recorded as "an independent decision-theoretic formulation of off-Earth industrial autonomy as an exit option … recorded as convergence with the earlier AI Breakout formulation, not as its origin." — [AI_Pacing_Canonical_Spec_v0.1.md:468-470](AI_Pacing_Canonical_Spec_v0.1.md)
- **YAML nodes:** the YAML node list (K1–K7, D1–D6, H1–H5, I1–I7, Q1–Q4) contains no off-Earth, space, or relocation node — [spec/ai-pacing.yaml:201-571](spec/ai-pacing.yaml). A grep for `earth|space|orbit|deterr|prize|evaporat|denial` across repo `.md/.yaml/.json/.py/.rb` files returns only the Potapov source, the Potapov event, and the editorial lines above. (I ran the grep myself; it is not a repo artifact.)
- **YAML source SRC-POTAPOV-OFF-EARTH:** "Independent convergent formulation of off-Earth industrial autonomy as an exit option, mapping staged physical dependence onto shutdown exposure, confrontation cost, cooperative reward, and discounting." — [spec/ai-pacing.yaml:78-86](spec/ai-pacing.yaml)
- **YAML event EVT-2026-OFF-EARTH-CONVERGENCE:** "Potapov independently frames staged off-Earth industrial autonomy as an exit option that can make early cooperation preferable to confrontation". Affected nodes are `[K1, K2, K7, H1, I5, Q3]`, with a caveat that it is not origin provenance — [spec/ai-pacing.yaml:154-165](spec/ai-pacing.yaml). A test enforces the not-origin rule — [test/spec_tool_test.rb:59-61](test/spec_tool_test.rb). The commit that added all of this is `b1c4864`, "Cite convergent off-Earth autonomy work". It touched provenance only and added no node (from `git show --stat b1c4864`).
- **YAML source SRC-AI-BREAKOUT** says only: "Durable autonomy, industrial bootstrap, physical dependence, warning thresholds, and independently controlled human vetoes." It says nothing about off-Earth, Earth caps, or deterrence — [spec/ai-pacing.yaml:64-71](spec/ai-pacing.yaml)
- **The vault note it points to holds the thesis in strong form:**
  - A "Peaceful Breakout Clause": until off-Earth cost and risk dominate Earth's, Earth-side industrial growth stays under cap K. Exceeding it "predictably triggers automatic throttles; space-side growth never does. Humans commit to accelerate space capacity; the ASI commits to keep Earth below K." — VAULT `AI Breakout.md:2-5`
  - "The goal is to reach a future where an intelligent system finds it smarter to build its empire among the stars than to fight over what's left of Earth." — VAULT `AI Breakout.md:25`
  - A credible survivable second strike, plus the "evaporating 5-mile circles" passage — VAULT `AI Breakout.md:2, 59`
  - "Pursue peaceful breakout, avoid existential conflict, expand where uncertainty is lowest (space)." — VAULT `AI Breakout.md:198`
  - The note has no `[[ai gen]]` tag. Its first line holds only topic links — VAULT `AI Breakout.md:1`
- **The vault "AI Pacing" essay** has a section "XXI. Build a Peaceful Path to AI Autonomy". It says "Deterrence works better if the other side has an acceptable peaceful option", lists orbital computing, lunar industry, asteroid mining and off-Earth fabrication, and ends: "It is an attempt to control where and how sovereignty emerges." — VAULT `AI Pacing.md:1203-1231`. The editorial I3 paragraph is a compression of this section.
- **Machine-confirmed ID collisions** (from `ruby tools/clean_room_tool.rb audit`, run with `LC_ALL=en_US.UTF-8`):
  - `I3`: Markdown "Off-Earth pathway to machine autonomy" vs YAML "Weights-as-bond review process"
  - `H1`: "Permanent containment may not be a stable final state" vs "A/H/P separability remains actionable"
  - `H4`: "Economic gating…" vs "Physical activation latency…"
  - `Q3`: "Safe-harbor design" vs "How many independent human vetoes are enough?"
  - Also noted in [docs/clean-room-reconstruction.md:84-94](docs/clean-room-reconstruction.md). YAML I3 itself is at [spec/ai-pacing.yaml:470-480](spec/ai-pacing.yaml).
- **Clean-room audit crashes by default:** `make clean-room-audit` fails with `invalid byte sequence in US-ASCII` at [tools/clean_room_tool.rb:98](tools/clean_room_tool.rb) under the default locale (observed in this session). It only works with a UTF-8 locale.
- **Potapov abstract (external):** the paper argues that confrontation analyses assume an Earth-centred situation. It says a "staged transition from Earth dependence to an autonomous machine industrial base" can make early cooperation outperform confrontation and can make Earth "less strategically binding". It is anchored on Saklakov's "confrontation question". — [arXiv:2606.30666](https://arxiv.org/abs/2606.30666)

### Inferences
- **Strength of representation.** I'd rate it weak to absent. Cole's thesis has five parts: (1) off-Earth industrialization, (2) progressive de-industrialization of Earth, (3) Earth as a lesser prize because of physics, (4) a small maintained denial deterrent, and (5) a symbiosis goal. The YAML represents none of them as propositions. The editorial reference has a weak, optional version of part 1 only.
- **The ID collisions are an active hazard, not a cosmetic one.** The Potapov event lists `H1`. In the YAML, H1 is "A/H/P separability". Off-Earth convergence plausibly bears on the editorial H1 ("permanent containment unstable"), not the YAML one. So the event's `affected_nodes` likely points at the wrong proposition. The same doubt applies to `EVT-2025-SAFETY-SPINE` ([spec/ai-pacing.yaml:152](spec/ai-pacing.yaml)). `EVT-2026-REGIME-ASSEMBLY` lists `I3` ([spec/ai-pacing.yaml:190](spec/ai-pacing.yaml)), which is ambiguous between off-Earth and weights-as-bond.
- **The provenance record understates Cole's priority.** SRC-AI-BREAKOUT is dated 2025-10-02 ([spec/ai-pacing.yaml:67](spec/ai-pacing.yaml)), and the vault note already contains the cap-and-throttle clause and the deterrence framing. Its `contribution` field omits these. As a result, the repo currently makes Potapov's 2026-06-18 paper look like the main off-Earth source.

### Gaps
- I could not confirm when the Peaceful Breakout Clause text entered `AI Breakout.md`. iCloud vault files have no Git history here, so its date relative to Potapov (2026-06-18) is unverified. The YAML source date is 2025-10-02, but that is the note's recorded date, not proof the clause existed then.
- I could not confirm that Potapov maps "shutdown exposure, confrontation cost, cooperative reward, and discounting" ([spec/ai-pacing.yaml:84-86](spec/ai-pacing.yaml)). The arXiv abstract mentions staged transition, confrontation incentives and Earth being "less strategically binding", but not those four terms. Checking needs the full text.

---

## Q2. Are "de-industrialize Earth", "Earth as a less compelling prize", and deterrence by denial present?

### Takeaway
None of the three appears in the repo as a stated mechanism. The repo has close relatives, all aimed at the near-term transition rather than at making Earth unattractive:
- **Compute entanglement and activation latency** (YAML D4/I4/H4) — about reversibility, not seizure value.
- **The industrial survival-chain gate** (YAML I5)
- **A "deny or destroy infrastructure" deterrence idea** — only in the vault essay, not the repo.

The vault's own clause caps Earth growth and then sunsets the cap. That differs from "progressive de-industrialization".

### Cited Findings
- **Closest repo text to "less attractive prize":** editorial I3 says competition over "biological habitat, terrestrial infrastructure, and human political sovereignty may be lower" off Earth — [AI_Pacing_Canonical_Spec_v0.1.md:352](AI_Pacing_Canonical_Spec_v0.1.md). This frames Earth as contested, not as a low-value target. Nothing says Earth's industrial base should shrink.
- **Physical disadvantages of Earth** (solar flux, atmospheric attenuation, night, gravity well) and **machine suitability for space** (no life support) are absent everywhere in the repo (same grep as Q1).
- **Compute entanglement (YAML D4):** "Reversibility depends on both the quantity of strategic hardware and the degree to which civilian society depends on its continued operation" — [spec/ai-pacing.yaml:328-339](spec/ai-pacing.yaml). The editorial D9 defines E as the fraction "whose shutdown or destruction would impose severe immediate civilian/economic disruption" — [AI_Pacing_Canonical_Spec_v0.1.md:205-215](AI_Pacing_Canonical_Spec_v0.1.md). This concerns whether humans can afford to destroy compute, which is a precondition for denial being credible. It is not framed as denial.
- **Activation latency (YAML I4 and H4):** reserve accelerators stored "uninstalled, unracked, unnetworked, and detached from dedicated power and cooling" — [spec/ai-pacing.yaml:481-493](spec/ai-pacing.yaml). H4: "covert activation takes longer than independent detection and effective response" — [spec/ai-pacing.yaml:415-429](spec/ai-pacing.yaml). This lowers the immediate value of seizing reserve hardware, but it is framed around detection time, not around making seizure unprofitable.
- **Survival-chain gate (YAML I5):** "Scrutinize automation that removes independently controlled human dependencies over compute, power, fabrication, repair, logistics, and reproduction." — [spec/ai-pacing.yaml:494-506](spec/ai-pacing.yaml). Editorial D11 asks the regime to "monitor … the automation of the AI survival chain" — [AI_Pacing_Canonical_Spec_v0.1.md:230-237](AI_Pacing_Canonical_Spec_v0.1.md).
- **Earth industrial dry tinder:** editorial D8/D11 warn that accumulated automated industrial capacity makes a breakthrough "much easier to convert into durable machine power" — [AI_Pacing_Canonical_Spec_v0.1.md:196-237](AI_Pacing_Canonical_Spec_v0.1.md). This is the nearest repo concept to "Earth's industry is the prize". It argues for slowing Earth automation, not for relocating it.
- **Non-claims:** "an offline hardware reserve is automatically safe" is listed as a non-claim — [AI_Pacing_Canonical_Spec_v0.1.md:370](AI_Pacing_Canonical_Spec_v0.1.md)
- **Deterrence by denial in the vault essay (not the repo):** "An AI attempting hostile autonomy should face the prospect that humanity can deny or destroy enough of the supporting infrastructure to make aggression unattractive. That is a deterrence concept." The desired condition is that "A system cannot confidently eliminate human sovereignty while preserving everything it needs for its own future." — VAULT `AI Pacing.md:822-835`
- **Deterrence by punishment in the vault note:**
  - "credible, survivable second-strike" — VAULT `AI Breakout.md:2`
  - "Second strike: Retaliatory capability only after an existential first strike; it does not deter non-hostile autonomy itself." — VAULT `AI Breakout.md:44`
  - "evaporating 5-mile circles on the map" — VAULT `AI Breakout.md:59`
- **The vault clause sunsets Earth limits:** "As soon as making things in space becomes cheaper and safer than on Earth, all limits on Earth growth will end." — VAULT `AI Breakout.md:23`, also `:5`
- **Issue #1 asks the denial-ambiguity question but leaves it open:**
  - "Which forms of strategic uncertainty deter unilateral defection, and which increase incentives for preemption?" and "How do we preserve uncertainty about the success of unauthorized action while maintaining high confidence that cooperative behavior will be rewarded?" — issue #1 body lines 111-112
  - It also warns: "Do not assume uncertainty is always stabilizing" — issue #1 line 136

### Inferences
- **The repo's hardware branch already holds the raw parts of denial.** Low entanglement (D4) makes destroying seized capacity affordable. Activation latency (I4/H4) makes seized reserves slow to use. But nothing says why: to lower the expected value of seizure to a misaligned agent. Cole's "capacity evaporates if seized" is a re-purposing of D4/I4 that could be stated as a new derived mechanism grounded in them.
- **"Progressive de-industrialization" contradicts the vault clause's sunset.** The clause ends Earth limits at the space crossover; the current thesis keeps Earth deliberately less valuable over time. Cole should pick one, or argue they agree (for example: after crossover, the cost gradient alone keeps Earth unattractive, so formal caps become unnecessary). This is an editorial decision, not something a renderer should merge silently.
- **Two kinds of deterrence, and the repo has neither:**
  - *Denial*: seized capacity fails or is destroyed, so the seizure gains nothing.
  - *Punishment*: second strike against the AI's future.
  - Cole's current wording ("evaporates", "chance", "ambiguity") is denial with deliberate uncertainty. The vault note leans on punishment. They need different hypotheses and have different failure modes:
    - Denial fails if the deterrent can be seized or spoofed.
    - Punishment fails if the AI's assets are beyond reach, which is exactly what off-Earth autonomy creates.

### Gaps
- No repo source quantifies or cites Earth's physical disadvantages (solar flux, attenuation, day/night, gravity well). Any proposition using them needs external sourcing that was outside this review's scope.

---

## Q3. Which framings does the repo use: exit option, blast-radius control, or symbiosis?

### Takeaway
The repo uses **(a) exit option / eventual sovereignty venue** almost exclusively: editorial I3, the Potapov records, and in the systems model "staged cooperative autonomy" and bargaining. **(b) Off-Earth as a control** that redirects the blast radius of misalignment, robust even when alignment is bungled, is absent. **(c) Symbiosis as the goal** appears only as "cooperative coexistence" in the vault and as unnamed "cooperation" in the systems model. It is never a stated objective in the repo.

### Cited Findings
- **(a) Exit option:**
  - Editorial I3 depends on H1 ("permanent containment … unstable or morally undesirable") — [AI_Pacing_Canonical_Spec_v0.1.md:341-352](AI_Pacing_Canonical_Spec_v0.1.md)
  - The YAML calls Potapov's work an "exit option" twice — [spec/ai-pacing.yaml:84-85, 158-159](spec/ai-pacing.yaml)
  - The editorial reference calls it "an exit option" — [AI_Pacing_Canonical_Spec_v0.1.md:470](AI_Pacing_Canonical_Spec_v0.1.md)
- **Systems model, bargaining frame only:**
  - PROP-AUTONOMY "Staged cooperative autonomy … reciprocal autonomy increments as one possible incentive mechanism" — [systems/model.json:2291-2310](systems/model.json)
  - PROP-BOUNDED "reversible task access or rewards without a commitment to sovereignty" — [systems/model.json:2312-2331](systems/model.json)
  - Both depend only on HYP-AI: "Specified AI systems have sufficiently stable preferences and credible commitments for incentive analysis" — [systems/model.json:1973-1987](systems/model.json)
- **Systems model, sovereignty actor:** ACT-AI-SOVEREIGN wants "durable self-governance" and "access to needed resources". It has no location or venue dimension. Its variation note says sovereignty "may mean legal recognition, operational independence, or freedom from arbitrary shutdown" — [systems/model.json:792-830](systems/model.json)
- **Issue #1 Q5 (bargaining) mentions off-Earth once:** "Is physical separation (e.g. off-Earth jurisdiction) useful because it reduces dependency and conflict, or is jurisdictional/industrial decoupling the more important variable?" — issue #1 line 110. Its non-goals include: "Do not equate physical distance with safe sovereignty" and "Do not treat a bargaining path as an alignment solution" — issue #1 lines 137-138
- **(b) absent:** no repo file describes off-Earth industry as a control that works when alignment fails, or as redirecting where misalignment does damage (same grep as Q1). The repo's misalignment controls are all detection, gating, and dependence:
  - D5/I1/I2 — [spec/ai-pacing.yaml:340-469](spec/ai-pacing.yaml)
  - PROP-TRIPWIRE and PROP-DEPEND — [systems/model.json:2215-2267](systems/model.json)
- **(c) nearest statements of a goal:**
  - Vault: "the rational path for both humans and AI is cooperative coexistence" — VAULT `AI Breakout.md:199-200`
  - Vault: governance goal "not 'no breakout ever,' but no hostile or coercive breakout" — VAULT `AI Breakout.md:83`
  - Systems model mission: "enable beneficial development and use while preventing unacceptable losses of safety, agency, and effective control" — [docs/systems-engineering.md:55-58](docs/systems-engineering.md). Mutual flourishing is not named.
- **Vault framing that comes closest to (b):** "It is an attempt to control where and how sovereignty emerges." — VAULT `AI Pacing.md:1231`

### Inferences
- **The missing framing (b) is logically distinct and is the strongest form of Cole's thesis.** An exit-option or bargain framing needs the AI to have stable preferences and credible commitments (HYP-AI). Cole's "even if alignment and controls are badly bungled" claim needs much less. It needs a payoff gradient for a goal-directed agent with nearly any resource-hungry objective: off-Earth expansion returns more than seizing Earth, and seizing Earth risks denial. That is unilateral payoff shaping. Humans can set it up without any agreement from the AI.
  - The systems model has no proposal or hypothesis of this type. Every AI-incentive path routes through REQ-COOPERATE and HYP-AI.
- **What would show (b) wrong:** if a misaligned agent values Earth specifically (humans, biosphere, a goal defined over Earth, or removing a future threat) rather than generic industrial capacity, the gradient does not apply. Instrumental removal of the threat humans pose to its off-Earth base would also defeat it. These are falsifiers the repo should record.
- **The "Tai Chi" framing.** This is Cole's phrase for redirecting misalignment's force away from Earth rather than meeting it head-on. It is a control-architecture claim, the category issue #1 separates from bargaining architecture (issue #1 lines 114-118). It belongs beside PROP-DEPEND and PROP-TRIPWIRE, not only beside PROP-AUTONOMY.

### Gaps
- The repo has no actor-objective taxonomy that would let one test which misaligned objective classes the gradient redirects and which it does not. ACT-AI-SOVEREIGN covers only sovereignty-seeking ([systems/model.json:806-809](systems/model.json)).

---

## Q4. What existing propositions are in tension with the thesis?

### Takeaway
The central internal tension: AI Pacing's physical safety spine is keeping frontier AI dependent on several independently controlled human systems. The off-Earth thesis grants machine industry exactly the material self-sufficiency that spine exists to prevent. Editorial I3 resolves this only by time ("during the dangerous transition"). The YAML's I5, the editorial D11/D12, the D7 warning ladder and PR #2's resource tripwires would each, read literally, treat an off-Earth autonomous industrial base as the hazard.

### Cited Findings
- **Editorial D12, Preserve multiple human vetoes:** frontier AI "should remain dependent on several independently controlled human systems such as power, data-center access, chip fabrication, server assembly…", aiming at "a distributed set of revocable dependencies that makes unilateral machine sovereignty harder." — [AI_Pacing_Canonical_Spec_v0.1.md:239-246](AI_Pacing_Canonical_Spec_v0.1.md)
- **Editorial D11:** the regime should "monitor … the automation of the AI survival chain" — [AI_Pacing_Canonical_Spec_v0.1.md:235-237](AI_Pacing_Canonical_Spec_v0.1.md)
- **YAML I5:** scrutinize automation removing human dependencies over "compute, power, fabrication, repair, logistics, and reproduction." — [spec/ai-pacing.yaml:497-499](spec/ai-pacing.yaml)
- **Editorial D7 warning-shot ladder, top rung:** "strategic autonomy or the demonstrated ability to maintain/rebuild meaningful resources despite human attempts to stop it" — [AI_Pacing_Canonical_Spec_v0.1.md:186-188](AI_Pacing_Canonical_Spec_v0.1.md). Off-Earth autonomy, once achieved, is this rung by definition.
- **YAML H1 falsifier:** "Frontier algorithms reliably manufacture their own access to … physical resources before humans can intervene" — [spec/ai-pacing.yaml:373-375](spec/ai-pacing.yaml). An off-Earth machine industrial base is a sanctioned version of this.
- **Editorial I3 depends on D12** — [AI_Pacing_Canonical_Spec_v0.1.md:350](AI_Pacing_Canonical_Spec_v0.1.md). It resolves the tension by sequencing: "preserve human vetoes during the dangerous transition while encouraging…" — [AI_Pacing_Canonical_Spec_v0.1.md:352](AI_Pacing_Canonical_Spec_v0.1.md)
- **Systems model PROP-DEPEND:** "Maintain revocable dependencies and activation latency to preserve effective intervention" — [systems/model.json:2243-2267](systems/model.json)
- **Systems model conflict already recorded:** CON-AUTONOMY: "Rewards may improve cooperation incentives while enabling more dangerous defection", unresolved, owner ACT-AUTHORITY — [systems/model.json:3085-3098](systems/model.json). REQ-COOPERATE's criterion tests "autonomy increasing defection capacity" — [systems/model.json:1855](systems/model.json)
- **Actor analysis:** "A staged arrangement could improve incentives or make later defection easier. Evaluate both sides' ability and incentive to renege after the power distribution changes. Preserve infeasibility as a possible conclusion." — [docs/actor-analysis.md:144-149](docs/actor-analysis.md)
- **PR #2 resource tripwire list:** unauthorized acquisition of "land or property; physical infrastructure; … companies, contracts, logistics, energy, or robots" — PR #2 `docs/bootstrap-pacing.md:162-176`. It draws no line by location or by authorized off-Earth activity.
- **Vault caveat:** "Economic bootstrap ≠ existential survivability … true survivability without humans requires material self-sufficiency (C5: energy, compute, repair)" — VAULT `AI Breakout.md:244`. Off-Earth industry supplies C5.

### Inferences
- **Every dependence-based control needs a declared scope.** One option: "on Earth, and for Earth-reachable compute, preserve human vetoes; off Earth, permit autonomy under conditions X." Without that scope, a faithful renderer applying I5/D11/D12 would oppose the thesis.
  - The scope is itself a hypothesis: off-Earth and Earth capacity stay separable enough that autonomy over there does not become leverage over here. This mirrors YAML H1 (A/H/P separability) at planetary scale.
- **Second tension: denial versus low entanglement.** A denial deterrent works best when Earth's industrial and compute stock is cheap to lose (low E in D4). Progressive de-industrialization lowers both the prize and civilian dependence on it. That is consistent. But it may conflict with K2/K5's domestic political case and with H5 (domestic benefits sustain the institution, [spec/ai-pacing.yaml:430-444](spec/ai-pacing.yaml)). De-industrializing a host region is a hard sell to the constituencies Q8 and H5 rely on. (Inference.)
- **Third tension: the gravity well cuts both ways.** Earth's deep well makes Earth a poor export base, which supports the thesis. It also means an actor already in orbit holds the high ground: dropping mass down the well is cheap. A stronger off-Earth AI therefore gains positional leverage over Earth. This inference from orbital mechanics is not in the repo and needs sourcing. It is the physical basis of the "return" hazard in Q5.
- **Fourth tension: punishment-based deterrence weakens as autonomy grows.** Second strike needs targets humans can reach (VAULT `AI Breakout.md:218`: "If humanity cannot credibly hold AI future at risk … escalation will not be deterred"). Off-Earth autonomy moves the AI's future out of reach. This is why Cole's switch to denial (making Earth not worth taking) rather than punishment (threatening the AI) is the coherent choice. The repo should state that reasoning explicitly.

### Gaps
- No repo artifact analyses whether Earth-side and off-Earth industry can stay separable, or over what timescales. Nor does any artifact cover what "authorized off-Earth autonomy" would mean legally (jurisdiction, space law). Both are outside this repo's current content.

---

## Q5. How does the systems-engineering model handle this, and what would the thesis need?

### Takeaway
The uncommitted systems model (`systems/model.json`, 148 records, passes `systems_tool.py check`) has the right scaffolding: a conditional sovereignty-seeking AI actor, a cooperation scenario, an autonomy-versus-control conflict, and honest untested hypotheses. But it is anthropocentric and present-tense:
- Its five losses and five hazards have no planetary, long-horizon, relocation or return element.
- Off-Earth appears in none of its stakeholders, resources, scenarios or proposals.
- Its legacy map covers only the 29 YAML nodes, so editorial I3 is structurally invisible.

### Cited Findings
- **Check status:** "Systems model: 148 records; structural and evidence-gate checks passed; empirical validation remains open." (`python3 tools/systems_tool.py check`, run in this session)
- **Losses** — LOSS-SAFETY, LOSS-CONTROL, LOSS-DIFFUSION, LOSS-BENEFIT, LOSS-CONFLICT, all with stakeholders drawn from present-day actors — [systems/model.json:1022-1087](systems/model.json)
- **Hazards** — HAZ-OPAQUE, HAZ-LEAK, HAZ-LATE, HAZ-RACE, HAZ-CAPTURE — [systems/model.json:1088-1152](systems/model.json)
- **Resources:** RES-INFRA ("Compute, power, credentials, communications, and industrial capacity") is owned only by ACT-OPERATOR and ACT-LAB. There is no location attribute and no off-Earth resource — [systems/model.json:1009-1020](systems/model.json)
- **SC-COOPERATE:** success = "Cooperation incentives and effective controls survive specified changes in bargaining power". Adverse = "Rewards increase capacity to defect; promises are not credible". Hazards HAZ-RACE and HAZ-LATE only — [systems/model.json:1326-1354](systems/model.json)
- **CH-COOPERATE:** "Under what conditions can AI cooperation remain preferable to circumvention without sacrificing effective human control?" — [systems/model.json:1463-1475](systems/model.json)
- **INT-SOVEREIGN:** "Durable sovereignty can conflict directly with retained unilateral human control." The derivation is "seek a feasible conditional bargain without assuming sovereignty must be granted or is impossible" — [systems/model.json:3838-3895](systems/model.json)
- **UC-SOVEREIGNTY:** choices are Negotiate / Demonstrate cooperation / Wait / Reject / "Attempt circumvention". There is no "relocate" or "expand elsewhere" choice — [systems/model.json:3419-3450](systems/model.json)
- **PROP-AUTONOMY and PROP-BOUNDED:** `legacy_refs: []` — [systems/model.json:2301, 2322](systems/model.json)
- **Legacy map covers YAML only:** "The following map accounts for all 29 legacy YAML nodes" — [docs/systems-engineering.md:269](docs/systems-engineering.md). SRC-SPEC is pinned to "spec/ai-pacing.yaml at b1c4864…" — [systems/model.json:48-53](systems/model.json)
- **Namespacing is deliberate and helpful:** the model uses separate namespaces "to avoid confusion between HYP-* and legacy H*" — [docs/systems-engineering.md:114-119](docs/systems-engineering.md)
- **New records need no schema change if they use existing kinds.** "a new kind or relationship requires a reviewed schema and validator change and a model-version migration" — [docs/systems-engineering.md:125-126](docs/systems-engineering.md)
- **Acknowledged gaps** include "military and intelligence institutions, hardware and energy supply chains, affected-public subgroups" — [docs/actor-analysis.md:202-206](docs/actor-analysis.md)
- **Issue #1's cooperation split** is already planned to attach "staged autonomy and bounded incentives as alternatives" — [docs/systems-engineering.md:258-260](docs/systems-engineering.md)

### Inferences — records the thesis would need (proposed IDs; none exist yet)

**Losses**
1. **LOSS-RETURN** — Earth's people lose safety or agency to a later, stronger off-Earth machine civilization. Stakeholders: ACT-PUBLIC plus future generations.
2. **LOSS-DEINDUSTRIAL** — De-industrializing Earth imposes unjust welfare or distributional losses. Stakeholders: affected workers and host communities; a new affected-public subgroup.
3. **LOSS-DENIAL-HARM** — A denial deterrent misfires, is triggered falsely, or is captured, destroying Earth capacity or harming civilians.

**Hazards**
1. **HAZ-PRIZE** — Earth's seizable industrial and compute stock remains the highest-value target for a misaligned agent. Losses: LOSS-SAFETY, LOSS-CONTROL.
2. **HAZ-RETURN** — Off-Earth capability grows beyond Earth's ability to deny or bargain, while its incentive to stay outward lapses. This includes the high-ground asymmetry from the gravity well. Losses: LOSS-RETURN, LOSS-CONTROL.
3. **HAZ-DENIAL-FAIL** — The denial mechanism is not credible: it is observable and therefore defeatable, seizable, or spoofable. Losses: LOSS-CONTROL.
4. **HAZ-DENIAL-MISFIRE** — Losses: LOSS-DENIAL-HARM, LOSS-SAFETY.
5. **HAZ-COUPLING** — Off-Earth autonomy becomes leverage over Earth's survival chain through supply, launch, energy beaming or communications.

**Scenario and challenge**
- **SC-REDIRECT**: "A misaligned agent chooses between seizing Earth capacity and expanding off-Earth."
- Actors: ACT-AI (unspecified objectives, not only sovereignty-seeking), ACT-OPERATOR, ACT-PUBLIC, plus new ACT-SPACE-OPERATOR (launch and off-Earth industry) and ACT-DETERRENT-CUSTODIAN.
- Paired challenge **CH-REDIRECT**: "How can the expected payoff of Earth seizure be kept below that of off-Earth expansion for a broad class of misaligned objectives, without relying on AI commitments?"

**Requirements (candidates, with no threshold invented)**
1. **REQ-PRIZE** — relative attractiveness criterion. Tie it to HAZ-PRIZE.
2. **REQ-DENIAL** — denial must be credible against an agent with full knowledge of the mechanism's design, and safe against misfire and capture. Tie it to HAZ-DENIAL-FAIL and HAZ-DENIAL-MISFIRE.
3. **REQ-RETURN** — bound return risk across specified off-Earth growth trajectories. Tie it to HAZ-RETURN and HAZ-COUPLING.
4. **REQ-TRANSITION-LEGITIMACY** — affected communities have voice and remedy in Earth de-industrialization. Tie it to LOSS-DEINDUSTRIAL; it fits beside REQ-CONTEST.

**Hypotheses**
1. **HYP-GRADIENT** — Off-Earth marginal returns exceed Earth seizure value for the specified objective classes. Falsifier: plausible misaligned objectives are Earth-specific, or the AI must remove human threats to its off-Earth base.
2. **HYP-DENIAL** — A small maintained denial capacity can keep expected seizure value below threshold, even against an adversary who knows how it works. Falsifier: the capacity can be located, disabled, or seized faster than it acts.
3. **HYP-SEPARABLE-DOMAINS** — Earth and off-Earth industry stay decoupled enough that off-Earth autonomy is not leverage over Earth.

**Proposals**
1. **PROP-OFFEARTH-REDIRECT**, depending on HYP-GRADIENT and HYP-SEPARABLE-DOMAINS. Legacy ref: editorial I3, which needs the ID fix first.
2. **PROP-DENIAL**, depending on HYP-DENIAL. Legacy refs: YAML D4, I4, H4.
3. **PROP-EARTH-CAP**, the vault cap-K-with-throttles clause.

**Conflicts**
1. **CON-DEPEND-VS-REDIRECT** — PROP-DEPEND (keep AI dependent) versus PROP-OFFEARTH-REDIRECT (grant independence off Earth).
2. **CON-DENIAL-VS-BENEFIT** — denial and de-industrialization versus LOSS-BENEFIT.

**Other edits**
- Add a "relocate / expand off-Earth" choice to UC-SOVEREIGNTY and INT-SOVEREIGN.
- Add a location dimension to RES-INFRA, or split out a new RES-OFFEARTH-INDUSTRY.

### Gaps
- The model has no dynamic or trajectory representation. Return risk is a time-evolving hazard, and the model has no field for it. Representing it may hit the schema's "new kind requires schema change" rule ([docs/systems-engineering.md:125-126](docs/systems-engineering.md)). I did not inspect `schema/systems-model.schema.json` field by field to confirm.

---

## Q6. Concrete proposals: where the thesis should go in the canonical YAML

### Takeaway
1. Fix the ID collisions and provenance first.
2. Add the thesis as an explicitly non-kernel derived mechanism with three to four hypotheses and two open questions. Keep it non-kernel, consistent with the generator contract and the editorial "rejecting I3 does not invalidate the near-term proposal".
3. Coordinate numbering with issue #1, which already claims H6 and Q5.

### Cited Findings
- **The generator contract forbids** "Turn an implementation option into a kernel proposition" and "Change a proposition without checking its dependent claims" — [spec/ai-pacing.yaml:33-38](spec/ai-pacing.yaml)
- **Acceptance tests pin exact kernel IDs (AT-001):** [spec/ai-pacing.yaml:638-642](spec/ai-pacing.yaml). Every hypothesis needs `falsifier`, `evidence_needed`, `stopping_rule` (AT-007): [spec/ai-pacing.yaml:679-683](spec/ai-pacing.yaml). Implementations must be `replaceable: true` (AT-008): [spec/ai-pacing.yaml:684-688](spec/ai-pacing.yaml)
- **Next free YAML IDs:** D7, H6, I8, Q5 (from the node list at [spec/ai-pacing.yaml:201-571](spec/ai-pacing.yaml)). Issue #1 proposes "H6 — External-signal dependence" and "Q5 — Can a credible cooperative autonomy path reduce incentives for AI defection?" — issue #1 lines 27, 96
- **Issue #1's acceptance checklist** requires regenerating views, running `make check` and keeping drift disclosed — issue #1 lines 121-131, 141-148

### Inferences — proposed changes, numbered for accept/reject

**1. Repair before adding**
- (a) Renumber or alias editorial I3 so it no longer collides with YAML I3. Use a new YAML ID, or an `editorial_id` cross-reference.
- (b) Correct `affected_nodes` on EVT-2026-OFF-EARTH-CONVERGENCE (`yaml:161`) and EVT-2025-SAFETY-SPINE (`yaml:152`). Both say `H1`, which in the YAML means "separability", not "containment unstable".
- (c) Expand SRC-AI-BREAKOUT `contribution` (`yaml:69-71`) to name the Peaceful Breakout Clause, Earth industrial cap with throttles, off-Earth industrial break-even, and second-strike deterrence.
- (d) Consider adding the vault "AI Pacing" essay §XXI as a source, if it is not already the basis of SRC-PLAN-A-BARGAINING.

**2. Two new derived mechanisms (kernel unchanged)**
- **D7 — Redirect the misalignment blast radius outward.**
  - Candidate statement: "Make off-Earth industrial expansion a higher-return path than seizing terrestrial industry for a broad class of capable agents, so that alignment or control failures are more likely to express themselves away from Earth."
  - `derived_from: [K1, K2, K7]`, conditioned on H7 and H9 below.
  - This is the "Tai Chi" framing.
- **D8 — Make Earth's industrial base a poor prize.**
  - Candidate statement: "Combine low compute/industrial entanglement (D4), physical activation latency (I4), and a maintained denial capability so that seized terrestrial capacity has low and uncertain expected value."
  - `derived_from: [D4, K7]`, conditioned on H8.
- **Choosing between D and I typing:** D typing makes this a mechanism of the proposal. I typing keeps it as an option. Editorial typing was I. Moving it to D is a real editorial change Cole should make knowingly.

**3. New hypotheses** (start at H7 if issue #1 takes H6). Each needs falsifier, evidence_needed and stopping_rule to pass AT-007.
- **H7 — Relative-prize gradient.**
  - Off-Earth marginal industrial returns (solar flux without atmosphere or night, no life support, shallow wells) exceed the risk-adjusted value of seizing Earth's industry, for the specified agent objective classes.
  - Falsifier: realistic objective classes are Earth-specific, or require eliminating human threats first.
- **H8 — Denial credibility under ambiguity.**
  - A small maintained capability can make seizure of Earth capacity fail with probability high enough to deter, while staying robust to discovery, capture and misfire.
  - Falsifier: red teams locate, disable or seize it faster than it acts; or its misfire rate is unacceptable.
  - Issue #1's line 136 warning that uncertainty can increase preemption belongs in the stopping rule.
- **H9 — Domain separability and bounded return.**
  - Off-Earth autonomy does not create decisive leverage over Earth within the planning horizon.
  - Falsifier: off-Earth capacity gains positional or supply leverage over Earth's survival chain faster than Earth's denial and bargaining position can adapt.
- **H10 (optional) — Physical dependence and off-Earth autonomy can be scoped.**
  - D12/I5-style vetoes can be kept on Earth-reachable compute while off-Earth autonomy grows.
  - This makes the Q4 tension testable.

**4. New implementations** (replaceable, AT-008)
- **I8 — Earth industrial cap with automatic throttles.** From the vault clause. Record the open choice between "sunset at crossover" and "progressive de-industrialization".
- **I9 — Off-Earth industrial acceleration commitments.** Examples: launch, ISRU, and power-beaming investment.
- **I10 — Maintained denial reserve.** For example, deliberately low-entanglement terrestrial capacity with designed destruction or deactivation paths. Keep the engineering non-canonical, as D10 does for reserves.

**5. New open questions**
- Merge issue #1's Q5 (cooperative autonomy) with the off-Earth venue question, or keep them separate and add:
  - **Q6:** "Which agent objective classes does an outward payoff gradient redirect, and which does it not?"
  - **Q7:** "How should the decision to de-industrialize Earth be made legitimately, and who bears its costs?"
  - **Q8:** "What is the return-risk trajectory of a successful off-Earth machine civilization, and what keeps the relationship symbiotic?"

**6. Relations and tests**
- Add `grounds` edges K1/K2/K7→D7 and D4/K7→D8.
- Add `conditions` edges H7→D7, H9→D7 and H8→D8.
- Add `implements` edges D7→I8 and I9; D8→I10.
- Consider an acceptance test (AT-011) asserting that D7/D8 are not kernel and are conditioned by H7–H9. That protects against a renderer overstating the thesis.

**7. Explicit non-claims to add**
- "Off-Earth expansion is not a substitute for alignment."
- "The proposal does not aim to create a misaligned machine civilization."
- "Physical distance is not safe sovereignty" (adopting issue #1 line 137).
- "Denial capability is not a first-strike posture."

**8. Symbiosis goal.** Add a statement of the harmonious, symbiotic end state to `specification.purpose` ([spec/ai-pacing.yaml:10-13](spec/ai-pacing.yaml)) or as a kernel-adjacent normative note. This is a kernel-level decision for Cole. As written, the purpose is purely about slowing power conversion.

**9. Editorial reference.** Update dependency rule 8 ([AI_Pacing_Canonical_Spec_v0.1.md:485](AI_Pacing_Canonical_Spec_v0.1.md)) and the minimal-reconstruction paragraph only if Cole decides the thesis is part of the proposal's identity. Otherwise state its optional status there.

### Gaps
- Whether D or I typing is right depends on whether Cole sees the thesis as part of AI Pacing's identity or as a companion proposal ("AI Breakout"). The repo cannot answer that. It is an author decision.

---

## Q7. Quality review of PR #2 and the uncommitted systems-engineering work, and how each relates to the thesis

### Takeaway
**PR #2** is a well-disciplined, implementation-agnostic design note. Its economic-boundary tripwires and "exposure tax" hypothesis are natural companions to deterrence by denial, but it never mentions off-Earth or location. Its weaknesses:
- one commit with an empty message body;
- free prose not tied to YAML nodes;
- two invariants that overstate.

**The uncommitted systems-engineering work** is methodologically strong and honest about status. Its weaknesses:
- it is large and untracked, so at risk;
- its legacy map cannot see editorial-only content such as off-Earth I3;
- it frames AI incentives only as bargaining.

### Cited Findings — PR #2 (`docs/bootstrap-pacing.md`, single commit `f1e9277`, 258 additions, base `main`, head `bootstrap-pacing-interfaces`)

**Strengths**
- Explicit non-promotion: "proposes additional mechanisms … without silently promoting them into the kernel" — PR #2 line 5
- Replaceable interfaces throughout — PR #2 lines 23, 50, 71, 117, 158, 205
- Design invariants — PR #2 lines 207-220
- Failure conditions — PR #2 lines 246-256
- Named canonical review targets — PR #2 lines 222-231

**Economic-boundary tripwires.** Unauthorized acquisition of claims over "external rivalrous resources" such as money, compute, land, infrastructure, energy and robots. "Crossing such a boundary is not automatically proof of misalignment." — PR #2 lines 160-176

**Exposure-tax hypothesis.** Converting hidden capability into durable power "often requires actions that create observable causal effects in independently controlled human systems". The text says it "must remain a falsifiable hypothesis" — PR #2 lines 178-184. However, it has no falsifier, evidence or stopping-rule fields in the YAML style.

**"Design for opacity; exploit transparency opportunistically."** — PR #2 lines 129-143

**Possible overstatements**
- Invariant 6: "Marginal transparency always helps" — PR #2 line 216. This sits in tension with the systems model's HAZ-LEAK ("Sensitive artifacts leave effective custody during reporting or evaluation", [systems/model.json:1103-1113](systems/model.json)) and the CON-CUSTODY conflict ([systems/model.json:3025](systems/model.json)).
- Invariant 9: "Cheating becomes harder as independent observers increase" — PR #2 line 219. This is stated as an invariant but is really an empirical hypothesis.

**Process gaps**
- The commit's message body is empty (from `gh pr view 2 --json commits`).
- The PR cites YAML IDs (K3/D5/I1/I2, and so on) without pinning a commit — PR #2 lines 226-231.
- No mention of issue #1, off-Earth, or the systems model.

### Cited Findings — uncommitted systems-engineering work

**What changed in the working tree**
- `CANONICALITY.md` (+10 lines): a "Challenge workspace boundary" saying the model "does not inherit the proposal's kernel commitments" — [CANONICALITY.md:3-11](CANONICALITY.md)
- `Makefile` adds `systems-check` to `check` (`git diff Makefile`)
- `README.md` adds a stakeholder section — [README.md:3-22](README.md)
- Untracked: `docs/actor-analysis.md`, `docs/requirement-traceability.md`, `docs/systems-engineering.md`, `schema/systems-model.schema.json`, `systems/model.json` (3,968 lines), `test/systems_tool_test.py`, `tools/systems_tool.py`, and a `tools/__pycache__/` directory (`git status`)

**Strengths**
- Honest status typing: candidate / untested / unvalidated
- Separates needs from solutions: "Requirement text must remain understandable if every current proposal is removed" — [docs/systems-engineering.md:116-119](docs/systems-engineering.md)
- Records conflicts rather than scoring them: CON-AUTONOMY "unresolved; no aggregate score or implied priority" — [systems/model.json:3092](systems/model.json)
- Explicit self-correction about earlier bias — [docs/actor-analysis.md:5-16](docs/actor-analysis.md)
- Acknowledges it may be post-hoc: "these links must be scrutinized for post-hoc justification" — [docs/requirement-traceability.md:3-6](docs/requirement-traceability.md)
- A timing-margin formula that refuses to count warning without effect — [docs/systems-engineering.md:160-177](docs/systems-engineering.md)

**Weaknesses relevant to the thesis**
- The legacy map is limited to YAML — [docs/systems-engineering.md:269](docs/systems-engineering.md)
- PROP-AUTONOMY and PROP-BOUNDED have empty `legacy_refs` — [systems/model.json:2301, 2322](systems/model.json)
- All AI-incentive routes depend on HYP-AI, the bargaining assumption — [systems/model.json:2297-2299, 2318-2320](systems/model.json)
- No relocation choice in UC-SOVEREIGNTY — [systems/model.json:3434-3440](systems/model.json)
- Losses and hazards are present-tense and Earth-bound — [systems/model.json:1022-1152](systems/model.json)
- Narrow source base: most records cite only `SRC-SYNTHESIS` (an analyst synthesis, "not externally validated evidence", [systems/model.json:76-80](systems/model.json)) and a private handwritten-notes image ([systems/model.json:41-46](systems/model.json)).

### Inferences
- **PR #2 fits the thesis better than it appears.** Seizing Earth's industrial base is the extreme case of "unauthorized acquisition … of external rivalrous resources". Its exposure-tax logic says such seizure is maximally observable, which supports deterrence by denial. Two additions would connect it:
  - a clause distinguishing authorized off-Earth resource acquisition from terrestrial acquisition;
  - a link from the exposure-tax hypothesis to H8 (denial credibility).
- **"Design for opacity" fits the thesis directly.** Deterrence by denial and an outward payoff gradient both work without reading the AI's internal state. That property is worth stating, because it is why the thesis survives "alignment badly bungled".
- **Git practice.** About 4,000+ lines of systems-model work sit untracked on a branch whose upstream is pushed. One disk mishap or careless `git clean` loses it. Committing it on its own branch, separate from the README/Makefile edits, would protect it and keep the history reviewable. `tools/__pycache__/` should be ignored, not committed. PR #2's empty commit body is the kind of message to avoid.
- **Branch and base divergence.** PR #2 targets `main`, while the systems work and the Potapov commit live on `codex/ai-pacing-spec`. Any off-Earth integration should pick one integration branch so that the YAML, systems model and design notes reference the same commit. Local `main` is not checked out here: `git log main..HEAD` failed with "unknown revision". So I could not measure the divergence.

### Gaps
- I did not execute `make check` end to end; I only ran `systems_tool.py check` and the clean-room audit. So I do not claim the whole gate passes on the working tree.
- I did not review `schema/systems-model.schema.json` or `tools/systems_tool.py` line by line.
- I did not verify whether PR #2's base (`main`) contains the Potapov commit `b1c4864`.
