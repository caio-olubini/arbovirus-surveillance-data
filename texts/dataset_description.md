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
| Health bulletins | MoH Plone listing | periodic PDFs (irregular cadence) | national | from 2019 | `data/bulletins/<year>/*.pdf` + `manifest.csv` |
| EBC / Agência Brasil | EBC search API | article-level | national | query-driven (default: dengue) | `data/news/dengue/{articles,listings,manifest.jsonl,state.json}` |
| Reference tables | IBGE / project vocabulary | static | UF or municipality | committed with repo | `br_federative_units.csv`, `br_municipalities.csv`, `popular_terms.csv` |
| Legacy merge panel | R scripts under `r (original)/` | weekly (symptom onset) | federative unit | multi-source join when inputs exist | `Arbo_SARI_disease_table.csv` (absent in this checkout) |

Join keys shared by the Python analysis-ready tables are Sunday-anchored
`ew` (or `ew_symptom_onset` on SINAN), `state_abbrev` (two-letter UF code),
and for related Trends `month` (`YYYY-MM`). Climate additionally carries
`source` ∈ {`zenodo`, `arco`}.

## Epidemiological cases (SINAN dengue)

The epidemiological case series is a weekly count of notified dengue cases in
Brazil, derived from SINAN, the Ministry of Health’s national registry of
notifiable diseases. Each source row is one notified patient, and the
transform reduces that record to counts by epidemiological week and federative
unit, discarding individual-level detail. Records are published as one
compressed CSV per processing year on the Ministry of Health S3 bucket at
`https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SINAN/Dengue/csv/DENGBR<YY>.csv.zip`
and collected with `arboili sinan` into `data/epidemiological/SINAN/`.
Download years are configured from 2010 to 2026 in `config.yml`. The
transformation follows the ARBOILI data descriptor (Borges et al., 2026).

The distinction between the documented corpus and this checkout matters for
every count quoted below. The full corpus described in
`src/pipeline/sinan/README.md` comprises 17 files spanning 2010–2026, about 7
GB uncompressed. This checkout holds 13 files, `DENGBR14.csv` through
`DENGBR26.csv` (2014–2026), about 5.9 GB on disk; the 2010–2013 exports were
not downloaded. Row and case totals from the two differ, and a checkout figure
should not be read as a full-corpus measurement.

The transform (`arboili transform sinan`) projects five source fields:
`DT_DIGITA` (the date the notification was keyed into the system),
`DT_NOTIFIC` (the date the notification form was completed), `DT_SIN_PRI` (the
date of first symptoms), `SG_UF_NOT` (the federative unit of notification, as
a numeric IBGE code) and `CLASSI_FIN` (the final case classification). It
keeps records whose symptom-onset-to-notification interval is more than −180
and less than 1 day, floors each of the three dates to the Sunday on or before
it, aggregates the records by the three week columns together with the
classification and the unit, and replaces the numeric IBGE code with the
two-letter abbreviation from `br_federative_units.csv`. The data-entry field
`DT_DIGITA` is unavailable for the year set 2014–2020: absent from the
2014–2019 exports and declared but empty in the 2020 export.

The output is one row per unique combination of `ew_recorded`,
`ew_notification`, `ew_symptom_onset`, `final_classification` and
`state_abbrev`, with `case_count` giving the number of notifications in that
combination.

| Column | Type | Description |
|---|---|---|
| `ew_recorded` | date | first day of the epidemiological week of data entry; null for 2014–2020 |
| `ew_notification` | date | first day of the epidemiological week of notification |
| `ew_symptom_onset` | date | first day of the epidemiological week of symptom onset; the primary time axis |
| `final_classification` | integer | SINAN final case classification; null where a case is not yet adjudicated |
| `state_abbrev` | text | two-letter federative unit of notification |
| `case_count` | integer | notifications in this combination |

Three kinds of absence are preserved rather than filled: `ew_recorded` is null
where the source field is unavailable, `final_classification` is null where a
case is not yet adjudicated, and, in the wider dataset, a period outside a
source’s coverage is left empty. Nulls are never replaced by zeros or
placeholder dates. Discarded cases (`final_classification = 5`) and
unclassified cases are retained, so the series supports more than one case
definition; reproducing the article’s dengue totals requires excluding the
discarded records.

Two artefacts are written to `data/epidemiological/SINAN/`:
`SINAN_dengue_cases.parquet`, the primary columnar file, and
`SINAN_dengue_cases.csv.gz`, for compatibility with the existing R scripts.
Rows are sorted by federative unit, then by the three week columns, then by
classification, with nulls last, so the output is deterministic and a re-run
overwrites it with identical content.

