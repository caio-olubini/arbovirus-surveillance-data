"""Dense embeddings over the frozen text corpus → pooled weekly features (braço 02).

The representation: one vector per article from a **frozen** encoder, then a mean
over the articles of a week. Nothing here is fine-tuned — fine-tuning would turn
the braço into a different experiment, and `notes/02` fixes the base braço as the
frozen one.

One encoder is not one configuration. The braço runs a **bracket** of them
(`spec.VARIANTS`), all unsupervised and unlabelled, so that a null result can be
told apart from "this particular encoder was too weak". Three things vary across
the bracket and each is declared per variant rather than hardcoded here:

* **the pooling** — masked mean or `[CLS]`, whichever the encoder's authors
  published. BGE-M3's dense embedding *is* its `[CLS]` token; forcing a mean on
  it would measure a configuration nobody uses.
* **the window** — 512 tokens for every model that can take it, so a gain cannot
  come from one encoder quietly reading more text than another. Serafim's window
  is 128 and is the declared exception.
* **whitening** — an optional post-hoc linear correction for the anisotropy that
  mean pooling without fine-tuning is known to suffer from.

Two things are shared with braço 01 on purpose, because protocol 00 fixes them as
common ground rather than as part of any representation:

* **The article set.** The same `lang_guess == "pt"` and dengue-term gates, so the
  braços see the same 4,369 articles and the comparison isolates the
  representation instead of the corpus.
* **The geo scoping.** `UfMatcher` from `lexicon.steps` — mention-based, state
  level, municipalities unresolved. The spatial mismatch between national news and
  a UF-level target is a declared limitation, not something to re-solve per braço.

The one approximation worth knowing about: **articles are truncated at the
variant's window**. A 34,960-character era-B article and a 163-character era-C
note both become one vector, and only the `n_tokens` column says which of them
lost text.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
import polars as pl

from ..corpus import LOCATIONS, article_input, scoped_locations
from ..text.spec import TEXT, TITLE
from .spec import (
    ARTICLE_ID,
    ARTICLE_OUTPUT_COLUMNS,
    BASE_VARIANT_ID,
    DIM,
    EMBEDDING,
    EMB_MEAN,
    EW,
    INPUT_TITLE,
    LOCATION,
    MAX_TOKENS,
    MODEL_ID,
    MODEL_REVISION,
    N_ARTICLES,
    N_TOKENS,
    NATIONAL_LOCATION,
    OUTPUT_COLUMNS,
    POOLING_CLS,
    REQUIRED_EXTRA,
    VARIANT,
)

log = logging.getLogger("pipeline.news.embeddings")

DEFAULT_BATCH_SIZE = 16

# Floor on the whitening eigenvalues. The covariance of L2-normalized vectors is
# near-singular (768 dimensions, a mean vector of norm ~0.95), so the smallest
# eigenvalues are numerical noise and their reciprocal is not a transform.
WHITENING_EPSILON = 1e-5


class MissingExtraError(RuntimeError):
    """The optional `embeddings` extra is not installed.

    Raised instead of `ImportError` so the CLI can print one sentence rather than
    a traceback, the same contract the other stages' refusals follow.
    """


# ---------------------------------------------------------------------------
# The encoder
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Encoded:
    """One batch's vectors, plus what the tokenizer saw before truncation."""

    vectors: np.ndarray          # (n, dim) float32, L2-normalized
    n_tokens: list[int]          # tokens per text, *before* the max_tokens cut


class Encoder(Protocol):
    """What the stage needs from a model, so tests and the notebook can fake it.

    The real implementation is `TransformerEncoder`; the tests and the notebook's
    fixture section pass a deterministic stand-in instead, which keeps the
    aggregation logic testable without a 400 MB download.
    """

    model_id: str
    model_revision: str
    dim: int

    def encode(self, texts: Sequence[str]) -> Encoded: ...


