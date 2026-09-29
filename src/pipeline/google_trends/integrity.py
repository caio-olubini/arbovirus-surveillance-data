"""Integrity checks over Google Trends search (EW) and related (monthly) series."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from .spec import (
    EW,
    GROUP_KEYS,
    MONTH,
    MONTH_PATTERN,
    NATIONAL_LOCATION,
    OUTPUT_COLUMNS,
    QUERY_GROUP_KEYS,
    QUERY_OUTPUT_COLUMNS,
    RELATED_TITLE,
    STATE_ABBREV,
    TOPIC_GROUP_KEYS,
    TOPIC_OUTPUT_COLUMNS,
    VALUE,
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
    return Check("unique_keys", False, f"{duplicates:,} duplicate group keys")


def check_weeks_start_on_sunday(series: pl.DataFrame) -> Check:
    bad = series.filter(
        pl.col(EW).is_not_null() & (pl.col(EW).dt.weekday() != SUNDAY)
    ).height
    if bad == 0:
        return Check("weeks_start_on_sunday", True, "all ew dates are Sundays")
    return Check("weeks_start_on_sunday", False, f"{bad:,} non-Sunday ew values")


def check_states(
    series: pl.DataFrame,
    fu_path: Path,
    keep_br: bool = True,
    require_complete: bool = True,
) -> Check:
    expected = set(pl.read_csv(fu_path)["ABBREVIATION"].to_list())
    if keep_br:
        expected = expected | {NATIONAL_LOCATION}
    actual = set(series[STATE_ABBREV].unique().to_list())
    unknown = actual - expected
    if unknown:
        return Check("states", False, f"not in reference table: {sorted(unknown)}")
    required = expected - {NATIONAL_LOCATION}
    missing = required - actual
    if require_complete and missing:
        return Check("states", False, f"never appear in the series: {sorted(missing)}")
    if missing:
        return Check(
            "states",
            True,
            f"{len(actual)} known locations (incomplete extract; missing {len(missing)} UFs)",
        )
    return Check("states", True, f"{len(actual)} locations present")


def check_value_domain(series: pl.DataFrame) -> Check:
    """Google Trends index is typically 0–100; allow nulls, flag extremes."""
    bad = series.filter(
        pl.col(VALUE).is_not_null() & ((pl.col(VALUE) < 0) | (pl.col(VALUE) > 100))
    ).height
    if bad == 0:
        return Check("value_domain", True, "value in [0, 100] or null")
    return Check("value_domain", False, f"{bad:,} rows outside [0, 100]")


def run_all(
    series: pl.DataFrame, fu_path: Path, keep_br: bool = True
) -> list[Check]:
    return [
        check_schema(series),
        check_unique_keys(series),
        check_weeks_start_on_sunday(series),
        check_states(series, fu_path, keep_br=keep_br, require_complete=True),
        check_value_domain(series),
    ]


def check_related_schema(series: pl.DataFrame, kind: str) -> Check:
    expected = TOPIC_OUTPUT_COLUMNS if kind == "topics" else QUERY_OUTPUT_COLUMNS
    actual = tuple(series.columns)
    if actual == expected:
        return Check("schema", True, f"{len(actual)} columns in published order ({kind})")
    return Check("schema", False, f"expected {expected}, got {actual}")


def check_related_unique_keys(series: pl.DataFrame, kind: str) -> Check:
    keys = TOPIC_GROUP_KEYS if kind == "topics" else QUERY_GROUP_KEYS
    if series.height == 0:
        return Check("unique_keys", True, "0 rows (empty after drop_empty is allowed)")
    duplicates = series.height - series.select(keys).unique().height
    if duplicates == 0:
        return Check("unique_keys", True, f"{series.height:,} rows, all keys distinct")
    return Check("unique_keys", False, f"{duplicates:,} duplicate group keys")


def check_month_format(series: pl.DataFrame) -> Check:
    if series.height == 0:
        return Check("month_format", True, "0 rows")
    bad = series.filter(
        pl.col(MONTH).is_null() | ~pl.col(MONTH).str.contains(MONTH_PATTERN)
    ).height
    if bad == 0:
        return Check("month_format", True, "all months match YYYY-MM")
    return Check("month_format", False, f"{bad:,} rows with invalid month")


def check_related_titles_present(series: pl.DataFrame) -> Check:
    """After drop_empty, related_title should be non-null; empty table is OK for partial runs."""
    if series.height == 0:
        return Check("related_titles", True, "0 rows (partial / empty extract)")
    bad = series.filter(
        pl.col(RELATED_TITLE).is_null() | (pl.col(RELATED_TITLE).str.strip_chars() == "")
    ).height
    if bad == 0:
        return Check("related_titles", True, f"{series.height:,} non-empty related titles")
    return Check("related_titles", False, f"{bad:,} blank related_title rows")


def run_all_related(
    series: pl.DataFrame,
    fu_path: Path,
    kind: str,
    keep_br: bool = True,
    require_complete_ufs: bool = False,
) -> list[Check]:
    """Integrity for monthly related tables. Full UF coverage off by default (extract incomplete)."""
    if kind not in {"topics", "queries"}:
        raise ValueError(f"kind must be 'topics' or 'queries', got {kind!r}")
    return [
        check_related_schema(series, kind),
        check_related_unique_keys(series, kind),
        check_month_format(series),
        check_states(
            series, fu_path, keep_br=keep_br, require_complete=require_complete_ufs
        ),
        check_value_domain(series),
        check_related_titles_present(series),
    ]
