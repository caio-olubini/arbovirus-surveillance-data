"""Dense embeddings over the frozen text corpus → pooled weekly features (braço 02).

The representation: one vector per article from a **frozen** encoder, then a mean
over the articles of a week. Nothing here is fine-tuned — fine-tuning would turn
the braço into a different experiment, and `notes/02` fixes the base braço as the
frozen one.

Two things are shared with braço 01 on purpose, because protocol 00 fixes them as
common ground rather than as part of any representation:

* **The article set.** The same `lang_guess == "pt"` and dengue-term gates, so the
  two braços see the same 4,369 articles and the comparison isolates the
  representation instead of the corpus.
* **The geo scoping.** `UfMatcher` from `lexicon.steps` — mention-based, state
  level, municipalities unresolved. The spatial mismatch between national news and
  a UF-level target is a declared limitation, not something to re-solve per braço.

Both moved to `news.corpus` when braço 03 arrived and needed them too; they are
re-exported here so the braço-02 API is unchanged.

The one approximation worth knowing about: **articles are truncated at
`MAX_TOKENS`**. A 34,960-character era-B article and a 163-character era-C note
both become one 768-vector, and only the `n_tokens` column says which of them lost
text. Truncation is recorded rather than hidden, and chunked pooling is the
declared next step if the tail turns out to matter.
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
    DIM,
    EMBEDDING,
    EMB_MEAN,
    EMB_STD,
    EW,
    LOCATION,
    MAX_TOKENS,
    MODEL_ID,
    MODEL_REVISION,
    N_ARTICLES,
    N_TOKENS,
    NATIONAL_LOCATION,
    OUTPUT_COLUMNS,
    REQUIRED_EXTRA,
)

log = logging.getLogger("pipeline.news.embeddings")

DEFAULT_BATCH_SIZE = 16


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
    n_tokens: list[int]          # tokens per text, *before* the MAX_TOKENS cut


class Encoder(Protocol):
    """What the stage needs from a model, so tests and the notebook can fake it.

    The real implementation is `BertimbauEncoder`; the tests and the notebook's
    fixture section pass a deterministic stand-in instead, which keeps the
    aggregation logic testable without a 400 MB download.
    """

    model_id: str
    model_revision: str
    dim: int

    def encode(self, texts: Sequence[str]) -> Encoded: ...


class BertimbauEncoder:
    """BERTimbau with masked mean pooling over the last hidden state.

    Mean pooling over the *masked* last hidden state, not the `[CLS]` token and
    not the model's pooler head: `[CLS]` is trained for next-sentence prediction
    and the pooler is discarded by every sentence-embedding recipe precisely
    because it is the weakest read of the sentence. The mask matters — without it
    the padding positions, which are `[PAD]` embeddings, drag the mean toward
    whatever the model does with `[PAD]`.

    Vectors are L2-normalized so that a week's mean is a centroid on the unit
    sphere rather than a magnitude-weighted average, and `emb_std` is then an
    angular spread. Normalization is recorded as a run parameter for the same
    reason the lexicon is versioned: it changes the numbers.
    """

    def __init__(
        self,
        model_id: str,
        model_revision: str,
        tokenizer: Any,
        model: Any,
        torch: Any,
        device: str = "cpu",
        normalize: bool = True,
    ) -> None:
        self.model_id = model_id
        self.model_revision = model_revision
        self.normalize = normalize
        self.device = device
        self._tokenizer = tokenizer
        self._model = model
        self._torch = torch
        self.dim = int(model.config.hidden_size)

    def encode(self, texts: Sequence[str]) -> Encoded:
        torch = self._torch
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
            max_length=MAX_TOKENS,
            return_tensors="pt",
        )
        batch = {key: value.to(self.device) for key, value in batch.items()}

        with torch.no_grad():
            hidden = self._model(**batch).last_hidden_state          # (n, t, d)
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


def load_encoder(
    model_name: str,
    model_revision: str,
    device: str = "cpu",
    normalize: bool = True,
) -> BertimbauEncoder:
    """Load the frozen encoder. Needs the `embeddings` extra and a download.

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
    # The neuralmind checkpoint ships `pytorch_model.bin` and no safetensors, so
    # the fallback is named explicitly rather than left to the default, which
    # prefers safetensors and would otherwise decide this for us.
    model = AutoModel.from_pretrained(
        model_name, revision=model_revision, use_safetensors=False
    )
    model.eval()
    model.to(device)
    log.info("loaded %s@%s (%d-wide, %s)", model_name, model_revision[:8], model.config.hidden_size, device)
    return BertimbauEncoder(
        model_id=model_name,
        model_revision=model_revision,
        tokenizer=tokenizer,
        model=model,
        torch=torch,
        device=device,
        normalize=normalize,
    )


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

def _batches(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def encode_articles(
    corpus: pl.DataFrame,
    encoder: Encoder,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> pl.DataFrame:
    """One embedding per article, in the order the corpus is given.

    The corpus is expected to be already filtered to the articles this braço is
    allowed to see — the filter is common ground, and applying it here would make
    it invisible to the caller that has to justify it.
    """
    rows = corpus.select(ARTICLE_ID, EW, TITLE, TEXT).iter_rows(named=True)
    records = list(rows)
    texts = [article_input(row[TITLE] or "", row[TEXT] or "") for row in records]

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
        EMB_STD: pl.Float32,
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
    """Mean vector and dispersion per (ew, location), BR included.

    Every article contributes to BR; it also contributes to each UF it names, so
    one article can land in several rows of the same week — the same scoping rule
    braço 01 uses, and the reason `n_articles` can sum to more than the corpus.

    `emb_std` is the **norm** of the per-dimension standard deviation, not the
    vector: a 768-wide std column would double the table to say one number the
    norm already carries. Population std (`ddof=0`), so a week with a single
    article is exactly 0 — "no dispersion observed", which is the honest reading
    and the one that keeps the column finite.

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
        mean = block.mean(axis=0)
        spread = block.std(axis=0) if block.shape[0] > 1 else np.zeros(block.shape[1])
        records.append(
            {
                EW: ew,
                LOCATION: location,
                EMB_MEAN: mean.astype(np.float32),
                EMB_STD: np.float32(np.linalg.norm(spread)),
                N_ARTICLES: int(block.shape[0]),
            }
        )
    return pl.DataFrame(records, schema=pooled_schema(dim)).select(OUTPUT_COLUMNS)


def truncation_stats(articles: pl.DataFrame) -> tuple[int, int]:
    """(articles above the token limit, the longest one's token count)."""
    if articles.height == 0:
        return 0, 0
    over = articles.filter(pl.col(N_TOKENS) > MAX_TOKENS)
    longest = int(articles[N_TOKENS].max() or 0)
    return over.height, longest


__all__ = [
    "BertimbauEncoder",
    "Encoded",
    "Encoder",
    "MissingExtraError",
    "article_input",
    "article_schema",
    "encode_articles",
    "load_encoder",
    "pool_by_week",
    "pooled_schema",
    "scoped_locations",
    "truncation_stats",
]
