"""The point metrics, including the MAPE trap the module documents."""

from __future__ import annotations

import math

import pytest

from src.forecast.metrics import mae, mape, mape_denominator, rmse

TRUTH = [10.0, 20.0, 30.0]
PRED = [12.0, 18.0, 33.0]


def test_mae_is_the_mean_absolute_error():
    assert mae(TRUTH, PRED) == pytest.approx((2 + 2 + 3) / 3)


def test_rmse_is_the_root_mean_squared_error():
    assert rmse(TRUTH, PRED) == pytest.approx(math.sqrt((4 + 4 + 9) / 3))


def test_rmse_is_never_below_mae():
    assert rmse(TRUTH, PRED) >= mae(TRUTH, PRED)


def test_rmse_equals_mae_when_every_error_has_the_same_size():
    assert rmse([1.0, 1.0], [3.0, 3.0]) == mae([1.0, 1.0], [3.0, 3.0])


def test_a_perfect_forecast_scores_zero():
    assert mae(TRUTH, TRUTH) == 0
    assert rmse(TRUTH, TRUTH) == 0
    assert mape(TRUTH, TRUTH) == 0


def test_mape_is_a_fraction_not_a_percentage():
    assert mape([100.0], [110.0]) == pytest.approx(0.1)


@pytest.mark.parametrize("metric", [mae, rmse, mape])
def test_length_mismatch_is_refused(metric):
    with pytest.raises(ValueError, match="same length"):
        metric([1.0, 2.0], [1.0])


@pytest.mark.parametrize("metric", [mae, rmse, mape])
def test_an_empty_comparison_is_refused(metric):
    with pytest.raises(ValueError, match="no observations"):
        metric([], [])


# --- the MAPE trap ----------------------------------------------------------


def test_mape_drops_the_weeks_it_cannot_score():
    """A zero week is excluded rather than turned into an infinite error."""
    assert mape([0.0, 100.0], [500.0, 110.0]) == pytest.approx(0.1)


def test_mape_reports_its_own_denominator():
    assert mape_denominator([0.0, 1.0, 5.0, 0.0]) == 2


def test_mape_with_every_week_zero_is_undefined():
    with pytest.raises(ValueError, match="undefined"):
        mape([0.0, 0.0], [1.0, 1.0])


def test_one_tiny_week_can_dominate_mape():
    """The failure mode the docstring warns about, demonstrated.

    Two near-perfect weeks and one week of one notified case: the mean is
    useless, which is why `evaluate` always reports the denominator beside it.
    """
    value = mape([1.0, 1000.0, 1000.0], [500.0, 1000.0, 1000.0])
    assert value > 100
