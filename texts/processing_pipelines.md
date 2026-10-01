# Processing pipelines

Collection and transformation steps follow the `arboili` CLI and
`config.yml`. Shared Sunday flooring for epidemiological weeks lives in
`src/pipeline/epiweek.py` (`floor_to_sunday`). Walkthrough notebooks under
`notebooks/` unroll each transform on fixtures and document literature
alignment.

## 1. Epidemiological cases (SINAN dengue)

Notifiable dengue records come from Brazil’s Sistema de Informação de Agravos
de Notificação (SINAN). Collection (`arboili sinan`) builds deterministic
Ministry of Health S3 URLs rather than scraping the JavaScript open-data
portal:

```
https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/DENGBR<YY>.csv.zip
```

where `<YY>` is the two-digit processing year. Default years in `config.yml`
are 2010–2026 (`sources.sinan.from_year` / `to_year`). Each zip is opened in
memory and the CSV extracted into `data/epidemiological/SINAN/`; `keep_zip`
defaults to false. Already-present CSVs are skipped. Progress and failures are
written to `manifest.csv` and `failures.csv` in that directory.

Files are named by processing year, not by event year. A notification filed in
late December and keyed in January can land in either annual export, so a
single epidemiological week can be split across two files. That property is
resolved later in the transform (§4.5 of `src/pipeline/sinan/README.md`).

The export schema changed twice over the covered period, and not
monotonically. The 2010–2013 exports (66 columns) populate `DT_DIGITA`. The
2014–2019 exports (119 columns) omit `DT_DIGITA` entirely. The 2020 export
declares the column among 121 fields but leaves every value empty. From 2021
onward the field is populated again. The data-entry gap is therefore the year
set 2014–2020, matching the ARBOILI data descriptor Table 1 footnote (Borges
et al., 2026; doi:10.1038/s41597-025-06155-6). Availability is declared as
that set in `src/pipeline/sinan/spec.py`; a threshold of the form “available
from year *N*” cannot express the gap.

Five fields are projected at read time; everything else is discarded:

| Field | Meaning |
|---|---|
| `DT_DIGITA` | date the notification was keyed into the system |
| `DT_NOTIFIC` | date the notification form was completed |
| `DT_SIN_PRI` | date of first symptoms |
| `SG_UF_NOT` | federative unit of notification (numeric IBGE code) |
| `CLASSI_FIN` | final case classification |

The transform (`arboili transform sinan`) then applies the steps below.
Defaults reproduce the published R series while extending past the article’s
2024 endpoint when later yearly files are present.

**Consistency filter.** Records are retained when
`-180 < (DT_SIN_PRI − DT_NOTIFIC) < 1` in days. Both bounds are strict and
configurable as `dif_lower` / `dif_upper` in `config.yml`. The lower bound
removes data-entry errors such as a birth date typed into the onset field
(the article’s prose describes the 180-day rule). The upper bound removes
onsets dated after their own notification; that bound is present in the
published R code but not in the article text. Records with a missing onset or
notification date fail the comparison and are excluded. On the full 17-file
corpus documented in the SINAN pipeline README, this filter excludes 69,476 of
28,638,473 records (0.24%).

**Epidemiological weeks.** Each of the three dates is floored to the Sunday on
or before it (`floor_to_sunday`). Weeks are stored as dates (for example
`2024-01-07`), not as `YYYYWW` ordinals, and SINAN’s native week columns
(`SEM_NOT`, `SEM_PRI`) are ignored so all three axes share one rule. Sunday
anchoring matches R’s `floor_date(unit="week")` and aligns with the Google
Trends weekly extract, which is also Sunday-keyed.

**Aggregation.** Cases are counted by
`(ew_recorded, ew_notification, ew_symptom_onset, final_classification,
state_abbrev)`. After all years are combined, a second aggregation merges
group keys that were split across calendar-year files at year boundaries
(documented for the 2012–2013 week spanning New Year). Numeric IBGE UF codes
are then replaced by abbreviations from
`data/epidemiological/br_federative_units.csv`; codes absent from that table
are dropped.

**Null behaviour.** Where `DT_DIGITA` is unavailable (2014–2020),
`ew_recorded` is null, not a fabricated date. Unclassified cases
(`final_classification` null) and discarded cases (code 5) are retained so
downstream users can apply their own case definition; reproducing the
article’s dengue counts requires excluding discarded records. Symptom columns
carried by the legacy R path are deliberately out of scope. Chikungunya is
parameterised in `spec.py` but has no collector or source files yet.

