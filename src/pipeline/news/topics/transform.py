"""Run the topics stage: frozen corpus → weekly topic shares, topic terms, sweep.

Three outputs, and the third is what makes the first two checkable. The shares are
the covariate the forecaster consumes; the meta table says what each topic *is*;
the sweep table is the evidence for the k that both were built at. `notes/03` says
the choice of k is itself a result worth reporting, so it is written out rather
than left in a log.
"""

from __future__ import annotations

import gzip
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from ..corpus import scoped_locations, select_articles
from ..lexicon.steps import load_lexicon, load_uf_matcher
from .spec import (
    COHERENCE_METRIC,
    COVARIATE_GRAIN,
    DEFAULT_FAMILY,
    DEFAULT_FORMATS,
    DEFAULT_ITERATIONS,
    DEFAULT_SEED,
    FORMAT_CSV_GZ,
    FORMAT_PARQUET,
    K_RANGE,
    META_OUTPUT_NAME,
    MIN_DF,
    OUTPUT_NAME,
    SWEEP_OUTPUT_NAME,
    TOP_TERMS,
)
from .steps import (
    ModelFactory,
    article_frame,
    covariate_bucket,
    load_model_factory,
    pool_shares,
    select_k,
    sweep_table,
    tokenize_corpus,
    topic_meta,
)

log = logging.getLogger("pipeline.news.topics")


@dataclass
class NewsTopicsTransformResult:
    articles_in: int = 0
    articles: int = 0
    skipped: int = 0
    # Structural, and always 0 today: a model that fails to fit raises out of
    # `transform()` rather than being dropped and counted. The field is here
    # because `cli.main` reads `result.failed` for the exit code on every
    # transform, and a stage that silently lacks it crashes *after* writing its
    # outputs — which is exactly what braço 02 did the first time it ran.
    failed: int = 0
    # Documents whose tokens were all stopwords. They still count toward
    # `n_articles` (the article set is protocol-00 common ground) and carry a
    # uniform share row, so this is reported rather than silently absorbed.
    empty_docs: int = 0
    topics: int = 0
    family: str = ""
    coherence: float = 0.0
    model_id: str = ""
    sweep: list[tuple[int, float, float]] = field(default_factory=list)
    rows_out: int = 0
    weeks: int = 0
    locations: int = 0
    outputs: list[Path] = field(default_factory=list)
    elapsed: float = 0.0

    def __str__(self) -> str:
        sweep = " ".join(f"k={k}:{coh:.3f}" for k, coh, _ in self.sweep)
        parts = [
            f"articles={self.articles:,}/{self.articles_in:,}",
            f"skipped={self.skipped:,}",
            f"failed={self.failed}",
            f"model={self.model_id}",
            f"topics={self.topics}",
            f"coherence={self.coherence:.4f}",
            f"sweep=[{sweep}]",
            f"empty_docs={self.empty_docs}",
            f"rows={self.rows_out:,}",
            f"weeks={self.weeks:,}",
            f"locations={self.locations}",
            f"elapsed={self.elapsed:.1f}s",
        ]
        if self.outputs:
            parts.append(f"outputs={', '.join(p.name for p in self.outputs)}")
        return f"NewsTopicsTransformResult({', '.join(parts)})"


def transform(
    corpus_path: Path,
    fu_path: Path,
    lexicon_path: Path,
    out_dir: Path,
    k_range: tuple[int, ...] | list[int] = K_RANGE,
    grain: str = COVARIATE_GRAIN,
    family: str = DEFAULT_FAMILY,
    seed: int = DEFAULT_SEED,
    iterations: int = DEFAULT_ITERATIONS,
    min_df: int = MIN_DF,
    metric: str = COHERENCE_METRIC,
    top_terms: int = TOP_TERMS,
    portuguese_only: bool = True,
    require_disease_term: bool = True,
    formats: tuple[str, ...] | list[str] = DEFAULT_FORMATS,
    model_factory: ModelFactory | None = None,
) -> NewsTopicsTransformResult:
    """Fit the topic model over the frozen corpus and pool it to (ew, location).

    `corpus_path` is the parquet written by `arboili transform news-text`.
    `model_factory` is injectable so the unit tests and the walkthrough notebook
    can drive the whole stage — selection, pooling, integrity — without the
    optional dependency; production passes nothing and gets tomotopy.
    """
    started = time.monotonic()
    result = NewsTopicsTransformResult()
    result.family = family

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

    docs = tokenize_corpus(kept)
    article_ids, ews = article_frame(kept)
    result.empty_docs = sum(1 for doc in docs if not doc)
    covariates = [covariate_bucket(ew, grain) for ew in ews]

    factory = model_factory or load_model_factory(
        family=family, seed=seed, iterations=iterations, min_df=min_df
    )
    sweep = select_k(docs, covariates, k_range, factory, metric=metric)
    model = sweep.best
    assert model is not None  # select_k raises rather than returning an empty sweep
    result.topics = model.k
    result.coherence = sweep.best_coherence
    result.model_id = model.model_id
    result.sweep = [(row.k, row.coherence, row.ll_per_word) for row in sweep.rows]

    pooled = pool_shares(
        article_ids,
        ews,
        model.document_shares(),
        scoped_locations(kept, matcher),
        model.model_id,
    )
    meta = topic_meta(model, model.model_id, top_n=top_terms)
    candidates = sweep_table(sweep)

    result.rows_out = pooled.height
    if pooled.height:
        result.weeks = pooled["ew"].n_unique()
        result.locations = pooled["location"].n_unique()

    result.outputs = _write(pooled, meta, candidates, out_dir, formats)
    result.elapsed = time.monotonic() - started
    log.info(
        "news topics: %d topics selected from %s, %d pooled rows",
        result.topics, list(k_range), pooled.height,
    )
    return result


def _write(
    pooled: pl.DataFrame,
    meta: pl.DataFrame,
    candidates: pl.DataFrame,
    out_dir: Path,
    formats: tuple[str, ...] | list[str],
) -> list[Path]:
    """Parquet plus csv.gz. Both tables are long and narrow, so unlike braço 02's
    768-wide array they do survive csv text form and the csv.gz is written for R
    consumers, the same way braço 01 does."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    frames = (
        (pooled, OUTPUT_NAME),
        (meta, META_OUTPUT_NAME),
        (candidates, SWEEP_OUTPUT_NAME),
    )
    for fmt in formats:
        if fmt == FORMAT_PARQUET:
            for frame, name in frames:
                path = out_dir / f"{name}.parquet"
                frame.write_parquet(path, compression="zstd")
                log.info("wrote %s (%.1f MB)", path, path.stat().st_size / 1e6)
                written.append(path)
        elif fmt == FORMAT_CSV_GZ:
            for frame, name in frames:
                path = out_dir / f"{name}.csv.gz"
                with gzip.open(path, "wb", compresslevel=6) as handle:
                    frame.write_csv(handle)
                log.info("wrote %s (%.1f MB)", path, path.stat().st_size / 1e6)
                written.append(path)
        else:
            raise ValueError(f"Unknown output format {fmt!r}; expected {DEFAULT_FORMATS}")
    return written


__all__ = [
    "NewsTopicsTransformResult",
    "transform",
]
