"""News pipelines — three competing representations of the same frozen corpus.

The braços are *parallel*, not layered: each reads the frozen text corpus and
publishes its own feature table at the same grain (epidemiological week ×
location). The article then compares which representation predicts dengue
better. That comparison only means something because the common ground is
fixed — see notes/00-protocolo-comparacao.md.

    common.py       shared: HTML → text, accent folding, language guess
    text/           stage 0 — the frozen corpus every braço reads
    lexicon/        braço 01 — PT-BR lexicon + rules          (implemented)
    embeddings/     braço 02 — dense embeddings + EW pooling  (stub)
    topics/         braço 03 — temporal topic modeling        (stub)

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
