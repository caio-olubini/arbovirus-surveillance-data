"""Braço 01's rules: the numeral parser, the three count gates, and scoping.

The lexicon itself is the versioned reference under data/news/reference/, loaded
by the `news_lexicon` fixture, so these tests exercise the real weights rather
than a copy that could drift from what the pipeline runs.
"""

from __future__ import annotations

import polars as pl
import pytest

from src.pipeline.news.lexicon.steps import (
    _parse_number,
    analyse,
    build,
    count_mentions,
    severity_score,
)
from src.pipeline.news.lexicon.spec import NATIONAL_LOCATION, OUTPUT_COLUMNS


def _normalize(text: str) -> str:
    from src.pipeline.news.common import strip_accents

    return strip_accents(text)


# --- the numeral parser -----------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "scale", "expected"),
    [
        # Dotted-thousands grouping: the dots are the separator and the trailing
        # `mil` is a redundant reading of them. Multiplying gives 36.8 million
        # cases of dengue in one state.
        ("36.791", "mil", 36_791),
        ("6.131", "mil", 6_131),
        # No dots, so `mil` really does multiply.
        ("500", "mil", 500_000),
        ("6,6", "milhoes", 6_600_000),
        ("1.240", None, 1_240),
        ("380", None, 380),
    ],
)
def test_parse_number(raw: str, scale: str | None, expected: int) -> None:
    assert _parse_number(raw, scale) == expected


def test_parse_number_rejects_implausible_values() -> None:
    """A count above the plausibility ceiling is dropped, not emitted.

    The ceiling exists because a wrong count is worse for the model than a
    missing one — the reverse of the usual precision/recall preference.
    """
    assert _parse_number("99.000.000", None) is None
    assert _parse_number("0", None) is None


# --- the three gates on counts ---------------------------------------------


def test_count_gate_drops_a_negated_number(news_lexicon) -> None:
    text = _normalize("Não foram registrados 500 casos de dengue no município.")
    assert count_mentions(text, news_lexicon)[0] is None


def test_count_gate_drops_another_diseases_number(news_lexicon) -> None:
    """"11.881.430 casos de DRSAI" sits in an article that is about dengue."""
    text = _normalize(
        "A dengue avança e foram 11.881.430 casos de DRSAI, segundo o ministério."
    )
    assert count_mentions(text, news_lexicon)[0] is None


def test_count_gate_requires_the_sentence_to_name_dengue(news_lexicon) -> None:
    """Load-bearing and costly: this drops a real count.

    "No estado de São Paulo, foram 36.791 casos" never says "dengue", so it is
    dropped. The deliberate direction is to lose the count rather than keep one
    that may be an order of magnitude off — braço 04 recovers these.
    """
    unqualified = _normalize("No estado de São Paulo, foram 36.791 casos.")
    assert count_mentions(unqualified, news_lexicon)[0] is None

    named = _normalize("No estado de São Paulo, foram 36.791 casos de dengue.")
    assert count_mentions(named, news_lexicon)[0] == 36_791


def test_count_gate_keeps_deaths_separate_from_cases(news_lexicon) -> None:
    text = _normalize(
        "A dengue provocou 8.400 óbitos e 1.500.000 casos no país neste ano."
    )
    cases, deaths = count_mentions(text, news_lexicon)
    assert deaths == 8_400
    assert cases == 1_500_000


def test_count_is_a_maximum_not_a_sum(news_lexicon) -> None:
    """A week's coverage repeats one cumulative figure across articles.

    Summing would scale with how often the press repeated the number rather
    than with the epidemic.
    """
    text = _normalize(
        "Foram 500 mil casos de dengue. "
        "O balanço anterior apontava 500 mil casos de dengue."
    )
    assert count_mentions(text, news_lexicon)[0] == 500_000


# --- severity ---------------------------------------------------------------


def test_severity_scores_outbreak_above_alert(news_lexicon) -> None:
    """The weights are ordinal, not calibrated — they order and stop there."""
    alert = severity_score(_normalize("O município está em alerta."), news_lexicon)
    outbreak = severity_score(_normalize("O município vive um surto."), news_lexicon)
    epidemic = severity_score(_normalize("O estado enfrenta uma epidemia."), news_lexicon)
    assert 0 < alert < outbreak < epidemic


def test_severity_is_dropped_inside_a_negation_window(news_lexicon) -> None:
    """A character window, not syntax — so this is deliberately crude."""
    assert severity_score(_normalize("Não há surto na região."), news_lexicon) == 0
    assert severity_score(_normalize("Há surto na região."), news_lexicon) > 0


