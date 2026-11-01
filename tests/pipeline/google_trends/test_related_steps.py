"""Google Trends related topics/queries step tests."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from src.pipeline.google_trends.related_steps import (
    RelatedSource,
    build_queries,
    build_topics,
)
from src.pipeline.google_trends.spec import (
    QUERY_GROUP_KEYS,
    QUERY_OUTPUT_COLUMNS,
    RELATED_TITLE,
    SOURCE,
    SOURCE_EXTRACT,
    SOURCE_SEED,
    STATE_ABBREV,
    TOPIC_OUTPUT_COLUMNS,
    VALUE,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "google_trends"

QUERY_HEADER = "topic_title,date,location,value,disease\n"


def _src(name: str) -> list[RelatedSource]:
    return [RelatedSource(FIXTURES / name)]


def _csv(path: Path, rows: list[str]) -> Path:
    path.write_text(QUERY_HEADER + "".join(rows), encoding="utf-8")
    return path


def test_build_topics_drops_empty_and_parses_schema() -> None:
    series = build_topics(
        _src("GoogleTrends_related_topic_sample.csv"),
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
        _src("GoogleTrends_related_topic_sample.csv"),
        drop_empty=False,
    ).collect()
    assert series.height == 4


def test_build_queries_and_value_domain() -> None:
    series = build_queries(
        _src("GoogleTrends_related_query_sample.csv"),
        keep_br=True,
        drop_empty=True,
    ).collect()
    assert tuple(series.columns) == QUERY_OUTPUT_COLUMNS
    assert series.height == 4  # one blank title dropped
    assert series[VALUE].max() <= 100
    assert set(series[STATE_ABBREV].unique().to_list()) == {"AC", "SP", "BR"}


def test_drop_br_related() -> None:
    series = build_queries(
        _src("GoogleTrends_related_query_sample.csv"),
        keep_br=False,
        drop_empty=True,
    ).collect()
    assert "BR" not in series[STATE_ABBREV].to_list()


def test_single_source_is_labelled_as_the_extract() -> None:
    series = build_queries(_src("GoogleTrends_related_query_sample.csv")).collect()
    assert set(series[SOURCE].unique().to_list()) == {SOURCE_EXTRACT}


def test_concat_keeps_one_row_per_key_and_the_seed_wins(tmp_path: Path) -> None:
    seed = _csv(
        tmp_path / "seed.csv",
        ["dengue,2021-01,SP,42,Dengue\n", "zika,2021-01,SP,7,Dengue\n"],
    )
    extract = _csv(
        tmp_path / "extract.csv",
        ["dengue,2021-01,SP,41,Dengue\n", "vacina,2026-06,SP,88,Dengue\n"],
    )
    series = build_queries(
        [RelatedSource(extract, SOURCE_EXTRACT), RelatedSource(seed, SOURCE_SEED)]
    ).collect()

    by_title = {
        title: (value, source)
        for title, value, source in series.select(RELATED_TITLE, VALUE, SOURCE).iter_rows()
    }
    # Overlapping key → the seed's 42 survives, not our 41.
    assert by_title["dengue"] == (42.0, SOURCE_SEED)
    assert by_title["zika"] == (7.0, SOURCE_SEED)
    assert by_title["vacina"] == (88.0, SOURCE_EXTRACT)
    assert series.height == 3
    assert series.select(QUERY_GROUP_KEYS).unique().height == series.height


def test_precedence_does_not_depend_on_source_order(tmp_path: Path) -> None:
    """The winner comes from SOURCE_PRECEDENCE, not from list position."""
    seed = _csv(tmp_path / "seed.csv", ["dengue,2021-01,SP,42,Dengue\n"])
    extract = _csv(tmp_path / "extract.csv", ["dengue,2021-01,SP,41,Dengue\n"])

    seed_first = build_queries(
        [RelatedSource(seed, SOURCE_SEED), RelatedSource(extract, SOURCE_EXTRACT)]
    ).collect()
    seed_last = build_queries(
        [RelatedSource(extract, SOURCE_EXTRACT), RelatedSource(seed, SOURCE_SEED)]
    ).collect()

    assert seed_first[VALUE].to_list() == [42.0]
    assert seed_last[VALUE].to_list() == [42.0]


def test_blank_seed_row_does_not_shadow_a_real_extract_row(tmp_path: Path) -> None:
    """Empty placeholders are dropped before dedup, so they never win a key."""
    seed = _csv(tmp_path / "seed.csv", [",2021-01,SP,,Dengue\n"])
    extract = _csv(tmp_path / "extract.csv", ["dengue,2021-01,SP,41,Dengue\n"])

    series = build_queries(
        [RelatedSource(extract, SOURCE_EXTRACT), RelatedSource(seed, SOURCE_SEED)]
    ).collect()

    assert series.height == 1
    assert series[RELATED_TITLE].to_list() == ["dengue"]
    assert series[SOURCE].to_list() == [SOURCE_EXTRACT]
