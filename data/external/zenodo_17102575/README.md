# Frozen seed — Zenodo `10.5281/zenodo.17102575`

Third-party published dataset, kept here **immutable** as the frozen base for the
sources this checkout has not collected itself. Do not edit these files and do
not point a collector's `out_dir` at this directory: the Google Trends related
extractor read-merge-writes its output CSVs, which would silently corrupt the
seed.

| | |
|---|---|
| **DOI (version)** | [10.5281/zenodo.17102575](https://doi.org/10.5281/zenodo.17102575) |
| **DOI (concept)** | [10.5281/zenodo.17102574](https://doi.org/10.5281/zenodo.17102574) — 1 version published |
| **Authors** | Borges, Marcelo E.; Almeida, Alexandra; Codeço, Cláudia T.; Machado, Dalila |
| **Published** | 2025-09-11 |
| **License** | CC BY 4.0 — attribution required |
| **Companion paper** | Borges et al., *Scientific Data* 13, 68 (2026), [10.1038/s41597-025-06155-6](https://doi.org/10.1038/s41597-025-06155-6) |
| **Retrieved** | 2026-11-01, from `https://zenodo.org/api/records/17102575/files/<name>/content` |

## Files

Only the five files this checkout does **not** produce itself are kept here.
`SINAN_dengue_cases.csv.gz` and `GoogleTrends_search.csv` are in the Zenodo
record too, but this repo collects and transforms those itself, so they were
left out rather than duplicated.

| File | Rows | Grain | Coverage |
|---|---|---|---|
| `GoogleTrends_related_query.csv` | 79,255 | query × month × location × disease | 2020-01 → 2025-03 |
| `GoogleTrends_related_topic.csv` | 120,232 | topic × month × location × disease | 2020-01 → 2025-03 |
| `Arbo_SARI_disease_table.csv` | 23,268 | epi-week × location | 2009-04-19 → 2025-03-16 |
| `SIVEP_cases.csv.gz` | 546,414 | epi-week × state × classification | 2009-04-19 → 2025-03-23 |
| `SINAN_chik_cases.csv.gz` | 259,619 | epi-week × state × classification | 2014-08-10 → 2025-03-23 |

Row counts are the file line count minus the header, measured at retrieval.
Integrity: `checksums.sha256` (SHA-256, computed locally) — the MD5 values
published by Zenodo are reproduced in the table below and were verified to
match on download.

### Google Trends related

```
GoogleTrends_related_query.csv   topic_title, date, location, value, disease
GoogleTrends_related_topic.csv   topic_title, topic_id, date, location, value, disease, key_symptom
```

- `date` is `YYYY-MM`; `location` is a two-letter UF code plus `BR` — **28
  locations** (27 UFs + national), 4 diseases (`Dengue`, `Chikungunya`,
  `Influenza/gripe`, `COVID-19`), 63 months.
- `value` is the Google Trends 0–100 relative scale; blank means no data.
- `topic_id` is a Freebase/Knowledge-Graph id (`/m/…`, `/g/…`).
- `key_symptom` flags rows that are one of the controlled-vocabulary symptoms.
- These column names are **identical** to this repo's own partial extract
  (`data/google_trends/GoogleTrends_related_{topic,query}.csv`), so the two
  concatenate directly.

### Epidemiological panels

```
Arbo_SARI_disease_table.csv   ew_symptom_onset, location, dengue_cases, chik_cases,
                              arbo_cases, sari_cases, covid_cases, flu_cases,
                              other_sari_cases, na_sari_cases
SIVEP_cases.csv.gz            ew_recorded, ew_notification, ew_symptom_onset,
                              final_classification_original, state_abbrev,
                              final_classification_new, case_count, fever, cough,
                              sore_throat, breath_shortness, resp_distress, diarrhea,
                              vomiting, smell_loss, taste_loss, ab_pain, fatigue
SINAN_chik_cases.csv.gz       ew_recorded, ew_notification, ew_symptom_onset,
                              final_classification, state_abbrev, case_count, fever,
                              myalgia, headache, rash, vomiting, nausea, back_pain,
                              conjunctivitis, arthritis, arthralgia, petechiae,
                              leukopenia, tourniquet_test, retro-orbital_pain
```

The symptom columns are weekly **counts of records carrying that symptom**, not
booleans. `ew_*` columns are Sunday-anchored dates, matching the join key used
by this repo's transforms.

## Caveats before using this as a base

1. **Time window is shorter than this repo's own extract.** The published GT
   related data stops at **2025-03**; the local partial extract runs to
   **2026-09**. The two are complementary, not interchangeable — the recent
   months exist only locally. Same for the panels: the merged table ends
   2025-03-16.
2. **Different extraction method.** The authors used the R package
   `gtrendsAPI` (endpoint `googleapis.com/trends/v1beta`); this repo uses
   `pytrends`. On the 8,476 (query, date, location) keys present in both for
   Dengue, 63% match exactly, the median absolute difference is **1 point** on
   the 0–100 scale, and 61 keys (0.7%) differ by more than 10. Same
   measurement, different normalisation — this divergence must be stated in
   the methods, not silently merged.
3. **`state_abbrev` is inconsistent between the two SINAN/SIVEP files.**
   `SIVEP_cases.csv.gz` uses two-letter UF codes; `SINAN_chik_cases.csv.gz`
   uses numeric IBGE codes (`11`, `12`, …). Normalise before joining.
4. **The `ew_*` columns do not share one span, and some are sparse.** Measured
   over the whole files:

   | File | Column | Span | Blank |
   |---|---|---|---|
   | SIVEP | `ew_recorded` | 2009-05-03 → 2025-03-23 | 3,429 |
   | SIVEP | `ew_notification` | 2009-04-19 → 2025-03-23 | 1 |
   | SIVEP | `ew_symptom_onset` | 2009-04-19 → 2024-12-29 | 0 |
   | chik | `ew_recorded` | 2021-01-03 → 2025-03-23 | **87,715 (34%)** |
   | chik | `ew_notification` | 2014-12-28 → 2025-03-16 | 0 |
   | chik | `ew_symptom_onset` | 2014-08-10 → 2025-03-16 | 0 |

   In particular `SINAN_chik_cases.csv.gz` cannot be keyed on `ew_recorded` —
   a third of its rows have no value there. Use `ew_symptom_onset` or
   `ew_notification`.
5. **Topics are not empty here.** The local pytrends extract returned empty
   topic titles for every request; this seed has 1,372 distinct topic titles.
   It is currently the only source of related-topic data in the project.

## Checksums

| File | Size (B) | SHA-256 (local) | MD5 (Zenodo, verified) |
|---|---|---|---|
| `GoogleTrends_related_query.csv` | 3,339,944 | `d130be4b…4956aa` | `01a1612eb5d4ee17e4f5dc01c44f41de` |
| `GoogleTrends_related_topic.csv` | 6,313,678 | `20859d18…d42f6a` | `bc22deb23ed58682918305bf48e22235` |
| `Arbo_SARI_disease_table.csv` | 841,126 | `dd73355a…d48ef6` | `b6f0dcd38970cd199721db109762aefd` |
| `SIVEP_cases.csv.gz` | 4,438,619 | `3426be56…3b3db53` | `448a8db96bab93e8fd9858b7fba38ad1` |
| `SINAN_chik_cases.csv.gz` | 2,329,212 | `585d8e05…c15905` | `b89094d188fddba14fd332fbde60e48e` |

Full digests: `checksums.sha256`. Verify with
`shasum -a 256 -c data/external/zenodo_17102575/checksums.sha256`.

## Attribution

If these files feed a published product, cite the dataset (Borges et al., 2025,
Zenodo, CC BY 4.0) alongside the companion paper. CC BY 4.0 requires
attribution — see the DOI block above.
