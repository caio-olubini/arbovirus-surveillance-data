# Forecast evaluation

The **ruler**. Everything the article claims is a difference between two numbers
produced here, so the harness is written before any model exists: protocol 00
puts the naive baselines first precisely because the number a text
representation has to beat is the one *without* any news in it, and that number
has to exist before a representation can be compared against it.

This package is the third sibling of `collection/` (which fetches) and
`pipeline/` (which transforms). It downloads nothing and reshapes nothing; it
consumes the case table those two build.

| Stage | Entry point | Status |
|---|---|---|
| Target panel | `load_target` | **complete** |
| Target panel per state | `load_target(by_state=True)` | **complete** |
| Rolling origin | `rolling_origin` | **complete** |
| Naive baselines | `python -m src.forecast` | **complete** |
| Point metrics | `mae`, `rmse`, `mape` | **complete** |
| Quantile grid | `spec.QUANTILE_LEVELS` | **complete** |
| Distributional metrics | `wis`, `coverage`, `interval_width` | **complete** |
| Baseline distributions | `predictive_quantiles` | **complete** |
| Score window | `evaluate(score_from=…)` | **complete** |
| Run record | `setup_record`, `write_record` | **complete** |
| "No text" model (SINAN + GT + ERA5) | — | next |

```bash
uv run python -m src.forecast --out data/forecast
```

The command prints both tables and writes five files into `--out`:
`dengue_br_h1_predictions.parquet` (one row per scored week),
`..._metrics.parquet` (the summary), `..._quantiles.parquet` (one row per scored
week *per quantile level*), `..._intervals.parquet` (one row per central band)
and `..._run.json` (the setup). The record exists because the summary does not
defend itself: read it six months later and it cannot say whether the history
was 104 weeks or 200, and the difference between those two is not small. It
carries no date or time, so two runs of the same command write the same bytes —
a record that differs means a flag differed.

---

## 1. The first number

Brazil, all ages, suspected dengue, **1 week ahead**, first forecast after 104
weeks (two years) of history. 661 weeks from 2014-01-05 to 2026-08-30,
19,039,254 cases; 557 scored week-forecasts per baseline.

| Baseline | MAE (cases/week) | RMSE | MAPE |
|---|---|---|---|
| persistence (last observed week) | **4,047** | 9,716 | 13.3% |
| seasonal naive (same week last year) | 30,714 | 70,080 | 119.8% |

**Two windows, and the paper scores 157 weeks of them.** Google Trends is frozen
through 2024-12-29 and starts 2020-01-26, so the feature sets that use search only
exist where the four sources overlap: 2022-01-02 to 2024-12-29, **157 scored
weeks** — and 154 for the search-bearing sets, which need 104 weeks of search
history behind them. On that window the bar is a different number, and it is the
one the paper reports:

| Baseline | MAE (cases/week) | RMSE | MAPE |
|---|---|---|---|
| persistence (last observed week) | **9,022** | 17,257 | 16.3% |
| seasonal naive (same week last year) | 39,552 | 88,857 | 42.1% |

Persistence is 2.1× worse on the paper window than on the 2016–2024 window and
2.2× worse than on the default panel, because 2024 — the record year — is inside
it. Both long windows are declared robustness: quoting 4,047 as "the bar" makes
the problem look easier than it is.

There are three windows, and they are told apart by two flags, never by eye:

| Window | Command | Scored weeks | Persistence MAE | Seasonal naive MAE |
|---|---|---|---|---|
| Panel to 2026 (default) | — | 557 | 4,047 | 30,714 |
| Long, 2016–2024 | `--to-year 2024` | 470 | 4,358 | 23,618 |
| Paper, 2022-01-02 to 2024-12-29 | `--to-year 2024 --score-from 2022` | 157 | **9,022** | 39,552 |

The 557-week row is the default because it uses every week the case table holds;
protocol 00 calls the 470-week row "the long window" and quotes it beside the
paper window. `--score-from` alone does not give the paper window — the panel
still runs to 2026 and the scored weeks come out at 244. Both flags are needed,
and the record file captures them.