The full corpus yields 1,057,243 rows representing 28,568,997 cases across 27
federative units, with symptom-onset weeks from August 2009 to July 2026 and
884 consecutive weeks without a gap. This checkout yields 595,061 rows
covering 23,104,205 cases in 27 units, with symptom-onset weeks from
2013-07-28 to 2026-08-30 across 683 distinct weeks; 2026 is a partial year.
The two sets of totals are not directly comparable, since the checkout omits
the 2010–2013 files.

| Caveat | Detail |
|---|---|
| Reporting delay | The most recent weeks are incomplete; the article recommends nowcasting, and no adjustment is applied here |
| Espírito Santo, 2020–2022 | All-classification counts collapse after transfer to e-SUS VS (11,159 cases in 2022 against 80,668 in 2019) and recover from 2023 (138,361) |
| Discarded cases | `final_classification = 5` retained; exclude these to reproduce the article’s dengue totals |
| Chikungunya | Parameterised in the transform but not implemented; no source files and no collector |
| Symptom columns | The fourteen symptom count columns carried by the R path are out of scope |

Primary join axes for surveillance models are `ew_symptom_onset` and
`state_abbrev`, which align with the `ew` × `state_abbrev` grain of the
climate and Google Trends search products.

## SIVEP / SARI

Severe Acute Respiratory Infection (SARI) hospitalization records come from
SIVEP-Gripe, Brazil's national registry of severe respiratory illness. They
enter ARBOILI as a respiratory comparator beside the arbovirus counts, and
they are part of the multi-source panel published with the project (Borges et
al., 2026).

SARI is handled only by the legacy R script `r
(original)/scripts/2_1_transform_sivep_data.R`. There is no Python collector
and no `transform` stage for it. The script reads every file matching
`INFLUD*` under `data/epidemiological/SIVEP/` and takes the processing year
from the file name, because the column set changes with the year. Files before
2019 carry eleven columns: three dates, the notification state, the final
classification, and six symptom fields. The 2019 export adds vomiting and the
influenza PCR flag. Exports from 2020 onward add loss of smell, loss of taste,
abdominal pain, fatigue, the SARS-CoV-2 antigen and PCR flags, and the
influenza antigen flag.

The transformation then floors dates and reduces the records to counts. Each
of `DT_DIGITA`, `DT_NOTIFIC` and `DT_SIN_PRI` is parsed from `%d/%m/%Y` and
floored to the Sunday that opens its epidemiological week. A symptom field is
kept only where its value is 1, and the kept values are summed within each
group, so the output holds counts rather than case-level flags. The final
classification is recoded before summarizing: class 3 folds into 2, class 9
becomes missing, and from 2020 a combined COVID/influenza label is assigned
from the classification together with the laboratory flags. State codes are
mapped to two-letter abbreviations through `br_federative_units.csv`. Both the
original and the recoded classification are retained as separate columns. The
result is written to `data/epidemiological/SIVEP/SIVEP_cases.csv.gz`, with one
row per recorded, notification and symptom-onset week, per classification and
per state.

The final merge script `r (original)/scripts/4_prepare_final_disease_table.R`
reads that file and splits SARI into four series before joining them to the
arbovirus counts: all-SARI, COVID (classifications 5 and 0), influenza (1 and
0) and other (2 and 4). Rows with a missing classification are carried as a
separate series rather than folded into these four. The join keys are
symptom-onset week and state, and the script adds a Brazil-wide aggregate row
before writing `data/epidemiological/Arbo_SARI_disease_table.csv`.

No `data/epidemiological/SIVEP/` tree exists in this checkout. SARI is
therefore a documented path rather than a produced product here, and the
merged panel that depends on it is absent as well.

## Google Trends search index

The Google Trends search index is a weekly, state-level measure of relative
search interest for the disease and symptom vocabulary used in ARBOILI. Terms
cover the four target diseases and their associated symptoms, from fever and
joint pain to loss of smell. The raw artefact is
`data/google_trends/GoogleTrends_search.csv`, extracted with pytrends; the
analysis-ready product is `GoogleTrends_search_EW.parquet`, with a
`GoogleTrends_search_EW.csv.gz` companion for the R scripts.

Both files carry one row for each state and topic in a given epidemiological
week. The raw file names its columns `date`, `location`, `topic` and `value`;
the transform renames the first two to `ew` and `state_abbrev` and leaves the
others unchanged.

