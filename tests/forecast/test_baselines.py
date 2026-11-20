"""The naive baselines. Small, exact, and about the arithmetic only."""

from __future__ import annotations

import pytest

from src.forecast.baselines import BASELINE_FUNCS, persistence, seasonal_naive
from src.forecast.spec import BASELINES


def test_registry_covers_every_declared_baseline():
    assert set(BASELINES) == set(BASELINE_FUNCS)


# --- persistence ------------------------------------------------------------


def test_persistence_repeats_the_last_observed_week():
    assert persistence([10.0, 20.0, 30.0], horizon=1) == [30.0]


def test_persistence_repeats_it_for_every_step():
    assert persistence([10.0, 20.0, 30.0], horizon=3) == [30.0, 30.0, 30.0]


def test_persistence_needs_a_history():
    with pytest.raises(ValueError, match="at least one observed week"):
        persistence([], horizon=1)


@pytest.mark.parametrize("horizon", [0, -1])
def test_persistence_rejects_a_non_positive_horizon(horizon: int):
    with pytest.raises(ValueError, match="horizon"):
        persistence([1.0], horizon=horizon)


# --- seasonal naive ---------------------------------------------------------


def test_seasonal_naive_reads_one_year_back():
    history = list(range(1, 61))  # 60 weeks, values 1..60
    # Step 1 predicts position 60; its twin last season is 52 weeks earlier, at
    # position 8 (value 9) — not the last observed week.
    assert seasonal_naive(history, horizon=1) == [9.0]


def test_seasonal_naive_walks_forward_instead_of_repeating():
    """A 3-step forecast reads three consecutive weeks of last season."""
    history = list(range(1, 61))
    assert seasonal_naive(history, horizon=3) == [9.0, 10.0, 11.0]


def test_every_step_sits_exactly_the_lag_before_the_week_it_predicts():
    """The property the whole baseline rests on, checked by construction."""
    history = list(range(1, 61))
    n = len(history)
    for step, predicted in enumerate(seasonal_naive(history, horizon=5), start=1):
        assert predicted == history[n + step - 1 - 52]


def test_seasonal_naive_horizon_one_equals_a_lag_shift():
    history = [float(i % 7) for i in range(120)]
    assert seasonal_naive(history, horizon=1) == [history[120 - 52]]


def test_seasonal_naive_accepts_a_custom_lag():
    history = list(range(1, 21))
    assert seasonal_naive(history, horizon=1, lag=4) == [17.0]


def test_seasonal_naive_refuses_a_history_shorter_than_the_lag():
    with pytest.raises(ValueError, match="at least 52 weeks"):
        seasonal_naive(list(range(1, 52)), horizon=1)


def test_seasonal_naive_accepts_a_history_exactly_as_long_as_the_lag():
    """52 weeks is enough for one step: the reference week is the first one."""
    assert seasonal_naive(list(range(1, 53)), horizon=1) == [1.0]


def test_a_horizon_longer_than_the_lag_is_refused():
    """Past the lag the baseline would read the present, not last season."""
    with pytest.raises(ValueError, match="exceeds lag"):
        seasonal_naive(list(range(1, 61)), horizon=53, lag=52)


def test_a_horizon_equal_to_the_lag_is_allowed():
    """The longest legal horizon walks the whole previous season, week by week."""
    history = list(range(1, 61))
    assert seasonal_naive(history, horizon=52, lag=52) == [
        float(v) for v in history[len(history) - 52:]
    ]


def test_seasonal_naive_rejects_a_non_positive_lag():
    with pytest.raises(ValueError, match="lag"):
        seasonal_naive(list(range(60)), horizon=1, lag=0)
