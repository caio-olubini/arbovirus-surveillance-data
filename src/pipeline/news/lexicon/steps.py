"""Lexicon + rules over the frozen text corpus → weekly features (braço 01).

Everything here is dictionary and regex work: no model, no GPU, no annotation.
That is the point of this braço — it is the representation that can be closed
first, and the one with direct precedent in dengue (see notes/01).

The two approximations worth knowing about, both deliberate and both reported
rather than hidden:

* **Negation is a character window, not syntax.** A term is dropped when a
  negation cue appears in the preceding `NEGATION_WINDOW` characters. It does
  not understand scope, so "não apenas um surto" loses a real "surto". The
  annotation study in notes/01 is what will quantify this.
* **Geo scoping is state-level and mention-based.** An article counts for a UF
  when it names that UF. It does not resolve municipalities to their state, so
  an article that says only "Araçatuba" contributes to BR and not to SP. That
  biases per-UF volume downward, unevenly across UFs, and is a declared
  limitation — see the pipeline README.
"""

from __future__ import annotations

import logging
import re
from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from ..common import strip_accents
from .spec import (
    EW,
    LOCATION,
    LOCATIVE_CUES,
    LOCATIVE_LOOKBACK,
    MAX_PLAUSIBLE_COUNT,
    NATIONAL_LOCATION,
    NEGATION_WINDOW,
    NEWS_ARTICLES_WITH_CASES,
    NEWS_CASES,
    NEWS_DEATHS,
    NEWS_SEVERITY,
    NEWS_VOLUME,
    OUTPUT_COLUMNS,
    PLURAL_CAO_REPLACEMENT,
    PLURAL_CAO_SUFFIX,
    PLURAL_ES_ENDINGS,
    PLURAL_INVARIANT_ENDINGS,
    QUALIFIER_LOOKAHEAD,
    QUALIFIER_PATTERN,
    SENTENCE_END,
)

log = logging.getLogger("pipeline.news.lexicon")


# ---------------------------------------------------------------------------
# Lexicon loading
# ---------------------------------------------------------------------------

def _plural(term: str) -> str:
    """Regular Portuguese plural of a single normalized word.

    The `-cao` rule has to come first: the generic `+s` would turn
    `hospitalizacao` into `hospitalizacaos`, which appears nowhere.
    """
    if term.endswith(PLURAL_CAO_SUFFIX):
        return term[: -len(PLURAL_CAO_SUFFIX)] + PLURAL_CAO_REPLACEMENT
    if term.endswith(PLURAL_ES_ENDINGS):
        return term + "es"
    if term.endswith(PLURAL_INVARIANT_ENDINGS):
        return term
    return term + "s"


def _compile(terms: Iterable[str], *, auto_plural: bool) -> tuple[re.Pattern[str], ...]:
    """Word-boundary patterns for each term, pluralized when asked.

    Word boundaries, never substrings: `\\bdor\\b` must not fire on `dormir`.
    Multi-word phrases are matched as written — pluralizing the last word of
    `aumento de casos` would produce nonsense.
    """
    patterns: list[re.Pattern[str]] = []
    seen: set[str] = set()
    for raw in terms:
        term = strip_accents(str(raw)).strip()
        if not term:
            continue
        forms = [term]
        if auto_plural and " " not in term:
            plural = _plural(term)
            if plural != term:
                forms.append(plural)
        for form in forms:
            if form in seen:
                continue
            seen.add(form)
            patterns.append(re.compile(rf"\b{re.escape(form)}\b"))
    return tuple(patterns)


@dataclass(frozen=True)
class SeverityTier:
    name: str
    weight: int
    patterns: tuple[re.Pattern[str], ...]


