"""Thin Google Trends search transform steps."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from ..epiweek import floor_to_sunday
from .spec import (
    EW,
    NATIONAL_LOCATION,
    OUTPUT_COLUMNS,
    STATE_ABBREV,
    TOPIC,
    VALUE,
)


def scan_search(path: Path) -> pl.LazyFrame:
    """Open the extractor CSV (date, location, topic, value)."""
    return pl.scan_csv(
        path,
        schema_overrides={
            "date": pl.String,
            "location": pl.String,
            "topic": pl.String,
            "value": pl.Float64,
        },
    )


def rename_keys(frame: pl.LazyFrame) -> pl.LazyFrame:
    """date → ew, location → state_abbrev (names only; Sunday floor is separate)."""
    return frame.rename({"date": EW, "location": STATE_ABBREV})


def parse_ew(frame: pl.LazyFrame) -> pl.LazyFrame:
    return frame.with_columns(
        pl.col(EW).str.to_date("%Y-%m-%d", strict=False)
    )


def floor_ew(frame: pl.LazyFrame) -> pl.LazyFrame:
    """Ensure ew is the Sunday start; already-Sunday dates are unchanged."""
    return frame.with_columns(floor_to_sunday(EW).alias(EW))


def drop_national(frame: pl.LazyFrame, keep_br: bool) -> pl.LazyFrame:
    if keep_br:
        return frame
    return frame.filter(pl.col(STATE_ABBREV) != NATIONAL_LOCATION)


def order_columns(frame: pl.LazyFrame) -> pl.LazyFrame:
    return frame.select(OUTPUT_COLUMNS).sort(STATE_ABBREV, EW, TOPIC)


def build(
    path: Path,
    keep_br: bool = True,
) -> pl.LazyFrame:
    frame = scan_search(path)
    frame = rename_keys(frame)
    frame = parse_ew(frame)
    frame = floor_ew(frame)
    frame = drop_national(frame, keep_br=keep_br)
    return order_columns(frame)
