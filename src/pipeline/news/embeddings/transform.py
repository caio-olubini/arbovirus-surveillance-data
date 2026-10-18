"""Run the embeddings stage: frozen corpus → dense per-article and weekly tables.

Two outputs per configuration, because pooling is lossy: the per-article table is
what any later re-pooling, chunking or error analysis needs, and it is the one
that costs the inference. Re-pooling from it is seconds; re-encoding is the whole
run.

The stage runs one configuration of the bracket (`spec.VARIANTS`) per call, or the
whole bracket with `variant_id="all"`. Running them one at a time is deliberate:
each is a download and a long CPU pass, and a caller who only wants the encoder
swap should not have to re-run the base to get it.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import polars as pl

from ..corpus import select_articles as _select_articles
from ..lexicon.steps import load_lexicon, load_uf_matcher
from .spec import (
    BASE_VARIANT_ID,
    DEFAULT_FORMATS,
    EW,
    EMBEDDING,
    FORMAT_PARQUET,
    VARIANTS,
    VARIANT_ORDER,
    Variant,
    table_names,
    variant as resolve_variant,
)
from .steps import (
    DEFAULT_BATCH_SIZE,
    Encoder,
    encode_articles,
    fit_whitening,
    load_encoder,
    pool_by_week,
    scoped_locations,
    truncation_stats,
    whiten_articles,
)

log = logging.getLogger("pipeline.news.embeddings")


@dataclass
class NewsEmbeddingsTransformResult:
    variant: str = BASE_VARIANT_ID
    pooling: str = ""
    whitening: bool = False
    input_fields: str = ""
    max_tokens: int = 0
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
            f"variant={self.variant}",
            f"pooling={self.pooling}",
            f"whitening={self.whitening}",
            f"input={self.input_fields}",
            f"max_tokens={self.max_tokens}",
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
    variant_id: str = BASE_VARIANT_ID,
    batch_size: int = DEFAULT_BATCH_SIZE,
    portuguese_only: bool = True,
    require_disease_term: bool = True,
    normalize: bool | None = None,
    whitening_fit_until: date | None = None,
    formats: tuple[str, ...] | list[str] = DEFAULT_FORMATS,
    encoder: Encoder | None = None,
) -> NewsEmbeddingsTransformResult:
    """Encode the frozen corpus and pool it to (ew, location) for one variant.

    `corpus_path` is the parquet written by `arboili transform news-text`.
    `encoder` is injectable so tests and the walkthrough notebook can drive the
    aggregation without downloading the checkpoint; production passes nothing and
    gets the variant's pinned model.

    `whitening_fit_until` bounds the articles the whitening transform is fitted
    on. The default, `None`, fits over the whole corpus — which is the right
    choice for the *descriptive* reading the bracket is currently for, and the
    wrong one for any predictive evaluation, where it has seen the period being
    predicted. Protocol 00's rolling-origin run must pass an origin here.
    """
    started = time.monotonic()
    result = NewsEmbeddingsTransformResult()
    settings = resolve_variant(variant_id)

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
        encoder = load_encoder(
            settings.model_name,
            settings.model_revision,
            normalize=settings.normalize if normalize is None else normalize,
            pooling=settings.pooling,
            prefix=settings.prefix,
            max_tokens=settings.max_tokens,
        )

    _fill_variant_fields(result, settings)
    result.model_id = encoder.model_id
    result.model_revision = encoder.model_revision
    result.dim = encoder.dim

    articles = encode_articles(
        kept,
        encoder,
        batch_size=batch_size,
        input_fields=settings.input_fields,
        variant_id=settings.id,
    )
    if settings.whitening:
        articles = _whiten(articles, whitening_fit_until)
    result.truncated, result.longest_tokens = truncation_stats(articles, settings.max_tokens)

    pooled = pool_by_week(articles, scoped_locations(kept, matcher), encoder.dim)
    result.rows_out = pooled.height
    if pooled.height:
        result.weeks = pooled[EW].n_unique()
        result.locations = pooled["location"].n_unique()

    result.outputs = _write(articles, pooled, out_dir, formats, settings.id)
    result.elapsed = time.monotonic() - started
    log.info(
        "news embeddings [%s]: %d articles, %d pooled rows",
        settings.id,
        articles.height,
        pooled.height,
    )
    return result


@dataclass
class BracketResult:
    """The whole bracket's run, in the shape `cli.main` expects.

    `cli.main` reads `.failed` off whatever a transform returns to decide its exit
    code, so a bracket run has to answer that question too. It answers the only
    way that is useful: fail if any configuration failed, and say which.
    """

    results: list[NewsEmbeddingsTransformResult] = field(default_factory=list)

    @property
    def failed(self) -> int:
        return sum(result.failed for result in self.results)

    @property
    def elapsed(self) -> float:
        return sum(result.elapsed for result in self.results)

    def __str__(self) -> str:
        lines = [f"NewsEmbeddingsBracketResult({len(self.results)} configurations, "
                 f"{self.elapsed / 60:.1f} min total)"]
        lines.extend(f"  {result}" for result in self.results)
        return "\n".join(lines)


def transform_bracket(
    corpus_path: Path,
    fu_path: Path,
    lexicon_path: Path,
    out_dir: Path,
    variant_ids: tuple[str, ...] = VARIANT_ORDER,
    **kwargs,
) -> BracketResult:
    """Run every configuration of the bracket, one after another.

    Sequential on purpose. Each variant holds a multi-hundred-MB model in memory,
    and loading two at once on a CPU-only machine is slower than loading them in
    turn — the win would be overlapping the download with the inference, which the
    HuggingFace cache already does on the second run.
    """
    bracket = BracketResult()
    for variant_id in variant_ids:
        log.info("bracket: %s (%d of %d)", variant_id, len(bracket.results) + 1, len(variant_ids))
        bracket.results.append(
            transform(
                corpus_path=corpus_path,
                fu_path=fu_path,
                lexicon_path=lexicon_path,
                out_dir=out_dir,
                variant_id=variant_id,
                **kwargs,
            )
        )
    return bracket


def _fill_variant_fields(result: NewsEmbeddingsTransformResult, settings: Variant) -> None:
    result.variant = settings.id
    result.pooling = settings.pooling
    result.whitening = settings.whitening
    result.input_fields = settings.input_fields
    result.max_tokens = settings.max_tokens


def _whiten(articles: pl.DataFrame, fit_until: date | None) -> pl.DataFrame:
    """Fit the transform on the declared window, apply it to every article.

    The fit window and the application window are separate on purpose: the point
    of a rolling origin is that the transform is estimated from the past and then
    applied to the future, not that the future is left unwhitened.
    """
    fit_frame = articles
    if fit_until is not None:
        fit_frame = articles.filter(pl.col(EW) <= fit_until)
    if fit_frame.height < 2:
        raise ValueError(
            f"Whitening needs at least 2 articles to fit on; the window ending "
            f"{fit_until} holds {fit_frame.height}."
        )
    params = fit_whitening(fit_frame[EMBEDDING].to_numpy())
    log.info("whitening fitted on %d of %d articles", fit_frame.height, articles.height)
    return whiten_articles(articles, params)


def _write(
    articles: pl.DataFrame,
    pooled: pl.DataFrame,
    out_dir: Path,
    formats: tuple[str, ...] | list[str],
    variant_id: str,
) -> list[Path]:
    """Parquet only. A csv.gz of a 768-float column is enormous and lossy."""
    out_dir.mkdir(parents=True, exist_ok=True)
    article_name, pooled_name = table_names(variant_id)
    written: list[Path] = []
    for fmt in formats:
        if fmt != FORMAT_PARQUET:
            raise ValueError(
                f"Unknown output format {fmt!r}; braço 02 writes {DEFAULT_FORMATS} "
                f"only (a dense embedding does not survive csv text form)."
            )
        for frame, name in ((articles, article_name), (pooled, pooled_name)):
            path = out_dir / f"{name}.parquet"
            frame.write_parquet(path, compression="zstd")
            log.info("wrote %s (%.1f MB)", path, path.stat().st_size / 1e6)
            written.append(path)
    return written


__all__ = [
    "BracketResult",
    "NewsEmbeddingsTransformResult",
    "select_articles",
    "transform",
    "transform_bracket",
]
