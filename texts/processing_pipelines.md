# Processing pipelines

Collection and transformation steps follow the `arboili` CLI and
`config.yml`. Shared Sunday flooring for epidemiological weeks lives in
`src/pipeline/epiweek.py` (`floor_to_sunday`). Walkthrough notebooks under
`notebooks/` unroll each transform on fixtures and document literature
alignment.

## 1. Epidemiological cases (SINAN dengue)

Notifiable dengue records come from Brazil’s Sistema de Informação de Agravos
de Notificação (SINAN), the national registry that receives one record per
notified patient. The Ministry of Health publishes the dengue extract as one
compressed CSV per processing year on a public S3 bucket, and collection
(`arboili sinan`) builds each URL deterministically:

```
https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/DENGBR<YY>.csv.zip
```

`<YY>` is the two-digit processing year, and `config.yml` configures 2010–2026
(`sources.sinan`). Each archive is opened in memory and its CSV written to
`data/epidemiological/SINAN/`; an existing CSV is skipped, and `manifest.csv`
and `failures.csv` record status. The full corpus documented in the pipeline
README comprises 17 files from 2010 to 2026, about 7 GB uncompressed, the
largest (2024) at 1.7 GB and 6.6 million records. The checkout used here holds
13 files, `DENGBR14.csv` through `DENGBR26.csv`, covering 2014–2026 and about
5.9 GB on disk; the 2010–2013 exports were not downloaded.

Two properties of the export shape the transformation. Files are named by
processing year rather than event year, so a notification completed in late
December and keyed in January can fall in either annual file, and a single
epidemiological week can be split across two exports. The schema also changed
twice, and not monotonically. The 2010–2013 exports carry 66 columns and
populate the data-entry date `DT_DIGITA`; the 2014–2019 exports carry 119
columns and omit the field entirely; the 2020 export declares it among 121
columns but leaves every value empty; from 2021 onward it is populated again.
The availability gap is therefore the year set 2014–2020, which no threshold
of the form “available from year N” can express. The pipeline declares that
set in `spec.py`, matching the footnote to Table 1 in Borges et al. (2026),
and an integrity check confirms the resulting nulls fall exactly in those
years.

Five fields are projected at read time and the remaining 61 to 116 columns are
discarded: `DT_DIGITA`, `DT_NOTIFIC` (the date the notification form was
completed), `DT_SIN_PRI` (the date of first symptoms), `SG_UF_NOT` (the
federative unit of notification, as a numeric IBGE code) and `CLASSI_FIN` (the
final case classification). The projection keeps even the largest file small
enough to stream.

Records are retained when the interval between symptom onset and notification
satisfies `-180 < (DT_SIN_PRI − DT_NOTIFIC) < 1` days. Both bounds are strict,
and both are exposed as `dif_lower` and `dif_upper`. The lower bound removes
data-entry errors, the case the article describes as an interval “exceeded 180
days” caused by an incorrect onset date. The upper bound removes records whose
onset is dated after their own notification. That bound appears in the
published R code but not in the article’s prose, which describes only the
180-day rule; the default here applies both, because the objective is to
reproduce the published series. Across the full 17-file corpus the filter
removes 69,476 of 28,638,473 records, or 0.24%.

Each of the three dates is then floored to the Sunday on or before it, the
first day of its Brazilian epidemiological week. Weeks are stored as dates,
such as 2024-01-07, rather than ordinals such as 2024W01, which matches the
published dataset and allows direct joins to sources keyed to the same Sunday,
including the Google Trends weekly extract of section 3. SINAN’s own week
columns, `SEM_NOT` and `SEM_PRI`, are ignored so that all three axes follow
one rule and the year-boundary convention stays explicit rather than
inherited.

Cases are counted by the combination of the three week columns, the final
classification and the federative unit. Because the input is partitioned by
calendar year while the aggregation is by epidemiological week, the week
beginning Sunday 30 December 2012 is emitted by both the 2012 and 2013 files,
splitting its count across two rows with the same key. A second aggregation
over the combined years merges them. On the full corpus, 468 group keys were
affected, all in that single boundary week. Numeric IBGE codes are then
replaced by two-letter abbreviations through
`data/epidemiological/br_federative_units.csv`; codes absent from that table
are dropped rather than kept unlabelled.

