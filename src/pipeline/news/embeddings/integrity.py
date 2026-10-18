"""Integrity checks over the dense-embedding tables (braço 02).

Structural invariants only, plus one numerical one: `check_finite`. Whether the
vectors *mean* anything is a modelling question, not something a check can assert
— but a NaN that reaches the forecaster does not fail loudly, it quietly
propagates, and that is the failure worth mechanising against.

The checks are variant-agnostic: they assert that whatever configuration produced
a table produced it consistently, not that the configuration was the right one.
That matters more now than it did when the braço had a single encoder, because the
bracket means a table can be self-consistent and still be the wrong width for the
file it is in.
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
    EW,
    GROUP_KEYS,
    LOCATION,
    MODEL_ID,
    N_ARTICLES,
    N_TOKENS,
    NATIONAL_LOCATION,
    OUTPUT_COLUMNS,
    VARIANT,
    VARIANTS,
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
    """Every embedding is as wide as its own `dim` column says, in both tables.

    The column is a fixed-width `Array` precisely so this can fail loudly: a
    ragged or truncated vector would otherwise reach the forecaster as a
    differently-shaped row that nothing downstream expects.

    The expected width is read from the table rather than fixed at 768, because
    the bracket spans 768-wide and 1024-wide encoders and a hardcoded width would
    silently reject half of it.
    """
    if articles.height == 0 and pooled.height == 0:
        return Check("dim_consistent", True, "empty tables")

    if articles.height:
        declared = set(articles[DIM].unique().to_list())
        if len(declared) != 1:
            return Check("dim_consistent", False, f"article table declares several widths: {sorted(declared)}")
        width = declared.pop()
        if articles.schema[EMBEDDING] != pl.Array(pl.Float32, width):
            return Check(
                "dim_consistent",
                False,
                f"article {EMBEDDING} is {articles.schema[EMBEDDING]}, declared {width}",
            )
    else:
        width = pooled.schema[EMB_MEAN].size

    if pooled.height and pooled.schema[EMB_MEAN] != pl.Array(pl.Float32, width):
        return Check(
            "dim_consistent",
            False,
            f"pooled {EMB_MEAN} is {pooled.schema[EMB_MEAN]}, article width is {width}",
        )
    return Check("dim_consistent", True, f"{width}-wide vectors throughout")


def check_variant_consistent(articles: pl.DataFrame) -> Check:
    """One table, one configuration.

    The braço now publishes a table per variant. A table carrying two variant ids
    would mean two configurations were concatenated, and every number read off it
    afterwards would be a blend of two encoders.
    """
    if articles.height == 0:
        return Check("variant_consistent", True, "0 rows")
    seen = set(articles[VARIANT].unique().to_list())
    if len(seen) != 1:
        return Check("variant_consistent", False, f"several variants in one table: {sorted(seen)}")
    name = seen.pop()
    if name not in VARIANTS:
        return Check("variant_consistent", False, f"unknown variant {name!r}")
    declared = set(articles[MODEL_ID].unique().to_list())
    expected = {VARIANTS[name].model_name}
    if declared != expected:
        return Check(
            "variant_consistent",
            False,
            f"variant {name!r} should carry {expected}, table carries {sorted(declared)}",
        )
    return Check("variant_consistent", True, f"{name} · {sorted(declared)[0]}")


def check_finite(articles: pl.DataFrame, pooled: pl.DataFrame) -> Check:
    """No NaN or infinity anywhere — masked pooling can fail quietly.

    The whitened variant makes this check load-bearing rather than ceremonial: it
    multiplies by the inverse square root of a near-singular covariance, and an
    unfloored eigenvalue there produces infinities that look like large numbers.
    """
    for frame, column, label in (
        (articles, EMBEDDING, "article"),
        (pooled, EMB_MEAN, "pooled"),
    ):
        if frame.height == 0:
            continue
        bad = int((~np.isfinite(frame[column].to_numpy())).sum())
        if bad:
            return Check("finite", False, f"{bad:,} non-finite values in {label} {column}")
    return Check("finite", True, "all vectors are finite")


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
        check_variant_consistent(articles),
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
    "check_variant_consistent",
    "check_weeks_start_on_sunday",
    "run_all",
]
