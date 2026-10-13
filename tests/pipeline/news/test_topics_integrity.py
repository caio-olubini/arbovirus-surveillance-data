"""Braço 03's integrity checks: the fixture tables pass, and each guard fires.

Every check is exercised in both directions, because a check that only ever passes
is indistinguishable from no check at all. The one that matters most is
`check_shares_sum_to_one`: a topic mixture is a point on the simplex, so shares that
do not add to 1 mean the pooling is wrong and the column is not a share.
"""

from __future__ import annotations

from datetime import date

import polars as pl

from src.pipeline.news.topics.integrity import (
    check_article_counts,
    check_finite,
    check_locations_known,
    check_meta_schema,
    check_national_row_per_week,
    check_share_schema,
    check_shares_in_unit_interval,
    check_shares_sum_to_one,
    check_single_model,
    check_sweep_schema,
    check_sweep_selects_one,
    check_topic_ids_consistent,
    check_unique_keys,
    check_weeks_start_on_sunday,
    run_all,
)
from src.pipeline.news.topics.spec import (
    COHERENCE,
    LL_PER_WORD,
    META_OUTPUT_COLUMNS,
    MODEL_ID,
    NATIONAL_LOCATION,
    N_ARTICLES,
    OUTPUT_COLUMNS,
    SELECTED,
    SWEEP_OUTPUT_COLUMNS,
    TOPIC_ID,
)
from src.pipeline.news.topics.steps import META_SCHEMA, SHARE_SCHEMA, SWEEP_SCHEMA

SUNDAY = date(2011, 1, 9)
MONDAY = date(2011, 1, 10)
MODEL = "tomotopy-dmr-k2-seed42"
OTHER_MODEL = "tomotopy-dmr-k5-seed42"
# The model the conftest fixture publishes: the fake's coherence peaks at k=15.
FIXTURE_MODEL = "tomotopy-dmr-k15-seed42"


def _group(ew: date, location: str, shares: list[float], n_articles: int = 3) -> list[dict]:
    """The rows of one (ew, location) group, one per topic."""
    return [
        {
            "ew": ew,
            "location": location,
            "topic_id": topic_id,
            "share": share,
            "n_articles": n_articles,
            "model_id": MODEL,
        }
        for topic_id, share in enumerate(shares)
    ]


def _pooled(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=SHARE_SCHEMA).select(OUTPUT_COLUMNS)


def _meta(rows: list[dict]) -> pl.DataFrame:
    base = {"model_id": MODEL, "topic_id": 0, "term": "dengue", "weight": 0.9}
    return pl.DataFrame([{**base, **row} for row in rows], schema=META_SCHEMA).select(
        META_OUTPUT_COLUMNS
    )


def _sweep(rows: list[dict]) -> pl.DataFrame:
    base = {
        "model_id": MODEL,
        "topic_id": 2,
        "coherence": 0.42,
        "ll_per_word": -8.1,
        "selected": False,
    }
    return pl.DataFrame([{**base, **row} for row in rows], schema=SWEEP_SCHEMA).select(
        SWEEP_OUTPUT_COLUMNS
    )


# --- the fixture ------------------------------------------------------------


def test_all_checks_pass_on_the_fixture_tables(news_topics_tables, fu_path) -> None:
    pooled, meta, candidates = news_topics_tables
    checks = run_all(pooled, meta, candidates, fu_path)
    failed = [c for c in checks if not c.passed]
    assert not failed, "; ".join(str(c) for c in failed)


def test_the_published_columns_are_in_order(news_topics_tables) -> None:
    pooled, meta, candidates = news_topics_tables
    assert tuple(pooled.columns) == OUTPUT_COLUMNS
    assert tuple(meta.columns) == META_OUTPUT_COLUMNS
    assert tuple(candidates.columns) == SWEEP_OUTPUT_COLUMNS


def test_the_fixture_sweep_selects_the_peak_k(news_topics_tables) -> None:
    """The fake's coherence peaks at 15, so the published model must be k=15 and
    the sweep must say so."""
    pooled, meta, candidates = news_topics_tables
    assert set(pooled[MODEL_ID].to_list()) == {FIXTURE_MODEL}
    assert candidates.filter(pl.col(SELECTED))[TOPIC_ID][0] == 15


# --- schemas ----------------------------------------------------------------


def test_a_wrong_share_schema_is_caught() -> None:
    assert check_share_schema(_pooled(_group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4]))).passed
    wrong = _pooled(_group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4])).drop(N_ARTICLES)
    assert not check_share_schema(wrong).passed