@dataclass(frozen=True)
class Lexicon:
    """The frozen lexicon, compiled once and reused for every article."""

    severity: tuple[SeverityTier, ...]
    disease: tuple[re.Pattern[str], ...]
    clinical: tuple[re.Pattern[str], ...]
    vector: tuple[re.Pattern[str], ...]
    negations: re.Pattern[str]
    count_pattern: re.Pattern[str]
    unit_kinds: dict[str, str]
    # Disease-family terms plus the generic words (`doença`, `arbovirose`) that
    # may legitimately qualify a count we want. Anything else after "de"/"por"
    # means the number belongs to another disease.
    dengue_scope: tuple[re.Pattern[str], ...]
    qualifier_pattern: re.Pattern[str]
    require_disease_term: bool
    version: int

    @property
    def severity_score_max(self) -> int:
        return sum(tier.weight for tier in self.severity)


def _alternation(forms: Iterable[str]) -> str:
    """Regex alternation, longest first so `casos` is not eaten by `caso`."""
    unique = sorted({strip_accents(str(f)).strip() for f in forms if str(f).strip()},
                    key=len, reverse=True)
    return "|".join(re.escape(form) for form in unique)


def load_lexicon(path: Path) -> Lexicon:
    """Read and compile the versioned PT-BR lexicon."""
    if not path.exists():
        raise FileNotFoundError(
            f"Lexicon not found: {path}. The braço 01 lexicon is versioned under "
            f"data/news/reference/."
        )
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))

    tiers: list[SeverityTier] = []
    for name, block in data.get("severity", {}).items():
        tiers.append(
            SeverityTier(
                name=name,
                weight=int(block["weight"]),
                patterns=_compile(block.get("terms") or [], auto_plural=True),
            )
        )
    if not tiers:
        raise ValueError(f"{path} defines no severity tiers; news_severity would be 0.")

    unit_kinds: dict[str, str] = {}
    for kind, forms in (data.get("count_units") or {}).items():
        for form in forms:
            unit_kinds[strip_accents(str(form)).strip()] = kind

    scale_forms = [
        form for forms in (data.get("count_scales") or {}).values() for form in forms
    ]
    scales = _alternation(scale_forms)
    units = _alternation(unit_kinds)
    if not units:
        raise ValueError(f"{path} defines no count_units; news_cases would be null.")

    count_pattern = re.compile(
        rf"(?P<num>\d{{1,3}}(?:\.\d{{3}})+|\d+(?:,\d+)?)\s*"
        rf"(?:(?P<scale>{scales})\s+)?"
        rf"(?P<unit>{units})\b"
    )

    # One alternation rather than a tuple: the negation check is a single
    # `search` per match, on the hot path for every severity hit.
    negation_forms = _alternation(data.get("negations") or [])
    negations = (
        re.compile(rf"\b(?:{negation_forms})\b")
        if negation_forms
        else re.compile(r"(?!x)x")  # matches nothing
    )

    disease = _compile(data.get("disease") or [], auto_plural=False)
    generic = _compile(data.get("generic_disease_words") or [], auto_plural=True)

    return Lexicon(
        severity=tuple(tiers),
        disease=disease,
        clinical=_compile(data.get("clinical") or [], auto_plural=True),
        vector=_compile(data.get("vector") or [], auto_plural=True),
        negations=negations,
        count_pattern=count_pattern,
        unit_kinds=unit_kinds,
        dengue_scope=disease + generic,
        qualifier_pattern=re.compile(QUALIFIER_PATTERN),
        require_disease_term=bool(data.get("require_disease_term", True)),
        version=int(data.get("version", 0)),
    )


# ---------------------------------------------------------------------------
# Location matching
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class UfMatcher:
    """Finds federative-unit mentions in one article.

    Full state names are matched on the *original* text, case-sensitively, and
    that is load-bearing: accent-folding makes `Pará` and the preposition `para`
    the same string, which would scope nearly every article to Pará.

    Two-letter codes are matched on the original text too, and only when a
    locative cue precedes them (or they sit in parentheses). Bare codes are not
    usable: `SE` is the reflexive pronoun, and `PA` collides with `p.a.`.
    """

    name_patterns: tuple[tuple[re.Pattern[str], str], ...]
    abbrev_pattern: re.Pattern[str]
    abbrevs: frozenset[str]

    def find(self, original: str) -> set[str]:
        found = {abbrev for pattern, abbrev in self.name_patterns if pattern.search(original)}
        for match in self.abbrev_pattern.finditer(original):
            code = match.group("code")
            if code in self.abbrevs:
                found.add(code)
        return found


