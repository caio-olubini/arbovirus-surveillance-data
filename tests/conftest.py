"""Shared fixtures for the pipeline tests."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

REPO = Path(__file__).resolve().parents[1]
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "sinan"
NEWS_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "news"
FEDERATIVE_UNITS = REPO / "data" / "epidemiological" / "br_federative_units.csv"
NEWS_LEXICON = REPO / "data" / "news" / "reference" / "lexico_dengue.yaml"

# Where `arboili transform sinan` writes by default. Present only once the real
# ~7 GB transformation has been run, which is why those tests are opt-in.
REAL_SERIES = REPO / "data" / "epidemiological" / "SINAN" / "SINAN_dengue_cases.parquet"


@pytest.fixture(scope="session")
def fixture_dir() -> Path:
    return FIXTURE_DIR


@pytest.fixture(scope="session")
def fu_path() -> Path:
    return FEDERATIVE_UNITS


@pytest.fixture(scope="session")
def fixture_series(tmp_path_factory: pytest.TempPathFactory) -> pl.DataFrame:
    """The full pipeline run over the committed fixtures.

    Session-scoped so the integrity checks share one transformation rather than
    rebuilding it per test.
    """
    from src.pipeline.sinan import transform

    out_dir = tmp_path_factory.mktemp("sinan_series")
    transform(
        in_dir=FIXTURE_DIR,
        out_dir=out_dir,
        fu_path=FEDERATIVE_UNITS,
        formats=["parquet"],
    )
    return pl.read_parquet(out_dir / "SINAN_dengue_cases.parquet")


@pytest.fixture(scope="session")
def real_series() -> pl.DataFrame:
    """The series built from the full SINAN archive; skips when absent."""
    if not REAL_SERIES.exists():
        pytest.skip(f"{REAL_SERIES.name} not built — run `arboili transform sinan`")
    return pl.read_parquet(REAL_SERIES)


# --- news -------------------------------------------------------------------
#
# The news fixtures are real saved pages: one era-C article, three era-B ones
# (including the page whose body was never fetched and the one where a naive
# scorer picks the "Últimas notícias" rail), plus a synthetic page that matches
# none of the known containers. See tests/fixtures/news/ and the pipeline README.


@pytest.fixture(scope="session")
def news_fixture_dir() -> Path:
    return NEWS_FIXTURE_DIR


@pytest.fixture(scope="session")
def news_corpus() -> pl.DataFrame:
    """The frozen text corpus over the committed news fixtures."""
    from src.pipeline.news.text.steps import build

    return build(NEWS_FIXTURE_DIR)


@pytest.fixture(scope="session")
def news_lexicon():
    """Braço 01's compiled lexicon — the versioned reference, not a copy."""
    from src.pipeline.news.lexicon.steps import load_lexicon

    return load_lexicon(NEWS_LEXICON)


@pytest.fixture(scope="session")
def news_matcher():
    """The state matcher, built from the shared federative-unit table."""
    from src.pipeline.news.lexicon.steps import load_uf_matcher

    return load_uf_matcher(FEDERATIVE_UNITS)


@pytest.fixture(scope="session")
def news_features(news_corpus, news_lexicon, news_matcher) -> pl.DataFrame:
    """Braço 01's (ew, location) features over the fixture corpus."""
    from src.pipeline.news.lexicon.steps import build

    return build(news_corpus, news_lexicon, news_matcher)