Missing values are preserved as nulls and never filled. Where the data-entry
date is unavailable, `ew_recorded` is null rather than a default date, and
about 190,000 rows carry that null across the full corpus. In the checkout,
`ew_recorded` is populated only from 2021 onward and is null on 190,244 rows.
Unclassified cases, whose `final_classification` is null, and discarded cases
(code 5) are both retained so that downstream users can apply their own case
definition. Two data-entry defects survive the filter, which constrains
symptom onset only against the notification date and never inspects the
data-entry date. Five rows in the checkout carry an `ew_recorded` of
1799-12-29; all five are Espírito Santo, all are 2024 notifications, and each
represents one case. A further 53 rows, 57 cases, record a data-entry week
earlier than their symptom-onset week, an ordering that a notification keyed
after the patient fell ill cannot produce.

The series is written as `SINAN_dengue_cases.parquet` and
`SINAN_dengue_cases.csv.gz` under `data/epidemiological/SINAN/`, one row per
unique key with a `case_count`. On the full corpus it holds 1,057,243 rows
representing 28,568,997 cases across 27 federative units, spanning
symptom-onset weeks from August 2009 to July 2026 in 884 consecutive weeks
without a gap. The same transform over the 13 checkout files produces 595,061
rows covering 23,104,205 cases in 27 units, with symptom-onset weeks from
2013-07-28 to 2026-08-30 across 683 distinct weeks.

## 2. Climate (ERA5 Zenodo → ARCO → optional CDS; transform climate)

Climate covariates are built so that every federative unit and epidemiological
week carries the same physical predictors as the dengue case series and the
Google Trends search index. Daily meteorology comes from the ERA5 family. ERA5
is the Copernicus global atmospheric reanalysis documented by Hersbach et al.
(2020; doi:10.1002/qj.3803), and ERA5-Land is the higher-resolution land
product documented by Muñoz-Sabater et al. (2021;
doi:10.5194/essd-13-4349-2021). Each backend draws on one of the two products.

Collection (`arboili era5`, alias `climate`) tries backends in order. The
primary source is municipality-level ERA5-Land parquet files on Zenodo for
1950–2022 (doi:10.5281/zenodo.10036212) and for 2025
(doi:10.5281/zenodo.18257037). Gap years without Zenodo coverage, including
2023–2024, are filled from the Google ARCO-ERA5 public Zarr store, which holds
ERA5 on a 0.25° grid under `gs://gcp-public-data-arco-era5/...` and allows
anonymous access. Copernicus CDS downloads of `reanalysis-era5-land` remain
available when `backends` includes `cds` and require `~/.cdsapirc`, but they
are not part of the default transform. Default backends are Zenodo then ARCO,
and the analysis window defaults to 2014 onward. Collected files land under
`data/climate/era5/{zenodo,arco}/` with a combined `manifest.csv`.

Six dengue-relevant fields are retained: 2 m temperature (daily mean, plus
daily minimum and maximum when the product provides them), 2 m dewpoint
temperature, total precipitation and surface pressure. Wind is omitted to
limit download size on the historical Zenodo set. Temperatures are converted
from kelvin to degrees Celsius, precipitation from metres to millimetres and
pressure from pascals to hectopascals. Relative humidity is derived from air
temperature and dewpoint with the August-Roche-Magnus approximation and
clipped to [0, 100], following the dewpoint-based humidity construction used
for ERA5 dengue covariates by Sebastianelli et al. (2024). Tiny negative
precipitation values introduced by floating-point noise in ARCO extracts are
clipped to zero; true missing values are left null.

Zenodo files already store daily zonal statistics for Brazilian
municipalities, and the area-mean statistic for each variable is kept so that
municipality values stay comparable across polygons of different size.
Municipality days are floored to the Sunday that opens each Brazilian
epidemiological week. Within each municipality-week, temperature, relative
humidity and pressure are averaged, precipitation is summed, and rainy days
are counted as days with precipitation of at least 0.03 mm, the threshold used
in the dengue climate feature sets that guided this pipeline (Sebastianelli et
al., 2024; configurable as `pipeline.climate.rainy_day_mm`). Thermal range is
computed after weekly aggregation as the difference between weekly maximum and
minimum temperature.

Municipality-week series are reduced to federative units by
population-weighted means, not area means, matching the spatial reduction used
for dengue climate covariates at microregion and UF scales (Zhu et al., 2025;
Chen and Moraga, 2025). Weights come from IBGE 2024 municipal population
estimates in `data/climate/br_municipalities.csv`, joined to IBGE municipality
codes and geographic centroids. The file holds 5,571 municipalities with their
population and centroid coordinates.

