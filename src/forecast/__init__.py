"""Forecast evaluation against the shared SINAN target series.

This package is the third sibling of `collection/` (which fetches) and
`pipeline/` (which transforms). Nothing here downloads or reshapes data: it
consumes the products those two build and answers the question the article is
actually about — **whether feature sets carry signal about dengue beyond the
simpler ones they are added to**.

The order of work is fixed by protocol 00 (`notes/00-protocolo-comparacao.md`):
the naive baselines first, then the "no text" model, and only then the text
representations. That order exists because the number a feature set has to beat
is the one without it, and that number has to be computed before anything is
compared against it.

Nothing in this package is a modelling choice yet. It holds the evaluation
harness — the target panel, the rolling origin, the metrics, the quantile grid
and the baselines — which is the part every later model must share for a
comparison to mean anything.
"""

from __future__ import annotations

from .baselines import persistence, seasonal_naive
from .evaluate import ForecastRun, evaluate
from .interval import empirical_quantile, error_histories, predictive_quantiles
from .metrics import coverage, interval_score, interval_width, mae, mape, pinball, rmse, wis
from .panel import load_target
from .record import setup_record, write_record
from .splits import rolling_origin

__all__ = [
    "ForecastRun",
    "coverage",
    "empirical_quantile",
    "error_histories",
    "evaluate",
    "interval_score",
    "interval_width",
    "load_target",
    "mae",
    "mape",
    "persistence",
    "pinball",
    "predictive_quantiles",
    "rmse",
    "rolling_origin",
    "seasonal_naive",
    "setup_record",
    "wis",
    "write_record",
]
