"""Schema of the lexicon feature table (braço 01) and its matching constants.

Grain: one row per (epidemiological week, location), where location is `BR` or a
federative unit. That is the grain every news braço publishes, so the three can
be swapped in the same model without reshaping.

Features are the three the research note fixes — `news_volume`, `news_severity`,
`news_cases` — plus `news_deaths`, whose rule (`"X óbitos"`) the note's own regex
list names, and `news_articles_with_cases`, which reports how thin the evidence
behind `news_cases` is. That last one exists to answer the note's open question
of whether `news_cases` is worth keeping at all.
"""

from __future__ import annotations

import re

# --- column names -----------------------------------------------------------

EW = "ew"
LOCATION = "location"
NEWS_VOLUME = "news_volume"
NEWS_SEVERITY = "news_severity"
NEWS_CASES = "news_cases"
NEWS_DEATHS = "news_deaths"
NEWS_ARTICLES_WITH_CASES = "news_articles_with_cases"

OUTPUT_COLUMNS = (
    EW,
    LOCATION,
    NEWS_VOLUME,
    NEWS_SEVERITY,
    NEWS_CASES,
    NEWS_DEATHS,
    NEWS_ARTICLES_WITH_CASES,
)
GROUP_KEYS = (EW, LOCATION)

OUTPUT_NAME = "EBC_dengue_lexicon_EW"

# National rows, same code the Google Trends stage uses.
NATIONAL_LOCATION = "BR"

# --- matching constants -----------------------------------------------------

# Characters scanned backwards from a match for a negation cue. Wide enough for
# "não há registro de surto", narrow enough not to reach across a sentence.
NEGATION_WINDOW = 40

# Tokens scanned backwards for a locative cue before a two-letter UF code. Bare
# codes are too dangerous to accept on their own: "SE" is the reflexive pronoun
# and "PA" collides with "p.a.". Requiring uppercase *and* a locator is what
# keeps Sergipe out of every other article.
LOCATIVE_LOOKBACK = 3

# Prepositions and possessives that mark a following token as a place.
LOCATIVE_CUES = (
    "em", "no", "na", "nos", "nas", "de", "do", "da", "dos", "das",
    "para", "pelo", "pela", "ate", "desde", "entre",
    "estado", "governo", "interior", "cidade", "capital", "municipio",
)

# Values per case/obit count. Beyond this the number is a year, a population or
# a phone number, not a case count. Brazil's worst dengue year on record
# (2024) reported ~6.6 million cases and ~6,100 deaths, so this is loose enough
# to admit every real figure and tight enough to reject a national population.
MAX_PLAUSIBLE_COUNT = 50_000_000

# A count followed by "de"/"por" plus a disease word is only ours when that word
# is a dengue-family term or a generic one. See `generic_disease_words` in the
# lexicon for why: dengue coverage cites other diseases, and their numbers are
# an order of magnitude away from dengue's.
QUALIFIER_LOOKAHEAD = 40
# Up to two intervening words so "casos prováveis de dengue" and "casos
# confirmados de dengue" are seen as dengue-qualified, while "casos e 10 mortes
# de dengue" is not (the qualifier does not attach to the count).
QUALIFIER_PATTERN = r"^\s+(?:\w+\s+){0,2}(?:de|por)\s+(\w+)"

# Sentence boundary for scoping a count to its context. The corpus has been
# through `clean_text`, so paragraphs are `\n\n` and sentences end in `.`/`?`/`!`.
SENTENCE_END = re.compile(r"[.!?]\s|\n")

# Regular plural endings, applied to single-word lexicon terms.
# `-cao` → `-coes` first, because the naive `+s` rule would give `-caos`.
PLURAL_CAO_SUFFIX = "cao"
PLURAL_CAO_REPLACEMENT = "coes"
PLURAL_ES_ENDINGS = ("r", "z")
PLURAL_INVARIANT_ENDINGS = ("s", "x")
