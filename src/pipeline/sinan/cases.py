"""The case series a downstream braço is allowed to predict.

Protocol 00 fixes the target as common ground between braços: only the
*representation* of the text may vary. The target therefore has to be one
function that every braço calls, not three copies that happen to agree today —
and they did not agree. Two notebooks summed every notification; a third kept
only the confirmed ones. The three series differ by up to 42% of their total,
which is the size of a finding.

The definition is the published implementation's.
`r/scripts/4_prepare_final_disease_table.R` filters
`final_classification != 5 | is.na(final_classification)`: every notification,
minus the ones ruled out after investigation. That is the dengue **suspected**
case series — the event the surveillance system counts — and it is the one that
reproduces the data paper's annual totals, exactly, for every year from 2014 to
2023.

It is deliberately *not* the confirmed series (`final_classification` 10, 11 or
12). Confirmed cases are the subset that finished investigation, so that filter
removes 2.8 million notifications over the period — 14.6% — and removes them
unevenly: 31% of the 2017 series, 8% of 2024's. A model trained on it would be
predicting a curve the surveillance system does not publish.
"""

from __future__ import annotations

import polars as pl

from .spec import CASE_COUNT, EW_SYMPTOM_ONSET, FINAL_CLASSIFICATION, STATE_ABBREV

# SINAN's "descartado": the notification was investigated and ruled out. Every
# other code is a suspected case, including the null — a case awaiting
# adjudication is the most recent one, not an absent one.
DISCARDED = 5

WEEK = EW_SYMPTOM_ONSET


def suspected(frame: pl.DataFrame) -> pl.DataFrame:
    """Drop the notifications ruled out after investigation.

    The `is_null()` is not defensive padding. polars' `!=` returns null for a
    null operand and `filter` drops null, so `!= DISCARDED` on its own would
    silently discard the 54,875 notifications that have no final classification
    yet — the most recent weeks, which are exactly the ones nowcasting work
    targets. The R implementation spells the condition out as `is.na(...)`; the
    two have to agree, so this one spells it out too.
    """
    return frame.filter(
        (pl.col(FINAL_CLASSIFICATION) != DISCARDED)
        | pl.col(FINAL_CLASSIFICATION).is_null()
    )


def weekly_cases(frame: pl.DataFrame, by_state: bool = False) -> pl.DataFrame:
    """Suspected cases summed to the epidemiological week of symptom onset.

    Symptom onset, not notification: the notification week carries the data-entry
    lag, and two series keyed on different dates are not comparable — protocol 00
    fixes onset for every braço.

    `by_state` keeps the federative unit for the per-UF reading; without it the
    result is national. The output is sorted on its key so callers do not have to
    be, and carries the same `case_count` name the source table uses for the
    per-group count.
    """
    keys = [WEEK, STATE_ABBREV] if by_state else [WEEK]
    return (
        suspected(frame)
        .group_by(keys)
        .agg(pl.col(CASE_COUNT).sum().alias(CASE_COUNT))
        .sort(keys)
    )
