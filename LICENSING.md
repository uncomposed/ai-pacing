# Licensing

Status: proposed in issue #100. The canonical editor's starting choice was MIT
for everything; this file proposes MIT for code and CC BY 4.0 for text and data.
It takes effect when the editor merges it.

## What each license covers

| Material | License | Text |
|---|---|---|
| **Code**: source files, scripts, tests, JSON Schemas, the Makefile and CI workflows (`.py`, `.rb`, `.sh`, `.mjs`, `.yml` under `.github/`, `schema/*.json`, `Makefile`), wherever they sit in the tree | MIT | [`LICENSE`](LICENSE) |
| **Text and data the project wrote**: `spec/`, `.idea/`, `docs/`, `reports/`, `research_notes/`, `generated/`, `renderings/`, `evidence/`, `systems/`, `eval/`, `examples/`, the Markdown files at the repository root, figures, result tables and cached numerical results | Creative Commons Attribution 4.0 International (CC BY 4.0) | [`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0) |
| **Third-party material** | The upstream terms. Not licensed by this repository. | see below |

If a file fits both of the first two rows, either license may be used.

## Third-party material

`research_notes/external/` replicates and audits other people's models and
data. Each folder's `SOURCES.yaml` records every source with its license as
found. In particular:

- a few upstream data files are committed verbatim (for example
  `research_notes/external/ai-futures-model/epoch_primary/*.csv`, from Epoch AI
  under CC BY 4.0). They keep their upstream license and attribution;
- some committed tables hold numbers taken or derived from sources that state
  no license or reserve all rights. They are included as cited facts with
  attribution. This repository grants no rights in the underlying sources;
- upstream code and bundles are fetched by script and are not committed.

Short quotations from cited works remain their authors'.

## Attribution

For CC BY 4.0 material, credit "AI Pacing, edited by Cole Miller", link
<https://github.com/uncomposed/ai-pacing>, name the full commit ID or release
tag you used, and say if you changed it. [`CITATION.cff`](CITATION.cff) gives
the same information in machine-readable form.

A rendering, critique or variant should also follow the publication rule in
the README: name the exact Git state it targets, and do not present a changed
proposal as a faithful rendering.

## AI-drafted text

Much of the text was drafted with AI assistance, as each node's provenance and
each note's status line record. The licenses above apply to whatever rights the
author holds in that material. Crediting the project does not mean the editor
wrote or endorses every sentence: before attributing a specific claim to the
editor, check the provenance of the node or note it comes from.

## Contributions

Contributions are accepted under these same terms: code under MIT, text and
data under CC BY 4.0.
