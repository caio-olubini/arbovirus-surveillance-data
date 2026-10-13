"""Braço 02's aggregation: masking, scoping, pooling and dispersion.

The encoder is faked (see `tests/conftest.py`), because the real one is a 400 MB
download and what these tests are about is everything *around* it: that the mean
is taken over the articles that actually landed in a row, that BR is added by
construction, that a single-article week has zero dispersion, and that a week with
no article stays absent rather than becoming a zero vector.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import polars as pl
import pytest

from src.pipeline.news.embeddings.spec import (
    ARTICLE_OUTPUT_COLUMNS,
    EMB_MEAN,
    EMB_STD,
    EMBEDDING,
    EMBEDDING_DIM,
    N_ARTICLES,
    NATIONAL_LOCATION,
    OUTPUT_COLUMNS,
)
from src.pipeline.news.embeddings.steps import (
    article_input,
    encode_articles,
    pool_by_week,
    pooled_schema,
    scoped_locations,
    truncation_stats,
)
from src.pipeline.news.embeddings.transform import select_articles, transform

from tests.conftest import FEDERATIVE_UNITS, NEWS_LEXICON

# Width used by the hand-built tables below. Deliberately not the model's 768:
# these tests are about the arithmetic of pooling, and two dimensions are enough
# to say what a mean and a dispersion are. `pool_by_week` takes the width as an
# argument, so nothing here has to agree with the pinned checkpoint.
DIM = 2


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


def _article_table(vectors: list[list[float]], days: list[date]) -> pl.DataFrame:
    """A hand-built article table, so pooling is tested without any encoder."""
    return pl.DataFrame(
        {
            "article_id": [f"a{i}" for i in range(len(vectors))],
            "ew": days,
            "embedding": [np.asarray(v, dtype=np.float32) for v in vectors],
        },
        schema={
            "article_id": pl.String,
            "ew": pl.Date,
            "embedding": pl.Array(pl.Float32, len(vectors[0])),
        },
    )


def _locations(pairs: list[tuple[str, list[str]]]) -> pl.DataFrame:
    return pl.DataFrame(
        pairs,
        schema={"article_id": pl.String, "locations": pl.List(pl.String)},
        orient="row",
    )


# --- the article input ------------------------------------------------------


def test_article_input_joins_title_and_body() -> None:
    """The headline carries the week's framing, so it must not be dropped."""
    assert article_input("Surto cresce", "Corpo.") == "Surto cresce\nCorpo."


def test_article_input_survives_a_missing_title() -> None:
    assert article_input("", "Corpo.") == "\nCorpo."


# --- encoding ---------------------------------------------------------------


def test_encode_articles_emits_one_row_per_article(news_corpus, news_embedding_encoder) -> None:
    articles = encode_articles(news_corpus, news_embedding_encoder, batch_size=2)
    assert articles.height == news_corpus.height
    assert tuple(articles.columns) == ARTICLE_OUTPUT_COLUMNS
    assert articles.schema[EMBEDDING] == pl.Array(pl.Float32, news_embedding_encoder.dim)


def test_encode_articles_keeps_a_batch_boundary_from_losing_a_row(
    news_corpus, news_embedding_encoder
) -> None:
    """The fixture corpus is 5 rows; batching by 2 leaves a partial batch.

    A dropped partial batch is the classic off-by-one here, and it would shrink
    the corpus silently.
    """
    one = encode_articles(news_corpus, news_embedding_encoder, batch_size=1)
    three = encode_articles(news_corpus, news_embedding_encoder, batch_size=3)
    assert one.height == three.height == news_corpus.height
    assert one["article_id"].to_list() == three["article_id"].to_list()


def test_encode_articles_records_the_model_and_revision(
    news_corpus, news_embedding_encoder
) -> None:
    articles = encode_articles(news_corpus, news_embedding_encoder)
    assert set(articles["model_id"].to_list()) == {news_embedding_encoder.model_id}
    assert set(articles["model_revision"].to_list()) == {news_embedding_encoder.model_revision}