class TransformerEncoder:
    """A frozen `AutoModel` with masked mean or `[CLS]` pooling.

    Mean pooling over the *masked* last hidden state, not the `[CLS]` token and
    not the model's pooler head: `[CLS]` is trained for next-sentence prediction
    and the pooler is discarded by every sentence-embedding recipe precisely
    because it is the weakest read of the sentence. The mask matters — without it
    the padding positions, which are `[PAD]` embeddings, drag the mean toward
    whatever the model does with `[PAD]`.

    `[CLS]` is offered because for some encoders it is not the weak read it is for
    BERT: BGE-M3's dense embedding is defined as its `[CLS]` token, so reading it
    with a mean would be reading a different model than the one that was trained.

    `prefix` is prepended to every text. E5 is trained with `passage: ` on
    documents and `query: ` on queries, and skipping the prefix measurably
    degrades it; these are articles, so they are passages.

    Vectors are L2-normalized so that a week's mean is a centroid on the unit
    sphere rather than a magnitude-weighted average. Normalization is recorded as
    a run parameter for the same reason the lexicon is versioned: it changes the
    numbers.
    """

    def __init__(
        self,
        model_id: str,
        model_revision: str,
        tokenizer: Any,
        model: Any,
        torch: Any,
        device: str = "cpu",
        pooling: str = "mean",
        prefix: str = "",
        max_tokens: int = MAX_TOKENS,
        normalize: bool = True,
    ) -> None:
        if pooling not in ("mean", POOLING_CLS):
            raise ValueError(f"Unknown pooling {pooling!r}; expected 'mean' or {POOLING_CLS!r}")
        self.model_id = model_id
        self.model_revision = model_revision
        self.pooling = pooling
        self.prefix = prefix
        self.max_tokens = max_tokens
        self.normalize = normalize
        self.device = device
        self._tokenizer = tokenizer
        self._model = model
        self._torch = torch
        self.dim = int(model.config.hidden_size)

    def encode(self, texts: Sequence[str]) -> Encoded:
        torch = self._torch
        texts = [f"{self.prefix}{text}" for text in texts] if self.prefix else list(texts)
        # Two passes over the tokenizer: one untruncated to record how long the
        # article really was, one padded and truncated to what the model takes.
        # The alternative — reading the length off `attention_mask` — cannot tell
        # a 512-token article from a 3,000-token one.
        counts = [
            len(ids)
            for ids in self._tokenizer(
                list(texts), add_special_tokens=True, truncation=False
            )["input_ids"]
        ]
        batch = self._tokenizer(
            list(texts),
            padding=True,
            truncation=True,
            max_length=self.max_tokens,
            return_tensors="pt",
        )
        batch = {key: value.to(self.device) for key, value in batch.items()}

        with torch.no_grad():
            hidden = self._model(**batch).last_hidden_state          # (n, t, d)
            if self.pooling == POOLING_CLS:
                pooled = hidden[:, 0, :]
            else:
                mask = batch["attention_mask"].unsqueeze(-1).to(hidden.dtype)
                summed = (hidden * mask).sum(dim=1)
                lengths = mask.sum(dim=1).clamp(min=1e-9)
                pooled = summed / lengths

        if self.normalize:
            norm = pooled.norm(dim=1, keepdim=True).clamp(min=1e-12)
            pooled = pooled / norm

        return Encoded(
            vectors=pooled.detach().cpu().numpy().astype(np.float32, copy=False),
            n_tokens=counts,
        )


# The name this class had while braço 02 was BERTimbau-only. Kept so the notebook
# and any older import keep working; new code should say `TransformerEncoder`.
BertimbauEncoder = TransformerEncoder


def load_encoder(
    model_name: str,
    model_revision: str,
    device: str = "cpu",
    normalize: bool = True,
    pooling: str = "mean",
    prefix: str = "",
    max_tokens: int = MAX_TOKENS,
) -> TransformerEncoder:
    """Load a frozen encoder. Needs the `embeddings` extra and a download.

    `device` is not auto-detected. The notebook and the pipeline then produce the
    same numbers wherever they run, which is the point of pinning the revision in
    the first place; a caller who wants a GPU passes it explicitly.
    """
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except ImportError as error:  # pragma: no cover - depends on the environment
        raise MissingExtraError(
            f"Braço 02 needs the optional `{REQUIRED_EXTRA}` extra (torch + "
            f"transformers). Install it with:\n\n    uv sync --extra {REQUIRED_EXTRA}\n"
        ) from error

    tokenizer = AutoTokenizer.from_pretrained(model_name, revision=model_revision)
    # No `use_safetensors` override: the bracket spans checkpoints that ship only
    # `pytorch_model.bin` (BERTimbau, BGE-M3) and ones that ship only
    # `model.safetensors` (Serafim), and the default — prefer safetensors, fall
    # back to the pickle — is the only setting that loads all four. Forcing the
    # pickle, which this did while the braço was BERTimbau-only, would make
    # Serafim fail to load at all.
    model = AutoModel.from_pretrained(model_name, revision=model_revision)
    model.eval()
    model.to(device)
    log.info(
        "loaded %s@%s (%d-wide, %s pooling, %d tokens, %s)",
        model_name,
        model_revision[:8],
        model.config.hidden_size,
        pooling,
        max_tokens,
        device,
    )
    return TransformerEncoder(
        model_id=model_name,
        model_revision=model_revision,
        tokenizer=tokenizer,
        model=model,
        torch=torch,
        device=device,
        pooling=pooling,
        prefix=prefix,
        max_tokens=max_tokens,
        normalize=normalize,
    )