**Outputs.** `SINAN_dengue_cases.parquet` and `.csv.gz` under
`data/epidemiological/SINAN/`. On the documented full corpus the series has
about 1.06 million rows and covers symptom-onset weeks from August 2009
through mid-2026, with 2025 complete and 2026 partial when last measured in
the pipeline README. Integrity checks cover schema, unique keys, Sunday
anchors, UF membership, and the declared `DT_DIGITA` gap years. In the
present checkout, yearly CSVs for 2014–2026 are on disk (~5.8 GB); years
2010–2013 and the transform products were not present at the time of writing.

Known source caveats inherited from Borges et al. (2026) and the pipeline
README: recent weeks are incomplete under reporting delay; Espírito Santo
dengue counts collapse for 2020–2022 after notifications moved to e-SUS VS,
then recover from 2023; no nowcasting adjustment is applied.

## 2. Climate (ERA5 Zenodo → ARCO → optional CDS; transform climate)

Climate covariates are built so that each federative unit and epidemiological
week carries the same physical predictors as the dengue case series and the
Google Trends search index. Daily meteorology comes from the ERA5 family.
ERA5 is the Copernicus global atmospheric reanalysis documented by Hersbach
et al. (2020). ERA5-Land is the higher-resolution land product documented by
Muñoz-Sabater et al. (2021).

Collection (`arboili era5`, alias `climate`) tries backends in order.
The primary product is municipality-level ERA5-Land parquet files on Zenodo
for 1950–2022 (doi:10.5281/zenodo.10036212) and for 2025
(doi:10.5281/zenodo.18257037). Years without Zenodo coverage, including
2023–2024, are filled from the Google ARCO-ERA5 public Zarr store (ERA5 on a
0.25° grid under `gs://gcp-public-data-arco-era5/...`, anonymous access).
Copernicus CDS downloads of `reanalysis-era5-land` remain available when
`backends` includes `cds` but are not part of the default transform. Default
backends are Zenodo then ARCO; the analysis window defaults to 2014 onward
while Zenodo bulk files still ship the longer historical span. Collected
files land under `data/climate/era5/{zenodo,arco}/` with a combined
`manifest.csv`.

Six dengue-relevant fields are retained at collection and transform time: 2 m
temperature (daily mean, and daily minimum and maximum when the product
provides them), 2 m dewpoint temperature, total precipitation and surface
pressure. Wind is omitted to limit download size on the historical Zenodo
set. Temperatures are converted from kelvin to degrees Celsius, precipitation
from metres to millimetres and pressure from pascals to hectopascals.
Relative humidity (%) is derived from air temperature and dewpoint with the
August-Roche-Magnus approximation and clipped to [0, 100], following the
dewpoint-based humidity construction used for ERA5 dengue covariates by
Sebastianelli et al. (2024). Tiny negative precipitation values introduced by
floating-point noise in ARCO extracts are clipped to zero; true missing
values are left null.

Zenodo files already store daily zonal statistics for Brazilian
municipalities. The area-mean statistic for each variable is kept so that
municipality values remain comparable across polygons of different size.
Municipality days are then floored to the Sunday that opens each Brazilian
epidemiological week. Within each municipality-week, temperature, relative
humidity and pressure are averaged, precipitation is summed and rainy days
are counted as days with precipitation of at least 0.03 mm, the threshold
used in the dengue climate feature sets that guided this pipeline
(Sebastianelli et al., 2024; configurable as `pipeline.climate.rainy_day_mm`).
Thermal range is computed after weekly aggregation as the difference between
weekly maximum and minimum temperature.

Municipality-week series are reduced to federative units by
population-weighted means, not area means, matching the spatial reduction
used for dengue climate covariates at microregion and UF scales (Zhu et al.,
2025; Chen and Moraga, 2025). Weights come from IBGE 2024 municipal
population estimates in `data/climate/br_municipalities.csv`, joined to IBGE
municipality codes and geographic centroids. For ARCO months, each
municipality inherits the daily values of the nearest 0.25° cell to its
centroid (equirectangular distance; ARCO longitudes in 0–360° are shifted to
geographic longitude before matching), after which the same population
weights are applied. This nearest-cell map is reproducible without GIS zonal
statistics. It substitutes for true polygon-grid intersection with WorldPop
and is intended for UF-scale surveillance covariates rather than fine-grained
local exposure.