class FakeEncoder:
    """Deterministic stand-in for BERTimbau, for the braço 02 tests.

    The stage's real dependency is a 400 MB checkpoint and a network fetch, and
    neither belongs in the unit suite. What the tests actually exercise is the
    aggregation — masking, scoping, pooling, dispersion — so the encoder only has
    to be *some* deterministic function from text to unit vector. Seeding it from
    a CRC of the text (rather than `hash`, which is salted per process) keeps the
    vectors identical across runs and machines.
    """

    model_id = "test/fake-encoder"
    model_revision = "0" * 40

    def __init__(self, dim: int | None = None):
        from src.pipeline.news.embeddings.spec import EMBEDDING_DIM

        # The real width by default: the integrity checks assert the published
        # tables against the pinned model's 768, so a narrower fake would make
        # the fixture fail checks that production passes.
        self.dim = EMBEDDING_DIM if dim is None else dim

    def _vector(self, text: str) -> "np.ndarray":
        import zlib

        import numpy as np

        rng = np.random.default_rng(zlib.crc32(text.encode("utf-8")))
        vector = rng.standard_normal(self.dim)
        return vector / np.linalg.norm(vector)

    def encode(self, texts):
        import numpy as np

        from src.pipeline.news.embeddings.steps import Encoded

        return Encoded(
            vectors=np.stack([self._vector(text) for text in texts]).astype(np.float32),
            # Word count, not a real tokenizer: the tests only need a positive,
            # text-dependent integer that can exceed MAX_TOKENS.
            n_tokens=[len(text.split()) for text in texts],
        )


@pytest.fixture(scope="session")
def news_embedding_encoder() -> FakeEncoder:
    """Braço 02's encoder, without the checkpoint download."""
    return FakeEncoder()


