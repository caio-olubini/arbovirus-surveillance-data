"""Run the Google Trends related topics/queries thin transform."""

from __future__ import annotations

import gzip
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from .related_steps import RelatedSource, build_queries, build_topics
from .spec import QUERY_OUTPUT_NAME, SOURCE, TOPIC_OUTPUT_NAME

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
    topic_rows_by_source: dict[str, int] = field(default_factory=dict)
    query_rows_by_source: dict[str, int] = field(default_factory=dict)
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
        if self.topic_rows_by_source:
            parts.append(f"topics_by_source={_fmt_sources(self.topic_rows_by_source)}")
        if self.query_rows_by_source:
            parts.append(f"queries_by_source={_fmt_sources(self.query_rows_by_source)}")
        if self.outputs:
            parts.append(f"outputs={', '.join(p.name for p in self.outputs)}")
        if self.notes:
            parts.append(f"notes={'; '.join(self.notes)}")
        return f"GTrendsRelatedTransformResult({', '.join(parts)})"


def _fmt_sources(counts: dict[str, int]) -> str:
    return ", ".join(f"{name}={count:,}" for name, count in sorted(counts.items()))


def _counts_by_source(frame: pl.DataFrame) -> dict[str, int]:
    if frame.height == 0:
        return {}
    return {
        str(name): int(count)
        for name, count in frame.group_by(SOURCE)
        .len()
        .sort(SOURCE)
        .iter_rows()
    }


def _existing(sources: Sequence[RelatedSource]) -> list[RelatedSource]:
    return [s for s in sources if s.path.exists()]


def transform_related(
    topic_sources: Sequence[RelatedSource],
    query_sources: Sequence[RelatedSource],
    out_dir: Path,
    keep_br: bool = True,
    drop_empty: bool = True,
    formats: tuple[str, ...] | list[str] = DEFAULT_FORMATS,
) -> GTrendsRelatedTransformResult:
    """Reshape related CSVs → monthly parquet + csv.gz (partial extracts OK).

    Accepts more than one input per table — the frozen Zenodo seed plus this
    repo's own extractor output — concatenates them, tags every row with the
    ``source`` it came from, and keeps one row per group key using
    ``spec.SOURCE_PRECEDENCE``. Missing inputs are a note, not an error, so a
    partial extract still transforms.
    """
    started = time.monotonic()
    result = GTrendsRelatedTransformResult(kept_br=keep_br, dropped_empty=drop_empty)

    topics_present = _existing(topic_sources)
    queries_present = _existing(query_sources)

    for missing in [s for s in topic_sources if s not in topics_present]:
        result.notes.append(f"topics input missing: {missing.path}")
    for missing in [s for s in query_sources if s not in queries_present]:
        result.notes.append(f"queries input missing: {missing.path}")

    if not topics_present and not queries_present:
        raise FileNotFoundError(
            "No related topics or queries CSV found. Run `arboili gt-related` "
            "first (resumable; may be incomplete), or check the frozen seed "
            "path in config.yml."
        )

    if topics_present:
        topics = build_topics(
            topics_present, keep_br=keep_br, drop_empty=drop_empty
        ).collect()
        result.topic_rows = topics.height
        result.topic_rows_by_source = _counts_by_source(topics)
        result.outputs.extend(_write(topics, out_dir, TOPIC_OUTPUT_NAME, formats))
        if topics.height == 0:
            result.notes.append(
                "topics table empty after drop_empty — extract may only have placeholder rows"
            )
        log.info("gt-related topics: %d rows", topics.height)
    else:
        result.notes.append("no topics input available")

    if queries_present:
        queries = build_queries(
            queries_present, keep_br=keep_br, drop_empty=drop_empty
        ).collect()
        result.query_rows = queries.height
        result.query_rows_by_source = _counts_by_source(queries)
        result.outputs.extend(_write(queries, out_dir, QUERY_OUTPUT_NAME, formats))
        log.info("gt-related queries: %d rows", queries.height)
    else:
        result.notes.append("no queries input available")

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
