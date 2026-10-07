"""Braço 02 — dense sentence embeddings + pooling by epi week. Not implemented.

The schema this stage will publish is in `spec.py`; the hypothesis, the model
candidates and the counter-evidence are in notes/02-embeddings-densos.md.

What is missing, concretely:

1. A pinned encoder. BERTimbau and BioBERTpt are the two candidates the note
   names; choosing one is a research decision, and it has to be frozen before
   any embedding is computed or the experiment is not reproducible.
2. The dependency itself (`torch` + `transformers`). Nothing in this repository
   imports either today, so no version is pinned — adding them is a deliberate
   step, not a side effect of writing this stub.
3. A decision on pooling, and on whether the pooled vector is used whole or
   reduced (PCA) before it reaches the forecaster.

Until then the stage refuses to run rather than emitting something plausible.
"""

from __future__ import annotations

from .spec import (
    ARTICLE_OUTPUT_NAME,
    DEFAULT_FORMATS,
    OUTPUT_COLUMNS,
    OUTPUT_NAME,
    PLANNED_DIM,
    REQUIRED_EXTRA,
)


def transform(*args: object, **kwargs: object) -> None:
    """Refuse, with the reason and the note that owns the decision."""
    raise NotImplementedError(
        "Braço 02 (dense embeddings) is not implemented. It needs "
        f"{REQUIRED_EXTRA} and a frozen encoder choice — see "
        "notes/02-embeddings-densos.md and src/pipeline/news/embeddings/spec.py. "
        "The schema is already written down so the three representations stay "
        "swappable."
    )


__all__ = [
    "ARTICLE_OUTPUT_NAME",
    "DEFAULT_FORMATS",
    "OUTPUT_COLUMNS",
    "OUTPUT_NAME",
    "PLANNED_DIM",
    "REQUIRED_EXTRA",
    "transform",
]
