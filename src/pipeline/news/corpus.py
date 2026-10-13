"""Protocol-00 common ground: which articles a braço may see, and where they count.

Not the frozen text table — that is `text/`, and it *is* the corpus. This module
decides the **analysis corpus**: the subset of that table a representation braço is
allowed to look at, and the locations each surviving article counts for.

Both belong here rather than inside any braço, because
[`notes/00-protocolo-comparacao.md`](../../../../notes/00-protocolo-comparacao.md)
fixes them as invariant: only the *representation* of the text may differ between
braços 01, 02 and 03. If one braço sees 4,369 articles and another sees 4,569, the
comparison measures the filter instead of the representation — so the filter has
to be one function, called by all of them, not three copies that happen to agree
today.

Layering: this module sits *above* `common` and `lexicon` and *below* the braços.
It is the reason `embeddings` and `topics` can both be complete without either
importing the other — the braços are parallel, so a shared piece cannot live in
one of them.
"""

from __future__ import annotations

import polars as pl

from .common import strip_accents
from .lexicon.steps import Lexicon, UfMatcher, mentions_disease
from .text.spec import ARTICLE_ID, LANG_GUESS, TEXT, TITLE

# UFs an article names, before BR is added. A List column, not a wide boolean
# matrix: the number of UFs per article is small and the join that consumes it
# explodes it anyway.
LOCATIONS = "locations"


def article_input(title: str | None, text: str | None) -> str:
    """Title and body as one string — the join every matcher works against.

    The title is the headline, which is where a week's framing lives ("Surto de
    dengue cresce no interior de SP"), so dropping it would throw away the most
    topical sentence of the article.
    """
    return f"{title or ''}\n{text or ''}"


def select_articles(
    corpus: pl.DataFrame,
    lexicon: Lexicon,
    portuguese_only: bool = True,
    require_disease_term: bool = True,
) -> tuple[pl.DataFrame, int]:
    """The article set a braço may see, and how many were dropped.

    Two gates, both protocol-00 common ground:

    * **Language.** `lang_guess == "pt"` drops the ~3.7% of the corpus Agência
      Brasil publishes in Spanish. The slice is not random — 61 of the 171 are
      from 2016, the Zika and Olympics year — so leaving it in would add articles
      whose text no PT-BR term can match, inflating volume while measuring nothing.
    * **Disease term.** Drops errata pages, photo-agenda stubs and digests whose
      dengue link is incidental.

    Returns the kept frame *and* the dropped count, because a caller that has to
    justify the article set needs the number, not just the survivors.
    """
    kept = corpus
    if portuguese_only and LANG_GUESS in kept.columns:
        kept = kept.filter(pl.col(LANG_GUESS) == "pt")
    if require_disease_term:
        # Row-wise on purpose: the gate is a regex sweep over thousands of bodies,
        # and a `map_elements` expression would be slower and harder to read than
        # this. `mentions_disease` is braço 01's own function, imported rather than
        # re-implemented — the point of the shared module.
        keep_mask = [
            mentions_disease(strip_accents(article_input(title, text)), lexicon)
            for title, text in kept.select(TITLE, TEXT).iter_rows()
        ]
        kept = kept.filter(pl.Series(keep_mask, dtype=pl.Boolean))
    return kept, corpus.height - kept.height


def scoped_locations(corpus: pl.DataFrame, matcher: UfMatcher) -> pl.DataFrame:
    """The UFs each article names. BR is added later, at aggregation time.

    Mention-based and state-level, which is a declared limitation rather than an
    implementation detail: an article that says only "Araçatuba" counts for BR and
    not for SP. It is the same `UfMatcher` braço 01 uses, so the per-UF series of
    all three braços share one bias instead of three different ones.
    """
    rows = [
        {
            ARTICLE_ID: article_id,
            LOCATIONS: sorted(matcher.find(article_input(title, text))),
        }
        for article_id, title, text in corpus.select(ARTICLE_ID, TITLE, TEXT).iter_rows()
    ]
    return pl.DataFrame(
        rows, schema={ARTICLE_ID: pl.String, LOCATIONS: pl.List(pl.String)}
    )


__all__ = [
    "LOCATIONS",
    "article_input",
    "scoped_locations",
    "select_articles",
]
