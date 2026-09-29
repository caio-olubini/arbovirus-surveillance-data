"""Climate transformation steps (LazyFrame in → LazyFrame out where possible)."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import polars as pl

from ..epiweek import floor_to_sunday
from .spec import (
    ARCO_VARIABLES,
    CODE_MUNI,
    DEFAULT_RAINY_DAY_MM,
    EW,
    FEATURE_COLUMNS,
    KELVIN_TO_CELSIUS,
    LAT,
    LON,
    OUTPUT_COLUMNS,
    POPULATION,
    PRECIP_M_TO_MM,
    PRECIP_TOT,
    PRESSURE,
    PRESSURE_PA_TO_HPA,
    RAINY_DAYS,
    REL_HUMID,
    SOURCE,
    STATE_ABBREV,
    TEMP_MAX,
    TEMP_MEAN,
    TEMP_MIN,
    THERMAL_RANGE,
    ZENODO_FILES,
)

log = logging.getLogger("pipeline.climate")

# August–Roche–Magnus constants for saturation vapour pressure (T in °C).
_MAGNUS_A = 17.625
_MAGNUS_B = 243.04


def relative_humidity(temp_c: pl.Expr, dewpoint_c: pl.Expr) -> pl.Expr:
    """RH (%) from air temperature and dewpoint (°C), August–Roche–Magnus.

    Clipped to [0, 100]. Null when either input is null.
    """
    e = (_MAGNUS_A * dewpoint_c / (_MAGNUS_B + dewpoint_c)).exp()
    es = (_MAGNUS_A * temp_c / (_MAGNUS_B + temp_c)).exp()
    return (100.0 * e / es).clip(0.0, 100.0)


def load_municipalities(path: Path) -> pl.LazyFrame:
    """Municipality → UF + population (+ centroids for ARCO nearest-cell map)."""
    return pl.scan_csv(path).select(
        pl.col(CODE_MUNI).cast(pl.Int64),
        pl.col("state_code").cast(pl.Int16),
        pl.col(STATE_ABBREV).cast(pl.String),
        pl.col(POPULATION).cast(pl.Float64),
        pl.col(LAT).cast(pl.Float64),
        pl.col(LON).cast(pl.Float64),
    )


def scan_zenodo_variable(
    path: Path,
    feature: str,
    name_stat: str,
    from_year: int | None = None,
    to_year: int | None = None,
) -> pl.LazyFrame:
    """Read one Zenodo long parquet, keep one zonal statistic, optionally year-filter."""
    frame = (
        pl.scan_parquet(path)
        .filter(pl.col("name") == name_stat)
        .select(
            pl.col(CODE_MUNI).cast(pl.Int64),
            pl.col("date").cast(pl.Date),
            pl.col("value").cast(pl.Float64).alias(feature),
        )
    )
    if from_year is not None:
        frame = frame.filter(pl.col("date").dt.year() >= from_year)
    if to_year is not None:
        frame = frame.filter(pl.col("date").dt.year() <= to_year)
    return frame


def join_zenodo_daily(
    coverage_dir: Path,
    from_year: int | None = None,
    to_year: int | None = None,
) -> pl.LazyFrame:
    """Join the six Zenodo variable files into one mun×date wide frame (Kelvin/m/Pa)."""
    pieces: list[pl.LazyFrame] = []
    for filename, (feature, name_stat) in ZENODO_FILES.items():
        path = coverage_dir / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Missing Zenodo file {path}. Run `arboili era5` first."
            )
        pieces.append(scan_zenodo_variable(path, feature, name_stat, from_year, to_year))

    frame = pieces[0]
    for piece in pieces[1:]:
        frame = frame.join(piece, on=[CODE_MUNI, "date"], how="full", coalesce=True)
    return frame


def convert_physical_units(frame: pl.LazyFrame) -> pl.LazyFrame:
    """Kelvin→°C, precip m→mm, pressure Pa→hPa; derive RH and thermal range."""
    temp_mean_c = pl.col("temp_mean_k") - KELVIN_TO_CELSIUS
    dewpoint_c = pl.col("dewpoint_k") - KELVIN_TO_CELSIUS
    temp_min_c = pl.col("temp_min_k") - KELVIN_TO_CELSIUS
    temp_max_c = pl.col("temp_max_k") - KELVIN_TO_CELSIUS

    # Clamp tiny negative precip (ARCO float noise) to 0; true missings stay null.
    precip_mm = (
        pl.when(pl.col("precip_m").is_null())
        .then(None)
        .otherwise((pl.col("precip_m") * PRECIP_M_TO_MM).clip(lower_bound=0.0))
    )
    return frame.with_columns(
        temp_min_c.alias(TEMP_MIN),
        temp_mean_c.alias(TEMP_MEAN),
        temp_max_c.alias(TEMP_MAX),
        precip_mm.alias(PRECIP_TOT),
        (pl.col("pressure_pa") / PRESSURE_PA_TO_HPA).alias(PRESSURE),
        relative_humidity(temp_mean_c, dewpoint_c).alias(REL_HUMID),
    ).with_columns(
        (pl.col(TEMP_MAX) - pl.col(TEMP_MIN)).alias(THERMAL_RANGE),
    )


def mark_rainy_days(
    frame: pl.LazyFrame, threshold_mm: float = DEFAULT_RAINY_DAY_MM
) -> pl.LazyFrame:
    """Boolean daily rainy flag; null precip → null flag (stays out of the count)."""
    return frame.with_columns(
        pl.when(pl.col(PRECIP_TOT).is_null())
        .then(None)
        .otherwise(pl.col(PRECIP_TOT) >= threshold_mm)
        .alias("_is_rainy")
    )


def add_epiweek(frame: pl.LazyFrame, date_column: str = "date") -> pl.LazyFrame:
    return frame.with_columns(floor_to_sunday(date_column).alias(EW)).drop(date_column)


def aggregate_mun_week(frame: pl.LazyFrame) -> pl.LazyFrame:
    """Mun × epi-week: means for continuous vars, sum precip, count rainy days."""
    return frame.group_by(CODE_MUNI, EW).agg(
        pl.col(TEMP_MIN).mean(),
        pl.col(TEMP_MEAN).mean(),
        pl.col(TEMP_MAX).mean(),
        pl.col(PRECIP_TOT).sum(),
        pl.col(REL_HUMID).mean(),
        pl.col(PRESSURE).mean(),
        pl.col("_is_rainy").sum().cast(pl.Float64).alias(RAINY_DAYS),
    ).with_columns(
        (pl.col(TEMP_MAX) - pl.col(TEMP_MIN)).alias(THERMAL_RANGE),
    )


def _pop_weighted_mean(column: str) -> pl.Expr:
    """Population-weighted mean that stays null when every value is null.

    polars' ``sum`` over an all-null series is 0, which would otherwise turn
    missing ARCO ``temp_min``/``temp_max`` into zeros after dividing by total
    population.
    """
    weight = pl.when(pl.col(column).is_not_null()).then(pl.col(POPULATION)).otherwise(0.0)
    weighted_sum = (
        pl.when(pl.col(column).is_not_null())
        .then(pl.col(column) * pl.col(POPULATION))
        .otherwise(0.0)
        .sum()
    )
    weight_sum = weight.sum()
    return (
        pl.when(weight_sum > 0)
        .then(weighted_sum / weight_sum)
        .otherwise(None)
        .alias(column)
    )


def pop_weighted_to_uf(
    frame: pl.LazyFrame, municipalities: pl.LazyFrame
) -> pl.LazyFrame:
    """Population-weighted mean of mun×EW features up to UF×EW."""
    joined = frame.join(
        municipalities.select(CODE_MUNI, STATE_ABBREV, POPULATION),
        on=CODE_MUNI,
        how="inner",
    )
    return joined.group_by(EW, STATE_ABBREV).agg(
        *[_pop_weighted_mean(column) for column in FEATURE_COLUMNS]
    )


def order_columns(frame: pl.LazyFrame, source: str) -> pl.LazyFrame:
    return (
        frame.with_columns(pl.lit(source).alias(SOURCE))
        .select(OUTPUT_COLUMNS)
        .sort(SOURCE, STATE_ABBREV, EW)
    )


def nearest_grid_indices(
    mun_lat: np.ndarray,
    mun_lon: np.ndarray,
    grid_lat: np.ndarray,
    grid_lon: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Map each municipality to the nearest ARCO grid cell (equirectangular approx)."""
    # ARCO longitudes are often 0–360; mun lon is geographic (−180–180).
    lon = np.asarray(grid_lon, dtype=np.float64)
    if lon.min() >= 0 and mun_lon.min() < 0:
        mun_lon_use = np.where(mun_lon < 0, mun_lon + 360.0, mun_lon)
    else:
        mun_lon_use = mun_lon

    # Nearest via searchsorted on sorted axes (lat decreasing in ARCO).
    lat = np.asarray(grid_lat, dtype=np.float64)
    lat_asc = lat[0] < lat[-1]
    lat_sorted = lat if lat_asc else lat[::-1]
    lat_pos = np.searchsorted(lat_sorted, mun_lat)
    lat_pos = np.clip(lat_pos, 1, len(lat_sorted) - 1)
    left, right = lat_sorted[lat_pos - 1], lat_sorted[lat_pos]
    pick_right = np.abs(mun_lat - right) < np.abs(mun_lat - left)
    lat_idx_sorted = np.where(pick_right, lat_pos, lat_pos - 1)
    lat_idx = lat_idx_sorted if lat_asc else (len(lat) - 1 - lat_idx_sorted)

    lon_sorted = np.sort(lon)
    lon_pos = np.searchsorted(lon_sorted, mun_lon_use)
    lon_pos = np.clip(lon_pos, 1, len(lon_sorted) - 1)
    left, right = lon_sorted[lon_pos - 1], lon_sorted[lon_pos]
    pick_right = np.abs(mun_lon_use - right) < np.abs(mun_lon_use - left)
    lon_val = np.where(pick_right, right, left)
    # Map chosen lon values back to original index.
    lon_index_map = {float(v): i for i, v in enumerate(lon)}
    lon_idx = np.array([lon_index_map[float(v)] for v in lon_val], dtype=np.int64)
    return lat_idx.astype(np.int64), lon_idx


