"""Temporal topic modeling over the frozen text corpus → weekly topic shares (braço 03).

The representation: fit one topic model over the whole corpus with the *period* as
a document covariate (DMR), then publish the mean topic mixture of each week's
articles. The hypothesis is in `notes/03`: a week's coverage is not a block — it
mixes cases, vector, public policy, vaccine, hospital collapse — and tracking which
mixture a week carries says **what** the press was talking about, where braço 01's
`news_volume` only says **how much**.

Two things are shared with braços 01 and 02 on purpose, because protocol 00 fixes
them as common ground rather than as part of any representation:

* **The article set.** The same `lang_guess == "pt"` and dengue-term gates, via
  `news.corpus` — so all three braços see the same articles and the comparison
  isolates the representation instead of the filter.
* **The geo scoping.** The same `UfMatcher`-based, mention-level scoping, also from
  `news.corpus`.

What is specific to this braço is the *fit*: `k` is selected by coherence over a
swept range (`select_k`), and the covariate makes the model temporal. Both are
recorded rather than assumed — the sweep is written out as its own table, and the
selected `k` travels in the `model_id`.

The one approximation worth knowing about: **a topic model cannot see a document
twice.** DMR is fit once over the whole corpus, so the topics are shaped by all 24
years at once — including 2024, the record year. `notes/03` names this risk
("um tópico ajustado no corpus inteiro pode ser dominado por 2024"); the sweep
table and the per-topic coherence are what make it visible, and a rolling-origin
refit is the declared next step if it turns out to matter.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

import numpy as np
import polars as pl

from ..common import strip_accents
from ..corpus import LOCATIONS, article_input
from ..text.spec import ARTICLE_ID, EW as CORPUS_EW, TEXT, TITLE
from .spec import (
    COHERENCE,
    COHERENCE_METRIC,
    COHERENCE_TOP_N,
    COVARIATE_GRAIN,
    COVARIATE_GRAINS,
    DEFAULT_FAMILY,
    DEFAULT_ITERATIONS,
    DEFAULT_SEED,
    EW,
    FAMILY_DMR,
    FAMILY_LDA,
    GRAIN_MONTH,
    GRAIN_WEEK,
    GRAIN_YEAR,
    LL_PER_WORD,
    LOCATION,
    META_OUTPUT_COLUMNS,
    MIN_DF,
    MIN_TOKEN_LEN,
    MODEL_FAMILIES,
    MODEL_ID,
    MODEL_ID_PREFIX,
    NATIONAL_LOCATION,
    N_ARTICLES,
    OUTPUT_COLUMNS,
    REQUIRED_EXTRA,
    SELECTED,
    SHARE,
    STOPWORDS_PT,
    SWEEP_OUTPUT_COLUMNS,
    TERM,
    TOKEN_PATTERN,
    TOPIC_ID,
    TOP_TERMS,
    WEIGHT,
)

log = logging.getLogger("pipeline.news.topics")

_TOKEN = re.compile(TOKEN_PATTERN)
_STOPWORDS = frozenset(STOPWORDS_PT)


class MissingExtraError(RuntimeError):
    """The optional `topics` extra is not installed.

    Raised instead of `ImportError` so the CLI can print one sentence rather than
    a traceback — the same contract braço 02's `MissingExtraError` follows.
    """


def _tomotopy() -> Any:
    """Import tomotopy on demand, with the install instruction if it is absent.

    Deferred rather than module-level so that importing this module — which the
    package `__init__` does, and which the unit tests do without the extra — never
    needs the dependency.
    """
    try:
        import tomotopy
    except ImportError as error:  # pragma: no cover - depends on the environment
        raise MissingExtraError(
            f"Braço 03 needs the optional `{REQUIRED_EXTRA}` extra (tomotopy). "
            f"Install it with:\n\n    uv sync --extra {REQUIRED_EXTRA}\n"
        ) from error
    return tomotopy


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    """One article's tokens, ready for the model's vocabulary.

    Accent-fold, keep letters, drop stopwords and one/two-letter tokens. No
    lemmatizer and no POS tagger: `notes/03` proposed spaCy's `pt_core_news`, and
    it was set aside because it would add a several-hundred-megabyte model as the
    only consumer of a new NLP runtime in a repository whose other news braço is
    pure regex. The cost of dropping it is recall on rare inflections, and `MIN_DF`
    prunes those out of the vocabulary anyway.

    Folding before matching is what makes the stopword list one flat tuple:
    `não`/`nao` and `está`/`esta` collapse to one entry each, so the list does not
    have to enumerate every accented spelling the corpus contains.
    """
    return [
        token
        for token in _TOKEN.findall(strip_accents(text))
        if len(token) >= MIN_TOKEN_LEN and token not in _STOPWORDS
    ]


def tokenize_corpus(corpus: pl.DataFrame) -> list[list[str]]:
    """Tokens for every row, in the order the corpus is given.

    Title and body joined, exactly as braços 01 and 02 read them — the headline is
    where a week's framing lives, so dropping it would lose the most topical
    sentence of the article.
    """
    return [
        tokenize(article_input(title, text))
        for title, text in corpus.select(TITLE, TEXT).iter_rows()
    ]


def covariate_bucket(ew: date, grain: str = COVARIATE_GRAIN) -> str:
    """The DMR metadata string for one epidemiological week.

    `month` is the default and not the weekly grain the tables are keyed by,
    because DMR regresses prevalence on the covariate's levels: 965 weekly levels
    against ~4.5 articles each would be an over-parameterised fit, while ~290
    monthly levels get ~15. The published grain stays weekly either way.
    """
    if grain == GRAIN_MONTH:
        return f"{ew.year:04d}-{ew.month:02d}"
    if grain == GRAIN_YEAR:
        return f"{ew.year:04d}"
    if grain == GRAIN_WEEK:
        return ew.isoformat()
    raise ValueError(f"Unknown covariate grain {grain!r}; expected one of {COVARIATE_GRAINS}.")


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------

def model_id(family: str, k: int, seed: int) -> str:
    """Self-describing run identifier, carried in every published row.

    `k` and `seed` are *in* the string because they are the two choices that change
    what the numbers mean: `k` fixes how many rows a week has, and `seed` fixes
    which fit produced them. The library version is pinned in `pyproject.toml` and
    reported in the transform result — putting it here as well would make the id
    churn on a patch release without telling the reader anything the lock file does
    not already say.
    """
    return f"{MODEL_ID_PREFIX}-{family}-k{k}-seed{seed}"


class TopicModel(Protocol):
    """What the stage needs from a model, so tests and the notebook can fake it.

    The real implementation is `TomotopyTopicModel`; the unit tests and the
    walkthrough notebook pass a deterministic stand-in instead, which keeps the
    selection, aggregation and integrity logic testable without the dependency.
    """

    model_id: str
    k: int
    n_docs: int

    def fit(self, docs: Sequence[Sequence[str]], covariates: Sequence[str]) -> None: ...
    def document_shares(self) -> np.ndarray: ...
    def topic_words(self, top_n: int) -> list[list[tuple[str, float]]]: ...
    def coherence(self, metric: str, top_n: int) -> float: ...
    def ll_per_word(self) -> float: ...


class TomotopyTopicModel:
    """A tomotopy DMR (or LDA) fit, behind the `TopicModel` protocol.

    DMR conditions topic *prevalence* on a per-document covariate — here the period
    — which is the mechanism STM extends. LDA is the same training loop with the
    covariate dropped, so running the baseline costs a parameter and not a second
    stage.

    **Reproducibility needs `seed` *and* `workers=1`.** tomotopy warns that a fixed
    seed does not fix the result when the Gibbs sampler runs on more than one
    worker, because the scheduling becomes nondeterministic. Pinning the seed alone
    would look reproducible and not be, which is the same trap braço 02 avoided by
    pinning a commit sha instead of a branch name.
    """

    def __init__(
        self,
        k: int,
        family: str = DEFAULT_FAMILY,
        seed: int = DEFAULT_SEED,
        iterations: int = DEFAULT_ITERATIONS,
        min_df: int = MIN_DF,
    ) -> None:
        if family not in MODEL_FAMILIES:
            raise ValueError(f"Unknown model family {family!r}; expected one of {MODEL_FAMILIES}.")
        self.k = k
        self.family = family
        self.seed = seed
        self.iterations = iterations
        self.min_df = min_df
        self.model_id = model_id(family, k, seed)
        self.n_docs = 0
        self._model: Any = None
        # Indices of the documents that actually entered the fit. A document whose
        # tokens are all stopwords cannot be added, and `document_shares` has to
        # put its row back in the right place.
        self._added: list[int] = []

    def fit(self, docs: Sequence[Sequence[str]], covariates: Sequence[str]) -> None:
        if len(docs) != len(covariates):
            raise ValueError(
                f"{len(docs)} documents but {len(covariates)} covariates; DMR needs one "
                f"period per document."
            )
        tomotopy = _tomotopy()
        model_cls = tomotopy.DMRModel if self.family == FAMILY_DMR else tomotopy.LDAModel
        self._model = model_cls(k=self.k, seed=self.seed, min_df=self.min_df)
        self.n_docs = len(docs)
        self._added = []
        for index, words in enumerate(docs):
            if not words:
                continue
            if self.family == FAMILY_DMR:
                self._model.add_doc(words, metadata=covariates[index])
            else:
                self._model.add_doc(words)
            self._added.append(index)
        if not self._added:
            raise ValueError("Every document tokenized to nothing; there is no model to fit.")
        self._model.train(self.iterations, workers=1)
        log.info(
            "%s: %d/%d documents, %d vocabulary terms",
            self.model_id, len(self._added), self.n_docs, self._model.num_vocabs,
        )

    def document_shares(self) -> np.ndarray:
        """(n_docs, k) topic distribution per article.

        Documents that tokenized to nothing get a uniform row rather than being
        dropped: they are still in the article set protocol 00 fixes, so they must
        still count toward `n_articles`, and a uniform distribution is the honest
        reading of "this document carries no topic information" — it leaves the
        week's mean where it was instead of inventing a lean toward one topic.
        """
        shares = np.full((self.n_docs, self.k), 1.0 / self.k, dtype=np.float32)
        for row, doc in enumerate(self._model.docs):
            shares[self._added[row]] = doc.get_topic_dist()
        return shares

    def topic_words(self, top_n: int = TOP_TERMS) -> list[list[tuple[str, float]]]:
        return [self._model.get_topic_words(topic, top_n=top_n) for topic in range(self.k)]

    def coherence(self, metric: str = COHERENCE_METRIC, top_n: int = COHERENCE_TOP_N) -> float:
        tomotopy = _tomotopy()
        return float(
            tomotopy.coherence.Coherence(self._model, coherence=metric, top_n=top_n).get_score()
        )

    def ll_per_word(self) -> float:
        """Held-out-style likelihood per word.

        Reported in the sweep table and deliberately **not** used to choose k:
        `notes/03` fixes coherence as the criterion, and likelihood is known to
        favour larger k. Writing it down anyway is what lets a reader check that
        the two disagree.
        """
        return float(self._model.ll_per_word)


ModelFactory = Callable[[int], TopicModel]


def load_model_factory(
    family: str = DEFAULT_FAMILY,
    seed: int = DEFAULT_SEED,
    iterations: int = DEFAULT_ITERATIONS,
    min_df: int = MIN_DF,
) -> ModelFactory:
    """The production factory: one `TomotopyTopicModel` per candidate k.

    Imports tomotopy eagerly so a missing extra fails here, before the corpus is
    read and tokenized, rather than after — the same fail-fast the CLI relies on.
    """
    _tomotopy()
    if family not in MODEL_FAMILIES:
        raise ValueError(f"Unknown model family {family!r}; expected one of {MODEL_FAMILIES}.")

    def factory(k: int) -> TopicModel:
        return TomotopyTopicModel(
            k=k, family=family, seed=seed, iterations=iterations, min_df=min_df
        )

    return factory


# ---------------------------------------------------------------------------
# k selection
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KSweepRow:
    """One candidate k and what it scored."""

    model_id: str
    k: int
    coherence: float
    ll_per_word: float


@dataclass
class KSweep:
    """The whole sweep, plus the fitted model that won it.

    Both halves are kept because they answer different questions: `rows` is the
    evidence a reader checks the choice against, and `best` is the fit that gets
    published — refitting it would be wasted work and, worse, could differ.
    """

    rows: list[KSweepRow] = field(default_factory=list)
    best: TopicModel | None = None

    @property
    def best_k(self) -> int:
        if self.best is None:
            raise ValueError("Empty sweep: no model was fitted.")
        return self.best.k

    @property
    def best_coherence(self) -> float:
        return max(row.coherence for row in self.rows)


def select_k(
    docs: Sequence[Sequence[str]],
    covariates: Sequence[str],
    k_range: Sequence[int],
    factory: ModelFactory,
    metric: str = COHERENCE_METRIC,
    top_n: int = COHERENCE_TOP_N,
) -> KSweep:
    """Fit one model per candidate k and keep the most coherent.

    Coherence, never perplexity — `notes/03` and Greene 2014 both fix that, and the
    reason is that likelihood rises with k almost mechanically while coherence does
    not. Ties go to the **smaller** k: the sweep is evaluated in ascending order and
    only a strictly better score displaces the incumbent, so an uninformative
    plateau resolves to the more parsimonious model instead of the largest one.
    """
    sweep = KSweep()
    best_score = float("-inf")
    for k in k_range:
        model = factory(k)
        model.fit(docs, covariates)
        score = model.coherence(metric, top_n)
        sweep.rows.append(
            KSweepRow(
                model_id=model.model_id,
                k=k,
                coherence=score,
                ll_per_word=model.ll_per_word(),
            )
        )
        log.info("%s: coherence(%s)=%.4f", model.model_id, metric, score)
        if score > best_score:
            best_score = score
            sweep.best = model
    if sweep.best is None:
        raise ValueError(f"k_range {list(k_range)} is empty; there is nothing to select.")
    return sweep


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

SHARE_SCHEMA: dict[str, pl.DataType] = {
    EW: pl.Date,
    LOCATION: pl.String,
    TOPIC_ID: pl.Int64,
    SHARE: pl.Float32,
    N_ARTICLES: pl.Int64,
    MODEL_ID: pl.String,
}

META_SCHEMA: dict[str, pl.DataType] = {
    MODEL_ID: pl.String,
    TOPIC_ID: pl.Int64,
    TERM: pl.String,
    WEIGHT: pl.Float32,
}

SWEEP_SCHEMA: dict[str, pl.DataType] = {
    MODEL_ID: pl.String,
    TOPIC_ID: pl.Int64,
    COHERENCE: pl.Float32,
    LL_PER_WORD: pl.Float32,
    SELECTED: pl.Boolean,
}


def pool_shares(
    article_ids: Sequence[str],
    ews: Sequence[date],
    shares: np.ndarray,
    locations: pl.DataFrame,
    model_id_value: str,
) -> pl.DataFrame:
    """Mean topic mixture per (ew, location), BR included.

    The same aggregation contract braço 02 uses: every article contributes to BR,
    and also to each UF it names, so one article can land in several rows of the
    same week. The mean is unweighted, so each *article* speaks once regardless of
    how long it is — a 34,960-character era-B feature and a 163-character era-C note
    are one voice each, which is what "what was the press talking about" means.

    Only observed pairs are emitted. A week with no article is *absent*, not a row
    of zeros: a zero share vector is not a point in the simplex and would read as
    "coverage that says nothing" rather than "no coverage". The consumer left-joins
    onto the target calendar exactly as it does for braços 01 and 02.

    Shares sum to 1 within a (ew, location) by construction, because each article's
    row is a distribution and the mean of distributions is a distribution. That is
    the invariant `check_shares_sum_to_one` asserts.
    """
    n_docs, k = shares.shape
    if n_docs == 0:
        return pl.DataFrame(schema=SHARE_SCHEMA)

    long = pl.DataFrame(
        {
            ARTICLE_ID: [article_id for article_id in article_ids for _ in range(k)],
            EW: [ew for ew in ews for _ in range(k)],
            TOPIC_ID: list(range(k)) * n_docs,
            SHARE: shares.reshape(-1).astype(np.float32).tolist(),
        }
    )
    pairs = (
        long.join(locations, on=ARTICLE_ID, how="inner")
        .with_columns(
            pl.concat_list(
                pl.col(LOCATIONS), pl.lit([NATIONAL_LOCATION], dtype=pl.List(pl.String))
            ).alias(LOCATIONS)
        )
        .explode(LOCATIONS)
        .rename({LOCATIONS: LOCATION})
    )

    # Counted on distinct articles, not on rows: the long table has one row per
    # (article, topic), so a plain count would multiply the week's article count by
    # k and report a coverage figure that is off by an order of magnitude.
    # `pl.len()` yields u32, while `SHARE_SCHEMA` declares Int64 — and the
    # empty-frame branch above returns exactly that declared schema. Casting keeps
    # the two branches, and the declaration and the artifact, from disagreeing on
    # the one column that is a count.
    counts = (
        pairs.select(EW, LOCATION, ARTICLE_ID)
        .unique()
        .group_by(EW, LOCATION)
        .agg(pl.len().cast(pl.Int64).alias(N_ARTICLES))
    )
    means = pairs.group_by(EW, LOCATION, TOPIC_ID).agg(
        pl.col(SHARE).mean().cast(pl.Float32).alias(SHARE)
    )
    return (
        means.join(counts, on=[EW, LOCATION], how="left")
        .with_columns(pl.lit(model_id_value).alias(MODEL_ID))
        .select(OUTPUT_COLUMNS)
        .sort(EW, LOCATION, TOPIC_ID)
    )


def topic_meta(model: TopicModel, model_id_value: str, top_n: int = TOP_TERMS) -> pl.DataFrame:
    """The topic → term → weight table a human reads to know what a topic *is*.

    Not optional: "topic 7 predicts dengue" is not a finding anyone can check, so
    every topic is published with its defining terms.
    """
    rows = [
        {
            MODEL_ID: model_id_value,
            TOPIC_ID: topic_id,
            TERM: term,
            WEIGHT: float(weight),
        }
        for topic_id, words in enumerate(model.topic_words(top_n))
        for term, weight in words
    ]
    return pl.DataFrame(rows, schema=META_SCHEMA).select(META_OUTPUT_COLUMNS)


def sweep_table(sweep: KSweep) -> pl.DataFrame:
    """The selection evidence, one row per candidate k."""
    rows = [
        {
            MODEL_ID: row.model_id,
            TOPIC_ID: row.k,
            COHERENCE: float(row.coherence),
            LL_PER_WORD: float(row.ll_per_word),
            SELECTED: row.k == sweep.best_k,
        }
        for row in sweep.rows
    ]
    return pl.DataFrame(rows, schema=SWEEP_SCHEMA).select(SWEEP_OUTPUT_COLUMNS)


def article_frame(corpus: pl.DataFrame) -> tuple[list[str], list[date]]:
    """(article ids, epi weeks) in corpus order — the row identity for pooling."""
    rows = corpus.select(ARTICLE_ID, CORPUS_EW).iter_rows()
    records = list(rows)
    return [row[0] for row in records], [row[1] for row in records]


__all__ = [
    "KSweep",
    "KSweepRow",
    "META_SCHEMA",
    "MissingExtraError",
    "ModelFactory",
    "SHARE_SCHEMA",
    "SWEEP_SCHEMA",
    "TomotopyTopicModel",
    "TopicModel",
    "article_frame",
    "covariate_bucket",
    "load_model_factory",
    "model_id",
    "pool_shares",
    "select_k",
    "sweep_table",
    "tokenize",
    "tokenize_corpus",
    "topic_meta",
]
