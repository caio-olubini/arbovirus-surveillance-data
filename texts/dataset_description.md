# Dataset description

ARBOILI assembles multi-source surveillance inputs for arboviruses and related
digital and environmental signals in Brazil. Sources are stratified by
federative unit (26 states plus the Federal District) where the grain allows,
with an optional national (`BR`) row for Google Trends. Collection writes under
`data/`; analysis-ready tables are produced by `uv run arboili transform …`
after extraction. Paths below are relative to the project root. Checkout
presence is noted where it differs from the configured or documented full
corpus.

## Overview

| Family | Provider / access | Temporal grain | Spatial grain | Configured coverage | Primary product(s) |
|--------|-------------------|----------------|---------------|---------------------|--------------------|
| SINAN dengue | MoH S3 open dumps | case-level → Sunday epi-week | federative unit | yearly files 2010–2026 (`config.yml`) | `data/epidemiological/SINAN/DENGBR*.csv`; transform → `SINAN_dengue_cases.parquet` (+ `.csv.gz`) |
| SIVEP / SARI | MoH SIVEP-Gripe (legacy R) | case-level → Sunday epi-week | federative unit | `INFLUD*` under `data/epidemiological/SIVEP/` when collected | `SIVEP_cases.csv.gz` via R; absent in this checkout |
| Google Trends search | pytrends (unofficial API) | weekly → Sunday epi-week | 27 UF + `BR` | 5-year window ending 2024-12-31 | `GoogleTrends_search.csv` → `GoogleTrends_search_EW.*` |
| Google Trends related | pytrends related topics/queries | monthly | 27 UF + `BR` | from 2020-01 (partial extracts OK) | `GoogleTrends_related_{topic,query}.csv` → `*_monthly.*` |
| Climate ERA5 family | Zenodo ERA5-Land mun daily; ARCO ERA5 0.25°; optional CDS | daily → Sunday epi-week | municipality then UF | analysis default from 2014; Zenodo bulk 1950–2022 and 2025 | `data/climate/era5/{zenodo,arco}/…` → `ERA5_UF_EW.*` |
| INMET (optional) | INMET annual station ZIPs | daily station | station | from 2000 (`config.yml`); out of climate transform | `data/climate/inmet/` when collected (absent here) |
| Health bulletins | MoH Plone listing | weekly PDFs (irregular) | national | from 2019 | `data/bulletins/<year>/*.pdf` + `manifest.csv` |
| EBC / Agência Brasil | EBC search API | article-level | national | query-driven (default: dengue) | `data/news/dengue/{articles,listings,manifest.jsonl,state.json}` |
| Reference tables | IBGE / project vocabulary | static | UF or municipality | committed with repo | `br_federative_units.csv`, `br_municipalities.csv`, `popular_terms.csv` |
| Legacy merge panel | R scripts under `r (original)/` | weekly (symptom onset) | federative unit | multi-source join when inputs exist | `Arbo_SARI_disease_table.csv` (absent in this checkout) |

Join keys shared by the Python analysis-ready tables are Sunday-anchored
`ew` (or `ew_symptom_onset` on SINAN), `state_abbrev` (two-letter UF code),
and for related Trends `month` (`YYYY-MM`). Climate additionally carries
`source` ∈ {`zenodo`, `arco`}.

## Epidemiological cases (SINAN dengue)

Notifiable dengue records come from Brazil’s Sistema de Informação de Agravos
de Notificação (SINAN), published as yearly case-level CSVs on the Ministry of
Health S3 bucket. URL pattern:

```
https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/DENGBR<YY>.csv.zip
```

Collection (`arboili sinan`) extracts `DENGBR<YY>.csv` into
`data/epidemiological/SINAN/` and logs status in `manifest.csv`. Configured
download years are 2010–2026 (`sources.sinan` in `config.yml`). In this
checkout, years 2014–2026 are present (~5.8 GB of CSVs); 2010–2013 were not
on disk at the time of writing. Each row is one notified patient. Files are
keyed by processing year, so event weeks near New Year can span two exports.