def load_uf_matcher(fu_path: Path) -> UfMatcher:
    """Build the state matcher from the shared federative-unit reference table."""
    table = pl.read_csv(fu_path)
    names: list[tuple[re.Pattern[str], str]] = []
    abbrevs: set[str] = set()
    for name, abbrev in table.select("NAME", "ABBREVIATION").iter_rows():
        abbrevs.add(abbrev)
        names.append((re.compile(rf"\b{re.escape(name)}\b"), abbrev))

    cues = "|".join(re.escape(cue) for cue in LOCATIVE_CUES)
    # Up to LOCATIVE_LOOKBACK - 1 words may sit between the cue and the code:
    # "no estado de SP", "no interior do RJ".
    filler = rf"(?:\w+\s+){{0,{LOCATIVE_LOOKBACK - 1}}}"
    abbrev_pattern = re.compile(
        rf"(?:\b(?:{cues})\s+{filler}|[(/])(?P<code>[A-Z]{{2}})\b"
    )
    return UfMatcher(
        name_patterns=tuple(names),
        abbrev_pattern=abbrev_pattern,
        abbrevs=frozenset(abbrevs),
    )


# ---------------------------------------------------------------------------
# Per-article analysis
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ArticleSignals:
    """What one article contributes, before it is spread across locations."""

    severity: int
    cases: int | None
    deaths: int | None
    has_disease_term: bool
    locations: frozenset[str]


def _negated(normalized: str, start: int, lexicon: Lexicon) -> bool:
    """Is the match at `start` inside a negation window?"""
    window = normalized[max(0, start - NEGATION_WINDOW) : start]
    return lexicon.negations.search(window) is not None


def severity_score(normalized: str, lexicon: Lexicon) -> int:
    """Weighted count of non-negated severity hits."""
    score = 0
    for tier in lexicon.severity:
        for pattern in tier.patterns:
            hits = sum(
                1 for match in pattern.finditer(normalized)
                if not _negated(normalized, match.start(), lexicon)
            )
            score += tier.weight * hits
    return score


def mentions_disease(normalized: str, lexicon: Lexicon) -> bool:
    """Does a *normalized* article name a dengue-family disease anywhere?

    Public because braço 02 shares it. The article set is common ground under
    protocol 00 — the gate drops errata pages, photo-agenda stubs and digests
    whose dengue link is incidental — so both braços must drop the same articles,
    or the comparison measures the corpus instead of the representation.

    Takes text that has already been through `strip_accents`, like every other
    matcher in this module; normalizing here would re-fold the same article once
    per pattern.
    """
    return any(pattern.search(normalized) for pattern in lexicon.disease)


def _parse_number(raw: str, scale: str | None) -> int | None:
    """Portuguese numeral: `.` groups thousands, `,` is the decimal mark.

    The `mil` multiplier is skipped when the number is already written in
    dotted-thousands form. "36.791 mil casos" is how the corpus writes 36,791 —
    the dots *are* the thousands separator and the trailing `mil` is a redundant
    reading of them. Multiplying gives 36.8 million cases of dengue in one state,
    which is the kind of plausible-looking absurdity this stage must not emit.
    "500 mil casos" carries no dots and does multiply.
    """
    grouped = "." in raw
    text = raw.replace(".", "").replace(",", ".")
    try:
        value = float(text)
    except ValueError:  # pragma: no cover - the regex only emits numeric text
        return None
    if scale in {"milhao", "milhoes"}:
        value *= 1_000_000
    elif scale is not None and not grouped:
        value *= 1_000
    if value <= 0 or value > MAX_PLAUSIBLE_COUNT:
        return None
    return int(round(value))


