"""Turning a point forecast into a distribution, for baselines that have none.

The naive baselines report one number per week, and a distributional metric has
nothing to score until they report a spread. The spread does not have to be
invented: each baseline has made h-step-ahead errors before, and the empirical
distribution of its own past errors *is* the uncertainty it has shown. Every
quantile here comes from that sample and from nothing else.

Three properties make this honest rather than decorative:

- **Only the past.** At origin *i* the error sample contains the errors the
  baseline could have observed — the ones whose target week had already
  happened by *i*. `ErrorHistory.sample` is where that bound lives, and it is
  the property the tests hold it to.
- **The same forecast.** The point forecast is the centre of the distribution,
  by construction: the errors are centred on their own median before being added
  back (`predictive_quantiles`). Otherwise a row would report an MAE for one
  forecast and a WIS for another, and the bias of the naive would leak into the
  spread. The bias is still measured — by MAE, where it belongs.
- **Nothing about the model.** These are the naive baselines' intervals, not a
  model's. A fitted model reports its own predictive distribution; this module
  is what lets the baselines be scored on the same rule until then.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from .spec import MIN_ERROR_SAMPLE

# A forecast function returns one value per step of the horizon.
Forecast = Callable[[Sequence[float], int], list[float]]


def empirical_quantile(sorted_values: Sequence[float], level: float) -> float:
    """The `level` quantile of an already-sorted sample, by linear interpolation.

    Hyndman & Fan's type 7 — the definition numpy, R and pandas call the default,
    so the number here matches what a reader recomputing it elsewhere gets. The
    choice matters and is therefore declared rather than left to the
    implementation: the nine quantile definitions in that paper disagree by up to
    a whole order statistic on small samples. Polars is the exception worth
    naming: it defaults to `interpolation="nearest"`, so `pl.Series.quantile`
    without an argument returns a different number.
    """
    if not sorted_values:
        raise ValueError("no sample to take a quantile of.")
    if not 0.0 < level < 1.0:
        raise ValueError(f"a quantile level is strictly between 0 and 1, got {level}.")

    n = len(sorted_values)
    position = level * (n - 1)
    lower = int(position)
    upper = min(lower + 1, n - 1)
    weight = position - lower
    return sorted_values[lower] + weight * (sorted_values[upper] - sorted_values[lower])


def quantiles_from_sample(
    values: Sequence[float], levels: Sequence[float]
) -> dict[float, float]:
    """Every level's quantile from one sample, sorting once."""
    ordered = sorted(values)
    return {
        level: empirical_quantile(ordered, level)
        for level in sorted(set(levels))
    }


@dataclass(frozen=True)
class ErrorHistory:
    """The errors a baseline has already made at one step of the horizon.

    `first` is the panel position of the earliest error that could be computed —
    the first week with enough history behind it for this baseline. `values[k]`
    is the error made at position `first + k`, and the sequence is contiguous, so
    the errors visible from an origin are always a prefix.

    One history per step, not one per baseline: at step 4 a forecast is wrong by
    more than at step 1, and a single spread for the whole horizon would report
    the easier step's uncertainty at the harder step. The step is carried here so
    that the visibility bound cannot be got wrong by a caller.
    """

    first: int
    values: list[float]
    step: int

    def sample(self, origin_index: int) -> list[float]:
        """The errors whose target week had already been observed at the origin.

        The forecast made at position *t* for step *s* is scored on week `t + s`,
        so it is known at origin *i* only when `t + s <= i`. Everything after
        that is the future the origin is not allowed to have seen.
        """
        visible = origin_index - self.step - self.first + 1
        if visible <= 0:
            return []
        return self.values[:visible]


def error_histories(
    values: Sequence[float],
    horizon: int,
    forecast: Forecast,
    name: str | None = None,
) -> dict[int, ErrorHistory]:
    """Walk the whole panel once per step, recording what the baseline got wrong.

    Computed over the full panel rather than per origin because the errors do not
    depend on the origin: the error made at position *t* is a function of the
    weeks up to `t + step`, and later origins see it as one more observation.
    Sorting once and slicing a prefix is the whole of the per-origin cost.

    The first positions fail, because the baseline needs history before it can
    answer — the seasonal naive needs a season behind it. That prefix is skipped,
    and if no position succeeds the baseline's own complaint is re-raised rather
    than swallowed: a baseline that cannot forecast at all on this panel should
    say so, not produce an empty sample. `name` is how the complaint says *which*
    baseline, because the caller runs two of them and the reader should not have
    to guess.
    """
    who = name or "this baseline"
    histories: dict[int, ErrorHistory] = {}

    for step in range(1, horizon + 1):
        errors: list[float] = []
        first: int | None = None
        refusal: ValueError | None = None

        for position in range(len(values) - step):
            try:
                predicted = forecast(list(values[: position + 1]), horizon)[step - 1]
            except ValueError as exc:
                refusal = exc
                continue
            if first is None:
                first = position
            errors.append(values[position + step] - predicted)

        if first is None:
            # A recusa do próprio baseline vai na mensagem, e não só no `from`.
            # Um horizonte maior que a defasagem sazonal chega aqui como "nunca
            # previu nada neste painel", e o painel não tem culpa nenhuma — quem
            # lê precisa do motivo real para não tentar alargar o painel à toa.
            because = f" It refused every position, saying: {refusal}" if refusal else ""
            raise ValueError(
                f"{who} never produced a forecast at step {step} on a "
                f"panel of {len(values)} weeks at horizon {horizon}.{because}"
            ) from refusal
        histories[step] = ErrorHistory(first=first, values=errors, step=step)

    return histories


def predictive_quantiles(
    point: float,
    sample: Sequence[float],
    levels: Sequence[float],
    min_sample: int = MIN_ERROR_SAMPLE,
) -> dict[float, float] | None:
    """The predictive quantiles of a point forecast, or None if there is no sample.

    `None` and not an arbitrary number when the sample is too thin: a 0.025
    quantile read off five observations is not a measurement, and averaging it
    into a WIS would move the headline number for a reason no reader could see.
    The caller skips the origin instead, and `n_quantile` records how many weeks
    each baseline did reach the floor on.

    An empty sample is skipped whatever the floor says, because a quantile of
    nothing does not exist. Zero is a floor the flag accepts — it means "score as
    soon as one error has been observed" — so without this the very first origin
    of a baseline whose errors are not known yet would abort the run instead of
    being skipped like every other week below the floor.
    """
    if not sample or len(sample) < min_sample:
        return None
    centre = empirical_quantile(sorted(sample), 0.5)
    return {
        level: point + (value - centre)
        for level, value in quantiles_from_sample(sample, levels).items()
    }