| Column | Type | Description |
|---|---|---|
| `ew` | date | first day (Sunday) of the epidemiological week |
| `state_abbrev` | text | two-letter federative unit, or `BR` for the national row |
| `topic` | text | search term or Freebase topic title |
| `value` | integer | relative search interest on the 0–100 index |

The table is a complete rectangular grid. Every combination of the 258
observed weeks, 28 locations and 30 topics is present, so the product holds
216,720 rows (258 × 28 × 30). The raw CSV holds the same 216,720 rows, since
the transform changes column names and date anchoring but not the row count.
The weeks run from 2020-01-26 to 2024-12-29, the locations are the 27
federative units plus national `BR`, and values span the full 0 to 100 range
with no nulls. The extraction manifest `manifest_search.csv` records 840
requests, all with status `ok`, and the raw CSV occupies about 6.4 MB.

Topics are the labels produced by the vocabulary in
`data/google_trends/popular_terms.csv`. The table holds 117 rows across 26
groups; each row names a Portuguese term or a Freebase identifier, and the
`is_code` flag marks which of the two applies. Disease queries use hard-coded
Freebase identifiers, dengue `/m/09wsg`, chikungunya `/m/01__7l`, influenza
`/m/0cycc` and COVID-19 `/m/01cpyy`, so that a term resolves to one Knowledge
Graph entity rather than to a string match. Symptom groups fall back to the
Portuguese term flagged `main=True` when no identifier exists, and redundant
smell/taste and eye groups are excluded before extraction. The surviving
vocabulary yields 30 topics in this checkout, spanning the four diseases and
their symptoms.

Integrity checks confirm that each `(ew, state_abbrev, topic)` key is unique
and that weeks fall on Sundays. They also confirm the full federative-unit set
and values inside [0, 100].

The transform `arboili transform gtrends` renames the two key columns and
floors dates to Sunday, then runs a schema check. It keeps the national `BR`
rows by default and drops them only under `--drop-br`. It applies no
rescaling, topic filter or imputation, so the product inherits both the
zero-fill and any nulls present in the raw extract; the field dictionary above
lists no derived columns.

| Artefact | Role |
|---|---|
| `GoogleTrends_search.csv` | raw extract, one row per `(date, location, topic)` |
| `manifest_search.csv` | request log, 840 rows, all with status `ok` |
| `GoogleTrends_search_EW.parquet` | primary analysis-ready table |
| `GoogleTrends_search_EW.csv.gz` | same rows, for the R scripts |

Join the product to the SINAN dengue series and to `ERA5_UF_EW` on `(ew,
state_abbrev)`, a key all three tables share. Both columns are stored as plain
date and text fields, so the join needs no lookup table at analysis time.
`topic` is a third key for reshaping the long table into a wide panel with one
column per term; a model that needs a single symptom series filters on `topic`
first, and one that needs the national series filters on `state_abbrev =
'BR'`. The related-trends product described in the next section keeps a
monthly grain and joins on `month`, not `ew`, so it cannot enter the weekly
panel without an explicit mapping.

The most important caveat for reusers is that the values are a relative index
within each request window, not absolute search volume. Each series is scaled
to the peak of its own window, so 100 marks the week of highest relative
interest for that topic and location, and every other week is read against
that peak. Two locations can be compared within the same window, but the index
carries no information about how many searches produced it, and a term with a
low base rate can reach 100 on very few queries. Zero entries record weeks in
which Google reported no volume, while nulls mark values that extraction could
not obtain; the two are not interchangeable. Because the scale is set per
window, values from this product should not be compared with Google Trends
figures quoted from other extractions or with counts from other sources. The
product ends at 2024-12-31 and does not extend to later weeks, so a reuser who
needs a longer panel must re-run the collector with a new `reference_date`.

## Google Trends related topics and queries
Monthly related vocabulary is written to `data/google_trends/` as two raw CSVs
by the `arboili gt-related` collector, and reshaped into two analysis-ready
products by `arboili transform gt-related`. The topic extract,
`GoogleTrends_related_topic.csv`, carries the columns `topic_title`,
`topic_id`, `date`, `location`, `value`, `disease` and `key_symptom`. The
query extract, `GoogleTrends_related_query.csv`, carries `topic_title`,
`date`, `location`, `value` and `disease`; it has no `topic_id` or
`key_symptom` because a query is a raw search string rather than a
knowledge-graph entity. Both files are keyed by calendar month (`date`,
`YYYY-MM`), federative unit (`location`, a two-letter abbreviation or the
national `BR`) and seed disease, which in this checkout is `Dengue` on every
row. Requests that fail without a 429 are written to `query_error_topic.csv`
or `query_error_query.csv` alongside the extracts. The collector merges each
run into the existing CSV and keeps the latest row per key, so a resumed run
extends the file rather than replacing it.

