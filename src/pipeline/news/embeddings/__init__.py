"""Braço 02 — dense sentence embeddings → weekly features.

`arboili transform news-embeddings` reads the frozen text corpus, encodes each
article with a pinned checkpoint (frozen — no fine-tuning), and pools the vectors
by (epidemiological week, location), location being `BR` or a federative unit.
That is the grain every news braço publishes, so the three stay swappable in the
same model.

The braço is a **bracket** of configurations rather than a single encoder. One
dense configuration made a null result uninterpretable — "the representation lost"
could not be told apart from "this encoder was too weak" — so the stage publishes
several unsupervised, no-training variants of the same representation and the
comparison reads the range. See `spec.VARIANTS` and the module docstring of
`steps.py`.

Two tables per variant: the per-article vectors, which cost the inference and are
what any later re-pooling needs, and the pooled weekly table the forecaster
consumes. The base configuration keeps the unsuffixed table names.

Needs the optional `embeddings` extra:

    uv sync --extra embeddings

See notes/02-embeddings-densos.md for the hypothesis and the evidence, and
`src/pipeline/news/README.md` §3 for the measured output and the limitations.
"""

from __future__ import annotations

from .spec import (
    ARTICLE_OUTPUT_COLUMNS,
    BASE_VARIANT_ID,
    DEFAULT_FORMATS,
    EMBEDDING_DIM,
    MODEL_NAME,
    MODEL_REVISION_SHA,
    OUTPUT_COLUMNS,
    REQUIRED_EXTRA,
    VARIANTS,
    VARIANT_ORDER,
    Variant,
    table_names,
    variant,
)
from .steps import Encoder, MissingExtraError, load_encoder
from .transform import NewsEmbeddingsTransformResult, transform, transform_bracket

__all__ = [
    "ARTICLE_OUTPUT_COLUMNS",
    "BASE_VARIANT_ID",
    "DEFAULT_FORMATS",
    "EMBEDDING_DIM",
    "MODEL_NAME",
    "MODEL_REVISION_SHA",
    "OUTPUT_COLUMNS",
    "REQUIRED_EXTRA",
    "VARIANTS",
    "VARIANT_ORDER",
    "Encoder",
    "MissingExtraError",
    "NewsEmbeddingsTransformResult",
    "Variant",
    "load_encoder",
    "table_names",
    "transform",
    "transform_bracket",
    "variant",
]
