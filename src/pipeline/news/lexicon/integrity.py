"""Integrity checks over the lexicon feature table (braço 01).

Structural invariants only. Whether the features *mean* anything is the
annotation study in notes/01, not something a check can assert.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from .spec import (
    EW,
    GROUP_KEYS,
    LOCATION,
    NATIONAL_LOCATION,
    NEWS_ARTICLES_WITH_CASES,
    NEWS_CASES,
    NEWS_DEATHS,
    NEWS_SEVERITY,
    NEWS_VOLUME,
    OUTPUT_COLUMNS,
)

SUNDAY = 7


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
    return Check("unique_keys", False, f"{duplicates:,} duplicate (ew, location) keys")


def check_weeks_start_on_sunday(series: pl.DataFrame) -> Check:
    bad = series.filter(
        pl.col(EW).is_not_null() & (pl.col(EW).dt.weekday() != SUNDAY)
    ).height
    if bad == 0:
        return Check("weeks_start_on_sunday", True, "all ew dates are Sundays")
    return Check("weeks_start_on_sunday", False, f"{bad:,} non-Sunday ew values")


def check_locations_known(series: pl.DataFrame, fu_path: Path) -> Check:
    expected = set(pl.read_csv(fu_path)["ABBREVIATION"].to_list()) | {NATIONAL_LOCATION}
    unknown = set(series[LOCATION].unique().to_list()) - expected
    if unknown:
        return Check("locations_known", False, f"not in reference table: {sorted(unknown)}")
    return Check("locations_known", True, f"{series[LOCATION].n_unique()} known locations")


def check_non_negative(series: pl.DataFrame) -> Check:
    """Volume is a count of articles, so it starts at 1: a row exists only
    because something was written to it."""
    bad = series.filter(
        (pl.col(NEWS_VOLUME) < 1)
        | (pl.col(NEWS_SEVERITY) < 0)
        | (pl.col(NEWS_ARTICLES_WITH_CASES) < 0)
    ).height
    if bad == 0:
        return Check("non_negative", True, "volume >= 1 and derived counts >= 0")
    return Check("non_negative", False, f"{bad:,} rows with an out-of-range count")


def check_cases_domain(series: pl.DataFrame) -> Check:
    """A stated count is null or a positive number; 0 would mean the regex
    matched a number the parser then rejected silently."""
    for column in (NEWS_CASES, NEWS_DEATHS):
        bad = series.filter(
            pl.col(column).is_not_null() & (pl.col(column) < 1)
        ).height
        if bad:
            return Check("cases_domain", False, f"{bad:,} non-positive {column} values")
    return Check("cases_domain", True, "counts are null or positive")


def check_articles_with_cases(series: pl.DataFrame) -> Check:
    """At most one count per article, so contributors cannot exceed volume."""
    bad = series.filter(
        pl.col(NEWS_ARTICLES_WITH_CASES) > pl.col(NEWS_VOLUME)
    ).height
    if bad == 0:
        return Check(
            "articles_with_cases",
            True,
            "contributors never exceed article volume",
        )
    return Check(
        "articles_with_cases",
        False,
        f"{bad:,} rows where contributors > news_volume",
    )


def check_national_row_per_week(series: pl.DataFrame) -> Check:
    """Every week must carry a BR row.

    Every article contributes to BR by construction, so a week present without a
    national row means the location spread dropped something.
    """
    if series.height == 0:
        return Check("national_row_per_week", True, "0 rows")
    weeks = set(series[EW].unique().to_list())
    national = set(series.filter(pl.col(LOCATION) == NATIONAL_LOCATION)[EW].to_list())
    missing = sorted(weeks - national)
    if missing:
        shown = ", ".join(str(day) for day in missing[:3])
        return Check(
            "national_row_per_week",
            False,
            f"{len(missing):,} weeks without a BR row (e.g. {shown})",
        )
    return Check("national_row_per_week", True, f"{len(weeks):,} weeks all carry BR")


def run_all(series: pl.DataFrame, fu_path: Path) -> list[Check]:
    return [
        check_schema(series),
        check_unique_keys(series),
        check_weeks_start_on_sunday(series),
        check_locations_known(series, fu_path),
        check_non_negative(series),
        check_cases_domain(series),
        check_articles_with_cases(series),
        check_national_row_per_week(series),
    ]
