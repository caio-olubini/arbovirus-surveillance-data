"""Planned schema for braço 03 — temporal topic modeling.

Not implemented. See notes/03-topic-modeling.md.

Two tables: the weekly topic shares the forecaster consumes, and the topic-term
table a human reads to know what a topic *is*. The second is not optional — a
topic index with no readable definition is uninterpretable in a paper, and
"topic 7 predicts dengue" is not a finding anyone can check.
"""

from __future__ import annotations

# --- weekly shares ----------------------------------------------------------

EW = "ew"
LOCATION = "location"
TOPIC_ID = "topic_id"
SHARE = "share"
MODEL_ID = "model_id"

OUTPUT_COLUMNS = (EW, LOCATION, TOPIC_ID, SHARE, MODEL_ID)
GROUP_KEYS = (EW, LOCATION, TOPIC_ID)

OUTPUT_NAME = "EBC_dengue_topics_EW"

NATIONAL_LOCATION = "BR"

# --- topic definitions ------------------------------------------------------

TERM = "term"
WEIGHT = "weight"

META_OUTPUT_COLUMNS = (MODEL_ID, TOPIC_ID, TERM, WEIGHT)
META_OUTPUT_NAME = "EBC_dengue_topics_meta"

# The number of topics is the central modelling choice and is deliberately not
# fixed here. The note's plan is to fit across a range and select on held-out
# likelihood or coherence — pinning a K in the schema would make that sweep look
# like a schema change.
TOPIC_COUNT = None

# STM is the primary candidate (it takes a time covariate directly, which is the
# point of "temporal"); BERTopic is the comparator and LDA the baseline.
PLANNED_MODEL = "stm"

REQUIRED_EXTRA = "stm (r), bertopic, scikit-learn"