def arco_month_to_muni_daily(
    nc_path: Path,
    municipalities: pl.DataFrame,
    lat_idx: np.ndarray,
    lon_idx: np.ndarray,
) -> pl.DataFrame:
    """Extract ARCO daily fields at each municipality's nearest grid cell.

    ARCO monthly NetCDFs carry daily *means* for temperature (not true daily
    min/max). ``temp_min`` / ``temp_max`` are left null; ``temp_mean`` is filled.
    """
    import xarray as xr

    ds = xr.open_dataset(nc_path)
    try:
        times = pl.Series("date", pd_dates_to_date(ds["time"].values))
        code_muni = municipalities[CODE_MUNI].to_numpy()
        n_mun = len(code_muni)
        n_time = times.len()

        n = n_mun * n_time
        columns: dict[str, object] = {
            CODE_MUNI: np.repeat(code_muni, n_time),
            "date": np.tile(times.to_numpy(), n_mun),
            # ARCO daily means have no true min/max — leave null, not NaN.
            "temp_min_k": pl.Series("temp_min_k", [None] * n, dtype=pl.Float64),
            "temp_max_k": pl.Series("temp_max_k", [None] * n, dtype=pl.Float64),
        }

        for nc_var, feature in ARCO_VARIABLES.items():
            if nc_var not in ds:
                log.warning("%s: missing variable %s", nc_path.name, nc_var)
                columns[feature] = pl.Series(feature, [None] * n, dtype=pl.Float64)
                continue
            data = np.asarray(ds[nc_var].values)  # (time, lat, lon)
            # fancy index: for each mun, take its (lat_idx, lon_idx) over time
            extracted = data[:, lat_idx, lon_idx]  # (time, mun)
            columns[feature] = extracted.T.reshape(-1)

        for key in ("temp_mean_k", "dewpoint_k", "precip_m", "pressure_pa"):
            columns.setdefault(key, pl.Series(key, [None] * n, dtype=pl.Float64))

        # NetCDF missing values arrive as NaN; keep them as proper nulls.
        return pl.DataFrame(columns).with_columns(pl.col(pl.Float64).fill_nan(None))
    finally:
        ds.close()


