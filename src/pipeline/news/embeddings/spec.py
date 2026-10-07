"""Planned schema for braço 02 — dense embeddings pooled by epi week.

Not implemented. The columns below are the contract this braço is expected to
honour when it lands, written down now so the three representations stay
swappable in the same model. See notes/02-embeddings-densos.md.

Two tables, because pooling is lossy and the per-article vectors are what any
later re-pooling or error analysis needs:

    EBC_dengue_embeddings_article   one row per article, embedding as a List
    EBC_dengue_embeddings_EW        one row per (ew, location), pooled

The model choice is deliberately *not* pinned here: BERTimbau vs. BioBERTpt is a
decision the note leaves open, and pinning it in the schema would make an
experiment change look like a schema change.
"""

from __future__ import annotations

# --- per-article table ------------------------------------------------------

ARTICLE_ID = "article_id"
EW = "ew"
EMBEDDING = "embedding"
MODEL_ID = "model_id"
DIM = "dim"

ARTICLE_OUTPUT_COLUMNS = (ARTICLE_ID, EW, EMBEDDING, MODEL_ID, DIM)
ARTICLE_OUTPUT_NAME = "EBC_dengue_embeddings_article"

# --- pooled table -----------------------------------------------------------

LOCATION = "location"
POOLED = "embedding"
POOLING = "pooling"          # "mean" | "max" | "attention" — recorded per run

OUTPUT_COLUMNS = (EW, LOCATION, POOLED)
GROUP_KEYS = (EW, LOCATION)

OUTPUT_NAME = "EBC_dengue_embeddings_EW"

NATIONAL_LOCATION = "BR"

# Embeddings are dense and high-dimensional, so parquet only: a csv.gz of a
# 768-float column is both enormous and lossy in text form.
DEFAULT_FORMATS = ("parquet",)

# Declared as a roadmap number, not a decision. Both candidates the note names
# are 768-wide, so the pooled table's shape is stable either way.
PLANNED_DIM = 768

# Missing dependency. Named so the error message can say what to install.
REQUIRED_EXTRA = "torch, transformers"
