"""The point metrics and the distributional ones, including the MAPE trap.

The point half is arithmetic anyone can recheck. The distributional half is not,
so it is checked against properties instead of against expected numbers: the
pinball loss is minimised by the true quantile, the interval score is the width
when nothing misses, and WIS equals twice the mean pinball loss. Those three are
what make the numbers mean what the docstrings claim.
"""

from __future__ import annotations

import math

import pytest

from src.forecast.metrics import (
    coverage,
    interval_score,
    interval_width,
    mae,
    mape,
    mape_denominator,
    pinball,
    rmse,
    wis,
)

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


# --- the distributional half -------------------------------------------------
#
# A quantile grid of three levels is enough to check the arithmetic by hand: the
# median, and the 0.25/0.75 pair that makes one central interval of nominal
# coverage 0.5.

GRID = (0.25, 0.5, 0.75)


def test_pinball_is_asymmetric_by_design():
    """At the 90th percentile, landing above the forecast costs nine times as much.

    That asymmetry is what makes a 90th percentile mean anything: a forecast that
    is symmetric is not a quantile forecast.
    """
    above = pinball([100.0], [90.0], 0.9)  # truth above the 0.9 quantile
    below = pinball([80.0], [90.0], 0.9)  # truth below it
    assert above == pytest.approx(9.0)  # 0.9 x 10
    assert below == pytest.approx(1.0)  # 0.1 x 10


def test_the_median_of_the_pinball_loss_is_half_the_absolute_error():
    assert pinball([10.0, 20.0], [12.0, 18.0], 0.5) == pytest.approx(
        0.5 * mae([10.0, 20.0], [12.0, 18.0])
    )


def test_the_pinball_loss_is_minimised_by_the_true_quantile():
    """The property that makes it a proper scoring rule.

    Sweeping the forecast across the sample, the loss bottoms out at the value
    that really is the 0.25 quantile — so a forecaster cannot do better than
    report the quantile it believes. This is checked rather than assumed: a loss
    without it would still produce a number, and the number would reward a
    confident forecast for being confident.
    """
    sample = [1.0, 2.0, 3.0, 4.0, 5.0]  # o quantil 0,25 da amostra é 2
    losses = {q: pinball(sample, [q] * len(sample), 0.25) for q in sample}
    assert min(losses, key=losses.get) == 2.0
    assert sorted(losses.values())[0] < sorted(losses.values())[1]  # um só mínimo


def test_a_quantile_level_outside_the_open_unit_interval_is_refused():
    with pytest.raises(ValueError, match="strictly between"):
        pinball([1.0], [1.0], 1.0)


def test_the_interval_score_is_the_width_when_nothing_misses():
    assert interval_score([5.0, 5.0], [4.0, 4.0], [6.0, 6.0], level=0.5) == pytest.approx(2.0)


def test_the_interval_score_punishes_a_miss_by_forty_times_the_distance():
    """Um intervalo de 95% errado por 2 casos custa a largura mais 40 x 2."""
    value = interval_score([10.0], [0.0], [8.0], level=0.95)
    assert value == pytest.approx(8.0 + 40.0 * 2.0)


def test_a_wider_interval_pays_for_itself_only_if_it_stops_missing():
    """A largura é o preço da cobertura, e o teste diz quanto ela custa.

    Alargar o intervalo até engolir a observação sempre melhora a nota — é por
    isso que `coverage` anda junto com a largura, e não sozinha.
    """
    narrow = interval_score([10.0], [4.0], [6.0], level=0.5)
    wide = interval_score([10.0], [0.0], [12.0], level=0.5)
    assert narrow == pytest.approx(2.0 + 4.0 * 4.0)
    assert wide == pytest.approx(12.0)


def test_an_inverted_interval_is_refused_rather_than_scored():
    with pytest.raises(ValueError, match="inverted"):
        interval_score([5.0], [9.0], [3.0], level=0.5)


def test_wis_equals_twice_the_mean_pinball_over_the_grid():
    """The identity that makes WIS the CRPS on a quantile grid, not a second number.

    This is the assertion that pins the normalisation: `1 / (K + 1/2)` is what
    makes the two coincide, and any other constant would break this test while
    still producing a plausible-looking number.
    """
    truth = [10.0, 20.0, 30.0, 40.0]
    quantiles = {
        0.25: [8.0, 18.0, 28.0, 38.0],
        0.5: [9.0, 19.0, 29.0, 39.0],
        0.75: [11.0, 21.0, 31.0, 41.0],
    }
    spread = sum(pinball(truth, quantiles[level], level) for level in GRID) / len(GRID)
    assert wis(truth, quantiles, GRID) == pytest.approx(2 * spread)


def test_wis_equals_the_absolute_error_when_there_is_only_a_median():
    """A grid with no interval left is the median's error, in the same unit."""
    truth = [10.0, 20.0]
    assert wis(truth, {0.5: [12.0, 18.0]}, (0.5,)) == pytest.approx(2.0)


