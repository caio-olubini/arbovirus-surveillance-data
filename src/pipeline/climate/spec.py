"""Climate feature schema, unit conventions, and Zenodo filename maps.

Physical features only — no lags (those belong on the model side). Keys are
Sunday-anchored epidemiological week (`ew`) and federative-unit abbreviation.
"""

from __future__ import annotations

# Output keys
EW = "ew"
STATE_ABBREV = "state_abbrev"
SOURCE = "source"

# Physical feature columns (paper methods / articles/README.md)
TEMP_MIN = "temp_min"
TEMP_MEAN = "temp_mean"
TEMP_MAX = "temp_max"
PRECIP_TOT = "precip_tot"
REL_HUMID = "rel_humid"
PRESSURE = "pressure"
RAINY_DAYS = "rainy_days"
THERMAL_RANGE = "thermal_range"

FEATURE_COLUMNS = (
    TEMP_MIN,
    TEMP_MEAN,
    TEMP_MAX,
    PRECIP_TOT,
    REL_HUMID,
    PRESSURE,
    RAINY_DAYS,
    THERMAL_RANGE,
)

OUTPUT_COLUMNS = (EW, STATE_ABBREV, SOURCE, *FEATURE_COLUMNS)

SOURCE_ZENODO = "zenodo"
SOURCE_ARCO = "arco"

# Literature rainy-day threshold (~0.03 mm); see pipeline README.
DEFAULT_RAINY_DAY_MM = 0.03

# ERA5 native units → analysis units
KELVIN_TO_CELSIUS = 273.15
PRECIP_M_TO_MM = 1000.0
PRESSURE_PA_TO_HPA = 100.0

# Zenodo long-parquet files → (canonical feature name before unit conversion,
# the `name` statistic to keep). Zonal mean is the area-representative value.
ZENODO_FILES: dict[str, tuple[str, str]] = {
    "2m_temperature_min.parquet": ("temp_min_k", "2m_temperature_min_mean"),
    "2m_temperature_mean.parquet": ("temp_mean_k", "2m_temperature_mean_mean"),
    "2m_temperature_max.parquet": ("temp_max_k", "2m_temperature_max_mean"),
    "2m_dewpoint_temperature_mean.parquet": (
        "dewpoint_k",
        "2m_dewpoint_temperature_mean_mean",
    ),
    "total_precipitation_sum.parquet": (
        "precip_m",
        "total_precipitation_sum_mean",
    ),
    "surface_pressure_mean.parquet": (
        "pressure_pa",
        "surface_pressure_mean_mean",
    ),
}

# ARCO NetCDF variable → intermediate name (Kelvin / metres / Pascals)
ARCO_VARIABLES: dict[str, str] = {
    "2m_temperature": "temp_mean_k",
    "2m_dewpoint_temperature": "dewpoint_k",
    "total_precipitation": "precip_m",
    "surface_pressure": "pressure_pa",
}

OUTPUT_NAME = "ERA5_UF_EW"

# Municipality reference columns
CODE_MUNI = "code_muni"
POPULATION = "population"
LAT = "lat"
LON = "lon"
