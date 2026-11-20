"""The target panel. Its whole job is to refuse a series with a hole in it."""

from __future__ import annotations

import datetime as dt

import polars as pl
import pytest

from src.forecast.panel import TargetGapError, load_target
from src.forecast.spec import CASES, EW
from tests.forecast.conftest import DISCARDED, START, SUSPECTED


def write(tmp_path, frame: pl.DataFrame) -> str:
    path = tmp_path / "SINAN_dengue_cases.parquet"
    frame.write_parquet(path)
    return str(path)


def test_a_continuous_series_becomes_a_continuous_panel(tmp_path, cases_from_weeks):
    frame = cases_from_weeks({i: [(10, SUSPECTED)] for i in range(5)})
    panel = load_target(write(tmp_path, frame), from_year=None)
    assert panel.height == 5
    assert panel[CASES].null_count() == 0
    assert panel[EW].to_list()[0] == START


def test_the_calendar_has_one_row_per_week_and_no_repeats(tmp_path, cases_from_weeks):
    frame = cases_from_weeks({i: [(1, SUSPECTED)] for i in range(30)})
    panel = load_target(write(tmp_path, frame), from_year=None)
    weeks = panel[EW].to_list()
    assert weeks == sorted(set(weeks))
    assert (weeks[-1] - weeks[0]).days == 29 * 7


def test_a_missing_week_is_refused_not_filled(tmp_path, cases_from_weeks):
    """The guard that stops the seasonal lag from reading the wrong week."""
    weeks = {i: [(1, SUSPECTED)] for i in range(10)}
    del weeks[5]
    with pytest.raises(TargetGapError, match="1 week"):
        load_target(write(tmp_path, cases_from_weeks(weeks)), from_year=None)


def test_the_error_names_the_missing_week(tmp_path, cases_from_weeks):
    weeks = {i: [(1, SUSPECTED)] for i in range(10)}
    del weeks[5]
    missing = START + dt.timedelta(weeks=5)
    with pytest.raises(TargetGapError, match=str(missing)):
        load_target(write(tmp_path, cases_from_weeks(weeks)), from_year=None)


def test_an_absent_tail_outside_the_window_is_not_a_gap(tmp_path, cases_from_weeks):
    """The window is defined by its own first and last week, so weeks that were
    never in the data are simply not part of the question."""
    frame = cases_from_weeks({i: [(1, SUSPECTED)] for i in (4, 5, 6)})
    panel = load_target(write(tmp_path, frame), from_year=None)
    assert panel.height == 3


def test_a_partial_year_raises_and_from_year_is_the_way_out(tmp_path, cases_from_weeks):
    """The real 2013 behaves like this: present, but with weeks missing.

    Unfiltered the panel refuses; narrowed to the complete year it is usable.
    """
    weeks = {i: [(1, SUSPECTED)] for i in list(range(50)) + [55]}
    frame = cases_from_weeks(weeks)
    with pytest.raises(TargetGapError):
        load_target(write(tmp_path, frame), from_year=None)

    panel = load_target(write(tmp_path, frame), from_year=2021)
    assert panel.height == 1
    assert panel[EW].to_list() == [START + dt.timedelta(weeks=55)]


def test_discarded_notifications_are_not_cases(tmp_path, cases_from_weeks):
    frame = cases_from_weeks({0: [(7, SUSPECTED), (1000, DISCARDED)]})
    panel = load_target(write(tmp_path, frame), from_year=None)
    assert panel[CASES].to_list() == [7.0]


def test_cases_awaiting_classification_count_as_suspected(tmp_path, cases_from_weeks):
    """The null classification is the most recent week, not an absent one."""
    frame = cases_from_weeks({0: [(5, SUSPECTED)]}).with_columns(
        pl.lit(None, dtype=pl.Int32).alias("final_classification")
    )
    panel = load_target(write(tmp_path, frame), from_year=None)
    assert panel[CASES].to_list() == [5.0]


def test_rows_in_the_same_week_are_summed(tmp_path, cases_from_weeks):
    frame = cases_from_weeks({0: [(3, SUSPECTED), (4, SUSPECTED)]})
    panel = load_target(write(tmp_path, frame), from_year=None)
    assert panel[CASES].to_list() == [7.0]


def test_a_window_with_no_cases_is_refused(tmp_path, cases_from_weeks):
    frame = cases_from_weeks({0: [(1, DISCARDED)]})
    with pytest.raises(TargetGapError, match="No case weeks"):
        load_target(write(tmp_path, frame), from_year=None)


def test_the_panel_is_sorted_by_week(tmp_path, cases_from_weeks):
    shuffled = pl.DataFrame(
        {
            "ew_symptom_onset": [
                START + dt.timedelta(weeks=w) for w in (2, 0, 1)
            ],
            "case_count": [3, 1, 2],
            "final_classification": [SUSPECTED] * 3,
        }
    )
    panel = load_target(write(tmp_path, shuffled), from_year=None)
    assert panel[CASES].to_list() == [1.0, 2.0, 3.0]


def test_a_to_year_narrows_the_end_of_the_window(tmp_path, cases_from_weeks):
    frame = cases_from_weeks({i: [(1, SUSPECTED)] for i in range(60)})
    panel = load_target(write(tmp_path, frame), from_year=2020, to_year=2020)
    assert panel[EW].max().year == 2020
    assert panel.height < 60
