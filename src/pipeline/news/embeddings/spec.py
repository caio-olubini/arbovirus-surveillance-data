"""Schema of the dense-embedding tables (braço 02) and its bracket of configurations.

Braço 02 stopped being one configuration on 2026-10-14. `notes/00` fixes 01/02/03
as *competing representations* and requires that only the representation vary —
but a single dense configuration makes a null result uninterpretable, because "the
representation lost" cannot be told apart from "this particular encoder was too
weak". The braço therefore publishes a **bracket**: several unsupervised,
no-training configurations of the same representation, read as a range rather
than as a point.

Everything in the bracket is untrained and unlabelled, which is the footing braço
01's hand-built lexicon is already on. Nothing is fine-tuned: fine-tuning would
make the encoder a trained model of dengue news, which is a different
representation from the one the comparison fixes, and it would give braço 02 a
supervision the other two braços do not have.

Two tables per configuration, because pooling is lossy and the per-article
vectors are what any later re-pooling or error analysis needs:

    EBC_dengue_embeddings[_<variant>]_article   one row per article
    EBC_dengue_embeddings[_<variant>]_EW        one row per (ew, location), pooled

The base configuration keeps the unsuffixed names: it is the published braço-02
table, and the variants are suffixed so the bracket is self-describing on disk.

Embeddings are dense and high-dimensional, so the outputs are parquet only: a
csv.gz of a 768-float column is both enormous and lossy in text form.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- per-article table ------------------------------------------------------

ARTICLE_ID = "article_id"
EW = "ew"
EMBEDDING = "embedding"
# Which configuration produced this row. The braço now emits one article table
# per variant, and the filename says which — but a table read on its own should
# not depend on its name to be interpretable. It sits with the other provenance
# columns rather than in the payload.
VARIANT = "variant"
MODEL_ID = "model_id"
MODEL_REVISION = "model_revision"
DIM = "dim"
# Tokens the article produced *before* truncation. Carried per row because
# `max_tokens` truncation is lossy and silent: a 34,960-character era-B article
# and a 163-character era-C note both become one vector, and only this column
# says which of them lost text. It is also the column a later chunked encoder
# would key on to re-encode only the truncated tail.
N_TOKENS = "n_tokens"

# Keys first, then provenance, then the payload last — the same ordering rule the
# frozen text corpus follows, so a table printed without truncation shows the
# identity of a row before a wall of floats.
ARTICLE_OUTPUT_COLUMNS = (
    ARTICLE_ID,
    EW,
    EMBEDDING,
    VARIANT,
    MODEL_ID,
    MODEL_REVISION,
    DIM,
    N_TOKENS,
)
ARTICLE_GROUP_KEYS = (ARTICLE_ID,)

# --- pooled table -----------------------------------------------------------

LOCATION = "location"
EMB_MEAN = "emb_mean"
N_ARTICLES = "n_articles"

# `emb_std` used to sit here and was **removed on 2026-10-14**. For L2-normalized
# article vectors the per-dimension standard deviation obeys
#
#     ‖std‖² = (1/n) Σᵢ ‖vᵢ − m‖² = 1 − ‖m‖²
#
# (the parallel-axis identity on the unit sphere), so the published scalar was an
# exact deterministic function of `emb_mean` — measured at a maximum deviation of
# 1.6e-06 over the 2,073 real rows with n > 1. It carried no information the mean
# did not already carry, and its documented "undefined on 59.8% of rows" problem
# was a symptom of that identity rather than a separate defect: one article gives
# ‖m‖ = 1 and therefore exactly 0. No scalar dispersion of unit vectors escapes
# this — mean pairwise cosine distance is 1 − ‖m‖² too — so the column was not
# repaired, it was deleted, and the dispersion hypothesis is now read as being
# absorbed by the mean rather than as a feature of its own.
OUTPUT_COLUMNS = (EW, LOCATION, EMB_MEAN, N_ARTICLES)

GROUP_KEYS = (EW, LOCATION)

# National rows, same code the other news braços and Google Trends use.
NATIONAL_LOCATION = "BR"

# --- table names ------------------------------------------------------------

TABLE_STEM = "EBC_dengue_embeddings"
ARTICLE_TABLE_SUFFIX = "article"
POOLED_TABLE_SUFFIX = "EW"


def table_names(variant_id: str) -> tuple[str, str]:
    """(article table, pooled table) for a configuration.

    The base configuration keeps the historical unsuffixed names, because that
    table is the published braço-02 artefact and renaming it would invalidate
    every reference to it for no gain. Every variant is suffixed, so a directory
    listing shows the whole bracket.
    """
    if variant_id == BASE_VARIANT_ID:
        return (
            f"{TABLE_STEM}_{ARTICLE_TABLE_SUFFIX}",
            f"{TABLE_STEM}_{POOLED_TABLE_SUFFIX}",
        )
    slug = variant_id.replace("-", "_")
    return (
        f"{TABLE_STEM}_{slug}_{ARTICLE_TABLE_SUFFIX}",
        f"{TABLE_STEM}_{slug}_{POOLED_TABLE_SUFFIX}",
    )


# --- the bracket ------------------------------------------------------------

# Pooling is not a free parameter to hold constant across the bracket. BGE-M3's
# dense embedding is the `[CLS]` token (its `1_Pooling/config.json` says
# `pooling_mode_cls_token: true`), while E5 and Serafim are masked means. Forcing
# one pooling on all of them would measure a configuration no one uses and would
# make a weak BGE-M3 uninterpretable — the same mistake the bracket exists to
# avoid. Each encoder is therefore read the way its authors published it, and the
# pooling is declared per variant rather than fixed.

POOLING_MEAN = "mean"
POOLING_CLS = "cls"

INPUT_TITLE_BODY = "title_body"
INPUT_TITLE = "title"

# E5 is trained with instruction prefixes; documents take `passage: `, queries
# take `query: `. These are articles, so they are passages.
E5_PREFIX = "passage: "


@dataclass(frozen=True)
class Variant:
    """One configuration of the dense representation.

    `max_tokens` is the encoder's own window, except that the bracket fixes it at
    512 for every model that can take it, so a gain cannot come from one encoder
    silently reading more text than another. Serafim is the declared exception:
    its window is 128, so it reads title and lead rather than the whole body, and
    that is stated rather than hidden behind a uniform number.
    """

    id: str
    label: str
    model_name: str
    model_revision: str
    pooling: str
    prefix: str
    input_fields: str
    max_tokens: int
    normalize: bool = True
    whitening: bool = False
    note: str = ""

    @property
    def is_base(self) -> bool:
        return self.id == BASE_VARIANT_ID


BASE_VARIANT_ID = "bertimbau-mean"

# The base configuration: the PT-BR standard, frozen and pinned by commit, read
# with the pooling every sentence-embedding recipe uses. It is the point the rest
# of the bracket is measured against, and the one the published table carries.
BERTIMBAU = "neuralmind/bert-base-portuguese-cased"
BERTIMBAU_REVISION = "94d69c95f98f7d5b2a8700c420230ae10def0baa"

VARIANTS: dict[str, Variant] = {
    "bertimbau-mean": Variant(
        id="bertimbau-mean",
        label="BERTimbau · masked mean",
        model_name=BERTIMBAU,
        model_revision=BERTIMBAU_REVISION,
        pooling=POOLING_MEAN,
        prefix="",
        input_fields=INPUT_TITLE_BODY,
        max_tokens=512,
        note=(
            "The base. Pre-trained on brWaC, a general web corpus, which is what "
            "news is. MTEB-BR (arXiv:2607.04581) puts BERTimbau-base 9th of 93 on "
            "native PT-BR classification while it is weak on retrieval — and the "
            "question here is closer to classification than to retrieval, so this "
            "is a defensible point rather than a straw man."
        ),
    ),
    "bertimbau-whitening": Variant(
        id="bertimbau-whitening",
        label="BERTimbau · masked mean · whitening",
        model_name=BERTIMBAU,
        model_revision=BERTIMBAU_REVISION,
        pooling=POOLING_MEAN,
        prefix="",
        input_fields=INPUT_TITLE_BODY,
        max_tokens=512,
        whitening=True,
        note=(
            "The one documented weakness of mean pooling without fine-tuning is "
            "anisotropy: token vectors crowd into a narrow cone, so unrelated "
            "sentences look alike (Ethayarajh 2019, doi:10.18653/v1/D19-1006). "
            "Whitening (Su 2021, arXiv:2103.15316; WhiteningBERT, "
            "doi:10.18653/v1/2021.findings-emnlp.23) is the fix that needs no "
            "labels and no training, so it stays inside the bracket's footing."
        ),
    ),
    "e5-large": Variant(
        id="e5-large",
        label="multilingual E5-large · masked mean",
        model_name="intfloat/multilingual-e5-large",
        model_revision="3d7cfbdacd47fdda877c5cd8a79fbcc4f2a574f3",
        pooling=POOLING_MEAN,
        prefix=E5_PREFIX,
        input_fields=INPUT_TITLE_BODY,
        max_tokens=512,
        note=(
            "The strongest publicly available multilingual model on the MMTEB "
            "suite (arXiv:2502.13595). Its pretraining cutoff is not documented "
            "on the model card, so it is admitted with the leakage risk declared "
            "and validated temporally — protocol 00 asks for a known cutoff and "
            "this variant does not have one."
        ),
    ),
    "bge-m3": Variant(
        id="bge-m3",
        label="BGE-M3 · CLS",
        model_name="BAAI/bge-m3",
        model_revision="5617a9f61b028005a4858fdac845db406aefb181",
        pooling=POOLING_CLS,
        prefix="",
        input_fields=INPUT_TITLE_BODY,
        max_tokens=512,
        note=(
            "Read with CLS pooling, which is how its dense embedding is defined; "
            "its window is 8192 but the bracket holds it at 512 so the encoder is "
            "the only thing that varies. Same undocumented cutoff as E5."
        ),
    ),
    "title-only": Variant(
        id="title-only",
        label="BERTimbau · title only",
        model_name=BERTIMBAU,
        model_revision=BERTIMBAU_REVISION,
        pooling=POOLING_MEAN,
        prefix="",
        input_fields=INPUT_TITLE,
        max_tokens=512,
        note=(
            "The floor: the least text a dense reading can be given, with no "
            "truncation at all. If the bracket cannot beat counting articles even "
            "here, the failure is not the 512-token window."
        ),
    ),
    "serafim-title": Variant(
        id="serafim-title",
        label="Serafim PT · title + lead (128 tokens)",
        model_name="PORTULAN/serafim-100m-portuguese-pt-sentence-encoder",
        model_revision="e7a455266e3436f89d9509364ffb1a01fd9df999",
        pooling=POOLING_MEAN,
        prefix="",
        input_fields=INPUT_TITLE_BODY,
        max_tokens=128,
        note=(
            "The only encoder in the bracket trained specifically for Portuguese "
            "(Gomes et al. 2024, arXiv:2407.19527; MIT). Its window is 128 tokens, "
            "so it reads title and lead rather than the whole body — the declared "
            "exception to the 512 rule, and a structural disadvantage that is "
            "stated rather than smoothed over."
        ),
    ),
}

# The order the bracket is reported in: the base first, then its unsupervised
# correction, then the encoder swap, then the two narrow configurations.
VARIANT_ORDER: tuple[str, ...] = (
    "bertimbau-mean",
    "bertimbau-whitening",
    "e5-large",
    "bge-m3",
    "title-only",
    "serafim-title",
)


def variant(variant_id: str) -> Variant:
    """Look one up, with the available ids in the error rather than a bare KeyError."""
    try:
        return VARIANTS[variant_id]
    except KeyError:
        known = ", ".join(VARIANT_ORDER)
        raise KeyError(
            f"Unknown braço-02 variant {variant_id!r}. Known: {known}."
        ) from None


# --- back-compatible aliases ------------------------------------------------
# The base configuration's values, under the names the rest of the braço (and the
# notebook) already imports. They describe the base variant and nothing else —
# anything variant-aware should read `Variant` fields instead.
MODEL_NAME = VARIANTS[BASE_VARIANT_ID].model_name
MODEL_REVISION_SHA = VARIANTS[BASE_VARIANT_ID].model_revision
EMBEDDING_DIM = 768
MAX_TOKENS = VARIANTS[BASE_VARIANT_ID].max_tokens

# --- outputs ----------------------------------------------------------------

FORMAT_PARQUET = "parquet"
DEFAULT_FORMATS = (FORMAT_PARQUET,)

# The optional-dependency group in pyproject.toml that carries torch and
# transformers. Named so the error message can say exactly what to install.
REQUIRED_EXTRA = "embeddings"

__all__ = [
    "ARTICLE_GROUP_KEYS",
    "ARTICLE_ID",
    "ARTICLE_OUTPUT_COLUMNS",
    "BASE_VARIANT_ID",
    "BERTIMBAU",
    "BERTIMBAU_REVISION",
    "DEFAULT_FORMATS",
    "DIM",
    "EMBEDDING",
    "EMBEDDING_DIM",
    "EMB_MEAN",
    "EW",
    "E5_PREFIX",
    "FORMAT_PARQUET",
    "GROUP_KEYS",
    "INPUT_TITLE",
    "INPUT_TITLE_BODY",
    "LOCATION",
    "MAX_TOKENS",
    "MODEL_ID",
    "MODEL_NAME",
    "MODEL_REVISION",
    "MODEL_REVISION_SHA",
    "NATIONAL_LOCATION",
    "N_ARTICLES",
    "N_TOKENS",
    "OUTPUT_COLUMNS",
    "POOLING_CLS",
    "POOLING_MEAN",
    "REQUIRED_EXTRA",
    "VARIANT",
    "VARIANTS",
    "VARIANT_ORDER",
    "Variant",
    "table_names",
    "variant",
]
