"""Braço 03's tokenization, k-selection and pooling.

The model is faked (see `tests/conftest.py`), because the real one is a C++ Gibbs
sampler and what these tests are about is everything *around* it: that the tokenizer
folds accents and drops stopwords without dropping dengue vocabulary, that `select_k`
picks the most coherent candidate and resolves a plateau toward the smaller k, that a
week's shares form a distribution, and that `n_articles` counts articles rather than
(article, topic) rows.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import polars as pl
import pytest

from src.pipeline.news.topics.spec import (
    GRAIN_MONTH,
    GRAIN_WEEK,
    GRAIN_YEAR,
    MODEL_ID,
    NATIONAL_LOCATION,
    N_ARTICLES,
    OUTPUT_COLUMNS,
    SHARE,
    TOPIC_ID,
    TOP_TERMS,
)
from src.pipeline.news.topics.steps import (
    META_SCHEMA,
    SHARE_SCHEMA,
    KSweep,
    KSweepRow,
    TomotopyTopicModel,
    covariate_bucket,
    model_id,
    pool_shares,
    select_k,
    sweep_table,
    tokenize,
    tokenize_corpus,
    topic_meta,
)
from src.pipeline.news.topics.transform import transform

from tests.conftest import FEDERATIVE_UNITS, NEWS_LEXICON, FakeTopicModel

SUNDAY = date(2011, 1, 9)
NEXT_SUNDAY = date(2011, 1, 16)
MONDAY = date(2011, 1, 10)

# Deliberately small: these tests are about the arithmetic of pooling, and three
# topics are enough to say what a share, a mean and a sum are.
K = 3


def _corpus(rows: list[dict]) -> pl.DataFrame:
    schema = {
        "article_id": pl.String,
        "published_at": pl.String,
        "ew": pl.Date,
        "title": pl.String,
        "text": pl.String,
        "lang_guess": pl.String,
    }
    return pl.DataFrame(rows, schema=schema)


def _row(article_id: str, day: date, text: str, title: str = "", lang: str = "pt") -> dict:
    return {
        "article_id": article_id,
        "published_at": f"{day.isoformat()}T06:14:00",
        "ew": day,
        "title": title,
        "text": text,
        "lang_guess": lang,
    }


def _locations(pairs: list[tuple[str, list[str]]]) -> pl.DataFrame:
    return pl.DataFrame(
        pairs,
        schema={"article_id": pl.String, "locations": pl.List(pl.String)},
        orient="row",
    )


def _shares(rows: list[list[float]]) -> np.ndarray:
    return np.asarray(rows, dtype=np.float32)


# --- tokenization -----------------------------------------------------------


def test_tokenize_folds_accents() -> None:
    """Folding is what lets the stopword list be one flat tuple.

    `não`/`nao` and `está`/`esta` collapse to one entry each, so the list does not
    have to enumerate every accented spelling the corpus contains.
    """
    assert tokenize("Não há vacinação") == ["vacinacao"]


def test_tokenize_drops_stopwords_and_short_tokens() -> None:
    assert tokenize("A dengue avança no país") == ["dengue", "avanca", "pais"]


def test_tokenize_drops_attribution_boilerplate() -> None:
    """`disse` and `segundo` are content words by part of speech, but in a corpus
    of attributed news prose they cluster into a topic that says nothing about
    dengue."""
    assert tokenize("O ministro disse que a dengue caiu, segundo o boletim") == [
        "ministro",
        "dengue",
        "caiu",
        "boletim",
    ]


def test_tokenize_keeps_the_domain_vocabulary() -> None:
    """The stopword list must not eat the words the topics are made of."""
    assert tokenize("Casos de dengue e mortes por aedes aegypti") == [
        "casos",
        "dengue",
        "mortes",
        "aedes",
        "aegypti",
    ]


def test_tokenize_drops_numerals() -> None:
    """The corpus writes case counts as `36.791`, and a token that is one week's
    number is not a topic."""
    assert tokenize("Foram 36.791 casos em 2024") == ["casos"]


def test_tokenize_of_nothing_is_empty() -> None:
    assert tokenize("") == []
    assert tokenize("de a o e") == []


def test_tokenize_corpus_reads_title_and_body(news_corpus) -> None:
    """The headline is where a week's framing lives, so dropping it would lose the
    most topical sentence of the article."""
    docs = tokenize_corpus(news_corpus)
    assert len(docs) == news_corpus.height
    assert all(isinstance(doc, list) for doc in docs)


# --- the covariate ----------------------------------------------------------


def test_covariate_bucket_by_grain() -> None:
    assert covariate_bucket(SUNDAY, GRAIN_MONTH) == "2011-01"
    assert covariate_bucket(SUNDAY, GRAIN_YEAR) == "2011"
    assert covariate_bucket(SUNDAY, GRAIN_WEEK) == "2011-01-09"


def test_covariate_bucket_rejects_an_unknown_grain() -> None:
    with pytest.raises(ValueError, match="grain"):
        covariate_bucket(SUNDAY, "fortnight")


def test_month_grain_collapses_a_month_of_weeks() -> None:
    """The reason the default is a month and not the weekly output grain: DMR
    regresses prevalence on the covariate's levels, and 965 weekly levels against
    ~4.5 articles each would be an over-parameterised fit."""
    weeks = [date(2011, 1, 2), date(2011, 1, 9), date(2011, 1, 16)]
    assert len({covariate_bucket(day, GRAIN_MONTH) for day in weeks}) == 1
    assert len({covariate_bucket(day, GRAIN_WEEK) for day in weeks}) == 3


# --- the model --------------------------------------------------------------


def test_model_id_carries_k_and_seed() -> None:
    """Both are in the string because both change what the numbers mean: k fixes
    how many rows a week has, and the seed fixes which fit produced them."""
    assert model_id("dmr", 15, 42) == "tomotopy-dmr-k15-seed42"


def test_an_unknown_family_is_refused_before_any_import() -> None:
    """Raised in the constructor, so the message does not depend on whether the
    optional extra happens to be installed."""
    with pytest.raises(ValueError, match="family"):
        TomotopyTopicModel(k=5, family="bertopic")


def test_the_fake_reports_a_row_per_document() -> None:
    model = FakeTopicModel(k=4)
    model.fit([["dengue"], ["vacina"], []], ["2011-01"] * 3)
    assert model.document_shares().shape == (3, 4)


def test_a_document_with_no_tokens_gets_a_uniform_row() -> None:
    """Not dropped and not NaN: it is still in the article set protocol 00 fixes,
    so it must still count, and a uniform row leaves the week's mean where it was
    instead of inventing a lean toward one topic."""
    model = FakeTopicModel(k=4)
    model.fit([["dengue"], []], ["2011-01"] * 2)
    assert np.allclose(model.document_shares()[1], 0.25)


def test_every_document_row_sums_to_one() -> None:
    model = FakeTopicModel(k=5)
    model.fit([["dengue", "caso"], ["vacina"], []], ["2011-01"] * 3)
    assert np.allclose(model.document_shares().sum(axis=1), 1.0)


def test_fit_refuses_mismatched_covariates() -> None:
    """DMR needs one period per document; a silent zip would drop documents."""
    with pytest.raises(ValueError, match="covariates"):
        FakeTopicModel(k=3).fit([["dengue"], ["vacina"]], ["2011-01"])


def test_topic_words_are_distinct_within_a_topic() -> None:
    """The meta table is keyed by (model, topic, term), so a repeat would be a
    duplicated key rather than a curiosity."""
    model = FakeTopicModel(k=3)
    model.fit([["dengue", "caso", "vacina", "aedes"]], ["2011-01"])
    for words in model.topic_words(top_n=4):
        terms = [term for term, _ in words]
        assert len(set(terms)) == len(terms)


# --- k selection ------------------------------------------------------------


def test_select_k_picks_the_most_coherent_candidate() -> None:
    sweep = select_k(
        [["dengue"], ["vacina"]], ["2011-01", "2011-01"], (5, 10, 15, 20, 25),
        lambda k: FakeTopicModel(k),
    )
    assert sweep.best_k == FakeTopicModel.PEAK_K
    assert sweep.best_coherence == max(row.coherence for row in sweep.rows)
    assert [row.k for row in sweep.rows] == [5, 10, 15, 20, 25]


def test_select_k_records_every_candidate_not_only_the_winner() -> None:
    """The sweep is the evidence a reader checks the choice against, so the models
    that lost have to be in it."""
    sweep = select_k(
        [["dengue"], ["vacina"]], ["2011-01", "2011-01"], (5, 10, 15),
        lambda k: FakeTopicModel(k),
    )
    assert len(sweep.rows) == 3
    assert all(isinstance(row, KSweepRow) for row in sweep.rows)
    assert all(row.ll_per_word for row in sweep.rows)


def test_select_k_breaks_a_tie_toward_the_smaller_k() -> None:
    """The sweep runs in ascending order and only a *strictly* better score
    displaces the incumbent, so an uninformative plateau resolves to the more
    parsimonious model instead of the largest one."""

    class Flat(FakeTopicModel):
        def coherence(self, metric: str = "c_v", top_n: int = 10) -> float:
            return 0.5

    sweep = select_k(
        [["dengue"]], ["2011-01"], (5, 10, 15), lambda k: Flat(k)
    )
    assert sweep.best_k == 5


def test_select_k_keeps_the_fitted_winner_rather_than_refitting() -> None:
    """Refitting would be wasted work and, worse, could differ."""
    fitted: list[FakeTopicModel] = []

    def factory(k: int):
        model = FakeTopicModel(k)
        fitted.append(model)
        return model

    sweep = select_k([["dengue"]], ["2011-01"], (5, 10, 15), factory)
    assert sweep.best in fitted


def test_an_empty_k_range_is_refused() -> None:
    with pytest.raises(ValueError, match="empty"):
        select_k([["dengue"]], ["2011-01"], (), lambda k: FakeTopicModel(k))


def test_sweep_table_flags_exactly_the_selected_k() -> None:
    sweep = select_k(
        [["dengue"], ["vacina"]], ["2011-01", "2011-01"], (5, 10, 15),
        lambda k: FakeTopicModel(k),
    )
    table = sweep_table(sweep)
    assert table.filter(pl.col("selected")).height == 1
    assert table.filter(pl.col("selected"))[TOPIC_ID][0] == sweep.best_k
    assert table[MODEL_ID].n_unique() == 3


def test_an_empty_sweep_has_no_best_k() -> None:
    with pytest.raises(ValueError, match="Empty sweep"):
        _ = KSweep().best_k


# --- the meta table ---------------------------------------------------------


def test_topic_meta_publishes_terms_for_every_topic() -> None:
    """Not optional: "topic 7 predicts dengue" is not a finding anyone can check,
    so every topic is published with its defining terms."""
    model = FakeTopicModel(k=3)
    model.fit([["dengue", "caso", "vacina", "aedes"]], ["2011-01"])
    meta = topic_meta(model, model.model_id, top_n=4)
    assert tuple(meta.columns) == ("model_id", "topic_id", "term", "weight")
    assert meta[TOPIC_ID].n_unique() == 3
    assert set(meta[MODEL_ID].to_list()) == {model.model_id}


def test_topic_meta_honours_top_n() -> None:
    model = FakeTopicModel(k=2)
    model.fit([["dengue", "caso", "vacina", "aedes", "mosquito"]], ["2011-01"])
    assert topic_meta(model, model.model_id, top_n=2).height == 2 * 2


# --- pooling ----------------------------------------------------------------


def test_pool_adds_br_to_every_article_and_each_named_uf() -> None:
    pooled = pool_shares(
        ["a0"], [SUNDAY], _shares([[0.5, 0.3, 0.2]]),
        _locations([("a0", ["RJ", "BA"])]), "m",
    )
    assert set(pooled["location"].to_list()) == {NATIONAL_LOCATION, "RJ", "BA"}
    assert tuple(pooled.columns) == OUTPUT_COLUMNS


def test_pool_shares_sum_to_one_per_week_and_location() -> None:
    """The invariant that makes the column a share: a topic mixture is a point on
    the simplex, and the mean of distributions is a distribution."""
    pooled = pool_shares(
        ["a0", "a1"], [SUNDAY, SUNDAY],
        _shares([[0.5, 0.3, 0.2], [0.1, 0.1, 0.8]]),
        _locations([("a0", ["RJ"]), ("a1", [])]), "m",
    )
    totals = pooled.group_by("ew", "location").agg(pl.col(SHARE).sum())
    assert all(abs(total - 1.0) < 1e-6 for total in totals[SHARE].to_list())


def test_pool_mean_is_over_the_articles_that_landed_in_the_row() -> None:
    pooled = pool_shares(
        ["a0", "a1"], [SUNDAY, SUNDAY],
        _shares([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        _locations([("a0", []), ("a1", [])]), "m",
    )
    national = pooled.filter(pl.col("location") == NATIONAL_LOCATION).sort(TOPIC_ID)
    assert np.allclose(national[SHARE].to_numpy(), [0.5, 0.5, 0.0])


def test_pool_counts_articles_not_article_topic_rows() -> None:
    """The long table has one row per (article, topic), so a plain count would
    multiply the week's coverage by k and report a figure off by an order of
    magnitude."""
    pooled = pool_shares(
        ["a0", "a1"], [SUNDAY, SUNDAY],
        _shares([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        _locations([("a0", []), ("a1", [])]), "m",
    )
    assert set(pooled[N_ARTICLES].to_list()) == {2}
    assert pooled.height == K


def test_pool_counts_only_the_articles_in_that_location() -> None:
    """`n_articles` is what makes a share interpretable: 0.6 over one article and
    over forty are different claims."""
    pooled = pool_shares(
        ["a0", "a1"], [SUNDAY, SUNDAY],
        _shares([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        _locations([("a0", ["RJ"]), ("a1", [])]), "m",
    )
    assert pooled.filter(pl.col("location") == "RJ")[N_ARTICLES].to_list() == [1] * K
    assert pooled.filter(pl.col("location") == NATIONAL_LOCATION)[N_ARTICLES].to_list() == [2] * K


def test_pool_omits_a_week_with_no_article() -> None:
    """Absent, not a row of zeros: a zero vector is not a point in the simplex and
    would read as "coverage that says nothing" rather than "no coverage"."""
    pooled = pool_shares(["a0"], [SUNDAY], _shares([[1.0, 0.0, 0.0]]), _locations([("a0", [])]), "m")
    assert pooled["ew"].n_unique() == 1
    assert set(pooled["ew"].to_list()) == {SUNDAY}


def test_pool_keeps_a_row_for_each_week_separately() -> None:
    """Two weeks, not one merged row — the grain is (ew, location, topic), so the
    national rows are one per week *per topic*."""
    pooled = pool_shares(
        ["a0", "a1"], [SUNDAY, NEXT_SUNDAY],
        _shares([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        _locations([("a0", []), ("a1", [])]), "m",
    )
    national = pooled.filter(pl.col("location") == NATIONAL_LOCATION)
    assert national["ew"].n_unique() == 2
    assert national.height == 2 * K


def test_pool_over_nothing_returns_the_empty_schema() -> None:
    pooled = pool_shares([], [], np.zeros((0, K), dtype=np.float32), _locations([]), "m")
    assert pooled.height == 0
    assert tuple(pooled.columns) == OUTPUT_COLUMNS
    assert pooled.schema == SHARE_SCHEMA


def test_pool_matches_the_declared_schema() -> None:
    """Both branches must agree: `pl.len()` is u32 and `SHARE_SCHEMA` says Int64,
    so a run over real articles and a run over none would otherwise publish
    different dtypes for the same column."""
    populated = pool_shares(
        ["a0"], [SUNDAY], _shares([[1.0, 0.0, 0.0]]), _locations([("a0", [])]), "m"
    )
    empty = pool_shares([], [], np.zeros((0, K), dtype=np.float32), _locations([]), "m")
    assert populated.schema == SHARE_SCHEMA
    assert empty.schema == SHARE_SCHEMA
    assert populated.schema[N_ARTICLES] == pl.Int64


def test_pool_stamps_the_model_id_on_every_row() -> None:
    """The id travels with the numbers, so a table found on disk says which fit
    produced it."""
    pooled = pool_shares(["a0"], [SUNDAY], _shares([[1.0, 0.0, 0.0]]), _locations([("a0", [])]), "m")
    assert set(pooled[MODEL_ID].to_list()) == {"m"}


# --- end to end -------------------------------------------------------------


def test_transform_writes_the_three_tables_over_the_fixture(
    news_corpus, tmp_path, news_lexicon
) -> None:
    """The full stage, with only the model substituted.

    Five fixture pages, five different weeks, every one of them about dengue — so
    the pooled table must carry a national row per week, the meta table must
    define every topic, and the sweep must record every candidate k.
    """
    corpus_path = tmp_path / "EBC_dengue_text.parquet"
    news_corpus.write_parquet(corpus_path)
    result = transform(
        corpus_path=corpus_path,
        fu_path=FEDERATIVE_UNITS,
        lexicon_path=NEWS_LEXICON,
        out_dir=tmp_path,
        model_factory=lambda k: FakeTopicModel(k),
    )
    assert result.articles == news_corpus.height
    assert result.topics == FakeTopicModel.PEAK_K
    assert result.model_id == model_id("dmr", FakeTopicModel.PEAK_K, 42)
    assert len(result.sweep) == 5
    assert result.failed == 0

    pooled = pl.read_parquet(tmp_path / "EBC_dengue_topics_EW.parquet")
    meta = pl.read_parquet(tmp_path / "EBC_dengue_topics_meta.parquet")
    sweep = pl.read_parquet(tmp_path / "EBC_dengue_topics_sweep.parquet")
    assert pooled.filter(pl.col("location") == NATIONAL_LOCATION)["ew"].n_unique() == (
        news_corpus["ew"].n_unique()
    )
    assert meta[TOPIC_ID].n_unique() == FakeTopicModel.PEAK_K
    assert sweep.filter(pl.col("selected")).height == 1
    assert result.rows_out == pooled.height
    assert {path.suffix for path in result.outputs} == {".parquet", ".gz"}


def test_transform_honours_the_top_terms_setting(news_corpus, tmp_path) -> None:
    corpus_path = tmp_path / "EBC_dengue_text.parquet"
    news_corpus.write_parquet(corpus_path)
    result = transform(
        corpus_path=corpus_path,
        fu_path=FEDERATIVE_UNITS,
        lexicon_path=NEWS_LEXICON,
        out_dir=tmp_path,
        k_range=(2,),
        top_terms=TOP_TERMS,
        formats=("parquet",),
        model_factory=lambda k: FakeTopicModel(k),
    )
    meta = pl.read_parquet(tmp_path / "EBC_dengue_topics_meta.parquet")
    assert meta.height <= result.topics * TOP_TERMS


def test_transform_reports_the_covariate_grain_it_used(news_corpus, tmp_path) -> None:
    """The grain is a run parameter, so it must not be silently the default."""
    corpus_path = tmp_path / "EBC_dengue_text.parquet"
    news_corpus.write_parquet(corpus_path)
    seen: list[list[str]] = []

    def factory(k: int):
        model = FakeTopicModel(k)

        original = model.fit

        def fit(docs, covariates):
            seen.append(list(covariates))
            return original(docs, covariates)

        model.fit = fit
        return model

    transform(
        corpus_path=corpus_path,
        fu_path=FEDERATIVE_UNITS,
        lexicon_path=NEWS_LEXICON,
        out_dir=tmp_path,
        k_range=(2,),
        grain=GRAIN_YEAR,
        formats=("parquet",),
        model_factory=factory,
    )
    assert seen, "the model was never fitted"
    assert all(len(bucket) == 4 for bucket in seen[0])


def test_transform_names_the_missing_corpus(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="news-text"):
        transform(
            corpus_path=tmp_path / "absent.parquet",
            fu_path=FEDERATIVE_UNITS,
            lexicon_path=NEWS_LEXICON,
            out_dir=tmp_path,
        )


def test_transform_refuses_an_unknown_format(news_corpus, tmp_path) -> None:
    corpus_path = tmp_path / "EBC_dengue_text.parquet"
    news_corpus.write_parquet(corpus_path)
    with pytest.raises(ValueError, match="format"):
        transform(
            corpus_path=corpus_path,
            fu_path=FEDERATIVE_UNITS,
            lexicon_path=NEWS_LEXICON,
            out_dir=tmp_path,
            formats=("xlsx",),
            model_factory=lambda k: FakeTopicModel(k),
        )


def test_transform_keeps_csv_gz_viable_because_the_tables_are_narrow(
    news_corpus, tmp_path
) -> None:
    """Unlike braço 02's 768-wide array, both tables are long and narrow, so the
    csv.gz an R consumer reads is written by default."""
    corpus_path = tmp_path / "EBC_dengue_text.parquet"
    news_corpus.write_parquet(corpus_path)
    result = transform(
        corpus_path=corpus_path,
        fu_path=FEDERATIVE_UNITS,
        lexicon_path=NEWS_LEXICON,
        out_dir=tmp_path,
        k_range=(2,),
        model_factory=lambda k: FakeTopicModel(k),
    )
    names = {path.name for path in result.outputs}
    assert "EBC_dengue_topics_EW.csv.gz" in names
    assert "EBC_dengue_topics_meta.csv.gz" in names
    assert "EBC_dengue_topics_sweep.csv.gz" in names


def test_transform_keeps_a_monday_article_in_the_week_it_was_assigned(
    tmp_path, news_lexicon
) -> None:
    """The epi week comes from the corpus, not from the publish date, so a Monday
    article stays in the Sunday-anchored week the news-text stage gave it."""
    corpus = _corpus([_row("a", MONDAY, "A dengue avança no país.")])
    corpus_path = tmp_path / "EBC_dengue_text.parquet"
    corpus.write_parquet(corpus_path)
    transform(
        corpus_path=corpus_path,
        fu_path=FEDERATIVE_UNITS,
        lexicon_path=NEWS_LEXICON,
        out_dir=tmp_path,
        k_range=(2,),
        formats=("parquet",),
        model_factory=lambda k: FakeTopicModel(k),
    )
    pooled = pl.read_parquet(tmp_path / "EBC_dengue_topics_EW.parquet")
    assert set(pooled["ew"].to_list()) == {MONDAY}


def test_meta_schema_is_the_published_one() -> None:
    assert tuple(META_SCHEMA) == ("model_id", "topic_id", "term", "weight")