def _belongs_to_dengue(normalized: str, end: int, lexicon: Lexicon) -> bool:
    """False when the count is explicitly qualified by another disease.

    Only fires when the count is directly followed by "de"/"por" and a word: that
    word must be a dengue-family or generic disease term. An unqualified count
    passes, which keeps the rule narrow — it is here to reject "11.881.430 casos
    de DRSAI", not to police every number in the corpus.
    """
    tail = normalized[end : end + QUALIFIER_LOOKAHEAD]
    qualifier = lexicon.qualifier_pattern.match(tail)
    if qualifier is None:
        return True
    word = qualifier.group(1)
    return any(pattern.fullmatch(word) for pattern in lexicon.dengue_scope)


def _sentence_of(normalized: str, position: int, starts: list[int]) -> int:
    """Index of the sentence containing `position`, given precomputed starts."""
    return max(0, bisect_right(starts, position) - 1)


def count_mentions(normalized: str, lexicon: Lexicon) -> tuple[int | None, int | None]:
    """Largest case count and largest death count stated in the text.

    Three gates, in order, because raw number extraction from general news prose
    is dominated by numbers that are not about dengue at all — the corpus alone
    contains "700 mil mortes" (covid), "655 mil mortes" (malária), "38.892
    mortes" (violência) and "24 mil mortes prematuras" (poluição), each inside an
    article that is genuinely about dengue:

    1. not negated,
    2. not qualified by another disease ("11.881.430 casos de DRSAI"),
    3. stated in a sentence that names a dengue-family disease.

    Gate 3 is the load-bearing one and it costs recall: a sentence like "No
    estado de São Paulo, foram 36.791 casos" is dropped when it never says
    "dengue". That is the deliberate direction — a count that is an order of
    magnitude wrong is worse for the model than a count that is missing, and the
    missing ones are recoverable by braço 04's structured extraction.

    The maximum, not the sum: a week's coverage repeats the same cumulative
    figure across several articles, and summing would scale with how many times
    the press repeated one number rather than with the epidemic.

    Note what this number is *not*: most articles report a cumulative-to-date
    figure ("ao longo de 2024, 6,6 milhões de casos"), so the weekly maximum is
    the scale of the largest figure the press stated that week, not the week's
    incidence. See the pipeline README.
    """
    starts = [0]
    starts.extend(match.end() for match in SENTENCE_END.finditer(normalized))
    dengue_sentence = [
        any(pattern.search(normalized[start:end]) for pattern in lexicon.disease)
        for start, end in zip(starts, starts[1:] + [len(normalized)])
    ]

    cases: int | None = None
    deaths: int | None = None
    for match in lexicon.count_pattern.finditer(normalized):
        if _negated(normalized, match.start(), lexicon):
            continue
        if not _belongs_to_dengue(normalized, match.end(), lexicon):
            continue
        if not dengue_sentence[_sentence_of(normalized, match.start(), starts)]:
            continue
        value = _parse_number(match.group("num"), match.group("scale"))
        if value is None:
            continue
        kind = lexicon.unit_kinds.get(match.group("unit"))
        if kind == "obitos":
            deaths = value if deaths is None else max(deaths, value)
        else:
            cases = value if cases is None else max(cases, value)
    return cases, deaths


