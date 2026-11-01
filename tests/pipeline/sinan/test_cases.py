"""The target series: which notifications count, and on which week.

The definition is the one place where getting it wrong is silent. Every wrong
variant here still returns a plausible series — a smaller one, or a larger one —
so nothing downstream fails; the numbers just stop being the published ones. The
tests below pin the three ways it can go wrong: dropping the unclassified rows
with the discarded ones, keeping the discarded rows, and keying on the
notification week instead of the onset week.
"""

from __future__ import annotations

from datetime import date

import polars as pl

from src.pipeline.sinan.cases import DISCARDED, suspected, weekly_cases
from src.pipeline.sinan.spec import (
    CASE_COUNT,
    EW_SYMPTOM_ONSET,
    FINAL_CLASSIFICATION,
    STATE_ABBREV,
)

MONDAY = date(2024, 6, 10)   # onset
SUNDAY = date(2024, 6, 9)    # the epi week that starts the Sunday before


def frame(rows: list[tuple[date, int | None, str, int]]) -> pl.DataFrame:
    """One row per (week, classification, state), as the published table holds them."""
    return pl.DataFrame(
        {
            EW_SYMPTOM_ONSET: [r[0] for r in rows],
            FINAL_CLASSIFICATION: [r[1] for r in rows],
            STATE_ABBREV: [r[2] for r in rows],
            CASE_COUNT: [r[3] for r in rows],
        },
        schema_overrides={FINAL_CLASSIFICATION: pl.Int8},
    )


# --------------------------------------------------------------------------
# suspected
# --------------------------------------------------------------------------

def test_discarded_is_the_only_code_dropped() -> None:
    """Codes 1 and 8 are the pre-2014 scheme and survive alongside 10-12.

    Treating only 10-12 as real would drop the older coding entirely, which is
    the mistake this definition exists to undo.
    """
    kept = suspected(frame([
        (MONDAY, 1, "SP", 5), (MONDAY, 2, "SP", 5), (MONDAY, 8, "SP", 5),
        (MONDAY, 10, "SP", 5), (MONDAY, 11, "SP", 5), (MONDAY, 12, "SP", 5),
        (MONDAY, DISCARDED, "SP", 99),
    ]))
    assert kept[CASE_COUNT].sum() == 30


def test_unclassified_rows_survive_the_filter() -> None:
    """The polars trap: `!= 5` alone returns null for a null code, and filter drops it.

    These are the most recent weeks — the ones awaiting adjudication — so losing
    them silently would bias the series against exactly the period nowcasting
    targets.
    """
    kept = suspected(frame([(MONDAY, None, "SP", 7), (MONDAY, DISCARDED, "SP", 99)]))
    assert kept.height == 1
    assert kept[CASE_COUNT].sum() == 7


def test_nothing_else_is_dropped() -> None:
    """No state filter, no week filter, no deduplication hides in here."""
    source = frame([(MONDAY, 10, "SP", 3), (MONDAY, 10, "RJ", 4), (MONDAY, None, "RJ", 5)])
    assert suspected(source).height == source.height


# --------------------------------------------------------------------------
# weekly_cases
# --------------------------------------------------------------------------

def test_weekly_cases_sums_within_the_week() -> None:
    series = weekly_cases(frame([
        (SUNDAY, 10, "SP", 3), (SUNDAY, 12, "SP", 4), (SUNDAY, DISCARDED, "SP", 90),
    ]))
    assert series.to_dicts() == [{EW_SYMPTOM_ONSET: SUNDAY, CASE_COUNT: 7}]


def test_weekly_cases_is_national_unless_asked_for_states() -> None:
    rows = [(SUNDAY, 10, "SP", 3), (SUNDAY, 10, "RJ", 4)]
    assert weekly_cases(frame(rows)).to_dicts() == [
        {EW_SYMPTOM_ONSET: SUNDAY, CASE_COUNT: 7}
    ]
    assert weekly_cases(frame(rows), by_state=True).sort(STATE_ABBREV).to_dicts() == [
        {EW_SYMPTOM_ONSET: SUNDAY, STATE_ABBREV: "RJ", CASE_COUNT: 4},
        {EW_SYMPTOM_ONSET: SUNDAY, STATE_ABBREV: "SP", CASE_COUNT: 3},
    ]


def test_weekly_cases_keys_on_onset_not_notification() -> None:
    """The onset week is what the caller passes; nothing re-derives a date here.

    This pins the contract rather than the arithmetic: a frame whose only date
    column is `ew_symptom_onset` has to be enough, so no caller can quietly
    substitute the notification week.
    """
    series = weekly_cases(frame([(SUNDAY, 10, "SP", 1)]))
    assert series.columns == [EW_SYMPTOM_ONSET, CASE_COUNT]
    assert series[EW_SYMPTOM_ONSET][0] == SUNDAY
