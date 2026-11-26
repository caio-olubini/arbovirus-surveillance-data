"""Roda os baselines ingênuos e imprime o número que todo modelo tem que bater.

    python -m src.forecast

O ponto deste ponto de entrada é tornar o primeiro resultado do projeto
alcançável em um comando. Todo o resto do repositório até aqui produz um
*produto* — arquivos que estão certos ou não. Isto produz uma *medição*, e uma
medição que não se re-executa numa linha é uma que ninguém vai reconferir.

Os padrões são os que o protocolo 00 fixa para a primeira passada: o Brasil
inteiro, uma semana à frente, dois anos de histórico antes da primeira previsão.
Cada um deles é uma flag, e cada flag muda os números, então o que for citado numa
tabela tem que dizer quais flags o produziram — e é por isso que `--out` escreve o
registro da execução ao lado dos resultados, em vez de gravar só os resultados.
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
    MIN_ERROR_SAMPLE,
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
        "--score-from",
        type=int,
        default=None,
        help="First year whose weeks are scored. The panel — and so the history "
        "the first forecast may read — still starts at --from-year; only the "
        "grading moves. Omit to score every week the panel reaches.",
    )
    parser.add_argument(
        "--min-error-sample",
        type=int,
        default=MIN_ERROR_SAMPLE,
        help="Observed errors a baseline needs before its distribution is scored. "
        "Below this the week is skipped in the probabilistic tables only.",
    )
    parser.add_argument(
        "--config", type=Path, default=None, help="Path to config.yml."
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def resolve_cases(path: Path | None, config_path: Path | None) -> Path:
    """O parquet em nível de caso: a flag se dada, senão o out_dir do sinan no config."""
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
        score_from=args.score_from,
        min_error_sample=args.min_error_sample,
    )

    first, last = panel[EW].min(), panel[EW].max()
    print(
        f"Target: suspected dengue cases, Brazil, {panel.height} weeks "
        f"({first} → {last}), {panel[CASES].sum():,} cases total."
    )
    scoring = (
        "every week the panel reaches"
        if run.score_from is None
        else f"weeks from {run.score_from} onward"
    )
    print(
        f"Setup: horizon {run.horizon} week(s), first forecast after "
        f"{run.min_train} weeks of history, scoring {scoring}, "
        f"{run.predictions.height:,} scored week-forecasts."
    )
    print()
    print(run.summary())
    print()
    print(run.distribution_summary())
    print()

    if args.out:
        out_dir = load_config(args.config).resolve(args.out) if not args.out.is_absolute() else args.out
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = f"dengue_{GEOGRAPHY.lower()}_h{run.horizon}"
        pred_path = out_dir / f"{stem}_predictions.parquet"
        metrics_path = out_dir / f"{stem}_metrics.parquet"
        quantile_path = out_dir / f"{stem}_quantiles.parquet"
        interval_path = out_dir / f"{stem}_intervals.parquet"
        record_path = out_dir / f"{stem}_run.json"
        run.predictions.write_parquet(pred_path)
        run.metrics.write_parquet(metrics_path)
        run.quantile_predictions.write_parquet(quantile_path)
        run.intervals.write_parquet(interval_path)
        # Os parquets carregam o resultado; o registro carrega a montagem que o
        # produziu, que é a metade que uma tabela não reconstrói depois.
        write_record(
            setup_record(panel, run, cases_path),
            record_path,
            command=shlex.join(
                ["python", "-m", "src.forecast", *(argv if argv is not None else sys.argv[1:])]
            ),
        )
        print(f"Wrote {pred_path}")
        print(f"Wrote {metrics_path}")
        print(f"Wrote {quantile_path}")
        print(f"Wrote {interval_path}")
        print(f"Wrote {record_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