**Persistence is the real bar, not the seasonal naive.** Copying last year is
7.6× worse than copying last week on the default panel, 5.4× on the 2016–2024
window and 4.4× on the paper window, because dengue in Brazil moves by multiples
between years — 2024 averaged 125,779 cases/week against 32,001 in 2023. The
seasonal naive predicts the previous season's level into a year that has nothing
to do with it. Any later claim of the form "our model beats the naive baseline"
has to say *which* naive *and on which window*, and the honest answer is
persistence on the paper window.

The number is robust to the two things that could have manufactured it:

- Dropping the 2024 epidemic year: persistence 2,614, seasonal 24,105 — the gap
  survives, it is not one year's artefact.
- Dropping the final, incomplete week: 4,046 against 4,047 — no effect.

Where persistence actually hurts is the epidemic take-off, which is the whole
point of the exercise: its five worst weeks of the year are weeks 20, 21, 11, 16
and 19 — May, late May, March — the weeks the curve is climbing.

## 2. The shared contract

**Target.** `pipeline.sinan.cases.weekly_cases` — every notification minus the
ones ruled out after investigation, summed to the epi week of **symptom onset**.
One function, called here, so no braço can quietly predict a different curve.
The docstring in that module records what happened when three notebooks each had
their own definition: series differing by up to 42% of their total.

**Gap-free calendar.** `load_target` rebuilds the calendar as a continuous
weekly range and **raises** if any week between the first and the last is
missing. This is not defensiveness. The evaluation indexes the series by
position, so a missing week shifts every later position by one and the seasonal
lag silently reads 51 or 53 weeks back. A loud failure is the only safe
behaviour. 2013 in the SINAN file is exactly this case — present, with three
weeks missing — so the panel starts in 2014.

**Rolling origin.** `rolling_origin` yields each origin in turn; at origin *i* a
model may read the series up to position *i* and nothing after it. A single
holdout at the end would let a model be tuned on the period it is scored on, and
would hide instability — a method that works in 2021 and fails in 2024 would get
one averaged number and no warning. Origins whose horizon would run past the end
of the panel are dropped, not scored short.

## 3. The distribution behind the number

The naive baselines report one number per week. To score them on a distributional
metric they need a spread, and the spread is not invented: each baseline has made
its own h-step-ahead errors before, and the empirical distribution of those errors
is the uncertainty it has shown. Every quantile comes from that sample and from
nothing else.

**Only the past.** At origin *i* the sample holds the errors whose target week had
already happened by *i* — the error made at position *t* for step *s* is known at
that origin only when `t + s <= i`. An error the baseline could not have observed
is not in the sample that scores it.

**One history per step.** A forecast is wrong by more at step 4 than at step 1, so
each step carries its own error sample; a single spread for the whole horizon
would report the easier step's uncertainty at the harder one.

**104 errors before scoring, and below that the week is skipped.** Two seasons,
which is what `MIN_ERROR_SAMPLE` fixes. Persistence reaches 103 errors by its first
origin, so its distributions begin one week later; the seasonal naive has 52 there
and begins later still. Inside the paper's window both are far above the floor and
it changes nothing — on the default panel to 2026 it trims the first weeks, and
`n_quantile` carries the count so the trimming is visible. A week below the floor
leaves the probabilistic tables and stays in the point ones; it does not receive a
quantile read off five observations.

**The point forecast is the centre of the distribution.** The errors are centred on
their own median before being added back, so the MAE and the WIS on the same line
score the same forecast. The baseline's bias stays where it is measured, in the
MAE.

### The quantile grid

Seven levels, 0.025 to 0.975 — three central intervals: 50%, 80% and 95%. The
subset comes from the COVID-19 Forecast Hub, which asks for it on incident cases.
The most extreme level is the second of eighty ordered observations and the error
samples run in the hundreds, so a wider grid would put weight on tails the sample
cannot support.

Quantiles are Hyndman & Fan's type 7, by linear interpolation — the definition
numpy, R and pandas call the default, so a reader recomputing one gets the number
printed here. Polars is the exception worth naming: `pl.Series.quantile` without an
argument interpolates to the nearest order statistic and returns a different value.

