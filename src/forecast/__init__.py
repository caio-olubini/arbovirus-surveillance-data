"""Forecast evaluation against the shared SINAN target series.

This package is the third sibling of `collection/` (which fetches) and
`pipeline/` (which transforms). Nothing here downloads or reshapes data: it
consumes the products those two build and answers the question the article is
actually about — **which representation of the news predicts dengue best**.

The order of work is fixed by protocol 00 (`notes/00-protocolo-comparacao.md`):
the naive baselines first, then the "no text" model, and only then the text
representations. That order exists because the number a representation has to
beat is the one without any news in it, and that number has to be computed
before any representation is compared against it.

Nothing in this package is a modelling choice yet. It holds the evaluation
harness — the target panel, the rolling origin, the metrics and the baselines —
which is the part every later model must share for a comparison to mean
anything.
"""

from __future__ import annotations

from .baselines import persistence, seasonal_naive
from .evaluate import ForecastRun, evaluate
from .metrics import mae, mape, rmse
from .panel import load_target
from .record import setup_record, write_record
from .splits import rolling_origin

__all__ = [
    "ForecastRun",
    "evaluate",
    "load_target",
    "mae",
    "mape",
    "persistence",
    "rmse",
    "rolling_origin",
    "seasonal_naive",
    "setup_record",
    "write_record",
]
