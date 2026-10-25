# External models and cases

Replications of published models and source-grounded case reconstructions, one folder each. Each
folder has a README (purpose, status split into source replication, numerical correctness and
empirical validation, how to run, discrepancies), a `SOURCES.yaml` (every source pinned, with
license) and fast tests run by `make check`.

| folder | subject | issue | status |
|---|---|---|---|
| [epoch-gate](epoch-gate/) | Epoch AI GATE (arXiv:2503.04941) | #13 | Official compiled solver rerun bit-identical to the playground presets; partial independent equation checks; no empirical validation. |
| [hugging-face-incident](hugging-face-incident/) | July 2026 evaluation-agent intrusion at Hugging Face | #15 | Source-grounded reconstruction (fitted, not predictive); OpenAI's posts unread; no empirical validation. |
| [metr-time-horizons](metr-time-horizons/) | METR task-completion time horizons (TH1.0, TH1.1) and developer-productivity studies | #12 | TH1.1 published horizons reproduced from METR's runs (independent fit within 1.6e-4; doubling times exact); dated table with revisions; retrospective holdout (declared verdict: trend baseline not established); one locked forecast, unresolved; no empirical validation. |