def test_truncation_stats_reports_articles_above_the_limit(news_embedding_encoder) -> None:
    """`n_tokens` is what keeps MAX_TOKENS truncation visible rather than silent."""
    corpus = _corpus([
        _row("short", date(2011, 1, 9), "duas palavras"),
        _row("long", date(2011, 1, 9), " ".join(["palavra"] * 600)),
    ])
    articles = encode_articles(corpus, news_embedding_encoder)
    over, longest = truncation_stats(articles)
    assert over == 1
    assert longest == 600


# --- scoping ----------------------------------------------------------------


def test_scoped_locations_finds_named_states(news_corpus, news_matcher) -> None:
    found = scoped_locations(news_corpus, news_matcher)
    assert set(found.columns) == {"article_id", "locations"}
    assert found.height == news_corpus.height
    # The 2011 fixture page is the one about prevention in the country.
    assert all(isinstance(value, list) for value in found["locations"].to_list())


def test_scoped_locations_does_not_invent_a_state(news_matcher) -> None:
    """A page that names no UF must not be scoped to one.

    `Pará` versus the preposition `para` is the trap this guards: folding accents
    here would scope nearly every article to PA.
    """
    corpus = _corpus([_row("a", date(2011, 1, 9), "O ministro viajou para Brasília.")])
    found = scoped_locations(corpus, news_matcher)
    assert found["locations"].to_list() == [[]]


# --- pooling ----------------------------------------------------------------


def test_pool_adds_br_to_every_article_and_each_named_uf() -> None:
    articles = _article_table([[1.0, 0.0]], [date(2011, 1, 9)])
    pooled = pool_by_week(articles, _locations([("a0", ["RJ", "BA"])]), DIM)
    assert set(pooled["location"].to_list()) == {NATIONAL_LOCATION, "RJ", "BA"}
    assert tuple(pooled.columns) == OUTPUT_COLUMNS
    assert set(pooled[N_ARTICLES].to_list()) == {1}


def test_pool_mean_is_over_the_articles_that_landed_in_the_row() -> None:
    """Two articles in the same week: the mean is theirs, not the corpus's."""
    articles = _article_table(
        [[1.0, 0.0], [0.0, 1.0]],
        [date(2011, 1, 9), date(2011, 1, 9)],
    )
    pooled = pool_by_week(articles, _locations([("a0", []), ("a1", [])]), DIM)
    mean = pooled.filter(pl.col("location") == NATIONAL_LOCATION)[EMB_MEAN].to_numpy()
    assert np.allclose(mean[0], [0.5, 0.5])
    assert pooled[N_ARTICLES].to_list() == [2]


def test_pool_one_article_has_no_dispersion() -> None:
    articles = _article_table([[1.0, 0.0]], [date(2011, 1, 9)])
    pooled = pool_by_week(articles, _locations([("a0", [])]), DIM)
    assert pooled[EMB_STD].to_list() == [0.0]


def test_pool_dispersion_grows_with_heterogeneity() -> None:
    """`emb_std` is the signal the note asks for: a week of one story is not the
    same as a week of five unrelated ones, even at equal volume."""
    day = date(2011, 1, 9)
    tight = _article_table([[1.0, 0.0], [0.99, 0.14]], [day, day])
    loose = _article_table([[1.0, 0.0], [0.0, 1.0]], [day, day])
    tight_std = pool_by_week(tight, _locations([("a0", []), ("a1", [])]), DIM)
    loose_std = pool_by_week(loose, _locations([("a0", []), ("a1", [])]), DIM)
    assert tight_std[EMB_STD][0] < loose_std[EMB_STD][0]


def test_pool_omits_a_week_with_no_article() -> None:
    """Absent, not a zero vector.

    A zero embedding is a real point in the space and would read as "news that
    means nothing" instead of "no news" — the distinction `notes/02` asks the
    `no_news` indicator to carry.
    """
    articles = _article_table([[1.0, 0.0]], [date(2011, 1, 9)])
    pooled = pool_by_week(articles, _locations([("a0", [])]), DIM)
    assert pooled["ew"].n_unique() == 1