@pytest.fixture(scope="session")
def news_embedding_tables(
    news_corpus, news_lexicon, news_embedding_encoder, tmp_path_factory: pytest.TempPathFactory
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Braço 02's (article, pooled) tables over the fixture corpus.

    Runs the real `transform()` — real lexicon gate, real UF matcher, real
    pooling — with only the encoder substituted.
    """
    from src.pipeline.news.embeddings import transform

    out_dir = tmp_path_factory.mktemp("news_embeddings")
    transform(
        corpus_path=_corpus_parquet(news_corpus, tmp_path_factory),
        fu_path=FEDERATIVE_UNITS,
        lexicon_path=NEWS_LEXICON,
        out_dir=out_dir,
        encoder=news_embedding_encoder,
    )
    return (
        pl.read_parquet(out_dir / "EBC_dengue_embeddings_article.parquet"),
        pl.read_parquet(out_dir / "EBC_dengue_embeddings_EW.parquet"),
    )


def _corpus_parquet(corpus: pl.DataFrame, tmp_path_factory: pytest.TempPathFactory):
    """`transform()` reads the corpus from disk, so the fixture writes one."""
    path = tmp_path_factory.mktemp("news_corpus") / "EBC_dengue_text.parquet"
    corpus.write_parquet(path)
    return path


class FakeTopicModel:
    """Deterministic stand-in for tomotopy's DMR, for the braço 03 tests.

    The real dependency is a C++ Gibbs sampler that takes minutes over the real
    corpus, and its numbers are not what these tests are about. What they exercise
    is everything *around* the fit: that coherence selects an argmax with ties
    going to the smaller k, that a week's shares add to 1, that BR is added by
    construction, that `n_articles` counts articles rather than (article, topic)
    rows. So the fake only has to be *some* deterministic function from tokens to a
    point on the simplex.

    Two deliberate properties, both load-bearing:

    * **Coherence peaks at k=15.** `select_k` needs a real argmax to find, and the
      default `K_RANGE` (5, 10, 15, 20, 25) is symmetric around 15, so the winner is
      unambiguous and a plateau test can be built by moving the peak.
    * **Topic terms are drawn from the vocabulary the fake actually saw.** The meta
      table then reads like a topic table — real corpus words, no repeats within a
      topic — so `check_unique_keys(meta, ...)` and the reader both get something
      meaningful.
    """

    PEAK_K = 15

    def __init__(
        self,
        k: int,
        family: str | None = None,
        seed: int = 42,
        iterations: int = 1000,
        min_df: int = 3,
    ) -> None:
        from src.pipeline.news.topics.spec import DEFAULT_FAMILY
        from src.pipeline.news.topics.steps import model_id

        self.k = k
        self.family = family or DEFAULT_FAMILY
        self.seed = seed
        self.iterations = iterations
        self.min_df = min_df
        self.model_id = model_id(self.family, k, seed)
        self.n_docs = 0
        self._docs: list[list[str]] = []
        self._vocab: list[str] = []
        self._shares = None

    def fit(self, docs, covariates) -> None:
        import numpy as np

        if len(docs) != len(covariates):
            raise ValueError(
                f"{len(docs)} documents but {len(covariates)} covariates; DMR needs one "
                f"period per document."
            )
        self.n_docs = len(docs)
        self._docs = [list(doc) for doc in docs]
        self._vocab = sorted({token for doc in self._docs for token in doc}) or ["vazio"]
        self._shares = np.stack([self._row(doc) for doc in self._docs]).astype(np.float32)

    def _row(self, doc: list[str]):
        """One article's topic mixture: deterministic, on the simplex, never NaN."""
        import zlib

        import numpy as np

        if not doc:
            # The same reading the real model takes: a document with no tokens
            # carries no topic information, so it gets the uniform row rather than
            # a NaN that would poison the week's mean.
            return np.full(self.k, 1.0 / self.k, dtype=np.float32)
        rng = np.random.default_rng(zlib.crc32(" ".join(doc).encode("utf-8")))
        weights = rng.random(self.k) + 1e-3
        return (weights / weights.sum()).astype(np.float32)

    def document_shares(self):
        return self._shares

    def topic_words(self, top_n: int = 15):
        size = len(self._vocab)
        take = min(top_n, size)
        words = []
        for topic in range(self.k):
            start = (topic * 3) % size
            # Consecutive indices mod the vocabulary: distinct within a topic as
            # long as `take <= size`, which is how `take` is set above.
            picks = [self._vocab[(start + i) % size] for i in range(take)]
            words.append([(term, 1.0 - 0.05 * i) for i, term in enumerate(picks)])
        return words

    def coherence(self, metric: str = "c_v", top_n: int = 10) -> float:
        """Single-peaked at `PEAK_K`, so `select_k` has an argmax to find."""
        return 1.0 - abs(self.k - self.PEAK_K) / 100.0

    def ll_per_word(self) -> float:
        """Reported in the sweep and never used to choose k — as in production."""
        return -8.0 + self.k / 1000.0


@pytest.fixture(scope="session")
def news_topic_model() -> FakeTopicModel:
    """One fitted fake, for tests that need a model and not a whole transform."""
    model = FakeTopicModel(k=3)
    model.fit([["dengue", "caso"], ["vacina", "aedes"], []], ["2011-01", "2011-01", "2011-02"])
    return model


@pytest.fixture(scope="session")
def news_topics_tables(
    news_corpus, news_lexicon, tmp_path_factory: pytest.TempPathFactory
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Braço 03's (pooled, meta, sweep) tables over the fixture corpus.

    Runs the real `transform()` — real lexicon gate, real UF matcher, real
    selection, real pooling — with only the model substituted. The default
    `K_RANGE` is kept, so the fixture also exercises the real sweep path.
    """
    from src.pipeline.news.topics import transform

    out_dir = tmp_path_factory.mktemp("news_topics")
    transform(
        corpus_path=_corpus_parquet(news_corpus, tmp_path_factory),
        fu_path=FEDERATIVE_UNITS,
        lexicon_path=NEWS_LEXICON,
        out_dir=out_dir,
        model_factory=lambda k: FakeTopicModel(k),
    )
    return (
        pl.read_parquet(out_dir / "EBC_dengue_topics_EW.parquet"),
        pl.read_parquet(out_dir / "EBC_dengue_topics_meta.parquet"),
        pl.read_parquet(out_dir / "EBC_dengue_topics_sweep.parquet"),
    )