# --- geo scoping ------------------------------------------------------------


def test_full_state_name_matches_case_sensitively(news_matcher) -> None:
    """`Pará` must not match the preposition `para` in any article ever written.

    Accent-folding both sides is what the rest of the pipeline does for
    matching, and here it would be catastrophic: nearly every Portuguese
    sentence contains "para".
    """
    assert news_matcher.find("O ministro viajou para Brasília.") == set()
    assert news_matcher.find("O surto no Pará cresceu.") == {"PA"}


def test_bare_two_letter_codes_do_not_match(news_matcher) -> None:
    """`SE` is a reflexive pronoun and `PA` collides with `p.a.`."""
    assert news_matcher.find("SP registrou casos.") == set()
    assert news_matcher.find("O estado de SP registrou casos.") == {"SP"}
    assert news_matcher.find("Casos no RJ cresceram.") == {"RJ"}
    assert news_matcher.find("O avanço (MG) preocupa.") == {"MG"}


def test_analyse_spreads_one_article_across_locations(news_lexicon, news_matcher) -> None:
    signals = analyse(
        "O Rio de Janeiro e a Bahia registraram 1.200 casos de dengue.",
        "",
        news_lexicon,
        news_matcher,
    )
    assert signals.locations == {"RJ", "BA"}
    assert signals.cases == 1_200
    assert signals.has_disease_term


def test_analyse_reports_no_disease_term_for_an_unrelated_page(
    news_lexicon, news_matcher
) -> None:
    signals = analyse("O congresso discutiu a reforma tributária.", "", news_lexicon, news_matcher)
    assert not signals.has_disease_term


# --- aggregation ------------------------------------------------------------


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


def test_build_spreads_across_br_and_each_named_uf(news_lexicon, news_matcher) -> None:
    from datetime import date

    corpus = _corpus([
        {
            "article_id": "a",
            "published_at": "2011-01-11T06:14:00",
            "ew": date(2011, 1, 9),
            "title": "",
            "text": "A dengue no Rio de Janeiro preocupa as autoridades.",
            "lang_guess": "pt",
        }
    ])
    frame = build(corpus, news_lexicon, news_matcher)
    assert set(frame["location"].to_list()) == {NATIONAL_LOCATION, "RJ"}
    assert tuple(frame.columns) == OUTPUT_COLUMNS
    assert set(frame["news_volume"].to_list()) == {1}


def test_build_omits_weeks_with_no_article(news_lexicon, news_matcher) -> None:
    """A week with no coverage is absent, not zero.

    Emitting the dense grid would assert 0 for every UF the national news never
    names, which is a different claim from "no article this week".
    """
    from datetime import date

    corpus = _corpus([
        {
            "article_id": "a",
            "published_at": "2011-01-11T06:14:00",
            "ew": date(2011, 1, 9),
            "title": "",
            "text": "A dengue no Rio de Janeiro preocupa as autoridades.",
            "lang_guess": "pt",
        }
    ])
    frame = build(corpus, news_lexicon, news_matcher)
    assert frame["ew"].n_unique() == 1


def test_build_drops_non_portuguese_when_asked(news_lexicon, news_matcher) -> None:
    from datetime import date

    rows = [
        {
            "article_id": "pt",
            "published_at": "2011-01-11T06:14:00",
            "ew": date(2011, 1, 9),
            "title": "",
            "text": "A dengue avança no país.",
            "lang_guess": "pt",
        },
        {
            "article_id": "es",
            "published_at": "2011-01-11T06:14:00",
            "ew": date(2011, 1, 9),
            "title": "",
            "text": "El dengue avanza en el país.",
            "lang_guess": "other",
        },
    ]
    kept = build(_corpus(rows), news_lexicon, news_matcher, portuguese_only=False)
    dropped = build(_corpus(rows), news_lexicon, news_matcher, portuguese_only=True)
    assert kept.filter(pl.col("location") == NATIONAL_LOCATION)["news_volume"][0] == 2
    assert dropped.filter(pl.col("location") == NATIONAL_LOCATION)["news_volume"][0] == 1


def test_build_over_the_fixture_corpus(news_features: pl.DataFrame) -> None:
    """Every fixture page is about dengue, so every week carries a BR row.

    The five pages land in five different weeks — including the one whose body
    was never fetched, which still counts because its *title* names dengue.
    """
    assert tuple(news_features.columns) == OUTPUT_COLUMNS
    br = news_features.filter(pl.col("location") == NATIONAL_LOCATION)
    assert br.height == 5
    assert br.height == news_features["ew"].n_unique()
    assert set(br["news_volume"].to_list()) == {1}
