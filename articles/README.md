# Climate methodology references

Papers used to ground how climate becomes EW×UF features for dengue in Brazil,
plus the canonical ERA5 / ERA5-Land reanalysis descriptions behind the Zenodo
and ARCO products consumed by this pipeline.

## Dengue–climate feature engineering (UF / microregion × time)

Use these three for spatial and temporal reduction choices (ignore duplicate
filenames if present — prefer the longer names):

| File | Citation | Grain | Source |
|------|----------|-------|--------|
| `01_zhu_2025_spatiotemporal_dengue_climate_factors.pdf` | Zhu et al., *Sci Data* (2025) [doi:10.1038/s41597-025-05045-1](https://doi.org/10.1038/s41597-025-05045-1) | microregion × epi-week | ERA5-Land (GEE), population-weighted |
| `02_chen_moraga_2025_lstm_shap_climate_lags_uf.pdf` | Chen & Moraga, *BMC Public Health* (2025) [doi:10.1186/s12889-025-22106-7](https://doi.org/10.1186/s12889-025-22106-7) | **27 UF × epi-week** | ERA5, population-weighted + SHAP lags |
| `03_sebastianelli_2024_ensemble_ml_climate_fu.pdf` | Sebastianelli et al., *Sci Rep* (2024) [doi:10.1038/s41598-024-52796-9](https://doi.org/10.1038/s41598-024-52796-9) | 27 FU × month | ERA5-Land + RH from dewpoint |

## Reanalysis sources (ERA5 family)

Zenodo municipality-daily files are built from **ERA5-Land**; ARCO gap months
come from the public **ERA5** 0.25° archive. These two papers document those
reanalyses:

| File | Citation | Role in this repo |
|------|----------|-------------------|
| `04_hersbach_2020_era5_global_reanalysis.pdf` | Hersbach et al., *Q. J. R. Meteorol. Soc.* (2020) [doi:10.1002/qj.3803](https://doi.org/10.1002/qj.3803) | Canonical ERA5 description; underlies Google ARCO-ERA5 extracts (`gs://gcp-public-data-arco-era5/...`) used for gap years (e.g. 2023–2024) |
| `05_munoz_sabater_2021_era5_land.pdf` | Muñoz-Sabater et al., *Earth Syst. Sci. Data* (2021) [doi:10.5194/essd-13-4349-2021](https://doi.org/10.5194/essd-13-4349-2021) | ERA5-Land description; underlies Zenodo municipality daily parquets (doi:10.5281/zenodo.10036212, doi:10.5281/zenodo.18257037) |

**Download status (this checkout):**

- `05_munoz_sabater_2021_era5_land.pdf` — obtained from Copernicus ESSD open-access PDF (`essd-13-4349-2021.pdf`).
- `04_hersbach_2020_era5_global_reanalysis.pdf` — **not obtained here** (re-checked 2026-10-07). The article is open access (CC BY, published version), but Wiley serves it behind a **Cloudflare JS challenge** (`Just a moment...` → HTTP 403 to every automated request). Unpaywall, OpenAlex, Semantic Scholar and OpenAIRE all resolve to the same blocked Wiley URL — there is no green-OA repository copy to fall back on, and the Wiley TDM endpoint needs a token. Header/browser spoofing does not clear the challenge. **Download it manually in a browser** from [doi:10.1002/qj.3803](https://doi.org/10.1002/qj.3803) (or the direct link `https://rmets.onlinelibrary.wiley.com/doi/pdf/10.1002/qj.3803`) and save as `04_hersbach_2020_era5_global_reanalysis.pdf`.

The two short filenames (`02_lstm_shap_dengue_brazil_climate_lags.pdf`, `03_ensemble_ml_dengue_outbreaks_climate.pdf`) are failed downloads — 4 KB HTML error pages, not PDFs — and duplicate the longer-named files above; ignore or delete them.

## Shared transformation pattern

1. **Source**: almost always Copernicus **ERA5 / ERA5-Land** (not INMET) — authors cite sparse station coverage at national scale.
2. **Time**: hour/day → **epidemiological week** (Sunday start) — mean for temp/humidity/pressure; **sum** for precip; count **rainy days** (threshold ~0.03 mm).
3. **Space**: grid → admin unit with **population-weighted** average (WorldPop/IBGE), not simple area mean.
4. **Core features**: `temp_{min,med,max}`, `precip_{tot}` (+ rainy days), `rel_humid_{min,med,max}`, often pressure / thermal_range.
5. **Model use** (Chen & Moraga): climate enters as **lags** (weeks); SHAP picks top vars per UF because of multicollinearity within min/med/max groups.

## Implication for this repo (INMET ZIPs)

INMET is point stations, not a grid. To mimic the literature at UF×EW you still need: station → daily min/mean/max/sum → Sunday-anchored epi-week → UF aggregate (population- or capital-weighted, or mean of stations in UF). ERA5 remains the literature default if station coverage is uneven.

---

# Reference library — `references.csv`

`references.csv` is the project's Zotero-importable bibliography: every source
**cited by this repository**, in the Zotero CSV export schema (87 columns,
`Item Type` in Zotero's camelCase names, `Author` as `Last, First; Last, First`).
It is the single place to register a new citation — add the row here when a
pipeline or text starts citing something new, then re-import.

## Importing into Zotero

Zotero → **File → Import…** → select `references.csv` → *Import into a new
collection* (or an existing one). The header names match Zotero's own export, so
the field mapping is automatic; nothing needs to be set by hand.

Notes:

- The file is **UTF-8 without BOM**, which is what Zotero expects. Do not
  re-save it from Excel (that adds a BOM and mangles accented names).
- `Key` is intentionally **empty** for repo-derived rows so Zotero assigns fresh
  keys; the one row carried over from an existing library (`Tam et al. 2024`)
  keeps its original key.
- Rows carry `Manual Tags` prefixed with `arboili` to make the import easy to
  find and merge.
- Re-importing will create duplicates if the item already exists in the target
  library — check Zotero's **Duplicate Items** pane afterwards. Duplicate
  detection is by DOI for the journal articles and datasets.

## What is in it

| Type | Count | Items |
|------|-------|-------|
| `journalArticle` | 6 | Borges 2026 (ARBOILI descriptor), Zhu 2025, Chen & Moraga 2025, Sebastianelli 2024, Hersbach 2020 (ERA5), Muñoz-Sabater 2021 (ERA5-Land) |
| `dataset` | 4 | Zenodo 17102575 (ARBOILI), Zenodo 10036212 (ERA5-Land 1950–2022), Zenodo 18257037 (ERA5-Land 2025), IBGE population estimates 2024 |
| `software` | 1 | kelvins/Municipios-Brasileiros (municipality centroids) |
| `conferencePaper` | 1 | Tam et al. 2024 (carried over from the author's library) |

Bibliographic metadata for the papers and Zenodo records was pulled from the
Crossref and DataCite APIs (DOIs in the file), not transcribed by hand.
