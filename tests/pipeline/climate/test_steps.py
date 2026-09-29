"""Climate step unit tests on synthetic frames."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl
import pytest

from src.pipeline.climate.spec import (
    DEFAULT_RAINY_DAY_MM,
    EW,
    PRECIP_TOT,
    REL_HUMID,
    STATE_ABBREV,
    TEMP_MEAN,
)
from src.pipeline.climate.steps import (
    add_epiweek,
    aggregate_mun_week,
    convert_physical_units,
    mark_rainy_days,
    pop_weighted_to_uf,
    relative_humidity,
)
from src.pipeline.epiweek import floor_to_sunday

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "climate"


def test_floor_to_sunday_shared() -> None:
    frame = pl.DataFrame({"d": [date(2024, 1, 10)]}, schema={"d": pl.Date})
    assert frame.select(floor_to_sunday("d").alias("ew"))["ew"][0] == date(2024, 1, 7)


def test_relative_humidity_saturation() -> None:
    """When T == Td, RH should be ~100%."""
    frame = pl.DataFrame({"t": [25.0], "td": [25.0]})
    rh = frame.select(relative_humidity(pl.col("t"), pl.col("td")).alias("rh"))["rh"][0]
    assert rh == pytest.approx(100.0, abs=0.1)


def test_relative_humidity_dry_air() -> None:
    frame = pl.DataFrame({"t": [30.0], "td": [10.0]})
    rh = frame.select(relative_humidity(pl.col("t"), pl.col("td")).alias("rh"))["rh"][0]
    assert 0 < rh < 50


def test_kelvin_and_precip_unit_conversion() -> None:
    daily = pl.DataFrame(
        {
            "code_muni": [1100015],
            "date": [date(2025, 1, 1)],
            "temp_min_k": [273.15 + 20.0],
            "temp_mean_k": [273.15 + 25.0],
            "temp_max_k": [273.15 + 30.0],
            "dewpoint_k": [273.15 + 25.0],  # Td == T → RH ≈ 100%
            "precip_m": [0.005],  # 5 mm
            "pressure_pa": [101325.0],
        }
    ).lazy()
    out = convert_physical_units(daily).collect()
    assert out[TEMP_MEAN][0] == pytest.approx(25.0)
    assert out[PRECIP_TOT][0] == pytest.approx(5.0)
    assert out["pressure"][0] == pytest.approx(1013.25)
    assert out[REL_HUMID][0] == pytest.approx(100.0, abs=0.5)
    assert out["thermal_range"][0] == pytest.approx(10.0)


def test_rainy_day_threshold() -> None:
    daily = pl.DataFrame(
        {
            "code_muni": [1, 1, 1],
            "date": [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)],
            PRECIP_TOT: [0.02, 0.03, 1.0],
        }
    ).lazy()
    flagged = mark_rainy_days(daily, DEFAULT_RAINY_DAY_MM).collect()
    assert flagged["_is_rainy"].to_list() == [False, True, True]


def test_add_epiweek_and_weekly_agg() -> None:
    # Sun–Sat week starting 2024-01-07
    daily = pl.DataFrame(
        {
            "code_muni": [1, 1, 1],
            "date": [date(2024, 1, 7), date(2024, 1, 8), date(2024, 1, 9)],
            "temp_min": [20.0, 21.0, 22.0],
            "temp_mean": [25.0, 26.0, 27.0],
            "temp_max": [30.0, 31.0, 32.0],
            PRECIP_TOT: [1.0, 0.0, 2.0],
            REL_HUMID: [80.0, 70.0, 60.0],
            "pressure": [1000.0, 1001.0, 1002.0],
            "_is_rainy": [True, False, True],
        }
    ).lazy()
    weekly = aggregate_mun_week(add_epiweek(daily)).collect()
    assert weekly.height == 1
    assert weekly[EW][0] == date(2024, 1, 7)
    assert weekly[PRECIP_TOT][0] == pytest.approx(3.0)
    assert weekly["rainy_days"][0] == pytest.approx(2.0)
    assert weekly[TEMP_MEAN][0] == pytest.approx(26.0)


def test_population_weighted_mean() -> None:
    mun_week = pl.DataFrame(
        {
            "code_muni": [1, 2],
            EW: [date(2024, 1, 7), date(2024, 1, 7)],
            "temp_min": [20.0, 30.0],
            "temp_mean": [20.0, 30.0],
            "temp_max": [20.0, 30.0],
            PRECIP_TOT: [0.0, 10.0],
            REL_HUMID: [50.0, 50.0],
            "pressure": [1000.0, 1000.0],
            "rainy_days": [0.0, 1.0],
            "thermal_range": [0.0, 0.0],
        }
    ).lazy()
    mun = pl.DataFrame(
        {
            "code_muni": [1, 2],
            STATE_ABBREV: ["SP", "SP"],
            "population": [1.0, 3.0],
        }
    ).lazy()
    uf = pop_weighted_to_uf(mun_week, mun).collect()
    assert uf.height == 1
    # (20*1 + 30*3) / 4 = 27.5
    assert uf[TEMP_MEAN][0] == pytest.approx(27.5)
    assert uf[PRECIP_TOT][0] == pytest.approx(7.5)


def test_population_weighted_all_null_stays_null() -> None:
    """ARCO lacks daily min/max — must not become 0 after weighting."""
    mun_week = pl.DataFrame(
        {
            "code_muni": [1, 2],
            EW: [date(2024, 1, 7), date(2024, 1, 7)],
            "temp_min": [None, None],
            "temp_mean": [20.0, 30.0],
            "temp_max": [None, None],
            PRECIP_TOT: [0.0, 10.0],
            REL_HUMID: [50.0, 50.0],
            "pressure": [1000.0, 1000.0],
            "rainy_days": [0.0, 1.0],
            "thermal_range": [None, None],
        }
    ).lazy()
    mun = pl.DataFrame(
        {
            "code_muni": [1, 2],
            STATE_ABBREV: ["SP", "SP"],
            "population": [1.0, 3.0],
        }
    ).lazy()
    uf = pop_weighted_to_uf(mun_week, mun).collect()
    assert uf["temp_min"][0] is None
    assert uf["temp_max"][0] is None
    assert uf[TEMP_MEAN][0] == pytest.approx(27.5)


def test_fixture_zenodo_roundtrip_schema() -> None:
    """Tiny committed Zenodo-like fixture pivots to expected feature columns."""
    path = FIXTURES / "zenodo_daily_sample.parquet"
    if not path.exists():
        pytest.skip("climate fixture not built")
    frame = pl.read_parquet(path)
    assert {"code_muni", "date", "temp_mean_k", "precip_m"}.issubset(frame.columns)
