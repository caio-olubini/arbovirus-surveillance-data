"""Google Trends thin-transform step tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from src.pipeline.google_trends.spec import EW, OUTPUT_COLUMNS, STATE_ABBREV
from src.pipeline.google_trends.steps import build, drop_national, rename_keys

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "google_trends"


def test_rename_date_and_location() -> None:
    frame = pl.DataFrame(
        {"date": ["2020-01-26"], "location": ["SP"], "topic": ["dengue"], "value": [1.0]}
    ).lazy()
    out = rename_keys(frame).collect()
    assert EW in out.columns and STATE_ABBREV in out.columns
    assert "date" not in out.columns and "location" not in out.columns


def test_build_floors_to_sunday_and_keeps_br() -> None:
    series = build(FIXTURES / "GoogleTrends_search_sample.csv", keep_br=True).collect()
    assert tuple(series.columns) == OUTPUT_COLUMNS
    assert series[EW].dt.weekday().unique().to_list() == [7]
    assert "BR" in series[STATE_ABBREV].to_list()
    # 2020-01-26 is already a Sunday
    assert date(2020, 1, 26) in series[EW].to_list()


def test_drop_br() -> None:
    series = build(FIXTURES / "GoogleTrends_search_sample.csv", keep_br=False).collect()
    assert "BR" not in series[STATE_ABBREV].to_list()
    assert set(series[STATE_ABBREV].to_list()) == {"AC", "SP"}


def test_drop_national_helper() -> None:
    frame = pl.DataFrame(
        {STATE_ABBREV: ["SP", "BR"], EW: [date(2020, 1, 26), date(2020, 1, 26)]}
    ).lazy()
    assert drop_national(frame, keep_br=False).collect().height == 1
