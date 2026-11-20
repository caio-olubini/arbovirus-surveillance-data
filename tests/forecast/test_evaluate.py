"""O laço. O trabalho dele é ser entediante e nunca mostrar o futuro a um modelo."""

from __future__ import annotations

import polars as pl
import pytest

from src.forecast.evaluate import (
    MAE,
    MAPE_N,
    MEAN_TRUTH,
    N,
    ORIGIN_EW,
    PRED,
    RMSE,
    TRUE,
    evaluate,
    format_metrics,
)
from src.forecast.spec import BASELINE, EW, HORIZON


def rising(n: int) -> list[float]:
    """1, 2, 3, … — uma série cujo erro é exatamente o passo do horizonte."""
    return [float(i) for i in range(1, n + 1)]


# --- forma ------------------------------------------------------------------


def test_one_row_per_scored_week_per_baseline(panel_from_values):
    panel = panel_from_values(rising(10))
    run = evaluate(panel, baselines=("persistence",), min_train=4, horizon=1)
    assert run.predictions.height == 6  # 10 semanas, 4 treinam, 1 pontua


def test_two_baselines_double_the_rows_and_get_a_line_each(panel_from_values):
    panel = panel_from_values(rising(120))
    run = evaluate(panel, min_train=104, horizon=1)
    assert run.metrics.height == 2
    assert set(run.metrics[BASELINE].to_list()) == {"persistence", "seasonal_naive"}
    assert run.predictions.height == 2 * 16


def test_the_run_records_the_setup_it_was_given(panel_from_values):
    """Um número sem suas flags não é reproduzível."""
    panel = panel_from_values(rising(120))
    run = evaluate(panel, min_train=104, horizon=1)
    assert run.horizon == 1
    assert run.min_train == 104
    assert run.baselines == ("persistence", "seasonal_naive")
    # `step` muda quais semanas são pontuadas, então uma execução que andou de
    # duas em duas semanas tem que ser distinguível de uma que andou toda semana.
    assert evaluate(panel, min_train=104, step=2).step == 2


def test_predictions_name_the_origin_week_they_were_made_from(panel_from_values):
    panel = panel_from_values(rising(10))
    run = evaluate(panel, baselines=("persistence",), min_train=4, horizon=1)
    weeks = panel[EW].to_list()
    for row in run.predictions.iter_rows(named=True):
        assert row[ORIGIN_EW] == weeks[weeks.index(row[EW]) - 1]


# --- a aritmética -----------------------------------------------------------


def test_persistence_error_equals_the_step_at_every_step(panel_from_values):
    """Numa série que sobe um por semana, estar h passos velho custa exatamente h."""
    panel = panel_from_values(rising(20))
    run = evaluate(panel, baselines=("persistence",), min_train=4, horizon=3)
    by_step = {r[HORIZON]: r[MAE] for r in run.metrics.iter_rows(named=True)}
    assert by_step == {1: 1.0, 2: 2.0, 3: 3.0}


def test_seasonal_naive_error_equals_the_annual_gap(panel_from_values):
    """52 semanas atrás numa série que sobe um por semana erra 52, toda semana."""
    panel = panel_from_values(rising(120))
    run = evaluate(panel, baselines=("seasonal_naive",), min_train=104, horizon=1)
    assert run.metrics[MAE].to_list() == [52.0]


def test_mape_denominator_is_reported_beside_mape(panel_from_values):
    panel = panel_from_values(rising(120))
    run = evaluate(panel, baselines=("persistence",), min_train=104, horizon=1)
    row = run.metrics.row(0, named=True)
    assert row[MAPE_N] == row[N]  # sem semanas zero nesta série, então nenhuma cai


def test_the_summary_reports_the_scale_of_the_series(panel_from_values):
    panel = panel_from_values(rising(120))
    run = evaluate(panel, baselines=("persistence",), min_train=104, horizon=1)
    row = run.metrics.row(0, named=True)
    assert row[MEAN_TRUTH] == pytest.approx(sum(rising(120)[104:]) / 16)


def test_metrics_group_by_step_rather_than_averaging_them(panel_from_values):
    panel = panel_from_values(rising(20))
    run = evaluate(panel, baselines=("persistence",), min_train=4, horizon=3)
    assert sorted(run.metrics[HORIZON].to_list()) == [1, 2, 3]


def test_rmse_is_at_least_mae_in_the_table(panel_from_values):
    panel = panel_from_values(rising(120))
    run = evaluate(panel, min_train=104, horizon=1)
    for row in run.metrics.iter_rows(named=True):
        assert row[RMSE] >= row[MAE]


# --- a regra que importa ----------------------------------------------------