The transform products inherit those keys under new names.
`GoogleTrends_related_topic_monthly.parquet`, with a matching `.csv.gz`, has
columns `month`, `state_abbrev`, `disease`, `related_title`, `topic_id`,
`value` and `key_symptom`. `GoogleTrends_related_query_monthly.parquet` has
`month`, `state_abbrev`, `disease`, `related_title` and `value`. Grain is the
calendar month, not the epidemiological week, so these tables join to SINAN,
climate and the weekly search index on `state_abbrev` and a calendar month,
never on `ew`. Values are on Google's relative interest scale, the same scale
as the weekly index, with the smallest reported bucket written as 0.1. The
`key_symptom` flag marks a topic drawn from the symptom vocabulary. The topic
product keeps `topic_id`, so each related title can be traced back to its
knowledge-graph entity; the query product has no equivalent identifier because
Google returns only the search string.

The related dataset is incomplete in this checkout, and the two products
differ in what survived. The raw topic CSV holds 807 rows and the raw query
CSV holds 938 rows, so the query extract is the larger of the two. Every one
of the 807 topic rows has a blank title, and after the default drop the
monthly topic product has 0 rows. The query CSV carries titles on most of its
rows, and its monthly product holds 15 rows. `manifest_related.csv` records
1,518 answered requests, all with status `ok`, across 1,512 distinct tuples;
six keys appear twice because a retried request was appended rather than
overwritten. Collection has reached only dengue, covering 15 of the 28
geographies. Within those the related-topics phase is far ahead of the
related-queries phase: 1,189 of the rows are `topics` requests against 329
`queries` requests, and the queries side has reached only four geographies.
The two tables therefore cover a subset of states rather than the full
country. The monthly products were generated before the most recent collection
batch, so their counts trail the raw CSVs; re-running the transform raises
them. Both raw extracts span calendar months from 2020-01 to 2026-09.

The empty topic product is a property of the source, not a processing fault.
Google returned blank topic titles for every related-topics request in this
checkout, so the extractor wrote a placeholder row for each and the transform
dropped all of them under `drop_empty_related: true`. The topic CSV is
therefore an all-placeholder file, and the topic product stays empty until
Google returns titles; the transform will populate it on the next run once it
does. The same requests returned titled rows through `related_queries()`,
which is why the query extract carries the usable signal. Only 72 of the 938
query rows are placeholders, and the other 866 carry a title, so the query CSV
is both the larger and the more informative extract.

That incompleteness is expected rather than a defect. The collector is a long,
rate-limited loop of 18,144 requests at 81 months that stops cleanly on HTTP
429 and resumes from its manifest, so a full pass is normally spread over
several sessions. The transform treats a partial extract as a first-class
input: its integrity checks run with `require_complete_ufs=False`, and it
writes the monthly tables from whatever the manifest has already delivered.
Re-running `arboili gt-related` and then `arboili transform gt-related`
extends the same two tables in place, and the row counts above are a snapshot
of a run in progress. Until the collector finishes, the two monthly tables are
a preview of coverage rather than a complete national panel.

## Climate (ERA5 family → UF × epi-week)

Physical covariates come from the ERA5 reanalysis family, reduced to one row
per federative unit and Brazilian epidemiological week so that they join the
case series and the search index without further calendar or geography
alignment. The two reanalyses behind the product are documented in the
literature: ERA5 by Hersbach et al. (2020; doi:10.1002/qj.3803) and ERA5-Land
by Muñoz-Sabater et al. (2021; doi:10.5194/essd-13-4349-2021).
Municipality-daily ERA5-Land parquets come from Zenodo
(doi:10.5281/zenodo.10036212 for 1950–2022; doi:10.5281/zenodo.18257037 for
2025), and gap years such as 2023–2024 come from the Google ARCO-ERA5 public
Zarr store on a 0.25° grid. Copernicus CDS is an optional third backend. The
product is written to `data/climate/era5/ERA5_UF_EW.parquet` with a `.csv.gz`
companion.