Analytical fields retained by the Python transform are `DT_DIGITA`,
`DT_NOTIFIC`, `DT_SIN_PRI`, `SG_UF_NOT` and `CLASSI_FIN`. After date parsing,
the onset-to-notification filter `-180 < Δdays < 1`, Sunday epi-week flooring
and aggregation, the product is one row per
`(ew_recorded, ew_notification, ew_symptom_onset, final_classification,
state_abbrev)` with `case_count`. Output names:
`SINAN_dengue_cases.parquet` and `.csv.gz` in the SINAN directory (not yet
written in this checkout). On the documented full 17-file corpus the series
has about 1.06 million rows covering symptom-onset weeks from August 2009
through mid-2026 (pipeline README).

| Caveat | Detail |
|---|---|
| `ew_recorded` null 2014–2020 | Column absent 2014–2019; present but empty in 2020 (Borges et al., 2026, Table 1 footnote) |
| Reporting delay | Most recent weeks incomplete; no nowcasting applied |
| Espírito Santo 2020–2022 | Counts collapse after transfer to e-SUS VS; recover from 2023 |
| Symptoms | Fourteen symptom count columns from the R path are out of scope |
| Chikungunya | Parameterised; no `CHIKBR*` files or collector yet |
| Discarded cases | Classification 5 retained; exclude to match article dengue totals |

Primary join axes for surveillance models are `ew_symptom_onset` and
`state_abbrev`, matching climate `ew` × `state_abbrev` and Trends search
`ew` × `state_abbrev`.

## SIVEP / SARI

Severe Acute Respiratory Infection (SARI) hospitalisation data from
SIVEP-Gripe are part of the project’s multi-source goal and of the published
ARBOILI merge. In this repository they are handled only by the legacy R
script `r (original)/scripts/2_1_transform_sivep_data.R`, which expects
`INFLUD*` files under `data/epidemiological/SIVEP/`, applies year-dependent
column sets (symptoms and SARS-CoV-2 / influenza lab flags expand after
2019), floors dates to Sunday epi-weeks, and writes `SIVEP_cases.csv.gz`.
There is no Python collector or `transform` stage for SIVEP. No SIVEP tree
is present in this checkout. Treat SARI as R-side until those paths are
populated. The final merge script splits SARI into all-SARI, COVID
(classifications 5 and 0), influenza (1 and 0) and other (2 and 4) series
before joining to arbovirus counts.

## Google Trends search index

Weekly search interest is extracted with pytrends into
`data/google_trends/GoogleTrends_search.csv`. Access method: unofficial
Google Trends HTML/API client (no key). Configured window:
`reference_date: 2024-12-31` with a five-year lookback
(`sources.gt_search`). Geography: 27 UF abbreviations plus `BR`. Topics:
symptom and disease groups from `popular_terms.csv`, preferring Freebase
IDs (`/m/…`) when `is_code` is true, plus hard-coded disease IDs for dengue,
chikungunya, influenza and COVID-19. Sleep defaults to 2 s; progress in
`manifest_search.csv`. Missing combinations among observed dates, locations
and topics are filled with 0 at save time. Values are a relative 0–100 index
per request window, not absolute search volume.

| Property | Value (this checkout) |
|---|---|
| Raw file | `GoogleTrends_search.csv` (~6.4 MB, 216,720 data rows) |
| Columns | `date`, `location`, `topic`, `value` |
| Observed weeks | 2020-01-26 … 2024-12-29 |
| Transform product | `GoogleTrends_search_EW.parquet` (+ `.csv.gz`), same row count |
| Transform columns | `ew`, `state_abbrev`, `topic`, `value` |

`arboili transform gtrends` renames and Sunday-floors only; it does not
rescale or impute. National rows stay unless `--drop-br`. Join to SINAN /
climate on `(ew, state_abbrev)`; topic remains a third key for panel
reshaping.

## Google Trends related topics and queries

Monthly related topics and queries are written to
`GoogleTrends_related_topic.csv` and `GoogleTrends_related_query.csv` by
`arboili gt-related`. Same geography as search; four disease Freebase queries;
months from `start_month: "2020-01"`. Full run ≈ 13,400 requests at 5 s sleep
(≈ 18 h). Resumable via `manifest_related.csv`; HTTP 429 stops after save.
Partial extracts are first-class inputs.

