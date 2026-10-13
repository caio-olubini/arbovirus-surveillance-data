"""Run the embeddings stage: frozen corpus → dense per-article and weekly tables.

Two outputs, because pooling is lossy: the per-article table is what any later
re-pooling, chunking or error analysis needs, and it is the one that costs the
inference. Re-pooling from it is seconds; re-encoding is the whole run.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from ..corpus import select_articles as _select_articles
from ..lexicon.steps import load_lexicon, load_uf_matcher
from .spec import (
    ARTICLE_OUTPUT_NAME,
    DEFAULT_FORMATS,
    FORMAT_PARQUET,
    MODEL_NAME,
    MODEL_REVISION_SHA,
    OUTPUT_NAME,
)
from .steps import (
    DEFAULT_BATCH_SIZE,
    Encoder,
    encode_articles,
    load_encoder,
    pool_by_week,
    scoped_locations,
    truncation_stats,
)

log = logging.getLogger("pipeline.news.embeddings")


@dataclass
class NewsEmbeddingsTransformResult:
    articles_in: int = 0
    articles: int = 0
    skipped: int = 0
    # Structural, and always 0 today: a batch that fails to encode raises out of
    # `transform()` rather than being dropped and counted. The field is here
    # because `cli.main` reads `result.failed` for the exit code on every
    # transform, and a stage that silently lacks it crashes *after* writing its
    # outputs — which is exactly what happened the first time this ran.
    failed: int = 0
    truncated: int = 0
    longest_tokens: int = 0
    rows_out: int = 0
    weeks: int = 0
    locations: int = 0
    model_id: str = ""
    model_revision: str = ""
    dim: int = 0
    outputs: list[Path] = field(default_factory=list)
    elapsed: float = 0.0

    def __str__(self) -> str:
        parts = [
            f"articles={self.articles:,}/{self.articles_in:,}",
            f"skipped={self.skipped:,}",
            f"failed={self.failed}",
            f"rows={self.rows_out:,}",
            f"weeks={self.weeks:,}",
            f"locations={self.locations}",
            f"model={self.model_id}@{self.model_revision[:8]}",
            f"dim={self.dim}",
            f"truncated={self.truncated:,}/{self.articles:,} (max {self.longest_tokens:,} tokens)",
            f"elapsed={self.elapsed:.1f}s",
        ]
        if self.outputs:
            parts.append(f"outputs={', '.join(p.name for p in self.outputs)}")
        return f"NewsEmbeddingsTransformResult({', '.join(parts)})"


def select_articles(
    corpus: pl.DataFrame,
    lexicon,
    portuguese_only: bool = True,
    require_disease_term: bool = True,
) -> tuple[pl.DataFrame, int]:
    """Re-exported from `news.corpus`, where braço 03 can reach it too.

    Kept as a name here because braço 02's tests and notebook import it from this
    module; the implementation and its rationale live in the shared module.
    """
    return _select_articles(
        corpus,
        lexicon,
        portuguese_only=portuguese_only,
        require_disease_term=require_disease_term,
    )


def transform(
    corpus_path: Path,
    fu_path: Path,
    lexicon_path: Path,
    out_dir: Path,
    model_name: str = MODEL_NAME,
    model_revision: str = MODEL_REVISION_SHA,
    batch_size: int = DEFAULT_BATCH_SIZE,
    portuguese_only: bool = True,
    require_disease_term: bool = True,
    normalize: bool = True,
    formats: tuple[str, ...] | list[str] = DEFAULT_FORMATS,
    encoder: Encoder | None = None,
) -> NewsEmbeddingsTransformResult:
    """Encode the frozen corpus and pool it to (ew, location).

    `corpus_path` is the parquet written by `arboili transform news-text`.
    `encoder` is injectable so tests and the walkthrough notebook can drive the
    aggregation without downloading the checkpoint; production passes nothing and
    gets the pinned BERTimbau.
    """
    started = time.monotonic()
    result = NewsEmbeddingsTransformResult()

    if not corpus_path.exists():
        raise FileNotFoundError(
            f"News-text corpus not found: {corpus_path}. "
            f"Run `arboili transform news-text` first."
        )

    corpus = pl.read_parquet(corpus_path)
    result.articles_in = corpus.height

    lexicon = load_lexicon(lexicon_path)
    matcher = load_uf_matcher(fu_path)
    kept, dropped = select_articles(
        corpus,
        lexicon,
        portuguese_only=portuguese_only,
        require_disease_term=require_disease_term,
    )
    result.skipped = dropped
    result.articles = kept.height

    if encoder is None:
        encoder = load_encoder(model_name, model_revision, normalize=normalize)
    result.model_id = encoder.model_id
    result.model_revision = encoder.model_revision
    result.dim = encoder.dim

    articles = encode_articles(kept, encoder, batch_size=batch_size)
    result.truncated, result.longest_tokens = truncation_stats(articles)

    pooled = pool_by_week(articles, scoped_locations(kept, matcher), encoder.dim)
    result.rows_out = pooled.height
    if pooled.height:
        result.weeks = pooled["ew"].n_unique()
        result.locations = pooled["location"].n_unique()

    result.outputs = _write(articles, pooled, out_dir, formats)
    result.elapsed = time.monotonic() - started
    log.info("news embeddings: %d articles, %d pooled rows", articles.height, pooled.height)
    return result


def _write(
    articles: pl.DataFrame,
    pooled: pl.DataFrame,
    out_dir: Path,
    formats: tuple[str, ...] | list[str],
) -> list[Path]:
    """Parquet only. A csv.gz of a 768-float column is enormous and lossy."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fmt in formats:
        if fmt != FORMAT_PARQUET:
            raise ValueError(
                f"Unknown output format {fmt!r}; braço 02 writes {DEFAULT_FORMATS} "
                f"only (a dense embedding does not survive csv text form)."
            )
        for frame, name in ((articles, ARTICLE_OUTPUT_NAME), (pooled, OUTPUT_NAME)):
            path = out_dir / f"{name}.parquet"
            frame.write_parquet(path, compression="zstd")
            log.info("wrote %s (%.1f MB)", path, path.stat().st_size / 1e6)
            written.append(path)
    return written


__all__ = [
    "NewsEmbeddingsTransformResult",
    "select_articles",
    "transform",
]
