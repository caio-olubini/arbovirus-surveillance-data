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