| Column | Unit | Description |
|---|---|---|
| `ew` | date (Sunday) | first day of the epidemiological week; join key |
| `state_abbrev` | text | two-letter federative unit abbreviation, 27 units |
| `source` | text | `zenodo` or `arco` |
| `temp_min` | °C | weekly mean of daily minimum 2 m temperature; null on ARCO rows |
| `temp_mean` | °C | weekly mean of daily mean 2 m temperature |
| `temp_max` | °C | weekly mean of daily maximum 2 m temperature; null on ARCO rows |
| `precip_tot` | mm | weekly sum of daily precipitation |
| `rel_humid` | % | weekly mean relative humidity, clipped to [0, 100] |
| `pressure` | hPa | weekly mean surface pressure |
| `rainy_days` | count (0–7) | days in the week with precipitation of at least 0.03 mm |
| `thermal_range` | °C | weekly `temp_max` minus `temp_min`; null when the extremes are null |

In this checkout the table holds 18,036 rows spanning 666 epidemiological
weeks from 2013-12-29 to 2026-09-27 across 27 federative units, of which
14,121 rows are Zenodo and 3,915 are ARCO. Each of the 27 units contributes
668 rows, one for every week-and-source pair. Zenodo supplies 523 of the 666
weeks and ARCO 145, so the two backends meet on two boundary weeks, 2024-12-29
and 2025-12-28, which carry both sources and are the only weeks with more than
one. The week series is complete and gapless from the first week to the last.
Each source is retained as its own row set under the `source` column, so a
reuser can restrict an analysis to one backend or pool both.

Backend spatial resolution differs. Zenodo rows derive from municipality-level
zonal statistics, whereas ARCO rows assign each municipality the nearest 0.25°
grid cell before the same population weighting. The `source` column records
which path produced a row, and the weekly values remain comparable across it
because both paths apply the same unit conversions, the same humidity
derivation and the same population-weighted UF reduction.

The values are weekly summaries rather than daily fields. Temperature,
humidity and pressure are within-week means, precipitation is a within-week
total, and rainy days count the days above the threshold. That grain matches
the weekly resolution of the dengue case series and needs no resampling before
a join.

The null pattern is exact and follows from the two backends. `temp_min`,
`temp_max` and `thermal_range` are null on the 3,915 ARCO rows and on no
Zenodo row, because the ARCO daily extracts keep only the hour-to-day mean of
2 m temperature. Every other column has zero nulls. On the Zenodo rows the
measured ranges are 4.24 to 26.52 °C for `temp_min`, 7.93 to 31.87 °C for
`temp_mean`, 12.10 to 38.30 °C for `temp_max`, 0 to 276.32 mm for
`precip_tot`, 24.27 to 95.97 % for `rel_humid`, 896.54 to 1010.16 hPa for
`pressure`, 0 to 7 for `rainy_days`, and 3.02 to 15.37 °C for `thermal_range`.
The relative-humidity and rainy-day values fall inside the bounds the
integrity check enforces.

The join key shared with the dengue case series and the Google Trends search
index is `(ew, state_abbrev)`, with `source` distinguishing the two backends
where an analysis needs it. `ew` is a Sunday-anchored date, not a week
ordinal, so the three sources align on the same calendar without a lookup
table. The transform is deterministic, and both output formats carry the same
eleven columns. Climate lags are not materialised in this table; lagged
predictors are left to the modelling side. INMET station archives are not an
input to the product.

## Optional INMET stations

Annual INMET station archives are an optional companion to the ERA5 climate
product, collected only when `arboili inmet` is run explicitly. Each archive
is one calendar year of observations from the national station network. No
INMET files are present in this checkout, and none is an input to `ERA5_UF_EW`
or to any other table described here. The collector makes the archives
available on request; the analysis-ready tables do not depend on them.

ERA5 is the default for a structural reason. INMET is a network of point
stations, not a grid. Station siting follows airports, capitals and historical
observing programmes, so coverage is uneven across the 27 federative units,
and a single UF can hold many stations or very few. A state with one long
record and a state with a dozen short ones enter any reduction on unequal
footing. A gridded product also removes the separate decision of how many
stations stand in for a state. ERA5 and ERA5-Land supply complete daily fields
on a regular grid, which the project reduces to federative units without gaps.
The dengue climate literature grounding this project favours reanalysis over
sparse national station networks for UF-scale covariates, and that is why
station data stays outside the transform (see `articles/README.md`).

Reaching the UF × epidemiological-week grain used by the other tables would
need a separate path. Each station file would be reduced to daily summaries of
temperature and precipitation, the daily values floored to the Sunday that
opens each Brazilian epidemiological week, and stations within a UF combined
into one weekly series. That last step needs a weighting rule, because
averaging raw stations would let a densely instrumented state dominate.
Population weights over station catchments, capital-city weights and a plain
mean of stations in the UF are the options the project records, and none is
implemented. Any such path would sit beside `transform climate` rather than
inside it, because the transform reads only the ERA5 tree. The station path
also inherits the reporting gaps of the network, so a UF-week can be empty
where ERA5 always returns a value.

