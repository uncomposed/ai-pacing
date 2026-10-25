# RE-Bench: fixed-budget comparisons (issue #58)

[[ai gen]] 2026-10-25. First reproducible milestone for #58. Part of #58, not all of it (see
[Status against #58](#status-against-58)).

RE-Bench (METR, arXiv:2411.15114) has 7 ML research-engineering environments. Agents and human experts
are scored on each under a time budget. Scores are normalized per environment: 0 is the starting
solution and 1 is the reference solution. This folder pins the released material, recomputes what can
be recomputed without running a task or a model, and records the fixed-budget comparisons as dated
evidence.

These are **fixed-budget benchmark scores**. They are not METR time horizons, which are a logistic fit
of success against human task time (`../metr-time-horizons/`, #12). They are also not research
productivity. [`observables.yaml`](observables.yaml) holds the separation and the tests enforce it.

## Status

| | |
|---|---|
| Source replication | Partial. Two things reproduce: the README score transforms (8/8) and the arithmetic of the paper's tables. The ceiling table reproduces for 6 of 7 environments. The headline fixed-budget curve (Fig. 1) does **not** reproduce: its data was never released. |
| Numerical correctness | `reproduce.py` recomputes everything from `data/`. `test_re_bench.py` (in `make check`) checks the committed results against a fresh recomputation within 1e-9. The workflow rebuilds `data/` from the pinned sources and compares within 1e-9 relative. |
| Empirical validation | None. Nothing is fitted or forecast. Matching a published table is not validation. |

## Sources (pinned; [`SOURCES.yaml`](SOURCES.yaml), [`sources.sha256`](sources.sha256))

- **RE-Bench repository**, `a0cc6d4` (2026-10-20, the last commit; archived, tasks deprecated). This
  commit only adds a notice to README.md, so the task files are those of `93b9806` (2025-01-30). MIT
  licence, with METR's request to keep the tasks out of training data. Nothing is vendored. No task was
  run.
- **Paper**, arXiv:2411.15114. The LaTeX source of v1 (2024-11-22) and v2 (2025-05-27) was read in
  full. METR's PDF on metr.org is v1. From v1 to v2 the only change to any number is the lines-of-code
  column.
- **METR's released runs**: the RE-Bench rows of `eval-analysis-public` at `52cb829`, the same pin as
  #12. TH1.0 has 7 environments, 32 agents and 91 human rows. TH1.1 has 5 environments, 20 agents and
  71 human rows.
- **Not available:** the paper's "analysis code and anonymized human expert data". The paper says they
  are "coming soon". On 2026-10-25 they were in none of METR's 41 public GitHub repositories, nor in
  the RE-Bench repository.

## What reproduces and what does not (`results/reproduction.json`)

| check | result |
|---|---|
| README start and reference scores equal the scoring code's transform of the README raw values (`log(loss-1.5)`, `log(s)`, `log(ms)`) | 8/8 within rounding |
| Paper ceiling table (raw ceiling, normalized with the README start and reference scores) | 6/7. **Scaling Law Experiment does not match.** The published 1.27-1.36 needs a reference score of about 0.80; the README gives 0.84, which yields 1.17-1.28. Rust Codecontests matches only with the unrounded reference score (implied 0.127; README 0.13). |
| Baseline-sourcing table: runs 45+17+9 = 71, people 43+11+7 = 61, run-weighted mean 0.644 against 0.64 | matches |
| Text against the same table | **Inconsistent.** The text gives 0.96 (professional network) and 0.46 (hiring); the table gives 0.98 and 0.48. |
| Abstract "82% of expert attempts achieve a non-zero score" against the paper's own validation table (> 0.05 at 8 h) | **Inconsistent.** 60/71 = 84.5%; 82% would be 58/71. |
| Validation claims: every environment > 70% making progress; > 80% of experts "matches expectation"; major issues in > 5% of runs | True as pooled (87.3%, 8.2%). Scaling Law alone is at 75% on "matches expectation". |
| METR's released human rows against the paper's validation table | Different run sets. Counts differ in every environment, e.g. Optimize LLM Foundry has 8 runs in the paper and 17 in TH1.0. The released human rows are not the paper's 71 baselines. |
| Agents 4x humans at 2 h; humans narrowly ahead at 8 h; humans 2x at 32 h; 36th/37th percentile at 8 h; 24% at or above the reference | **Not reproducible.** Needs per-run trajectories that were never released. |
| Attempt rates (36.8, 25.3, 3.4 per hour); $123 per agent run against $1,855 per human run | Not reproducible (needs run logs). Recorded as benchmark process, not productivity. |

## Fixed-budget comparisons

**From the paper** (`EV-REBENCH-PAPER-V1-2024`, revised as `EV-REBENCH-PAPER-V2-2025`; dated
2024-11-22). The comparison is best-of-k over independent runs, at equal total time.

- At 2 h, the best agents score 4x the human experts.
- At 8 h, humans are narrowly ahead.
- At 32 h, humans score 2x the top agent.

The agents are o1-preview in AIDE and Claude 3.5 Sonnet (20241022) in Modular. These figures are
recorded as quoted. They are not reproduced.

**From METR's released runs** (`data/fixed_budget.csv`; `EV-REBENCH-METR-TH10-2026-03-05`,
`EV-REBENCH-METR-TH11-2026-03-05`). This is a single run (best-of-1) of each agent, compared with the
human 8-hour baselines on the same environments. METR publishes no RE-Bench-only aggregate, so these
numbers are computed here, not reproduced.

How the score is computed:

- Each run's score is METR's `score_cont`. It runs from 0 to 1 and appears clipped at 1, unlike the
  paper's normalization.
- Runs are averaged within an environment. Environments then get equal weight.
- The interval is a 95% bootstrap over runs within each environment.
- The ratio is the agent mean divided by the human mean. The human mean is 0.72 on the 5 TH1.1
  environments.

TH1.1 is the closest the released data gets to an equal budget. Its Inspect runs have an 8-hour limit,
the same as the human baselines:

| agent | release | limit | runs | mean score [95%] | share >= reference | ratio to human |
|---|---|---|---|---|---|---|
| GPT-4 0314 | 2023-03-14 | 10 h | 30 | 0.04 [0.01, 0.06] | 0.00 | 0.05 |
| GPT-4 1106 (Inspect) | 2023-11-06 | 8 h | 19 | 0.00 [0.00, 0.00] | 0.00 | 0.00 |
| Claude 3 Opus (Inspect) | 2024-03-04 | 8 h | 20 | 0.00 [0.00, 0.01] | 0.00 | 0.01 |
| GPT-4 Turbo (Inspect) | 2024-04-09 | 8 h | 20 | 0.00 [0.00, 0.00] | 0.00 | 0.00 |
| GPT-4o (Inspect) | 2024-05-13 | 8 h | 20 | 0.00 [0.00, 0.00] | 0.00 | 0.00 |
| Claude 3.5 Sonnet (Old) (Inspect) | 2024-06-20 | 8 h | 20 | 0.26 [0.15, 0.38] | 0.15 | 0.36 |
| o1-preview | 2024-09-12 | 10 h | 36 | 0.07 [0.03, 0.12] | 0.00 | 0.10 |
| Claude 3.5 Sonnet (New) (Inspect) | 2024-10-22 | 8 h | 20 | 0.25 [0.14, 0.36] | 0.05 | 0.34 |
| o1 (Inspect) | 2024-12-05 | 8 h | 20 | 0.22 [0.09, 0.36] | 0.05 | 0.31 |
| Claude 3.7 Sonnet (Inspect) | 2025-02-24 | 8 h | 20 | 0.44 [0.34, 0.56] | 0.00 | 0.61 |
| o3 (Inspect) | 2025-04-16 | 8 h | 20 | 0.46 [0.38, 0.57] | 0.15 | 0.64 |
| Claude 4 Opus (Inspect) | 2025-05-22 | 8 h | 20 | 0.50 [0.34, 0.65] | 0.20 | 0.69 |
| Claude 4.1 Opus (Inspect) | 2025-08-05 | 8 h | 20 | 0.58 [0.49, 0.66] | 0.15 | 0.80 |
| GPT-5 (Inspect) | 2025-08-07 | 8 h | 20 | 0.70 [0.57, 0.82] | 0.40 | 0.98 |
| Gemini 3 Pro | 2025-11-18 | 8 h | 20 | 0.72 [0.60, 0.84] | 0.35 | 1.00 |
| GPT-5.1-Codex-Max (Inspect) | 2025-11-19 | 8 h | 30 | 0.78 [0.67, 0.88] | 0.43 | 1.09 |
| Claude Opus 4.5 (Inspect) | 2025-11-24 | 8 h | 20 | 0.74 [0.63, 0.85] | 0.40 | 1.03 |
| GPT-5.2 | 2025-12-11 | 8 h | 20 | 0.50 [0.37, 0.62] | 0.35 | 0.69 |
| Claude Opus 4.6 (Inspect) | 2026-02-05 | 8 h | 39 | 0.97 [0.91, 1.00] | 0.97 | 1.35 |
| GPT-5.3-Codex | 2026-02-05 | 8 h | 40 | 0.43 [0.33, 0.54] | 0.25 | 0.60 |

Read this table with these limits:

- **Clipping caps the ratio.** Because scores are clipped at 1, no agent can exceed about 1.39 (1/0.72).
  Claude Opus 4.6 is near that ceiling, so the clipped score no longer separates it from humans at the
  top.
- **The human interval is left out.** The interval covers agent runs only. The human mean is treated as
  fixed.
- **Scaffolds and limits differ.** Two legacy rows ran for 10 h.
- **This is not a capability trend.** No fit is made, and none should be read off the table.
- **TH1.0 is not an equal-budget comparison.** Its rows (32 agents, 7 environments) are in the CSV, but
  the agent limits are 10 or 20 h against the humans' 8 h.
- **This is not independent of the time horizons.** These are the same runs METR's TH1.0 and TH1.1
  horizons are fitted to.

## Research-productivity observations

RE-Bench has none. It scores short, self-contained environments. It measures no research output and no
research labour in real R&D. Two quantities in the paper sound like productivity, and both are recorded
as `benchmark_process` in `observables.yaml`:

- **Attempt rate.** Agents score 10x more often per hour than humans. This is a rate inside the
  benchmark.
- **Cost per run.** About $123 per agent run against about $1,855 per human run. This compares costs at
  unequal scores and leaves out GPU cost.

Neither is identified as a link in the units bridge. That agrees with the #42 recheck, which found no
identified research-productivity link. The developer-productivity studies already recorded for #12
(`EV-METR-RCT-2025`, `EV-METR-UPLIFT-2026`) cover coding tasks, not research. Other sources of direct
research-productivity observations are a follow-up.

## Files

| file | what |
|---|---|
| `fetch_sources.sh` | clones and downloads the pinned sources into `.upstream/` (git-ignored) and checks `sources.sha256` |
| `build_data.py` | cache to `data/` (standard library only) |
| `data/task_scores.csv` | versions, start and reference scores, and transforms per environment |
| `data/paper_values.json` | paper numbers taken by regex from the LaTeX (v2 values, plus the v1 differences) |
| `data/human_baselines.csv`, `data/fixed_budget.csv`, `data/run_dates.json` | aggregates of METR's released RE-Bench rows |
| `reproduce.py` | the checks above, written to `results/reproduction.json`; `--check` compares |
| `compare_data.py` | numeric-tolerance comparison of a rebuilt `data/` with the committed one |
| `observables.yaml` | the class of each quantity (fixed-budget score, benchmark process, ...) |
| `test_re_bench.py` | fast offline tests, run by `make check` |

## How to run

```sh
python3 research_notes/external/re-bench/test_re_bench.py       # offline, part of make check
python3 research_notes/external/re-bench/reproduce.py --check   # offline
bash research_notes/external/re-bench/fetch_sources.sh          # network: github.com, arxiv.org
python3 research_notes/external/re-bench/build_data.py --out /tmp/rb && \
  python3 research_notes/external/re-bench/compare_data.py /tmp/rb
```

The `re-bench-repro` workflow (`.github/workflows/re-bench-repro.yml`) runs the networked part by hand:
fetch, verify, rebuild and compare. It uploads its outputs as an artifact and never commits.

**Re-pinning.** If `fetch_sources.sh` reports a hash mismatch, a source has changed. Record the new pin
and the hashes, and add a new evidence record per `P-REVISIONS`. Do not overwrite `data/` silently.

## Status against #58

- [ ] **Pin RE-Bench and reproduce its released results, without new model evaluations.** Partly met.
  The pins are in place and nothing was run. Everything that can be recomputed from released material
  has been. The headline fixed-budget results cannot be, because their data is unreleased (stopping
  rule: no new evaluations).
- [x] **Record fixed-budget comparisons as dated evidence records, kept separate from time-horizon
  capability.** Done: 4 records, each listing time-horizon capability under `not_for`, with the shared
  runs declared.
- [x] **Record any direct research-productivity observations as a separate observable.** Done for
  RE-Bench, which has none. The `research_productivity` class exists in `observables.yaml` and is
  empty; the two lookalike quantities are classed as benchmark process.

The PR says `Part of #58` because the first box is only partly met.
