"""Braço 03 — temporal topic modeling. Not implemented.

Schema in `spec.py`; hypothesis, model candidates and the closest precedent
(EpiNews) in notes/03-topic-modeling.md.

What is missing, concretely:

1. A model. STM is the note's primary candidate because it takes time as a
   covariate, which is what makes the model *temporal* rather than a topic model
   applied to a sorted corpus. BERTopic and LDA are the comparator and baseline.
2. The number of topics, selected on held-out likelihood or coherence rather
   than chosen. That selection is itself a result worth reporting.
3. A tokenizer decision for PT-BR — stopwords, and whether to lemmatize. STM's
   R implementation and the Python alternatives disagree about preprocessing, so
   this has to be fixed and recorded, not inherited from a default.
4. Dependencies (`stm` is R, so this braço needs a bridge or a Python
   alternative; `bertopic` and `scikit-learn` are not installed today).

Until then the stage refuses to run rather than emitting something plausible.
"""

from __future__ import annotations

from .spec import (
    META_OUTPUT_COLUMNS,
    META_OUTPUT_NAME,
    OUTPUT_COLUMNS,
    OUTPUT_NAME,
    PLANNED_MODEL,
    REQUIRED_EXTRA,
    TOPIC_COUNT,
)


def transform(*args: object, **kwargs: object) -> None:
    """Refuse, with the reason and the note that owns the decision."""
    raise NotImplementedError(
        "Braço 03 (temporal topic modeling) is not implemented. It needs "
        f"{REQUIRED_EXTRA}, a topic count selected rather than guessed, and a "
        "frozen PT-BR preprocessing recipe — see notes/03-topic-modeling.md and "
        "src/pipeline/news/topics/spec.py."
    )


__all__ = [
    "META_OUTPUT_COLUMNS",
    "META_OUTPUT_NAME",
    "OUTPUT_COLUMNS",
    "OUTPUT_NAME",
    "PLANNED_MODEL",
    "REQUIRED_EXTRA",
    "TOPIC_COUNT",
    "transform",
]