For ARCO months, each municipality inherits the daily values of the nearest
0.25° cell to its centroid (equirectangular distance; ARCO longitudes in
0–360° are shifted to geographic longitude before matching), after which the
same population weights are applied. The ARCO and CDS extracts are restricted
to the bounding box in `config.yml`, from 5.5° N to 34° S and from 74° W to
34° W. The nearest-cell map substitutes for true polygon-grid intersection
with WorldPop and suits UF-scale surveillance covariates rather than
fine-grained local exposure.

ARCO daily extracts retain only the hour-to-day mean of 2 m temperature, so
`temp_min` and `temp_max`, together with the thermal range derived from them,
are null on ARCO rows; mean temperature, precipitation, relative humidity and
pressure remain populated. Population weighting skips nulls per feature so
that an all-null field does not collapse to zero. Climate lags are not
materialised: lagged predictors belong on the modelling side. The output table
`ERA5_UF_EW` holds one row per epidemiological week, federative unit and
source (`zenodo` or `arco`), with the physical features above.

The transform runs integrity checks over the schema, the unique key, Sunday
anchors, federative-unit membership, the source domain, and the value bounds
enforced on humidity, precipitation and rainy days. Unit tests exercise
humidity derivation, unit conversion, Sunday flooring and population weighting
on committed fixtures.

## 3. Google Trends search index

Weekly search interest for dengue, chikungunya, influenza and COVID-19
symptoms is extracted from Google Trends through pytrends, an unofficial
client for the public Trends site that requires no API key. The collector
`arboili gt-search` is a Python port of the legacy R script
`3_extract_GT_api.R`, and it calls `interest_over_time()` once for each topic
and location pair. Google Trends reports a normalized relative index rather
than a search count, so the collector treats each response as a self-contained
series.

Every request covers the same five-year window, ending at `reference_date:
2024-12-31` in `config.yml`. The end date is fixed rather than set to the run
date so that a repeated extract returns the same weeks; a rolling window would
shift the series every time collection ran, and the shift would be invisible
in the output. Fixing the end date makes the extract reproducible from the
configuration alone, and the returned weeks run from 2020-01-26 to 2024-12-29.

Geography is the 27 federative units plus the national aggregate. The units
are passed as geo codes of the form `BR-XX`, built from the two-letter
abbreviations in `data/epidemiological/br_federative_units.csv`, and the
national row uses the code `BR`. Each location is queried separately, so a
response holds one weekly series instead of a multi-region comparison, and no
ranking across regions enters the extract.

Vocabulary comes from `data/google_trends/popular_terms.csv`, a controlled
list of 117 rows in 26 groups that pairs Portuguese symptom and disease terms
with Google topic identifiers. Query construction prefers a Freebase topic ID
when a row sets `is_code` true, and otherwise the single term flagged
`main=True`. Freebase IDs resolve a polysemous Portuguese string to one
Knowledge Graph entity, which a free-text query cannot. Disease-level
identifiers are hard-coded alongside the table: dengue `/m/09wsg`, chikungunya
`/m/01__7l`, influenza `/m/0cycc` and COVID-19 `/m/01cpyy`. A small set of
redundant smell/taste and eye groups is excluded at extraction, because those
clusters duplicate rows already covered by other groups. The surviving
vocabulary yields 30 topics.

Once a batch completes, the collector fills every missing `(date, location,
topic)` combination among the observed dates, locations and topics with 0
before writing the raw CSV. Google omits a week when it has too little data to
report, so the fill makes the panel rectangular and lets a later join run
without its own gap-filling step. A zero therefore records a week in which
Google reported no search volume for that term and place, and it never stands
in for a request that was not made.

Requests are spaced by a default `sleep` of 2 s, which can be raised if rate
limiting appears. An HTTP 429 response triggers a save and a graceful stop
instead of a crash, and progress is appended to `manifest_search.csv`, so the
collector resumes from the last unfinished pair. The manifest records the geo,
topic, requested window, status and rows fetched for each request. Walking the
cross of 30 topics and 28 locations issues 840 requests, and in this checkout
the manifest holds 840 rows, every one with status `ok`.

