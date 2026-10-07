"""Shared news-text extraction and normalization.

`extract` turns one saved Agência Brasil page into clean article text; every news
stage reads the frozen corpus that produces, so this module runs in exactly one
place. `strip_accents` is the matching-time normalization the lexicon stage and
the title-agreement check both need. The module lives at the package root because
all three representation braços depend on it and none of them owns it.

The corpus spans two template generations, and the boundary is not cosmetic:

  era "b"  (2002-2014)  body in ``div.inside``; ``<h1>`` holds the *site* name
                        ("Agência Brasil"), so the title only exists in ``<title>``
  era "c"  (2014-2026)  body in ``main.main-site > div.node-conteudo``;
                        ``<h1>`` holds the real title

The era is detected and recorded per article, together with the rule that fired.
A silent fallback would produce a corpus that looks fine and is subtly wrong,
which is exactly the failure this pipeline exists to avoid.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

ERA_B = "b"
ERA_C = "c"
ERA_FALLBACK = "fallback"

# Era C containers, most specific first. `node-conteudo` is the article node;
# `container-noticia` is its wrapper; `region-content` is the last resort before
# falling back to heuristics.
ERA_C_SELECTORS: tuple[str, ...] = (
    "div.node-conteudo",
    "div.container-noticia",
    "div.region-content",
)

# Era B container. Verified present across the whole 2002-2014 span.
ERA_B_SELECTORS: tuple[str, ...] = ("div.inside",)

# `<title>` carries the article title on both eras, with the site name appended.
_TITLE_SUFFIX = re.compile(r"\s*[|\-–]\s*Ag[eê]ncia Brasil\s*$", re.IGNORECASE)

# Boilerplate that sits inside the extracted container on some pages.
_BOILERPLATE = (
    re.compile(r"Raz[ãa]o Social:\s*Empresa Brasil de Comunica[çc][ãa]o.*$", re.DOTALL),
    re.compile(r"Todo o conte[úu]do deste site est[áa] publicado.*$", re.DOTALL),
)

_WHITESPACE = re.compile(r"[ \t ]+")
_BLANK_LINES = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class Extracted:
    """One article's text plus the provenance of how it was obtained."""

    title: str
    text: str
    era: str
    extractor: str

    @property
    def char_count(self) -> int:
        return len(self.text)


def strip_accents(value: str) -> str:
    """Drop combining marks and casefold — for matching, never for display.

    Portuguese inflects and accents heavily ("notificação"/"notificacao",
    "óbito"/"obitos"), and the corpus is 24 years of inconsistent typesetting.
    Normalizing both the pattern and the haystack is what makes a single
    lowercase lexicon entry match every surface form.
    """
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()


# Agência Brasil publishes in Spanish as well as Portuguese. Counting function
# words on a normalized sample is crude but sufficient, and the crude parts are
# bounded: the two marker sets are disjoint enough that a Portuguese article
# cannot out-score its own language by accident.
_LANG_SAMPLE_CHARS = 1500
_PT_MARKERS = (" o ", " a ", " dos ", " das ", " nao ", " para o ", " milhoes ")
_ES_MARKERS = (" el ", " los ", " las ", " millones ", " de la ", " en el ", " que se ")
_LANG_MIN_MARKERS = 3


def guess_language(text: str) -> str:
    """`"pt"` or `"other"` — a marker-count heuristic, not detection.

    This exists because the corpus is not monolingual and the non-Portuguese
    slice is *not* random: 61 of the 172 Spanish articles are from 2016, the
    Zika and Olympics year. A PT-BR lexicon silently under-counts those weeks,
    and a bias that lands on an epidemic year is worth carrying as a column
    rather than discovering in review.
    """
    probe = f" {strip_accents(text[:_LANG_SAMPLE_CHARS])} "
    portuguese = sum(1 for marker in _PT_MARKERS if marker in probe)
    spanish = sum(1 for marker in _ES_MARKERS if marker in probe)
    if spanish >= _LANG_MIN_MARKERS and spanish > portuguese:
        return "other"
    return "pt"


def clean_text(value: str) -> str:
    """Collapse runs of spaces, drop blank-line runs, strip the ends."""
    value = _WHITESPACE.sub(" ", value)
    value = "\n".join(line.strip() for line in value.split("\n"))
    value = _BLANK_LINES.sub("\n\n", value)
    return value.strip()