# ---------------------------------------------------------------------------
# Whitening
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Whitening:
    """The fitted transform: a centring and a linear map.

    Kept as a value rather than applied in place so the fit window is an explicit
    argument at the call site. Protocol 00's rolling-origin evaluation has to
    refit this per origin — a whitening fitted over the whole corpus has seen the
    period being predicted, which in a forecasting problem is the future.
    """

    mean: np.ndarray      # (dim,)
    kernel: np.ndarray    # (dim, dim)


def fit_whitening(vectors: np.ndarray, epsilon: float = WHITENING_EPSILON) -> Whitening:
    """Fit the whitening transform on a set of vectors.

    Su et al. 2021 (arXiv:2103.15316) and WhiteningBERT (Huang et al. 2021): centre
    the embeddings and map them by the inverse square root of their covariance,
    `W = U√Λ⁻¹` from the SVD of the covariance. The result is a space where the
    variance is spread evenly across directions instead of crowding into the
    narrow cone that makes unrelated sentences look alike.

    `epsilon` floors the eigenvalues. The covariance here is near-singular — 768
    dimensions and a mean of norm ~0.95 — so the smallest eigenvalues are
    numerical noise and their exact reciprocals would amplify it.
    """
    matrix = np.asarray(vectors, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] < 2:
        raise ValueError(
            f"Whitening needs a (n>1, dim) matrix to estimate a covariance; got {matrix.shape}"
        )
    mean = matrix.mean(axis=0)
    centred = matrix - mean
    covariance = np.cov(centred, rowvar=False)
    u, singular, _ = np.linalg.svd(covariance)
    kernel = u @ np.diag(1.0 / np.sqrt(singular + epsilon))
    return Whitening(
        mean=mean.astype(np.float32),
        kernel=kernel.astype(np.float32),
    )


def apply_whitening(vectors: np.ndarray, params: Whitening) -> np.ndarray:
    """`(x − μ) W`, then back onto the unit sphere.

    Re-normalizing matters for the comparison rather than for the whitening: the
    base configuration pools unit vectors, so a whitened variant that pooled
    magnitude-weighted means would differ from the base in two ways at once. The
    transform changes the *geometry*; the aggregation contract stays the same.
    """
    matrix = np.asarray(vectors, dtype=np.float32)
    whitened = (matrix - params.mean) @ params.kernel
    return normalize_rows(whitened)


