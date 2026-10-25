# CLAUDE.md

Agent guidance for this repository. Humans: see `CONTRIBUTING.md`.

## Commands

Run from the repo root. Use a UTF-8 locale and the pinned Python environment.

```sh
python3.12 -m venv .venv && .venv/bin/pip install -r .github/requirements-ci.txt
export PATH="$PWD/.venv/bin:$PATH" LANG=C.UTF-8 LC_ALL=C.UTF-8
make check          # the gate: tests, systems model, assumption register, spec, stale views
make generate       # rebuild generated/ from spec/ai-pacing.yaml (see rules below)
ruby tools/spec_tool.rb impact K4   # downstream nodes of a proposition
```

Model checks (CI job `model-check`), from
`research_notes/Off Earth industry as misalignment control/model/`:

```sh
python robust_design.py --check
python ci_sims.py compare-checks
python ci_sims.py repro --args "--stage oat_r --designs '[{}]'" --manifest repro_r0.1_base.json
```

These overwrite files under `results/`. Check `git status` afterwards and restore
anything you did not mean to change.

Cached ensemble runs (`results/*_runs/*.npz`) are reused only when their run
manifest's identity matches (`run_identity.py`; HANDOFF.md section 8b). Never
delete, overwrite or hand-edit a cache or `results/cache_provenance.json`; a
refused cache means the request changed, so re-solve into another `--runs-dir`.

## Environment

- Pins: Python 3.12, numpy 1.26.4, matplotlib 3.9.2, jsonschema 4.23.0
  (`.github/requirements-ci.txt`). A newer Python or numpy 2.x may give slightly
  different floats; use the pinned venv when exact numbers matter.
- `LANG=C.UTF-8` is needed; the Ruby tools handle non-ASCII text. The Makefile
  exports it for `make` targets; set it yourself for direct `ruby`/`python` runs.
- Rendering tests resolve historical commits, so the clone needs full history.

## Rules

- Authority order: Git commit, then `spec/ai-pacing.yaml`, then `.idea/*`, then
  the editorial Markdown, then everything else (`generated/`, renderings,
  research) as projections. See `CANONICALITY.md`.
- Never regenerate committed outputs (`generated/`, `results/`, `.npz` caches,
  figures) to hide drift or a mismatch. Find the cause, report it, and keep
  negative results. Do not loosen a check to make it pass. Run `make generate`
  only after an intentional spec or generator change, and commit its output
  with that change.
- Propose spec nodes only. New nodes get `provenance.author_status: proposed`;
  never write `accepted*`. The canonical editor accepts.
- Node IDs come from the single reserved-ID registry under `spec/`. Reserve
  before use; never pick the next number yourself, reuse or renumber.
- Keep three things separate: replication of a source model, numerical
  correctness, empirical validation. Never claim more than was shown. Ensemble
  shares are sampling-measure outcomes, not calibrated probabilities.
- CI: `check.yml` runs on every PR. `sims.yml` and `breakout.yml` are run by
  hand and never commit; a person reviews their artifacts before committing.

## Where things are

- Spec: `spec/ai-pacing.yaml`; tools in `tools/`; tests in `test/`; schemas in `schema/`.
- Model docs: `research_notes/Off Earth industry as misalignment control/model/HANDOFF.md`
  (start here; CI section), `results/equilibrium.md`, `results/robust_design.md`,
  `results/docking.md`, and the assumption register `assumptions.yaml`
  (`make assumptions-report`).
- Systems workspace: `systems/model.json`, `docs/systems-engineering.md`.
- Verification strategy: `docs/verification.md`.

## Commits

Short imperative subject, one logical change per commit, topic branch named
`<prefix>/<topic>`, PR against `main` using the PR template. Use `Closes #N` only
when every Done-when box is met, else `Part of #N`.
