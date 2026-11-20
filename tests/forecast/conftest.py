"""Builders shared by the forecast tests.

Both are factories rather than fixed frames: the point of most of these tests is
what happens at a specific shape (a gap, a horizon longer than the tail), and a
fixed fixture would have to be re-derived per test anyway.
"""

from __future__ import annotations

import datetime as dt

import polars as pl
import pytest

from src.forecast.spec import CASES, EW
from src.pipeline.sinan.spec import CASE_COUNT, EW_SYMPTOM_ONSET, FINAL_CLASSIFICATION

# A Sunday, so the weeks land on the same weekday the panel uses.
START = dt.date(2020, 1, 5)
SUSPECTED = 1  # any CLASSI_FIN other than 5
DISCARDED = 5


@pytest.fixture
def panel_from_values():
    """A target panel: one row per week, exactly the columns `load_target` returns."""

    def _make(values: list[float], start: dt.date = START) -> pl.DataFrame:
        return pl.DataFrame(
            {
                EW: pl.date_range(
                    start,
                    start + dt.timedelta(weeks=len(values) - 1),
                    interval="1w",
                    eager=True,
                ),
                CASES: [float(v) for v in values],
            }
        )

    return _make


@pytest.fixture
def cases_from_weeks():
    """A case-level frame: the input `weekly_cases` expects, one row per case.

    `weeks` maps a week offset from START to (cases, classification) pairs, so a
    test can add two rows to the same week or leave a week out entirely — which
    is the only way to exercise the gap guard.
    """

    def _make(weeks: dict[int, list[tuple[int, int]]]) -> pl.DataFrame:
        dates, counts, classes = [], [], []
        for offset, rows in weeks.items():
            for count, classification in rows:
                dates.append(START + dt.timedelta(weeks=offset))
                counts.append(count)
                classes.append(classification)
        return pl.DataFrame(
            {
                EW_SYMPTOM_ONSET: dates,
                CASE_COUNT: counts,
                FINAL_CLASSIFICATION: classes,
            }
        )

    return _make
