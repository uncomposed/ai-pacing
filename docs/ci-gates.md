# CI gates and required checks

Written 2026-10-25 for issue #7. This page describes the configured gates and the branch-protection settings
recommended once they are green on `main`. It changes no repository setting. Settings are changed by the repository
owner.

## 1. Four evidence categories, reported separately

The equilibrium model's gates (`research_notes/Off Earth industry as misalignment control/model/model_gates.py`)
report one status per category. A green check in one category says nothing about another.

| category | command (from `model/`) | CI job / step | a pass means | a pass does **not** mean |
|---|---|---|---|---|
| software and schema regression | `python model_gates.py software` | `model: numerical checks and software regression` (step `software: ...`) | unit tests pass; every cache has a valid manifest or inventory entry; `--check` output matches the committed copy except for the threshold-judged error measures; one cached ensemble re-solves to the cache | that the numbers are right: unchanged is not correct |
| numerical identities and approximations | `python model_gates.py numerics` | same job, step `numerics: ...` | error measures are below `CHECK_TOL` (1e-9). The saturation closed form agrees with the solver on strike/no-strike, is never later than it, and brackets the q_ea threshold. These are judged without any committed file. | that the model describes the world |
| external-model replication | `python model_gates.py replication` | `model: external-model replication (Saklakov, Clark)` | the solver, set to Saklakov's and Clark's limits, reproduces their closed forms and printed values to stated tolerances, and a deliberately broken solver fails the gate | that their assumptions hold, or anything about history |
| empirical validation | `python model_gates.py empirical` | same job as numerics, step `empirical validation: not established` | nothing: status is always `not_established` | — |

The repository-wide `make check` (job `software: make check (...)`) covers the spec, renderings, the systems
model, the assumption register and the model's unit tests. Convergence (stability in `nA`, `T_H` and ensemble size)
is not gated yet.

Powell, Potapov and Metzger are comparisons, not replications (`model/docking/replication.py`, `SOURCES`):
- Powell: his condition is evaluated on our quantities.
- Potapov: has no formal model; we test a formalisation we wrote.
- Metzger: his figure is read by eye.

They run only in the slow suite and never count toward the replication status.

## 2. Slow suites (not run on pull requests)

| workflow | trigger | what | why not on every PR |
|---|---|---|---|
| `docking.yml` | manual, weekly (Tue 05:41 UTC) | all five docking scripts. Saklakov and Clark fail the job on a switch point off its closed form or a sign disagreement. All five report drift against `docking/out/*.json`. | Saklakov about 9 min, Potapov about 12 min |
| `sims.yml` | manual, weekly (Mon 06:17 UTC) | ensemble stages; the weekly run re-solves `full__base` in 4 shards and compares with the cache | hours of compute |
| `breakout.yml` | push to `sims/breakout**`, manual | breakout-option ensembles | hours of compute |

`workflow_dispatch` and `schedule` take effect only once a workflow file is on `main`. A slow suite therefore
first runs after the PR that adds it is merged.

## 3. Integration with the locale fix (PR #4)

PR #4 (merged as `0351365`) adds `export LANG := C.UTF-8` to the `Makefile`, so every `make` target runs under a
UTF-8 locale. It interacts with the gates in four ways:

- `check.yml` already sets `LANG` and `LC_ALL` to `C.UTF-8` for every job, so CI was unaffected. PR #4 fixes local
  `make check` in a shell with no locale.
- The model gates call Python directly, not through `make`, so the Makefile export does not reach them. The
  workflows set the locale for these jobs (`check.yml`, and `docking.yml` from this change).
- `run_identity.py` reads sources and manifests as UTF-8 explicitly, so a run identity never depends on the locale.
- Run the model commands in a UTF-8 shell or the pinned venv recipe in `CLAUDE.md`.

The run that exposed the threshold problem (40215844769, PR #4) failed `compare-checks` on a 1.1e-12 error
measure. That was fixed in #17: error measures are now judged by `CHECK_TOL`, not by equality.

## 4. Operational state, rechecked 2026-10-25

- `main` is unprotected: `GET /repos/uncomposed/ai-pacing/branches/main` returns `protected: false`, with no
  required status checks. `GET /rulesets` returns an empty list.
- `check.yml` has run on pull requests and on pushes to `main`; for example, run 40217301491 on PR #21 and run
  40216945111 on `main`, both successful. The job names in section 1 first run on the PR that adds this page.
- `sims.yml` and `breakout.yml`: only the breakout run of 2026-10-21 (39637590689) has run on GitHub.
  `docking.yml` has not run.

This is a snapshot, not a permanent fact. Recheck it before changing settings.

## 5. Recommended required checks and branch protection

Apply only after the three jobs below have passed on `main` at least once, and only by the repository owner.

Required status checks on `main`, by their exact job names (renaming a job silently drops it from protection):

1. `software: make check (spec, renderings, systems model, model unit tests)`
2. `model: numerical checks and software regression`
3. `model: external-model replication (Saklakov, Clark)`

Do not require `docking`, `sims` or `breakout`. They do not run on pull requests, so a required check from them
would block every merge.

Branch protection (or an equivalent ruleset) for `main`:

- Require a pull request before merging, so no direct pushes.
- Require the three status checks above to pass.
- Require branches to be up to date before merging. This is optional: it re-runs CI after every merge to `main`,
  which slows a busy queue but catches semantic merge conflicts in committed outputs. Recommended for model
  changes.
- Block force pushes and deletion of `main`.
- Leave required reviews to the owner's choice. With one maintainer, a required approving review blocks the
  maintainer's own PRs.

A required green check establishes only its own category (section 1). Never close an empirical-validation issue
on the basis of CI success.
