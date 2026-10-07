"""Integrity checks over the frozen news-text corpus.

Each returns a `Check`; nothing raises. `run_all` gathers them so a caller can
print a report and decide. The checks are ordered cheapest-first: schema and keys
before anything that scans the body text.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from ..common import strip_accents
from .steps import bodyless_expr
from .spec import (
    ARTICLE_ID,
    CHAR_COUNT,
    ERA,
    EW,
    GROUP_KEYS,
    KNOWN_ERAS,
    KNOWN_LANGS,
    LANG_GUESS,
    LISTING_TITLE,
    MIN_CHARS,
    MIN_TITLE_AGREEMENT,
    OUTPUT_COLUMNS,
    TEXT,
    TITLE,
)

SUNDAY = 7


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str = ""

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}{f': {self.detail}' if self.detail else ''}"


def check_schema(corpus: pl.DataFrame) -> Check:
    actual = tuple(corpus.columns)
    if actual == OUTPUT_COLUMNS:
        return Check("schema", True, f"{len(actual)} columns in published order")
    return Check("schema", False, f"expected {OUTPUT_COLUMNS}, got {actual}")


def check_unique_keys(corpus: pl.DataFrame) -> Check:
    duplicates = corpus.height - corpus.select(GROUP_KEYS).unique().height
    if duplicates == 0:
        return Check("unique_keys", True, f"{corpus.height:,} rows, all keys distinct")
    return Check("unique_keys", False, f"{duplicates:,} duplicate {ARTICLE_ID}")


def check_weeks_start_on_sunday(corpus: pl.DataFrame) -> Check:
    bad = corpus.filter(
        pl.col(EW).is_not_null() & (pl.col(EW).dt.weekday() != SUNDAY)
    ).height
    null_ew = corpus.filter(pl.col(EW).is_null()).height
    if bad or null_ew:
        return Check(
            "weeks_start_on_sunday",
            False,
            f"{bad:,} non-Sunday and {null_ew:,} null ew values",
        )
    return Check("weeks_start_on_sunday", True, "all ew dates are Sundays")


def check_min_length(corpus: pl.DataFrame) -> Check:
    """Catch a regression to a header element, which yields ~20 chars.

    Reported with the shortest offender named, because the failure this guards
    against is invisible in an aggregate: a table of plausible titles with no
    article text behind them. Pages saved without a body are excluded — they are
    not a length regression and `bodyless_pages` names them instead.
    """
    short = corpus.filter(~bodyless_expr() & (pl.col(CHAR_COUNT) < MIN_CHARS))
    if short.height == 0:
        shortest = corpus[CHAR_COUNT].min()
        return Check(
            "min_length",
            True,
            f"{corpus.height:,} rows, shortest {shortest:,} chars",
        )
    names = ", ".join(short[ARTICLE_ID].head(3).to_list())
    return Check(
        "min_length",
        False,
        f"{short.height:,} rows under {MIN_CHARS} chars (e.g. {names})",
    )


def check_bodyless_pages(corpus: pl.DataFrame) -> Check:
    """Report pages saved without an article body; never fail on them.

    Three era-B pages (two from 2008-04-02, one from 2008-11-20) were fetched
    without their body: the saved HTML jumps from the headline to the
    "Últimas notícias" rail. They stay in the corpus — the article was published
    and names dengue, so `news_volume` should see it — but their text is a
    byline, so nothing downstream should read them for content. Reported rather
    than dropped for the same reason `langs_known` reports the Spanish slice: it
    is a property of the source, and its size is what a consumer needs.
    """
    flagged = corpus.filter(bodyless_expr())
    if flagged.height == 0:
        return Check("bodyless_pages", True, "every row carries article text")
    names = ", ".join(flagged[ARTICLE_ID].head(3).to_list())
    return Check(
        "bodyless_pages",
        True,
        f"{flagged.height} page(s) saved without a body (e.g. {names})",
    )


def check_eras_known(corpus: pl.DataFrame) -> Check:
    """Unknown era labels fail; `fallback` passes but is called out.

    A fallback row used the heuristic extractor, which is legitimate for a page
    the two selectors miss — but it is the population most likely to be subtly
    wrong, so its size belongs in the report.
    """
    counts = dict(corpus.group_by(ERA).len().iter_rows())
    unknown = sorted(set(counts) - set(KNOWN_ERAS))
    if unknown:
        return Check("eras_known", False, f"unexpected era labels: {unknown}")
    fallback = counts.get("fallback", 0)
    detail = ", ".join(f"{k}={v:,}" for k, v in sorted(counts.items()))
    if fallback:
        return Check("eras_known", True, f"{detail} — {fallback:,} via heuristic")
    return Check("eras_known", True, detail)


def check_langs_known(corpus: pl.DataFrame) -> Check:
    """Report the language split; never fail on it.

    A non-Portuguese article is a property of the corpus, not a defect. It is
    called out here because the braços that assume Portuguese need to know its
    size, and because the split is uneven across years.
    """
    counts = dict(corpus.group_by(LANG_GUESS).len().iter_rows())
    unknown = sorted(set(counts) - set(KNOWN_LANGS))
    if unknown:
        return Check("langs_known", False, f"unexpected lang values: {unknown}")
    detail = ", ".join(f"{k}={v:,}" for k, v in sorted(counts.items()))
    other = counts.get("other", 0)
    if other:
        by_year = (
            corpus.filter(pl.col(LANG_GUESS) == "other")
            .with_columns(pl.col(EW).dt.year().alias("year"))
            .group_by("year")
            .len()
            .sort("len", descending=True)
            .head(2)
            .iter_rows()
        )
        peaks = ", ".join(f"{year}={n}" for year, n in by_year)
        return Check("langs_known", True, f"{detail} — non-PT peaks at {peaks}")
    return Check("langs_known", True, detail)


def check_text_present(corpus: pl.DataFrame) -> Check:
    blank = corpus.filter(
        pl.col(TEXT).is_null() | (pl.col(TEXT).str.strip_chars() == "")
    ).height
    if blank == 0:
        return Check("text_present", True, f"{corpus.height:,} non-empty bodies")
    return Check("text_present", False, f"{blank:,} rows with empty body text")


def check_title_present(corpus: pl.DataFrame) -> Check:
    blank = corpus.filter(
        pl.col(TITLE).is_null() | (pl.col(TITLE).str.strip_chars() == "")
    ).height
    if blank == 0:
        return Check("title_present", True, f"{corpus.height:,} titles present")
    return Check("title_present", False, f"{blank:,} rows with an empty title")


def check_title_agreement(corpus: pl.DataFrame) -> Check:
    """Page title vs. the title the scraper read off the listing.

    Two independent reads of the same headline. They disagree when the extractor
    latches onto a nav heading, which is how the era-B regression looked.

    Both sides are accent-folded and whitespace-normalized before comparing. The
    scraper stores the listing title with HTML entities intact, so `steps`
    unescapes it on the way into the corpus — this check compares two already
    clean strings and deliberately does not re-unescape. The threshold is a
    floor rather than equality: 0.9% of the corpus differs in punctuation the
    site itself renders inconsistently.
    """
    pairs = corpus.select(TITLE, LISTING_TITLE).iter_rows()
    total = 0
    agree = 0
    for page, listing in pairs:
        if not page or not listing:
            continue
        total += 1
        if strip_accents(" ".join(page.split())) == strip_accents(" ".join(listing.split())):
            agree += 1
    if total == 0:
        return Check("title_agreement", False, "no rows carry both titles")
    share = agree / total
    if share >= MIN_TITLE_AGREEMENT:
        return Check("title_agreement", True, f"{share:.1%} of {total:,} rows agree")
    return Check(
        "title_agreement",
        False,
        f"{share:.1%} agree, below the {MIN_TITLE_AGREEMENT:.0%} floor "
        f"({total - agree:,} divergent)",
    )


def run_all(corpus: pl.DataFrame) -> list[Check]:
    return [
        check_schema(corpus),
        check_unique_keys(corpus),
        check_weeks_start_on_sunday(corpus),
        check_min_length(corpus),
        check_bodyless_pages(corpus),
        check_eras_known(corpus),
        check_langs_known(corpus),
        check_text_present(corpus),
        check_title_present(corpus),
        check_title_agreement(corpus),
    ]
