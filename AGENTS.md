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

All analyses are stratified by Brazilian federative unit (27 UFs: 26 states + DF) and aligned temporally for surveillance modeling.

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
│   ├── gtrends_related_pipeline.ipynb    ← step-by-step GT related monthly (partial OK)
│   ├── news_pipeline.ipynb               ← corpus + braço 01 steps + exploratory SINAN read
│   ├── news_embeddings_pipeline.ipynb    ← braço 02: encoder, pooling, braço-01-vs-02 read
│   └── news_topics_pipeline.ipynb        ← braço 03: tokenizer, k sweep, topic→term read
│
├── data/
│   ├── epidemiological/
│   │   ├── SINAN/                        ← DENGBR14–26.csv (2014–2026 present; 2010–2013 absent)
│   │   │   ├── SINAN_dengue_cases.parquet    ← transform sinan (595,061 rows)
│   │   │   └── SINAN_dengue_cases.csv.gz
│   │   ├── SIVEP/                        ← SARI case data (ABSENT; R-only, no Python collector)
│   │   ├── Arbo_SARI_disease_table.csv   ← merged arbovirus + SARI (ABSENT; R merge not run)
│   │   └── br_federative_units.csv       ← 27-row UF reference (CODE, NAME, ABBREVIATION, REGION)
│   │
│   ├── google_trends/
│   │   ├── GoogleTrends_search.csv       ← 5-year weekly search index, 27 UF + BR (~6.4 MB)
│   │   ├── GoogleTrends_search_EW.*      ← transform gtrends output (216,720 rows) ✓ complete
│   │   ├── GoogleTrends_related_topic.csv← monthly related topics 2020+ (PARTIAL)
│   │   ├── GoogleTrends_related_query.csv← monthly related queries 2020+ (PARTIAL)
│   │   ├── GoogleTrends_related_*_monthly.* ← transform gt-related outputs (near-empty while partial)
│   │   ├── popular_terms.csv             ← controlled vocabulary: diseases + symptoms in PT
│   │   ├── manifest_search.csv           ← extraction progress log (840 requests, complete)
│   │   └── manifest_related.csv          ← extraction progress log (resumable, partial)
│   │
│   ├── climate/
│   │   ├── br_municipalities.csv         ← IBGE mun→UF + pop + centroids (committed)
│   │   ├── era5/                         ← Zenodo parquets + ARCO/CDS fallbacks
│   │   │   ├── zenodo/<coverage>/*.parquet
│   │   │   ├── arco/era5_arco_YYYYMM.nc
│   │   │   ├── cds/…                     ← only if backends includes cds
│   │   │   ├── ERA5_UF_EW.parquet        ← transform climate output (18,036 rows) ✓ complete
│   │   │   └── manifest.csv
│   │   └── inmet/                        ← optional INMET annual station ZIPs (ABSENT)
│   │
│   ├── bulletins/
│   │   ├── 2019/ … 2026/                 ← 204 bulletin PDFs (raw; no parser)
│   │   ├── manifest.csv                  ← crawl index
│   │   └── failures.csv
│   │
│   ├── news/
│   │   ├── reference/
│   │   │   └── lexico_dengue.yaml        ← braço 01 lexicon (versioned; editing it invalidates 02/03 comparison)
│   │   └── dengue/
│   │       ├── state.json                ← scraping cursor/metadata
│   │       ├── manifest.jsonl            ← article index (one JSON per line)
│   │       ├── listings/                 ← raw search result HTML
│   │       └── articles/                 ← saved article HTML (4,569 files)
│   │
│   └── pipeline/news/                    ← news transform outputs (all braços)
│       ├── EBC_dengue_text.parquet       ← frozen corpus (transform news-text)
│       └── EBC_dengue_lexicon_EW.parquet ← braço 01 features (transform news-lexicon)
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
│       ├── google_trends/                ← GT search thin rename/validate
│       │   ├── README.md
│       │   └── spec.py / steps.py / transform.py / integrity.py
│       └── news/                         ← news representations (three parallel braços)
│           ├── README.md                 ← methods write-up: corpus, braços 01–03, measured facts
│           ├── common.py                 ← shared extraction + normalization (no HTML re-parsed downstream)
│           ├── corpus.py                 ← shared article-set gates + geo scoping (braços must not import each other)
│           ├── text/                     ← frozen corpus: HTML → text + Sunday EW
│           ├── lexicon/                  ← braço 01: PT-BR lexicon + rules → EW × (BR + UF)
│           ├── embeddings/               ← braço 02: BERTimbau → per-article + pooled EW × (BR + UF)
│           └── topics/                   ← braço 03: tomotopy DMR → EW × (BR + UF) × topic
│
├── notes/                                ← research-path tracker (not paper prose; see notes/README.md)
│   ├── 00-protocolo-comparacao.md        ← the comparison protocol (fixes the common ground)
│   ├── 01-lexico-regras.md … 05-llm-forecaster.md
│   └── ideias-soltas.md
│
├── scripts/
│   ├── build_muni_reference.py         ← regenerates br_municipalities.csv
│   └── resume_gt_related.sh            ← GT-related resume wrapper (backoff + TLS cert)
│
├── tests/
│   ├── fixtures/{sinan,climate,google_trends,news}/
│   └── pipeline/{sinan,climate,google_trends,news}/
│
└── r (original)/                       ← legacy R chain; not required for Python products
    ├── functions/
    │   ├── fun.R
    │   ├── getGraph2.R
    │   ├── getTopQueries2.R
    │   └── getTopTopics2.R
    └── scripts/
        ├── 1_extract_data.R
        ├── 2_transform_sinan_data.R      ← superseded by `transform sinan`
        ├── 2_1_transform_sivep_data.R    ← SIVEP SARI; input data absent here
        ├── 3_extract_GT_api.R            ← original R version of GT search extraction
        ├── 3_1_extract_related_search_GT_api.R
        ├── 4_prepare_final_disease_table.R ← merges all sources into Arbo_SARI_disease_table.csv (not run)
        └── align_gtrends_curve.R         ← temporal alignment of GT curves
```

---

## Checkout State (snapshot: 2026-10-13)

What is actually on disk versus configured. Re-verify before quoting numbers.

| Product | State | Detail |
|---------|-------|--------|
| `SINAN_dengue_cases.parquet` (+ `.csv.gz`) | ✅ **ready** | 595,061 rows, 13 files (2014–2026), weeks 2013-07-28 → 2026-08-30, 17.5 s. 2026 is a partial year. 2010–2013 not downloaded. |
| `ERA5_UF_EW.parquet` (+ `.csv.gz`) | ✅ **ready** | 18,036 rows, 666 epi-weeks (2013-12-29 → 2026-09-27), 27 UFs, `source` ∈ {zenodo, arco}. ~17 GB of raw ERA5 on disk. |
| `GoogleTrends_search_EW.parquet` (+ `.csv.gz`) | ✅ **ready** | 216,720 rows, 258 weeks (2020-01-26 → 2024-12-29), 27 UF + BR. 840/840 requests `ok`. |
| `GoogleTrends_related_*_monthly.*` | ⚠️ **partial** | ~1.2k of ~18.1k requests (≈7%). Only *Dengue* reached; 15 of 28 geos started. Topic titles come back empty, so the topics product is 0 rows until Google returns data. |
| `Arbo_SARI_disease_table.csv` | ❌ **absent** | R merge (`4_prepare_final_disease_table.R`) never run. |
| SIVEP / SARI | ❌ **absent** | No `data/epidemiological/SIVEP/`, no Python collector. R-only (`2_1_transform_sivep_data.R`). |
| Chikungunya | ❌ **absent** | Parameterised in `spec.py`; no `CHIKBR*` files and no collector. |
| INMET station ZIPs | ❌ **absent** | Optional; not an input to `transform climate`. |
| Bulletins | 🟡 raw | 204 PDFs, 2019–2026. No text extraction. |
| EBC news (raw) | 🟡 raw | 4,569 article HTML files for query `dengue`. |
| `EBC_dengue_text.parquet` (+ `.csv.gz`) | ✅ **ready** | 4,569 articles, 973 weeks (2002-02-17 → 2026-09-13), eras b=2,628 / c=1,941, 45 s. 3 pages saved without a body; 171 Spanish. `lang_guess` separates Spanish from not-Spanish only, so the **180 English articles (Agência Brasil's English edition) are labelled `pt`** and pass the language gate — a protocol-00 open item, surfaced by braço 03. |
| `EBC_dengue_lexicon_EW.parquet` (+ `.csv.gz`) | ✅ **ready** | 5,152 rows, 965 weeks × 28 locations, 4,369/4,569 articles, 6 s. Braço 01. |
| `EBC_dengue_embeddings_article.parquet` | ✅ **ready** | 4,369 rows × 7 cols, 12.6 MB. Braço 02, per article, 768-wide L2-normalized. Needs `--extra embeddings` to reproduce; 1,704/4,369 (39.0%) exceed 512 tokens and are truncated. |
| `EBC_dengue_embeddings_EW.parquet` | ✅ **ready** | 5,152 rows, 965 weeks × 28 locations, 8.7 MB, 574.6 s on CPU. Braço 02 pooled. Article set, week range and per-UF counts are identical to braço 01's — the common ground held. `emb_std` is 0 on the 3,079 rows (59.8%) that pool one article. |
| `EBC_dengue_topics_EW.parquet` (+ `.csv.gz`) | ✅ **ready** | 77,280 rows = 5,152 (EW × location) groups × 15 topics, 965 weeks × 28 locations, 221.3 s on CPU. Braço 03, tomotopy DMR. Needs `--extra topics` to reproduce. **k=15 selected by coherence (0.7510)**; the 5,152 groups are identical to braço 02's — the common ground held. |
| `EBC_dengue_topics_meta.parquet` (+ `.csv.gz`) | ✅ **ready** | 225 rows = 15 topics × 15 terms. What each topic *is*; not optional. |
| `EBC_dengue_topics_sweep.parquet` (+ `.csv.gz`) | ✅ **ready** | 5 rows, one per candidate k with its coherence and `ll_per_word`. The evidence for choosing 15. |

Tests: `uv run pytest` → 266 passed, 4 failed, 0 skipped. The 4 failures are all in
`tests/pipeline/sinan/test_integrity.py` and are pre-existing: the on-disk SINAN
series covers 2014–2026, while those tests assert ≥15 complete years from 2010.
They read a generated artefact and no news module is involved — re-run
`arboili transform sinan` against a 2010+ download, or relax the assertion.

### Resuming Google Trends related

The extraction is long (~18k requests, ~25 h at `sleep: 5`) and Google rate-limits
aggressively. It saves after every request and exits cleanly on HTTP 429. Use the
wrapper, which re-invokes it with exponential backoff:

```bash
scripts/resume_gt_related.sh        # run in its own terminal; appends to logs/gt-related.log
```

**TLS caveat (macOS, corporate proxy).** This machine sits behind a
TLS-inspecting proxy, so Python's bundled `certifi` store rejects Google with
`CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain`. The
wrapper exports `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` pointing at
`logs/macos-ca-bundle.pem` (a keychain export; `logs/` is gitignored) and
rebuilds it from the system keychains if missing. Any ad-hoc pytrends run needs
the same two variables, or it will fail the same way.

---

## Data Sources & Their Concerns

### 1. SINAN — Epidemiological Cases
- **Source**: Brazilian Ministry of Health S3 bucket
- **URL pattern**: `https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/DENGBR<YY>.csv.zip`
- **Coverage**: configured 2010–2026; **2014–2026 present on disk** (13 files, `DENGBR14.csv`–`DENGBR26.csv`, ~5.8 GB). 2010–2013 were not on the S3 mirror at download time.
- **Diseases**: Dengue, Chikungunya (separate datasets). Only dengue exists in this checkout.
- **Output**: `data/epidemiological/SINAN/*.csv` → `uv run arboili transform sinan` (Python) or `r (original)/scripts/2_transform_sinan_data.R` (legacy; its input glob does not match the downloaded filenames)
- **Concerns**:
  - S3 availability varies; run the smoke-test cell in `data_collection.ipynb` to probe live years
  - Raw files are case-level (one row per patient); aggregation to weekly/state-level is done by the transform
  - SIVEP data (SARI hospitalizations) is processed separately via `2_1_transform_sivep_data.R`; not collected here

### 2. Google Trends — Search Index
- **Source**: pytrends (unofficial Google Trends API, no key required)
- **Coverage**: 5-year rolling window ending 2024-12-31; weekly granularity
- **Scope**: 27 UFs + national (BR), diseases + symptom terms
- **Terms**: Defined in `data/google_trends/popular_terms.csv` (Portuguese names + Freebase topic IDs)
- **Output**: `data/google_trends/GoogleTrends_search.csv` (~6.4 MB) — **complete** (840/840 requests); transform product `GoogleTrends_search_EW.*` has 216,720 rows over 258 weeks
- **Concerns**:
  - Google Trends values are relative (0–100 scale, normalized per request window)
  - Rate limiting: HTTP 429 is common; extraction sleeps 2s per request (~3–5 min total)
  - Must use Freebase topic IDs (`/m/XXXXX`) for disease terms, not free text — see `popular_terms.csv`
  - Values are filled with 0 for (date, location, topic) combinations with no data
  - Resumable: manifest tracks progress, safe to re-run

### 3. Google Trends — Related Topics & Queries
- **Source**: pytrends `related_topics()` and `related_queries()`
- **Coverage**: Monthly from 2020-01 to present (window grows monthly; 81 months as of 2026-10)
- **Scope**: 27 UFs + BR, diseases (dengue, chikungunya, influenza, COVID-19). Iterated disease-first, so all of Dengue completes before Chikungunya starts.
- **Output**: `GoogleTrends_related_topic.csv` + `GoogleTrends_related_query.csv` — **both tiny/partial in this checkout** (~1.2k of ~18.1k requests, ≈7%; only Dengue, 15 of 28 geos)
- **Concerns**:
  - ~18,100 HTTP requests total (4 diseases × 28 geos × 81 months × 2 types); 5s sleep ≈ **25 h runtime**, and it grows every month
  - Highly resumable — saves after every successful request; safe to interrupt
  - HTTP 429 triggers a full save + graceful exit; restart from where it left off (use `scripts/resume_gt_related.sh`)
  - Related *topics* have returned empty titles for every request so far, so the topics product is 0 rows until Google serves data; *queries* is the useful signal
  - Needs the TLS trust-store workaround (see **Checkout State**) or every request fails with `CERTIFICATE_VERIFY_FAILED`

### 4. Climate — ERA5 family (Zenodo → ARCO → CDS) + INMET (optional)
- **Primary (fastest)**: Zenodo ERA5-Land municipality daily parquets (HTTP, no key)
  - 1950–2022: doi:10.5281/zenodo.10036212
  - 2025: doi:10.5281/zenodo.18257037
- **Fallback**: Google ARCO-ERA5 public Zarr (`gs://gcp-public-data-arco-era5`, anon) for gap years (2023–2024, …) — ERA5 0.25°, not Land
- **Last resort**: Copernicus CDS (`cdsapi`, queued; needs `~/.cdsapirc`) — only if `backends` includes `cds`
- **Output**: `data/climate/era5/{zenodo,arco,cds}/…` + combined `manifest.csv` → `ERA5_UF_EW.*` (**complete**: 18,036 rows, 666 epi-weeks, 27 UFs)
- **CLI**: `uv run arboili era5` (alias `climate`); optional `uv run arboili inmet`
- **Concerns**:
  - Zenodo historical files are ~3 GB each (6 dengue vars ≈ 18 GB) — disk space
  - Zenodo has no 2023–2024; ARCO fills those automatically
  - Aggregation to EW×UF: `uv run arboili transform climate` (pop-weighted; see `src/pipeline/climate/README.md`)

### 5. Health Bulletins — Ministry of Health PDFs
- **Source**: `https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/boletins/epidemiologicos`
- **Coverage**: 2019–2026; **204 PDFs on disk** (upstream count varies with the listing structure, not a fixed weekly cadence)
- **Concerns**:
  - Scraper relies on Plone CMS pagination — can break if MoH restructures the site
  - PDF URLs must be resolved through a chain of redirects (listing → item page → PDF link)
  - Not all entries are dengue-specific; bulletins cover all notifiable diseases
  - Currently not parsed — PDFs are stored raw for future NLP/extraction work

### 6. EBC News Articles — Agência Brasil
- **Source**: EBC search API (`busca.ebc.com.br`)
- **Query**: "dengue" (and optionally other arboviruses)
- **On disk**: 4,569 article HTML files, 46 completed listing pages
- **Concerns**:
  - The scraper saves raw HTML only; text extraction is `arboili transform news-text`
  - Resumable via `state.json` cursor; never re-fetches already-saved articles
  - 1s delay between requests; EBC search results are paginated (100/page)
  - `manifest.jsonl` is append-only — check for duplicates if re-scraping from scratch
  - **Two template generations**, boundary at ~2014 (which coincides with SINAN's
    coverage start). Era B (2002–2014) puts the body in `div.inside` and the *site
    name* in `<h1>`; era C (2014–2026) uses `div.node-conteudo` and the real title
    in `<h1>`. The extractor detects the era per article and records the rule that
    fired. Getting this wrong is silent — see `src/pipeline/news/README.md` §1.
  - Not monolingual: 171 of 4,569 articles (3.7%) are Spanish, concentrated in 2016
    (61, Zika/Olympics) and 2002 (24). The corpus carries a `lang_guess` column.

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

Each transform also has a required walkthrough notebook under `notebooks/` that unrolls the Python steps on fixtures and documents literature alignment: `sinan_pipeline.ipynb`, `climate_pipeline.ipynb`, `gtrends_pipeline.ipynb`, `gtrends_related_pipeline.ipynb`, `news_pipeline.ipynb` (corpus + braço 01), `news_embeddings_pipeline.ipynb` (braço 02), `news_topics_pipeline.ipynb` (braço 03). The three news notebooks are dev artifacts for the comparison — their closing sections are explicitly **not** the protocol-00 result.

All notebooks declare `metadata.kernelspec.name = "arboili"`. Run `scripts/install_kernel.sh` once after `uv sync` to register it — the `kernel.json` that ships inside the ipykernel wheel uses a bare `python` in `argv`, which editors cannot resolve, so the kernel appears in the picker and immediately disappears. Re-run the script after `uv sync --reinstall-package ipykernel`.

1. **Setup** — creates `data/` subdirectories
2. **SINAN** — downloads yearly dengue CSVs
3. **Google Trends search** — ~5 min
4. **Google Trends related** — ~25 hours (resumable, run overnight; prefer `scripts/resume_gt_related.sh`)
5. **ERA5** — Zenodo bulk + ARCO gap months (no CDS key needed)
6. **Bulletins** — scrapes MoH PDFs
7. **EBC news** — scrapes Agência Brasil articles
8. **Validation** — smoke tests + output inventory

Then run the Python transforms (below) to build the analysis-ready tables. The
legacy R chain (`r (original)/scripts/`, `1_` → `2_` → `3_` → `4_`) is **not**
needed for the Python products: `transform sinan` replaces
`2_transform_sinan_data.R`, and `4_prepare_final_disease_table.R` cannot run
until SIVEP data exists.

All extractors are **idempotent** — safe to re-run. Progress is tracked in `manifest.csv` files per source.

### Transformations

```bash
uv run arboili transform sinan           # SINAN case-level CSVs → weekly case series
uv run arboili transform climate         # ERA5 Zenodo+ARCO → UF × epi-week features
uv run arboili transform gtrends         # GT search → EW-keyed table (alias: gt-search)
uv run arboili transform gt-related      # GT related topics/queries → monthly (partial OK)
uv run arboili transform news-text       # EBC article HTML → the frozen news corpus
uv run arboili transform news-lexicon    # braço 01: lexicon + rules → EW × (BR + UF)
uv run arboili transform news-embeddings # braço 02: BERTimbau → per-article + pooled tables
                                         #   needs the optional extra: uv sync --extra embeddings
uv run arboili transform news-topics     # braço 03: DMR topics → EW × (BR + UF) × topic
                                         #   needs the optional extra: uv sync --extra topics
```

Shared calendar helper: `src/pipeline/epiweek.py` (`floor_to_sunday`). SINAN
re-exports it from `src/pipeline/sinan/epiweek.py` so older imports keep working.

#### `transform sinan`

Replaces the SINAN half of `r (original)/scripts/2_transform_sinan_data.R` (whose
input glob, `dengue_YYYY.csv.gz`, does not match the `DENGBR<YY>.csv` files the
downloader actually writes). Case counts only; the symptom columns the R script
carries serve a separate analysis and are not part of this series.

On the documented full 17-file corpus it aggregates ~7 GB into about 1.06M rows
(~11 s, peak RSS ~2.1 GB). **In this checkout** (13 files, 2014–2026, ~5.8 GB) it
produces **595,061 rows in ~17.5 s**, spanning onset weeks 2013-07-28 →
2026-08-30; 2026 is a partial calendar year.

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

#### `transform news-text` and `transform news-lexicon`

The news pipeline is three **competing representations** of one frozen corpus —
not layers. All three read `EBC_dengue_text.parquet`; none re-parses HTML. Methods,
measured corpus facts and declared limitations: `src/pipeline/news/README.md`.

- `news-text` is the only stage that touches HTML. It is deliberately *eager*
  (`build()` returns a `DataFrame`, not a `LazyFrame`): the cost is parsing 4,569
  files in Python, so there is no query plan to optimise. Output: 4,569 articles,
  973 weeks, 45 s. Columns include `era`, `extractor` and `lang_guess` as
  provenance, because a silent extraction regression is this stage's real risk.
- `news-lexicon` is braço 01: PT-BR lexicon + regex rules → 5,152 rows over
  965 weeks × 28 locations (BR + 27 UFs), 6 s. The lexicon is versioned at
  `data/news/reference/lexico_dengue.yaml`; **editing a term or weight invalidates
  the comparison with braços 02 and 03.**
- `news-embeddings` is braço 02: a **frozen** BERTimbau
  (`neuralmind/bert-base-portuguese-cased`, revision pinned to the commit sha
  `94d69c95f98f7d5b2a8700c420230ae10def0baa`) → masked-mean, L2-normalized
  per-article vectors, then mean + dispersion per (EW, location). Writes **two**
  tables, because re-encoding is the whole cost and re-pooling is seconds. It needs
  the optional extra `embeddings` (`torch` + `transformers`, ~800 MB) — without it
  the stage exits 1 telling you to `uv sync --extra embeddings`; the unit tests run
  either way, because the encoder is injectable. The article set is **braço 01's**:
  same language gate, same disease-term gate, same `UfMatcher`.
- `news-topics` (03) fits **tomotopy's DMR** (Mimno & McCallum 2012 — the mechanism
  STM extends) over the frozen corpus with the **period as the document covariate**,
  then publishes the mean topic mixture of each (EW, location). `k` is **selected, not
  configured**: the `k_range` sweep is scored by `c_v` coherence (never perplexity)
  and the whole sweep is written out so the choice is auditable. Writes **three**
  tables — shares, the topic→term meta table that says what a topic *is*, and the
  sweep. It needs the optional extra `topics` (`tomotopy`); without it the stage
  exits 1 telling you to `uv sync --extra topics`, and the unit tests run either way
  because the model is injectable. The article set and geo scoping are **braços
  01/02's**, imported from `news.corpus` — braços must not import each other, so the
  shared gate sits above all three.
- Braços 04/05 (LLM extraction, LLM forecaster) are *corredores por fora*: same
  corpus, different output kind. Notes only, no code. See `notes/04`/`notes/05`.

```bash
uv run pytest                     # unit + integrity tests, runs on committed fixtures
uv run pytest -m integration      # re-runs the integrity checks on the full series
```

---

## Temporal & Geographic Scope

| Source | Configured | On disk / produced | Granularity | Geography |
|--------|-----------|--------------------|-------------|-----------|
| SINAN dengue | 2010–2026 | raw 2014–2026; series 2013-07-28 → 2026-08-30 | yearly files → weekly series (`transform sinan`) | state |
| SIVEP SARI | varies–2024 | **absent** | weekly | state |
| GT search | 2019-12–2024-12 | **complete**: 2020-01-26 → 2024-12-29 | weekly → `transform gtrends` | 27 UF + BR |
| GT related | 2020-01–present | **~7%** (Dengue only) | monthly → `transform gt-related` (partial OK) | 27 UF + BR |
| ERA5 (Zenodo+ARCO) | 2014*–present | **complete**: 2013-12-29 → 2026-09-27 | daily → UF×EW (`transform climate`) | state |
| INMET (optional) | 2000–present | **absent** | daily (station); not in climate transform | station |
| Bulletins | 2019–2026 | 204 PDFs (raw) | weekly (irregular) | national |
| EBC news | varies–present | 4,569 articles (raw) | article-level | national |

\* Climate transform `from_year` defaults to 2014 in `config.yml`; Zenodo bulk files still cover 1950–2022.