def normalize_rows(matrix: np.ndarray) -> np.ndarray:
    """L2-normalize each row, leaving an all-zero row at zero instead of NaN."""
    matrix = np.asarray(matrix, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.where(norms > 0, norms, 1.0)


def whiten_articles(articles: pl.DataFrame, params: Whitening) -> pl.DataFrame:
    """Rewrite the embedding column of an article table in whitened space."""
    if articles.height == 0:
        return articles
    matrix = apply_whitening(articles[EMBEDDING].to_numpy(), params)
    return articles.with_columns(
        pl.Series(EMBEDDING, list(matrix), dtype=pl.Array(pl.Float32, matrix.shape[1]))
    )


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

def _batches(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def article_texts(
    corpus: pl.DataFrame, input_fields: str = "title_body"
) -> list[str]:
    """The text each article is encoded from.

    `title_body` is the default because the headline is where a week's framing
    lives ("Surto de dengue cresce no interior de SP"), and dropping it would
    throw away the most topical sentence of the article. `title` exists as the
    bracket's floor: the least text a dense reading can be given, and the only
    configuration where the 512-token window cannot be the explanation.
    """
    if input_fields == INPUT_TITLE:
        return [(row[TITLE] or "") for row in corpus.select(TITLE).iter_rows(named=True)]
    return [
        article_input(row[TITLE] or "", row[TEXT] or "")
        for row in corpus.select(TITLE, TEXT).iter_rows(named=True)
    ]


def encode_articles(
    corpus: pl.DataFrame,
    encoder: Encoder,
    batch_size: int = DEFAULT_BATCH_SIZE,
    input_fields: str = "title_body",
    variant_id: str = BASE_VARIANT_ID,
) -> pl.DataFrame:
    """One embedding per article, in the order the corpus is given.

    The corpus is expected to be already filtered to the articles this braço is
    allowed to see — the filter is common ground, and applying it here would make
    it invisible to the caller that has to justify it.
    """
    records = list(corpus.select(ARTICLE_ID, EW, TITLE, TEXT).iter_rows(named=True))
    texts = article_texts(corpus, input_fields)

    vectors: list[np.ndarray] = []
    tokens: list[int] = []
    for batch in _batches(texts, batch_size):
        encoded = encoder.encode(batch)
        vectors.append(encoded.vectors)
        tokens.extend(encoded.n_tokens)

    matrix = (
        np.concatenate(vectors, axis=0)
        if vectors
        else np.zeros((0, encoder.dim), dtype=np.float32)
    )
    return pl.DataFrame(
        {
            ARTICLE_ID: [row[ARTICLE_ID] for row in records],
            EW: [row[EW] for row in records],
            EMBEDDING: list(matrix),
            VARIANT: [variant_id] * len(records),
            MODEL_ID: [encoder.model_id] * len(records),
            MODEL_REVISION: [encoder.model_revision] * len(records),
            DIM: [encoder.dim] * len(records),
            N_TOKENS: tokens,
        },
        schema=article_schema(encoder.dim),
    ).select(ARTICLE_OUTPUT_COLUMNS)


def article_schema(dim: int) -> dict[str, pl.DataType]:
    """Fixed-width `Array`, not `List`: the width is a property of the model, and
    a ragged column would let a partial batch through unnoticed."""
    return {
        ARTICLE_ID: pl.String,
        EW: pl.Date,
        EMBEDDING: pl.Array(pl.Float32, dim),
        VARIANT: pl.String,
        MODEL_ID: pl.String,
        MODEL_REVISION: pl.String,
        DIM: pl.Int64,
        N_TOKENS: pl.Int64,
    }


def pooled_schema(dim: int) -> dict[str, pl.DataType]:
    return {
        EW: pl.Date,
        LOCATION: pl.String,
        EMB_MEAN: pl.Array(pl.Float32, dim),
        N_ARTICLES: pl.Int64,
    }


# ---------------------------------------------------------------------------
# Pooling
# ---------------------------------------------------------------------------
# `scoped_locations` used to live here. It moved to `news.corpus` when braço 03
# needed the same function: the geo scoping is protocol-00 common ground, so it
# cannot live inside one of the competing braços. It is re-exported below.

def pool_by_week(
    articles: pl.DataFrame,
    locations: pl.DataFrame,
    dim: int,
) -> pl.DataFrame:
    """Mean vector and article count per (ew, location), BR included.

    Every article contributes to BR; it also contributes to each UF it names, so
    one article can land in several rows of the same week — the same scoping rule
    braço 01 uses, and the reason `n_articles` can sum to more than the corpus.

    The mean is over the articles that landed in the row, so a week of five
    unrelated stories and a week of five copies of one story have the same
    `n_articles` and different means. That *is* the dispersion signal: for unit
    vectors the norm of the mean is a sufficient statistic for how far apart the
    week's articles are (`‖std‖² = 1 − ‖mean‖²`), which is why the separate
    `emb_std` column was removed rather than repaired — see `spec.py`.

    Only observed pairs are emitted. A week with no article is *absent*, not a
    zero vector: a zero embedding is a real point in the space and would read as
    "news that means nothing" rather than "no news". `notes/02` asks for a
    `no_news` indicator; absence is that indicator, and the consumer left-joins
    onto the target calendar exactly as it does for braço 01.
    """
    pairs = (
        articles.select(ARTICLE_ID, EW, EMBEDDING)
        .join(locations, on=ARTICLE_ID, how="inner")
        .with_columns(
            pl.concat_list(
                pl.col(LOCATIONS), pl.lit([NATIONAL_LOCATION], dtype=pl.List(pl.String))
            ).alias(LOCATIONS)
        )
        .explode(LOCATIONS)
        .rename({LOCATIONS: LOCATION})
        .with_row_index("_row")
    )
    if pairs.height == 0:
        return pl.DataFrame(schema=pooled_schema(dim))

    matrix = pairs[EMBEDDING].to_numpy()
    groups = pairs.group_by(EW, LOCATION).agg(pl.col("_row")).sort(EW, LOCATION)

    records: list[dict[str, Any]] = []
    for ew, location, indices in groups.iter_rows():
        block = matrix[indices]
        records.append(
            {
                EW: ew,
                LOCATION: location,
                EMB_MEAN: block.mean(axis=0).astype(np.float32),
                N_ARTICLES: int(block.shape[0]),
            }
        )
    return pl.DataFrame(records, schema=pooled_schema(dim)).select(OUTPUT_COLUMNS)


def truncation_stats(articles: pl.DataFrame, max_tokens: int = MAX_TOKENS) -> tuple[int, int]:
    """(articles above the token limit, the longest one's token count)."""
    if articles.height == 0:
        return 0, 0
    over = articles.filter(pl.col(N_TOKENS) > max_tokens)
    longest = int(articles[N_TOKENS].max() or 0)
    return over.height, longest


__all__ = [
    "BertimbauEncoder",
    "Encoded",
    "Encoder",
    "MissingExtraError",
    "TransformerEncoder",
    "WHITENING_EPSILON",
    "Whitening",
    "apply_whitening",
    "article_input",
    "article_schema",
    "article_texts",
    "encode_articles",
    "fit_whitening",
    "load_encoder",
    "normalize_rows",
    "pool_by_week",
    "pooled_schema",
    "scoped_locations",
    "truncation_stats",
    "whiten_articles",
]
