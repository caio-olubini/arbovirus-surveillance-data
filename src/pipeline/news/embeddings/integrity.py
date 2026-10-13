"""Integrity checks over the dense-embedding tables (braço 02).

Structural invariants only, plus one numerical one: `check_finite`. Whether the
vectors *mean* anything is a modelling question, not something a check can assert
— but a NaN that reaches the forecaster does not fail loudly, it quietly
propagates, and that is the failure worth mechanising against.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from .spec import (
    ARTICLE_GROUP_KEYS,
    ARTICLE_OUTPUT_COLUMNS,
    DIM,
    EMBEDDING,
    EMB_MEAN,
    EMB_STD,
    EMBEDDING_DIM,
    EW,
    GROUP_KEYS,
    LOCATION,
    N_ARTICLES,
    N_TOKENS,
    NATIONAL_LOCATION,
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


def _check_schema(frame: pl.DataFrame, columns: tuple[str, ...], name: str) -> Check:
    actual = tuple(frame.columns)
    if actual == columns:
        return Check(f"{name}_schema", True, f"{len(actual)} columns in published order")
    return Check(f"{name}_schema", False, f"expected {columns}, got {actual}")


def check_article_schema(articles: pl.DataFrame) -> Check:
    return _check_schema(articles, ARTICLE_OUTPUT_COLUMNS, "article")


def check_pooled_schema(pooled: pl.DataFrame) -> Check:
    return _check_schema(pooled, OUTPUT_COLUMNS, "pooled")


def check_unique_keys(frame: pl.DataFrame, keys: tuple[str, ...], name: str) -> Check:
    duplicates = frame.height - frame.select(keys).unique().height
    if duplicates == 0:
        return Check(f"{name}_unique_keys", True, f"{frame.height:,} rows, all keys distinct")
    return Check(f"{name}_unique_keys", False, f"{duplicates:,} duplicate {keys} keys")


def check_weeks_start_on_sunday(frame: pl.DataFrame, name: str = "") -> Check:
    """Both tables carry `ew`, and they carry it independently — the article one
    from the corpus, the pooled one from the group-by — so both are checked, and
    the label says which is which."""
    label = f"{name}_" if name else ""
    bad = frame.filter(
        pl.col(EW).is_not_null() & (pl.col(EW).dt.weekday() != SUNDAY)
    ).height
    if bad == 0:
        return Check(f"{label}weeks_start_on_sunday", True, "all ew dates are Sundays")
    return Check(f"{label}weeks_start_on_sunday", False, f"{bad:,} non-Sunday ew values")


def check_locations_known(pooled: pl.DataFrame, fu_path: Path) -> Check:
    expected = set(pl.read_csv(fu_path)["ABBREVIATION"].to_list()) | {NATIONAL_LOCATION}
    unknown = set(pooled[LOCATION].unique().to_list()) - expected
    if unknown:
        return Check("locations_known", False, f"not in reference table: {sorted(unknown)}")
    return Check("locations_known", True, f"{pooled[LOCATION].n_unique()} known locations")


def check_dim_consistent(articles: pl.DataFrame, pooled: pl.DataFrame) -> Check:
    """Every embedding is the model's width, in both tables.

    The column is a fixed-width `Array` precisely so this can fail loudly: a
    ragged or truncated vector would otherwise reach the forecaster as a
    differently-shaped row that nothing downstream expects.
    """
    for frame, column, label in (
        (articles, EMBEDDING, "article"),
        (pooled, EMB_MEAN, "pooled"),
    ):
        if frame.height == 0:
            continue
        dtype = frame.schema[column]
        if dtype != pl.Array(pl.Float32, EMBEDDING_DIM):
            return Check(
                "dim_consistent", False, f"{label} {column} is {dtype}, expected 768-wide"
            )
    declared = set(articles[DIM].unique().to_list()) if articles.height else set()
    if declared - {EMBEDDING_DIM}:
        return Check("dim_consistent", False, f"dim column says {sorted(declared)}")
    return Check("dim_consistent", True, f"{EMBEDDING_DIM}-wide vectors throughout")


def check_finite(articles: pl.DataFrame, pooled: pl.DataFrame) -> Check:
    """No NaN or infinity anywhere — masked pooling can fail quietly."""
    for frame, column, label in (
        (articles, EMBEDDING, "article"),
        (pooled, EMB_MEAN, "pooled"),
    ):
        if frame.height == 0:
            continue
        bad = int((~np.isfinite(frame[column].to_numpy())).sum())
        if bad:
            return Check("finite", False, f"{bad:,} non-finite values in {label} {column}")
    if pooled.height and pooled.filter(
        ~pl.col(EMB_STD).is_finite() | (pl.col(EMB_STD) < 0)
    ).height:
        return Check("finite", False, "emb_std has non-finite or negative values")
    return Check("finite", True, "all vectors and dispersions are finite")


def check_article_counts(pooled: pl.DataFrame) -> Check:
    """A pooled row exists because an article landed in it, so n_articles >= 1.

    The same rule braço 01 applies to `news_volume`: zero here would mean the
    location spread produced a row out of nothing.
    """
    bad = pooled.filter(pl.col(N_ARTICLES) < 1).height
    if bad == 0:
        return Check("article_counts", True, "every row pools at least one article")
    return Check("article_counts", False, f"{bad:,} rows with n_articles < 1")


def check_national_row_per_week(pooled: pl.DataFrame) -> Check:
    """Every week must carry a BR row.

    Every article contributes to BR by construction, so a week present without a
    national row means the location spread dropped something.
    """
    if pooled.height == 0:
        return Check("national_row_per_week", True, "0 rows")
    weeks = set(pooled[EW].unique().to_list())
    national = set(pooled.filter(pl.col(LOCATION) == NATIONAL_LOCATION)[EW].to_list())
    missing = sorted(weeks - national)
    if missing:
        shown = ", ".join(str(day) for day in missing[:3])
        return Check(
            "national_row_per_week",
            False,
            f"{len(missing):,} weeks without a BR row (e.g. {shown})",
        )
    return Check("national_row_per_week", True, f"{len(weeks):,} weeks all carry BR")


def check_token_counts(articles: pl.DataFrame) -> Check:
    """A token count is positive; zero would mean the tokenizer saw nothing."""
    bad = articles.filter(pl.col(N_TOKENS) < 1).height
    if bad == 0:
        return Check("token_counts", True, "every article tokenized to >= 1 token")
    return Check("token_counts", False, f"{bad:,} articles with n_tokens < 1")


def run_all(
    articles: pl.DataFrame, pooled: pl.DataFrame, fu_path: Path
) -> list[Check]:
    return [
        check_article_schema(articles),
        check_pooled_schema(pooled),
        check_unique_keys(articles, ARTICLE_GROUP_KEYS, "article"),
        check_unique_keys(pooled, GROUP_KEYS, "pooled"),
        check_weeks_start_on_sunday(articles, "article"),
        check_weeks_start_on_sunday(pooled, "pooled"),
        check_locations_known(pooled, fu_path),
        check_dim_consistent(articles, pooled),
        check_finite(articles, pooled),
        check_article_counts(pooled),
        check_token_counts(articles),
        check_national_row_per_week(pooled),
    ]


__all__ = [
    "Check",
    "check_article_counts",
    "check_article_schema",
    "check_dim_consistent",
    "check_finite",
    "check_locations_known",
    "check_national_row_per_week",
    "check_pooled_schema",
    "check_token_counts",
    "check_unique_keys",
    "check_weeks_start_on_sunday",
    "run_all",
]