The transform `arboili transform gtrends` (alias `gt-search`) is a thin rename
and validate step. It parses `date` as `ew`, renames `location` to
`state_abbrev`, floors each date to the Sunday that opens its Brazilian
epidemiological week, and writes `GoogleTrends_search_EW.parquet` with a
`GoogleTrends_search_EW.csv.gz` companion under `data/google_trends/`.
National `BR` rows are kept by default (`keep_br: true`); passing `--drop-br`
omits them. No rescaling, topic filter or imputation is applied, and nulls
that survive extraction stay null. That stance matters because the zero-fill
already happened upstream: a surviving null marks a value the collector could
not obtain, and replacing it would erase the distinction from a genuine zero.

Integrity checks run through `integrity.run_all` and require that each `(ew,
state_abbrev, topic)` key is unique and that dates fall on Sundays. They also
require the full federative-unit set and values within [0, 100]. The output
grain is one row for each state and topic in a given week. Values are a
relative 0–100 index within each request window, not absolute search volume, a
property that constrains every downstream comparison.

## 4. Google Trends related topics and queries
Related search vocabulary is collected separately from the weekly search
index, by the command `arboili gt-related`, a Python port of the legacy R
script `3_1_extract_related_search_GT_api.R`. The port replaces the private
trends endpoint the R script called with pytrends, the same unofficial client
used for the weekly index, which needs no API key. The collector iterates four
diseases: dengue, chikungunya, influenza (gripe) and COVID-19. It seeds each
with the same hard-coded Freebase topic IDs used by the weekly extractor:
`/m/09wsg`, `/m/01__7l`, `/m/0cycc` and `/m/01cpyy`. Freebase IDs are
preferred over free text because a single Portuguese word can map to more than
one entity, and the ID fixes the query to one topic. Each disease is crossed
with the 27 federative units, addressed through their Google geo codes
`BR-XX`, and with the national code `BR`, and with each calendar month from
`start_month: "2020-01"` to roughly one month before the run date. For every
combination the collector issues two pytrends calls, each covering a single
calendar month with its start and end date set to that month.
`related_topics()` returns knowledge-graph entities, each with a `topic_title`
and a Freebase `topic_id`, and `related_queries()` returns the raw search
strings that Google associates with the seed. That difference is why the topic
extract carries `topic_id` and `key_symptom` while the query extract carries
neither.

The unit of work is the tuple `(geo, topic, month, request_type)`. The request
count follows directly from the loop: four diseases times 28 geographies times
N months times two request types, with N growing by one each month as the
calendar advances. At the time of writing the window runs from 2020-01 to
2026-09, and at 81 months the formula gives 18,144 requests. The collector
logs every answered tuple to `manifest_related.csv`, one row per tuple with
fields `geo`, `topic`, `month`, `request_type`, `status`, `rows_fetched`,
`error` and `timestamp`. In this checkout the manifest holds 1,518 rows, all
with status `ok`, spanning 1,512 distinct tuples; six keys appear twice because
a retried request was appended rather than overwritten. The two request types
have advanced unevenly, with 1,189 `topics` rows against 329 `queries` rows, so
the topics phase has run across all 15 geographies reached while the queries
phase has reached only four of them.

The collector completes dengue across all months and geographies before it
starts chikungunya, so the partial tables in this checkout hold dengue only.
At the default sleep of 5 s between requests, a complete pass takes roughly 25
hours, so the run is built to survive interruption. It appends a manifest line
after each successful request and, on an HTTP 429 response, saves its
accumulated rows and exits cleanly. Other failures are recorded in the
manifest with status `error`, and the run continues. The next invocation reads
the manifest and resumes from the tuples that are not yet marked `ok`. The
wrapper `scripts/resume_gt_related.sh` re-invokes the collector with
exponential backoff until the manifest is complete. Because the manifest is
the only state, an interruption costs at most the request in flight.

Two extraction behaviours shape the raw files. Google reports its lowest
non-zero interest bucket as the string `"<1"`, which the collector coerces to
0.1 so the value column stays numeric and the smallest non-zero bucket sits on
the same axis as the larger values. When Google returns no related terms for a
tuple, the extractor may still write a row with a blank title instead of
discarding the response; the placeholder keeps the request and its emptiness
auditable. Related vocabulary stays at monthly grain on purpose. It describes
co-occurring search vocabulary, an exploratory signal rather than a
surveillance series, and Google exposes related terms by month. Expanding them
to epidemiological weeks would claim a weekly resolution the source does not
provide.

