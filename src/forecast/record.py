"""The setup a result table was produced with.

Protocol 00 rests on one premise: a number quoted in the paper has to say which
knobs produced it, because a comparison is only a comparison while everything
except the representation is held fixed. `--out` writes the predictions and the
summary, and the summary carries the horizon and the baseline — but not the first
week of the panel, not how many weeks of history the first forecast had, and not
how far the origins moved between one forecast and the next. Read that file in
six months and there is no way to tell whether the history was 104 weeks or 200,
and the difference between those two numbers is not small.

So the missing half is written beside the results, as JSON.

Nothing here depends on when the run happened. Two runs of the same command write
the same bytes, and that is what makes the file worth comparing: a record that
differs means a flag differed.
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from .evaluate import ORIGIN_EW, ForecastRun
from .spec import CASES, EW, GEOGRAPHY

# Bumped when a key is renamed or removed, so a reader can tell a missing key
# from a key that was never there.
SCHEMA = "forecast.run/1"


def setup_record(
    panel: pl.DataFrame,
    run: ForecastRun,
    cases_path: str | Path,
) -> dict:
    """The settings a result table has to travel with.

    The flags alone are not enough and the run alone is not enough. `min_train`
    is a count of weeks, so it says nothing until the panel says which weeks those
    were; two panels of different length can carry the same `min_train` and score
    different periods. Both go in.
    """
    first, last = panel[EW].min(), panel[EW].max()
    return {
        "schema": SCHEMA,
        "target": {
            "source": str(cases_path),
            "geography": GEOGRAPHY,
            "weeks": panel.height,
            "first_week": first.isoformat(),
            "last_week": last.isoformat(),
            "total_cases": int(panel[CASES].sum()),
        },
        "evaluation": {
            "horizon": run.horizon,
            "min_train": run.min_train,
            "step": run.step,
            "baselines": list(run.baselines),
            "origins": run.predictions[ORIGIN_EW].n_unique(),
            "scored": run.predictions.height,
        },
    }


def write_record(record: dict, path: str | Path, command: str | None = None) -> Path:
    """Write the record, with the command that produced it when one is known.

    The command is added here rather than in `setup_record` because it belongs to
    the caller: a notebook that calls `evaluate` directly has no command line, and
    an empty one would read as a command that was lost.
    """
    if command is not None:
        record = {**record, "command": command}
    path = Path(path)
    path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path