| Property | Topics | Queries |
|---|---|---|
| Raw columns | `topic_title`, `topic_id`, `date`, `location`, `value`, `disease`, `key_symptom` | `topic_title`, `date`, `location`, `value`, `disease` |
| Transform product | `GoogleTrends_related_topic_monthly.*` | `GoogleTrends_related_query_monthly.*` |
| Transform columns | `month`, `state_abbrev`, `disease`, `related_title`, `topic_id`, `value`, `key_symptom` | `month`, `state_abbrev`, `disease`, `related_title`, `value` |
| Grain | calendar month (`YYYY-MM`), not epi-week | same |
| Empty titles | dropped by default (`drop_empty_related: true`) | same |
| `"<1"` values | coerced to 0.1 | same |

In this checkout both related extracts are incomplete (topic CSV on the order
of hundreds of rows; query CSV nearly empty; ~1,200 `ok` manifest rows).
Integrity does not require all 27 UFs until collection finishes. Join to other
tables is by `state_abbrev` and calendar month, not by `ew`.

## Climate (ERA5 family → UF × epi-week)

Physical covariates come from the ERA5 reanalysis family. ERA5 itself is the
global atmospheric reanalysis described by Hersbach et al. (2020;
doi:10.1002/qj.3803). ERA5-Land is the land-surface product described by
Muñoz-Sabater et al. (2021; doi:10.5194/essd-13-4349-2021). Collection
(`arboili era5`) prefers Zenodo HTTP bulk of municipality-daily ERA5-Land
parquets (doi:10.5281/zenodo.10036212 for 1950–2022;
doi:10.5281/zenodo.18257037 for 2025), then Google ARCO-ERA5 public Zarr
(`gs://gcp-public-data-arco-era5/...`, anonymous) for years Zenodo does not
cover (for example 2023–2024; ERA5 0.25°, not Land). Copernicus CDS
(`reanalysis-era5-land`) is optional when `backends` includes `cds` and
requires `~/.cdsapirc`. Default backends are `[zenodo, arco]`; collection and
transform analysis windows default to `from_year: 2014`.

Variables retained: 2 m temperature (min/mean/max when available), 2 m
dewpoint, total precipitation, surface pressure. After Kelvin→°C, m→mm and
Pa→hPa conversion, relative humidity is derived with the August-Roche-Magnus
formula (Sebastianelli et al., 2024). Municipality days are floored to Sunday
epi-weeks; within-week means for temperature, humidity and pressure, sum for
precipitation, and rainy-day counts at ≥ 0.03 mm. Municipality-week series are
reduced to UF by population-weighted means using IBGE 2024 populations in
`br_municipalities.csv` (Zhu et al., 2025; Chen and Moraga, 2025). ARCO months
use nearest 0.25° cell to each municipality centroid before the same weights.

| Column | Unit | Notes |
|---|---|---|
| `ew` | date (Sunday) | join key with SINAN / GT search |
| `state_abbrev` | text | 27 UF abbreviations |
| `source` | text | `zenodo` or `arco` |
| `temp_min`, `temp_mean`, `temp_max` | °C | min/max null on ARCO rows |
| `precip_tot` | mm | weekly sum |
| `rel_humid` | % | clipped to [0, 100] |
| `pressure` | hPa | |
| `rainy_days` | count 0–7 | precip ≥ 0.03 mm |
| `thermal_range` | °C | `temp_max − temp_min`; null when extremes null |

Product path: `data/climate/era5/ERA5_UF_EW.parquet` (+ `.csv.gz`). In this
checkout: 18,036 rows, weeks 2013-12-29 … 2026-09-27 (14,121 Zenodo; 3,915
ARCO). Climate lags are not materialised. INMET is not an input.

## Optional INMET stations

Annual INMET station ZIPs may be downloaded with `arboili inmet` from
`https://portal.inmet.gov.br/uploads/dadoshistoricos/<year>.zip` into
`data/climate/inmet/` (`from_year: 2000`). They are not inputs to
`transform climate` and are absent from this checkout. Reaching UF × epi-week
grain would require a separate station aggregation path; ERA5 remains the
literature-aligned default for national UF covariates.

