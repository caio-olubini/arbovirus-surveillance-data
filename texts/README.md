# Generated manuscript texts

This folder holds English manuscript drafts grounded in the ARBOILI repository:
collection modules under `src/collection/`, transforms under `src/pipeline/`,
`config.yml`, pipeline READMEs, `articles/README.md`, and `AGENTS.md`.

| File | Intended use | Quality bar |
|------|----------------|-------------|
| `dataset_description.md` | Data Records / appendix-style inventory of sources, products, join keys and caveats | Each family gets prose or multi-row detail at the depth of the climate section (provider, DOI/URL, grain, variables, path, gaps) |
| `processing_pipelines.md` | Methods-style description of collection and transform steps by data family | Match climate §2: named sources, units, aggregation rules, literature already in `articles/`, null/fallback behaviour, output grain |

Texts are regenerated from repo documentation and measured checkout presence;
they are not a substitute for reading the pipeline READMEs or running the CLI.
Do not invent coverage years, row counts or DOIs beyond what the repository
(and papers under `articles/`) already records. When a product is absent on
disk, say so and still describe the intended pipeline from `config.yml` and
the relevant README or R script.