**One probabilistic number, not two.** On this symmetric grid the weighted interval
score is twice the mean pinball loss over the grid, which is the discretised CRPS
(Bracher et al. 2021). The paper therefore reports WIS, with the coverage and the
width of each central band beside it.

**The WIS is in cases and it is not on the MAE's scale.** The sum is divided by
`K + 1/2` before it is reported, where K is the number of intervals, so a WIS below
the MAE printed on the same line is not a gain. Read a WIS against another WIS.

### What the two baselines scored on the paper window

157 weeks, h=1, Brazil:

| Baseline | MAE | WIS | 50% band | 80% band | 95% band |
|---|---|---|---|---|---|
| persistence | 9,022 | 7,224 | 0.32 / 1,736 | 0.60 / 9,280 | 0.78 / 25,209 |
| seasonal naive | 39,552 | 31,890 | 0.50 / 11,139 | 0.77 / 59,940 | 0.87 / 169,523 |

Each band is written as coverage / width, in cases.

Both baselines' bands are narrower than they claim: the 95% band covers 0.78 of the
weeks for persistence and 0.87 for the seasonal naive. The sample behind each
origin holds errors made in quieter weeks, and the scored window contains 2024,
whose errors are larger than most of them. The gap between the coverage a band
claims and the coverage it reaches is read beside the width, and it is part of what
the paper reports.

## 4. What is deliberately not here yet

- **A model's own distribution.** The naive baselines are scored on WIS, coverage
  and width, but their spread is read off their own past errors, not produced by a
  model. The first model that emits intervals brings its own predictive
  distribution, and only then is a probabilistic comparison between
  *representations* possible. The rule it will be scored on already exists (§3) and
  is already exercised.
- **The target lag.** SINAN's most recent weeks are under-reported and get
  rewritten as notifications arrive — the last observed week here is 3,330 cases
  against ~9,000 the weeks before. It costs the headline number nothing (see
  above), but any *operational* reading has to end the panel well before the
  cliff.
- **Per-state reading.** Protocol 00 now declares UF as robustness beside the BR
  headline (2026-11-20), and the reason is measurable rather than editorial. The
  news feature tables do carry 28 locations — BR and the 27 UF, 2002-02-17 to
  2026-09-13 — but the state rows are a **locative attribution inside a single
  national outlet's corpus**. One article naming three states counts in all three,
  so the state rows hold 7,223 mentions for 4,369 national articles: they do not
  add up to the BR row, which contains every article by construction. BR stays the
  headline; UF is measured and reported beside it.
- **Covariates.** Google Trends and ERA5 enter with the "no text" baseline, not
  with the naive baselines: they are the first thing news has to beat, and beating
  the naive baselines alone proves nothing, because they are easier than these.
- **The annual MAPE denominator.** `mape` reports how many weeks it could score
  beside the value. On this series nothing is dropped — the floor is 1,341 cases
  — and the real cost is elsewhere: MAPE ranks weeks by relative error, so the
  week it calls worst erred 4,647 cases while the week MAE calls worst erred
  84,739. `evaluate` carries the denominator so a MAPE never travels without its
  base.

## 5. Open decisions this package has to absorb

Recorded in `notes/00-protocolo-comparacao.md`; the values now in force are in
`spec.py`, and every one is a flag on the command above.

| Decision | Now | Why |
|---|---|---|
| Horizon | 1 week headline; 4 weeks declared | Shortest path to a first number and where the naive is hardest to beat. Multi-step is measured as declared robustness, not promised as future work (2026-11-20). |
| Level | raw counts | Log is a modelling choice; it belongs with the model, not the ruler. |
| Geography | BR headline; UF declared | The comparison is honest where news and target share a grain — and the state rows are an attribution, not a partition (§4). |
| Score window | 2022-01-02 to 2024-12-29 | Where all four sources overlap. `--to-year 2024 --score-from 2022` cuts the scored weeks without cutting the training history, so a model still sees 2014 onward. |
| First week | 2014-01-05 | 2013 is incomplete. |
| Min train | 104 weeks | The seasonal baseline needs a full season *behind* the one it copies. |
| Seasonal lag | 52 weeks | Convention, not identity: a year is 52.18 weeks, so the reference week drifts about a day per cycle. |
