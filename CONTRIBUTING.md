# Contributing to AI Pacing

This repository is a versioned, machine-readable idea (the specification), a set of
deterministic views of it, and a research workspace around it. Contributions are
welcome as issues and pull requests. The rules below exist so that a reader can
always tell what is canonical, what is a projection, and how much of a result is
actually established.

## Repository layout

| Path | What it is | Authority |
|---|---|---|
| `spec/ai-pacing.yaml` | The canonical specification (K, D, H, I, Q nodes, sources, acceptance tests). | Normative |
| `.idea/` | IRAP registry identity: `manifest.yaml`, `verifiers.yaml`, `verification-policy.yaml`, `publication.yaml`. | Normative for identity and verification policy |
| `AI_Pacing_Canonical_Spec_v0.1.md` | Supplied editorial reference, used to audit the YAML. Known to diverge (`make clean-room-audit`). | Reference only |
| `generated/` | Deterministic views of the YAML (canonical JSON, claims CSV, graph, audit trail, matrices). | Projection |
| `renderings/`, `examples/renderings/` | Renderings (for example the draw.io dependency map) and their rendering envelopes. | Projection |
| `schema/` | JSON Schemas for the spec, rendering envelopes and the systems model. | Tooling |
| `tools/` | Ruby and Python tools: `spec_tool.rb`, `rendering_tool.rb`, `irap_tool.rb`, `registry_payload.rb`, `clean_room_tool.rb`, `systems_tool.py`, `assumptions_tool.py`. | Tooling |
| `test/` | Unit and mutation tests for the tools. | Tooling |
| `systems/model.json` | Systems-engineering challenge workspace (stakeholders, hazards, requirements, candidate solutions). A draft, not part of the proposal. | Draft, separate from the spec |
| `docs/` | Verification strategy, systems engineering, clean-room reconstruction, actor analysis, off-Earth pact note. | Explanatory |
| `eval/clean-room/` | Clean-room reconstruction rubric. Keep it away from the generator. | Verifier material |
| `reports/`, `research_notes/` | Research. `research_notes/Off Earth industry as misalignment control/` holds notes and the equilibrium model (below). | Research, not normative |

The off-Earth model lives in
`research_notes/Off Earth industry as misalignment control/model/`. It has
`equilibrium_model.py` (solver), `robust_design.py` and `robust_report.py`
(ensembles and reports), `breakout_options.py`, `ci_sims.py` (CI helper),
`assumptions.yaml` (assumption register), `docking/` (comparisons with published
models), and `results/` (committed outputs, including cached `.npz` ensembles).
Read its `HANDOFF.md` before changing it; the CI section there explains the checks.

## Authority order

From [`CANONICALITY.md`](CANONICALITY.md):

1. An exact Git commit identifies an immutable state of the idea.
2. Within it, `spec/ai-pacing.yaml` is the normative specification.
3. `.idea/manifest.yaml`, `.idea/verifiers.yaml` and `.idea/verification-policy.yaml`
   define IRAP identity and verification policy.
4. `AI_Pacing_Canonical_Spec_v0.1.md` is the editorial reference.
5. Everything under `generated/`, diagrams, websites and essays is a projection and
   never overrides the YAML.

Research notes and the model are not part of this order. They do not change the
specification; they can motivate a proposed change to it.

## Running the checks locally

Requirements: Ruby (CI uses 4.0), Python 3.12 and the pinned packages. Use a
UTF-8 locale; the Ruby tools read and write non-ASCII text.

```sh
python3 -m venv .venv
.venv/bin/pip install -r .github/requirements-ci.txt   # numpy 1.26.4, matplotlib 3.9.2, jsonschema 4.23.0
export PATH="$PWD/.venv/bin:$PATH" LANG=C.UTF-8 LC_ALL=C.UTF-8
make check
```

`make check` runs the unit and mutation tests, `make systems-check`,
`make assumptions-check`, and `ruby tools/spec_tool.rb check` (structure, typed
layers, ten semantic acceptance tests, JSON Schema conformance, and whether the
committed views in `generated/` are stale). Other targets: `make validate`,
`make accept`, `make test`, `make systems-report`, `make assumptions-report`,
`make clean-room`, `make clean-room-audit` (diagnostic only, not part of `check`).
`.venv/` is not in `.gitignore`; do not commit it.

The rendering tests resolve historical commits, so they need full git history
(`git fetch --unshallow` if your clone is shallow; CI uses `fetch-depth: 0`).

### Model checks

CI also runs the equilibrium model against its committed outputs (job
`model-check`). Locally, from the model directory, with the pinned venv active:

```sh
cd "research_notes/Off Earth industry as misalignment control/model"
python robust_design.py --check                # round-1 regression, identities, closed forms
python ci_sims.py compare-checks               # compare with the committed reference
python ci_sims.py repro --args "--stage oat_r --designs '[{}]'" --manifest repro_r0.1_base.json
```