The transform `arboili transform gt-related` reshapes both extracts. It
renames `date` to `month`, `location` to `state_abbrev`, and `topic_title` to
`related_title`. Rows with a blank `related_title` are dropped by default, and
`--keep-empty` (or `drop_empty_related: false`) retains them for audit.
National `BR` rows stay unless `--drop-br` is passed. The transform writes
`GoogleTrends_related_topic_monthly.*` and
`GoogleTrends_related_query_monthly.*` to `data/google_trends/`, as parquet
with a compressed CSV companion, from whatever the manifest has delivered. Its
integrity checks run with `require_complete_ufs=False`, so a partial extract
passes validation while collection is unfinished. The drop is reversible,
since the raw CSV is left untouched. Re-running the collector and then the
transform extends the same two tables in place.

## 5. Health bulletins
Bulletin collection (`arboili bulletins`) crawls the Ministry of Health
epidemiological bulletin listing at
`https://www.gov.br/saude/pt-br/centrais-de-conteudo/publicacoes/boletins/epidemiologicos`.
The run starts at `from_year: 2019`, and `to_year` null resolves to the
current calendar year, so each invocation extends the corpus as new editions
appear. Every year has its own listing under `.../edicoes/<year>`, and the
collector iterates years in order. The listing is public and needs no key or
authentication. The CLI exposes `--output-dir`, `--from-year` and `--to-year`;
the defaults are `data/bulletins` and the configured range. The portal returns
HTTP 403 to clients without a browser-like User-Agent, so the collector sets
an explicit User-Agent header and advertises HTML and PDF content types.
Requests are spaced by a default delay of 1 s, and each GET is retried up to
three times with linear backoff before the entry is recorded as failed.

For each year the scraper walks Plone pagination by incrementing the
`?b_start:int=N` offset. The CMS does not emit a reliable `rel=next` link, so
the crawler cannot follow a declared next-page pointer. It reads the entry
links on the current page and advances the offset by the number of new entries
that page yielded, not by a fixed page size, then stops when a page produces
no new entry URLs. Entry links are normalized to absolute URLs with the query
string and fragment removed, so the pagination parameter never registers as a
new entry, and the year's entries are deduplicated across pages before any
download starts. Listing pages themselves, whose path ends at `edicoes` or
`edicoes/<year>`, are excluded from the entry set.

Each listing entry is resolved to a downloadable PDF through a chain of
redirects and page types. Three shapes appear on gov.br: a direct `.pdf` URL,
returned unchanged; a `.pdf/view` wrapper, whose `/view` suffix is stripped;
and a Plone item that requires scraping the entry page for a download endpoint
(`@@download/file`, `at_download/file`), a direct PDF anchor, an embedded
`embed`, `iframe` or `object` source, or a child item one level deeper. The
resolver follows this chain recursively to a depth of two, so a Document page
whose payload sits under a nested item is still reached. Candidate download
endpoints are probed with a HEAD request that follows redirects and accepted
only when the final response content type is PDF, which rejects an HTML error
page served under a PDF-looking path. An entry that yields no PDF once the
chain is exhausted is recorded as failed with the reason `no PDF link found on
entry page`.

PDFs are stored under `data/bulletins/<year>/` with the original filename
taken from the PDF URL, sanitized to a filesystem-safe form. A file already
present and non-empty is skipped, so a re-run fetches only new editions.
Downloads stream to a temporary `.part` file and are renamed on completion,
which keeps a partial transfer from being mistaken for a finished one. The
status of each entry is `downloaded`, `existing` or `failed`. `manifest.csv`
records one row per discovered entry with the year, entry URL, resolved PDF
URL, filename, status and timestamp; `failures.csv` holds the subset whose
status is failed. Both files are rewritten on every run and reflect the latest
known state. The manifest is the only index the collector writes; there is no
database or per-year manifest. A listing-level crawl failure is captured as a
single failed entry for that year, so it surfaces in `failures.csv` rather
than aborting the run. The process exits with status 1 when any entry failed,
which lets a scheduled run detect an incomplete crawl.

A `--retry-failed` mode re-attempts only the URLs recorded in a previous
`failures.csv` and skips the listing crawl, so recovering failed downloads
does not require re-walking the site. With no path given it reads
`<output-dir>/failures.csv`. Rows whose file now exists on disk are promoted
to `existing` without a network request. The retry reuses the same resolver
and storage rules as a normal run.