The archives remain a documented option for users who need station-level
observations, for example to validate reanalysis or to examine a municipality
with a long station record. A user who wants that would run the collector and
build a reduction of their own. Reproducing the UF × epi-week panel in this
repository does not require them, and the ERA5 tables stay the join key for
the case and search series.

## Health bulletins
Epidemiological bulletins are periodic publications in which the Brazilian
Ministry of Health reports the national situation of notifiable diseases. The
ARBOILI corpus is the set of bulletin PDFs collected from the Ministry's
central content listing into `data/bulletins/<year>/`, one directory per
publication year from 2019 onward. Collection is configured from 2019, so
earlier editions of the series are out of scope. The listing covers all
notifiable diseases and special editions, not dengue alone, so the corpus is
broader than the arbovirus and respiratory sources that share the ARBOILI
scope; editions on rabies and other topics sit alongside dengue issues.

The corpus holds 204 PDFs spanning 2019 to 2026, laid out as eight year
directories, `2019/` through `2026/`. The year directories are the only
organizational level; the PDFs sit directly inside them. The per-year
composition is uneven: 3 bulletins in 2019, 47 in 2020, 49 in 2021, 48 in
2022, 18 in 2023, 16 in 2024, 19 in 2025 and 4 in 2026. `manifest.csv` records
212 data rows for 204 distinct `(year, filename)` pairs; the eight extra rows
are entries whose resolved filename already existed on disk and were therefore
skipped as duplicates. Those eight duplicate rows fall one per year from 2019
to 2026. 2019 and 2026 are sparse relative to 2020 to 2022.

The configured window runs from 2019 to the current calendar year. Within that
window the crawl resolved every entry it discovered, but the corpus is not a
fixed series: coverage begins at 2019 and the number of editions per year
varies with the listing.

Every file is a raw PDF, with no extraction applied. No text is pulled from a
page and no structured record is produced, so the corpus carries only what the
publisher emitted. Filenames are the originals from the upstream URLs, mixing
`-` and `_` separators and giving volume and edition numbers in more than one
convention, for example `boletim-epidemiologico-svs-38-2-interativo.pdf` and
`boletim_epidemiologico_svs_52.pdf`. The only temporal key the corpus adds is
the year directory; publication dates inside the documents are not extracted,
and no epidemiological-week key is derived. No sidecar or metadata file
accompanies the PDFs. The files come directly from the public listing rather
than from a data repository, so the corpus has no dataset DOI of its own.

Scope is national. The Ministry issues these bulletins as a single series for
the country, and the listing is not partitioned by state, so the corpus has no
federative-unit key as the SINAN, climate and Google Trends products do.
Joining the corpus to the weekly tables would require reading location from
the document text, which the collector never does. No bulletin-derived
variable enters the analysis-ready tables. Because the corpus is not keyed to
a week or a unit, it cannot be reshaped onto the `(ew, state_abbrev)` grain of
the other tables without an extraction step.

`data/bulletins/manifest.csv` is the index for the corpus. Each row gives the
year, the entry URL on the listing, the resolved PDF URL, the stored filename,
a status of `downloaded`, `existing` or `failed`, an error string, and an ISO
8601 timestamp in UTC. The header is
`year,entry_url,pdf_url,filename,status,error,timestamp`.
`data/bulletins/failures.csv` uses the same columns and holds only the failed
subset, which is empty in this checkout.

Completeness tracks the upstream listing rather than a publication cadence.
The count per year reflects what the Ministry had posted and what the crawl
could resolve, not a fixed weekly or monthly schedule. The uneven counts are
the point: 2019 and 2026 are sparse relative to 2020 to 2022, and 2026 is a
partial calendar year because collection stops at the current year. Crawl
completeness also depends on the Plone structure remaining stable, because a
CMS restructure would break both the pagination and the entry resolution
chain. `failures.csv` is empty in this checkout, so every discovered entry
resolved to a file, but a run against a restructured site could record
failures there.

Relative to the structured products, the corpus is a documentary source. It
preserves the Ministry's own published account of each period, which the case
series does not, and it is the raw input for any later text extraction or
content analysis. Its national grain and irregular coverage make it best
suited to manual review or to a separate extraction stage rather than to a
direct join with the weekly state-level tables.

