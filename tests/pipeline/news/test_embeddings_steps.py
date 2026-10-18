"""Braço 02's aggregation: input assembly, scoping, pooling and whitening.

The encoder is faked (see `tests/conftest.py`), because the real one is a 400 MB
download and what these tests are about is everything *around* it: that the mean
is taken over the articles that actually landed in a row, that BR is added by
construction, that a week with no article stays absent rather than becoming a
zero vector, and that a variant's declared parameters — input field, token
window, whitening — reach the tables rather than only the run log.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import polars as pl
import pytest

from src.pipeline.news.embeddings.spec import (
    ARTICLE_OUTPUT_COLUMNS,
    BASE_VARIANT_ID,
    EMB_MEAN,
    EMBEDDING,
    INPUT_TITLE,
    N_ARTICLES,
    NATIONAL_LOCATION,
    OUTPUT_COLUMNS,
    VARIANT,
    VARIANTS,
    table_names,
    variant,
)
from src.pipeline.news.embeddings.steps import (
    apply_whitening,
    article_input,
    article_texts,
    encode_articles,
    fit_whitening,
    normalize_rows,
    pool_by_week,
    pooled_schema,
    scoped_locations,
    truncation_stats,
    whiten_articles,
)
from src.pipeline.news.embeddings.transform import select_articles, transform

from tests.conftest import FEDERATIVE_UNITS, NEWS_LEXICON

# Width used by the hand-built tables below. Deliberately not the model's 768:
# these tests are about the arithmetic of pooling, and two dimensions are enough
# to say what a mean is. `pool_by_week` takes the width as an argument, so nothing
# here has to agree with the pinned checkpoint.
DIM = 2

SUNDAY = date(2011, 1, 9)


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


def _cone(n: int = 400, dim: int = 8, spread: float = 0.05, seed: int = 0) -> np.ndarray:
    """`n` unit vectors crowded into a narrow cone around the first axis.

    This is the anisotropy whitening exists to correct: mean pooling without
    fine-tuning puts unrelated sentences in a cone, so cosine similarity is high
    between texts that have nothing to do with each other.
    """
    rng = np.random.default_rng(seed)
    axis = np.zeros(dim)
    axis[0] = 1.0
    return normalize_rows(axis + spread * rng.standard_normal((n, dim)))


def _mean_cosine(vectors: np.ndarray) -> float:
    """Mean cosine similarity over every unordered pair, off the diagonal."""
    unit = normalize_rows(vectors)
    gram = unit @ unit.T
    n = gram.shape[0]
    off_diagonal = (gram.sum() - np.trace(gram)) / (n * (n - 1))
    return float(off_diagonal)


# --- the article input ------------------------------------------------------


def test_article_input_joins_title_and_body() -> None:
    """The headline carries the week's framing, so it must not be dropped."""
    assert article_input("Surto cresce", "Corpo.") == "Surto cresce\nCorpo."


def test_article_input_survives_a_missing_title() -> None:
    assert article_input("", "Corpo.") == "\nCorpo."


def test_article_texts_defaults_to_title_and_body() -> None:
    corpus = _corpus([_row("a", SUNDAY, "o corpo", title="A manchete")])
    assert article_texts(corpus) == ["A manchete\no corpo"]


def test_article_texts_can_drop_the_body_entirely() -> None:
    """The bracket's floor: the least text a dense reading can be given.

    It is the one configuration where the 512-token window cannot be the
    explanation for a weak result, so the body has to actually be absent from
    what the encoder sees — not merely down-weighted.
    """
    corpus = _corpus([_row("a", SUNDAY, "o corpo com a palavra secreta", title="A manchete")])
    assert article_texts(corpus, INPUT_TITLE) == ["A manchete"]
    assert "secreta" in article_texts(corpus)[0]


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


def test_encode_articles_stamps_the_variant_it_was_asked_for(news_corpus, news_embedding_encoder) -> None:
    """A table must not depend on its filename to say which configuration made it."""
    articles = encode_articles(news_corpus, news_embedding_encoder, variant_id="e5-large")
    assert set(articles[VARIANT].to_list()) == {"e5-large"}
    assert encode_articles(news_corpus, news_embedding_encoder)[VARIANT][0] == BASE_VARIANT_ID


def test_truncation_stats_reports_articles_above_the_limit(news_embedding_encoder) -> None:
    """`n_tokens` is what keeps window truncation visible rather than silent."""
    corpus = _corpus([
        _row("short", SUNDAY, "duas palavras"),
        _row("long", SUNDAY, " ".join(["palavra"] * 600)),
    ])
    articles = encode_articles(corpus, news_embedding_encoder)
    over, longest = truncation_stats(articles)
    assert over == 1
    assert longest == 600


