"""Schema of the frozen news-text corpus.

One row per saved Agência Brasil article, in the order the three representation
braços (lexicon, embeddings, topics) all read it. Nothing downstream re-parses
HTML: this table *is* the corpus.

The published table is deliberately wide on provenance — `era`, `extractor`,
`listing_title` — because the extraction spans two site generations and a silent
regression to a header element is the failure this stage exists to catch.
"""

from __future__ import annotations

# --- column names -----------------------------------------------------------

ARTICLE_ID = "article_id"
PUBLISHED_AT = "published_at"
EW = "ew"
SECTION = "section"
URL = "url"
TITLE = "title"
LISTING_TITLE = "listing_title"
TEXT = "text"
ERA = "era"
EXTRACTOR = "extractor"
CHAR_COUNT = "char_count"
LANG_GUESS = "lang_guess"

# Keys first, then metadata, then the payload last: a table printed without
# truncation shows the identity of a row before a wall of body text.
OUTPUT_COLUMNS = (
    ARTICLE_ID,
    PUBLISHED_AT,
    EW,
    SECTION,
    URL,
    TITLE,
    LISTING_TITLE,
    TEXT,
    ERA,
    EXTRACTOR,
    CHAR_COUNT,
    LANG_GUESS,
)
GROUP_KEYS = (ARTICLE_ID,)

OUTPUT_NAME = "EBC_dengue_text"

# --- input layout -----------------------------------------------------------

# Written by `arboili ebc` under the query directory.
MANIFEST_NAME = "manifest.jsonl"
ARTICLES_DIRNAME = "articles"

# --- quality thresholds -----------------------------------------------------

# A correct extraction bottoms out at 128 chars (a one-sentence 2002 wire note);
# a header-only regression yields ~20. 100 separates the two without flagging
# any real article.
MIN_CHARS = 100

# Three era-B pages were saved with no article body at all: the HTML jumps from
# the headline straight to the "Últimas notícias" rail. Their extracted text is
# a bare byline — 40 to 45 chars and no sentence terminator. They are kept (the
# article was published and names dengue, so `news_volume` should count it) and
# reported by `bodyless_pages` rather than read as a length regression.
BODYLESS_MAX_CHARS = 100

# `listing_title` is the title the scraper read off the search results, with
# HTML entities left escaped; `title` is what the article page itself says.
# They agree on 99.1% of the corpus, the rest being `&quot;`/`&#039;` — so a
# floor, not an equality.
MIN_TITLE_AGREEMENT = 0.95

# Era labels emitted by `news.common`. `fallback` means neither generation's
# container matched and a heuristic was used; those rows need a human look.
KNOWN_ERAS = ("b", "c", "fallback")

# `lang_guess` values. `other` is almost entirely Spanish — Agência Brasil
# publishes a Spanish edition, and 61 of the 171 non-Portuguese articles are
# from 2016. Braço 01's PT-BR lexicon must not be read as covering them.
KNOWN_LANGS = ("pt", "other")