def test_a_wrong_meta_schema_is_caught() -> None:
    assert check_meta_schema(_meta([{}])).passed
    assert not check_meta_schema(_meta([{}]).drop("weight")).passed


def test_a_wrong_sweep_schema_is_caught() -> None:
    assert check_sweep_schema(_sweep([{}])).passed
    assert not check_sweep_schema(_sweep([{}]).drop(SELECTED)).passed


# --- keys -------------------------------------------------------------------


def test_a_duplicated_topic_row_is_caught() -> None:
    rows = _group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4])
    assert check_unique_keys(_pooled(rows), ("ew", "location", "topic_id"), "share").passed
    assert not check_unique_keys(
        _pooled(rows + rows[:1]), ("ew", "location", "topic_id"), "share"
    ).passed


def test_the_same_topic_in_two_weeks_is_not_a_duplicate() -> None:
    rows = _group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4]) + _group(
        date(2011, 1, 16), NATIONAL_LOCATION, [0.6, 0.4]
    )
    assert check_unique_keys(_pooled(rows), ("ew", "location", "topic_id"), "share").passed


def test_a_duplicated_meta_term_is_caught() -> None:
    keys = ("model_id", "topic_id", "term")
    assert check_unique_keys(_meta([{}]), keys, "meta").passed
    assert not check_unique_keys(_meta([{}, {}]), keys, "meta").passed


# --- the calendar and the geography -----------------------------------------


def test_a_non_sunday_week_fails() -> None:
    assert check_weeks_start_on_sunday(
        _pooled(_group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4]))
    ).passed
    assert not check_weeks_start_on_sunday(
        _pooled(_group(MONDAY, NATIONAL_LOCATION, [0.6, 0.4]))
    ).passed


def test_locations_must_be_br_or_a_known_uf(fu_path) -> None:
    assert check_locations_known(
        _pooled(_group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4])), fu_path
    ).passed
    assert check_locations_known(_pooled(_group(SUNDAY, "RJ", [0.6, 0.4])), fu_path).passed
    unknown = check_locations_known(_pooled(_group(SUNDAY, "XX", [0.6, 0.4])), fu_path)
    assert not unknown.passed
    assert "XX" in unknown.detail


def test_every_week_must_carry_a_br_row() -> None:
    only_uf = _pooled(_group(SUNDAY, "RJ", [0.6, 0.4]))
    check = check_national_row_per_week(only_uf)
    assert not check.passed
    assert "1 weeks without a BR row" in check.detail

    with_br = _pooled(
        _group(SUNDAY, "RJ", [0.6, 0.4]) + _group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4])
    )
    assert check_national_row_per_week(with_br).passed


# --- the simplex ------------------------------------------------------------


def test_shares_that_do_not_sum_to_one_are_caught() -> None:
    """The check that catches a pooling error the schema cannot see: a topic
    emitted twice, a week's rows drawn from two different models, a mean taken
    over the wrong axis. All of those leave a well-formed table that is not a set
    of shares."""
    assert check_shares_sum_to_one(
        _pooled(_group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4]))
    ).passed
    off = check_shares_sum_to_one(_pooled(_group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.5])))
    assert not off.passed
    assert NATIONAL_LOCATION in off.detail


def test_float32_drift_is_tolerated() -> None:
    """Summing k float32 shares drifts by ~1e-6, which must not be a failure."""
    shares = [1.0 / 7] * 7
    assert check_shares_sum_to_one(_pooled(_group(SUNDAY, NATIONAL_LOCATION, shares))).passed


def test_a_share_outside_the_unit_interval_is_caught() -> None:
    assert check_shares_in_unit_interval(
        _pooled(_group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4]))
    ).passed
    assert not check_shares_in_unit_interval(
        _pooled(_group(SUNDAY, NATIONAL_LOCATION, [1.6, -0.6]))
    ).passed


def test_a_nan_share_fails_the_finite_check() -> None:
    """Nothing downstream raises on a NaN — it propagates into the forecaster
    quietly, which is exactly why it is checked here."""
    assert check_finite(
        _pooled(_group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4])), _meta([{}])
    ).passed
    poisoned = check_finite(
        _pooled(_group(SUNDAY, NATIONAL_LOCATION, [float("nan"), 0.4])), _meta([{}])
    )
    assert not poisoned.passed


def test_a_non_finite_meta_weight_fails() -> None:
    assert not check_finite(
        _pooled(_group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4])),
        _meta([{"weight": float("inf")}]),
    ).passed


# --- counts and consistency -------------------------------------------------


