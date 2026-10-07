"""Run the news-text stage: saved EBC HTML → the frozen text corpus."""

from __future__ import annotations

import gzip
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from .spec import CHAR_COUNT, ERA, EXTRACTOR, MIN_CHARS, OUTPUT_NAME
from .steps import bodyless_expr, build, missing_article_files

log = logging.getLogger("pipeline.news.text")

FORMAT_PARQUET = "parquet"
FORMAT_CSV_GZ = "csv_gz"
DEFAULT_FORMATS = (FORMAT_PARQUET, FORMAT_CSV_GZ)


@dataclass
class NewsTextTransformResult:
    articles: int = 0
    failed: int = 0
    short: int = 0
    bodyless: int = 0
    era_counts: dict[str, int] = field(default_factory=dict)
    extractor_counts: dict[str, int] = field(default_factory=dict)
    outputs: list[Path] = field(default_factory=list)
    elapsed: float = 0.0

    def __str__(self) -> str:
        parts = [
            f"articles={self.articles:,}",
            f"failed={self.failed}",
            f"short={self.short}",
            f"bodyless={self.bodyless}",
        ]
        if self.era_counts:
            eras = " ".join(f"{k}={v:,}" for k, v in sorted(self.era_counts.items()))
            parts.append(f"eras[{eras}]")
        if self.extractor_counts:
            rules = " ".join(
                f"{k}={v:,}" for k, v in sorted(self.extractor_counts.items())
            )
            parts.append(f"rules[{rules}]")
        parts.append(f"elapsed={self.elapsed:.1f}s")
        if self.outputs:
            parts.append(f"outputs={', '.join(p.name for p in self.outputs)}")
        return f"NewsTextTransformResult({', '.join(parts)})"


def transform(
    root: Path,
    out_dir: Path,
    formats: tuple[str, ...] | list[str] = DEFAULT_FORMATS,
) -> NewsTextTransformResult:
    """Extract every article under `root` and write the frozen text corpus.

    `root` is the query directory the scraper wrote, e.g. `data/news/dengue` —
    it must hold `articles/` and `manifest.jsonl`.
    """
    started = time.monotonic()
    result = NewsTextTransformResult()

    if not root.exists():
        raise FileNotFoundError(
            f"EBC query directory not found: {root}. Run `arboili ebc` first."
        )

    corpus = build(root)
    result.articles = corpus.height
    result.failed = len(missing_article_files(root))
    # Era and rule counts are reported rather than asserted: they are the only
    # cheap signal that the extraction still lands on the right container.
    result.era_counts = dict(corpus.group_by(ERA).len().iter_rows())
    result.extractor_counts = dict(corpus.group_by(EXTRACTOR).len().iter_rows())
    # `short` is a length regression; `bodyless` is a page saved without its
    # body. Separate counts, because only the first is a defect in this stage.
    result.bodyless = corpus.filter(bodyless_expr()).height
    result.short = corpus.filter(
        ~bodyless_expr() & (pl.col(CHAR_COUNT) < MIN_CHARS)
    ).height
    result.outputs = _write(corpus, out_dir, formats)
    result.elapsed = time.monotonic() - started
    log.info("news text: %d articles written", corpus.height)
    return result


def _write(
    corpus: pl.DataFrame, out_dir: Path, formats: tuple[str, ...] | list[str]
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fmt in formats:
        if fmt == FORMAT_PARQUET:
            path = out_dir / f"{OUTPUT_NAME}.parquet"
            corpus.write_parquet(path, compression="zstd")
        elif fmt == FORMAT_CSV_GZ:
            path = out_dir / f"{OUTPUT_NAME}.csv.gz"
            with gzip.open(path, "wb", compresslevel=6) as handle:
                corpus.write_csv(handle)
        else:
            raise ValueError(f"Unknown output format {fmt!r}; expected {DEFAULT_FORMATS}")
        log.info("wrote %s (%.1f MB)", path, path.stat().st_size / 1e6)
        written.append(path)
    return written
