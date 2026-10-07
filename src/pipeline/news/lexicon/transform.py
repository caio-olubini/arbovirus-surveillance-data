"""Run the lexicon stage: frozen text corpus → weekly features (braço 01)."""

from __future__ import annotations

import gzip
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from .spec import (
    EW,
    LOCATION,
    NATIONAL_LOCATION,
    NEWS_VOLUME,
    OUTPUT_NAME,
)
from .steps import build, load_lexicon, load_uf_matcher

log = logging.getLogger("pipeline.news.lexicon")

FORMAT_PARQUET = "parquet"
FORMAT_CSV_GZ = "csv_gz"
DEFAULT_FORMATS = (FORMAT_PARQUET, FORMAT_CSV_GZ)


@dataclass
class NewsLexiconTransformResult:
    rows_out: int = 0
    failed: int = 0
    weeks: int = 0
    locations: int = 0
    articles: int = 0
    articles_in: int = 0
    uf_mentions: int = 0
    lexicon_version: int = 0
    outputs: list[Path] = field(default_factory=list)
    elapsed: float = 0.0

    def __str__(self) -> str:
        parts = [
            f"rows={self.rows_out:,}",
            f"failed={self.failed}",
            f"weeks={self.weeks:,}",
            f"locations={self.locations}",
            f"articles={self.articles:,}/{self.articles_in:,}",
            f"uf_mentions={self.uf_mentions:,}",
            f"lexicon=v{self.lexicon_version}",
            f"elapsed={self.elapsed:.1f}s",
        ]
        if self.outputs:
            parts.append(f"outputs={', '.join(p.name for p in self.outputs)}")
        return f"NewsLexiconTransformResult({', '.join(parts)})"


def transform(
    corpus_path: Path,
    lexicon_path: Path,
    fu_path: Path,
    out_dir: Path,
    require_disease_term: bool | None = None,
    portuguese_only: bool = True,
    formats: tuple[str, ...] | list[str] = DEFAULT_FORMATS,
) -> NewsLexiconTransformResult:
    """Score the frozen corpus with the PT-BR lexicon and aggregate by (ew, UF).

    `corpus_path` is the parquet written by `arboili transform news-text`.
    """
    started = time.monotonic()
    result = NewsLexiconTransformResult()

    if not corpus_path.exists():
        raise FileNotFoundError(
            f"News-text corpus not found: {corpus_path}. "
            f"Run `arboili transform news-text` first."
        )

    lexicon = load_lexicon(lexicon_path)
    matcher = load_uf_matcher(fu_path)
    corpus = pl.read_parquet(corpus_path)
    result.articles_in = corpus.height
    series = build(
        corpus,
        lexicon,
        matcher,
        require_disease_term=require_disease_term,
        portuguese_only=portuguese_only,
    )

    result.rows_out = series.height
    result.lexicon_version = lexicon.version
    if series.height:
        result.weeks = series[EW].n_unique()
        result.locations = series[LOCATION].n_unique()
        national = series.filter(pl.col(LOCATION) == NATIONAL_LOCATION)
        result.articles = int(national[NEWS_VOLUME].sum())
        result.uf_mentions = int(series[NEWS_VOLUME].sum()) - result.articles

    result.outputs = _write(series, out_dir, formats)
    result.elapsed = time.monotonic() - started
    log.info("news lexicon: %d rows written", series.height)
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
