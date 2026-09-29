# Google Trends transforms

Post-collection reshape of Google Trends extracts so they share join keys with
SINAN and climate. Two stages:

| Stage | CLI | Grain | Status |
|---|---|---|---|
| Search index | `arboili transform gtrends` | UF × Sunday epi-week | complete extract |
| Related topics/queries | `arboili transform gt-related` | UF × month | **partial extract OK** |

```bash
uv run arboili transform gtrends      # alias: gt-search
uv run arboili transform gt-related
```

Walkthrough notebooks:

- [`notebooks/gtrends_pipeline.ipynb`](../../../notebooks/gtrends_pipeline.ipynb) — search
- [`notebooks/gtrends_related_pipeline.ipynb`](../../../notebooks/gtrends_related_pipeline.ipynb) — related

---

## 1. Search (weekly)

**In.** `data/google_trends/GoogleTrends_search.csv`  
**Out.** `GoogleTrends_search_EW.parquet` (+ `.csv.gz`).

Thin rename/validate only: `date`→`ew`, `location`→`state_abbrev`, Sunday floor,
optional `--drop-br`. No rescaling, no topic filtering, no imputation.

| Extractor | Transform | Notes |
|---|---|---|
| `date` | `ew` | Parsed as date; floored to Sunday |
| `location` | `state_abbrev` | 27 UF abbreviations + optional `BR` |
| `topic` | `topic` | unchanged |
| `value` | `value` | Google Trends index 0–100; nulls stay null |

Integrity: schema, unique `(ew, state_abbrev, topic)`, Sundays, full UF set,
value ∈ [0, 100].

---

## 2. Related topics & queries (monthly)

**In.** `GoogleTrends_related_topic.csv`, `GoogleTrends_related_query.csv`  
**Out.** `GoogleTrends_related_topic_monthly.*`, `GoogleTrends_related_query_monthly.*`

**Grain stays monthly** — not expanded to epi-weeks. Related vocabulary is
exploratory / co-occurrence, not a weekly surveillance panel.

**Partial extracts are first-class.** The collector is ~18 h and often incomplete
(HTTP 429). The transform runs on whatever is present; integrity does **not**
require all 27 UFs. Re-run after more `arboili gt-related` progress.

| Extractor | Transform |
|---|---|
| `date` (`YYYY-MM`) | `month` |
| `location` | `state_abbrev` |
| `topic_title` | `related_title` |
| `topic_id` | `topic_id` (topics only) |
| `value` | `value` (coerces `"<1"` → 0.1) |
| `disease` | `disease` |
| `key_symptom` | `key_symptom` (topics only) |

**Empty placeholders.** When Google returns no related terms, the extractor may
still write a row with blank `topic_title`. Default `drop_empty_related: true`
drops those; pass `--keep-empty` to retain them for audit.

---

## 3. National (`BR`) rows

Kept by default for both stages (`keep_br: true`). `--drop-br` omits them.

---

## 4. Validation

- Search: `integrity.run_all`
- Related: `integrity.run_all_related(..., kind="topics"|"queries")` with
  `require_complete_ufs=False` by default

Fixtures under `tests/fixtures/google_trends/`.
