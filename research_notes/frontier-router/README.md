# Frontier-comparison router

Research note for proposed nodes I12 and Q17 ([issue #89](https://github.com/uncomposed/ai-pacing/issues/89)).
This is research, not specification. It can motivate a proposal; it does not change
`spec/ai-pacing.yaml`.

**Evidence status.** `router_model.py` is arithmetic on assumed inputs. It is checked
against its own closed forms, identities, and a seeded Monte Carlo in
`test_router_model.py`. Nothing here is replicated from a published model, and nothing
is empirically validated. Every dollar figure follows from the inputs at the end of `router_model.py` (`BASE`, `RATCHET`, `SHOPPING`)
and changes when they change.

## 1. The mechanism

K4 and K6 both depend on an *observable public frontier*, and H3 asks whether that
frontier can be measured well enough to govern. The router is a way to measure it:

- **Terms of service.** Anyone who uses the router accepts that, on some requests,
  their prompt is also answered by a second model. This is part of the product, not
  an opt-in. The user always gets the model they asked for. When a second answer
  was drawn, the user gets whichever answer is judged better at no extra charge.
- **Blinded comparison.** Each pair is judged with the model identities hidden.
  Checkable outcomes come first: tests that pass, answers that verify, agent runs
  that finish. Behavioural signals the router already sees count too: retries,
  switching to another model, whether the user kept the output. A model judge
  handles the rest.
- **Sampling by information, not volume.** The second model is chosen, and the
  request is chosen for comparison, where the answer is least known: domains with
  few comparisons and model pairs whose ratings are close. A few thousand creative-
  writing comparisons are enough, and the long tail gets its share.
- **Output.** A per-domain rating for every tracked model, with error bars, against
  a frontier reference. Section 3 says why the reference should exclude
  signatories.

What it measures: the economic frontier as it is served through APIs, across many
domains, continuously, on fresh prompts that no one could have trained on.

What it does not measure:

- First-party products. Agentic tools, computer use, and enterprise deployments
  served by labs directly carry extra tooling that a raw API call does not, which
  is H3's "hidden scaffolds" falsifier.
- Internal models.
- Rare dangerous-capability domains. These should not be sampled from organic
  traffic: copying a flagged prompt to a second model doubles its exposure.
  Flagged prompts are excluded from comparison.

The router does not reduce risk from users who split a task across providers. It is
one more provider, and a user can send it only the harmless pieces.

## 2. Does it pay for itself?

The requirement is that measurement is not a net cost: break-even is acceptable, a
small surplus is better. The point that settles it is that **the number of
comparisons a frontier estimate needs is set by the precision wanted, not by
traffic.** For a win-rate half-width h at 95% confidence, each (domain, model) cell
needs n = 1.96² · 0.25 / h² comparisons. That is a fixed cost per period. The routing
fee scales with spend. So above some throughput the fee covers the measurement, and
the share of spend it takes keeps falling as the router grows.

Base inputs (all assumed): 200 domains, 12 tracked models, a task mix of 80% short
tasks ($0.015 per comparison including judging) and 20% long agentic tasks ($0.60),
1 billion requests a month, and a 5.5% fee, which is
[OpenRouter's reported standard rate](https://www.truefoundry.com/blog/openrouter-pricing).

| Half-width h | Margin floor (Elo) | Comparisons/month | Cost $/month | Share of requests sampled | Break-even routed spend $/month |
|---:|---:|---:|---:|---:|---:|
| 0.05 | 34.9 | 924,000 | 121,968 | 0.09% | 2.2 M |
| 0.03 | 20.9 | 2,563,200 | 338,342 | 0.26% | 6.2 M |
| 0.02 | 13.9 | 5,762,400 | 760,637 | 0.58% | 13.8 M |
| 0.01 | 6.9 | 23,049,600 | 3,042,547 | 2.30% | 55.3 M |

How to read it:

- **Precision is the cost driver, and it sets the pace limit.** A release margin
  ε smaller than the measurement's half-width cannot be enforced, because it cannot
  be told apart from noise. Halving the margin quadruples the cost (cost ∝ 1/ε²).
  The tightest pace the pledge can enforce is therefore a budget line.
- **The numbers are an upper bound on comparisons.** Each comparison informs two
  models' cells, not one. Adaptive matchmaking, such as Inclusion Arena's proximity
  sampling, cuts the count further.
- **Extra revenue lowers the threshold.** At h = 0.03, break-even falls from $6.2 M
  to $5.6 M a month of routed spend with a 0.5-point premium for the best-of-two
  feature, and to $4.3 M with $100k a month from selling aggregate frontier
  reports. Natural buyers are AI insurers, safety institutes, and procurement
  offices. Raw prompt–answer pairs are never sold: that is the distillation channel
  the release pledge is meant to close.
- **Agentic tasks dominate cost.** They are 20% of comparisons and about 90% of the
  spend in the base mix. They are also where frontier differences show most, so
  under-sampling them to save money would be the wrong economy.

## 3. Which releases set the reference: the leapfrog ratchet

The pledge as first stated: a signatory releases nothing more than ε above the best
model *anyone else* has released. If "anyone else" includes other signatories, two
signatories can take turns. A releases at B + ε, then B at A + ε, and so on. Nobody
breaks the rule, and the frontier rises ε per release.

`simulate_frontier` runs signatories on a staggered release cycle with internal
capability well ahead (assumed: ε = 10 Elo, a 6-month cycle per lab,
non-signatories improving at 1 Elo a month):

| Signatories | Reference includes signatories | Reference is non-signatories only |
|---:|---:|---:|
| 1 | 1.00 | 1.00 |
| 2 | 3.33 | 1.00 |
| 3 | 5.00 | 1.00 |
| 5 | 8.33 | 1.00 |

Frontier speed is in Elo per month; the simulation matches the closed form
k · ε / interval exactly. Under the first rule, **more signatories make the frontier
move faster**, which is the opposite of what the pledge is for. Referencing
non-signatories only, plus a shared signatory ceiling that moves only through K4's
adversarial review, holds the frontier to the pace of the fastest lab that has not
signed. A second requirement follows: only independently developed models should
count toward the reference. Otherwise a signatory can raise its own ceiling by
licensing or leaking to a non-signatory that releases first.

## 4. Counting every submission: variant shopping

A lab that may measure m variants and release any one that comes in within ε gets a
model through with probability 1 − (1 − Φ((ε − x)/σ))^m, where x is its true excess
above the frontier and σ is the measurement noise. The excess admitted at a 50% pass
rate, with ε = σ = 10 Elo:

| Variants m | Admitted excess (closed form) | Monte Carlo, 20,000 trials |
|---:|---:|---:|
| 1 | 10.0 | 9.97 |
| 3 | 18.2 | 18.2 |
| 10 | 25.0 | 25.0 |
| 27 | 29.5 | 29.5 |

With 27 tries, the rule admits a model about 2σ above where it should stop. Twenty-
seven is the number of private Llama 4 variants that
[The Leaderboard Illusion](https://arxiv.org/abs/2504.20879) reports Meta tested on
LMArena before release. The fix is procedural: register every variant before
measurement, and rule on all of them, not on the best-measuring one.

## 5. Gaming the router

- **Detection.** A provider can recognize router traffic and serve it a different
  model. Countermeasures: accounts that cannot be linked to the router, and spot
  checks against the provider's direct API.
- **Opposite incentives.** A signatory wants to measure low, to stay within ε. A
  non-signatory may want to measure high, for market share. Each direction needs
  its own checks.
- **Style over substance.** Judges, human or model, reward polish. This is the main
  known failure of preference arenas. Weight checkable outcomes heavily.

## 6. Related work

This design combines pieces that already exist separately. What is new is using
organic traffic under terms of service, paying for it from the routing fee, and
feeding the result into a release rule.

- **LMArena** (formerly Chatbot Arena). Volunteers vote between two anonymous
  answers, and Bradley–Terry ratings are fitted to the votes.
  [The Leaderboard Illusion](https://arxiv.org/abs/2504.20879) (Singh et al., 2025)
  documents private-variant testing and selective disclosure: section 4's problem.
- **Scale AI, SEAL Showdown** (2025). During normal chat, users are sometimes
  invited to compare their current model with a random opponent, blind, with
  results segmented by country, language, and profession.
  [Methodology](https://scale.com/showdown/methodology),
  [tech report](https://static.scale.com/uploads/654197dc94d34f66c0f5184e/SEAL_Showdown_Tech_Report.pdf).
  This is the closest existing match to in-traffic comparison, but it is opt-in
  per comparison and not tied to any governance rule.
- **Inclusion Arena** (Ant Group, 2025). Comparisons are built into two live apps,
  with over a million battles and proximity sampling that pairs models of similar
  rating so each comparison carries more information.
  [arXiv:2508.11452](https://arxiv.org/abs/2508.11452).
- **Yupp** (2025–2026). Every prompt was answered by two models, users picked the
  better one and were paid in credits, and preference data was sold to labs. It
  reported 1.3 M users. It shut down in March 2026, reportedly because labs moved
  their demand to expert-written data and agentic evaluation.
  ([SiliconANGLE](https://siliconangle.com/2025/06/13/yupp-launches-33m-build-crypto-incentivized-ai-evaluation-platform/),
  shutdown reported by [AI Chief](https://aichief.com/news/chris-dixons-33m-bet-fails-as-yuppai-shuts-down/)).
  This is the most direct warning on economics: a business that sells preference
  data to labs depends on labs wanting it. This design charges for routing and
  treats measurement as a cost the fee absorbs, so it does not need that market.
- **OpenRouter.** It publishes usage rankings, which show what people choose, not
  what models can do. Its fee structure is the reference for section 2.

## 7. Open points

- What domain list? The cells are only as good as the taxonomy (Q1).
- How to treat first-party products, which the router never sees.
- Whether the frontier reference should be per domain (a model within ε on average
  can lead by far more in one domain) and how a per-domain rule handles a domain
  with too few comparisons to rate.
- Whether the router itself should be a signatory-neutral nonprofit, a public-
  benefit company, or a public utility; it cannot be owned by a lab.

## Files

| File | What it is |
|---|---|
| `router_model.py` | Measurement cost, break-even, ratchet simulation, variant shopping. `--check` compares with the committed results. |
| `test_router_model.py` | Closed-form, identity and Monte Carlo checks; run by `make check`. |
| `results/scenarios.json` | Committed output of `router_model.py --write` for the inputs `BASE`, `RATCHET` and `SHOPPING`. |