`--check` and `repro` write files under `results/` and the model directory. If you
run them in your working tree, `git status` afterwards and do not commit changes you
did not intend (see "No silent regeneration" below). Match the pinned versions when
exact numbers matter. Even with them, floats can differ in the last bits across
platforms: on one Linux x86-64 machine with the pinned packages, `--check` passed but
`compare-checks` reported `$.reg_maxdiff: 0.0 vs 1.1226575225009583e-12 (beyond
tolerance)` against the committed reference. If you see this, report it with your
platform; do not overwrite the reference or loosen the tolerance.

## Regenerating views

`generated/` is rebuilt from the YAML:

```sh
make generate
make check
```

Do this only when you changed `spec/ai-pacing.yaml` (or the generator in
`tools/spec_tool.rb`) on purpose, and commit the regenerated files in the same
change. If `make check` reports a stale view and you did not touch the spec or the
generator, find out why before regenerating; regenerating to make the gate pass
hides the drift.

## Continuous integration

- `.github/workflows/check.yml` runs on every pull request and every push to
  `main`: `make check` plus the model checks above. No secrets, read-only token.
  Python and package versions come from `.github/requirements-ci.txt`; change them
  only together with a re-check of every committed output.
- `.github/workflows/sims.yml` runs the model's ensemble stages. Start it by hand
  (Actions tab, sims, Run workflow). It also runs weekly as a reproducibility
  check against the committed cache.
- `.github/workflows/breakout.yml` runs the breakout-option ensembles. Start it by
  hand (or push a branch named `sims/breakout...`).
- sims and breakout never commit or push. They upload artifacts. A person
  downloads them, reads them, and commits the outputs deliberately. Do not
  automate that step, and do not commit an artifact you have not reviewed.

## Proposing spec changes

The canonical editor (Cole Miller, see `specification.responsibility` in the YAML)
decides what enters the specification. Contributors propose; they do not accept.

1. Open a spec-proposal issue (template provided). Name the kind: `K` kernel,
   `D` derived, `H` hypothesis (needs a falsifier, evidence requirement and
   stopping rule), `I` replaceable implementation, `Q` open question. Give the
   candidate statement, what it depends on or supports, and what would falsify it.
2. Node IDs come from a single reserved-ID list; see the reserved-ID registry under
   `spec/`. Reserve an ID there before using it, and never reuse or renumber one.
   Do not pick the next free number from your own reading of the YAML.
3. In the PR, add the node as proposed: `provenance.author_status: proposed`, with
   honest `origin`, `sources` and `ai_roles`. The tooling only requires a non-empty
   status, so this is a convention you are responsible for. Do not write
   `accepted*` yourself; the editor changes that, and AI-assisted proposals must say
   so in `ai_roles`.
4. Check downstream effects first: `ruby tools/spec_tool.rb impact <ID>`. Never turn
   an implementation option into a kernel proposition, or a hypothesis or open
   question into a conclusion (see `generator_contract` in the YAML).
5. Run `make generate` and `make check`, and commit the regenerated views with the
   spec change.

Changes to existing accepted nodes follow the same route and need an explicit
note on what changes and which dependents were checked.

## Evidence standards

The repository separates three things that are easy to conflate. Say which one
your result is.

- **Replication of a source model**: your code reproduces a published model's own
  outputs, in its own units, within a stated tolerance. It says nothing about the
  world.
- **Numerical correctness**: the solver does what its equations say (closed-form
  checks, identities, convergence, cross-platform stability). It says nothing about
  whether the equations are right.
- **Empirical validation**: predictions are compared with observations, with
  frozen cutoffs and simple baselines, separating retrospective tests from locked
  forecasts. Author or stakeholder agreement is not empirical support.

Rules that follow:

- Never overclaim. Use the status words in the existing notes (`implemented`,
  `verified`, `human_validated`) accurately; only the person named in the register
  can set `human_validated`.
- Ensemble shares come from a sampling measure, not calibrated probabilities.
  Report the measure, horizon and predicate with the number.
- Preserve negative results and failed checks. Write them up; do not delete them.
- **No silent regeneration.** Do not regenerate committed outputs (`generated/`,
  `results/`, cached `.npz`, figures) to make a mismatch disappear. If an output
  changes, explain why in the PR, and show the old and new values. A reproducibility
  failure is a finding, not something to overwrite. Do not loosen a check to pass.
- Parameters belong in `assumptions.yaml`; `make assumptions-check` fails when they
  drift from the model.

## Branches, commits and pull requests

From the history:

- Work on a topic branch, not `main`. Branches are named `<prefix>/<topic>`
  (`claude/off-earth-pact`, `codex/ai-pacing-spec`, `ci/github-actions`); simulation
  runs use `sims/breakout...`. Open a pull request against `main`.
- Commit subjects are short, imperative and specific ("Add assumption register for
  the off-Earth pact model, checked by make check", "Fix world-sweep crackdown rows
  and add the chi0-near-1 ablation script"). One logical change per commit.
- Commit bodies say what was verified and what was not.
- If an AI system wrote part of the change, keep the trailers your tool adds.
- Use the pull request template. `Closes #N` only when every Done-when box of the
  issue is met; otherwise `Part of #N` and list which boxes are done.
- Do not merge your own PR if you are not the maintainer, and do not push to `main`.
- Keep spec changes and model changes in separate PRs where you can: they rest on
  different evidence.
