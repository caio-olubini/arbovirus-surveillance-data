"""Braço 01 — PT-BR lexicon + rules → weekly news features.

`arboili transform news-lexicon` reads the frozen text corpus, scores it with the
versioned lexicon in `data/news/reference/lexico_dengue.yaml`, and publishes
`news_volume`, `news_severity`, `news_cases` and `news_deaths` per
(epidemiological week, location), location being `BR` or a federative unit.

See notes/01-lexico-regras.md for the hypothesis and the evidence.
"""

from __future__ import annotations

from .spec import EW, LOCATION, OUTPUT_COLUMNS, OUTPUT_NAME
from .transform import NewsLexiconTransformResult, transform

__all__ = [
    "EW",
    "LOCATION",
    "OUTPUT_COLUMNS",
    "OUTPUT_NAME",
    "NewsLexiconTransformResult",
    "transform",
]
