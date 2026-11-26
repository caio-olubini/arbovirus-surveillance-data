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

Every item in `references.csv` that is an article and is open access is on disk,
except the Hersbach ERA5 description. The five in the tables above were already
present; the two added on **2026-11-10** are the project's own data descriptor
and the format-restriction paper carried over from the author's library:

| File | Citation | Source of the file |
|------|----------|--------------------|
| `00_borges_2026_arboili_data_descriptor.pdf` | Borges et al., *Sci Data* (2026) [doi:10.1038/s41597-025-06155-6](https://doi.org/10.1038/s41597-025-06155-6) | nature.com published PDF (gold OA) — the reference article for this dataset |
| `06_tam_2024_let_me_speak_freely.pdf` | Tam et al., EMNLP Industry Track (2024) [doi:10.18653/v1/2024.emnlp-industry.91](https://doi.org/10.18653/v1/2024.emnlp-industry.91) | ACL Anthology published PDF (gold OA) |

The four added on **2026-11-21** are the sources the plan's Passo 1 had left
unverified (see [notas 06](../notes/06-desenho-do-experimento.md)); all four were
confirmed by API before download:

| File | Citation | Source of the file |
|------|----------|--------------------|
| `08_koplewitz_2022_internet_data_20_cities_brazil.pdf` | Koplewitz et al., *PLoS Negl. Trop. Dis.* (2022) [doi:10.1371/journal.pntd.0010071](https://doi.org/10.1371/journal.pntd.0010071) | PLOS published PDF (gold OA) |
| `09_silva_nery_2026_ml_capitals_brazil.pdf` | Silva & Nery, *Int. J. Biometeorol.* (2026) [doi:10.1007/s00484-026-03300-7](https://doi.org/10.1007/s00484-026-03300-7) | Springer published PDF (OA) — the Europe PMC endpoint returned JSON, the Springer link served the real file |
| `10_arboalvo_2025_bayesian_natal_rn.pdf` | Alves et al., *PLoS Negl. Trop. Dis.* (2025) [doi:10.1371/journal.pntd.0012984](https://doi.org/10.1371/journal.pntd.0012984) | PLOS published PDF (gold OA) |
| `11_palmer_2026_dengue_hospitalizations_delays.pdf` | Palmer et al., *PLOS Digit. Health* (2026) [doi:10.1371/journal.pdig.0001206](https://doi.org/10.1371/journal.pdig.0001206) | PLOS published PDF (gold OA) |

The twelve added on **2026-11-25** are the forecasting, nowcasting and
forecast-evaluation line the literature review needed as base texts. Eleven came
from publisher or repository open access; one is an accepted-manuscript copy.
`File Attachments` in `references.csv` was filled for each.

| File | Citation | Source of the file |
|------|----------|--------------------|
| `07_araujo_2026_probabilistic_forecasts_dengue_preparedness.pdf` | Araujo et al., *PNAS* (2026) [doi:10.1073/pnas.2508989123](https://doi.org/10.1073/pnas.2508989123) | Europe PMC `PMC12912988` — supersedes the earlier "no PDF on purpose" note, which predated the PMC deposit |
| `12_johansson_2019_open_challenge_probabilistic_dengue.pdf` | Johansson et al., *PNAS* (2019) [doi:10.1073/pnas.1909865116](https://doi.org/10.1073/pnas.1909865116) | eScholarship (UC) accepted manuscript — the PNAS PDF endpoint answers 403 |
| `13_bracher_2021_evaluating_epidemic_forecasts_interval.pdf` | Bracher et al., *PLoS Comput. Biol.* (2021) [doi:10.1371/journal.pcbi.1008618](https://doi.org/10.1371/journal.pcbi.1008618) | PLOS published PDF (gold OA) |
| `14_gneiting_2007_strictly_proper_scoring_rules.pdf` | Gneiting & Raftery, *JASA* (2007) [doi:10.1198/016214506000001437](https://doi.org/10.1198/016214506000001437) | Raftery's UW publication page, author copy of the published version — Unpaywall reports it closed |
| `17_pollett_2021_reporting_items_epidemic_forecasting.pdf` | Pollett et al., *PLoS Med.* (2021) [doi:10.1371/journal.pmed.1003793](https://doi.org/10.1371/journal.pmed.1003793) | PLOS published PDF (gold OA) |
| `18_wu_2025_ensemble_short_term_dengue_forecasts.pdf` | Wu et al., *PNAS* (2025) [doi:10.1073/pnas.2422335122](https://doi.org/10.1073/pnas.2422335122) | Europe PMC `PMC12377650` |
| `19_xiao_2025_dengue_nowcasting_brazil_surveillance.pdf` | Xiao et al., *PLoS Negl. Trop. Dis.* (2025) [doi:10.1371/journal.pntd.0012501](https://doi.org/10.1371/journal.pntd.0012501) | PLOS published PDF (gold OA) |
| `20_picinini_freitas_2025_probabilistic_epidemic_burden.pdf` | Picinini Freitas et al., *Infect. Dis. Model.* (2025) [doi:10.1016/j.idm.2025.07.014](https://doi.org/10.1016/j.idm.2025.07.014) | Europe PMC `PMC12359213` |
| `21_chen_moraga_2025_assessing_dengue_forecasting_methods.pdf` | Chen & Moraga, *Trop. Med. Health* (2025) [doi:10.1186/s41182-025-00723-7](https://doi.org/10.1186/s41182-025-00723-7) | BMC published PDF (gold OA) |
| `23_bastos_2019_correcting_reporting_delays.pdf` | Bastos et al., *Stat. Med.* (2019) [doi:10.1002/sim.8303](https://doi.org/10.1002/sim.8303) | arXiv `1709.09150` preprint of the published article |
| `24_lim_2021_temporal_fusion_transformers.pdf` | Lim et al., *Int. J. Forecast.* (2021) [doi:10.1016/j.ijforecast.2021.03.012](https://doi.org/10.1016/j.ijforecast.2021.03.012) | arXiv `1912.09363` preprint of the published article |
| `26_tan_2024_language_models_useful_time_series.pdf` | Tan et al., NeurIPS (2024) [arXiv:2406.16964](https://arxiv.org/abs/2406.16964) | arXiv preprint |

The same pass filled the empty `File Attachments` of
`00_borges_2026_arboili_data_descriptor.pdf`, which was already on disk but
unlinked.

- Four items in `references.csv` are **closed access** and are therefore still
  absent — the first three confirmed against Unpaywall on 2026-11-25, the fourth
  against OpenAlex on 2026-11-26: Tashman (2000)
  [doi:10.1016/s0169-2070(00)00065-0](https://doi.org/10.1016/s0169-2070(00)00065-0),
  Bergmeir & Benítez (2012)
  [doi:10.1016/j.ins.2011.12.028](https://doi.org/10.1016/j.ins.2011.12.028),
  Codeço et al. (2018)
  [doi:10.1016/j.respe.2018.05.408](https://doi.org/10.1016/j.respe.2018.05.408),
  and Hyndman & Fan (1996)
  [doi:10.1080/00031305.1996.10473566](https://doi.org/10.1080/00031305.1996.10473566),
  *The American Statistician* 50(4), 361–365 — the definition of the type-7 sample
  quantile the forecast intervals are read on. The Codeço item is not an article at
  all but a one-page congress abstract (S386) in *Revue d'Épidémiologie et de Santé
  Publique*; no full text exists to fetch.
- `05_munoz_sabater_2021_era5_land.pdf` — obtained from Copernicus ESSD open-access PDF (`essd-13-4349-2021.pdf`).
- `04_hersbach_2020_era5_global_reanalysis.pdf` — **the one open-access article still missing** (re-checked 2026-11-10). The article is open access (CC BY, published version), but Wiley serves it behind a **Cloudflare JS challenge** (`Just a moment...` → HTTP 403 to every automated request). Unpaywall, OpenAlex, Semantic Scholar and OpenAIRE all resolve to the same blocked Wiley URL — there is no green-OA repository copy to fall back on, the Wiley TDM endpoint needs a token, the Wayback Machine has no snapshot of the PDF, and the ECMWF eLibrary path 404s. Header/browser spoofing does not clear the challenge. **Download it manually in a browser** from [doi:10.1002/qj.3803](https://doi.org/10.1002/qj.3803) (or the direct link `https://rmets.onlinelibrary.wiley.com/doi/pdf/10.1002/qj.3803`) and save as `04_hersbach_2020_era5_global_reanalysis.pdf`.

The two short filenames (`02_lstm_shap_dengue_brazil_climate_lags.pdf`, `03_ensemble_ml_dengue_outbreaks_climate.pdf`) are failed downloads — 1.8 KB HTML error pages ("Preparing to download", the PMC proof-of-work challenge), not PDFs — and duplicate the longer-named files above; ignore or delete them.

PDFs under `articles/` are **git-ignored** (`articles/**/*.pdf`) on purpose: they
are local reading artefacts. What is versioned is the bibliography itself —
`references.csv`, `search.json`, `ranking.md`, `relatorio.md` and the READMEs.
A fresh clone therefore has the metadata but none of the PDFs.

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
