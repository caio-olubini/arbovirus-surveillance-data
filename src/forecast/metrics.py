"""How a forecast is scored: three point metrics, then five distributional ones.

The point half is `mae`, `rmse` and `mape`, and `mape` is the one with a trap —
documented rather than smoothed over. The distributional half scores a forecast
that reports quantiles instead of a single number: `pinball`, `interval_score`,
`wis`, `coverage` and `interval_width`.

**One probabilistic number, not two.** The ask usually arrives as
"WIS/CRPS/coverage", as if that were three numbers. On a symmetric quantile grid
they are one: the weighted interval score is exactly twice the mean pinball loss
over the grid (Bracher et al. 2021), and that is exactly the discretised CRPS.
Protocol 00 therefore asks for WIS, with the coverage and the width of each
central band beside it, and that is what this module computes — one number,
rather than two names for the same one.
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence


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


# --- the distributional half -------------------------------------------------
#
# A forecast that reports quantiles is scored against the truth once, at every
# level it reported. The functions below are the whole of it: `pinball` is
# the rule each level is honest under, `interval_score` and `wis` collapse a grid
# of them into one number, and `coverage` and `interval_width` say how the
# intervals were shaped.


def _check_level(level: float) -> None:
    if not 0.0 < level < 1.0:
        raise ValueError(
            f"a quantile level is strictly between 0 and 1, got {level}."
        )


# Quanto um nível acima de 0.5 pode divergir de `1 - nível` e ainda ser o espelho
# dele. A tolerância existe para o arredondamento do literal, não para aceitar
# grade assimétrica: quem escreve 0.33 e 0.67 tem um par central e não sabe que
# `1 - 0.33` é 0.6699999999999999. Ela é apertada de propósito, porque a
# identidade `WIS = 2 x pinball médio` só vale para o par exato — a folga toda
# vira erro no número, e 1e-9 virava 1e-8 de desvio.
MIRROR_TOLERANCE = 1e-12


def pinball(y_true: Sequence[float], y_pred: Sequence[float], level: float) -> float:
    """Mean pinball loss at one quantile level, in cases.

    The rule a quantile forecast is honest under: it is minimised by reporting
    the true `level`-quantile of the predictive distribution, so a forecaster
    cannot gain by overstating confidence. It is asymmetric on purpose — at
    level 0.9, landing above the forecast costs nine times what landing below it
    costs, which is what makes "the 90th percentile" mean anything.

    Scored in cases, like MAE. It is not the MAE, though: the two sides are
    weighted differently at every level except 0.5, where the two coincide. A
    pinball is read against another pinball — at another level, or for another
    baseline — not against an MAE on the same line.
    """
    _check_level(level)
    _paired(y_true, y_pred)
    total = 0.0
    for truth, pred in zip(y_true, y_pred):
        gap = truth - pred
        total += level * gap if gap >= 0 else (level - 1.0) * gap
    return total / len(y_true)


def interval_score(
    y_true: Sequence[float],
    lower: Sequence[float],
    upper: Sequence[float],
    level: float,
) -> float:
    """Mean interval score of a central interval of nominal coverage `level`.

    `(upper - lower)` for a week that lands inside, and that width plus
    `2 / (1 - level)` times the distance it missed by when it does not (Bracher
    et al. 2021). The width term is what stops a model from buying coverage with
    an interval so wide it says nothing.

    `level` is the coverage the interval claims — 0.5 for the interquartile
    range, 0.95 for the usual outer band — not a quantile level. The two are
    related by `alpha = 1 - level`: a 0.95 interval is the 0.025 and 0.975
    quantiles, and missing it costs forty times the distance missed.
    """
    _check_level(level)
    _paired(y_true, lower)
    _paired(y_true, upper)
    alpha = 1.0 - level
    total = 0.0
    for truth, low, high in zip(y_true, lower, upper):
        if high < low:
            raise ValueError(
                f"the interval is inverted on a week where the truth is "
                f"{truth}: lower {low} is above upper {high}."
            )
        total += high - low
        if truth < low:
            total += (2.0 / alpha) * (low - truth)
        elif truth > high:
            total += (2.0 / alpha) * (truth - high)
    return total / len(y_true)


def _pairs(levels: Sequence[float]) -> list[tuple[float, float]]:
    """The central intervals a grid declares: each level below 0.5 and its mirror.

    One pairing, computed once, used both to validate the grid and to sum it. That
    is the point: when the check asks one question ("does every level have *a*
    mirror?") and the sum asks another ("which level do I read as the mirror?"),
    a grid can pass the check and then be scored wrongly — a level accepted and
    never summed, or the same interval counted twice.

    Intentions, in the order the grid is read:
    - only a level above 0.5 can be the mirror of a level below it, so a level can
      never be paired with itself or with a same-side neighbour;
    - the mirror is the nearest level within tolerance, and it is *claimed*, so no
      two lower levels can share one upper level;
    - a level above 0.5 that nobody claimed is refused rather than ignored. A grid
      with an orphan above the median has no orphan below it, which is why asking
      only the lower half misses it.

    The pairing is greedy, so a grid carrying two levels within the tolerance of
    each other can be refused although some pairing of it exists. That is the safe
    side of the choice: it is a refusal with a message, not a number.
    """
    lower = sorted(t for t in levels if t < 0.5)
    available = sorted(t for t in levels if t > 0.5)
    pairs: list[tuple[float, float]] = []

    for level in lower:
        near = [
            other for other in available if abs((1.0 - level) - other) <= MIRROR_TOLERANCE
        ]
        if not near:
            raise ValueError(
                f"level {level} has no opposite in the grid {sorted(levels)}: a "
                f"central interval needs both of its quantiles, and a level with "
                f"no mirror would be silently dropped from the sum."
            )
        upper = min(
            near, key=lambda other: (abs((1.0 - level) - other), other)
        )
        available.remove(upper)
        pairs.append((level, upper))

    if available:
        raise ValueError(
            f"these levels have no opposite in the grid {sorted(levels)}: "
            f"{available}. A grid has one level above 0.5 for each level below "
            f"it, and these belong to no central interval."
        )
    return pairs


def _check_grid(levels: Sequence[float]) -> list[tuple[float, float]]:
    """A grid the CRPS equivalence holds on: the median, and paired levels.

    Returns the pairs, so the caller scores exactly the intervals this validated
    rather than pairing the grid a second time by its own rule.
    """
    for level in levels:
        _check_level(level)
    repeated = sorted(
        {t for t in levels if sum(1 for other in levels if other == t) > 1}
    )
    if repeated:
        raise ValueError(
            f"these levels appear more than once: {repeated}. A repeated level "
            f"would count as a second central interval, and WIS divides by the "
            f"number of intervals, so the number would not be the mean pinball."
        )
    if 0.5 not in levels:
        raise ValueError(
            "the grid must contain 0.5: the median is the level every other "
            "level is paired against."
        )
    return _pairs(levels)


def wis(
    y_true: Sequence[float],
    quantiles: Mapping[float, Sequence[float]],
    levels: Sequence[float],
) -> float:
    """Mean weighted interval score, in cases — the headline probabilistic number.

    Bracher et al. 2021, in the form the forecast hubs use: the median's absolute
    error at half weight plus each central interval's score weighted by
    `alpha / 2`, over `K + 1/2` where `K` is the number of intervals. Lower is
    better.

    **It is in cases, and it is not on the MAE's scale.** The sum is divided by
    `K + 1/2` before it is reported, so the two numbers do not answer on the same
    footing and a WIS below the MAE printed beside it is not a gain. Nothing in
    the formula caps it at the MAE either — a wide band can push the WIS past it,
    and a perfect median with uselessly wide bands scores worse than the MAE
    alone. Read a WIS against another WIS.

    **It is not a second number beside CRPS.** On a symmetric grid, WIS is
    exactly twice the mean pinball loss over the grid, which is the discretised
    CRPS — the module's docstring says why that matters. `_check_grid` enforces
    the symmetry the identity needs, so a grid that would break it is refused
    instead of quietly producing a number under the wrong name.

    `quantiles` maps each level to that level's forecast per week; every level in
    `levels` must be present.
    """
    pairs = _check_grid(levels)
    missing = [t for t in levels if t not in quantiles]
    if missing:
        raise ValueError(f"no forecast for level(s): {sorted(missing)}.")

    inner = [0.5 * mae(y_true, quantiles[0.5])]
    for level, upper in pairs:
        alpha = 2.0 * level
        inner.append(
            (alpha / 2.0)
            * interval_score(
                y_true,
                quantiles[level],
                quantiles[upper],
                level=1.0 - alpha,
            )
        )
    intervals = len(inner) - 1
    return sum(inner) / (intervals + 0.5)


def coverage(
    y_true: Sequence[float], lower: Sequence[float], upper: Sequence[float]
) -> float:
    """The fraction of weeks that landed inside the interval, as a fraction.

    Read beside the interval's width, never alone: widening an interval always
    raises coverage, and an interval that covers everything has said nothing.
    A well-calibrated 95% interval covers 0.95 of the weeks; the gap between the
    two is the part of the result worth discussing, and it is measured on the
    same weeks as everything else here.
    """
    _paired(y_true, lower)
    _paired(y_true, upper)
    inside = sum(1 for t, low, high in zip(y_true, lower, upper) if low <= t <= high)
    return inside / len(y_true)


def interval_width(lower: Sequence[float], upper: Sequence[float]) -> float:
    """Mean width of the interval, in cases.

    What `coverage` cannot say on its own. "The 95% interval covered 0.96 of the
    weeks" and "it was 60,000 cases wide" are the same fact told twice, and only
    both together say whether the interval was informative.
    """
    _paired(lower, upper)
    return sum(high - low for low, high in zip(lower, upper)) / len(lower)
