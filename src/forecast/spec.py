"""Names and defaults shared by the forecast evaluation.

Everything a later stage might want to vary lives here as data, so that a reader
comparing two result tables can see which knob moved. The values below are the
ones protocol 00 fixed for the first pass — one week ahead, raw counts, Brazil —
and each of them is a flag on `python -m src.forecast`, because every one of them
changes the number.
"""

from __future__ import annotations

# --- column names -----------------------------------------------------------

EW = "ew"
CASES = "case_count"
BASELINE = "baseline"
HORIZON = "horizon"

# --- evaluation defaults ----------------------------------------------------

# One week ahead. Protocol 00 leaves the horizon open between 1 and 4 weeks;
# 1 is the shortest path to a first number and the one where the naive baseline
# is hardest to beat, so it is the honest place to start. A later run raises it.
DEFAULT_HORIZON = 1

# Two years of history before the first forecast. The seasonal baseline needs a
# full year to look back on, and one year is a single sample of a season: two
# means the first forecast is made with a year of context behind the one it
# copies. 104 weeks is also the point where the case series has been through at
# least one full inter-epidemic trough.
DEFAULT_MIN_TRAIN = 104

# 52 weeks, the conventional seasonal lag on weekly data. It is a convention and
# not an identity: a year is 52.18 weeks, so a lag of 52 walks backwards through
# the calendar by about a day each cycle. On a series with dengue's seasonality
# that is small enough to accept and large enough to state.
SEASONAL_LAG = 52

# The two baselines every later model has to beat, in the order they are
# reported. Deliberately dumb: if a text representation cannot clear these, the
# representation is not the finding, the baseline is.
BASELINES = ("persistence", "seasonal_naive")

# The first year whose case series is complete. SINAN's 2013 weeks exist only as
# the symptom-onset tail of notifications filed in 2014, so the series starts
# mid-2013 with gaps, and a gap breaks the seasonal lag silently — the 52nd
# point back stops being the same week of the previous year.
FIRST_COMPLETE_YEAR = 2014

# Where the comparison is honest. News is national and the target here is
# national, so there is no spatial mismatch to explain away; per-UF is the
# exploratory reading, and it waits until the national one works. Recorded here
# rather than only in prose so that a saved result carries the level it was
# computed at.
GEOGRAPHY = "BR"