## EBC / Agência Brasil news
The corpus holds article-level news HTML collected from Agência Brasil, the
state news agency operated by Empresa Brasil de Comunicação, for the search
term `dengue`. Every item is a Portuguese-language news article about dengue
in Brazil, saved as a single HTML document together with its metadata record,
and the search listings that produced it are retained alongside. The
collection lives under `data/news/<query>/`, here `data/news/dengue/`, and is
organized into four artefacts. `state.json` records the resume cursor and run
totals. `manifest.jsonl` is an append-only index with one JSON record per
article. `listings/page-NNNN.html` holds the raw search-result HTML for every
listing page visited. `articles/` holds the saved article HTML, named
`<YYYY-MM-DD>_<slug>_<hash>.html`, where the date is the publication date, the
slug comes from the URL tail and the hash is a six-character SHA-1 prefix of
the article URL.

The query matched two content types, `noticia` and `pagina`, so the corpus
mixes full news reports with section pages that the EBC index returns for the
same term. Each listing page carries up to 100 results, and the scraper visits
them in order until the discovered page count is reached. Manifest records
carry the fields a reuser needs to select and locate articles: the URL and
title, the snippet, the publication time in parsed and original form, the site
label and section slug such as `saude`, the thumbnail URL, the listing page
the article appeared on, and the relative path of the saved HTML. They also
carry the fetch timestamp and the HTTP status, with any error message.
Articles that returned a successful response have a local HTML file; failed
ones have their error recorded and no saved body. The section and publication
fields come from the search listing rather than from parsing the article page.

`state.json` is the corpus-level progress record. It stores the run
parameters: the query and site, along with the content types and page size. It
also stores what the search reported, meaning the totals and the last
completed page, plus the run timestamps. Counters for pages processed and for
articles fetched or failed are kept here too. A reuser can read the last
completed page to see how far a run advanced, and the failure counter to judge
how much of the manifest still needs a retry.

Each saved HTML file is the full server response for the article URL,
including the surrounding page markup rather than an isolated article body.
The listing files are likewise the complete search-result pages, so the
ranking and pagination are preserved. The corpus is a snapshot of what the EBC
index returned on the recorded run, not a fixed publication set. Re-running
the collector appends new records to the manifest and fetches only URLs that
are absent or previously failed, so the file grows over successive runs and
can hold more than one record for a URL when a retry succeeds later.

In this checkout the dengue scrape completed 46 listing pages. The state file
reports 4,571 total results and a last completed page of 46, with 4,569
articles fetched and 2 failures. The manifest holds 4,571 lines, matching the
total result count, and 4,569 article HTML files are present under
`articles/`. The gap between those two figures is exactly the two failed
requests: each failure still appends a manifest record with its error text,
but writes no HTML file. Because only status-200 entries are treated as
complete, those two URLs are retried on a later pass.

Geography is national and article-level. Records are keyed by URL and carry no
federative unit field. The corpus therefore cannot be joined to the UF-keyed
case series. The same applies to the Google Trends tables and the climate
features; that link would require a separate geocoding step that does not
exist in this release. Coverage is bounded by the search itself, which returns
what the EBC index exposes for the configured term rather than a curated
article list, and by the 46-page run recorded here.

No text extraction has been applied. The HTML is stored raw, with no
article-body parsing, no named-entity recognition and no language processing,
so the text is available for later NLP work but is not yet tabular. Reusers
who need article text, publication dates at finer resolution, or a state
assignment must derive them from the stored HTML. The manifest and state files
describe what was requested and fetched, not the content of the articles
themselves.

## Reference tables

Three lookup tables are committed to the repository rather than produced by
collection. They fix the identifiers, coordinates and query vocabulary that
the collectors and transforms read at run time.

### Federative units (`data/epidemiological/br_federative_units.csv`)

The federative-unit table has 27 rows, one for each state plus the Federal
District, and four columns: `CODE`, the IBGE unit code (`35` for São Paulo);
`NAME`; `ABBREVIATION`, the two-letter code (`SP`); and `REGION`, the IBGE
macro-region. `ABBREVIATION` supplies the `state_abbrev` values used across
the analysis tables. The SINAN transform (`arboili transform sinan`) joins it
on `SG_UF_NOT` to replace the numeric notification code with `state_abbrev`
before aggregation. Both Google Trends collectors expand `ABBREVIATION` into
the geo codes `BR-SP`, `BR-RJ` and the rest, then append national `BR` as a
separate location. The integrity checks for SINAN, climate and Google Trends
take its 27 codes as the valid state domain, so a federative unit that is
absent here fails validation. No transform reads `REGION`.

### Municipalities (`data/climate/br_municipalities.csv`)

