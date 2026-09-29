# Climate methodology references

Papers used to ground how climate becomes EW×UF features for dengue in Brazil.

Use these three (ignore duplicate filenames if present — prefer the longer names):

| File | Citation | Grain | Source |
|------|----------|-------|--------|
| `01_zhu_2025_spatiotemporal_dengue_climate_factors.pdf` | Zhu et al., *Sci Data* (2025) [doi:10.1038/s41597-025-05045-1](https://doi.org/10.1038/s41597-025-05045-1) | microregion × epi-week | ERA5-Land (GEE), population-weighted |
| `02_chen_moraga_2025_lstm_shap_climate_lags_uf.pdf` | Chen & Moraga, *BMC Public Health* (2025) [doi:10.1186/s12889-025-22106-7](https://doi.org/10.1186/s12889-025-22106-7) | **27 UF × epi-week** | ERA5, population-weighted + SHAP lags |
| `03_sebastianelli_2024_ensemble_ml_climate_fu.pdf` | Sebastianelli et al., *Sci Rep* (2024) [doi:10.1038/s41598-024-52796-9](https://doi.org/10.1038/s41598-024-52796-9) | 27 FU × month | ERA5-Land + RH from dewpoint |

## Shared transformation pattern

1. **Source**: almost always Copernicus **ERA5 / ERA5-Land** (not INMET) — authors cite sparse station coverage at national scale.
2. **Time**: hour/day → **epidemiological week** (Sunday start) — mean for temp/humidity/pressure; **sum** for precip; count **rainy days** (threshold ~0.03 mm).
3. **Space**: grid → admin unit with **population-weighted** average (WorldPop/IBGE), not simple area mean.
4. **Core features**: `temp_{min,med,max}`, `precip_{tot}` (+ rainy days), `rel_humid_{min,med,max}`, often pressure / thermal_range.
5. **Model use** (Chen & Moraga): climate enters as **lags** (weeks); SHAP picks top vars per UF because of multicollinearity within min/med/max groups.

## Implication for this repo (INMET ZIPs)

INMET is point stations, not a grid. To mimic the literature at UF×EW you still need: station → daily min/mean/max/sum → Sunday-anchored epi-week → UF aggregate (population- or capital-weighted, or mean of stations in UF). ERA5 remains the literature default if station coverage is uneven.