No transform stage follows collection. Files remain raw PDFs under
`data/bulletins/`, available for later text extraction or manual review. None
of the Python transforms consumes them, and no text extraction or
natural-language step is applied anywhere in the pipeline. Consumers who need
machine-readable content must build that stage themselves.

## 6. EBC / Agência Brasil news
News collection runs as `arboili ebc`. Each configured query produces one
scrape that writes to its own subdirectory under the output directory, so a
new search term is added by appending an entry to `sources.ebc.queries` in
`config.yml`. The shipped configuration names a single query, `dengue`,
against the Agência Brasil subsite (`site: agenciabrasil`), restricted to the
content types `noticia` and `pagina`, at 100 results per page, a ceiling of
10,000 pages and a one-second delay between requests. The command returns a
combined result across all queries, reporting how many articles were
downloaded, how many were already present and how many failed.

The scraper reads the EBC public search endpoint. `build_search_url` assembles
the query string from the base `https://busca.ebc.com.br/sites/{site}/nodes`,
the fixed parameters `per_page` and `q`, one `types[]` entry per configured
content type, and a `page` parameter that is omitted for the first page:

```
https://busca.ebc.com.br/sites/agenciabrasil/nodes?per_page=100&q=<query>&types[]=noticia&types[]=pagina&page=<N>
```

On a fresh run the scraper fetches page 1 once to read the total result count
and the highest page number. It takes the count from the result counter
element and the page number from the pagination links, falling back to a
single page when results are present but the pagination block is absent, and
stores both values in the state file. Paging then walks from the page after
the last completed one up to the smaller of the discovered page count and
`max_pages`, so the ceiling caps a run even when the search reports more.
Every listing page is saved to `listings/` before it is parsed, which keeps
the search results available for audit even if a later stage changes. Items
are read from the `ul#results` list; for each entry the scraper takes the
headline link with its URL and title, the snippet, the publication string, the
section slug and the thumbnail URL. The section is the first path segment of
the article URL, and the publication string follows the Brazilian `DD/MM/YYYY
às HH:MM` convention, normalized to ISO 8601 when it parses and otherwise kept
as text.

Article pages are fetched one at a time. Each article request is preceded by
the configured delay, and each listing page is followed by the same delay
before the next one is requested, which keeps the crawl within the request
rate EBC is asked to tolerate. A successful fetch writes the response body to
`articles/` and appends one record to `manifest.jsonl`; a request that raises
is recorded with its error message and counted as a failure. Requests share a
session with a fixed user agent and a 60-second timeout. A failed request is
retried up to three times, with waits that double from 2 seconds. The filename
combines the publication date and a slug of the URL tail with a six-character
SHA-1 prefix of the URL, which keeps names stable and sortable.

The manifest is the article index. Each line is one JSON object. It records
the article URL and title, the snippet, the publication time in parsed and
original form, the site label and section slug, the thumbnail URL, the listing
page the article appeared on, and the relative path of the saved HTML. It also
carries the fetch timestamp and the HTTP status, with any error message. Only
successful fetches count as complete. At startup the scraper reads the
manifest back and records every URL whose status is 200, so an interrupted run
skips completed articles and retries the failed ones on the next pass. The
file is append-only, so a record written by an earlier attempt stays in place.

State is what makes the job restartable. `state.json` holds the run parameters
and its progress. It records the query and site, along with the content types
and page size. It also records the discovered totals and the last completed
page, and counters for pages processed and articles fetched or failed. It is
written atomically after every listing page, through a temporary file that is
renamed into position, so a crash mid-write cannot leave a partial cursor. At
startup the scraper compares the saved query and site against the current
command line, along with the content types and page size, and exits with an
error when they disagree, which stops a resumed run from silently mixing two
different corpora. `--restart` clears the state and manifest for a deliberate
fresh start.

HTML is stored raw. There is no transform stage for this source and no text
extraction. Article bodies and listing pages are kept as delivered, and any
parsing, geocoding or language processing is left to downstream work that does
not exist in this release.

## 7. Optional INMET stations

