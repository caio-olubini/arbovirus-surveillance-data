"""Google Trends related topics/queries step tests."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from src.pipeline.google_trends.related_steps import build_queries, build_topics
from src.pipeline.google_trends.spec import (
    QUERY_OUTPUT_COLUMNS,
    RELATED_TITLE,
    STATE_ABBREV,
    TOPIC_OUTPUT_COLUMNS,
    VALUE,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "google_trends"


def test_build_topics_drops_empty_and_parses_schema() -> None:
    series = build_topics(
        FIXTURES / "GoogleTrends_related_topic_sample.csv",
        keep_br=True,
        drop_empty=True,
    ).collect()
    assert tuple(series.columns) == TOPIC_OUTPUT_COLUMNS
    # Sample has one blank-title SP row → dropped
    assert series.height == 3
    assert series.filter(pl.col(RELATED_TITLE).is_null()).is_empty()
    assert "BR" in series[STATE_ABBREV].to_list()


def test_build_topics_keep_empty() -> None:
    series = build_topics(
        FIXTURES / "GoogleTrends_related_topic_sample.csv",
        drop_empty=False,
    ).collect()
    assert series.height == 4


def test_build_queries_and_value_domain() -> None:
    series = build_queries(
        FIXTURES / "GoogleTrends_related_query_sample.csv",
        keep_br=True,
        drop_empty=True,
    ).collect()
    assert tuple(series.columns) == QUERY_OUTPUT_COLUMNS
    assert series.height == 4  # one blank title dropped
    assert series[VALUE].max() <= 100
    assert set(series[STATE_ABBREV].unique().to_list()) == {"AC", "SP", "BR"}


def test_drop_br_related() -> None:
    series = build_queries(
        FIXTURES / "GoogleTrends_related_query_sample.csv",
        keep_br=False,
        drop_empty=True,
    ).collect()
    assert "BR" not in series[STATE_ABBREV].to_list()
