# Climate transformation — ERA5 → UF × epidemiological week

How downloaded ERA5 products become analysis-ready climate features keyed by
federative unit and Sunday-anchored epidemiological week. Methods notes for the
data paper; grounded in the dengue–climate literature summarised in
[`articles/README.md`](../../../articles/README.md).

```bash
uv run arboili transform climate
```

Step-by-step walkthrough (fixtures + literature checklist):
[`notebooks/climate_pipeline.ipynb`](../../../notebooks/climate_pipeline.ipynb).

---

## 1. Objective and scope

**Goal.** Produce physical climate covariates at the same `(ew, state_abbrev)`
grain as the SINAN case series and Google Trends search index, so the sources
join without further calendar or geography alignment.

**Inputs.**

| Product | Path | Grain | Role |
|---|---|---|---|
| Zenodo ERA5-Land mun daily | `data/climate/era5/zenodo/<coverage>/*.parquet` | municipality × day | Primary (1950–2022, 2025, …) |
| ARCO-ERA5 daily NetCDF | `data/climate/era5/arco/era5_arco_YYYYMM.nc` | 0.25° grid × day | Gap years (2023–2024, …) |

**Output.** `data/climate/era5/ERA5_UF_EW.parquet` (+ `.csv.gz`), one row per
`(ew, state_abbrev, source)`.

**Out of scope.** INMET station ZIPs; CDS NetCDF transform (collection may still
download CDS); climate *lags* (model-side); WorldPop rasters.

---

## 2. Spatial aggregation — population-weighted means

Following Zhu et al. (2025) and Chen & Moraga (2025), grid/municipality values
are reduced to federative units with **population-weighted means**, not area
means.

Reference table: [`data/climate/br_municipalities.csv`](../../../data/climate/br_municipalities.csv)

| Column | Source |
|---|---|
| `code_muni` | IBGE 7-digit municipality code |
| `state_abbrev` / `state_code` | IBGE UF |
| `population` | IBGE Estimativas da População 2024 (`POP2024_*.xls`, sheet MUNICÍPIOS) |
| `lat`, `lon` | Municipality centroids ([kelvins/Municipios-Brasileiros](https://github.com/kelvins/Municipios-Brasileiros)) |

Regenerate with `uv run --with xlrd python scripts/build_muni_reference.py`
(after placing the IBGE `.xls` and centroids CSV under `/tmp/arboili_ref/`).

### Zenodo path

Files are already municipality daily zonal stats. After unit conversion and
epi-week aggregation at mun level, each feature \(x\) becomes

\[
x_{\mathrm{UF},w} = \frac{\sum_m p_m\, x_{m,w}}{\sum_m p_m}
\]

over municipalities \(m\) in the UF with population \(p_m\).

### ARCO path (pragmatic nearest-cell map)

ARCO cells are assigned to municipalities by **nearest centroid** on the 0.25°
grid (equirectangular; ARCO longitudes in 0–360 are shifted to match geographic
lon). Each municipality then inherits that cell’s daily values, and the same
population-weighted UF reduction applies.

**Tradeoff.** This is not a true polygon/area intersection with WorldPop. It is
reproducible without GIS dependencies, matches the locked “population-weighted
mun/grid → UF” decision, and is adequate for UF-scale surveillance covariates.
A future revision may replace nearest-centroid with raster zonal stats.

ARCO daily files carry **mean** temperature only (hour→day mean in collection).
`temp_min` and `temp_max` are therefore **null** for `source=arco`; `temp_mean`,
precip, humidity, and pressure are populated. Zenodo rows carry all three
temperature statistics.

---

## 3. Temporal aggregation — Sunday epi weeks

Daily municipality series are floored to the Sunday starting each Brazilian
epidemiological week (`src.pipeline.epiweek.floor_to_sunday`), then:

| Feature | Within-week rule (mun) |
|---|---|
| `temp_min`, `temp_mean`, `temp_max`, `rel_humid`, `pressure` | mean of daily values |
| `precip_tot` | sum of daily mm |
| `rainy_days` | count of days with precip ≥ threshold |
| `thermal_range` | `temp_max − temp_min` after the weekly means |

---

## 4. Physical features and units

| Column | Unit | Derivation |
|---|---|---|
| `temp_min` / `temp_mean` / `temp_max` | °C | ERA5 Kelvin − 273.15 |
| `precip_tot` | mm | ERA5 metres × 1000 |
| `rel_humid` | % | August–Roche–Magnus from \(T\) and dewpoint (°C), clipped to [0, 100] |
| `pressure` | hPa | ERA5 Pascals / 100 |
| `rainy_days` | count (0–7) | days with `precip_tot` ≥ **0.03 mm** |
| `thermal_range` | °C | `temp_max − temp_min` |
| `source` | text | `zenodo` or `arco` |

**Rainy-day threshold.** ~0.03 mm, as used in the dengue–climate feature sets
reviewed in `articles/README.md` (Sebastianelli / related ERA5 pipelines).
Configurable via `pipeline.climate.rainy_day_mm` / `--rainy-day-mm`.

**Nulls stay null.** No zero-filling for missing temperatures (ARCO min/max) or
gaps. Population weighting skips nulls per feature so an all-null field does not
collapse to 0. Tiny negative precip values from ARCO float noise are clipped to 0.

**No lags.** Lagged climate predictors are a modelling choice and are not
materialised here.

---

## 5. Zenodo statistic selection

Each Zenodo parquet is long (`code_muni`, `date`, `name`, `value`) with several
zonal statistics. The pipeline keeps the **area-mean** statistic
(e.g. `2m_temperature_mean_mean`, `total_precipitation_sum_mean`) so municipality
values are comparable regardless of polygon size.

---

## 6. Validation

`src.pipeline.climate.integrity` checks schema, unique `(ew, state_abbrev, source)`,
Sunday anchors, UF membership, source domain, RH/precip/rainy-day bounds, and
temperature order when min/mean/max are all present. Unit tests exercise RH,
unit conversion, Sunday flooring, and population weighting on committed fixtures
under `tests/fixtures/climate/`.