def pd_dates_to_date(values: object) -> list:
    """Convert xarray/numpy datetime64 values to Python date objects."""
    import pandas as pd

    return list(pd.to_datetime(values).date)


def build_zenodo_coverage(
    coverage_dir: Path,
    municipalities: pl.LazyFrame,
    source: str,
    from_year: int | None = None,
    to_year: int | None = None,
    rainy_day_mm: float = DEFAULT_RAINY_DAY_MM,
) -> pl.LazyFrame:
    """Full Zenodo path for one coverage folder → UF×EW features."""
    daily = join_zenodo_daily(coverage_dir, from_year, to_year)
    daily = convert_physical_units(daily)
    daily = mark_rainy_days(daily, rainy_day_mm)
    weekly = aggregate_mun_week(add_epiweek(daily))
    uf = pop_weighted_to_uf(weekly, municipalities)
    return order_columns(uf, source)


def build_arco_month(
    nc_path: Path,
    municipalities_df: pl.DataFrame,
    lat_idx: np.ndarray,
    lon_idx: np.ndarray,
    municipalities_lf: pl.LazyFrame,
    source: str,
    rainy_day_mm: float = DEFAULT_RAINY_DAY_MM,
) -> pl.LazyFrame:
    """One ARCO monthly NetCDF → UF×EW features."""
    daily = arco_month_to_muni_daily(nc_path, municipalities_df, lat_idx, lon_idx).lazy()
    daily = convert_physical_units(daily)
    daily = mark_rainy_days(daily, rainy_day_mm)
    weekly = aggregate_mun_week(add_epiweek(daily))
    uf = pop_weighted_to_uf(weekly, municipalities_lf)
    return order_columns(uf, source)