ARCO daily extracts retain only the hour-to-day mean of 2 m temperature, so
`temp_min` and `temp_max` (and thermal range derived from them) are null on
ARCO rows; mean temperature, precipitation, relative humidity and pressure
remain populated. Population weighting skips nulls per feature so that an
all-null field does not collapse to zero. Climate lags are not materialised:
lagged predictors belong on the modelling side. The output table
`ERA5_UF_EW` holds one row per epidemiological week, federative-unit
abbreviation and source (`zenodo` or `arco`), with the physical features
above (CLI: `arboili transform climate`). In this checkout the product has
18,036 rows spanning epidemiological weeks 2013-12-29 to 2026-09-27
(14,121 Zenodo; 3,915 ARCO).

## 3. Google Trends search index

Weekly search interest is extracted with pytrends (`arboili gt-search`), an
unofficial client for the public Google Trends site; no API key is required.
The run is a port of the legacy R script `3_extract_GT_api.R`. For each
`(topic × location)` pair the collector calls `interest_over_time()` over a
five-year window whose end is fixed at `reference_date: 2024-12-31` in
`config.yml` so the extract is reproducible. Geography is the 27 federative
units from `br_federative_units.csv` plus national `BR` (geo codes `BR-XX`
and `BR`). Default sleep between requests is 2 s; HTTP 429 triggers a save
and graceful stop via `manifest_search.csv`, so the run is resumable.

Query construction prefers Freebase topic IDs (`is_code=True` in
`data/google_trends/popular_terms.csv`) when available, otherwise the term
flagged `main=True`. Disease-level Freebase IDs are hard-coded alongside the
vocabulary table: dengue `/m/09wsg`, chikungunya `/m/01__7l`, influenza
`/m/0cycc`, COVID-19 `/m/01cpyy`. A small set of redundant smell/taste and eye
groups is excluded at extraction. Values are a relative 0–100 index within
each request window. After a successful batch, missing
`(date, location, topic)` combinations among the observed dates, locations
and topics are filled with 0 before writing
`data/google_trends/GoogleTrends_search.csv`. In this checkout that file has
216,720 data rows (~6.4 MB) and the observed weekly dates run from
2020-01-26 to 2024-12-29.

The search transform (`arboili transform gtrends`, alias `gt-search`) is a
thin rename and validate step: parse `date` as `ew`, rename `location` to
`state_abbrev`, floor to Sunday, optionally drop `BR` (`keep_br: true` by
default), and write `GoogleTrends_search_EW.parquet` (+ `.csv.gz`). No
rescaling, topic filter or imputation is applied; nulls that survive
extraction stay null. Integrity requires unique `(ew, state_abbrev, topic)`,
Sunday anchors, the full UF set and values in [0, 100]. The EW product in
this checkout has 216,720 rows with the same four columns.

## 4. Google Trends related topics and queries

Related vocabulary is collected separately (`arboili gt-related`) as a port
of `3_1_extract_related_search_GT_api.R`. For each of four diseases (dengue,
chikungunya, influenza/gripe, COVID-19, same Freebase IDs as above), each of
the 27 UFs plus `BR`, and each calendar month from `start_month: "2020-01"`
to roughly one month before the run date, the collector issues two pytrends
calls: `related_topics()` and `related_queries()`. That is on the order of
13,400 HTTP requests. Default sleep is 5 s (~18 h for a full run). Progress
is appended to `manifest_related.csv` after every successful request; HTTP
429 saves and exits so the next run resumes from unfinished
`(geo, topic, month, request_type)` tuples.

Raw outputs are `GoogleTrends_related_topic.csv` and
`GoogleTrends_related_query.csv`. Topic rows carry `topic_title`,
`topic_id`, `date` (YYYY-MM), `location`, `value`, `disease` and
`key_symptom`. Query rows omit `topic_id` / `key_symptom`. Values reported
by Google as `"<1"` are coerced to 0.1 at extraction. When Google returns no
related terms, the extractor may still write a placeholder row with a blank
title.

Grain stays monthly on purpose: related vocabulary is exploratory
co-occurrence, not a weekly surveillance panel. The transform
(`arboili transform gt-related`) reshapes to
`GoogleTrends_related_topic_monthly.*` and
`GoogleTrends_related_query_monthly.*` with columns
`month`, `state_abbrev`, `disease`, `related_title`, `value`, and (topics
only) `topic_id` and `key_symptom`. Blank `related_title` placeholders are
dropped unless `--keep-empty` / `drop_empty_related: false` is set. National
`BR` rows are kept by default. Integrity does not require full 27-UF
coverage while collection is unfinished (`require_complete_ufs=False`).

