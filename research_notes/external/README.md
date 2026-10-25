# External models

Replications of published models, one folder per model. Each folder has a README (purpose,
status, how to run, discrepancies), `SOURCES.yaml` (every source pinned with license) and
fast tests wired into `make check`. Status always separates source replication, numerical
correctness and empirical validation.

| slug | model | issue | status |
|---|---|---|---|
| [epoch-gate](epoch-gate/) | Epoch AI GATE (arXiv:2503.04941) | #13 | Official compiled solver rerun bit-identical to the playground presets; partial independent equation checks; no empirical validation. |