The INMET collector (`arboili inmet`) is an optional path for annual station
archives from the Brazilian national meteorological institute. Each calendar
year is published as one ZIP at
`https://portal.inmet.gov.br/uploads/dadoshistoricos/<year>.zip`, and the
collector downloads it into `data/climate/inmet/`. The default `from_year` is
2000, and `to_year` defaults to the current calendar year, so a bare
invocation requests every year from 2000 to the present. The `sources.inmet`
block in `config.yml` sets `out_dir`, `from_year` and `to_year`, and the CLI
reads those values as defaults. The `--from-year`, `--to-year` and
`--output-dir` flags override the configuration, and the run needs no account
or API key because the portal serves the uploads directly.

Downloads are streamed to a `.part` file and renamed on completion, so an
interrupted run does not leave a truncated ZIP in place. Before writing, the
collector inspects the response `Content-Type` and rejects anything that is
not a ZIP or an octet stream, which stops an HTML error page from being saved
under a `.zip` name. Failed requests are retried three times with a growing
delay, and the collector pauses one second between years. Each ZIP holds the
stations that reported during that calendar year.

A year whose ZIP is already on disk with non-zero size is skipped, which makes
re-running the command safe and cheap. After every run the collector writes
two reports into the output directory. `manifest.csv` records one row per year
attempted with the URL, filename, status (`downloaded`, `existing` or
`failed`), any error text and a UTC timestamp. `failures.csv` holds the failed
subset. The manifest carries one row for every year in the requested range,
including years skipped because the ZIP was already present, so its length
tracks the range rather than the number of downloads. A `--retry-failed` mode
reads `failures.csv` and re-attempts only those years, without re-requesting
the rest.

INMET stays out of the aggregate commands on purpose. `arboili all` runs
SINAN, Google Trends search, ERA5, bulletins and EBC, and INMET is not in that
list. `transform climate` reads only the ERA5 tree and never touches
`data/climate/inmet/`. The station archives are collected on request and left
as raw ZIPs, outside the climate product that the rest of the project joins
against. No transform stage unpacks them, and no table described here derives
from them.

## 8. Legacy R merge path

The Python transforms stop at per-source analysis-ready tables. The
multi-source panel described by Borges et al. (2026) is assembled instead by
legacy R under `r (original)/scripts/`, which the current CLI does not invoke.
Three scripts carry the work and run in numeric order.

`2_transform_sinan_data.R` reads case-level SINAN CSVs and aggregates them to
weekly case counts. It lists its dengue inputs with the glob
`^dengue_\\d{4}\\.csv\\.gz$`, and its chikungunya inputs with
`^chikungunya_\\d{4}\\.csv\\.gz$`. Neither pattern matches the
`DENGBR<YY>.csv` names the Python downloader writes, so on this checkout the
dengue loop finds no files and produces an empty summary. Where inputs do
match, the script floors the recorded, notification and symptom-onset dates to
the week, keeps records whose onset-to-notification difference falls strictly
between -180 and 1 days, and counts cases grouped by week and final
classification within each state. From 2014 onward it also sums fourteen
symptom flags. It writes `SINAN_dengue_cases.csv.gz` and, by the same logic,
`SINAN_chik_cases.csv.gz`.

`2_1_transform_sivep_data.R` handles SIVEP-Gripe. It reads every `INFLUD*`
file under `data/epidemiological/SIVEP/`, selects the year-appropriate column
set, and floors the three dates to the week. The script reconciles
classification before it aggregates: code 3 is folded into 2, code 9 becomes
missing, and the pre-rewrite code is kept in a second column. For 2019, a
positive `POS_PCRFLU` sets the classification to influenza. From 2020 the
script derives COVID and influenza flags from `CLASSI_FIN` together with the
PCR and antigen columns, then rewrites the classification as 5 (COVID only), 1
(influenza only) or 0 (both). It counts cases and symptom flags by week and
classification within each state, maps the IBGE state code to an abbreviation,
and writes `SIVEP_cases.csv.gz`.

`4_prepare_final_disease_table.R` joins the pieces. The dengue and chikungunya
series drop classification 5, are completed over onset week and state, and are
summed. The SARI series splits into four case columns. `sari_cases` holds all
SARI records; `covid_cases` takes classification 5 or 0; `flu_cases` takes 1
or 0; and `other_sari_cases` takes 2 or 4. A fifth column, `na_sari_cases`,
holds records whose classification is missing. The arbovirus and SARI tables
are joined on symptom-onset week and location, a Brazil-wide row is appended
by summing across states, and the result is written to
`data/epidemiological/Arbo_SARI_disease_table.csv`.
