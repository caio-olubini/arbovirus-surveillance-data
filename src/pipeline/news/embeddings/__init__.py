"""Braço 02 — dense BERTimbau embeddings → weekly features.

`arboili transform news-embeddings` reads the frozen text corpus, encodes each
article with a pinned BERTimbau checkpoint (frozen — no fine-tuning), and pools
the vectors by (epidemiological week, location), location being `BR` or a
federative unit. That is the grain every news braço publishes, so the three stay
swappable in the same model.

Two tables: the per-article vectors, which cost the inference and are what any
later re-pooling needs, and the pooled weekly table the forecaster consumes.

Needs the optional `embeddings` extra:

    uv sync --extra embeddings

See notes/02-embeddings-densos.md for the hypothesis and the evidence, and
`src/pipeline/news/README.md` §3 for the measured output and the limitations.
"""

from __future__ import annotations

from .spec import (
    ARTICLE_OUTPUT_COLUMNS,
    ARTICLE_OUTPUT_NAME,
    DEFAULT_FORMATS,
    EMBEDDING_DIM,
    MODEL_NAME,
    MODEL_REVISION_SHA,
    OUTPUT_COLUMNS,
    OUTPUT_NAME,
    REQUIRED_EXTRA,
)
from .steps import Encoder, MissingExtraError, load_encoder
from .transform import NewsEmbeddingsTransformResult, transform

__all__ = [
    "ARTICLE_OUTPUT_COLUMNS",
    "ARTICLE_OUTPUT_NAME",
    "DEFAULT_FORMATS",
    "EMBEDDING_DIM",
    "MODEL_NAME",
    "MODEL_REVISION_SHA",
    "OUTPUT_COLUMNS",
    "OUTPUT_NAME",
    "REQUIRED_EXTRA",
    "Encoder",
    "MissingExtraError",
    "NewsEmbeddingsTransformResult",
    "load_encoder",
    "transform",
]
