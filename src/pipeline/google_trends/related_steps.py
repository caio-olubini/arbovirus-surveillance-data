"""Monthly related topics/queries thin transform steps."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from .spec import (
    DISEASE,
    KEY_SYMPTOM,
    MONTH,
    NATIONAL_LOCATION,
    QUERY_GROUP_KEYS,
    QUERY_OUTPUT_COLUMNS,
    RELATED_TITLE,
    SOURCE,
    SOURCE_EXTRACT,
    SOURCE_PRECEDENCE,
    STATE_ABBREV,
    TOPIC_GROUP_KEYS,
    TOPIC_ID,
    TOPIC_OUTPUT_COLUMNS,
    VALUE,
)

# Sort key used only inside the dedup step; never reaches the output.
_RANK = "_rank"


@dataclass(frozen=True)
class RelatedSource:
    """One input CSV, plus the label written to the ``source`` column.

    The related tables are built from more than one CSV — the frozen Zenodo seed
    and this repo's own extractor output — so each input carries its own
    provenance. See ``spec.SOURCE_PRECEDENCE`` for which one wins on overlap.
    """

    path: Path
    source: str = SOURCE_EXTRACT


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


def _precedence_rank() -> pl.Expr:
    """Rank for the ``source`` column — lower wins. Unlisted labels rank last."""
    expr: pl.Expr = pl.lit(len(SOURCE_PRECEDENCE), dtype=pl.Int32)
    for rank, label in enumerate(SOURCE_PRECEDENCE):
        expr = (
            pl.when(pl.col(SOURCE) == label)
            .then(pl.lit(rank, dtype=pl.Int32))
            .otherwise(expr)
        )
    return expr


def _dedupe_by_precedence(frame: pl.LazyFrame, keys: tuple[str, ...]) -> pl.LazyFrame:
    """Keep one row per group key, preferring the source that ranks earlier.

    The seed and the extractor overlap on Dengue for the months the seed covers;
    both carry a value for those keys and the two clients disagree by a point or
    two. Resolving it here — rather than keeping both rows — is what keeps the
    output at one row per key, which the integrity checks assert.
    """
    return (
        frame.with_columns(_precedence_rank().alias(_RANK))
        .sort(_RANK, SOURCE)
        .unique(subset=list(keys), keep="first", maintain_order=True)
        .drop(_RANK)
    )


def order_topics(frame: pl.LazyFrame) -> pl.LazyFrame:
    return frame.select(TOPIC_OUTPUT_COLUMNS).sort(
        STATE_ABBREV, MONTH, DISEASE, RELATED_TITLE
    )


def order_queries(frame: pl.LazyFrame) -> pl.LazyFrame:
    return frame.select(QUERY_OUTPUT_COLUMNS).sort(
        STATE_ABBREV, MONTH, DISEASE, RELATED_TITLE
    )


def _prepare_topics(source: RelatedSource) -> pl.LazyFrame:
    frame = scan_related_topics(source.path)
    frame = rename_related_keys(frame)
    frame = frame.with_columns(
        pl.col(MONTH).cast(pl.String),
        pl.col(STATE_ABBREV).cast(pl.String),
        pl.col(DISEASE).cast(pl.String),
        pl.col(RELATED_TITLE).cast(pl.String),
        pl.col(TOPIC_ID).cast(pl.String),
        _parse_value("value"),
        pl.col(KEY_SYMPTOM).cast(pl.Boolean),
        pl.lit(source.source, dtype=pl.String).alias(SOURCE),
    )
    return frame


def _prepare_queries(source: RelatedSource) -> pl.LazyFrame:
    frame = scan_related_queries(source.path)
    frame = rename_related_keys(frame)
    frame = frame.with_columns(
        pl.col(MONTH).cast(pl.String),
        pl.col(STATE_ABBREV).cast(pl.String),
        pl.col(DISEASE).cast(pl.String),
        pl.col(RELATED_TITLE).cast(pl.String),
        _parse_value("value"),
        pl.lit(source.source, dtype=pl.String).alias(SOURCE),
    )
    return frame


def _concat(frames: Sequence[pl.LazyFrame]) -> pl.LazyFrame:
    if not frames:
        raise ValueError("at least one related source is required")
    return frames[0] if len(frames) == 1 else pl.concat(frames)


def build_topics(
    sources: Sequence[RelatedSource],
    keep_br: bool = True,
    drop_empty: bool = True,
) -> pl.LazyFrame:
    frame = _concat([_prepare_topics(s) for s in sources])
    # Empty placeholders are dropped *before* dedup, so a blank seed row can
    # never shadow a real row from the extractor on the same key.
    frame = drop_national(frame, keep_br=keep_br)
    frame = drop_empty_related(frame, drop=drop_empty)
    frame = _dedupe_by_precedence(frame, TOPIC_GROUP_KEYS)
    return order_topics(frame)


def build_queries(
    sources: Sequence[RelatedSource],
    keep_br: bool = True,
    drop_empty: bool = True,
) -> pl.LazyFrame:
    frame = _concat([_prepare_queries(s) for s in sources])
    frame = drop_national(frame, keep_br=keep_br)
    frame = drop_empty_related(frame, drop=drop_empty)
    frame = _dedupe_by_precedence(frame, QUERY_GROUP_KEYS)
    return order_queries(frame)
