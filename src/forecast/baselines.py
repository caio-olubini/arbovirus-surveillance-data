"""The naive baselines: the number every model has to beat.

These are deliberately dumb, and that is the point. Protocol 00 puts them first
in the order of work because a representation that cannot clear a straight line
through last year's data is not a finding about the representation. Dengue is
seasonal and strongly autocorrelated week to week, so both of these are
genuinely hard to beat — a model that loses to them has learned nothing, and a
model that barely wins has to be read with the season in mind.

Both are functions of the history alone. Neither is fitted, so both are exactly
reproducible and neither can leak: there is nothing to train on the future.
"""

from __future__ import annotations

from typing import Sequence

from .spec import BASELINES, SEASONAL_LAG


def persistence(history: Sequence[float], horizon: int) -> list[float]:
    """Every future week is the last observed week.

    The strongest of the two on a series with high week-to-week inertia, which
    dengue has: an epidemic week is the best single guess for the next one.
    """
    if not history:
        raise ValueError("persistence needs at least one observed week.")
    if horizon < 1:
        raise ValueError(f"horizon must be at least 1 week, got {horizon}.")
    return [float(history[-1])] * horizon


def seasonal_naive(
    history: Sequence[float],
    horizon: int,
    lag: int = SEASONAL_LAG,
) -> list[float]:
    """Every future week is the same week of the previous season.

    Multi-step is handled by walking forward from the lag rather than by
    repeating one value: at every step the answer sits exactly `lag` weeks
    before the week being predicted, so a 4-week forecast reads four
    consecutive weeks of last season instead of the same one four times.
    Repeating would make the far steps a copy of the near step and would flatter
    the baseline at long horizons.

    Two conditions bound this. The history must be at least `lag` weeks long, or
    there is no previous season to read. And the horizon may not exceed the lag,
    because past that point the "season" being copied has run into the weeks
    already observed — the baseline would be reading its own present and calling
    it a forecast.

    `lag=52` is the weekly convention, not an identity — a year is 52.18 weeks,
    so the reference week drifts about a day per cycle. The panel is gapless, so
    the drift is the calendar's and not a missing week's.
    """
    if horizon < 1:
        raise ValueError(f"horizon must be at least 1 week, got {horizon}.")
    if lag < 1:
        raise ValueError(f"lag must be at least 1 week, got {lag}.")

    if len(history) < lag:
        raise ValueError(
            f"seasonal_naive needs at least {lag} weeks of history to look back "
            f"one season, got {len(history)}."
        )
    if horizon > lag:
        raise ValueError(
            f"horizon {horizon} exceeds lag {lag}: past {lag} steps the previous "
            f"season runs into the observed weeks, and the baseline would be "
            f"copying the present instead of forecasting."
        )

    n = len(history)
    return [float(history[n - lag + (step - 1)]) for step in range(1, horizon + 1)]


# The registry the evaluation loop iterates. Adding a baseline here is the whole
# change: the loop reads the name, calls it, and writes the name into the results.
BASELINE_FUNCS = {
    "persistence": persistence,
    "seasonal_naive": seasonal_naive,
}


def _check_registry() -> None:
    """The declared order and the registry must not drift apart."""
    missing = [name for name in BASELINES if name not in BASELINE_FUNCS]
    if missing:
        raise RuntimeError(f"BASELINES names no function for: {missing}")


_check_registry()