def test_truncation_stats_follows_the_variant_window(news_embedding_encoder) -> None:
    """The window is per variant, so the count has to be taken per variant.

    Serafim's declared 128-token window truncates articles the 512-token
    configurations read whole, and that difference has to be visible in the run
    rather than inferred from the model name.
    """
    corpus = _corpus([
        _row("medium", SUNDAY, " ".join(["palavra"] * 200)),
        _row("long", SUNDAY, " ".join(["palavra"] * 600)),
    ])
    articles = encode_articles(corpus, news_embedding_encoder)
    assert truncation_stats(articles, 512)[0] == 1
    assert truncation_stats(articles, 128)[0] == 2


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
    corpus = _corpus([_row("a", SUNDAY, "O ministro viajou para Brasília.")])
    found = scoped_locations(corpus, news_matcher)
    assert found["locations"].to_list() == [[]]


# --- pooling ----------------------------------------------------------------


def test_pool_adds_br_to_every_article_and_each_named_uf() -> None:
    articles = _article_table([[1.0, 0.0]], [SUNDAY])
    pooled = pool_by_week(articles, _locations([("a0", ["RJ", "BA"])]), DIM)
    assert set(pooled["location"].to_list()) == {NATIONAL_LOCATION, "RJ", "BA"}
    assert tuple(pooled.columns) == OUTPUT_COLUMNS
    assert set(pooled[N_ARTICLES].to_list()) == {1}


def test_pool_mean_is_over_the_articles_that_landed_in_the_row() -> None:
    """Two articles in the same week: the mean is theirs, not the corpus's."""
    articles = _article_table([[1.0, 0.0], [0.0, 1.0]], [SUNDAY, SUNDAY])
    pooled = pool_by_week(articles, _locations([("a0", []), ("a1", [])]), DIM)
    mean = pooled.filter(pl.col("location") == NATIONAL_LOCATION)[EMB_MEAN].to_numpy()
    assert np.allclose(mean[0], [0.5, 0.5])
    assert pooled[N_ARTICLES].to_list() == [2]


def test_pool_publishes_no_separate_dispersion_column() -> None:
    """`emb_std` was removed on 2026-10-14, not repaired.

    For L2-normalized article vectors the parallel-axis identity gives
    `‖std‖² = 1 − ‖mean‖²` exactly, so a dispersion column is a deterministic
    function of a column the table already carries. The assertion is here so the
    removal is a decision the suite records rather than a gap someone re-adds.
    """
    articles = _article_table([[1.0, 0.0], [0.0, 1.0]], [SUNDAY, SUNDAY])
    pooled = pool_by_week(articles, _locations([("a0", []), ("a1", [])]), DIM)
    assert "emb_std" not in pooled.columns
    mean = pooled[EMB_MEAN].to_numpy()[0]
    # Two orthogonal unit vectors: ‖mean‖² = 0.5 and ‖std‖² = 0.5.
    assert np.isclose(1.0 - float(np.dot(mean, mean)), 0.5, atol=1e-6)


def test_pool_omits_a_week_with_no_article() -> None:
    """Absent, not a zero vector.

    A zero embedding is a real point in the space and would read as "news that
    means nothing" instead of "no news" — the distinction `notes/02` asks the
    `no_news` indicator to carry.
    """
    articles = _article_table([[1.0, 0.0]], [SUNDAY])
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
    articles = _article_table([[1.0, 0.0], [0.0, 1.0]], [SUNDAY, date(2011, 1, 16)])
    pooled = pool_by_week(articles, _locations([("a0", []), ("a1", [])]), DIM)
    assert pooled.filter(pl.col("location") == NATIONAL_LOCATION).height == 2


# --- whitening --------------------------------------------------------------


def test_whitening_spreads_a_narrow_cone() -> None:
    """The one thing whitening is for: unrelated vectors stop looking alike.

    Without it, mean-pooled BERT-family vectors sit in a cone where every pair
    has a high cosine similarity regardless of topic (Ethayarajh 2019), which is
    the failure mode that would make the base variant look worse than it is.
    """
    cone = _cone()
    spread = apply_whitening(cone, fit_whitening(cone))
    assert _mean_cosine(cone) > 0.9
    assert _mean_cosine(spread) < 0.5