def _strip_boilerplate(value: str) -> str:
    for pattern in _BOILERPLATE:
        value = pattern.sub("", value)
    return value


def _largest_paragraph_block(soup: BeautifulSoup) -> Tag | None:
    """Heuristic last resort: the parent holding the most paragraph text.

    Groups ``<p>`` by their parent and returns the parent with the largest total
    text. Grouping by parent rather than picking the single longest ``<p>`` keeps
    multi-paragraph articles from being truncated to their first paragraph.
    """
    totals: dict[Tag, int] = {}
    for paragraph in soup.find_all("p"):
        parent = paragraph.parent
        if isinstance(parent, Tag):
            totals[parent] = totals.get(parent, 0) + len(paragraph.get_text(" ", strip=True))
    if not totals:
        return None
    best = max(totals, key=lambda tag: totals[tag])
    return best if totals[best] >= 120 else None


def _container_score(tag: Tag) -> tuple[int, int]:
    """(paragraph text, link-free text) — how a body differs from page furniture.

    Era B pages carry three ``div.inside`` elements: a 20-character header, the
    article, and a "Últimas notícias" rail. Scoring on *all* text picks the rail,
    which out-scores the article on sheer volume while containing almost no
    prose — 1,126 of its 1,279 characters are anchor text.

    Paragraph text first: an article body has ``<p>`` elements and a rail does
    not, which settles it outright. Link-free text is the tiebreak for the pages
    whose body has no ``<p>`` at all, where both candidates score zero on the
    first key and only what remains after removing links separates them.
    """
    paragraphs = tag.find_all("p")
    paragraph_text = sum(len(p.get_text(" ", strip=True)) for p in paragraphs)
    total = len(tag.get_text(" ", strip=True))
    linked = sum(len(a.get_text(" ", strip=True)) for a in tag.find_all("a"))
    return paragraph_text, total - linked


def _best_match(soup: BeautifulSoup, selectors: tuple[str, ...]) -> tuple[Tag | None, str]:
    """First selector that matches anything, and its richest match.

    Not ``select_one``: era B pages carry several ``div.inside`` (a header one and
    the article one), and the first is the wrong one.
    """
    for selector in selectors:
        matches = soup.select(selector)
        if matches:
            return max(matches, key=_container_score), selector
    return None, ""


def _find_body(soup: BeautifulSoup) -> tuple[Tag | None, str, str]:
    """Return (container, era, extractor) for the best available rule."""
    found, selector = _best_match(soup, ERA_C_SELECTORS)
    if found is not None:
        return found, ERA_C, selector
    found, selector = _best_match(soup, ERA_B_SELECTORS)
    if found is not None:
        return found, ERA_B, selector
    fallback = _largest_paragraph_block(soup)
    if fallback is not None:
        return fallback, ERA_FALLBACK, "largest-paragraph-block"
    return None, ERA_FALLBACK, "none"


def _body_text(container: Tag) -> str:
    """Paragraph-joined text when the container has paragraphs, else all of it.

    Joining ``<p>`` keeps paragraph boundaries in the corpus, which the lexicon
    stage uses to scope count patterns and the topic stage uses as documents.
    """
    paragraphs = container.find_all("p")
    if paragraphs:
        parts = [clean_text(p.get_text(" ", strip=True)) for p in paragraphs]
        joined = "\n\n".join(part for part in parts if part)
        if joined:
            return clean_text(_strip_boilerplate(joined))
    return clean_text(_strip_boilerplate(container.get_text("\n", strip=True)))


def _title(soup: BeautifulSoup, era: str) -> str:
    """Era C keeps the title in ``<h1>``; era B only has it in ``<title>``.

    On era B the ``<h1>`` is the site name, so trusting it would silently label
    2,628 articles "Agência Brasil".
    """
    heading = soup.find("h1")
    if era == ERA_C and heading is not None:
        title = clean_text(heading.get_text(" ", strip=True))
        if title:
            return title
    if soup.title is not None:
        title = _TITLE_SUFFIX.sub("", clean_text(soup.title.get_text(" ", strip=True)))
        if title:
            return title
    if heading is not None:
        return clean_text(heading.get_text(" ", strip=True))
    return ""


def extract(html: str) -> Extracted:
    """Extract title and body text from one saved article page."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    container, era, extractor = _find_body(soup)
    text = _body_text(container) if container is not None else ""
    return Extracted(title=_title(soup, era), text=text, era=era, extractor=extractor)