def test_a_pooled_row_must_pool_at_least_one_article() -> None:
    """Zero would mean the location spread produced a row out of nothing."""
    assert check_article_counts(_pooled(_group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4]))).passed
    assert not check_article_counts(
        _pooled(_group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4], n_articles=0))
    ).passed


def test_a_topic_without_a_definition_is_caught() -> None:
    pooled = _pooled(_group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4]))
    defined = _meta([{"topic_id": 0}, {"topic_id": 1, "term": "caso"}])
    assert check_topic_ids_consistent(pooled, defined).passed

    undefined = _meta([{"topic_id": 0}])
    check = check_topic_ids_consistent(pooled, undefined)
    assert not check.passed
    assert "1" in check.detail


def test_a_gap_in_the_topic_ids_is_caught() -> None:
    """A gap would mean the model published fewer topics than k claimed, which is
    the one way a reader would mis-count the covariate's width."""
    pooled = _pooled(
        _group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4])
        + [
            {
                "ew": SUNDAY,
                "location": NATIONAL_LOCATION,
                "topic_id": 3,
                "share": 0.0,
                "n_articles": 3,
                "model_id": MODEL,
            }
        ]
    )
    defined = _meta([{"topic_id": 0}, {"topic_id": 1}, {"topic_id": 3, "term": "caso"}])
    check = check_topic_ids_consistent(pooled, defined)
    assert not check.passed
    assert "contiguous" in check.detail


def test_two_models_in_one_published_table_are_caught() -> None:
    rows = _group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4])
    rows[1] = {**rows[1], "model_id": OTHER_MODEL}
    check = check_single_model(_pooled(rows), _meta([{}]), _sweep([{}]))
    assert not check.passed
    assert "several models" in check.detail


def test_the_published_tables_must_agree_on_the_model() -> None:
    check = check_single_model(
        _pooled(_group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4])),
        _meta([{"model_id": OTHER_MODEL}]),
        _sweep([{"selected": True}]),
    )
    assert not check.passed
    assert "disagree" in check.detail


def test_the_sweep_may_hold_the_losing_models() -> None:
    """It has to: recording only the winner would hide the evidence for choosing
    it. So the check is that the published model is *among* the sweep's, not that
    the sweep holds exactly one."""
    check = check_single_model(
        _pooled(_group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4])),
        _meta([{}]),
        _sweep([{"model_id": OTHER_MODEL, "topic_id": 5}, {"model_id": MODEL, "selected": True}]),
    )
    assert check.passed


def test_a_published_model_absent_from_the_sweep_is_caught() -> None:
    check = check_single_model(
        _pooled(_group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4])),
        _meta([{}]),
        _sweep([{"model_id": OTHER_MODEL, "selected": True}]),
    )
    assert not check.passed
    assert "absent from the sweep" in check.detail


def test_publishing_a_model_the_sweep_did_not_select_is_caught() -> None:
    check = check_single_model(
        _pooled(_group(SUNDAY, NATIONAL_LOCATION, [0.6, 0.4])),
        _meta([{}]),
        _sweep([{"model_id": MODEL, "selected": False}, {"model_id": OTHER_MODEL, "selected": True}]),
    )
    assert not check.passed
    assert "flags" in check.detail


# --- the selection itself ---------------------------------------------------


def test_the_sweep_must_flag_exactly_one_candidate() -> None:
    none = check_sweep_selects_one(_sweep([{"topic_id": 2}, {"topic_id": 5}]))
    assert not none.passed
    assert "0 rows marked selected" in none.detail

    two = check_sweep_selects_one(
        _sweep([{"topic_id": 2, "selected": True}, {"topic_id": 5, "selected": True}])
    )
    assert not two.passed


def test_the_flagged_candidate_must_be_the_most_coherent() -> None:
    """The selection is the result notes/03 asks to be reported, so it is checked
    rather than trusted: a stale flag or an argmax taken over the wrong column
    would leave a plausible-looking sweep table."""
    good = check_sweep_selects_one(
        _sweep([
            {"topic_id": 2, "coherence": 0.30, "selected": False},
            {"topic_id": 5, "coherence": 0.42, "selected": True},
        ])
    )
    assert good.passed

    stale = check_sweep_selects_one(
        _sweep([
            {"topic_id": 2, "coherence": 0.30, "selected": True},
            {"topic_id": 5, "coherence": 0.42, "selected": False},
        ])
    )
    assert not stale.passed
    assert "most coherent" in stale.detail
    assert LL_PER_WORD in SWEEP_OUTPUT_COLUMNS
