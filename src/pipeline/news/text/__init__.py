"""News-text stage — the frozen corpus every representation braço reads.

`arboili transform news-text` turns the saved EBC HTML under
`data/news/<query>/articles/` into one row per article, keyed on the
Sunday-anchored epidemiological week. No braço re-parses HTML.
"""

from __future__ import annotations

from .spec import EW, OUTPUT_COLUMNS, OUTPUT_NAME
from .transform import NewsTextTransformResult, transform

__all__ = [
    "EW",
    "OUTPUT_COLUMNS",
    "OUTPUT_NAME",
    "NewsTextTransformResult",
    "transform",
]
