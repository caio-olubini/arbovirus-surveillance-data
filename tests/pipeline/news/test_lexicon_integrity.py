"""Braço 01's integrity checks: the fixture features pass, and each guard fires."""

from __future__ import annotations

from datetime import date

import polars as pl

from src.pipeline.news.lexicon.integrity import (
    check_articles_with_cases,
    check_cases_domain,
    check_locations_known,
    check_national_row_per_week,
    check_non_negative,
    check_unique_keys,
    run_all,
)
from src.pipeline.news.lexicon.spec import NATIONAL_LOCATION, OUTPUT_COLUMNS


def _features(rows: list[dict]) -> pl.DataFrame:
    schema = {
        "ew": pl.Date,
        "location": pl.String,
        "news_volume": pl.Int64,
        "news_severity": pl.Int64,
        "news_cases": pl.Int64,
        "news_deaths": pl.Int64,
        "news_articles_with_cases": pl.Int64,
    }
    return pl.DataFrame(rows, schema=schema).select(OUTPUT_COLUMNS)


def _row(**overrides) -> dict:
    row = {
        "ew": date(2011, 1, 9),
        "location": NATIONAL_LOCATION,
        "news_volume": 3,
        "news_severity": 6,
        "news_cases": 1_200,
        "news_deaths": None,
        "news_articles_with_cases": 1,
    }
    row.update(overrides)
    return row


def test_all_checks_pass_on_the_fixture_features(
    news_features: pl.DataFrame, fu_path
) -> None:
    checks = run_all(news_features, fu_path)
    failed = [c for c in checks if not c.passed]
    assert not failed, "; ".join(str(c) for c in failed)


def test_unique_keys_counts_duplicates() -> None:
    frame = _features([_row(), _row()])
    assert not check_unique_keys(frame).passed


def test_locations_must_be_br_or_a_known_uf(fu_path) -> None:
    assert check_locations_known(_features([_row()]), fu_path).passed
    assert check_locations_known(_features([_row(location="RJ")]), fu_path).passed
    unknown = check_locations_known(_features([_row(location="XX")]), fu_path)
    assert not unknown.passed
    assert "XX" in unknown.detail


def test_volume_is_never_zero() -> None:
    """A row exists because an article was counted; zero means the spread broke."""
    assert check_non_negative(_features([_row()])).passed
    assert not check_non_negative(_features([_row(news_volume=0)])).passed


def test_counts_are_null_or_positive() -> None:
    assert check_cases_domain(_features([_row(news_cases=None)])).passed
    assert check_cases_domain(_features([_row(news_cases=1)])).passed
    assert not check_cases_domain(_features([_row(news_cases=0)])).passed


def test_contributors_never_exceed_volume() -> None:
    """At most one case count per article, so this cannot exceed `news_volume`."""
    frame = _features([_row(news_volume=1, news_articles_with_cases=2)])
    assert not check_articles_with_cases(frame).passed


def test_every_week_must_carry_a_br_row() -> None:
    """Every article contributes to BR by construction.

    So a week without a BR row means the location spread dropped something —
    it cannot mean "no national coverage".
    """
    only_uf = _features([_row(location="RJ")])
    check = check_national_row_per_week(only_uf)
    assert not check.passed
    assert "1 weeks without a BR row" in check.detail

    with_br = _features([_row(location="RJ"), _row()])
    assert check_national_row_per_week(with_br).passed


def test_br_row_per_week_passes_on_the_fixture_features(news_features: pl.DataFrame) -> None:
    assert check_national_row_per_week(news_features).passed