def test_a_model_never_sees_a_week_after_its_origin(panel_from_values):
    """Dois painéis idênticos nas primeiras 59 semanas, depois bem diferentes.

    Toda previsão feita de uma origem dentro do trecho comum tem que ser idêntica
    nas duas execuções. Se alguma se mexeu, o laço leu o futuro.
    """
    common = rising(59)
    calm = panel_from_values(common + [1.0] * 61)
    shock = panel_from_values(common + [999_999.0] * 61)
    # A última origem cuja semana *pontuada* ainda está dentro do trecho comum.
    cutoff = calm[EW].to_list()[57]

    def up_to_cutoff(panel: pl.DataFrame) -> pl.DataFrame:
        run = evaluate(panel, baselines=("persistence",), min_train=4, horizon=1)
        return run.predictions.filter(pl.col(ORIGIN_EW) <= cutoff)

    assert up_to_cutoff(calm).equals(up_to_cutoff(shock))


def test_the_scored_week_is_always_after_the_origin_week(panel_from_values):
    panel = panel_from_values(rising(20))
    run = evaluate(panel, baselines=("persistence",), min_train=4, horizon=3)
    weeks = {w: i for i, w in enumerate(panel[EW].to_list())}
    for row in run.predictions.iter_rows(named=True):
        assert weeks[row[EW]] > weeks[row[ORIGIN_EW]]


def test_predictions_are_complete_and_ordered_within_each_baseline(panel_from_values):
    """Ordenadas por (baseline, passo): um bloco contíguo que anda pra frente cada."""
    panel = panel_from_values(rising(120))
    run = evaluate(panel, min_train=104, horizon=2)
    assert run.predictions[TRUE].null_count() == 0
    assert run.predictions[PRED].null_count() == 0
    for _, group in run.predictions.group_by([BASELINE, HORIZON], maintain_order=True):
        assert group[EW].is_sorted()
        assert group[ORIGIN_EW].is_sorted()


# --- recusas ----------------------------------------------------------------


def test_an_unknown_baseline_is_refused(panel_from_values):
    panel = panel_from_values(rising(20))
    with pytest.raises(ValueError, match="unknown baseline"):
        evaluate(panel, baselines=("oracle",), min_train=4)


def test_an_empty_baseline_list_is_refused(panel_from_values):
    panel = panel_from_values(rising(20))
    with pytest.raises(ValueError, match="no baselines"):
        evaluate(panel, baselines=(), min_train=4)


def test_a_panel_too_short_to_forecast_is_refused(panel_from_values):
    panel = panel_from_values(rising(10))
    with pytest.raises(ValueError, match="not enough"):
        evaluate(panel, baselines=("persistence",), min_train=20)


# --- a janela de pontuação --------------------------------------------------


def test_score_from_grades_only_weeks_in_later_years(panel_from_values):
    panel = panel_from_values(rising(200))
    run = evaluate(panel, baselines=("persistence",), min_train=8, score_from=2022)
    assert run.score_from == 2022
    assert all(week.year >= 2022 for week in run.predictions[EW].to_list())


def test_score_from_filters_the_scored_week_not_the_panel(panel_from_values):
    """Pontua as semanas da execução cheia a partir do ano — mesmas origens.

    O histórico atrás da primeira previsão corrigida fica intacto, então o corte
    é na semana prevista e não na semana em que o modelo estava.
    """
    panel = panel_from_values(rising(200))
    full = evaluate(panel, baselines=("persistence",), min_train=8)
    cut = evaluate(panel, baselines=("persistence",), min_train=8, score_from=2022)
    expected = [w for w in full.predictions[EW].to_list() if w.year >= 2022]
    assert cut.predictions[EW].to_list() == expected


def test_a_later_score_from_scores_fewer_weeks(panel_from_values):
    """As duas execuções diferem em quanto pontuam, e ambas pontuam algo."""
    panel = panel_from_values(rising(200))
    earlier = evaluate(panel, baselines=("persistence",), min_train=8, score_from=2021)
    later = evaluate(panel, baselines=("persistence",), min_train=8, score_from=2022)
    assert earlier.predictions.height > later.predictions.height > 0


def test_score_from_defaults_to_grading_every_week(panel_from_values):
    panel = panel_from_values(rising(120))
    run = evaluate(panel, baselines=("persistence",), min_train=104)
    assert run.score_from is None


def test_a_score_from_past_the_panel_is_refused(panel_from_values):
    panel = panel_from_values(rising(120))
    with pytest.raises(ValueError, match="no scored week"):
        evaluate(panel, baselines=("persistence",), min_train=8, score_from=2099)


# --- apresentação -----------------------------------------------------------


def test_the_summary_is_plain_text_with_every_baseline_in_it(panel_from_values):
    panel = panel_from_values(rising(120))
    run = evaluate(panel, min_train=104, horizon=1)
    text = run.summary()
    assert "persistence" in text
    assert "seasonal_naive" in text
    assert "MAE" in text
    assert len(text.splitlines()) == 4  # header, rule, and one row per baseline


def test_the_formatting_helper_accepts_a_bare_table(panel_from_values):
    panel = panel_from_values(rising(120))
    run = evaluate(panel, baselines=("persistence",), min_train=104, horizon=1)
    assert format_metrics(run.metrics) == run.summary()
