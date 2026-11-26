"""As constantes conferem a si mesmas no import.

A grade de quantis e as faixas centrais ficam escritas em dois lugares: a grade
diz quais níveis existem, e a tabela diz qual par forma cada faixa e que cobertura
ela promete. As duas podem divergir — basta alguém digitar um par que não está na
grade, ou uma cobertura que não é a daquela faixa —, então a concordância é
verificada. Não é obstáculo de ponto flutuante: `1 - 0.025` é o mesmo double que
`0.975`, então a tabela também poderia ser derivada. Uma faixa central que some 1 e
cujo par existe na grade é o que faz a largura e a cobertura de uma linha
descreverem a faixa que o nome dela diz.

A checagem roda uma vez, no import. Estes testes a chamam de novo, com as
constantes trocadas por monkeypatch, porque é a única maneira de exercitar a
recusa sem quebrar o módulo para o resto da suíte.
"""

from __future__ import annotations

import pytest

from src.forecast import spec


def test_the_shipped_constants_pass_their_own_check():
    spec._check_grid()


def test_a_pair_whose_levels_do_not_add_to_one_is_refused(monkeypatch):
    """O par trocado que passa pela checagem de cobertura.

    `(0.025, 0.9)` soma 0,925 — não é uma faixa central —, mas as duas metades
    existem na grade e `1 - 2 * 0.025` continua batendo com a cobertura
    declarada. A soma é a única das três checagens que recusa este par, e sem ela
    a tabela publicaria a largura de uma faixa com o nome de outra.
    """
    monkeypatch.setattr(spec, "CENTRAL_INTERVALS", ((0.025, 0.9, 0.95),))
    with pytest.raises(RuntimeError, match="must add to 1"):
        spec._check_grid()


def test_a_band_that_claims_the_wrong_coverage_is_refused(monkeypatch):
    monkeypatch.setattr(spec, "CENTRAL_INTERVALS", ((0.025, 0.975, 0.9),))
    with pytest.raises(RuntimeError, match="claims coverage"):
        spec._check_grid()


def test_a_level_that_is_not_in_the_grid_is_refused(monkeypatch):
    monkeypatch.setattr(spec, "CENTRAL_INTERVALS", ((0.025, 0.96, 0.95),))
    with pytest.raises(RuntimeError, match="not in"):
        spec._check_grid()


def test_the_shipped_bands_are_the_ones_the_grid_supports():
    """Três faixas, três pares, e a grade é exatamente a união delas com a mediana."""
    pairs = {(lower, upper) for lower, upper, _ in spec.CENTRAL_INTERVALS}
    assert pairs == {(0.025, 0.975), (0.1, 0.9), (0.25, 0.75)}
    na_grade = {0.5}
    for lower, upper in pairs:
        na_grade |= {lower, upper}
    assert na_grade == set(spec.QUANTILE_LEVELS)