def test_pool_over_nothing_returns_the_empty_schema() -> None:
    empty = pl.DataFrame(
        schema={
            "article_id": pl.String,
            "ew": pl.Date,
            "embedding": pl.Array(pl.Float32, DIM),
        }
    )
    pooled = pool_by_week(empty, _locations([]), DIM)
    assert pooled.height == 0
    assert tuple(pooled.columns) == OUTPUT_COLUMNS
    assert pooled.schema == pooled_schema(DIM)


def test_pool_keeps_a_row_for_each_week_separately() -> None:
    articles = _article_table(
        [[1.0, 0.0], [0.0, 1.0]],
        [date(2011, 1, 9), date(2011, 1, 16)],
    )
    pooled = pool_by_week(articles, _locations([("a0", []), ("a1", [])]), DIM)
    assert pooled.filter(pl.col("location") == NATIONAL_LOCATION).height == 2


# --- the article set --------------------------------------------------------


def test_select_articles_drops_non_portuguese(news_lexicon) -> None:
    corpus = _corpus([
        _row("pt", date(2011, 1, 9), "A dengue avança no país."),
        _row("es", date(2011, 1, 9), "El dengue avanza en el país.", lang="other"),
    ])
    kept, dropped = select_articles(corpus, news_lexicon)
    assert kept["article_id"].to_list() == ["pt"]
    assert dropped == 1


def test_select_articles_drops_pages_without_a_disease_term(news_lexicon) -> None:
    """The same gate braço 01 applies, so both braços see the same corpus."""
    corpus = _corpus([
        _row("dengue", date(2011, 1, 9), "A dengue avança no país."),
        _row("tributos", date(2011, 1, 9), "O congresso discutiu a reforma tributária."),
    ])
    kept, dropped = select_articles(corpus, news_lexicon)
    assert kept["article_id"].to_list() == ["dengue"]
    assert dropped == 1


def test_select_articles_can_be_told_to_keep_everything(news_lexicon) -> None:
    corpus = _corpus([_row("tributos", date(2011, 1, 9), "Reforma tributária.")])
    kept, dropped = select_articles(
        corpus, news_lexicon, portuguese_only=False, require_disease_term=False
    )
    assert kept.height == 1
    assert dropped == 0


# --- end to end -------------------------------------------------------------


def test_transform_writes_both_tables_over_the_fixture(
    news_corpus, news_embedding_encoder, tmp_path, news_lexicon
) -> None:
    """The full stage, with only the encoder substituted.

    Five fixture pages, five different weeks, every one of them about dengue — so
    the pooled table must carry five national rows.
    """
    corpus_path = tmp_path / "EBC_dengue_text.parquet"
    news_corpus.write_parquet(corpus_path)
    result = transform(
        corpus_path=corpus_path,
        fu_path=FEDERATIVE_UNITS,
        lexicon_path=NEWS_LEXICON,
        out_dir=tmp_path,
        encoder=news_embedding_encoder,
    )
    assert result.articles == news_corpus.height
    assert result.dim == news_embedding_encoder.dim
    national = pl.read_parquet(tmp_path / "EBC_dengue_embeddings_EW.parquet").filter(
        pl.col("location") == NATIONAL_LOCATION
    )
    assert national.height == news_corpus["ew"].n_unique()
    assert (tmp_path / "EBC_dengue_embeddings_article.parquet").exists()


def test_transform_names_the_missing_corpus(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="news-text"):
        transform(
            corpus_path=tmp_path / "absent.parquet",
            fu_path=FEDERATIVE_UNITS,
            lexicon_path=NEWS_LEXICON,
            out_dir=tmp_path,
        )


def test_transform_refuses_a_csv_output(tmp_path, news_corpus, news_embedding_encoder) -> None:
    """A 768-float column does not survive csv text form, so it is not offered."""
    corpus_path = tmp_path / "EBC_dengue_text.parquet"
    news_corpus.write_parquet(corpus_path)
    with pytest.raises(ValueError, match="parquet"):
        transform(
            corpus_path=corpus_path,
            fu_path=FEDERATIVE_UNITS,
            lexicon_path=NEWS_LEXICON,
            out_dir=tmp_path,
            encoder=news_embedding_encoder,
            formats=("csv_gz",),
        )
