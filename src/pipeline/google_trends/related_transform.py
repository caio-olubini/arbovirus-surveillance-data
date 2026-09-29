"""Run the Google Trends related topics/queries thin transform."""

from __future__ import annotations

import gzip
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from .related_steps import build_queries, build_topics
from .spec import QUERY_OUTPUT_NAME, TOPIC_OUTPUT_NAME

log = logging.getLogger("pipeline.google_trends.related")

FORMAT_PARQUET = "parquet"
FORMAT_CSV_GZ = "csv_gz"
DEFAULT_FORMATS = (FORMAT_PARQUET, FORMAT_CSV_GZ)


@dataclass
class GTrendsRelatedTransformResult:
    topic_rows: int = 0
    query_rows: int = 0
    failed: int = 0
    outputs: list[Path] = field(default_factory=list)
    elapsed: float = 0.0
    kept_br: bool = True
    dropped_empty: bool = True
    notes: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        parts = [
            f"topics={self.topic_rows:,}",
            f"queries={self.query_rows:,}",
            f"failed={self.failed}",
            f"keep_br={self.kept_br}",
            f"drop_empty={self.dropped_empty}",
            f"elapsed={self.elapsed:.1f}s",
        ]
        if self.outputs:
            parts.append(f"outputs={', '.join(p.name for p in self.outputs)}")
        if self.notes:
            parts.append(f"notes={'; '.join(self.notes)}")
        return f"GTrendsRelatedTransformResult({', '.join(parts)})"


def transform_related(
    topics_path: Path | None,
    queries_path: Path | None,
    out_dir: Path,
    keep_br: bool = True,
    drop_empty: bool = True,
    formats: tuple[str, ...] | list[str] = DEFAULT_FORMATS,
) -> GTrendsRelatedTransformResult:
    """Reshape related CSVs → monthly parquet + csv.gz (partial extracts OK)."""
    started = time.monotonic()
    result = GTrendsRelatedTransformResult(kept_br=keep_br, dropped_empty=drop_empty)

    topics_ok = topics_path is not None and topics_path.exists()
    queries_ok = queries_path is not None and queries_path.exists()
    if not topics_ok and not queries_ok:
        raise FileNotFoundError(
            "Neither related topics nor related queries CSV found. "
            "Run `arboili gt-related` first (resumable; may be incomplete)."
        )

    if topics_ok:
        assert topics_path is not None
        topics = build_topics(topics_path, keep_br=keep_br, drop_empty=drop_empty).collect()
        result.topic_rows = topics.height
        result.outputs.extend(_write(topics, out_dir, TOPIC_OUTPUT_NAME, formats))
        if topics.height == 0:
            result.notes.append(
                "topics table empty after drop_empty — extract may only have placeholder rows"
            )
        log.info("gt-related topics: %d rows", topics.height)
    else:
        result.notes.append(f"topics input missing: {topics_path}")

    if queries_ok:
        assert queries_path is not None
        queries = build_queries(queries_path, keep_br=keep_br, drop_empty=drop_empty).collect()
        result.query_rows = queries.height
        result.outputs.extend(_write(queries, out_dir, QUERY_OUTPUT_NAME, formats))
        log.info("gt-related queries: %d rows", queries.height)
    else:
        result.notes.append(f"queries input missing: {queries_path}")

    result.elapsed = time.monotonic() - started
    return result


def _write(
    series: pl.DataFrame,
    out_dir: Path,
    stem: str,
    formats: tuple[str, ...] | list[str],
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fmt in formats:
        if fmt == FORMAT_PARQUET:
            path = out_dir / f"{stem}.parquet"
            series.write_parquet(path, compression="zstd")
        elif fmt == FORMAT_CSV_GZ:
            path = out_dir / f"{stem}.csv.gz"
            with gzip.open(path, "wb", compresslevel=6) as handle:
                series.write_csv(handle)
        else:
            raise ValueError(f"Unknown output format {fmt!r}; expected {DEFAULT_FORMATS}")
        log.info("wrote %s (%.1f MB)", path, path.stat().st_size / 1e6)
        written.append(path)
    return written
