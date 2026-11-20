"""The rolling-origin loop: the machine that turns a panel into a number.

This is the piece the rest of the project plugs into. A baseline or a model
enters as a function of the history and leaves as a table of one row per scored
week, and every number in the paper comes out of that table. Nothing here knows
what a baseline does; adding braço 01 later is a registry entry, not a rewrite.

The contract that makes the comparison trustworthy is in `splits.py` — at origin
*i* the caller may read the panel up to position *i* and nothing after. Here the
loop simply never hands over more than that: the history passed to each baseline
is a slice that ends at the origin.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from .baselines import BASELINE_FUNCS
from .metrics import mae, mape, mape_denominator, rmse
from .spec import (
    BASELINE,
    BASELINES,
    CASES,
    DEFAULT_HORIZON,
    DEFAULT_MIN_TRAIN,
    EW,
    HORIZON,
)
from .splits import rolling_origin

# Result column names, kept here so a reader of the parquet knows what to expect.
ORIGIN_EW = "origin_ew"
TRUE = "y_true"
PRED = "y_pred"
N = "n"
MEAN_TRUTH = "mean_truth"
MAPE_N = "mape_n"
MAE = "mae"
RMSE = "rmse"
MAPE = "mape"


@dataclass(frozen=True)
class ForecastRun:
    """One evaluation: what was predicted, week by week, and how wrong it was.

    `predictions` keeps every scored week so a bad average can be traced back to
    the weeks that caused it — an epidemic peak missed by a wide margin is a
    different finding from uniform noise, and only the row-level table can tell
    them apart.

    `metrics` is the summary, grouped by baseline and by horizon step. With
    several steps ahead the grouping matters: step 1 and step 4 are different
    questions and averaging them into one number hides which one degraded.
    """

    predictions: pl.DataFrame
    metrics: pl.DataFrame
    horizon: int
    min_train: int
    step: int
    baselines: tuple[str, ...]

    def summary(self) -> str:
        """The metrics table as plain text, for a terminal or a notebook cell."""
        return format_metrics(self.metrics)


def format_metrics(metrics: pl.DataFrame) -> str:
    """Render the metrics table as aligned text.

    Polars' own repr truncates, and a truncated MAE is exactly the kind of thing
    that gets copied into a slide wrong, so the table is formatted by hand.
    """
    header = ("baseline", "step", "weeks", "MAE", "RMSE", "MAPE", "MAPE n")
    rows = [
        (
            row[BASELINE],
            str(row[HORIZON]),
            str(row[N]),
            f"{row[MAE]:,.0f}",
            f"{row[RMSE]:,.0f}",
            f"{row[MAPE] * 100:,.1f}%",
            str(row[MAPE_N]),
        )
        for row in metrics.iter_rows(named=True)
    ]
    widths = [
        max(len(header[i]), *(len(r[i]) for r in rows)) if rows else len(header[i])
        for i in range(len(header))
    ]
    lines = [
        "  ".join(h.rjust(w) for h, w in zip(header, widths)),
        "  ".join("-" * w for w in widths),
    ]
    lines += ["  ".join(c.rjust(w) for c, w in zip(r, widths)) for r in rows]
    return "\n".join(lines)


def evaluate(
    panel: pl.DataFrame,
    baselines: tuple[str, ...] = BASELINES,
    horizon: int = DEFAULT_HORIZON,
    min_train: int = DEFAULT_MIN_TRAIN,
    step: int = 1,
) -> ForecastRun:
    """Score every baseline at every origin in the panel.

    `panel` must come from `panel.load_target`: the loop indexes by position, so
    a missing week would make the seasonal baseline read the wrong reference week
    without raising. That guarantee is the panel's job, not this function's.

    `step` walks the origins forward by more than one week when the run is too
    slow to do every week. It changes which weeks are scored and therefore the
    numbers, so it is recorded on the run and belongs in any table that quotes
    them.
    """
    unknown = [name for name in baselines if name not in BASELINE_FUNCS]
    if unknown:
        raise ValueError(
            f"unknown baseline(s): {unknown}. Known: {sorted(BASELINE_FUNCS)}."
        )
    if not baselines:
        raise ValueError("no baselines to evaluate.")

    values = [float(v) for v in panel[CASES].to_list()]
    rows: list[dict] = []

    for origin in rolling_origin(panel, min_train=min_train, horizon=horizon, step=step):
        history = values[: origin.train_end]
        target_indices = list(origin.target_indices())

        for name in baselines:
            forecast = BASELINE_FUNCS[name](history, horizon)
            for offset, predicted in zip(target_indices, forecast):
                rows.append(
                    {
                        ORIGIN_EW: origin.ew,
                        EW: panel[EW][offset],
                        HORIZON: offset - origin.index,
                        BASELINE: name,
                        TRUE: values[offset],
                        PRED: predicted,
                    }
                )

    if not rows:
        raise ValueError(
            "no origin produced a forecast; the panel is shorter than min_train "
            "plus horizon."
        )

    predictions = pl.DataFrame(rows).sort([BASELINE, HORIZON, EW])

    summaries = []
    for (name, h), group in predictions.group_by([BASELINE, HORIZON], maintain_order=True):
        truth = group[TRUE].to_list()
        pred = group[PRED].to_list()
        summaries.append(
            {
                BASELINE: name,
                HORIZON: h,
                N: len(truth),
                MEAN_TRUTH: sum(truth) / len(truth),
                MAE: mae(truth, pred),
                RMSE: rmse(truth, pred),
                MAPE: mape(truth, pred),
                MAPE_N: mape_denominator(truth),
            }
        )

    metrics = pl.DataFrame(summaries).sort([BASELINE, HORIZON])
    return ForecastRun(
        predictions=predictions,
        metrics=metrics,
        horizon=horizon,
        min_train=min_train,
        step=step,
        baselines=tuple(baselines),
    )
