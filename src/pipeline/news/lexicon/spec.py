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

# --- literature grounding ---------------------------------------------------
#
# The lineage this braço descends from, and the numbers behind each design
# choice below. The full fichas — abstract, measured numbers, PDF — are in
# `articles/features-texto/` (`relatorio.md`, `ranking.md`); the citation lives
# here, next to the constants it justifies, so it cannot drift from the code.
#
# Author-year is the form the review chapter uses. One year differs from the
# local PDF name: the JAMIA HealthMap paper is cited by its 2008 issue, though
# the saved PDF is dated 2007 (online-first).
REFERENCES = (
    "Freifeld et al. 2008, JAMIA 15(2):150 — dictionary cascade headline→body, "
    "gazetteer of ~2,300 places and ~1,100 diseases, and the container rule that "
    "drops a generic place when a specific one is named. "
    "doi:10.1197/jamia.M2544",
    "Brownstein et al. 2008, PLoS Med 5(7):e151 — the same architecture; "
    "Portuguese listed as 'under development' in 2008. "
    "doi:10.1371/journal.pmed.0050151",
    "Collier et al. 2008, Bioinformatics 24(24):2940 — disease/location slots "
    "read from a formal ontology rather than a flat term list. "
    "doi:10.1093/bioinformatics/btn534",
    "Valentin et al. 2020, Comput Electron Agric — curated vocabulary + GeoNames "
    "+ HeidelTime dates + regex for case counts. "
    "doi:10.1016/j.compag.2019.105163",
    "Arsevska et al. 2018, PLoS ONE 13(8):e0199960 — F 85% on case counts "
    "against 95% on disease/host: the count is the weak slot. "
    "doi:10.1371/journal.pone.0199960",
    "Consoli et al. 2025, Sci Data — F1 0.658 on case counts against 0.851 for "
    "disease and 0.962 for country; deaths left unevaluated. "
    "doi:10.1038/s41597-025-05276-2",
    "Ng et al. 2020, CCDR 46(6) — no production surveillance system extracted "
    "case counts at the time of writing. doi:10.14745/ccdr.v46i06a06",
    "Carlson et al. 2023, PLOS Glob Public Health — the same disease under five "
    "names, cities spelled inconsistently, duplicate and impossible dates. "
    "doi:10.1371/journal.pgph.0001083",
    "Conway et al. 2010, J Med Internet Res 12(2):e23 — two annotators agreed on "
    "the *number* of events in only 67% of documents. doi:10.2196/jmir.1323",
    "Chanlekha et al. 2010, BMC Med Inform Decis Mak 10:1 — exact-location kappa "
    "0.806/0.749, rising to 0.997 under approximate agreement. "
    "doi:10.1186/1472-6947-10-1",
    "Hu et al. 2023, ACM Comput Surv — administrative units are the easiest "
    "toponym class (13 of 27 methods above 60% recall); no Portuguese model was "
    "evaluated. doi:10.1145/3625819",
)

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
# A plausibility ceiling is the cheap version of what the corpus literature
# reports as a document-level problem: impossible values reach the extractor
# (Carlson et al. 2023 — see REFERENCES).
MAX_PLAUSIBLE_COUNT = 50_000_000

# A count followed by "de"/"por" plus a disease word is only ours when that word
# is a dengue-family term or a generic one. See `generic_disease_words` in the
# lexicon for why: dengue coverage cites other diseases, and their numbers are
# an order of magnitude away from dengue's. The rule exists because a bare
# numeral carries no disease of its own — the count is only meaningful bound to
# the disease in its sentence (Ng et al. 2020 — see REFERENCES).
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
