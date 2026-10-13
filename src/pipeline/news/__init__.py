"""News pipelines — three competing representations of the same frozen corpus.

The braços are *parallel*, not layered: each reads the frozen text corpus and
publishes its own feature table at the same grain (epidemiological week ×
location). The article then compares which representation predicts dengue
better. That comparison only means something because the common ground is
fixed — see notes/00-protocolo-comparacao.md.

    common.py       shared: HTML → text, accent folding, language guess
    corpus.py       shared: the article-set gates and geo scoping every braço reuses
    text/           stage 0 — the frozen corpus every braço reads
    lexicon/        braço 01 — PT-BR lexicon + rules             (implemented)
    embeddings/     braço 02 — dense embeddings + EW pooling     (implemented)
    topics/         braço 03 — temporal topic modeling (DMR)     (implemented)

`corpus.py` exists because the braços are parallel: braço 03 needs the same
article gate and geo scoping braço 02 uses, but importing them from braço 02 would
make one representation depend on another. They sit above both instead.

Braços 04 and 05 (LLM extraction, LLM forecaster) are *not* here: they are
corredores por fora that consume the same corpus but produce different kinds of
output, and their notes are explicit that they are out of scope until the
baseline and at least one representation exist.
"""

from __future__ import annotations

from . import embeddings, lexicon, text, topics
from .common import Extracted, extract, guess_language, strip_accents

__all__ = [
    "Extracted",
    "embeddings",
    "extract",
    "guess_language",
    "lexicon",
    "strip_accents",
    "text",
    "topics",
]