## Health bulletins

Weekly epidemiological bulletin PDFs are scraped from the Ministry of Health
central content listing
(`…/publicacoes/boletins/epidemiologicos/edicoes/<year>`) into
`data/bulletins/<year>/`, indexed by `manifest.csv` (and `failures.csv`).
Configured start year is 2019; end year defaults to the current calendar year.
Resolution walks Plone pagination and entry pages to PDF URLs. PDFs are stored
raw; there is no text extraction or transform stage. Bulletins are national in
scope and not restricted to dengue. In this checkout about 204 PDFs are
present across 2019–2026. Completeness tracks upstream listing structure and
crawl success, not a fixed weekly cadence.

## EBC / Agência Brasil news

News HTML for the query `dengue` is scraped via the EBC search API
(`busca.ebc.com.br/sites/agenciabrasil/nodes`) into `data/news/dengue/`, with
`listings/`, `articles/`, append-only `manifest.jsonl`, and resumable
`state.json`. Default delay is 1 s; page size 100. Manifest fields include
URL, title, snippet, publication time, section, local HTML path and HTTP
status. No NLP or article-text pipeline is implemented. In this checkout the
dengue scrape reports 46 completed pages, about 4,569 articles fetched and
4,571 manifest lines. Geography is national (article-level), not UF-keyed.

## Reference tables

### Federative units (`data/epidemiological/br_federative_units.csv`)

Twenty-seven rows (26 states + DF). Columns: `CODE` (IBGE UF code, e.g. 35),
`NAME`, `ABBREVIATION` (e.g. `SP`), `REGION` (N, NE, CO, SE, SU). Used to map
SINAN `SG_UF_NOT` to `state_abbrev`, to build Google Trends geo codes
`BR-<ABBREVIATION>`, and as the UF domain for climate integrity checks.

### Municipalities (`data/climate/br_municipalities.csv`)

5,571 municipalities. Columns: `code_muni` (IBGE 7-digit), `state_code`,
`state_abbrev`, `muni_name`, `population` (IBGE Estimativas da População 2024,
sheet MUNICÍPIOS), `lat`, `lon` (centroids from
[kelvins/Municipios-Brasileiros](https://github.com/kelvins/Municipios-Brasileiros)).
Population weights for climate UF reduction; centroids for ARCO nearest-cell
assignment. Regenerable via `scripts/build_muni_reference.py` when new IBGE
estimates are placed under the documented temp path.

### Popular terms (`data/google_trends/popular_terms.csv`)

Controlled vocabulary for Trends extraction (117 rows, 26 groups in this
checkout). Columns: `group`, `group_pt`, `terms`, `exclude`, `main`,
`is_code`. When `is_code` is true, `terms` holds a Freebase topic ID
(`/m/…`) preferred over free text. Disease Freebase IDs for dengue,
chikungunya, influenza and COVID-19 are also hard-coded in the collectors.

## Legacy multi-source panel

Script `r (original)/scripts/4_prepare_final_disease_table.R` joins dengue and
chikungunya weekly case series (discarding classification 5), SIVEP-derived
SARI splits, and writes `data/epidemiological/Arbo_SARI_disease_table.csv`
keyed on symptom-onset week and location. That merged table is the published
multi-disease panel described by Borges et al. (2026). It is not produced by
the Python CLI and is absent from this checkout. Google Trends and climate
Python products can be joined to SINAN on `(ew, state_abbrev)` without waiting
for the R merge.

## Caveats shared across sources

Google Trends indices are relative within each request window. SINAN recent
weeks are incomplete under reporting delay; Espírito Santo dengue reporting
into SINAN was disrupted in 2020–2022. Climate mixes ERA5-Land (Zenodo) and
ERA5 0.25° (ARCO) with an explicit `source` column; ARCO rows leave
`temp_min` / `temp_max` null. Related Trends, bulletin corpora and news HTML
may be partial or unparsed. Numbers cited for full-corpus SINAN transforms
come from `src/pipeline/sinan/README.md`; verify against local files before
quoting row counts in a manuscript if the checkout is incomplete.
