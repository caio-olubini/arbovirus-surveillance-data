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
**plus** the frozen seed at `data/external/zenodo_17102575/`  
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

### Two sources, one table

The related tables are built from **two inputs per table**, concatenated:

1. this repo's own extractor output (`arboili gt-related`), and
2. the frozen seed — the published dataset of Borges et al.,
   [Zenodo 10.5281/zenodo.17102575](https://doi.org/10.5281/zenodo.17102575),
   kept immutable at `data/external/zenodo_17102575/`.

Neither alone is complete. The seed carries all four diseases across all 28
locations but stops at **2025-03**; our extractor reaches **2026-10** but is
still filling in the earlier months, and its related-*topics* requests return
nothing at all — the seed is the only source of topic data in the project.

Every output row carries a **`source`** column (`zenodo` | `pytrends`) recording
which client produced it, so the split is auditable and reportable.

**On overlapping keys the seed wins.** The two inputs were produced by different
clients — the R package `gtrendsAPI` for the seed, `pytrends` for ours — and they
disagree: over the 8,476 keys present in both (Dengue), 63% match exactly, the
median absolute difference is **1 point** on the 0–100 scale, and 61 keys (0.7%)
differ by more than 10. Precedence is fixed in `spec.SOURCE_PRECEDENCE` rather
than left to input order, which is what keeps the table comparable to the
published dataset across the span that dataset covers. The consequence to
disclose in the paper: the Dengue series changes client at 2025-04.

```bash
uv run arboili transform gt-related            # seed + our extract (default)
uv run arboili transform gt-related --no-seed  # our extract only
```

The dedup keeps **one row per group key**, so the unique-key integrity check
still holds. Empty placeholders are dropped *before* dedup, so a blank seed row
can never shadow a real row from our extractor.

Provenance, checksums and per-file caveats:
[`data/external/zenodo_17102575/README.md`](../../../data/external/zenodo_17102575/README.md).

---

## 3. National (`BR`) rows

Kept by default for both stages (`keep_br: true`). `--drop-br` omits them.

---

## 4. Validation

- Search: `integrity.run_all`
- Related: `integrity.run_all_related(..., kind="topics"|"queries")` with
  `require_complete_ufs=False` by default. Its `sources` check reports the
  `zenodo` / `pytrends` split and fails on any label `SOURCE_PRECEDENCE` does
  not list.

Fixtures under `tests/fixtures/google_trends/`.