def test_whitening_keeps_the_aggregation_contract() -> None:
    """Unit vectors in, unit vectors out.

    Re-normalizing after the transform is what makes the whitened variant
    comparable to the base: both pool unit vectors, so the only thing that
    differs between them is the geometry, not the aggregation.
    """
    cone = _cone(n=200, dim=16)
    whitened = apply_whitening(cone, fit_whitening(cone))
    assert whitened.shape == cone.shape
    assert whitened.dtype == np.float32
    assert np.allclose(np.linalg.norm(whitened, axis=1), 1.0, atol=1e-5)


def test_fit_whitening_needs_more_than_one_vector() -> None:
    with pytest.raises(ValueError, match="n>1"):
        fit_whitening(np.zeros((1, 4), dtype=np.float32))


def test_fit_whitening_needs_a_matrix() -> None:
    with pytest.raises(ValueError, match="n>1"):
        fit_whitening(np.zeros(4, dtype=np.float32))


def test_normalize_rows_leaves_a_zero_row_at_zero() -> None:
    """Dividing by a zero norm would give NaN, which `check_finite` then catches
    only after it has been written to disk."""
    matrix = np.array([[3.0, 4.0], [0.0, 0.0]], dtype=np.float32)
    out = normalize_rows(matrix)
    assert np.allclose(out[0], [0.6, 0.8])
    assert np.allclose(out[1], [0.0, 0.0])
    assert np.isfinite(out).all()


def test_whiten_articles_rewrites_the_embedding_column() -> None:
    """The per-article table is whitened too, not just the pooled one.

    Otherwise re-pooling from it — the thing the table exists for — would produce
    a different table than the published one.
    """
    vectors = _cone(n=6, dim=4)
    articles = _article_table(vectors.tolist(), [SUNDAY] * 6)
    whitened = whiten_articles(articles, fit_whitening(vectors))
    assert tuple(whitened.columns) == tuple(articles.columns)
    assert whitened.schema[EMBEDDING] == articles.schema[EMBEDDING]
    out = whitened[EMBEDDING].to_numpy()
    assert not np.allclose(out, articles[EMBEDDING].to_numpy())
    assert np.allclose(np.linalg.norm(out, axis=1), 1.0, atol=1e-5)


def test_whiten_articles_is_a_no_op_on_an_empty_table() -> None:
    empty = _article_table([[1.0, 0.0]], [SUNDAY]).filter(pl.col("article_id") == "nothing")
    assert whiten_articles(empty, fit_whitening(_cone(4, 2))).height == 0


# --- the bracket ------------------------------------------------------------


def test_table_names_suffix_everything_but_the_base() -> None:
    """The base keeps the published name; the rest say which configuration they
    are, so a directory listing shows the whole bracket without opening a file."""
    assert table_names(BASE_VARIANT_ID) == (
        "EBC_dengue_embeddings_article",
        "EBC_dengue_embeddings_EW",
    )
    assert table_names("e5-large") == (
        "EBC_dengue_embeddings_e5_large_article",
        "EBC_dengue_embeddings_e5_large_EW",
    )


def test_every_variant_declares_a_pinned_commit_not_a_branch() -> None:
    """A branch moves under the artifact; a 40-hex commit does not."""
    for variant_id, settings in VARIANTS.items():
        assert len(settings.model_revision) == 40, variant_id
        assert all(character in "0123456789abcdef" for character in settings.model_revision)
        assert settings.model_name and settings.label and settings.note
        assert settings.max_tokens > 0


def test_variant_lookup_names_the_alternatives() -> None:
    """A typo should list what is available, not raise a bare `KeyError`."""
    with pytest.raises(KeyError, match="bertimbau-whitening"):
        variant("bertimbau-whitning")
    assert variant("bertimbau-whitening").whitening
    assert not variant(BASE_VARIANT_ID).whitening


# --- the article set --------------------------------------------------------


def test_select_articles_drops_non_portuguese(news_lexicon) -> None:
    corpus = _corpus([
        _row("pt", SUNDAY, "A dengue avança no país."),
        _row("es", SUNDAY, "El dengue avanza en el país.", lang="other"),
    ])
    kept, dropped = select_articles(corpus, news_lexicon)
    assert kept["article_id"].to_list() == ["pt"]
    assert dropped == 1


def test_select_articles_drops_pages_without_a_disease_term(news_lexicon) -> None:
    """The same gate braço 01 applies, so both braços see the same corpus."""
    corpus = _corpus([
        _row("dengue", SUNDAY, "A dengue avança no país."),
        _row("tributos", SUNDAY, "O congresso discutiu a reforma tributária."),
    ])
    kept, dropped = select_articles(corpus, news_lexicon)
    assert kept["article_id"].to_list() == ["dengue"]
    assert dropped == 1


