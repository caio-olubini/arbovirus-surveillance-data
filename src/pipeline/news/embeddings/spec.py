"""Schema of the dense-embedding tables (braço 02) and its frozen model choice.

Two tables, because pooling is lossy and the per-article vectors are what any
later re-pooling or error analysis needs:

    EBC_dengue_embeddings_article   one row per article
    EBC_dengue_embeddings_EW        one row per (ew, location), pooled

The encoder is pinned here by id *and* by revision. `notes/02` left the choice
open (BERTimbau vs BioBERTpt); it was decided on 2026-10-13 in favour of
BERTimbau — the PT-BR standard, pre-trained on brWaC, a general web corpus,
which is what news is. BioBERTpt's vocabulary is clinical and its training
corpus is clinical notes and SciELO abstracts, not press prose. The revision is
a commit sha rather than a branch, so an embedding computed today can be
recomputed byte-for-byte later; a branch would silently move under the artifact.

Embeddings are dense and high-dimensional, so the outputs are parquet only: a
csv.gz of a 768-float column is both enormous and lossy in text form.
"""

from __future__ import annotations

# --- per-article table ------------------------------------------------------

ARTICLE_ID = "article_id"
EW = "ew"
EMBEDDING = "embedding"
MODEL_ID = "model_id"
MODEL_REVISION = "model_revision"
DIM = "dim"
# Tokens the article produced *before* truncation. Carried per row because
# `MAX_TOKENS` truncation is lossy and silent: a 34,960-character era-B article
# and a 163-character era-C note both become one 768-vector, and only this
# column says which of them lost text. It is also the column a later chunked
# encoder would key on to re-encode only the truncated tail.
N_TOKENS = "n_tokens"

# Keys first, then provenance, then the payload last — the same ordering rule the
# frozen text corpus follows, so a table printed without truncation shows the
# identity of a row before a wall of floats.
ARTICLE_OUTPUT_COLUMNS = (ARTICLE_ID, EW, EMBEDDING, MODEL_ID, MODEL_REVISION, DIM, N_TOKENS)
ARTICLE_GROUP_KEYS = (ARTICLE_ID,)
ARTICLE_OUTPUT_NAME = "EBC_dengue_embeddings_article"

# --- pooled table -----------------------------------------------------------

LOCATION = "location"
EMB_MEAN = "emb_mean"
EMB_STD = "emb_std"
N_ARTICLES = "n_articles"

OUTPUT_COLUMNS = (EW, LOCATION, EMB_MEAN, EMB_STD, N_ARTICLES)
GROUP_KEYS = (EW, LOCATION)
OUTPUT_NAME = "EBC_dengue_embeddings_EW"

# National rows, same code the other news braços and Google Trends use.
NATIONAL_LOCATION = "BR"

# --- the frozen encoder -----------------------------------------------------

MODEL_NAME = "neuralmind/bert-base-portuguese-cased"
# Named `_SHA` and not `MODEL_REVISION`, which is the *column* above: a single
# constant cannot be both, and silently shadowing one with the other is how the
# column ends up named after a commit hash.
MODEL_REVISION_SHA = "94d69c95f98f7d5b2a8700c420230ae10def0baa"

# Declared by the model, not chosen here: it is what makes the published tables
# self-describing, and what `check_dim_consistent` asserts the array width against.
EMBEDDING_DIM = 768

# BERT's positional limit. Articles above it are truncated, and `n_tokens` is
# how that stays visible instead of silent.
MAX_TOKENS = 512

# --- outputs ----------------------------------------------------------------

FORMAT_PARQUET = "parquet"
DEFAULT_FORMATS = (FORMAT_PARQUET,)

# The optional-dependency group in pyproject.toml that carries torch and
# transformers. Named so the error message can say exactly what to install.
REQUIRED_EXTRA = "embeddings"
