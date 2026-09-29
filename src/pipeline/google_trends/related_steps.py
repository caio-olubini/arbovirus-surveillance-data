"""Monthly related topics/queries thin transform steps."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from .spec import (
    DISEASE,
    KEY_SYMPTOM,
    MONTH,
    NATIONAL_LOCATION,
    QUERY_OUTPUT_COLUMNS,
    RELATED_TITLE,
    STATE_ABBREV,
    TOPIC_ID,
    TOPIC_OUTPUT_COLUMNS,
    VALUE,
)


def _parse_value(column: str = "value") -> pl.Expr:
    """Coerce GT related value (may be string, ``<1``, or int) to Float64."""
    as_str = pl.col(column).cast(pl.String)
    cleaned = (
        pl.when(as_str == "<1")
        .then(pl.lit("0.1"))
        .otherwise(as_str)
    )
    return cleaned.cast(pl.Float64, strict=False).alias(VALUE)


def scan_related_topics(path: Path) -> pl.LazyFrame:
    return pl.scan_csv(
        path,
        schema_overrides={
            "topic_title": pl.String,
            "topic_id": pl.String,
            "date": pl.String,
            "location": pl.String,
            "value": pl.String,
            "disease": pl.String,
            "key_symptom": pl.Boolean,
        },
    )


def scan_related_queries(path: Path) -> pl.LazyFrame:
    return pl.scan_csv(
        path,
        schema_overrides={
            "topic_title": pl.String,
            "date": pl.String,
            "location": pl.String,
            "value": pl.String,
            "disease": pl.String,
        },
    )


def rename_related_keys(frame: pl.LazyFrame) -> pl.LazyFrame:
    """date → month, location → state_abbrev, topic_title → related_title."""
    return frame.rename(
        {
            "date": MONTH,
            "location": STATE_ABBREV,
            "topic_title": RELATED_TITLE,
        }
    )


def drop_national(frame: pl.LazyFrame, keep_br: bool) -> pl.LazyFrame:
    if keep_br:
        return frame
    return frame.filter(pl.col(STATE_ABBREV) != NATIONAL_LOCATION)


def drop_empty_related(frame: pl.LazyFrame, drop: bool) -> pl.LazyFrame:
    """Drop placeholder rows with null/blank related_title (common when GT returns nothing)."""
    if not drop:
        return frame
    return frame.filter(
        pl.col(RELATED_TITLE).is_not_null()
        & (pl.col(RELATED_TITLE).str.strip_chars() != "")
    )


def order_topics(frame: pl.LazyFrame) -> pl.LazyFrame:
    return frame.select(TOPIC_OUTPUT_COLUMNS).sort(
        STATE_ABBREV, MONTH, DISEASE, RELATED_TITLE
    )


def order_queries(frame: pl.LazyFrame) -> pl.LazyFrame:
    return frame.select(QUERY_OUTPUT_COLUMNS).sort(
        STATE_ABBREV, MONTH, DISEASE, RELATED_TITLE
    )


def build_topics(
    path: Path,
    keep_br: bool = True,
    drop_empty: bool = True,
) -> pl.LazyFrame:
    frame = scan_related_topics(path)
    frame = rename_related_keys(frame)
    frame = frame.with_columns(
        pl.col(MONTH).cast(pl.String),
        pl.col(STATE_ABBREV).cast(pl.String),
        pl.col(DISEASE).cast(pl.String),
        pl.col(RELATED_TITLE).cast(pl.String),
        pl.col(TOPIC_ID).cast(pl.String),
        _parse_value("value"),
        pl.col(KEY_SYMPTOM).cast(pl.Boolean),
    )
    frame = drop_national(frame, keep_br=keep_br)
    frame = drop_empty_related(frame, drop=drop_empty)
    return order_topics(frame)


def build_queries(
    path: Path,
    keep_br: bool = True,
    drop_empty: bool = True,
) -> pl.LazyFrame:
    frame = scan_related_queries(path)
    frame = rename_related_keys(frame)
    frame = frame.with_columns(
        pl.col(MONTH).cast(pl.String),
        pl.col(STATE_ABBREV).cast(pl.String),
        pl.col(DISEASE).cast(pl.String),
        pl.col(RELATED_TITLE).cast(pl.String),
        _parse_value("value"),
    )
    frame = drop_national(frame, keep_br=keep_br)
    frame = drop_empty_related(frame, drop=drop_empty)
    return order_queries(frame)
