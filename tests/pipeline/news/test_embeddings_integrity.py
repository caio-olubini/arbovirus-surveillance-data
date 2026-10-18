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
    check_variant_consistent,
    run_all,
)
from src.pipeline.news.embeddings.spec import (
    BASE_VARIANT_ID,
    EMB_MEAN,
    EMBEDDING,
    EMBEDDING_DIM,
    MODEL_NAME,
    MODEL_REVISION_SHA,
    N_TOKENS,
    NATIONAL_LOCATION,
    OUTPUT_COLUMNS,
    VARIANT,
)

SUNDAY = date(2011, 1, 9)
MONDAY = date(2011, 1, 10)
DIM = EMBEDDING_DIM


def _articles(rows: list[dict]) -> pl.DataFrame:
    base = {
        "article_id": "a",
        "ew": SUNDAY,
        "embedding": np.zeros(DIM, dtype=np.float32),
        "variant": BASE_VARIANT_ID,
        "model_id": MODEL_NAME,
        "model_revision": MODEL_REVISION_SHA,
        "dim": EMBEDDING_DIM,
        "n_tokens": 42,
    }
    return pl.DataFrame(
        [{**base, **row} for row in rows],
        schema={
            "article_id": pl.String,
            "ew": pl.Date,
            "embedding": pl.Array(pl.Float32, DIM),
            "variant": pl.String,
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
        "n_articles": 3,
    }
    return pl.DataFrame(
        [{**base, **row} for row in rows],
        schema={
            "ew": pl.Date,
            "location": pl.String,
            "emb_mean": pl.Array(pl.Float32, DIM),
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
            "n_articles": [1],
        },
        schema={
            "ew": pl.Date,
            "location": pl.String,
            "emb_mean": pl.Array(pl.Float32, 4),
            "n_articles": pl.Int64,
        },
    )
    assert not check_dim_consistent(_articles([{}]), wrong).passed


def test_a_wide_encoder_is_not_rejected_for_being_wide() -> None:
    """The bracket spans 768-wide and 1024-wide encoders.

    The expected width is read off the table rather than fixed at 768, so a
    BGE-M3 run must not fail the check that exists to catch raggedness.
    """
    wide = pl.DataFrame(
        {
            "article_id": ["a"],
            "ew": [SUNDAY],
            "embedding": [np.zeros(1024, dtype=np.float32)],
            "variant": ["bge-m3"],
            "model_id": ["BAAI/bge-m3"],
            "model_revision": ["0" * 40],
            "dim": [1024],
            "n_tokens": [10],
        },
        schema={
            "article_id": pl.String,
            "ew": pl.Date,
            "embedding": pl.Array(pl.Float32, 1024),
            "variant": pl.String,
            "model_id": pl.String,
            "model_revision": pl.String,
            "dim": pl.Int64,
            "n_tokens": pl.Int64,
        },
    )
    pooled = pl.DataFrame(
        {
            "ew": [SUNDAY],
            "location": [NATIONAL_LOCATION],
            "emb_mean": [np.zeros(1024, dtype=np.float32)],
            "n_articles": [1],
        },
        schema={
            "ew": pl.Date,
            "location": pl.String,
            "emb_mean": pl.Array(pl.Float32, 1024),
            "n_articles": pl.Int64,
        },
    )
    assert check_dim_consistent(wide, pooled).passed


def test_a_table_may_carry_only_one_variant() -> None:
    """Two configurations concatenated into one file would make every number read
    off it a blend of two encoders."""
    assert check_variant_consistent(_articles([{}])).passed
    mixed = check_variant_consistent(_articles([{}, {"variant": "e5-large"}]))
    assert not mixed.passed
    assert "e5-large" in mixed.detail


def test_an_unknown_variant_is_not_a_configuration() -> None:
    """The variant id is a key into `spec.VARIANTS`; an id that is not in there
    describes a run nobody wrote down, which is the thing the bracket exists to
    prevent."""
    unknown = check_variant_consistent(_articles([{"variant": "bertimbau-mean-x"}]))
    assert not unknown.passed
    assert "unknown variant" in unknown.detail


def test_the_declared_model_must_be_the_variants_model() -> None:
    """The provenance guard: a file named for one encoder must not hold another.

    This is the failure that survives every other check — the vectors are finite,
    the width is consistent, the keys are unique — and only the model column says
    the table is not what its name claims.
    """
    swapped = check_variant_consistent(_articles([{"model_id": "BAAI/bge-m3"}]))
    assert not swapped.passed
    assert MODEL_NAME in swapped.detail


def test_a_nan_vector_fails_the_finite_check() -> None:
    """Masked pooling can divide by a zero mask and emit NaN.

    Nothing downstream raises on that — it propagates into the forecaster
    quietly, which is exactly why it is checked here.
    """
    poisoned = np.zeros(DIM, dtype=np.float32)
    poisoned[3] = np.nan
    assert check_finite(_articles([{}]), _pooled([{}])).passed
    assert not check_finite(_articles([{"embedding": poisoned}]), _pooled([{}])).passed


def test_an_infinite_pooled_vector_fails() -> None:
    """The whitened variant is why this is load-bearing: it multiplies by the
    inverse square root of a near-singular covariance, and an unfloored
    eigenvalue there produces infinities that look like large numbers."""
    infinite = np.zeros(DIM, dtype=np.float32)
    infinite[0] = np.inf
    assert not check_finite(_articles([{}]), _pooled([{"emb_mean": infinite}])).passed


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
    assert EMB_MEAN in pooled.columns
    assert N_TOKENS in articles.columns
    assert VARIANT in articles.columns
