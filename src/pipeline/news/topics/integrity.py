"""Integrity checks over the topic tables (braço 03).

Structural invariants, plus one numerical one that is specific to this braço:
`check_shares_sum_to_one`. A topic mixture is a point on the simplex, so the
shares of a (week, location) must add to 1 — if they do not, the pooling is wrong
and the "share" column is not a share. That is the check a reader would want to
run before trusting a topic covariate, and it is cheap enough to mechanise.

Every check is exercised in both directions in
`tests/pipeline/news/test_topics_integrity.py`, because a check that only ever
passes is indistinguishable from no check at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from .spec import (
    COHERENCE,
    EW,
    GROUP_KEYS,
    LL_PER_WORD,
    LOCATION,
    META_GROUP_KEYS,
    META_OUTPUT_COLUMNS,
    MODEL_ID,
    N_ARTICLES,
    NATIONAL_LOCATION,
    OUTPUT_COLUMNS,
    SELECTED,
    SHARE,
    SWEEP_OUTPUT_COLUMNS,
    TOPIC_ID,
)

SUNDAY = 7

# Float32 shares summed over k topics drift by ~1e-6, so the bound has to admit
# that. It is still tight enough that a genuine pooling error — a topic counted
# twice, a week's rows written from two different models — lands far outside it.
SHARE_TOLERANCE = 1e-3


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


def check_share_schema(pooled: pl.DataFrame) -> Check:
    return _check_schema(pooled, OUTPUT_COLUMNS, "share")


def check_meta_schema(meta: pl.DataFrame) -> Check:
    return _check_schema(meta, META_OUTPUT_COLUMNS, "meta")


def check_sweep_schema(candidates: pl.DataFrame) -> Check:
    return _check_schema(candidates, SWEEP_OUTPUT_COLUMNS, "sweep")


def check_unique_keys(frame: pl.DataFrame, keys: tuple[str, ...], name: str) -> Check:
    duplicates = frame.height - frame.select(keys).unique().height
    if duplicates == 0:
        return Check(f"{name}_unique_keys", True, f"{frame.height:,} rows, all keys distinct")
    return Check(f"{name}_unique_keys", False, f"{duplicates:,} duplicate {keys} keys")


def check_weeks_start_on_sunday(pooled: pl.DataFrame) -> Check:
    bad = pooled.filter(
        pl.col(EW).is_not_null() & (pl.col(EW).dt.weekday() != SUNDAY)
    ).height
    if bad == 0:
        return Check("weeks_start_on_sunday", True, "all ew dates are Sundays")
    return Check("weeks_start_on_sunday", False, f"{bad:,} non-Sunday ew values")


def check_locations_known(pooled: pl.DataFrame, fu_path: Path) -> Check:
    expected = set(pl.read_csv(fu_path)["ABBREVIATION"].to_list()) | {NATIONAL_LOCATION}
    unknown = set(pooled[LOCATION].unique().to_list()) - expected
    if unknown:
        return Check("locations_known", False, f"not in reference table: {sorted(unknown)}")
    return Check("locations_known", True, f"{pooled[LOCATION].n_unique()} known locations")


def check_shares_sum_to_one(
    pooled: pl.DataFrame, tolerance: float = SHARE_TOLERANCE
) -> Check:
    """A topic mixture is a distribution, so a week's shares must add to 1.

    This is the check that catches a pooling error the schema checks cannot see:
    a topic emitted twice, a week's rows drawn from two different models, or a
    mean taken over the wrong axis. All of those leave a table that looks
    well-formed and is not a set of shares.
    """
    if pooled.height == 0:
        return Check("shares_sum_to_one", True, "0 rows")
    totals = pooled.group_by(EW, LOCATION).agg(pl.col(SHARE).sum().alias("total"))
    bad = totals.filter((pl.col("total") - 1.0).abs() > tolerance)
    if bad.height == 0:
        worst = float((totals["total"] - 1.0).abs().max() or 0.0)
        return Check(
            "shares_sum_to_one",
            True,
            f"{totals.height:,} (ew, location) groups, max deviation {worst:.2e}",
        )
    example = bad.sort((pl.col("total") - 1.0).abs(), descending=True).row(0, named=True)
    return Check(
        "shares_sum_to_one",
        False,
        f"{bad.height:,} groups off by more than {tolerance:g} "
        f"(worst {example[EW]} {example[LOCATION]} = {example['total']:.4f})",
    )


def check_shares_in_unit_interval(pooled: pl.DataFrame) -> Check:
    bad = pooled.filter((pl.col(SHARE) < 0) | (pl.col(SHARE) > 1)).height
    if bad == 0:
        return Check("shares_in_unit_interval", True, "every share is in [0, 1]")
    return Check("shares_in_unit_interval", False, f"{bad:,} shares outside [0, 1]")


def check_finite(pooled: pl.DataFrame, meta: pl.DataFrame) -> Check:
    """No NaN or infinity anywhere.

    A zero-token document is assigned a uniform row rather than NaN, so a non-finite
    share means something upstream divided by zero — and nothing downstream raises
    on that, it propagates into the forecaster quietly.
    """
    for frame, column, label in ((pooled, SHARE, "share"), (meta, "weight", "meta weight")):
        if frame.height == 0:
            continue
        bad = frame.filter(~pl.col(column).is_finite()).height
        if bad:
            return Check("finite", False, f"{bad:,} non-finite values in {label}")
    return Check("finite", True, "all shares and weights are finite")


def check_article_counts(pooled: pl.DataFrame) -> Check:
    """A pooled row exists because an article landed in it, so n_articles >= 1."""
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


def check_topic_ids_consistent(pooled: pl.DataFrame, meta: pl.DataFrame) -> Check:
    """Every topic the shares reference has a definition, and the ids are contiguous.

    A gap in the ids would mean the model published fewer topics than `k` claimed,
    which is the one way a reader would mis-count the covariate's width.
    """
    if pooled.height == 0:
        return Check("topic_ids_consistent", True, "0 rows")
    pooled_ids = set(pooled[TOPIC_ID].unique().to_list())
    meta_ids = set(meta[TOPIC_ID].unique().to_list())
    if pooled_ids != meta_ids:
        missing = sorted(pooled_ids - meta_ids)
        extra = sorted(meta_ids - pooled_ids)
        return Check(
            "topic_ids_consistent",
            False,
            f"shares without a definition: {missing}; definitions without shares: {extra}",
        )
    expected = set(range(max(pooled_ids) + 1))
    if pooled_ids != expected:
        return Check(
            "topic_ids_consistent", False, f"ids are not contiguous 0..{max(pooled_ids)}"
        )
    return Check("topic_ids_consistent", True, f"{len(pooled_ids)} topics, ids 0..{max(pooled_ids)}")


def check_single_model(pooled: pl.DataFrame, meta: pl.DataFrame, candidates: pl.DataFrame) -> Check:
    """One run publishes one model, and the sweep is the record of choosing it.

    The shares and the meta table must each carry exactly one `model_id`, and the
    same one: the id encodes k and the seed, so a disagreement means a table was
    written from a different fit than its neighbour — the failure that would make
    the meta table describe topics the shares never used.

    The sweep is *expected* to carry several ids, one per candidate k. What is
    checked there is the thing that matters: the published model is among them and
    is the one flagged `selected`. Requiring one id across all three tables would
    fail on every real run, since the whole point of the sweep is to hold the
    models that lost.
    """
    published: dict[str, str] = {}
    for frame, label in ((pooled, "shares"), (meta, "meta")):
        if not frame.height:
            continue
        values = set(frame[MODEL_ID].unique().to_list())
        if len(values) != 1:
            return Check(
                "single_model", False, f"{label} carries several models: {sorted(values)}"
            )
        published[label] = next(iter(values))
    if len(set(published.values())) > 1:
        return Check("single_model", False, f"tables disagree on the model: {published}")
    if not published or not candidates.height:
        return Check("single_model", True, "0 rows")
    model = next(iter(published.values()))
    if model not in set(candidates[MODEL_ID].to_list()):
        return Check("single_model", False, f"published {model} is absent from the sweep table")
    selected = candidates.filter(pl.col(SELECTED))
    if selected.height == 1 and selected[MODEL_ID][0] != model:
        return Check(
            "single_model",
            False,
            f"published {model} but the sweep flags {selected[MODEL_ID][0]} as selected",
        )
    return Check("single_model", True, f"all published rows from {model}")


def check_sweep_selects_one(candidates: pl.DataFrame) -> Check:
    """Exactly one candidate is marked selected, and it is the most coherent.

    The selection is the result `notes/03` asks to be reported, so it is checked
    rather than trusted: a tie, a stale flag or an argmax taken over the wrong
    column would all leave a plausible-looking sweep table.
    """
    if candidates.height == 0:
        return Check("sweep_selects_one", True, "0 rows")
    selected = candidates.filter(pl.col(SELECTED))
    if selected.height != 1:
        return Check(
            "sweep_selects_one", False, f"{selected.height} rows marked selected, expected 1"
        )
    best = candidates.sort(COHERENCE, descending=True).row(0, named=True)
    chosen = selected.row(0, named=True)
    if best[TOPIC_ID] != chosen[TOPIC_ID]:
        return Check(
            "sweep_selects_one",
            False,
            f"selected k={chosen[TOPIC_ID]} but the most coherent is k={best[TOPIC_ID]} "
            f"({best[COHERENCE]:.4f} > {chosen[COHERENCE]:.4f})",
        )
    return Check(
        "sweep_selects_one",
        True,
        f"k={chosen[TOPIC_ID]} selected on {COHERENCE} "
        f"({chosen[COHERENCE]:.4f}; ll_per_word {chosen[LL_PER_WORD]:.4f})",
    )


def run_all(
    pooled: pl.DataFrame,
    meta: pl.DataFrame,
    candidates: pl.DataFrame,
    fu_path: Path,
) -> list[Check]:
    return [
        check_share_schema(pooled),
        check_meta_schema(meta),
        check_sweep_schema(candidates),
        check_unique_keys(pooled, GROUP_KEYS, "share"),
        check_unique_keys(meta, META_GROUP_KEYS, "meta"),
        check_weeks_start_on_sunday(pooled),
        check_locations_known(pooled, fu_path),
        check_shares_sum_to_one(pooled),
        check_shares_in_unit_interval(pooled),
        check_finite(pooled, meta),
        check_article_counts(pooled),
        check_topic_ids_consistent(pooled, meta),
        check_single_model(pooled, meta, candidates),
        check_sweep_selects_one(candidates),
        check_national_row_per_week(pooled),
    ]


__all__ = [
    "SHARE_TOLERANCE",
    "Check",
    "check_article_counts",
    "check_finite",
    "check_locations_known",
    "check_meta_schema",
    "check_national_row_per_week",
    "check_share_schema",
    "check_shares_in_unit_interval",
    "check_shares_sum_to_one",
    "check_single_model",
    "check_sweep_schema",
    "check_sweep_selects_one",
    "check_topic_ids_consistent",
    "check_unique_keys",
    "check_weeks_start_on_sunday",
    "run_all",
]
