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
| `spec/id-registry.yaml` | Reserved-ID registry: every K, D, H, I, Q ID used or reserved in the YAML, the editorial reference, research notes and issues. Checked by `make check`. | Normative for ID allocation |
| `.idea/` | IRAP registry identity: `manifest.yaml`, `verifiers.yaml`, `verification-policy.yaml`, `publication.yaml`. | Normative for identity and verification policy |
| `AI_Pacing_Canonical_Spec_v0.1.md` | Supplied editorial reference, frozen at its 2026-08-29 state. Used to audit the YAML against the original intent; the divergence is recorded in `docs/editorial-reference-status.md` (`make clean-room-audit`). | Historical reference, not updated |
| `generated/` | Deterministic views of the YAML (canonical JSON, claims CSV, graph, audit trail, matrices). | Projection |
| `renderings/`, `examples/renderings/` | Renderings (for example the draw.io dependency map) and their rendering envelopes. | Projection |
| `schema/` | JSON Schemas for the spec, the ID registry, rendering envelopes and the systems model. | Tooling |
| `tools/` | Ruby and Python tools: `spec_tool.rb`, `rendering_tool.rb`, `irap_tool.rb`, `registry_payload.rb`, `clean_room_tool.rb`, `systems_tool.py`, `assumptions_tool.py`. | Tooling |
| `test/` | Unit and mutation tests for the tools. | Tooling |
| `systems/model.json` | Systems-engineering challenge workspace (stakeholders, hazards, requirements, candidate solutions). A draft, not part of the proposal. | Draft, separate from the spec |
| `docs/` | Verification strategy, systems engineering, clean-room reconstruction, actor analysis, off-Earth pact note, proposed extensions (`proposed-extensions.md`). | Explanatory |
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
4. `AI_Pacing_Canonical_Spec_v0.1.md` is the frozen editorial reference (2026-08-29).
5. Everything under `generated/`, diagrams, websites and essays is a projection and
   never overrides the YAML.

Research notes and the model are not part of this order. They do not change the
specification; they can motivate a proposed change to it.

## Running the checks locally

Requirements: Ruby (CI uses 4.0), Python 3.12 and the pinned packages. Use a
UTF-8 locale; the Ruby tools read and write non-ASCII text. The Makefile exports
`LANG=C.UTF-8` for `make` targets, but set it in your shell too when you run
`ruby tools/...` or the model scripts directly.

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
`.venv/` is git-ignored.

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
exact numbers matter. Floats can still differ in the last bits across platforms, so
`--check`'s error measures (`reg_maxdiff` and the two identity differences) are
judged against `CHECK_TOL` in `robust_design.py` rather than compared with the
committed copy; every other number must match the reference. Do not loosen those
thresholds or overwrite the reference to make a failure go away.

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
2. Node IDs are the kind letter plus the number of the proposal issue: a
   hypothesis proposed in issue #95 is H95. GitHub allocates the number, so two
   branches cannot reserve the same ID. An issue may propose at most one node of
   each kind; to bundle several nodes of one kind, open one issue per node and
   link them. The reserved-ID registry `spec/id-registry.yaml` is still the one
   list of every ID used or reserved across the YAML, the editorial Markdown,
   research-note candidates and issue proposals. IDs allocated before
   2026-11-06 keep their sequential numbers; `legacy_ceiling` is frozen and
   `next-id` is retired. To reserve an ID:
   - run `ruby tools/spec_tool.rb issue-id H 95` (or `K`, `D`, `I`, `Q`), which
     checks the number is at or above `issue_numbering.min_issue` and not yet
     registered, and prints the ID;
   - add an entry under `ids:` with that `id`, its `kind`, `collision: none`, and
     one definition. Use `{source: yaml, title: <node title>, status: proposed}`
     when the node lands in the YAML in the same PR. For an issue or research-note
     candidate that is not in the YAML yet, use that source's key (declare it under
     `sources:` if it is new) with `status: reserved`;
   - declare the issue under `sources:` as `issue_<number>` if it is new;
   - if the issue or note already used a different number, add a `renumbering` row
     (`source`, `old`, `new`, `reason`).
   Local numbering in research files uses a prefix (`AR-H1` for assumption-register
   claims, `EQ-Q1` for equilibrium questions) so it is never mistaken for a spec ID;
   declare new ones under `local_namespaces`.
   Never reuse or renumber a registered ID. `make check` rejects an unregistered or
   retitled YAML node, an ID that collides with another definition, an
   issue-numbered ID whose node is not proposed in that issue, and a number
   that is neither below `legacy_ceiling` nor an issue number.
3. In the PR, add the node as proposed: `provenance.author_status: proposed` and
   `proposal: {issue: uncomposed/ai-pacing#N}`, with honest `origin`, `sources` and
   `ai_roles`. The tooling enforces this: `author_status` must be one of the known
   values, and a proposed node must name its issue. Proposed nodes are excluded
   from kernel identity, node-existence and dependency-path acceptance tests, and
   an accepted node may not depend on one. Do not write `accepted*` yourself; the
   editor changes that (and the registry status), and AI-assisted proposals must
   say so in `ai_roles`. See `docs/verification.md` and
   `docs/proposed-extensions.md` for a worked example.
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
- Contributions are accepted under the repository's licenses: code under MIT, text
  and data under CC BY 4.0 (`LICENSING.md`). Do not commit third-party material
  unless its license allows it and its `SOURCES.yaml` entry records that license.
- Keep spec changes and model changes in separate PRs where you can: they rest on
  different evidence.
