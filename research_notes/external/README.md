# External models and cases

Replications of published models and source-grounded case reconstructions, one folder each. Each
folder has a README (purpose, status split into source replication, numerical correctness and
empirical validation, how to run, discrepancies), a `SOURCES.yaml` (every source pinned, with
license) and fast tests run by `make check`.

| folder | subject | issue | status |
|---|---|---|---|
| [epoch-gate](epoch-gate/) | Epoch AI GATE (arXiv:2503.04941) | #13 | Official compiled solver rerun bit-identical to the playground presets; partial independent equation checks; no empirical validation. |
| [hugging-face-incident](hugging-face-incident/) | July 2026 evaluation-agent intrusion at Hugging Face | #15 | Source-grounded reconstruction (fitted, not predictive); OpenAI's posts unread; no empirical validation. |
| [units-bridge](units-bridge/) | Units and evidence bridging AI research to industrial growth and chip autonomy; Metzger recheck; coupling toy | #11 | Quantity dictionary and conversions checked by `make units-check`; Metzger Fig. 2 re-digitized; toy reduces to the solver's growth law; no empirical validation. |
| [ai-futures-model](ai-futures-model/) | AI Futures Model (AI Futures Project), commit `1c40ecdb` | #14 | First milestone: default trajectory replicated against upstream goldens (~1e-8); seeded distribution compared with the published 08-16-26 forecast; feedback-off and anchor runs; no empirical validation. |
