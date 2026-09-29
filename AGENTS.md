# ARBOILI / arbovirus-surveillance-data — Agent Context

> Canonical context for AI coding harnesses (Cursor, Claude Code, Copilot, Codex, Aider, etc.).
> Keep this file as the single source of truth; `CLAUDE.md` points here.

## Project Goal

ARBOILI is a **reproducible data paper** (part of a master's dissertation) on digital surveillance of arboviruses (dengue, chikungunya) and respiratory syndromes (SARI/influenza, COVID-19) in Brazil. The primary objective is to collect, transform, and publish a multi-source dataset linking:

- **Epidemiological case counts** (SINAN/SIVEP official notified cases)
- **Digital search behavior** (Google Trends weekly/monthly search interest)
- **Climate data** (ERA5-Land reanalysis via CDS; optional INMET station ZIPs)
- **Health bulletins** (Brazilian Ministry of Health PDFs)
- **News articles** (EBC/Agência Brasil press coverage)

All analyses are stratified by Brazilian federative unit (28 states + DF) and aligned temporally for surveillance modeling.

---

## Directory Tree

```
arbovirus-surveillance-data/
├── AGENTS.md                             ← this file (canonical agent context)
├── CLAUDE.md                             ← pointer → AGENTS.md (Claude Code)
├── README.md                             ← human-facing project description
├── article.pdf                           ← final research article
│
├── notebooks/
│   ├── data_collection.ipynb             ← main orchestration notebook (run this)
│   ├── sinan_pipeline.ipynb              ← step-by-step SINAN transform + lit checks
│   ├── climate_pipeline.ipynb            ← step-by-step climate UF×EW + lit checks
│   ├── gtrends_pipeline.ipynb            ← step-by-step GT search EW keys + lit checks
│   └── gtrends_related_pipeline.ipynb    ← step-by-step GT related monthly (partial OK)
│
├── data/
│   ├── epidemiological/
│   │   ├── SINAN/                        ← yearly dengue case CSVs (2010–2024)
│   │   ├── SIVEP/                        ← SARI case data
│   │   ├── Arbo_SARI_disease_table.csv   ← merged arbovirus + SARI (841 KB, final output)
│   │   └── br_federative_units.csv       ← 28 states reference table (CODE, NAME, ABR, REGION)
│   │
│   ├── google_trends/
│   │   ├── GoogleTrends_search.csv       ← 5-year weekly search index, all states (6.5 MB)
│   │   ├── GoogleTrends_search_EW.*      ← transform gtrends output (parquet + csv.gz)
│   │   ├── GoogleTrends_related_topic.csv← monthly related topics 2020+ (partial OK)
│   │   ├── GoogleTrends_related_query.csv← monthly related queries 2020+ (partial OK)
│   │   ├── GoogleTrends_related_*_monthly.* ← transform gt-related outputs
│   │   ├── popular_terms.csv             ← controlled vocabulary: diseases + symptoms in PT
│   │   ├── manifest_search.csv           ← extraction progress log
│   │   └── manifest_related.csv          ← extraction progress log
│   │
│   ├── climate/
│   │   ├── br_municipalities.csv         ← IBGE mun→UF + pop + centroids (committed)
│   │   ├── era5/                         ← Zenodo parquets + ARCO/CDS fallbacks
│   │   │   ├── zenodo/<coverage>/*.parquet
│   │   │   ├── arco/era5_arco_YYYYMM.nc
│   │   │   ├── cds/…                     ← only if backends includes cds
│   │   │   ├── ERA5_UF_EW.parquet        ← transform climate output
│   │   │   └── manifest.csv
│   │   └── inmet/                        ← optional INMET annual station ZIPs
│   │       ├── <year>.zip
│   │       ├── manifest.csv
│   │       └── failures.csv
│   │
│   ├── bulletins/
│   │   ├── 2019/ … 2026/                 ← ~280 epidemiological bulletin PDFs
│   │   ├── manifest.csv                  ← crawl index (77.9 KB)
│   │   └── failures.csv
│   │
│   └── news/
│       └── dengue/
│           ├── state.json                ← scraping cursor/metadata
│           ├── manifest.jsonl            ← article index (one JSON per line)
│           ├── listings/                 ← raw search result HTML
│           └── articles/                 ← saved article HTML
│
├── src/
│   ├── common.py                         ← ExtractResult dataclass (shared return type)
│   ├── config.py                         ← config.yml loader, shared by collection & pipeline
│   │
│   ├── collection/                       ← extraction modules (raw data in, nothing transformed)
│   │   ├── cli.py                        ← `arboili` CLI entry point, wraps every extractor
│   │   ├── epidemiological/
│   │   │   └── sinan_dengue.py           ← downloads SINAN CSVs from MoH S3
│   │   ├── google_trends/
│   │   │   ├── gtrends_api.py            ← pytrends wrapper + helpers
│   │   │   ├── extract_gt_search.py      ← 5-year weekly search index extractor
│   │   │   └── extract_gt_related.py     ← monthly related topics & queries extractor
│   │   ├── climate/
│   │   │   ├── download_era5_data.py     ← orchestrator Zenodo → ARCO → CDS
│   │   │   ├── era5_zenodo.py / era5_arco.py / era5_cds.py
│   │   │   └── download_inmet_data.py    ← INMET annual ZIP downloader (optional)
│   │   ├── bulletins/
│   │   │   └── download_boletins.py      ← MoH bulletin PDF scraper
│   │   └── ebc/
│   │       ├── scraper.py                ← EBC/Agência Brasil news scraper
│   │       ├── http_client.py            ← HTTP session + retry logic
│   │       ├── models.py                 ← Article, State dataclasses
│   │       ├── parsers.py                ← HTML parsing utilities
│   │       └── storage.py                ← file I/O + manifest management
│   │
│   └── pipeline/                         ← data transformation modules (post-collection)
│       ├── epiweek.py                    ← shared Sunday-anchored epidemiological week
│       ├── sinan/                        ← SINAN case-level CSVs → weekly case series
│       │   ├── README.md                 ← data-flow & methodology write-up (paper material)
│       │   ├── spec.py / steps.py / transform.py / integrity.py
│       │   └── epiweek.py                ← re-exports shared floor_to_sunday
│       ├── climate/                      ← Zenodo+ARCO → UF × epi-week features
│       │   ├── README.md                 ← pop-weights, units, rainy-day threshold
│       │   └── spec.py / steps.py / transform.py / integrity.py
│       └── google_trends/                ← GT search thin rename/validate
│           ├── README.md
│           └── spec.py / steps.py / transform.py / integrity.py
│
├── tests/
│   ├── fixtures/{sinan,climate,google_trends}/
│   └── pipeline/{sinan,climate,google_trends}/
│
└── r/
    ├── functions/
    │   ├── fun.R
    │   ├── getGraph2.R
    │   ├── getTopQueries2.R
    │   └── getTopTopics2.R
    └── scripts/
        ├── 1_extract_data.R
        ├── 2_transform_sinan_data.R      ← aggregates raw SINAN yearly CSVs → final table
        ├── 2_1_transform_sivep_data.R    ← processes SIVEP SARI data
        ├── 3_extract_GT_api.R            ← original R version of GT search extraction
        ├── 3_1_extract_related_search_GT_api.R
        ├── 4_prepare_final_disease_table.R ← merges all sources into Arbo_SARI_disease_table.csv
        └── align_gtrends_curve.R         ← temporal alignment of GT curves
```

---

## Data Sources & Their Concerns

### 1. SINAN — Epidemiological Cases
- **Source**: Brazilian Ministry of Health S3 bucket
- **URL pattern**: `https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/DENGBR<YY>.csv.zip`
- **Coverage**: 2010–2024 yearly case-level CSVs; 2025 not yet published
- **Diseases**: Dengue, Chikungunya (separate datasets)
- **Output**: `data/epidemiological/SINAN/*.csv` → transformed by `r/scripts/2_transform_sinan_data.R`
- **Concerns**:
  - S3 availability varies; run the smoke-test cell in `data_collection.ipynb` to probe live years
  - Raw files are case-level (one row per patient); aggregation to weekly/state-level is done in R
  - SIVEP data (SARI hospitalizations) is processed separately via `2_1_transform_sivep_data.R`

### 2. Google Trends — Search Index
- **Source**: pytrends (unofficial Google Trends API, no key required)
- **Coverage**: 5-year rolling window ending 2024-12-31; weekly granularity
- **Scope**: 28 Brazilian states + national (BR), diseases + symptom terms
- **Terms**: Defined in `data/google_trends/popular_terms.csv` (Portuguese names + Freebase topic IDs)
- **Output**: `data/google_trends/GoogleTrends_search.csv` (6.5 MB)
- **Concerns**:
  - Google Trends values are relative (0–100 scale, normalized per request window)
  - Rate limiting: HTTP 429 is common; extraction sleeps 2s per request (~3–5 min total)
  - Must use Freebase topic IDs (`/m/XXXXX`) for disease terms, not free text — see `popular_terms.csv`
  - Values are filled with 0 for (date, location, topic) combinations with no data
  - Resumable: manifest tracks progress, safe to re-run

### 3. Google Trends — Related Topics & Queries
- **Source**: pytrends `related_topics()` and `related_queries()`
- **Coverage**: Monthly from 2020-01 to present
- **Scope**: 28 states + BR, diseases (dengue, chikungunya, influenza, COVID-19)
- **Output**: `GoogleTrends_related_topic.csv` (6.3 MB) + `GoogleTrends_related_query.csv` (3.3 MB)
- **Concerns**:
  - ~13,400 HTTP requests total; 5s sleep per request ≈ **18 hours runtime**
  - Highly resumable — saves after every successful request; safe to interrupt
  - HTTP 429 triggers a full save + graceful exit; restart from where it left off

### 4. Climate — ERA5 family (Zenodo → ARCO → CDS) + INMET (optional)
- **Primary (fastest)**: Zenodo ERA5-Land municipality daily parquets (HTTP, no key)
  - 1950–2022: doi:10.5281/zenodo.10036212
  - 2025: doi:10.5281/zenodo.18257037
- **Fallback**: Google ARCO-ERA5 public Zarr (`gs://gcp-public-data-arco-era5`, anon) for gap years (2023–2024, …) — ERA5 0.25°, not Land
- **Last resort**: Copernicus CDS (`cdsapi`, queued; needs `~/.cdsapirc`) — only if `backends` includes `cds`
- **Output**: `data/climate/era5/{zenodo,arco,cds}/…` + combined `manifest.csv`
- **CLI**: `uv run arboili era5` (alias `climate`); optional `uv run arboili inmet`
- **Concerns**:
  - Zenodo historical files are ~3 GB each (6 dengue vars ≈ 18 GB) — disk space
  - Zenodo has no 2023–2024; ARCO fills those automatically
  - Aggregation to EW×UF: `uv run arboili transform climate` (pop-weighted; see `src/pipeline/climate/README.md`)

### 5. Health Bulletins — Ministry of Health PDFs
- **Source**: `https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/boletins/epidemiologicos`
- **Coverage**: 2019–2026, ~280 weekly epidemiological bulletins
- **Concerns**:
  - Scraper relies on Plone CMS pagination — can break if MoH restructures the site
  - PDF URLs must be resolved through a chain of redirects (listing → item page → PDF link)
  - Not all entries are dengue-specific; bulletins cover all notifiable diseases
  - Currently not parsed — PDFs are stored raw for future NLP/extraction work

### 6. EBC News Articles — Agência Brasil
- **Source**: EBC search API (`busca.ebc.com.br`)
- **Query**: "dengue" (and optionally other arboviruses)
- **Concerns**:
  - Scraper saves raw HTML; no text extraction pipeline exists yet
  - Resumable via `state.json` cursor; never re-fetches already-saved articles
  - 1s delay between requests; EBC search results are paginated (100/page)
  - `manifest.jsonl` is append-only — check for duplicates if re-scraping from scratch

---

## Key Vocabulary

| Term | Meaning |
|------|---------|
| SINAN | Sistema de Informação de Agravos de Notificação — Brazil's notifiable disease registry |
| SIVEP-Gripe | Sistema de Vigilância Epidemiológica da Gripe — SARI hospitalization registry |
| SARI | Severe Acute Respiratory Infection |
| INMET | Instituto Nacional de Meteorologia — Brazilian weather authority |
| EBC | Empresa Brasil de Comunicação — state news agency (Agência Brasil) |
| Arboviruses | Arthropod-borne viruses: dengue, chikungunya, zika (all in scope) |
| Freebase ID | Google Knowledge Graph topic ID (e.g. `/m/09wsg`) used for unambiguous GT queries |
| GT | Google Trends |
| federative unit | Brazilian state-level administrative unit (26 states + DF = 27 total + BR national) |

---

## Running the Pipeline

The canonical collection entry point is `notebooks/data_collection.ipynb`. Run cells top to bottom:

Each transform also has a required walkthrough notebook under `notebooks/` that unrolls the Python steps on fixtures and documents literature alignment: `sinan_pipeline.ipynb`, `climate_pipeline.ipynb`, `gtrends_pipeline.ipynb`, `gtrends_related_pipeline.ipynb`.

1. **Setup** — creates `data/` subdirectories
2. **SINAN** — downloads yearly dengue CSVs
3. **Google Trends search** — ~5 min
4. **Google Trends related** — ~18 hours (resumable, run overnight)
5. **ERA5** — downloads monthly ERA5-Land NetCDF (CDS)
6. **Bulletins** — scrapes MoH PDFs
7. **EBC news** — scrapes Agência Brasil articles
8. **Validation** — smoke tests + output inventory

After Python extraction, run R scripts in order (`1_` → `2_` → `3_` → `4_`) to produce the final `Arbo_SARI_disease_table.csv`.

All extractors are **idempotent** — safe to re-run. Progress is tracked in `manifest.csv` files per source.

### Transformations

```bash
uv run arboili transform sinan          # SINAN case-level CSVs → weekly case series
uv run arboili transform climate        # ERA5 Zenodo+ARCO → UF × epi-week features
uv run arboili transform gtrends        # GT search → EW-keyed table (alias: gt-search)
uv run arboili transform gt-related     # GT related topics/queries → monthly (partial OK)
```

Shared calendar helper: `src/pipeline/epiweek.py` (`floor_to_sunday`). SINAN
re-exports it from `src/pipeline/sinan/epiweek.py` so older imports keep working.

#### `transform sinan`

Replaces the SINAN half of `r/scripts/2_transform_sinan_data.R` (whose input glob,
`dengue_YYYY.csv.gz`, does not match the `DENGBR<YY>.csv` files the downloader
actually writes). Aggregates ~7 GB across 17 yearly files into
`SINAN_dengue_cases.parquet` + `.csv.gz` — about 1.06M rows, ~11 s, peak RSS
~2.1 GB. Case counts only; the symptom columns the R script carries serve a
separate analysis and are not part of this series.

Output is keyed by (recorded week, notification week, symptom-onset week, final
classification, state). Notes worth knowing:

- **Epi weeks are Sunday-anchored dates**, matching R's `floor_date(unit="week")`
  — not `YYYYWW` numbers, and *not* polars' `dt.truncate("1w")`, which anchors on
  Monday.
- **`ew_recorded` is null for 2014–2020.** The 2014–2019 exports omit `DT_DIGITA`;
  the 2020 export declares it but leaves every value empty. Matches the article's
  Table 1 footnote. The gap is non-monotonic, so it is declared as a year set in
  `spec.py`, never a threshold.
- **`state_abbrev` holds a real abbreviation** (`SP`, `RJ`), unlike the R script,
  which left the numeric IBGE code under that name.
- **Filter defaults reproduce the R behaviour**: kept records satisfy
  `-180 < (onset − notification) < 1` in days. Both bounds are strict and
  configurable; the article's prose describes only the 180-day rule.

#### `transform climate`

Zenodo municipality-daily ERA5-Land + ARCO 0.25° gap months →
`ERA5_UF_EW.parquet` (+ csv.gz). Population-weighted means using
`data/climate/br_municipalities.csv` (IBGE 2024 estimates + centroids). Physical
features only: temp min/mean/max (°C), precip_tot (mm), rel_humid (%), pressure
(hPa), rainy_days (threshold 0.03 mm), thermal_range. Emits `source` =
`zenodo`/`arco`. No lags. ARCO rows leave `temp_min`/`temp_max` null (daily mean
only in the collected NetCDFs). Methods: `src/pipeline/climate/README.md`.

#### `transform gtrends`

Thin rename/validate of `GoogleTrends_search.csv` → `GoogleTrends_search_EW.*`
(`date`→`ew`, `location`→`state_abbrev`, Sunday check). Keeps BR rows by default.
Methods: `src/pipeline/google_trends/README.md`.

#### `transform gt-related`

Thin reshape of monthly related topics/queries →
`GoogleTrends_related_topic_monthly.*` + `GoogleTrends_related_query_monthly.*`
(`date`→`month`, `location`→`state_abbrev`, `topic_title`→`related_title`).
Grain stays **monthly** (not EW). Partial extracts are supported; blank
`related_title` placeholders are dropped by default. Integrity does not require
full 27-UF coverage until the collector finishes. Methods: same README.

```bash
uv run pytest                     # unit + integrity tests, runs on committed fixtures
uv run pytest -m integration      # re-runs the integrity checks on the full series
```

---

## Temporal & Geographic Scope

| Source | Start | End | Granularity | Geography |
|--------|-------|-----|-------------|-----------|
| SINAN dengue | 2010 | 2026 | yearly files → weekly series (`transform sinan`) | state |
| SIVEP SARI | varies | 2024 | weekly | state |
| GT search | 2019-12 | 2024-12 | weekly → `transform gtrends` | state + BR |
| GT related | 2020-01 | present | monthly → `transform gt-related` (partial OK) | state + BR |
| ERA5 (Zenodo+ARCO) | 2014* | present | daily → UF×EW (`transform climate`) | state |
| INMET (optional) | 2000 | present | daily (station); not in climate transform | station |
| Bulletins | 2019 | 2026 | weekly (irregular) | national |
| EBC news | varies | present | article-level | national |

\* Climate transform `from_year` defaults to 2014 in `config.yml`; Zenodo bulk files still cover 1950–2022.
