"""Braço 02's integrity checks: the fixture tables pass, and each guard fires.

Every check is exercised in both directions, because a check that only ever
passes is indistinguishable from no check at all.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import polars as pl

from src.pipeline.news.embeddings.integrity import (
    check_article_counts,
    check_dim_consistent,
    check_finite,
    check_locations_known,
    check_national_row_per_week,
    check_token_counts,
    check_unique_keys,
    run_all,
)
from src.pipeline.news.embeddings.spec import (
    EMB_MEAN,
    EMBEDDING,
    EMBEDDING_DIM,
    N_TOKENS,
    NATIONAL_LOCATION,
    OUTPUT_COLUMNS,
)

SUNDAY = date(2011, 1, 9)
MONDAY = date(2011, 1, 10)
DIM = EMBEDDING_DIM


def _articles(rows: list[dict]) -> pl.DataFrame:
    base = {
        "article_id": "a",
        "ew": SUNDAY,
        "embedding": np.zeros(DIM, dtype=np.float32),
        "model_id": "test/fake-encoder",
        "model_revision": "0" * 40,
        "dim": EMBEDDING_DIM,
        "n_tokens": 42,
    }
    return pl.DataFrame(
        [{**base, **row} for row in rows],
        schema={
            "article_id": pl.String,
            "ew": pl.Date,
            "embedding": pl.Array(pl.Float32, DIM),
            "model_id": pl.String,
            "model_revision": pl.String,
            "dim": pl.Int64,
            "n_tokens": pl.Int64,
        },
    )


def _pooled(rows: list[dict]) -> pl.DataFrame:
    base = {
        "ew": SUNDAY,
        "location": NATIONAL_LOCATION,
        "emb_mean": np.zeros(DIM, dtype=np.float32),
        "emb_std": 0.5,
        "n_articles": 3,
    }
    return pl.DataFrame(
        [{**base, **row} for row in rows],
        schema={
            "ew": pl.Date,
            "location": pl.String,
            "emb_mean": pl.Array(pl.Float32, DIM),
            "emb_std": pl.Float32,
            "n_articles": pl.Int64,
        },
    ).select(OUTPUT_COLUMNS)


def test_all_checks_pass_on_the_fixture_tables(news_embedding_tables, fu_path) -> None:
    articles, pooled = news_embedding_tables
    checks = run_all(articles, pooled, fu_path)
    failed = [c for c in checks if not c.passed]
    assert not failed, "; ".join(str(c) for c in failed)


def test_unique_keys_counts_duplicates() -> None:
    assert not check_unique_keys(_articles([{}, {}]), ("article_id",), "article").passed
    # Same article twice in different weeks is still one article, but not a
    # duplicated key — which is why the key is (article_id,) and not (article_id, ew).
    assert check_unique_keys(
        _articles([{}, {"ew": MONDAY}]), ("article_id", "ew"), "article"
    ).passed


def test_locations_must_be_br_or_a_known_uf(fu_path) -> None:
    assert check_locations_known(_pooled([{}]), fu_path).passed
    assert check_locations_known(_pooled([{"location": "RJ"}]), fu_path).passed
    unknown = check_locations_known(_pooled([{"location": "XX"}]), fu_path)
    assert not unknown.passed
    assert "XX" in unknown.detail


def test_dim_must_match_the_model_width() -> None:
    articles = _articles([{}])
    pooled = _pooled([{}])
    assert check_dim_consistent(articles, pooled).passed
    assert not check_dim_consistent(
        _articles([{"dim": 1024}]), pooled
    ).passed


def test_dim_must_match_the_pooled_table_too() -> None:
    """The pooled vector is a mean of article vectors; a different width there
    means one of the two tables was produced by a different model."""
    wrong = pl.DataFrame(
        {
            "ew": [SUNDAY],
            "location": [NATIONAL_LOCATION],
            "emb_mean": [np.zeros(4, dtype=np.float32)],
            "emb_std": [0.0],
            "n_articles": [1],
        },
        schema={
            "ew": pl.Date,
            "location": pl.String,
            "emb_mean": pl.Array(pl.Float32, 4),
            "emb_std": pl.Float32,
            "n_articles": pl.Int64,
        },
    )
    assert not check_dim_consistent(_articles([{}]), wrong).passed


def test_a_nan_vector_fails_the_finite_check() -> None:
    """Masked pooling can divide by a zero mask and emit NaN.

    Nothing downstream raises on that — it propagates into the forecaster
    quietly, which is exactly why it is checked here.
    """
    poisoned = np.zeros(DIM, dtype=np.float32)
    poisoned[3] = np.nan
    assert check_finite(_articles([{}]), _pooled([{}])).passed
    assert not check_finite(_articles([{"embedding": poisoned}]), _pooled([{}])).passed


def test_a_negative_dispersion_fails() -> None:
    assert not check_finite(_articles([{}]), _pooled([{"emb_std": -0.1}])).passed


def test_a_pooled_row_must_pool_at_least_one_article() -> None:
    """Zero would mean the location spread produced a row out of nothing."""
    assert check_article_counts(_pooled([{}])).passed
    assert not check_article_counts(_pooled([{"n_articles": 0}])).passed


def test_token_counts_must_be_positive() -> None:
    assert check_token_counts(_articles([{}])).passed
    assert not check_token_counts(_articles([{"n_tokens": 0}])).passed


def test_every_week_must_carry_a_br_row() -> None:
    only_uf = _pooled([{"location": "RJ"}])
    check = check_national_row_per_week(only_uf)
    assert not check.passed
    assert "1 weeks without a BR row" in check.detail

    with_br = _pooled([{"location": "RJ"}, {}])
    assert check_national_row_per_week(with_br).passed


def test_a_non_sunday_week_fails() -> None:
    from src.pipeline.news.embeddings.integrity import check_weeks_start_on_sunday

    assert check_weeks_start_on_sunday(_pooled([{}])).passed
    assert not check_weeks_start_on_sunday(_pooled([{"ew": MONDAY}])).passed


def test_the_published_columns_are_in_order(news_embedding_tables) -> None:
    articles, pooled = news_embedding_tables
    assert tuple(pooled.columns) == OUTPUT_COLUMNS
    assert EMB_MEAN in articles.columns or EMBEDDING in articles.columns
    assert N_TOKENS in articles.columns
