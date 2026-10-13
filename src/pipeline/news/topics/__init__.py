"""Braço 03 — temporal topic modeling → weekly topic shares.

`arboili transform news-topics` reads the frozen text corpus, fits one topic model
over it with the period as a document covariate (tomotopy's DMR), and publishes the
mean topic mixture of each (epidemiological week, location) — location being `BR`
or a federative unit. That is the grain every news braço publishes, so the three
stay swappable in the same model.

Three tables: the weekly shares the forecaster consumes, the topic → term table
that says what each topic *is*, and the coherence sweep that justifies the number
of topics. The second is not optional — "topic 7 predicts dengue" is not a finding
anyone can check — and the third is the evidence `notes/03` asks to be reported
rather than left in a log.

`k` is selected by coherence over `K_RANGE`, never by perplexity, and the covariate
grain is a period (month by default), not the weekly grain the tables are keyed by.
Both choices, and why the model is DMR rather than STM or BERTopic, are argued in
`spec.py`.

Needs the optional `topics` extra:

    uv sync --extra topics

See notes/03-topic-modeling.md for the hypothesis and the evidence, and
`src/pipeline/news/README.md` §4 for the measured output and the limitations.
"""

from __future__ import annotations

from .integrity import Check, run_all
from .spec import (
    COHERENCE_METRIC,
    COVARIATE_GRAIN,
    DEFAULT_FORMATS,
    K_RANGE,
    META_OUTPUT_COLUMNS,
    META_OUTPUT_NAME,
    MODEL_FAMILIES,
    OUTPUT_COLUMNS,
    OUTPUT_NAME,
    REQUIRED_EXTRA,
    SWEEP_OUTPUT_COLUMNS,
    SWEEP_OUTPUT_NAME,
)
from .steps import MissingExtraError, TopicModel, load_model_factory
from .transform import NewsTopicsTransformResult, transform

__all__ = [
    "COHERENCE_METRIC",
    "COVARIATE_GRAIN",
    "DEFAULT_FORMATS",
    "K_RANGE",
    "META_OUTPUT_COLUMNS",
    "META_OUTPUT_NAME",
    "MODEL_FAMILIES",
    "OUTPUT_COLUMNS",
    "OUTPUT_NAME",
    "REQUIRED_EXTRA",
    "SWEEP_OUTPUT_COLUMNS",
    "SWEEP_OUTPUT_NAME",
    "Check",
    "MissingExtraError",
    "NewsTopicsTransformResult",
    "TopicModel",
    "load_model_factory",
    "run_all",
    "transform",
]