The municipality table covers 5,571 units with columns `code_muni` (the
seven-digit IBGE code), `state_code`, `state_abbrev`, `muni_name`,
`population`, `lat` and `lon`. Population counts come from the IBGE
Estimativas da População 2024, sheet MUNICÍPIOS; the coordinates are
municipality centroids from the kelvins/Municipios-Brasileiros dataset.
`state_abbrev` links each municipality to the federative-unit table, and
`code_muni` is the join key for the municipality-grain ERA5 inputs. The
climate transform uses `population` as the weight when it reduces
municipality-week series to federative units. The centroids are needed only
for the ARCO fallback months, where each municipality is assigned to its
nearest 0.25° grid cell; the Zenodo product already arrives at municipality
grain. `scripts/build_muni_reference.py` regenerates the file when new IBGE
estimates are placed under the temporary path it documents.

### Popular terms (`data/google_trends/popular_terms.csv`)

The popular-terms table is the controlled vocabulary for Google Trends
extraction: 117 rows in 26 groups, with columns `group`, `group_pt`, `terms`,
`exclude`, `main` and `is_code`. Groups cover diseases and symptoms, and
`group_pt` carries the Portuguese label. Rows flagged `exclude` are dropped
before any query is built. For each group the collector prefers a row where
`is_code` is true, whose `terms` holds a Freebase topic ID (`/m/...`), then
falls back to the row flagged `main`, then to the first term; 21 of the 117
rows carry a Freebase code. Each group contributes one query to the weekly
search extractor. The related extractor uses only the coded rows, and the
disease Freebase IDs for dengue, chikungunya, influenza and COVID-19 are
hard-coded in the collectors rather than read from this table.

## Legacy multi-source panel

`data/epidemiological/Arbo_SARI_disease_table.csv` is the merged multi-disease
panel published by Borges et al. (2026). Each row is one Brazilian location in
one epidemiological week, keyed on symptom-onset week (`ew_symptom_onset`, a
Sunday-anchored date) and `location` (a federative-unit abbreviation, plus a
`BR` row that aggregates the 27 units). The columns are `dengue_cases`,
`chik_cases`, `arbo_cases` (dengue plus chikungunya), `sari_cases`, and the
SARI splits `covid_cases`, `flu_cases`, `other_sari_cases` and
`na_sari_cases`. Dengue and chikungunya counts exclude final classification 5.
The table is the one place where the arbovirus and respiratory series are held
together at a common weekly grain.

The table is the published panel. It is not produced by the Python CLI, and it
is absent from this checkout. Neither `Arbo_SARI_disease_table.csv` nor the
`data/epidemiological/SIVEP/` tree that feeds it is on disk, so the R chain
cannot run here without first collecting SIVEP-Gripe `INFLUD*` files.
Reproducing the panel means running the three scripts in order with those
inputs in place. The dengue half additionally needs the input glob in
`2_transform_sinan_data.R` aligned with the `DENGBR<YY>.csv` names the
downloader writes.

Reusers who want a multi-source join now do not have to wait for the R merge.
The Python Google Trends product (`GoogleTrends_search_EW`) and the climate
product (`ERA5_UF_EW`) are both keyed on epidemiological week and state, so
both join directly to the SINAN weekly series on `(ew, state_abbrev)` at the
same grain. The dengue series produced by `transform sinan` supplies the
arbovirus counts under the same key. SARI is the only component that the
Python path cannot supply, so its split columns and the merged table remain an
R-only product until the SIVEP inputs are collected and the scripts are run.
The R panel names its state field `location` and its week field
`ew_symptom_onset`, where the Python products use `state_abbrev` and `ew`; a
join across the two needs those columns renamed.

The three R scripts are the documented path to the published multi-disease
table, not a stage the current Python CLI runs. The merged panel is the
reference for downstream surveillance modelling that needs dengue, chikungunya
and SARI in one table. The per-source Python products are the reference for
work that needs only the arbovirus series or its climate and search
covariates.

## Caveats shared across sources

Google Trends indices are relative within each request window. SINAN recent
weeks are incomplete under reporting delay; Espírito Santo dengue reporting
into SINAN was disrupted in 2020–2022. Climate mixes ERA5-Land (Zenodo) and
ERA5 0.25° (ARCO) with an explicit `source` column; ARCO rows leave
`temp_min` / `temp_max` null. Related Trends, bulletin corpora and news HTML
may be partial or unparsed. Numbers cited for full-corpus SINAN transforms
come from `src/pipeline/sinan/README.md`; verify against local files before
quoting row counts in a manuscript if the checkout is incomplete.