def test_a_grid_without_the_median_is_refused():
    with pytest.raises(ValueError, match="must contain 0.5"):
        wis([1.0], {0.25: [1.0], 0.75: [1.0]}, (0.25, 0.75))


def test_an_unpaired_level_is_refused():
    """A level with no mirror is not a central interval, so it cannot be summed."""
    with pytest.raises(ValueError, match="no opposite"):
        wis([1.0], {0.25: [1.0], 0.5: [1.0], 0.9: [1.0]}, (0.25, 0.5, 0.9))


def test_an_unpaired_level_above_the_median_is_refused_too():
    """The orphan can be on either side, and only asking the lower half misses it.

    A grid of 0.5 and 0.9 has no unpaired level *below* 0.5, so a check that only
    walks the lower half accepts it — and then the 0.9 forecast is never scored,
    which is a number under the wrong name rather than an error.
    """
    with pytest.raises(ValueError, match="no opposite"):
        wis([1.0], {0.5: [1.0], 0.9: [1.0]}, (0.5, 0.9))


def test_a_repeated_level_is_refused():
    """A repeated level would be counted twice as an interval and change the divisor.

    WIS divides by the number of central intervals, so a grid that names 0.25
    twice reports a number that is not twice the mean pinball loss, while every
    individual level in it looks legitimate.
    """
    quantiles = {
        0.1: [7.0],
        0.25: [8.0],
        0.5: [9.0],
        0.75: [12.0],
        0.9: [15.0],
    }
    clean = wis([10.0], quantiles, (0.1, 0.25, 0.5, 0.75, 0.9))
    spread = 2 * sum(
        pinball([10.0], quantiles[level], level)
        for level in (0.1, 0.25, 0.5, 0.75, 0.9)
    ) / 5
    assert clean == pytest.approx(spread)
    with pytest.raises(ValueError, match="more than once"):
        wis([10.0], quantiles, (0.1, 0.25, 0.25, 0.5, 0.75, 0.9))


def test_a_mirror_that_differs_only_by_rounding_is_still_scored():
    """A tolerância existe para o arredondamento do literal, não para grade assimétrica.

    Quem escreve os terços como 0.33 e 0.67 tem um par central e não sabe que
    `1 - 0.33` é 0.6699999999999999. Recusar isso seria recusar uma grade
    legítima; aceitar com a folga larga demais punha erro no número.
    """
    levels = (0.33, 0.5, 0.67)
    quantiles = {0.33: [7.0, 8.0], 0.5: [9.0, 10.0], 0.67: [15.0, 16.0]}
    truth = [10.0, 20.0]
    spread = 2 * sum(
        pinball(truth, quantiles[level], level) for level in levels
    ) / len(levels)
    assert wis(truth, quantiles, levels) == pytest.approx(spread)


def test_an_asymmetric_grid_is_refused_rather_than_scored_almost_right():
    """Uma folga de 1e-10 no par vira erro no número, e a identidade exige o par exato.

    Aceitar esta grade devolvia um WIS que não era duas vezes o pinball médio —
    por pouco, mas sem aviso. O que não é a identidade é recusado.
    """
    with pytest.raises(ValueError, match="no opposite"):
        wis(
            [10.0, 20.0],
            {0.1: [7.0, 8.0], 0.5: [9.0, 10.0], 0.9000000001: [15.0, 16.0]},
            (0.1, 0.5, 0.9000000001),
        )


def test_two_levels_that_would_share_a_mirror_are_refused():
    """Um espelho pertence a um nível só: dois níveis baixos não podem dividir o mesmo.

    Sem isso, o nível que sobra fica na grade e no `quantiles` e nunca é somado —
    aceito pela checagem e descartado na conta, que é o defeito que a checagem
    existe para impedir.
    """
    with pytest.raises(ValueError, match="no opposite"):
        wis(
            [10.0, 20.0],
            {
                0.25: [7.0, 8.0],
                0.25 + 1e-12: [7.0, 8.0],
                0.5: [9.0, 10.0],
                0.75: [15.0, 16.0],
            },
            (0.25, 0.25 + 1e-12, 0.5, 0.75),
        )


def test_a_missing_level_in_the_forecasts_is_refused():
    with pytest.raises(ValueError, match="no forecast for level"):
        wis([1.0], {0.5: [1.0], 0.75: [1.0]}, (0.25, 0.5, 0.75))


def test_coverage_counts_the_weeks_inside_the_interval():
    assert coverage([1.0, 5.0, 9.0], [0.0, 6.0, 0.0], [2.0, 8.0, 10.0]) == pytest.approx(2 / 3)


def test_the_width_is_the_mean_span_because_coverage_alone_says_nothing():
    assert interval_width([0.0, 2.0], [4.0, 6.0]) == pytest.approx(4.0)
    # A wider interval covers more, always: that is why the two travel together.
    assert coverage([100.0], [0.0], [10_000.0]) == 1.0
