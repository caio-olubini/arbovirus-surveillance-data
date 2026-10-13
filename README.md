# arbovirus-surveillance-data

Reproducible data pipeline (master's dissertation / data paper) for digital
surveillance of arboviruses (dengue, chikungunya) and respiratory syndromes
(SARI/influenza, COVID-19) in Brazil.

For AI coding agents, project context is in [`AGENTS.md`](./AGENTS.md).
It collects and transforms a multi-source dataset linking official
epidemiological case counts (SINAN, SIVEP-Gripe), digital search behaviour
(Google Trends), meteorological reanalysis (ERA5-Land; optional INMET), Ministry of Health bulletins,
and news coverage (Agência Brasil/EBC) — stratified by federative unit (26
states + DF) and aligned temporally for surveillance modelling.

The news source is transformed into **three competing representations** of one
frozen corpus (lexicon+rules, dense embeddings, topic modelling), a comparison
protocol fixed in [`notes/00-protocolo-comparacao.md`](./notes/00-protocolo-comparacao.md).
Research paths live in [`notes/`](./notes/), manuscript drafts in
[`texts/`](./texts/), and the curated climate references in [`articles/`](./articles/).

## Status

**Collection** — every source has a collector, but two are not fully on disk in
this checkout: SIVEP-Gripe is absent (R-only, no Python collector) and the
Google Trends *related* extract is ~7% complete. See
[Concerns per source](#concerns-per-source).

**Transforms** (`uv run arboili transform …`), with the products on disk today:

| Transform | Product | State |
|---|---|---|
| `sinan` | weekly case series — 595,061 rows, 2013-07-28 → 2026-08-30 | ✅ ready |
| `climate` | UF × epi-week features — 18,036 rows, 666 weeks, 27 UFs | ✅ ready |
| `gtrends` | EW-keyed search index — 216,720 rows, 258 weeks | ✅ ready |
| `gt-related` | monthly related topics/queries | 🟡 partial (~7% collected) |
| `news-text` | frozen news corpus — 4,569 articles, 973 weeks | ✅ ready |
| `news-lexicon` | braço 01 features — 5,152 rows, 965 weeks × 28 locations | ✅ ready |
| `news-embeddings` | braço 02 — BERTimbau vectors, per article + pooled — 5,152 rows, 965 weeks × 28 locations | ✅ ready |
| `news-topics` | braço 03 — temporal topics (DMR), 15 topics — 77,280 rows, 965 weeks × 28 locations | ✅ ready |

Braços 02 and 03 need an optional extra each: `uv sync --extra embeddings` for
`torch` + `transformers` (~800 MB), `uv sync --extra topics` for `tomotopy`
(~30 MB). Both stages say so and exit 1 if the extra is missing.

**Not started:**

- [ ] Pipeline — SIVEP-Gripe (SARI): no Python collector, R-only
- [ ] Pipeline — Bulletins: PDF text extraction (204 PDFs stored raw, unparsed)
- [ ] Final merge: join all series into one `Arbo_SARI_disease_table`
- [ ] Protocol-00 comparison: braços 01 / 02 / 03 under one model and one set of metrics

Tests: `uv run pytest` → **266 passed, 4 failed**. The four failures are
pre-existing and confined to `tests/pipeline/sinan/test_integrity.py`: the
on-disk SINAN series covers 2014–2026, while those tests assert ≥15 complete
years from 2010.

## Project structure

```
├── src/
│   ├── collection/       ← extractors: raw data in, nothing transformed
│   │   ├── cli.py        ← `arboili` CLI entry point
│   │   ├── epidemiological/   ← SINAN downloader (MoH S3)
│   │   ├── google_trends/     ← pytrends search + related topics/queries
│   │   ├── climate/           ← ERA5-Land (Zenodo → ARCO → CDS) + optional INMET
│   │   ├── bulletins/         ← MoH bulletin PDF scraper
│   │   └── ebc/               ← Agência Brasil news scraper
│   │
│   ├── pipeline/          ← post-collection transformations
│   │   ├── epiweek.py     ← shared Sunday-anchored epidemiological week
│   │   ├── sinan/         ← case-level CSVs → weekly case series
│   │   ├── climate/       ← ERA5 Zenodo+ARCO → UF × epi-week features
│   │   ├── google_trends/ ← GT search EW + related monthly
│   │   └── news/          ← three competing news representations
│   │       ├── common.py  ← shared extraction + normalization
│   │       ├── text/      ← frozen corpus: HTML → text + Sunday EW
│   │       ├── lexicon/   ← braço 01: PT-BR lexicon + rules → EW × (BR + UF)
│   │       ├── embeddings/← braço 02: BERTimbau → per-article + EW × (BR + UF)
│   │       └── topics/    ← braço 03: tomotopy DMR → EW × (BR + UF) × topic
│   │
│   ├── config.py          ← config.yml loader, shared by collection & pipeline
│   └── common.py          ← shared ExtractResult type
│
├── notebooks/             ← collection orchestration + per-source walkthroughs
│   ├── data_collection.ipynb
│   ├── sinan_pipeline.ipynb
│   ├── climate_pipeline.ipynb
│   ├── gtrends_pipeline.ipynb
│   ├── gtrends_related_pipeline.ipynb
│   ├── news_pipeline.ipynb
│   ├── news_embeddings_pipeline.ipynb
│   └── news_topics_pipeline.ipynb
├── notes/                 ← research-path tracker (00 protocol … 05 forecaster)
├── texts/                 ← generated English manuscript drafts
├── articles/              ← curated climate references (PDFs + references.csv)
├── scripts/               ← one-off helpers (muni reference, GT-related resume wrapper)
├── tests/                 ← unit + integrity tests, run on committed fixtures
├── r (original)/          ← legacy R chain; not required for the Python products
├── config.yml             ← all extraction/transformation settings
└── data/                  ← downloaded & transformed data (mostly git-ignored)
    ├── epidemiological/   ← SINAN CSVs + UF reference
    ├── google_trends/     ← search + related, raw and transformed
    ├── climate/           ← ERA5 raw (zenodo/arco) + UF × EW output
    ├── bulletins/         ← 204 MoH bulletin PDFs (raw)
    ├── news/dengue/       ← 4,569 article HTML + manifest
    └── pipeline/news/     ← frozen corpus + braços 01–03 features
```

## Concerns per source

| Source | Concern |
|---|---|
| SINAN (dengue cases) | S3 availability varies by year; case-level, aggregated to weekly by `pipeline/sinan`. 2010–2013 were not on the mirror at download time |
| SIVEP-Gripe (SARI) | Separate registry, processed independently from SINAN; no Python collector — absent in this checkout |
| Google Trends search | Relative index (0–100), not absolute volume; rate-limited, resumable |
| Google Trends related | ~18k requests, ~25 h resumable run; saves after every request |
| Climate (ERA5) | Zenodo HTTP (fast) → ARCO GCS gaps → optional CDS queue |
| Climate (INMET, optional) | Large ZIPs (50–200 MB each); station-level, not used by `all` |
| Bulletins | Scraper depends on MoH's Plone CMS pagination; PDFs stored raw, unparsed |
| EBC news | Raw HTML only; text extraction is the `news-text` transform. Two template generations (boundary ~2014) — see `src/pipeline/news/README.md` |

## Installation

The project is managed with [uv](https://docs.astral.sh/uv/). Install uv if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then clone the repository and create the environment:

```bash
git clone https://github.com/caio-olubini/arbovirus-surveillance-data
cd arbovirus-surveillance-data
uv sync
```

`uv sync` reads `pyproject.toml` and `uv.lock` and builds a virtual environment in `.venv/` with exactly the pinned dependency versions. Python 3.12 or newer is required; uv will fetch a suitable interpreter automatically if none is present.

No API keys or credentials are needed — every source is a public endpoint.

### Notebook kernel

The walkthrough notebooks in `notebooks/` declare the `arboili` kernel. Register it once after `uv sync`:

```bash
scripts/install_kernel.sh
```

The script writes an `arboili` spec under `~/Library/Jupyter/kernels/` and points both it and the venv's own `python3` spec at `.venv/bin/python` by absolute path. That second part is why the script exists: the `kernel.json` shipped inside the ipykernel wheel hardcodes a bare `python`, which is not a command on a stock macOS setup — the kernel picker lists it, fails to resolve the interpreter, and drops it again. Re-run the script after any `uv sync --reinstall-package ipykernel`, which restores that broken template.

## Usage

All extractors are exposed through the `arboili` command. Run it with `uv run`, which uses the project environment without needing to activate it:

```bash
uv run arboili --list
```

| Command | Description | Approx. runtime |
|---|---|---|
| `uv run arboili --list` | Show configured sources and their settings | instant |
| `uv run arboili sinan` | SINAN dengue yearly case CSVs from the MoH S3 bucket | ~10 min |
| `uv run arboili gt-search` | Google Trends weekly search index, 5-year window | ~5 min |
| `uv run arboili gt-related` | Google Trends monthly related topics & queries | ~25 h |
| `uv run arboili era5` | ERA5: Zenodo bulk + ARCO gap years (+ optional CDS) | tens of min (Zenodo) |
| `uv run arboili inmet` | INMET annual meteorological ZIPs (optional) | ~30 min |
| `uv run arboili bulletins` | Ministry of Health epidemiological bulletin PDFs | ~20 min |
| `uv run arboili ebc` | Agência Brasil news articles | ~1 h per query |
| `uv run arboili all` | Runs sinan, gt-search, era5, bulletins, and ebc in order | long (CDS queue) |
| `uv run arboili transform sinan` | SINAN case-level CSVs → weekly case series | ~11 s |
| `uv run arboili transform climate` | ERA5 Zenodo+ARCO → UF × epi-week climate features | depends on years |
| `uv run arboili transform gtrends` | Google Trends search → EW-keyed parquet/csv.gz | seconds |
| `uv run arboili transform gt-related` | Related topics/queries → monthly tables (partial OK) | seconds |
| `uv run arboili transform news-text` | EBC article HTML → frozen news corpus | ~45 s |
| `uv run arboili transform news-lexicon` | Corpus → braço 01 EW × (BR + UF) features | ~6 s |
| `uv run arboili transform news-embeddings` | Braço 02 — BERTimbau → per-article + pooled tables | ~575 s (CPU) |
| `uv run arboili transform news-topics` | Braço 03 — DMR topics → shares + meta + sweep tables | ~221 s (CPU) |

`all` deliberately excludes `gt-related`, which is an ~25-hour job better started on its own. Within `all`, a source that fails is logged and the run continues to the next one.

Every extractor is idempotent and resumable: already-downloaded files are skipped, progress is tracked in a `manifest.csv` (or `manifest.jsonl`) per source, and interrupting a run is safe — re-running picks up where it left off.

Pass `--verbose` for debug logging, and `--help` on any subcommand for its full flag list.

### Configuration

Defaults for every source live in [`config.yml`](config.yml) — year ranges, output directories, request delays, the Google Trends reference date, and the list of EBC search queries. Command-line flags override the file for one-off runs:

```bash
uv run arboili sinan --to-year 2023          # narrow the year range
uv run arboili gt-related --sleep 10         # back off harder on rate limits
uv run arboili ebc --query chikungunya       # ad-hoc scrape → data/news/chikungunya/
uv run arboili --config other.yml all        # use a different config file
```

Precedence is command-line flag → `config.yml` value → built-in default.

### Tests

```bash
uv run pytest                     # unit + integrity tests, runs on committed fixtures
uv run pytest -m integration      # re-runs the integrity checks on the full series
```

## Data sources

| Source | Origin | Coverage on disk | Granularity |
|---|---|---|---|
| SINAN dengue | MoH open-data S3 bucket | raw 2014–2026 → series 2013-07-28 → 2026-08-30 | case-level → weekly by state |
| SIVEP-Gripe (SARI) | MoH | **absent** | weekly by state |
| Google Trends search | pytrends | 2020-01-26 → 2024-12-29 | weekly, 27 UFs + BR |
| Google Trends related | pytrends | 2020-01 → present (~7% collected) | monthly, 27 UFs + BR |
| Climate | ERA5-Land (Zenodo) + ARCO; optional INMET | 2013-12-29 → 2026-09-27 | daily grid → epi-week × UF |
| Bulletins | gov.br/saude | 2019–2026 (204 PDFs) | weekly (irregular), national |
| News | Agência Brasil (EBC) | 2002-02-17 → 2026-09-13 (4,569 articles) | article-level, national |

Google Trends values are relative indices (0–100, normalised per request window), not absolute search counts. Disease terms are queried through Freebase topic IDs rather than free text — see `data/google_trends/popular_terms.csv`.
