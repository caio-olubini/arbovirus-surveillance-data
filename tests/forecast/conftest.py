"""Construtores compartilhados pelos testes do forecast.

Os dois são fábricas e não quadros fixos: o ponto da maioria destes testes é o
que acontece numa forma específica (um buraco, um horizonte maior que a cauda), e
uma fixture fixa teria que ser re-derivada por teste de qualquer jeito.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import polars as pl
import pytest

from src.forecast.spec import CASES, EW
from src.pipeline.sinan.spec import CASE_COUNT, EW_SYMPTOM_ONSET, FINAL_CLASSIFICATION

# Um domingo, para as semanas caírem no mesmo dia da semana que o painel usa.
START = dt.date(2020, 1, 5)
SUSPECTED = 1  # qualquer CLASSI_FIN diferente de 5
DISCARDED = 5

REPO = Path(__file__).resolve().parents[2]
# A tabela de casos que `arboili transform sinan` escreve por padrão. Só existe
# depois que a transformação real de ~7 GB rodou, e é por isso que o teste que a
# lê pula quando ela falta, em vez de falhar num checkout limpo.
REAL_CASES = REPO / "data" / "epidemiological" / "SINAN" / "SINAN_dengue_cases.parquet"
# A tabela de referência de 27 linhas de onde o projeto inteiro lê códigos de estado.
FEDERATIVE_UNITS = REPO / "data" / "epidemiological" / "br_federative_units.csv"


@pytest.fixture(scope="session")
def real_cases_path() -> str:
    """Caminho para a tabela de casos do arquivo completo; pula se não foi construída."""
    if not REAL_CASES.exists():
        pytest.skip(f"{REAL_CASES.name} not built — run `arboili transform sinan`")
    return str(REAL_CASES)


@pytest.fixture(scope="session")
def fu_path() -> Path:
    """A tabela de referência de unidades federativas, para os testes de `by_state`."""
    return FEDERATIVE_UNITS


@pytest.fixture
def panel_from_values():
    """Um painel-alvo: uma linha por semana, exatamente as colunas de `load_target`."""

    def _make(values: list[float], start: dt.date = START) -> pl.DataFrame:
        return pl.DataFrame(
            {
                EW: pl.date_range(
                    start,
                    start + dt.timedelta(weeks=len(values) - 1),
                    interval="1w",
                    eager=True,
                ),
                CASES: [float(v) for v in values],
            }
        )

    return _make


@pytest.fixture
def cases_from_weeks():
    """Um quadro em nível de caso: a entrada que `weekly_cases` espera, uma linha por caso.

    `weeks` mapeia um deslocamento de semana a partir de START para pares
    (casos, classificação), então um teste pode somar duas linhas na mesma semana
    ou deixar uma semana de fora por inteiro — que é o único jeito de exercitar a
    guarda de buraco.
    """

    def _make(weeks: dict[int, list[tuple[int, int]]]) -> pl.DataFrame:
        dates, counts, classes = [], [], []
        for offset, rows in weeks.items():
            for count, classification in rows:
                dates.append(START + dt.timedelta(weeks=offset))
                counts.append(count)
                classes.append(classification)
        return pl.DataFrame(
            {
                EW_SYMPTOM_ONSET: dates,
                CASE_COUNT: counts,
                FINAL_CLASSIFICATION: classes,
            }
        )

    return _make
