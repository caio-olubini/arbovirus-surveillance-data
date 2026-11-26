"""A distribuição que os baselines ingênuos ganham a partir dos próprios erros.

O que estes testes protegem é a propriedade que torna a coisa uma medição e não
um enfeite: no momento da origem, o quantil só pode ter visto o passado.
"""

from __future__ import annotations

import polars as pl
import pytest

from src.forecast.baselines import persistence, seasonal_naive
from src.forecast.interval import (
    ErrorHistory,
    empirical_quantile,
    error_histories,
    predictive_quantiles,
    quantiles_from_sample,
)
from src.forecast.spec import QUANTILE_LEVELS, SEASONAL_LAG


def rising(n: int) -> list[float]:
    return [float(i) for i in range(1, n + 1)]


# --- o quantil ---------------------------------------------------------------


@pytest.mark.parametrize("level", [0.025, 0.1, 0.25, 0.5, 0.9, 0.975])
def test_the_quantile_is_the_one_the_rest_of_the_world_computes(level):
    """Tipo 7 de Hyndman & Fan: o padrão de numpy, R e pandas.

    A definição importa — os nove tipos daquele artigo discordam entre si —, então
    ela é conferida contra uma implementação de fora em vez de contra a minha
    conta. `interpolation="linear"` é dito por extenso porque o padrão do Polars é
    `nearest`: quem recalcular esta coluna com `pl.Series.quantile` sem passar a
    interpolação obtém outro número, e é melhor descobrir isso aqui do que numa
    revisão.
    """
    values = [3.0, 1.0, 4.0, 1.5, 9.0, 2.6, 5.3]
    assert empirical_quantile(sorted(values), level) == pytest.approx(
        pl.Series(values).quantile(level, interpolation="linear")
    )


def test_the_median_of_an_odd_sample_is_the_middle_observation():
    assert empirical_quantile([1.0, 2.0, 3.0], 0.5) == 2.0


def test_a_level_outside_the_open_unit_interval_is_refused():
    with pytest.raises(ValueError, match="strictly between"):
        empirical_quantile([1.0, 2.0], 0.0)


def test_an_empty_sample_has_no_quantile():
    with pytest.raises(ValueError, match="no sample"):
        empirical_quantile([], 0.5)


def test_every_level_comes_out_of_one_sample():
    values = [1.0, 2.0, 3.0, 4.0]
    quantiles = quantiles_from_sample(values, (0.25, 0.5, 0.75))
    assert quantiles == {0.25: 1.75, 0.5: 2.5, 0.75: 3.25}


# --- a amostra de erros ------------------------------------------------------


def test_persistence_past_errors_are_the_weekly_steps():
    """Numa série que sobe um por semana, o erro de persistência é sempre 1."""
    history = error_histories(rising(10), 1, persistence)
    assert history[1].values == [1.0] * 9


def test_the_first_error_is_the_first_week_the_baseline_could_answer():
    """A persistência responde desde a segunda semana; a sazonal, só depois de um ano."""
    values = rising(120)
    assert error_histories(values, 1, persistence)[1].first == 0
    assert error_histories(values, 1, seasonal_naive)[1].first == SEASONAL_LAG - 1


def test_each_step_of_the_horizon_gets_its_own_errors():
    """O passo 4 erra mais que o passo 1, e as duas amostras não podem ser a mesma."""
    history = error_histories(rising(120), 4, persistence)
    assert set(history) == {1, 2, 3, 4}
    assert history[1].values[0] == 1.0
    assert history[4].values[0] == 4.0


def test_a_baseline_that_never_fits_is_refused_rather_than_left_empty():
    with pytest.raises(ValueError, match="never produced a forecast"):
        error_histories(rising(20), 1, seasonal_naive)


def test_the_refusal_carries_the_baselines_own_reason():
    """Um horizonte maior que a defasagem sazonal não é culpa do painel.

    A mensagem dizia só "nunca previu nada num painel de N semanas", e a causa
    real — o passo passar da defasagem — ficava apenas no `__cause__`. Quem lê a
    mensagem tentaria alargar o painel, que não tem nada a ver com o problema.
    """
    with pytest.raises(ValueError) as excinfo:
        error_histories(rising(120), SEASONAL_LAG + 1, seasonal_naive)
    assert "exceeds lag" in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, ValueError)


