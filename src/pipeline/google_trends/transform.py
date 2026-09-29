"""Run the Google Trends search-index thin transform."""

from __future__ import annotations

import gzip
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from .spec import OUTPUT_NAME
from .steps import build

log = logging.getLogger("pipeline.google_trends")

FORMAT_PARQUET = "parquet"
FORMAT_CSV_GZ = "csv_gz"
DEFAULT_FORMATS = (FORMAT_PARQUET, FORMAT_CSV_GZ)


@dataclass
class GTrendsTransformResult:
    rows_out: int = 0
    failed: int = 0
    outputs: list[Path] = field(default_factory=list)
    elapsed: float = 0.0
    kept_br: bool = True

    def __str__(self) -> str:
        parts = [
            f"rows={self.rows_out:,}",
            f"failed={self.failed}",
            f"keep_br={self.kept_br}",
            f"elapsed={self.elapsed:.1f}s",
        ]
        if self.outputs:
            parts.append(f"outputs={', '.join(p.name for p in self.outputs)}")
        return f"GTrendsTransformResult({', '.join(parts)})"


def transform(
    input_path: Path,
    out_dir: Path,
    keep_br: bool = True,
    formats: tuple[str, ...] | list[str] = DEFAULT_FORMATS,
) -> GTrendsTransformResult:
    """Rename/validate GoogleTrends_search.csv → EW-keyed parquet + csv.gz."""
    started = time.monotonic()
    result = GTrendsTransformResult(kept_br=keep_br)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Google Trends search file not found: {input_path}. "
            f"Run `arboili gt-search` first."
        )

    series = build(input_path, keep_br=keep_br).collect()
    result.rows_out = series.height
    result.outputs = _write(series, out_dir, formats)
    result.elapsed = time.monotonic() - started
    log.info("gtrends: %d rows written", series.height)
    return result


def _write(
    series: pl.DataFrame, out_dir: Path, formats: tuple[str, ...] | list[str]
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fmt in formats:
        if fmt == FORMAT_PARQUET:
            path = out_dir / f"{OUTPUT_NAME}.parquet"
            series.write_parquet(path, compression="zstd")
        elif fmt == FORMAT_CSV_GZ:
            path = out_dir / f"{OUTPUT_NAME}.csv.gz"
            with gzip.open(path, "wb", compresslevel=6) as handle:
                series.write_csv(handle)
        else:
            raise ValueError(f"Unknown output format {fmt!r}; expected {DEFAULT_FORMATS}")
        log.info("wrote %s (%.1f MB)", path, path.stat().st_size / 1e6)
        written.append(path)
    return written
