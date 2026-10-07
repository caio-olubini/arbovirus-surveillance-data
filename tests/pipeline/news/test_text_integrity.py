"""Corpus integrity checks: the fixture corpus passes, and each guard fires.

Every check is exercised in both directions. A check that only ever passes is
indistinguishable from no check at all, and this stage's history is two
extraction bugs that looked fine in aggregate.
"""

from __future__ import annotations

from datetime import date

import polars as pl

from src.pipeline.news.text.integrity import (
    check_bodyless_pages,
    check_min_length,
    check_schema,
    check_title_agreement,
    check_unique_keys,
    check_weeks_start_on_sunday,
    run_all,
)
from src.pipeline.news.text.spec import OUTPUT_COLUMNS

SUNDAY = date(2011, 1, 9)
MONDAY = date(2011, 1, 10)


def _corpus(**overrides) -> pl.DataFrame:
    """A one-row frame in the published schema, for failure-path tests."""
    row = {
        "article_id": "a",
        "published_at": "2011-01-11T06:14:00",
        "ew": SUNDAY,
        "section": "noticia",
        "url": "http://example.invalid/a",
        "title": "Título da matéria sobre dengue",
        "listing_title": "Título da matéria sobre dengue",
        "text": "O ministro da Saúde falou sobre a dengue no país.",
        "era": "b",
        "extractor": "div.inside",
        "char_count": 47,
        "lang_guess": "pt",
    }
    row.update(overrides)
    return pl.DataFrame([row], schema={k: pl.String for k in row} | {
        "ew": pl.Date, "char_count": pl.Int64,
    }).select(OUTPUT_COLUMNS)


def test_all_checks_pass_on_the_fixture_corpus(news_corpus: pl.DataFrame) -> None:
    checks = run_all(news_corpus)
    failed = [c for c in checks if not c.passed]
    assert not failed, "; ".join(str(c) for c in failed)


def test_schema_rejects_a_reordered_frame() -> None:
    frame = _corpus()
    assert check_schema(frame).passed
    assert not check_schema(frame.select(reversed(OUTPUT_COLUMNS))).passed


def test_unique_keys_counts_duplicates() -> None:
    frame = pl.concat([_corpus(), _corpus()])
    check = check_unique_keys(frame)
    assert not check.passed
    assert "1 duplicate" in check.detail


def test_weeks_must_start_on_sunday() -> None:
    assert check_weeks_start_on_sunday(_corpus()).passed
    assert not check_weeks_start_on_sunday(_corpus(ew=MONDAY)).passed


def test_min_length_flags_a_header_regression() -> None:
    """Bug 1 produced 20-character bodies: the site name and nothing else."""
    check = check_min_length(_corpus(text="Agência Brasil A+ A-", char_count=20))
    assert not check.passed
    assert "under 100" in check.detail


def test_min_length_ignores_a_bodyless_page() -> None:
    """A truncated fetch is reported by `bodyless_pages`, not counted twice.

    Without the split, the three 40-character bylines would fail this check
    forever and train the reader to ignore it.
    """
    bodyless = _corpus(
        article_id="2008-04-02_escolas",
        text="Danilo Macedo Repórter da Agência Brasil",
        char_count=40,
    )
    assert check_min_length(bodyless).passed
    # `bodyless_pages` reports rather than fails: a truncated fetch is a property
    # of the source, not a defect in this stage.
    assert check_bodyless_pages(bodyless).passed


def test_bodyless_pages_names_the_offenders(news_corpus: pl.DataFrame) -> None:
    check = check_bodyless_pages(news_corpus)
    assert check.passed
    assert "1 page" in check.detail
    assert "2008-04-02_escolas" in check.detail


def test_bodyless_pages_clean_corpus() -> None:
    assert check_bodyless_pages(_corpus()).detail == "every row carries article text"


def test_title_agreement_fails_below_the_floor() -> None:
    """Divergence is how a regression that latches onto a nav heading looks."""
    agree = check_title_agreement(_corpus())
    assert agree.passed
    assert "100.0%" in agree.detail

    diverged = _corpus(listing_title="Últimas notícias")
    assert not check_title_agreement(diverged).passed


def test_title_agreement_normalizes_whitespace_and_accents() -> None:
    """The two reads differ in spacing and casing, not in wording.

    Entity unescaping is *not* done here — `steps.iter_rows` unescapes the
    listing title on the way into the corpus, so this check compares two clean
    strings. Normalizing twice would hide a corpus that stopped unescaping.
    """
    frame = _corpus(
        title="Ministro  diz não à DENGUE",
        listing_title="Ministro diz nao à dengue",
    )
    assert check_title_agreement(frame).passed
