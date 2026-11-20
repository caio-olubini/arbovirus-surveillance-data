"""The target series, on a continuous weekly calendar.

Every baseline and every later model reads the target through this module, for
the same reason `pipeline.sinan.cases.weekly_cases` exists: protocol 00 fixes the
target as common ground, so it has to be one function rather than three that
happen to agree today.

The one thing this adds on top of `weekly_cases` is the **continuous calendar**,
and it is not a detail. A rolling-origin evaluation indexes the series by
position: the forecast for step *i* is compared against the value at *i*. If a
week is missing from the frame, every position after it shifts by one and the
seasonal baseline silently reads the wrong week — a lag of 52 lands 51 or 53
weeks back, and nothing raises. So the panel either is gapless or the function
refuses to return.
"""

from __future__ import annotations

import logging

import polars as pl

from ..pipeline.sinan.cases import weekly_cases
from ..pipeline.sinan.spec import EW_SYMPTOM_ONSET
from .spec import CASES, EW, FIRST_COMPLETE_YEAR

log = logging.getLogger("forecast")


class TargetGapError(ValueError):
    """The target series has a missing week where a complete one was promised."""


def load_target(
    cases_path: str,
    from_year: int | None = FIRST_COMPLETE_YEAR,
    to_year: int | None = None,
) -> pl.DataFrame:
    """Suspected dengue cases per epidemiological week, on a gapless calendar.

    `cases_path` is the case-level table written by `arboili transform sinan`,
    not the weekly series: the filter from notification to suspected case belongs
    to `weekly_cases` and is applied here rather than duplicated.

    The window starts in 2014 by default. 2013 exists in the file only as the
    symptom-onset tail of notifications filed in 2014, so it arrives with three
    weeks missing and a partial first year; `from_year=None` keeps it and will
    raise when the gap is found, which is the intended outcome rather than a
    bug to work around.
    """
    frame = pl.read_parquet(cases_path)
    weekly = weekly_cases(frame).rename({EW_SYMPTOM_ONSET: EW}).sort(EW)

    if from_year is not None:
        weekly = weekly.filter(pl.col(EW).dt.year() >= from_year)
    if to_year is not None:
        weekly = weekly.filter(pl.col(EW).dt.year() <= to_year)

    if weekly.height == 0:
        raise TargetGapError(
            f"No case weeks between {from_year} and {to_year} in {cases_path}."
        )

    first, last = weekly[EW].min(), weekly[EW].max()
    calendar = pl.DataFrame(
        {EW: pl.date_range(first, last, interval="1w", eager=True)}
    )
    panel = calendar.join(weekly, on=EW, how="left").sort(EW)

    missing = panel.filter(pl.col(CASES).is_null())
    if missing.height:
        weeks = ", ".join(str(w) for w in missing[EW].to_list()[:10])
        raise TargetGapError(
            f"{missing.height} week(s) missing from the target series between "
            f"{first} and {last}: {weeks}"
            + (" …" if missing.height > 10 else "")
            + ". A gap shifts every later position, so the seasonal lag would "
            "read the wrong week without raising. Narrow the window with "
            "`from_year` to a period that is complete."
        )

    log.info(
        "target: %d weeks, %s → %s, %d total cases",
        panel.height,
        first,
        last,
        panel[CASES].sum(),
    )
    return panel