def test_select_articles_can_be_told_to_keep_everything(news_lexicon) -> None:
    corpus = _corpus([_row("tributos", SUNDAY, "Reforma tributária.")])
    kept, dropped = select_articles(
        corpus, news_lexicon, portuguese_only=False, require_disease_term=False
    )
    assert kept.height == 1
    assert dropped == 0


# --- end to end -------------------------------------------------------------


def _corpus_path(news_corpus, tmp_path):
    path = tmp_path / "EBC_dengue_text.parquet"
    news_corpus.write_parquet(path)
    return path


def test_transform_writes_both_tables_over_the_fixture(
    news_corpus, news_embedding_encoder, tmp_path, news_lexicon
) -> None:
    """The full stage, with only the encoder substituted.

    Five fixture pages, five different weeks, every one of them about dengue — so
    the pooled table must carry five national rows.
    """
    result = transform(
        corpus_path=_corpus_path(news_corpus, tmp_path),
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


def test_transform_writes_a_suffixed_pair_per_variant(
    news_corpus, news_embedding_encoder, tmp_path
) -> None:
    """A variant run must not overwrite the published base table.

    The bracket is compared table against table, so every configuration has to
    leave its own pair on disk — and the run has to report the configuration it
    used, since the encoder is only one of the things that varies.
    """
    result = transform(
        corpus_path=_corpus_path(news_corpus, tmp_path),
        fu_path=FEDERATIVE_UNITS,
        lexicon_path=NEWS_LEXICON,
        out_dir=tmp_path,
        variant_id="e5-large",
        encoder=news_embedding_encoder,
    )
    assert result.variant == "e5-large"
    assert result.pooling == VARIANTS["e5-large"].pooling
    assert result.max_tokens == VARIANTS["e5-large"].max_tokens
    assert not result.whitening
    for name in table_names("e5-large"):
        assert (tmp_path / f"{name}.parquet").exists()
    assert not (tmp_path / "EBC_dengue_embeddings_EW.parquet").exists()
    articles = pl.read_parquet(tmp_path / "EBC_dengue_embeddings_e5_large_article.parquet")
    assert set(articles[VARIANT].to_list()) == {"e5-large"}


def test_transform_whitens_the_variant_that_asks_for_it(
    news_corpus, news_embedding_encoder, tmp_path
) -> None:
    """End to end over a five-article fixture, which is thin for a covariance.

    The floor on the eigenvalues is what keeps that from mattering: without it the
    near-singular directions would be inverted into noise, and the assertion that
    every vector is still finite is the one that would fail.
    """
    result = transform(
        corpus_path=_corpus_path(news_corpus, tmp_path),
        fu_path=FEDERATIVE_UNITS,
        lexicon_path=NEWS_LEXICON,
        out_dir=tmp_path,
        variant_id="bertimbau-whitening",
        encoder=news_embedding_encoder,
    )
    assert result.whitening
    articles = pl.read_parquet(tmp_path / "EBC_dengue_embeddings_bertimbau_whitening_article.parquet")
    vectors = articles[EMBEDDING].to_numpy()
    assert np.isfinite(vectors).all()
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)


def test_transform_refuses_to_whiten_on_an_empty_window(
    news_corpus, news_embedding_encoder, tmp_path
) -> None:
    """A covariance estimated from nothing is not a transform.

    Protocol 00's rolling origin will pass a real cutoff here, and a cutoff that
    precedes the corpus is the mistake that would otherwise be silent: the
    transform would be fitted on whatever happened to be left.
    """
    with pytest.raises(ValueError, match="at least 2 articles"):
        transform(
            corpus_path=_corpus_path(news_corpus, tmp_path),
            fu_path=FEDERATIVE_UNITS,
            lexicon_path=NEWS_LEXICON,
            out_dir=tmp_path,
            variant_id="bertimbau-whitening",
            whitening_fit_until=date(2000, 1, 1),
            encoder=news_embedding_encoder,
        )


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
    with pytest.raises(ValueError, match="parquet"):
        transform(
            corpus_path=_corpus_path(news_corpus, tmp_path),
            fu_path=FEDERATIVE_UNITS,
            lexicon_path=NEWS_LEXICON,
            out_dir=tmp_path,
            encoder=news_embedding_encoder,
            formats=("csv_gz",),
        )
