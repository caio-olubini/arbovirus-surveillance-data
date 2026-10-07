"""Frozen corpus → news-text table: manifest join, extraction, EW alignment.

Unlike the other transform stages this one is *eager*. `build()` returns a
`pl.DataFrame`, not a `LazyFrame`, because the expensive step is parsing 4,569
HTML files in Python — there is no query plan for polars to optimise, and a lazy
frame would only defer the same loop. The convention is kept everywhere it can
be (a single `build()` entry point, spec-driven column order).
"""

from __future__ import annotations

import html
import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import polars as pl

from ...epiweek import floor_to_sunday
from ..common import extract, guess_language
from .spec import (
    ARTICLE_ID,
    ARTICLES_DIRNAME,
    BODYLESS_MAX_CHARS,
    CHAR_COUNT,
    ERA,
    EW,
    EXTRACTOR,
    LANG_GUESS,
    LISTING_TITLE,
    MANIFEST_NAME,
    OUTPUT_COLUMNS,
    PUBLISHED_AT,
    SECTION,
    TEXT,
    TITLE,
    URL,
)

log = logging.getLogger("pipeline.news.text")

# `published_at` is a naive local datetime ("2026-09-16T16:44:00"). Reading it as
# a string and parsing explicitly avoids polars inferring a timezone.
PUBLISHED_FORMAT = "%Y-%m-%dT%H:%M:%S"

# Declared so an all-null column (e.g. a corpus with no `section`) still gets the
# published dtype instead of polars inferring Null.
SCHEMA: dict[str, pl.DataType] = {
    ARTICLE_ID: pl.String,
    PUBLISHED_AT: pl.String,
    SECTION: pl.String,
    URL: pl.String,
    TITLE: pl.String,
    LISTING_TITLE: pl.String,
    TEXT: pl.String,
    ERA: pl.String,
    EXTRACTOR: pl.String,
    CHAR_COUNT: pl.Int64,
    LANG_GUESS: pl.String,
}


def bodyless_expr() -> pl.Expr:
    """Rows whose text is a bare byline — a page saved without its article body.

    Three era-B pages were fetched without a body: the HTML jumps from the
    headline straight to the "Últimas notícias" rail, so all that is left is the
    credit line. They stay in the corpus — the article was published and its
    *title* names dengue, so `news_volume` should count it — but their text is
    not article content.

    The test is anchored on the byline's trailing site credit, not on shortness
    alone, and that is deliberate. Bug 1 produced 20-character bodies too
    ("Agência Brasil A+ A-"), so a length-only rule would quietly reclassify that
    regression as a truncated fetch and exempt it from `min_length` — the guard
    would stop guarding. The byline ends with the site credit; the header chrome
    does not. Anything the rule does not recognise falls through to the length
    guard, which is the loud direction.
    """
    tail = pl.col(TEXT).fill_null("").str.to_lowercase().str.strip_chars()
    return (pl.col(CHAR_COUNT) < BODYLESS_MAX_CHARS) & tail.str.contains(
        r"ag[êe]ncia brasil$"
    )


def load_manifest(root: Path) -> list[dict[str, Any]]:
    """Read the scraper's manifest, keeping only rows with a saved article.

    The scraper records every URL it saw, including the two whose fetch failed
    and therefore carry `local_path: null`. Those have no HTML to extract and are
    dropped here rather than surfacing as empty rows downstream.
    """
    path = root / MANIFEST_NAME
    if not path.exists():
        raise FileNotFoundError(
            f"EBC manifest not found: {path}. Run `arboili ebc` first."
        )
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("local_path"):
                rows.append(row)
    return rows


def missing_article_files(root: Path) -> list[Path]:
    """Manifest entries whose HTML is absent from disk.

    The corpus is frozen, so this being non-empty means data was moved or lost —
    not that the article should quietly become an empty row. `transform` surfaces
    the count in its result; `iter_rows` warns per file.
    """
    return [
        root / row["local_path"]
        for row in load_manifest(root)
        if not (root / row["local_path"]).exists()
    ]


def iter_rows(root: Path) -> Iterator[dict[str, Any]]:
    """Yield one dict per article: manifest metadata + extracted text.

    A file named in the manifest but absent on disk is skipped with a warning —
    the corpus is frozen, so a missing file means someone moved data, not that
    the article should silently become an empty row.
    """
    for row in load_manifest(root):
        path = root / row["local_path"]
        if not path.exists():
            log.warning("manifest lists a missing file: %s", path)
            continue
        got = extract(path.read_text(encoding="utf-8", errors="replace"))
        yield {
            ARTICLE_ID: path.stem,
            PUBLISHED_AT: row.get("published_at"),
            SECTION: row.get("section"),
            URL: row.get("url"),
            TITLE: got.title,
            # The scraper stored the listing title with entities intact.
            LISTING_TITLE: html.unescape(row.get("title") or ""),
            TEXT: got.text,
            ERA: got.era,
            EXTRACTOR: got.extractor,
            CHAR_COUNT: got.char_count,
            LANG_GUESS: guess_language(got.text),
        }


def add_ew(frame: pl.DataFrame) -> pl.DataFrame:
    """Derive the Sunday-anchored epi week from `published_at`."""
    return frame.with_columns(
        pl.col(PUBLISHED_AT)
        .str.to_datetime(PUBLISHED_FORMAT, strict=False)
        .alias(PUBLISHED_AT)
    ).with_columns(floor_to_sunday(PUBLISHED_AT).alias(EW))


def order_columns(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.select(OUTPUT_COLUMNS).sort(PUBLISHED_AT, ARTICLE_ID)


def build(root: Path) -> pl.DataFrame:
    """Extract every article under `root` into the frozen text corpus."""
    rows = list(iter_rows(root))
    if not rows:
        raise ValueError(
            f"No extractable articles under {root}. Expected {ARTICLES_DIRNAME}/ "
            f"and {MANIFEST_NAME} written by `arboili ebc`."
        )
    frame = pl.DataFrame(rows, schema=SCHEMA)
    return order_columns(add_ew(frame))
