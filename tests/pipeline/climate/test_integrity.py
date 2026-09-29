"""Climate integrity checks on a small synthetic UF×EW series."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from src.pipeline.climate.integrity import run_all
from src.pipeline.climate.spec import OUTPUT_COLUMNS
from src.pipeline.climate.steps import (
    add_epiweek,
    aggregate_mun_week,
    convert_physical_units,
    mark_rainy_days,
    order_columns,
    pop_weighted_to_uf,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "climate"


def _synthetic_series() -> pl.DataFrame:
    daily = pl.read_parquet(FIXTURES / "zenodo_daily_sample.parquet").lazy()
    mun = pl.scan_csv(FIXTURES / "br_municipalities_sample.csv")
    frame = convert_physical_units(daily)
    frame = mark_rainy_days(frame)
    frame = aggregate_mun_week(add_epiweek(frame))
    uf = pop_weighted_to_uf(frame, mun)
    return order_columns(uf, "zenodo").collect()


def test_integrity_passes_on_fixture_pipeline() -> None:
    series = _synthetic_series()
    assert tuple(series.columns) == OUTPUT_COLUMNS
    checks = run_all(series, FIXTURES / "br_federative_units_sample.csv")
    failed = [c for c in checks if not c.passed]
    assert not failed, "; ".join(str(c) for c in failed)
    assert set(series["state_abbrev"].to_list()) == {"SP", "RJ"}
    assert series["ew"][0] == date(2025, 1, 5)  # Sunday
