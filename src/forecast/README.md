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
| Rolling origin | `rolling_origin` | **complete** |
| Naive baselines | `python -m src.forecast` | **complete** |
| Point metrics | `mae`, `rmse`, `mape` | **complete** |
| Run record | `setup_record`, `write_record` | **complete** |
| "No text" model (SINAN + GT + ERA5) | — | next |

```bash
uv run python -m src.forecast --out data/forecast
```

The command prints the table and writes three files into `--out`:
`dengue_br_h1_predictions.parquet` (one row per scored week), `..._metrics.parquet`
(the summary) and `..._run.json` (the setup). The record exists because the
summary does not defend itself: read it six months later and it cannot say
whether the history was 104 weeks or 200, and the difference between those two
is not small. It carries no date or time, so two runs of the same command write
the same bytes — a record that differs means a flag differed.

---

## 1. The first number

Brazil, all ages, suspected dengue, **1 week ahead**, first forecast after 104
weeks (two years) of history. 661 weeks from 2014-01-05 to 2026-08-30,
19,039,254 cases; 557 scored week-forecasts per baseline.

| Baseline | MAE (cases/week) | RMSE | MAPE |
|---|---|---|---|
| persistence (last observed week) | **4,047** | 9,716 | 13.3% |
| seasonal naive (same week last year) | 30,714 | 70,080 | 119.8% |

**Persistence is the real bar, not the seasonal naive.** Copying last year is
7.6× worse than copying last week, because dengue in Brazil moves by multiples
between years — 2024 averaged 125,779 cases/week against 32,001 in 2023. The
seasonal naive predicts the previous season's level into a year that has nothing
to do with it. Any later claim of the form "our model beats the naive baseline"
has to say *which* naive, and the honest one is persistence.

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

## 3. What is deliberately not here yet

- **Probabilistic metrics.** Protocol 00 asks for WIS/CRPS and coverage beside
  the point metrics. The baselines emit one number per week, so there is no
  distribution to score; computing them now would mean inventing an uncertainty
  the baseline never claimed. They arrive with the first model that produces
  intervals.
- **The target lag.** SINAN's most recent weeks are under-reported and get
  rewritten as notifications arrive — the last observed week here is 3,330 cases
  against ~9,000 the weeks before. It costs the headline number nothing (see
  above), but any *operational* reading has to end the panel well before the
  cliff.
- **Per-state reading.** Protocol 00 lists UF as exploratory and BR as the
  honest level: news is national and the target here is national, so there is no
  spatial mismatch to explain away. UF comes after the BR comparison works.
- **Covariates.** Google Trends and ERA5 enter with the "no text" baseline, not
  with the baselines — they are the first thing news has to beat, not the floor.
- **The annual MAPE denominator.** `mape` reports how many weeks it could score
  beside the value. On this series nothing is dropped — the floor is 1,341 cases
  — and the real cost is elsewhere: MAPE ranks weeks by relative error, so the
  week it calls worst erred 4,647 cases while the week MAE calls worst erred
  84,739. `evaluate` carries the denominator so a MAPE never travels without its
  base.

## 4. Open decisions this package has to absorb

Recorded in `notes/00-protocolo-comparacao.md`; the values now in force are in
`spec.py`, and every one is a flag on the command above.

| Decision | Now | Why |
|---|---|---|
| Horizon | 1 week | Shortest path to a first number and where the naive is hardest to beat. Multi-step is the next axis. |
| Level | raw counts | Log is a modelling choice; it belongs with the model, not the ruler. |
| Geography | BR | The comparison is honest where news and target share a grain. |
| First week | 2014-01-05 | 2013 is incomplete. |
| Min train | 104 weeks | The seasonal baseline needs a full season *behind* the one it copies. |
| Seasonal lag | 52 weeks | Convention, not identity: a year is 52.18 weeks, so the reference week drifts about a day per cycle. |
