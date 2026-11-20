"""Rolling origin: fit on the past, predict the future, then move forward.

Protocol 00 fixes this as the only split allowed. The alternative — one holdout
at the end — lets a model be tuned on the period it is scored on, and it cannot
say anything about stability: a method that works in 2021 and fails in 2024 gets
one averaged number and no warning.

The rule enforced here is that a model at origin *i* may read `values[:i + 1]`
and nothing after it. `Origin` carries the cut so the caller does not have to
reconstruct it, and it is a position rather than a date precisely because the
panel is gapless (see `panel.py`).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterator

import polars as pl

from .spec import EW


@dataclass(frozen=True)
class Origin:
    """One forecast origin: the last week a model is allowed to have seen.

    `index` is the position of that week in the panel. The model may read the
    panel up to and including `index`, and is scored on the `horizon` weeks that
    follow it.
    """

    index: int
    ew: dt.date
    horizon: int

    @property
    def train_end(self) -> int:
        """Exclusive slice bound for the history a model may read."""
        return self.index + 1

    def target_indices(self) -> range:
        """Positions of the weeks this origin is scored on."""
        return range(self.index + 1, self.index + 1 + self.horizon)


def rolling_origin(
    panel: pl.DataFrame,
    min_train: int,
    horizon: int = 1,
    step: int = 1,
) -> Iterator[Origin]:
    """Yield every origin that has enough history and a complete horizon ahead.

    `min_train` is a count of weeks, not a date, so the same call works on any
    window. The last origin is the one whose final scored week is still inside
    the panel: origins that would be scored partly on weeks that do not exist
    are dropped rather than scored on a short horizon, because a shorter horizon
    is a different question and would quietly bias the per-horizon metrics.
    """
    weeks = panel[EW].to_list()
    n = len(weeks)

    if min_train < 1:
        raise ValueError(f"min_train must be at least 1 week, got {min_train}.")
    if horizon < 1:
        raise ValueError(f"horizon must be at least 1 week, got {horizon}.")

    last = n - horizon
    if last < min_train:
        raise ValueError(
            f"{n} weeks is not enough for min_train={min_train} with "
            f"horizon={horizon}: the first origin would be at position "
            f"{min_train} and the last at {last}. Widen the panel or lower "
            f"min_train."
        )

    for index in range(min_train - 1, last, step):
        yield Origin(index=index, ew=weeks[index], horizon=horizon)
