"""Extraction, language guessing and EW alignment over the news fixtures.

The fixture set is chosen so each assertion here covers a *different* path
through `common.extract`, because that is where this stage's two real bugs lived
and neither was visible in the corpus's own summary statistics.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from src.pipeline.news.common import (
    ERA_B,
    ERA_C,
    ERA_FALLBACK,
    extract,
    guess_language,
    strip_accents,
)
from src.pipeline.news.text.spec import OUTPUT_COLUMNS

# A headline from the "Últimas notícias" rail that every era-B page carries.
RAIL_HEADLINE = "Com shopping fechado no Rio"
RAIL_TITLE = "Últimas notícias"

ERA_B_2002 = "2002-09-30_584838_b533c1.html"
ERA_B_2011 = "2011-01-11_ministros-discutem-acoes-de-prevencao-e-controle-da-dengue-no-pais_4c9f9c.html"
ERA_B_BODYLESS = "2008-04-02_escolas-precisam-realizar-trabalho-de-conscientizacao-sobre-dengue-diz-temporao_861d4e.html"
ERA_C_2016 = "2016-02-04_presidente-dilma-pede-uniao-no-combate-ao-aedes-aegypti_1cef5f.html"
FALLBACK = "2021-03-14_synthetic-fallback-page_000001.html"


def _extract(news_fixture_dir: Path, name: str):
    html = (news_fixture_dir / "articles" / name).read_text(encoding="utf-8", errors="replace")
    return extract(html)


def test_era_b_body_is_the_article_not_the_news_rail(news_fixture_dir: Path) -> None:
    """The regression test for the scorer's second bug.

    Both era-B pages carry three `div.inside` elements and the third is the
    rail, which is *longer* than the article. Scoring on total text picked it
    for 42% of the real era-B corpus.
    """
    for name in (ERA_B_2002, ERA_B_2011):
        got = _extract(news_fixture_dir, name)
        assert got.era == ERA_B
        assert not got.text.startswith(RAIL_TITLE)
        assert RAIL_HEADLINE not in got.text


def test_era_b_title_comes_from_the_title_tag(news_fixture_dir: Path) -> None:
    """On era B the `<h1>` is the site name, so it must not be used as a title."""
    got = _extract(news_fixture_dir, ERA_B_2002)
    assert got.title == "Fórum discute combate à dengue no Rio"
    assert got.title != "Agência Brasil"


def test_era_c_uses_the_article_node(news_fixture_dir: Path) -> None:
    got = _extract(news_fixture_dir, ERA_C_2016)
    assert got.era == ERA_C
    assert got.extractor == "div.node-conteudo"
    assert got.title == "Presidenta Dilma pede união no combate ao Aedes aegypti"
    assert got.char_count == 163  # the corpus's shortest real body


def test_page_matching_no_container_falls_back(news_fixture_dir: Path) -> None:
    got = _extract(news_fixture_dir, FALLBACK)
    assert got.era == ERA_FALLBACK
    assert got.extractor == "largest-paragraph-block"
    # Multi-paragraph, so the heuristic did not truncate to the first one.
    assert got.text.count("Aedes aegypti") == 1
    assert "unidade de saúde mais próxima" in got.text


def test_bodyless_page_keeps_its_byline(news_fixture_dir: Path) -> None:
    """A page saved without a body yields the byline, not the rail and not ''."""
    got = _extract(news_fixture_dir, ERA_B_BODYLESS)
    assert got.era == ERA_B
    assert got.text == "Danilo Macedo Repórter da Agência Brasil"
    assert got.char_count == 40


def test_strip_accents_folds_for_matching() -> None:
    assert strip_accents("Notificação") == "notificacao"
    assert strip_accents("ÓBITOS") == "obitos"
    # Folding is what makes "Pará" and the preposition collide; callers that
    # need to tell them apart match the original text instead.
    assert strip_accents("Pará") == strip_accents("para")


def test_guess_language_separates_spanish_from_portuguese() -> None:
    spanish = (
        "El ministro de Salud dijo que los casos de dengue aumentaron. "
        "Según las autoridades, hay millones de personas en riesgo. "
        "Durante el verano, la situación se agravó en el país vecino."
    )
    portuguese = (
        "O ministro da Saúde disse que os casos de dengue aumentaram. "
        "Segundo as autoridades, há milhões de pessoas em risco. "
        "Durante o verão, a situação se agravou no país."
    )
    assert guess_language(spanish) == "other"
    assert guess_language(portuguese) == "pt"


def test_guess_language_defaults_to_pt_when_unsure() -> None:
    """The fallback is Portuguese: a PT-BR lexicon reading a short text is the
    safe direction, since the alternative silently drops the article."""
    assert guess_language("Dengue em São Paulo.") == "pt"
    assert guess_language("") == "pt"


def test_build_emits_the_published_schema(news_corpus: pl.DataFrame) -> None:
    assert tuple(news_corpus.columns) == OUTPUT_COLUMNS
    assert news_corpus.height == 5
    assert news_corpus["article_id"].n_unique() == 5


def test_build_aligns_every_week_to_a_sunday(news_corpus: pl.DataFrame) -> None:
    weekdays = news_corpus["ew"].dt.weekday().unique().to_list()
    assert weekdays == [7]


def test_build_keeps_the_bodyless_page(news_corpus: pl.DataFrame) -> None:
    """It is a published dengue article; only its text is missing.

    Dropping it would understate `news_volume`, so the row stays and the
    integrity check names it instead.
    """
    row = news_corpus.filter(pl.col("article_id").str.starts_with("2008-04-02_escolas"))
    assert row.height == 1
    assert row["char_count"][0] == 40
    assert row["era"][0] == ERA_B