def analyse(text: str, title: str, lexicon: Lexicon, matcher: UfMatcher) -> ArticleSignals:
    """Run every rule over one article's title + body."""
    original = f"{title}\n{text}"
    normalized = strip_accents(original)
    cases, deaths = count_mentions(normalized, lexicon)
    return ArticleSignals(
        severity=severity_score(normalized, lexicon),
        cases=cases,
        deaths=deaths,
        has_disease_term=mentions_disease(normalized, lexicon),
        locations=frozenset(matcher.find(original)),
    )


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def build(
    corpus: pl.DataFrame,
    lexicon: Lexicon,
    matcher: UfMatcher,
    require_disease_term: bool | None = None,
    portuguese_only: bool = True,
) -> pl.DataFrame:
    """Aggregate the corpus into (ew, location) features.

    Only observed pairs are emitted. A week with no article is *absent*, not
    zero — the consumer left-joins onto the target calendar. Emitting the dense
    grid would assert 0 for every UF that national news simply never names,
    which is a different claim from "no coverage this week".

    `portuguese_only` drops the articles `guess_language` flags as non-Portuguese
    (3.7% of the corpus, mostly Spanish, concentrated in 2016). Keeping them
    would add articles whose text no PT-BR term can match, which inflates
    `news_volume` while leaving `news_severity` and `news_cases` at zero for
    them — a row that looks like coverage and measures nothing.
    """
    require = (
        lexicon.require_disease_term
        if require_disease_term is None
        else require_disease_term
    )
    if portuguese_only and "lang_guess" in corpus.columns:
        corpus = corpus.filter(pl.col("lang_guess") == "pt")

    records: list[dict[str, Any]] = []
    skipped = 0
    for ew, title, text in corpus.select(EW, "title", "text").iter_rows():
        if ew is None:
            skipped += 1
            continue
        signals = analyse(text or "", title or "", lexicon, matcher)
        if require and not signals.has_disease_term:
            skipped += 1
            continue
        for location in signals.locations | {NATIONAL_LOCATION}:
            records.append(
                {
                    EW: ew,
                    LOCATION: location,
                    NEWS_SEVERITY: signals.severity,
                    NEWS_CASES: signals.cases,
                    NEWS_DEATHS: signals.deaths,
                    NEWS_ARTICLES_WITH_CASES: 0 if signals.cases is None else 1,
                }
            )

    if skipped:
        log.info("lexicon: %d articles skipped (no EW or no disease term)", skipped)
    if not records:
        return pl.DataFrame(schema=AGG_SCHEMA)

    frame = pl.DataFrame(records, schema=RECORD_SCHEMA)
    return (
        frame.group_by(EW, LOCATION)
        .agg(
            pl.len().alias(NEWS_VOLUME),
            pl.col(NEWS_SEVERITY).sum().alias(NEWS_SEVERITY),
            pl.col(NEWS_CASES).max().alias(NEWS_CASES),
            pl.col(NEWS_DEATHS).max().alias(NEWS_DEATHS),
            pl.col(NEWS_ARTICLES_WITH_CASES).sum().alias(NEWS_ARTICLES_WITH_CASES),
        )
        .select(OUTPUT_COLUMNS)
        .sort(EW, LOCATION)
    )


RECORD_SCHEMA: dict[str, pl.DataType] = {
    EW: pl.Date,
    LOCATION: pl.String,
    NEWS_SEVERITY: pl.Int64,
    NEWS_CASES: pl.Int64,
    NEWS_DEATHS: pl.Int64,
    NEWS_ARTICLES_WITH_CASES: pl.Int64,
}

AGG_SCHEMA: dict[str, pl.DataType] = {
    EW: pl.Date,
    LOCATION: pl.String,
    NEWS_VOLUME: pl.Int64,
    NEWS_SEVERITY: pl.Int64,
    NEWS_CASES: pl.Int64,
    NEWS_DEATHS: pl.Int64,
    NEWS_ARTICLES_WITH_CASES: pl.Int64,
}


def week_span(corpus: pl.DataFrame) -> tuple[date, date] | None:
    """First and last epi week in the corpus — reported for orientation."""
    bounds = corpus.select(
        pl.col(EW).min().alias("first"), pl.col(EW).max().alias("last")
    ).row(0)
    if bounds[0] is None:
        return None
    return bounds


__all__ = [
    "ArticleSignals",
    "Lexicon",
    "SeverityTier",
    "UfMatcher",
    "analyse",
    "build",
    "count_mentions",
    "load_lexicon",
    "load_uf_matcher",
    "mentions_disease",
    "severity_score",
    "week_span",
]
