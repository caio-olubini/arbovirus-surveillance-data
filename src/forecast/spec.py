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

# --- the quantile grid ------------------------------------------------------

# The levels every distributional metric is computed on: seven of them, which is
# three central intervals — 50%, 80%, 95%. The set comes from the COVID-19
# Forecast Hub, which asks for this seven-level subset on the incident-cases
# target while asking for twenty-three on deaths — so it is the field's own
# answer for a series of this kind, not a simplification of ours. The reason to
# prefer it here is the sample: the most extreme level is 0.025, the second of
# eighty ordered observations, and the error samples are in the hundreds, so a
# twenty-three-level grid would put weight on tails the data cannot support.
QUANTILE_LEVELS = (0.025, 0.1, 0.25, 0.5, 0.75, 0.9, 0.975)

# The central intervals reported beside WIS, one row each: the pair of levels
# that bound the interval and the coverage it claims. Written out rather than
# derived, so that what gets reported is readable in one place, and then checked
# against the grid below: a table typed by hand can drift from the grid it
# describes, and the check refuses the drift. Arithmetic would find these three
# pairs as well — `1 - 0.025` is the double that `0.975` is — so the check is not
# there for today's numbers; it is there for the next set somebody types.
CENTRAL_INTERVALS = ((0.025, 0.975, 0.95), (0.1, 0.9, 0.8), (0.25, 0.75, 0.5))

# How many observed h-step errors a predictive distribution needs before it is
# scored. Two full seasons: enough for the widest level on the grid to rest on
# more than a handful of order statistics. The rule bites only at the start of
# the panel — with 104 weeks of training, persistence has 103 errors by its
# first origin and the seasonal naive has 52, so its distributions begin later.
# Inside the paper's scoring window the samples are far above this floor and the
# floor changes nothing; on the default panel to 2026 it trims the first weeks,
# and the run record carries both counts so the difference is visible.
MIN_ERROR_SAMPLE = 104


def _check_grid() -> None:
    """The intervals and the grid must not drift apart."""
    for lower, upper, coverage in CENTRAL_INTERVALS:
        for level in (lower, upper):
            if level not in QUANTILE_LEVELS:
                raise RuntimeError(
                    f"the interval {lower}–{upper} names a level that is not in "
                    f"QUANTILE_LEVELS: {level}"
                )
        # As duas metades do par, e não só a de baixo: um `upper` trocado passa
        # pela checagem de cobertura sempre que o par errado tiver a mesma
        # largura, e aí a faixa pontuada não é a faixa que a tabela nomeia.
        if abs((lower + upper) - 1.0) > 1e-9:
            raise RuntimeError(
                f"the interval {lower}–{upper} is not a central pair: its levels "
                f"must add to 1, and they add to {lower + upper}."
            )
        if abs(coverage - (1.0 - 2.0 * lower)) > 1e-9:
            raise RuntimeError(
                f"the interval {lower}–{upper} claims coverage {coverage}, but its "
                f"levels say {1.0 - 2.0 * lower}."
            )


_check_grid()

