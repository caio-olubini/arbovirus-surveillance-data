"""Rolling origin: the split rule the whole comparison depends on."""

from __future__ import annotations

import polars as pl
import pytest

from src.forecast.spec import EW
from src.forecast.splits import Origin, rolling_origin


def origins(panel: pl.DataFrame, **kwargs) -> list[Origin]:
    return list(rolling_origin(panel, **kwargs))


def test_the_first_origin_has_exactly_min_train_weeks_behind_it(panel_from_values):
    panel = panel_from_values(list(range(10)))
    first = origins(panel, min_train=4, horizon=1)[0]
    assert first.index == 3
    assert first.train_end == 4
    # The history is a slice that ends at the origin — nothing after it.
    assert panel[EW].to_list()[: first.train_end][-1] == first.ew


def test_the_last_origin_leaves_a_complete_horizon_inside_the_panel(panel_from_values):
    panel = panel_from_values(list(range(10)))
    last = origins(panel, min_train=4, horizon=3)[-1]
    assert last.index == 6
    assert max(last.target_indices()) == 9  # the final week, not past it


def test_the_number_of_origins_follows_from_the_shape(panel_from_values):
    panel = panel_from_values(list(range(10)))
    # 10 weeks, 4 to train and 1 to score: 6 origins, one per forecastable week.
    assert len(origins(panel, min_train=4, horizon=1)) == 6


@pytest.mark.parametrize("horizon", [1, 2, 4])
def test_every_origin_is_scored_on_a_full_horizon(panel_from_values, horizon: int):
    panel = panel_from_values(list(range(30)))
    for origin in rolling_origin(panel, min_train=10, horizon=horizon):
        assert len(list(origin.target_indices())) == horizon


def test_origins_walk_forward_by_one_week(panel_from_values):
    panel = panel_from_values(list(range(20)))
    indices = [o.index for o in rolling_origin(panel, min_train=5, horizon=1)]
    assert indices == list(range(4, 19))


def test_step_skips_origins_without_moving_the_ends(panel_from_values):
    panel = panel_from_values(list(range(20)))
    every_other = origins(panel, min_train=5, horizon=1, step=2)
    assert [o.index for o in every_other] == [4, 6, 8, 10, 12, 14, 16, 18]
    assert every_other[0].index == 4


def test_target_indices_start_the_week_after_the_origin(panel_from_values):
    panel = panel_from_values(list(range(10)))
    origin = origins(panel, min_train=4, horizon=3)[0]
    assert list(origin.target_indices()) == [4, 5, 6]
    assert 3 not in origin.target_indices()  # the origin week itself is history


def test_the_origin_carries_the_week_it_refers_to(panel_from_values):
    panel = panel_from_values(list(range(10)))
    weeks = panel[EW].to_list()
    for origin in rolling_origin(panel, min_train=4, horizon=1):
        assert origin.ew == weeks[origin.index]


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"min_train": 0, "horizon": 1}, "min_train"),
        ({"min_train": -3, "horizon": 1}, "min_train"),
        ({"min_train": 4, "horizon": 0}, "horizon"),
        ({"min_train": 10, "horizon": 1}, "not enough"),
        ({"min_train": 9, "horizon": 2}, "not enough"),
    ],
)
def test_impossible_setups_are_refused(panel_from_values, kwargs, match):
    panel = panel_from_values(list(range(10)))
    with pytest.raises(ValueError, match=match):
        origins(panel, **kwargs)


def test_a_horizon_that_consumes_the_panel_yields_nothing(panel_from_values):
    """Tight but possible shapes still produce work rather than an error."""
    panel = panel_from_values(list(range(5)))
    assert len(origins(panel, min_train=4, horizon=1)) == 1
