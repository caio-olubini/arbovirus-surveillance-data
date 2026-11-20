"""Run the naive baselines and print the number every model has to beat.

    python -m src.forecast

The point of this entry point is to make the project's first result reachable in
one command. Everything else in the repository so far produces a *product* —
files that are correct or not. This produces a *measurement*, and a measurement
you cannot re-run in one line is one nobody will re-check.

The defaults are the ones protocol 00 fixes for the first pass: Brazil as a
whole, one week ahead, two years of history before the first forecast. Every one
of them is a flag, and every flag changes the numbers, so whatever is quoted in
a table has to say which flags produced it — which is why `--out` writes the
record of the run beside the results and not only the results.
"""

from __future__ import annotations

import argparse
import logging
import shlex
import sys
from pathlib import Path

import polars as pl

from ..config import load_config
from .evaluate import evaluate, format_metrics
from .panel import TargetGapError, load_target
from .record import setup_record, write_record
from .spec import (
    CASES,
    DEFAULT_HORIZON,
    DEFAULT_MIN_TRAIN,
    EW,
    FIRST_COMPLETE_YEAR,
    GEOGRAPHY,
)

log = logging.getLogger("forecast")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.forecast",
        description="Score the naive baselines on the shared dengue target series.",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=None,
        help="Case-level SINAN parquet written by `arboili transform sinan`. "
        "Defaults to the path in config.yml.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Directory for the result files (predictions, metrics, and the "
        "record of the setup that produced them). Omit to print only.",
    )
    parser.add_argument("--horizon", type=int, default=DEFAULT_HORIZON, help="Weeks ahead.")
    parser.add_argument(
        "--min-train",
        type=int,
        default=DEFAULT_MIN_TRAIN,
        help="Weeks of history before the first forecast.",
    )
    parser.add_argument(
        "--step",
        type=int,
        default=1,
        help="Walk origins forward by this many weeks instead of every week.",
    )
    parser.add_argument(
        "--from-year",
        type=int,
        default=FIRST_COMPLETE_YEAR,
        help="First year of the panel. The default skips 2013, which is incomplete.",
    )
    parser.add_argument("--to-year", type=int, default=None, help="Last year of the panel.")
    parser.add_argument(
        "--config", type=Path, default=None, help="Path to config.yml."
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def resolve_cases(path: Path | None, config_path: Path | None) -> Path:
    """The case-level parquet: the flag if given, else config.yml's sinan out_dir."""
    if path is not None:
        return path
    config = load_config(config_path)
    stage = config.pipeline("sinan")
    out_dir = config.resolve(stage.get("out_dir", "data/epidemiological/SINAN"))
    disease = stage.get("disease", "dengue")
    return out_dir / f"SINAN_{disease}_cases.parquet"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    cases_path = resolve_cases(args.cases, args.config)
    if not cases_path.exists():
        log.error(
            "Case table not found: %s\n"
            "Run `arboili transform sinan` first, or pass --cases.",
            cases_path,
        )
        return 1

    try:
        panel = load_target(
            str(cases_path), from_year=args.from_year, to_year=args.to_year
        )
    except TargetGapError as exc:
        log.error("%s", exc)
        return 1

    run = evaluate(
        panel,
        horizon=args.horizon,
        min_train=args.min_train,
        step=args.step,
    )

    first, last = panel[EW].min(), panel[EW].max()
    print(
        f"Target: suspected dengue cases, Brazil, {panel.height} weeks "
        f"({first} → {last}), {panel[CASES].sum():,} cases total."
    )
    print(
        f"Setup: horizon {run.horizon} week(s), first forecast after "
        f"{run.min_train} weeks of history, {run.predictions.height:,} scored "
        f"week-forecasts."
    )
    print()
    print(run.summary())
    print()

    if args.out:
        out_dir = load_config(args.config).resolve(args.out) if not args.out.is_absolute() else args.out
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = f"dengue_{GEOGRAPHY.lower()}_h{run.horizon}"
        pred_path = out_dir / f"{stem}_predictions.parquet"
        metrics_path = out_dir / f"{stem}_metrics.parquet"
        record_path = out_dir / f"{stem}_run.json"
        run.predictions.write_parquet(pred_path)
        run.metrics.write_parquet(metrics_path)
        # The two parquets carry the result; the record carries the setup that
        # produced it, which is the half a table cannot reconstruct later.
        write_record(
            setup_record(panel, run, cases_path),
            record_path,
            command=shlex.join(
                ["python", "-m", "src.forecast", *(argv if argv is not None else sys.argv[1:])]
            ),
        )
        print(f"Wrote {pred_path}")
        print(f"Wrote {metrics_path}")
        print(f"Wrote {record_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
