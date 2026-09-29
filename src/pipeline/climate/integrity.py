"""Integrity checks over a produced climate UF×EW series."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from .spec import (
    EW,
    FEATURE_COLUMNS,
    OUTPUT_COLUMNS,
    PRECIP_TOT,
    RAINY_DAYS,
    REL_HUMID,
    SOURCE,
    SOURCE_ARCO,
    SOURCE_ZENODO,
    STATE_ABBREV,
    TEMP_MAX,
    TEMP_MEAN,
    TEMP_MIN,
)

SUNDAY = 7
GROUP_KEYS = (EW, STATE_ABBREV, SOURCE)


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str = ""

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}{f': {self.detail}' if self.detail else ''}"


def check_schema(series: pl.DataFrame) -> Check:
    actual = tuple(series.columns)
    if actual == OUTPUT_COLUMNS:
        return Check("schema", True, f"{len(actual)} columns in published order")
    return Check("schema", False, f"expected {OUTPUT_COLUMNS}, got {actual}")


def check_unique_keys(series: pl.DataFrame) -> Check:
    duplicates = series.height - series.select(GROUP_KEYS).unique().height
    if duplicates == 0:
        return Check("unique_keys", True, f"{series.height:,} rows, all keys distinct")
    return Check("unique_keys", False, f"{duplicates:,} duplicate group keys")


def check_weeks_start_on_sunday(series: pl.DataFrame) -> Check:
    bad = series.filter(
        pl.col(EW).is_not_null() & (pl.col(EW).dt.weekday() != SUNDAY)
    ).height
    if bad == 0:
        return Check("weeks_start_on_sunday", True, "all ew dates are Sundays")
    return Check("weeks_start_on_sunday", False, f"{bad:,} non-Sunday ew values")


def check_states(series: pl.DataFrame, fu_path: Path) -> Check:
    expected = set(pl.read_csv(fu_path)["ABBREVIATION"].to_list())
    actual = set(series[STATE_ABBREV].unique().to_list())
    unknown = actual - expected
    if unknown:
        return Check("states", False, f"not in reference table: {sorted(unknown)}")
    missing = expected - actual
    if missing:
        return Check("states", False, f"never appear in the series: {sorted(missing)}")
    return Check("states", True, f"all {len(expected)} federative units present")


def check_source_domain(series: pl.DataFrame) -> Check:
    allowed = {SOURCE_ZENODO, SOURCE_ARCO}
    actual = set(series[SOURCE].unique().to_list())
    bad = actual - allowed
    if bad:
        return Check("source_domain", False, f"unexpected sources: {sorted(bad)}")
    return Check("source_domain", True, f"sources {sorted(actual)}")


def check_rh_bounds(series: pl.DataFrame) -> Check:
    bad = series.filter(
        pl.col(REL_HUMID).is_not_null()
        & ((pl.col(REL_HUMID) < 0) | (pl.col(REL_HUMID) > 100))
    ).height
    if bad == 0:
        return Check("rh_bounds", True, "rel_humid in [0, 100] or null")
    return Check("rh_bounds", False, f"{bad:,} rows outside [0, 100]")


def check_rainy_days_bounds(series: pl.DataFrame) -> Check:
    bad = series.filter(
        pl.col(RAINY_DAYS).is_not_null()
        & ((pl.col(RAINY_DAYS) < 0) | (pl.col(RAINY_DAYS) > 7.01))
    ).height
    if bad == 0:
        return Check("rainy_days_bounds", True, "rainy_days in [0, 7] or null")
    return Check("rainy_days_bounds", False, f"{bad:,} rows outside [0, 7]")


def check_precip_non_negative(series: pl.DataFrame) -> Check:
    bad = series.filter(pl.col(PRECIP_TOT).is_not_null() & (pl.col(PRECIP_TOT) < 0)).height
    if bad == 0:
        return Check("precip_non_negative", True, "precip_tot >= 0 or null")
    return Check("precip_non_negative", False, f"{bad:,} negative precip rows")


def check_temp_order(series: pl.DataFrame) -> Check:
    """Where all three temps are present, min ≤ mean ≤ max."""
    bad = series.filter(
        pl.col(TEMP_MIN).is_not_null()
        & pl.col(TEMP_MEAN).is_not_null()
        & pl.col(TEMP_MAX).is_not_null()
        & ((pl.col(TEMP_MIN) > pl.col(TEMP_MEAN)) | (pl.col(TEMP_MEAN) > pl.col(TEMP_MAX)))
    ).height
    if bad == 0:
        return Check("temp_order", True, "temp_min ≤ temp_mean ≤ temp_max when all present")
    return Check("temp_order", False, f"{bad:,} rows with inconsistent temperatures")


def check_feature_nulls_allowed(series: pl.DataFrame) -> Check:
    """Nulls are allowed (ARCO lacks daily min/max); at least one feature populated."""
    any_feature = pl.any_horizontal([pl.col(c).is_not_null() for c in FEATURE_COLUMNS])
    empty = series.filter(~any_feature).height
    if empty == 0:
        return Check("feature_nulls_allowed", True, "every row has ≥1 non-null feature")
    return Check("feature_nulls_allowed", False, f"{empty:,} rows with all features null")


def run_all(series: pl.DataFrame, fu_path: Path) -> list[Check]:
    return [
        check_schema(series),
        check_unique_keys(series),
        check_weeks_start_on_sunday(series),
        check_states(series, fu_path),
        check_source_domain(series),
        check_rh_bounds(series),
        check_rainy_days_bounds(series),
        check_precip_non_negative(series),
        check_temp_order(series),
        check_feature_nulls_allowed(series),
    ]
