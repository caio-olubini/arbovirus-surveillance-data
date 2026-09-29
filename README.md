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

## Status

- [x] Collection — all six sources (SINAN, SIVEP, Google Trends search + related, climate, bulletins, EBC news)
- [x] Pipeline — SINAN (`arboili transform sinan`): case-level CSVs → weekly case series
- [x] Pipeline — Climate (`arboili transform climate`): Zenodo+ARCO → UF × epi-week features
- [x] Pipeline — Google Trends search (`arboili transform gtrends`): thin EW-keyed table
- [x] Pipeline — Google Trends related (`arboili transform gt-related`): monthly tables (partial OK)
- [ ] Pipeline — SIVEP-Gripe (SARI): case-level → weekly series
- [ ] Pipeline — Google Trends related: monthly topics/queries → analysis table
- [ ] Pipeline — Bulletins: PDF text extraction (currently stored raw, unparsed)
- [ ] Pipeline — EBC news: article text extraction (currently stored raw, unparsed)
- [ ] Final merge: join all series into one `Arbo_SARI_disease_table`

## Project structure

```
├── src/
│   ├── collection/       ← extractors: raw data in, nothing transformed
│   │   ├── cli.py        ← `arboili` CLI entry point
│   │   ├── epidemiological/   ← SINAN downloader (MoH S3)
│   │   ├── google_trends/     ← pytrends search + related topics/queries
│   │   ├── climate/           ← ERA5-Land (CDS) + optional INMET ZIP downloaders
│   │   ├── bulletins/         ← MoH bulletin PDF scraper
│   │   └── ebc/                ← Agência Brasil news scraper
│   │
│   ├── pipeline/          ← post-collection transformations
│   │   ├── epiweek.py     ← shared Sunday-anchored epidemiological week
│   │   ├── sinan/         ← case-level CSVs → weekly case series
│   │   ├── climate/       ← ERA5 Zenodo+ARCO → UF × epi-week features
│   │   └── google_trends/ ← GT search CSV → EW-keyed table
│   │
│   ├── config.py          ← config.yml loader, shared by collection & pipeline
│   └── common.py          ← shared ExtractResult type
│
├── tests/                 ← unit + integrity tests, run on committed fixtures
├── notebooks/             ← collection orchestration + per-source pipeline walkthroughs
│   ├── data_collection.ipynb
│   ├── sinan_pipeline.ipynb
│   ├── climate_pipeline.ipynb
│   ├── gtrends_pipeline.ipynb
│   └── gtrends_related_pipeline.ipynb
├── config.yml             ← all extraction/transformation settings
└── data/                  ← downloaded & transformed data (mostly git-ignored)
```

## Concerns per source

| Source | Concern |
|---|---|
| SINAN (dengue cases) | S3 availability varies by year; case-level, aggregated to weekly by `pipeline/sinan` |
| SIVEP-Gripe (SARI) | Separate registry, processed independently from SINAN |
| Google Trends search | Relative index (0–100), not absolute volume; rate-limited, resumable |
| Google Trends related | ~13k requests, ~18h resumable run; saves after every request |
| Climate (ERA5) | Zenodo HTTP (fast) → ARCO GCS gaps → optional CDS queue |
| Climate (INMET, optional) | Large ZIPs (50–200 MB each); station-level, not used by `all` |
| Bulletins | Scraper depends on MoH's Plone CMS pagination; PDFs stored raw, unparsed |
| EBC news | Raw HTML only, no text-extraction pipeline yet; resumable via cursor |

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
| `uv run arboili gt-related` | Google Trends monthly related topics & queries | ~18 h |
| `uv run arboili era5` | ERA5: Zenodo bulk + ARCO gap years (+ optional CDS) | tens of min (Zenodo) |
| `uv run arboili inmet` | INMET annual meteorological ZIPs (optional) | ~30 min |
| `uv run arboili bulletins` | Ministry of Health epidemiological bulletin PDFs | ~20 min |
| `uv run arboili ebc` | Agência Brasil news articles | ~1 h per query |
| `uv run arboili all` | Runs sinan, gt-search, era5, bulletins, and ebc in order | long (CDS queue) |
| `uv run arboili transform sinan` | SINAN case-level CSVs → weekly case series | ~11 s |
| `uv run arboili transform climate` | ERA5 Zenodo+ARCO → UF × epi-week climate features | depends on years |
| `uv run arboili transform gtrends` | Google Trends search → EW-keyed parquet/csv.gz | seconds |
| `uv run arboili transform gt-related` | Related topics/queries → monthly tables (partial OK) | seconds |

`all` deliberately excludes `gt-related`, which is an ~18-hour job better started on its own. Within `all`, a source that fails is logged and the run continues to the next one.

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

| Source | Origin | Coverage | Granularity |
|---|---|---|---|
| SINAN dengue | MoH open-data S3 bucket | 2010–2024 | case-level → weekly by state |
| SIVEP-Gripe (SARI) | MoH | varies–2024 | weekly by state |
| Google Trends search | pytrends | 2019-12–2024-12 | weekly, 27 UFs + BR |
| Google Trends related | pytrends | 2020-01–present | monthly, 27 UFs + BR |
| Climate | ERA5-Land (CDS); optional INMET | 2000–present | hourly grid → monthly files |
| Bulletins | gov.br/saude | 2019–2026 | weekly, national |
| News | Agência Brasil (EBC) | varies–present | article-level, national |

Google Trends values are relative indices (0–100, normalised per request window), not absolute search counts. Disease terms are queried through Freebase topic IDs rather than free text — see `data/google_trends/popular_terms.csv`.
