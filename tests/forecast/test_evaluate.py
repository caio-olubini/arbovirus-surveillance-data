"""O laço. O trabalho dele é ser entediante e nunca mostrar o futuro a um modelo."""

from __future__ import annotations

import polars as pl
import pytest

from src.forecast.evaluate import (
    COVERAGE,
    COVERAGE_LEVEL,
    MAE,
    MAPE_N,
    MEAN_TRUTH,
    N,
    N_QUANTILE,
    ORIGIN_EW,
    PRED,
    QUANTILE,
    RMSE,
    TRUE,
    WIDTH,
    WIS,
    evaluate,
    format_distribution,
    format_metrics,
)
from src.forecast.spec import (
    BASELINE,
    CENTRAL_INTERVALS,
    EW,
    HORIZON,
    MIN_ERROR_SAMPLE,
    QUANTILE_LEVELS,
)


def rising(n: int) -> list[float]:
    """1, 2, 3, … — uma série cujo erro é exatamente o passo do horizonte."""
    return [float(i) for i in range(1, n + 1)]


# Uma série que sobe aos altos e baixos, para que os erros de persistência não
# sejam todos iguais: numa série de erro constante a distribuição tem largura
# zero, e largura zero não testa largura nenhuma.
PATTERN = (3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0)


def wobbly(n: int) -> list[float]:
    return [PATTERN[i % len(PATTERN)] + 10.0 * (i // len(PATTERN)) for i in range(n)]


# Uma grade de três níveis e um piso baixo: os testes da distribuição são sobre a
# mecânica, e a mecânica é a mesma em três níveis e em sete. O padrão de verdade
# — sete níveis, 104 erros — é exercitado no teste que usa os dois de propósito.
GRID = (0.25, 0.5, 0.75)


def distributed(panel: pl.DataFrame, **kwargs):
    """Uma execução com distribuição em toda origem, para os testes da metade
    probabilística."""
    options = {
        "baselines": ("persistence",),
        "min_train": 8,
        "levels": GRID,
        "min_error_sample": 6,
    }
    return evaluate(panel, **{**options, **kwargs})


def distributed_on_every_level(panel: pl.DataFrame, **kwargs):
    """O mesmo, na grade de verdade.

    Uma faixa central só vira linha quando os dois níveis que a formam foram
    pontuados; com a grade de três níveis, só a de 50% existe. Os testes sobre
    cobertura e largura precisam das três, então usam esta.
    """
    options = {"baselines": ("persistence",), "min_train": 8, "min_error_sample": 6}
    return evaluate(panel, **{**options, **kwargs})


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


def test_a_step_of_two_scores_every_other_week(panel_from_values):
    """`step` não é só um número no registro: ele muda quais semanas são pontuadas.

    O teste acima confere que o valor é gravado. Conferir o valor e não conferir o
    efeito deixa passar uma execução que anda de duas em duas semanas, grava
    `step: 2` e pontua toda semana: o registro descreveria outra execução, e todos
    os números sairiam de um conjunto de semanas diferente do declarado.
    """
    panel = panel_from_values(rising(120))
    semanal = evaluate(panel, baselines=("persistence",), min_train=104)
    quinzenal = evaluate(panel, baselines=("persistence",), min_train=104, step=2)
    semanas = semanal.predictions[EW].to_list()
    assert quinzenal.predictions[EW].to_list() == semanas[::2]


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


def test_a_short_panel_is_blamed_on_min_train_and_not_on_a_baseline(panel_from_values):
    """Quem não cabe no painel é o treino mínimo, e a mensagem tem de dizer isso.

    Os erros que alimentam os quantis vêm dos dois ingênuos, e o sazonal precisa
    de 52 semanas de história. Num painel curto demais para o `min_train`, quem
    falhava primeiro era a amostra de erro, culpando o baseline por um painel que
    nunca chegou à primeira origem — e a mensagem que diz quantas semanas faltam
    ficava escondida atrás dela.
    """
    panel = panel_from_values(rising(20))
    with pytest.raises(ValueError, match="is not enough for min_train"):
        evaluate(panel, min_train=50)


def test_a_baseline_that_cannot_forecast_says_which_one_it_is(panel_from_values):
    """Com dois ingênuos na execução, a recusa tem de nomear qual deles parou."""
    panel = panel_from_values(rising(20))
    with pytest.raises(ValueError, match="seasonal_naive never produced"):
        evaluate(panel, min_train=10)


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


# --- a metade probabilística -------------------------------------------------
#
# Estas são as perguntas que a distribuição tem que responder: ela é da previsão
# que está na outra tabela, ela começa quando a amostra de erros enche, e o
# intervalo largo cobre mais porque é mais largo — nada disso é de graça.


def test_one_row_per_level_per_scored_week(panel_from_values):
    """A tabela é longa: três níveis viram três linhas, e não três colunas."""
    run = distributed(panel_from_values(wobbly(60)))
    assert run.predictions.height == 52
    assert run.quantile_predictions.height == 52 * len(GRID)
    # `n_quantile` conta semanas, não linhas: a tabela de quantis diz três vezes
    # o que `scored` diz uma vez, e citar a contagem de linhas seria citar 156.
    assert run.metrics[N_QUANTILE].to_list() == [52]


def test_the_median_row_is_the_point_forecast_itself(panel_from_values):
    """Sem isso, uma linha reportaria um MAE para uma previsão e um WIS para outra."""
    run = distributed(panel_from_values(wobbly(60)))
    median = run.quantile_predictions.filter(pl.col(QUANTILE) == 0.5)
    joined = median.join(
        run.predictions, on=[BASELINE, HORIZON, EW, ORIGIN_EW], how="inner"
    )
    assert joined.height == median.height  # cada linha de quantil achou uma previsão só
    assert (joined[f"{PRED}_right"] - joined[PRED]).abs().max() == 0.0


def test_the_distribution_grows_with_the_horizon_and_so_does_the_error(panel_from_values):
    """Numa série que sobe um por semana, o WIS é o passo do horizonte.

    A distribuição aqui tem largura zero — os erros passados são todos iguais —,
    então o que sobra é a distância: o passo 3 custa três vezes o passo 1.
    """
    run = distributed(panel_from_values(rising(60)), horizon=3)
    by_step = {r[HORIZON]: r[WIS] for r in run.metrics.iter_rows(named=True)}
    assert by_step == {1: 1.0, 2: 2.0, 3: 3.0}


def test_a_further_step_starts_its_distribution_later(panel_from_values):
    """O erro do passo 3 só é conhecido três semanas depois de cometido.

    É por isso que a amostra disponível ao passo 3 é sempre menor que a do passo
    1 na mesma origem, e o piso morde antes nele.
    """
    run = distributed(panel_from_values(rising(60)), horizon=3)
    counts = {r[HORIZON]: r[N_QUANTILE] for r in run.metrics.iter_rows(named=True)}
    assert counts[1] > counts[3]


def test_every_central_interval_gets_a_row(panel_from_values):
    run = distributed_on_every_level(panel_from_values(wobbly(60)))
    assert run.intervals.height == len(CENTRAL_INTERVALS)
    assert run.intervals[COVERAGE_LEVEL].to_list() == sorted(
        c for _, _, c in CENTRAL_INTERVALS
    )


def test_a_band_whose_levels_were_not_scored_is_left_out(panel_from_values):
    """Meia faixa não é uma faixa: sem os dois níveis, não há linha."""
    run = distributed(panel_from_values(wobbly(60)))  # grade de três níveis
    assert run.intervals.height == 1
    assert run.intervals[COVERAGE_LEVEL].to_list() == [0.5]


def test_the_wider_band_is_wider_and_covers_more(panel_from_values):
    """Cobertura sem largura não diz nada; largura sem cobertura também não."""
    run = distributed_on_every_level(panel_from_values(wobbly(60)))
    by_level = {r[COVERAGE_LEVEL]: r for r in run.intervals.iter_rows(named=True)}
    assert by_level[0.95][WIDTH] > by_level[0.5][WIDTH]
    assert by_level[0.95][COVERAGE] >= by_level[0.5][COVERAGE]
    assert by_level[0.95][COVERAGE] <= 1.0


def test_the_published_coverage_counts_the_weeks_inside_the_band(panel_from_values):
    """A cobertura publicada é contada de novo, a partir das linhas que a execução gravou.

    As duas asserções que existiam sobre esta coluna eram ordem entre as faixas e
    teto 1,0 — as duas satisfeitas por uma coluna constante. Zerar a cobertura
    publicada, ou forçá-la a 100% em toda faixa, passava a suíte inteira, e a
    cobertura é metade do que o README publica sobre a distribuição. A contagem
    aqui é refeita a partir das tabelas, sem chamar de novo a função que produziu
    o número: o que se confere é que a coluna conta as semanas que a faixa cobre.
    """
    run = distributed_on_every_level(panel_from_values(wobbly(60)))
    # Uma tabela de faixas vazia faria o laço abaixo não rodar e o teste passar sem
    # conferir nada — justamente o caso em que a cobertura publicada não existe.
    assert run.intervals.height == len(CENTRAL_INTERVALS)
    faixas = {cobertura: (baixo, alto) for baixo, alto, cobertura in CENTRAL_INTERVALS}
    verdade = run.predictions.select(BASELINE, HORIZON, EW, TRUE)
    for linha in run.intervals.iter_rows(named=True):
        baixo, alto = faixas[linha[COVERAGE_LEVEL]]
        dentro = verdade
        for nivel, nome in ((baixo, "baixo"), (alto, "alto")):
            dentro = dentro.join(
                run.quantile_predictions.filter(pl.col(QUANTILE) == nivel).select(
                    BASELINE, HORIZON, EW, pl.col(PRED).alias(nome)
                ),
                on=[BASELINE, HORIZON, EW],
            )
        dentro = dentro.filter(
            (pl.col(BASELINE) == linha[BASELINE]) & (pl.col(HORIZON) == linha[HORIZON])
        )
        cobriu = dentro.filter(
            (pl.col(TRUE) >= pl.col("baixo")) & (pl.col(TRUE) <= pl.col("alto"))
        ).height
        assert linha[COVERAGE] == pytest.approx(cobriu / dentro.height)


def test_the_shipped_grid_and_floor_are_the_ones_spec_declares(panel_from_values):
    """O padrão de verdade: sete níveis e 104 erros, e é ele que o artigo cita."""
    run = evaluate(panel_from_values(wobbly(140)), baselines=("persistence",), min_train=104)
    assert run.levels == QUANTILE_LEVELS
    assert run.min_error_sample == MIN_ERROR_SAMPLE
    assert run.quantile_predictions[QUANTILE].n_unique() == len(QUANTILE_LEVELS)
    assert run.intervals.height == len(CENTRAL_INTERVALS)
    row = run.metrics.row(0, named=True)
    # O piso corta o começo do painel: há menos semanas com distribuição do que
    # semanas pontuadas, e as duas contagens aparecem na tabela por isso.
    assert 0 < row[N_QUANTILE] < row[N]


def test_a_panel_without_enough_errors_says_so_instead_of_scoring_zero(panel_from_values):
    """Zero semanas de WIS e um WIS de zero são coisas diferentes."""
    run = evaluate(
        panel_from_values(wobbly(20)),
        baselines=("persistence",),
        min_train=8,
        levels=GRID,
        min_error_sample=104,
    )
    assert run.predictions.height == 12
    assert run.quantile_predictions.height == 0
    assert run.quantile_predictions.columns == [
        ORIGIN_EW,
        EW,
        HORIZON,
        BASELINE,
        TRUE,
        QUANTILE,
        PRED,
    ]
    assert run.metrics[N_QUANTILE].to_list() == [0]
    assert run.metrics[WIS].to_list() == [None]
    assert "No distribution was scored" in run.distribution_summary()


def test_a_floor_of_zero_skips_the_origin_whose_errors_are_not_known_yet(
    panel_from_values,
):
    """O piso zero é aceito pela linha de comando, e pular não pode virar derrubar.

    Na primeira origem do sazonal nenhum erro dele foi observado ainda — a amostra
    está vazia, e um quantil de nada não existe. Antes disso a execução abortava
    com "no sample to take a quantile of" em vez de pular a semana, que é o que a
    linha de comando promete para toda semana abaixo do piso.
    """
    run = evaluate(
        panel_from_values(wobbly(120)),
        baselines=("seasonal_naive",),
        min_train=52,
        levels=GRID,
        min_error_sample=0,
    )
    scored = run.metrics[N].to_list()[0]
    with_distribution = run.metrics[N_QUANTILE].to_list()[0]
    # Exatamente uma semana a menos: só a primeira origem fica sem distribuição,
    # porque só ela ainda não tinha nenhum erro observado para ler.
    assert scored - with_distribution == 1
    assert with_distribution > 0


def test_no_quantile_sees_the_week_it_is_predicting(panel_from_values):
    """A mesma regra do laço, agora sobre os quantis.

    Dois painéis idênticos até a semana 160 e opostos depois: toda linha de
    quantil de uma origem dentro do trecho comum tem que ser igual nos dois. Se
    alguma se mexeu, a amostra de erros leu o futuro.
    """
    common = wobbly(160)
    calm = panel_from_values(common + [1.0] * 40)
    shock = panel_from_values(common + [999_999.0] * 40)
    cutoff = calm[EW].to_list()[157]

    def up_to_cutoff(panel: pl.DataFrame) -> pl.DataFrame:
        run = distributed(panel, min_train=8)
        return run.quantile_predictions.filter(pl.col(ORIGIN_EW) <= cutoff)

    assert up_to_cutoff(calm).height > 0
    assert up_to_cutoff(calm).equals(up_to_cutoff(shock))


def test_the_scoring_window_cuts_the_distribution_too(panel_from_values):
    panel = panel_from_values(wobbly(400))
    full = distributed(panel, min_train=8)
    cut = distributed(panel, min_train=8, score_from=2024)
    assert 0 < cut.quantile_predictions.height < full.quantile_predictions.height
    assert all(week.year >= 2024 for week in cut.quantile_predictions[EW].to_list())
    assert cut.metrics[N_QUANTILE].to_list() == [
        cut.quantile_predictions.filter(pl.col(QUANTILE) == 0.5).height
    ]


def test_the_distribution_summary_shows_the_weeks_behind_each_wis(panel_from_values):
    run = distributed_on_every_level(panel_from_values(wobbly(60)))
    text = run.distribution_summary()
    assert text == format_distribution(run.metrics, run.intervals)
    assert "WIS" in text
    assert str(run.metrics.row(0, named=True)[N_QUANTILE]) in text
    for _, _, nominal in CENTRAL_INTERVALS:
        assert f"{nominal * 100:,.0f}%" in text
    # Duas tabelas: a do WIS com uma linha por baseline, e a das faixas com uma
    # linha por faixa, separadas por uma linha em branco.
    assert len(text.splitlines()) == 3 + 1 + (2 + len(CENTRAL_INTERVALS))