In this checkout the related extract is partial: the related-topic CSV has a
few hundred rows, the related-query CSV is near-empty, and
`manifest_related.csv` records on the order of 1,200 successful request
tuples. That state is a valid transform input; re-running the collector and
then `transform gt-related` extends the monthly tables.

## 5. Health bulletins

Bulletin collection (`arboili bulletins`) crawls the Ministry of Health
epidemiological bulletin listing from
`https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/boletins/epidemiologicos`
starting at `from_year: 2019` (`to_year` null means the current calendar
year). For each year the scraper walks Plone pagination
(`?b_start:int=N`); the CMS does not emit a reliable `rel=next` link, so
pagination advances until a page yields no new entry URLs. Each listing entry
is then resolved through a chain of redirects and page types (direct PDF,
`/view` wrapper, or Plone Document with an Anexo) to a downloadable PDF URL.

PDFs are stored under `data/bulletins/<year>/` with the original filename.
Already-present files are skipped. `manifest.csv` records year, entry URL,
PDF URL, filename, status and timestamp; `failures.csv` holds failed rows.
A `--retry-failed` mode re-attempts only failure URLs without re-crawling
listings. Default delay between requests is 1 s. The portal can return 403
to bare clients; the collector sends an explicit User-Agent.

There is no transform stage. Files remain raw PDFs for later NLP or manual
use. Not every bulletin is dengue-specific; the listing covers all notifiable
diseases and special editions. In this checkout about 204 PDFs are present
across 2019–2026 (counts per year vary; 2019 and 2026 are sparse relative to
2020–2022). Crawl completeness depends on Plone structure remaining stable.

## 6. EBC / Agência Brasil news

News collection (`arboili ebc`) queries the EBC search API at
`busca.ebc.com.br` for configured terms. Default configuration scrapes
Agência Brasil (`site: agenciabrasil`) for `query: dengue`, content types
`noticia` and `pagina`, 100 results per page, up to 10,000 pages, with a 1 s
delay. Search URL pattern:

```
https://busca.ebc.com.br/sites/agenciabrasil/nodes?per_page=100&q=<query>&types[]=noticia&types[]=pagina&page=<N>
```

Output under `data/news/<query>/` (here `data/news/dengue/`):

| Artefact | Role |
|---|---|
| `state.json` | resume cursor (last completed page, totals, counters) |
| `manifest.jsonl` | one JSON record per article (append-only) |
| `listings/<page>.html` | raw search-result HTML for audit |
| `articles/<file>.html` | saved article HTML |

The scraper refuses to resume if CLI arguments disagree with `state.json`
unless `--restart` is passed. Articles already listed in the manifest are not
re-fetched. There is no transform or text-extraction stage; HTML is stored
raw for later NLP. In this checkout the dengue scrape completed 46 listing
pages with about 4,569 articles fetched (2 failures recorded in state) and
4,571 lines in `manifest.jsonl`.

## 7. Optional INMET stations

Optional station archives can be downloaded with `arboili inmet` from
`https://portal.inmet.gov.br/uploads/dadoshistoricos/<year>.zip` into
`data/climate/inmet/` (`from_year: 2000` by default). ZIPs are skipped when
already present; `manifest.csv` / `failures.csv` mirror the other collectors.
INMET is excluded from `arboili all` and from `transform climate`. Station
series would need a separate path (station → daily summaries → Sunday epi-week
→ UF aggregate) to reach the same grain as ERA5. The dengue climate papers
grounding this project favour ERA5 / ERA5-Land over sparse national station
networks for UF-scale covariates (`articles/README.md`). No INMET files are
present in this checkout.

## 8. Legacy R merge path

Python transforms stop at per-source analysis-ready tables. The multi-source
panel described in the ARBOILI data descriptor is assembled by legacy R under
`r (original)/scripts/`. Script `2_transform_sinan_data.R` aggregates raw
SINAN CSVs (its input glob does not match the `DENGBR<YY>.csv` names the
current downloader writes). Script `2_1_transform_sivep_data.R` processes
SIVEP-Gripe `INFLUD*` files under `data/epidemiological/SIVEP/` into
`SIVEP_cases.csv.gz`. Script `4_prepare_final_disease_table.R` joins dengue
and chikungunya case series (excluding discarded classification 5), SARI
splits (all SARI, COVID, influenza, other), and writes
`Arbo_SARI_disease_table.csv`, keyed on symptom-onset week and location.

No `data/epidemiological/SIVEP/` tree and no `Arbo_SARI_disease_table.csv`
are present in this checkout. Treat the R merge as the documented path to the
published multi-disease table, not as a stage the current Python CLI runs.