# --- o limite do passado -----------------------------------------------------


def test_the_sample_stops_at_the_origin():
    """O erro cometido na semana t só é conhecido na origem t + passo."""
    history = ErrorHistory(first=0, values=[float(i) for i in range(20)], step=1)
    assert len(history.sample(10)) == 10
    assert history.sample(10) == [float(i) for i in range(10)]


def test_a_step_further_ahead_shows_less():
    """O passo 4 precisa de mais semanas observadas para o mesmo erro estar pronto."""
    history = ErrorHistory(first=0, values=[float(i) for i in range(20)], step=4)
    assert len(history.sample(10)) == 7


def test_an_origin_inside_the_warmup_sees_nothing():
    history = ErrorHistory(first=51, values=[float(i) for i in range(20)], step=1)
    assert history.sample(20) == []


def test_the_sample_does_not_move_when_the_future_moves():
    """A mesma propriedade do laço, aplicada à distribuição.

    Dois painéis idênticos até a semana 60 e opostos depois: toda amostra visível
    de uma origem dentro do trecho comum tem que ser igual nos dois. É o que
    impede o quantil de usar a semana que ele deveria estar prevendo.
    """
    common = rising(60)
    for name, func in (("persistence", persistence), ("seasonal_naive", seasonal_naive)):
        calm = error_histories(common + [1.0] * 60, 1, func)
        shock = error_histories(common + [999_999.0] * 60, 1, func)
        for origin in (58, 59):
            assert calm[1].sample(origin) == shock[1].sample(origin), name


# --- a distribuição ---------------------------------------------------------


def test_a_thin_sample_gives_no_distribution_instead_of_a_made_up_one():
    """Cinco erros não fazem um quantil de 2,5%, e o resultado é ausência, não 0."""
    assert predictive_quantiles(100.0, [1.0, 2.0, 3.0, 4.0, 5.0], QUANTILE_LEVELS) is None


def test_the_distribution_is_centred_on_the_point_forecast():
    """A mediana da distribuição é a previsão pontual, ao caso.

    Sem isso, uma linha da tabela reportaria um MAE para uma previsão e um WIS
    para outra — e o viés do naive entraria na largura, que é o lugar errado.
    """
    sample = [1.0, 2.0, 3.0, 100.0, 101.0, 102.0, 103.0]
    quantiles = predictive_quantiles(5_000.0, sample, QUANTILE_LEVELS, min_sample=1)
    assert quantiles[0.5] == 5_000.0


def test_a_sample_below_the_floor_produces_nothing():
    assert predictive_quantiles(10.0, [1.0] * 103, QUANTILE_LEVELS, min_sample=104) is None
    assert predictive_quantiles(10.0, [1.0] * 104, QUANTILE_LEVELS, min_sample=104) is not None


def test_an_empty_sample_is_skipped_whatever_the_floor_says():
    """Piso zero não transforma nada em alguma coisa.

    Zero é um piso que a linha de comando aceita, e quer dizer "pontue assim que
    houver um erro". A primeira origem de um baseline cujos erros ainda não são
    conhecidos tem amostra vazia, e antes disso ela derrubava a execução inteira
    com "no sample to take a quantile of", em vez de pular a semana como todas as
    outras abaixo do piso.
    """
    assert predictive_quantiles(10.0, [], QUANTILE_LEVELS, min_sample=0) is None
    assert predictive_quantiles(10.0, [], QUANTILE_LEVELS, min_sample=-5) is None


def test_the_spread_is_the_sample_spread():
    """Uma amostra de erros constante dá um intervalo de largura zero."""
    quantiles = predictive_quantiles(10.0, [3.0] * 120, QUANTILE_LEVELS, min_sample=1)
    assert set(quantiles.values()) == {10.0}
