"""Point-forecast error metrics.

Protocol 00 asks for three point metrics and a set of probabilistic ones. Only
the first three are here: the baselines emit a single number per week, so there
is no distribution to score yet. WIS/CRPS and coverage arrive with the first
model that produces intervals, and until then computing them would mean
inventing an uncertainty the baseline never claimed.

`mape` is the one with a trap, and it is documented rather than smoothed over.
"""

from __future__ import annotations

import math
from typing import Sequence


def _paired(y_true: Sequence[float], y_pred: Sequence[float]) -> None:
    if len(y_true) != len(y_pred):
        raise ValueError(
            f"y_true and y_pred must be the same length, got "
            f"{len(y_true)} and {len(y_pred)}."
        )
    if not y_true:
        raise ValueError("no observations to score.")


def mae(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Mean absolute error, in cases. The headline number."""
    _paired(y_true, y_pred)
    return sum(abs(t - p) for t, p in zip(y_true, y_pred)) / len(y_true)


def rmse(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Root mean squared error, in cases.

    Read next to MAE, never instead of it. The gap between the two is the shape
    of the error: RMSE much larger than MAE means a few weeks dominate, which on
    this series is what a missed epidemic peak looks like.
    """
    _paired(y_true, y_pred)
    return math.sqrt(sum((t - p) ** 2 for t, p in zip(y_true, y_pred)) / len(y_true))


def mape(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Mean absolute percentage error, as a fraction (0.12 = 12%).

    Strictly, MAPE is undefined wherever the truth is zero, and a near-zero week
    makes it meaningless rather than merely noisy: the value being divided by is
    the thing that got small. So the function refuses to guess — it scores the
    weeks it can and hands back the count separately, because a MAPE quoted
    without its denominator is a number whose base is unknown.

    On the dengue series nothing is actually dropped (the floor is 1,341 cases,
    so `mape_n` equals `n`), and that is not a clean bill of health. MAPE
    weights a week by the inverse of its size, so it **ranks weeks differently**
    from MAE: the week this metric calls the worst erred 4,647 cases, while the
    week MAE calls the worst erred 84,739 — eighteen times more — and carries a
    third of the percentage error. Both orderings are defensible; they are not
    the same ordering, and reporting only one hides that a choice was made.
    """
    _paired(y_true, y_pred)
    scored = [
        abs((t - p) / t) for t, p in zip(y_true, y_pred) if t != 0
    ]
    if not scored:
        raise ValueError("every observed week was zero; MAPE is undefined.")
    return sum(scored) / len(scored)


def mape_denominator(y_true: Sequence[float]) -> int:
    """How many weeks `mape` can actually score."""
    return sum(1 for t in y_true if t != 0)
